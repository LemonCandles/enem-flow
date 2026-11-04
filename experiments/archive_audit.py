"""Auditoria integral do catálogo instalado, usando fontes e banco de ensaio."""

from collections import Counter
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import unicodedata

import pymupdf as fitz

from .common import ROOT, digest, file_digest, read_json, source_path, write_json


def plain(text):
    text = unicodedata.normalize('NFKD', text).casefold()
    return re.findall(r'[a-z0-9]+', ''.join(c for c in text if not unicodedata.combining(c)))


def independent_key(text, language, numbers, booklet=None):
    """Parser de linhas do Poppler, independente do extrator usado na geração."""
    order = [m.group().casefold().replace('ê', 'e') for m in re.finditer(r'INGL[ÊE]S|ESPANHOL', text, re.I)]
    order = list(dict.fromkeys(order))
    colors = list(
        dict.fromkeys(
            m.casefold()
            for m in re.findall(r'Gab[_ -]+(Azul|Amarelo|Branco|Rosa|Cinza|Verde|Laranja|Roxo)\b', text, re.I)
        )
    )
    color = next((color for color in colors if color in (booklet or '').casefold()), None)
    if len(colors) > 1 and color is None:
        raise ValueError('Informe a cor para o gabarito combinado.')
    answers = {}
    for line in text.splitlines():
        entries = list(
            re.finditer(r'(?<!\w)(\d{1,3})\s+\*?(ANULAD[AO]|[ABCDE])\b(?:\s+\*?(ANULAD[AO]|[ABCDE])\b)?', line, re.I)
        )
        for column, match in enumerate(entries):
            if len(colors) > 1 and column != colors.index(color):
                continue
            number = int(match[1])
            if number not in numbers:
                continue
            value = match[2]
            if match[3]:
                if len(order) != 2 or language not in order:
                    raise ValueError('Colunas de língua sem escolha inequívoca.')
                value = (match[2], match[3])[order.index(language)]
            answer = None if value.upper().startswith('ANULAD') else value.upper()
            if number in answers and answers[number] != answer:
                raise ValueError(f'Gabaritos conflitantes para {number}.')
            answers[number] = answer
    return answers


@lru_cache(maxsize=150)
def key_texts(path):
    with fitz.open(path) as doc:
        mupdf = '\n'.join(page.get_text() for page in doc)
    result = subprocess.run(['pdftotext', '-layout', '-nopgbrk', path, '-'], capture_output=True, text=True, check=True)
    return mupdf, result.stdout


def installed_exams(database):
    with sqlite3.connect(f'file:{Path(database).resolve()}?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        exams = [dict(row) for row in db.execute('SELECT * FROM exams WHERE status="published" ORDER BY year,id')]
        versions = {row['id']: dict(row) for row in db.execute('SELECT * FROM question_versions')}
    for exam in exams:
        exam['source'] = json.loads(exam['source'])
        exam['items'] = [
            dict(versions[key], content=json.loads(versions[key]['content'])) for key in json.loads(exam['items'])
        ]
    return exams


def audit_exam(exam, files, output, render_sources=False):
    from backend.app.schemas import QuestionContent
    from backend.app.preparation import blocking_issues
    from backend.app.services.content import iter_assets
    from scripts.exam_pdf import answer_key_rows, garbled

    questions, errors = [], []
    source = exam['source']
    find = lambda url, sha: next((r for r in files if r['url'] == url and r.get('sha256') == sha), None)
    record, key_record = (
        find(source['url'], source['sha256']),
        find(source['answer_key_url'], source['answer_key_sha256']),
    )
    if record is None or key_record is None:
        raise ValueError(f'{exam["id"]}: fonte/gabarito não registrados com os hashes declarados.')
    pdf = source_path('data/sources/' + record['path'], source['sha256'])
    key = source_path('data/sources/' + key_record['path'], source['answer_key_sha256'])
    numbers = {q['content']['number'] for q in exam['items']}
    languages = {
        q['content']['layout'].get('language')
        for q in exam['items']
        if q['content'].get('layout') and q['content']['layout'].get('language')
    }
    if len(languages) > 1:
        raise ValueError('Uma prova contém mais de uma opção de língua.')
    language = next(iter(languages), None)
    mupdf_text, poppler_text = key_texts(str(key))
    original = answer_key_rows(mupdf_text, language, numbers, exam['booklet'])
    independent = independent_key(poppler_text, language, numbers, exam['booklet'])
    if original != independent or set(original) != numbers:
        errors.append(
            {
                'code': 'answer_key_parser_disagreement',
                'missing': sorted(numbers - set(independent)),
                'differences': [n for n in numbers if original.get(n, '?') != independent.get(n, '?')],
            }
        )
    if len(exam['items']) != exam['expected_items'] or len(numbers) != len(exam['items']):
        errors.append({'code': 'invalid_exam_cardinality'})
    assets = {}
    with fitz.open(pdf) as doc:
        for item in exam['items']:
            c = QuestionContent.model_validate(item['content']).model_dump()
            findings = []
            n = c['number']
            if n not in original or c['correct_answer'] != original[n] or c['annulled'] != (original[n] is None):
                findings.append(
                    {'code': 'answer_key_mismatch', 'installed': c['correct_answer'], 'official': original.get(n)}
                )
            regions = (c.get('layout') or {}).get('blocks', [])
            source_text = ''
            for region in regions:
                page, box = region['page'], fitz.Rect(region['bbox'])
                if page < 1 or page > len(doc) or box.is_empty or not doc[page - 1].rect.contains(box):
                    findings.append({'code': 'invalid_source_region'})
                    continue
                source_text += '\n' + doc[page - 1].get_text(clip=box)
            if not regions:
                findings.append({'code': 'missing_source_regions'})
            displayed = '\n'.join(b['text'] for b in c['blocks'] if b['type'] == 'paragraph')
            displayed += '\n' + '\n'.join(a['text'] for a in c['alternatives'])
            for block in c['blocks']:
                if block['type'] == 'table':
                    displayed += '\n' + '\n'.join([*block['headers'], *(cell for row in block['rows'] for cell in row)])
                if block['type'] == 'image':
                    displayed += '\n' + block.get('caption', '') + '\n' + block.get('credit', '')
            if any('Alternativa não extraída' in a['text'] for a in c['alternatives']):
                findings.append({'code': 'placeholder_alternative'})
            if re.search(r'INSTRUÇÕES PARA A REDAÇÃO|PROPOSTA DE REDAÇÃO', displayed):
                findings.append({'code': 'unrelated_essay_section'})
            if '\ufffd' in displayed or any(garbled(line) for line in displayed.splitlines()):
                findings.append({'code': 'unreadable_displayed_text'})
            if any(ord(char) < 32 and char not in '\n\t\r' for char in displayed):
                findings.append({'code': 'control_character'})
            source_words = Counter(plain(source_text))
            native_words = Counter(plain(displayed))
            recall = sum((source_words & native_words).values()) / max(1, sum(source_words.values()))
            # Uma figura pode conter texto legítimo: cobertura baixa é triagem,
            # não prova automática de perda semântica.
            if recall < 0.65:
                findings.append({'code': 'low_text_coverage', 'ratio': recall})
            for asset in iter_assets(c):
                path = (ROOT / 'data' / asset['path'].lstrip('/')).resolve()
                if not path.is_relative_to((ROOT / 'data/assets').resolve()) or not path.is_file():
                    findings.append({'code': 'missing_asset', 'path': asset['path']})
                    continue
                if asset['path'] not in assets:
                    try:
                        with fitz.open(path) as image:
                            size = [image[0].rect.width, image[0].rect.height]
                        assets[asset['path']] = {'sha256': file_digest(path), 'size': size}
                    except Exception as error:
                        findings.append({'code': 'invalid_asset', 'path': asset['path'], 'reason': str(error)})
            used_assets = {asset['path'] for asset in iter_assets(c)}
            pixel_checked = 0
            for figure in (c.get('layout') or {}).get('extraction', {}).get('figures', []):
                if figure['asset'] not in used_assets:
                    findings.append({'code': 'omitted_source_figure', 'asset': figure['asset'], 'page': figure['page']})
                    continue
                path = ROOT / 'data' / figure['asset'].lstrip('/')
                if path.is_file():
                    expected = doc[figure['page'] - 1].get_pixmap(
                        matrix=fitz.Matrix(2.5, 2.5), clip=fitz.Rect(figure['bbox'])
                    )
                    actual = fitz.Pixmap(path)
                    same_size = (expected.width, expected.height, expected.n) == (actual.width, actual.height, actual.n)
                    expected_pixels, actual_pixels = expected.samples, actual.samples
                    if (
                        not same_size
                        or hashlib.sha256(expected_pixels).digest() != hashlib.sha256(actual_pixels).digest()
                    ):
                        delta = (
                            max((abs(a - b) for a, b in zip(expected_pixels, actual_pixels)), default=0)
                            if same_size
                            else None
                        )
                        rounding = same_size and delta <= 1
                        findings.append(
                            {
                                'code': 'source_figure_rounding_difference'
                                if rounding
                                else 'source_figure_pixel_mismatch',
                                'asset': figure['asset'],
                                'page': figure['page'],
                                'max_channel_delta': delta,
                                'severity': 'info' if rounding else 'error',
                            }
                        )
                    pixel_checked += 1
            pending = blocking_issues(c)
            result = {
                'id': item['id'],
                'question_id': item['question_id'],
                'canonical_id': item['canonical_id'],
                'number': n,
                'area': c['area'],
                'content_sha256': digest(c),
                'page': c['page'],
                'official_answer': original.get(n),
                'annulled': c['annulled'],
                'key_matches': not any(f['code'] == 'answer_key_mismatch' for f in findings),
                'findings': findings,
                'preparation_issues': pending,
                'text_token_coverage': recall,
                'regions': regions,
            }
            result['source_figures_pixel_checked'] = pixel_checked
            if render_sources:
                paths = []
                for ri, region in enumerate(regions):
                    target = output / 'originals' / exam['id'] / f'{n}-{ri}.png'
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        doc[region['page'] - 1].get_pixmap(
                            matrix=fitz.Matrix(1.7, 1.7), clip=fitz.Rect(region['bbox'])
                        ).save(target)
                    paths.append(str(target.relative_to(output)))
                result['source_images'] = paths
            questions.append(result)
    return {
        'id': exam['id'],
        'title': exam['title'],
        'questions': len(questions),
        'source_sha256': source['sha256'],
        'answer_key_sha256': source['answer_key_sha256'],
        'language': language,
        'source_path': str(pdf.relative_to(ROOT)),
        'answer_key_path': str(key.relative_to(ROOT)),
        'answer_key_extractors_agree': original == independent,
        'errors': errors,
        'assets': assets,
        'items': questions,
    }


def export_run(exam):
    from backend.app.services.content import public_question
    from backend.app.services.scoring import score

    metadata = {
        key: exam[key]
        for key in (
            'id',
            'title',
            'year',
            'application',
            'booklet',
            'day',
            'kind',
            'expected_items',
            'duration_minutes',
            'status',
        )
    }
    automatic = exam['source'].get('automatic_archive', {})
    metadata.update(
        item_count=len(exam['items']),
        source={k: exam['source'][k] for k in ('url', 'sha256', 'publisher', 'notes')},
        content_quality={
            'origin': 'automatic' if automatic else 'reviewed',
            'review_status': automatic.get('review_status', 'reviewed'),
            'blocking_issues': automatic.get('blocking_issues', 0),
        },
    )
    items = [
        dict(
            id=q['id'],
            question_id=q['question_id'],
            canonical_id=q['canonical_id'],
            version=q['version'],
            content=q['content'],
        )
        for q in exam['items']
    ]
    answers = {q['id']: q['content']['correct_answer'] for q in items}
    return {
        'id': 'audit-' + exam['id'],
        'exam': metadata,
        'items': [public_question(item, True) for item in items],
        'answers': answers,
        'started_at': 1700000000,
        'finished_at': 1700000100,
        'result': score(items, answers),
    }


def score_all(exams, reports, output, database):
    """Exercita as mesmas rotas em banco descartável, sem contas/tentativas reais."""
    import secrets
    from sqlalchemy import create_engine, select, func
    from sqlalchemy.orm import Session
    from backend.app.core.db import Base
    from backend.app import models as m, schemas as s
    from backend.app.routers.runs import start_run, finish_run

    signature = digest(
        {
            'exams': [(e['id'], [(q['id'], digest(q['content'])) for q in e['items']]) for e in exams],
            'official': {key: [(q['number'], q['official_answer']) for q in r['items']] for key, r in reports.items()},
            'code': {
                str(p.relative_to(ROOT)): file_digest(p)
                for p in [
                    ROOT / 'backend/app/routers/runs.py',
                    ROOT / 'backend/app/services/attempts.py',
                    ROOT / 'backend/app/services/scoring.py',
                    ROOT / 'backend/app/models/runs.py',
                ]
            },
        }
    )
    cached = output / 'scoring-report.json'
    if cached.exists():
        report = read_json(cached)
        if report.get('input_sha256') == signature:
            return report
    path = output / 'scoring-test.db'
    if path.exists():
        path = output / f'scoring-test-{time.time_ns()}.db'
    engine = create_engine('sqlite:///' + str(path))
    Base.metadata.create_all(engine)
    results = []
    with Session(engine, expire_on_commit=False) as db:
        from backend.app.services.identity import signatures

        identities = {}
        for exam in exams:
            for q in exam['items']:
                if q['canonical_id'] and q['canonical_id'] not in identities:
                    signature, answer = signatures(q['content'])
                    identities[q['canonical_id']] = m.CanonicalQuestion(
                        id=q['canonical_id'], signature=signature, answer_signature=answer
                    )
        # Identidades originais podem ter assinaturas de versões anteriores.
        with sqlite3.connect(f'file:{Path(database).resolve()}?mode=ro', uri=True) as original:
            existing = {
                row[0]: row for row in original.execute('SELECT id,signature,answer_signature FROM canonical_questions')
            }
        for key in identities:
            row = existing[key]
            db.add(m.CanonicalQuestion(id=row[0], signature=row[1], answer_signature=row[2]))
        db.flush()
        inserted = set()
        for exam in exams:
            for q in exam['items']:
                if q['id'] not in inserted:
                    db.add(
                        m.QuestionVersion(
                            **{
                                k: q[k]
                                for k in (
                                    'id',
                                    'question_id',
                                    'canonical_id',
                                    'version',
                                    'content',
                                    'status',
                                    'created_at',
                                )
                            }
                        )
                    )
                    inserted.add(q['id'])
            db.add(m.Exam(**{k: v for k, v in exam.items() if k != 'items'}, items=[q['id'] for q in exam['items']]))
        user = m.User(
            name='Ensaio integral descartável',
            email='archive-audit@invalid.local',
            password_hash=secrets.token_hex(32),
            role='student',
        )
        db.add(user)
        db.commit()
        for exam in exams:
            report = reports[exam['id']]
            official = {item['number']: item['official_answer'] for item in report['items']}
            eligible = sum(answer is not None for answer in official.values())
            if report['errors'] or not all(item['key_matches'] for item in report['items']):
                results.append({'id': exam['id'], 'status': 'blocked_by_key_audit'})
                continue
            for mode in ('correct', 'blank', 'wrong'):
                run = start_run(
                    s.StartRun(exam_id=exam['id'], idempotency_key=f'audit-{mode}-{digest(exam["id"])[:40]}'), user, db
                )
                saved = db.get(m.ExamRun, run['id'])
                saved.answers = (
                    {}
                    if mode == 'blank'
                    else {
                        item['id']: (
                            official[item['content']['number']]
                            if mode == 'correct' or item['content']['annulled']
                            else 'ABCDE'[('ABCDE'.index(official[item['content']['number']]) + 1) % 5]
                        )
                        for item in saved.items
                    }
                )
                db.commit()
                expected = {
                    'correct': eligible if mode == 'correct' else 0,
                    'total': eligible,
                    'answered': 0 if mode == 'blank' else eligible,
                    'unanswered': eligible if mode == 'blank' else 0,
                    'incorrect': eligible if mode == 'wrong' else 0,
                    'annulled': len(official) - eligible,
                    'percentage': 100.0 if mode == 'correct' and eligible else 0.0 if eligible else None,
                }
                finished = finish_run(saved.id, user, db)
                db.commit()
                before = db.scalar(
                    select(func.count()).select_from(m.LearningEvent).where(m.LearningEvent.run_id == saved.id)
                )
                repeated = finish_run(saved.id, user, db)
                db.commit()
                after = db.scalar(
                    select(func.count()).select_from(m.LearningEvent).where(m.LearningEvent.run_id == saved.id)
                )
                passed = finished['result'] == expected and repeated == finished and before == after == len(official)
                results.append(
                    {
                        'id': exam['id'],
                        'mode': mode,
                        'passed': passed,
                        'result': finished['result'],
                        'expected': expected,
                        'events': after,
                        'idempotent': repeated == finished and before == after,
                    }
                )
            print(f'Correção conferida: {exam["id"]}', flush=True)
    engine.dispose()
    path.chmod(0o600)
    return {
        'exams': len(exams),
        'scenarios': len(results),
        'failed': [r for r in results if not r.get('passed')],
        'results': results,
        'input_sha256': signature,
        'database_file': path.name,
    }


def reusable_report(exam, path, files, output, render_sources):
    """Resume only when versions, official sources, assets and crops agree."""
    if not path.is_file():
        return None
    from backend.app.schemas import QuestionContent

    report = read_json(path)
    if (
        report.get('source_sha256') != exam['source']['sha256']
        or report.get('answer_key_sha256') != exam['source']['answer_key_sha256']
    ):
        return None
    expected = [(q['id'], digest(QuestionContent.model_validate(q['content']).model_dump())) for q in exam['items']]
    actual = [(q['id'], q['content_sha256']) for q in report['items']]
    if expected != actual or any('source_figures_pixel_checked' not in q for q in report['items']):
        return None
    if any(
        f['code'] == 'source_figure_pixel_mismatch' and 'max_channel_delta' not in f
        for q in report['items']
        for f in q['findings']
    ):
        return None
    for key in ('source_path', 'answer_key_path'):
        source_path(report[key], report['source_sha256' if key == 'source_path' else 'answer_key_sha256'])
    for relative, asset in report['assets'].items():
        path = ROOT / 'data' / relative.lstrip('/')
        if not path.is_file() or file_digest(path) != asset['sha256']:
            return None
    if render_sources and any(
        not q.get('source_images') or any(not (output / p).is_file() for p in q['source_images'])
        for q in report['items']
    ):
        return None
    return report


def run(database, output, render_sources=False, scoring=False, resume=False):
    output.mkdir(parents=True, exist_ok=True)
    files = read_json(ROOT / 'data/sources/catalogo/acervo.json')['files']
    exams = installed_exams(database)
    reports = {}
    index = []
    for i, exam in enumerate(exams, 1):
        path = output / 'sources' / f'{exam["id"]}.json'
        report = reusable_report(exam, path, files, output, render_sources) if resume else None
        if report is None:
            report = audit_exam(exam, files, output, render_sources)
        reports[exam['id']] = report
        write_json(output / 'sources' / f'{exam["id"]}.json', report)
        write_json(output / 'runs' / f'{exam["id"]}.json', export_run(exam))
        index.append(
            {
                'id': exam['id'],
                'questions': len(exam['items']),
                'run_file': f'runs/{exam["id"]}.json',
                'source_report': f'sources/{exam["id"]}.json',
                'content_sha256': digest([q['content'] for q in exam['items']]),
            }
        )
        if i % 10 == 0:
            print(f'Fontes e gabaritos: {i}/{len(exams)} provas.', flush=True)
    summary = {
        'schema_version': '1.0',
        'exams': len(exams),
        'questions': sum(r['questions'] for r in reports.values()),
        'answer_key_mismatches': sum(not q['key_matches'] for r in reports.values() for q in r['items']),
        'parser_disagreements': sum(not r['answer_key_extractors_agree'] for r in reports.values()),
        'annulled': sum(q['annulled'] for r in reports.values() for q in r['items']),
        'source_figures_pixel_checked': sum(
            q['source_figures_pixel_checked'] for r in reports.values() for q in r['items']
        ),
        'findings': dict(Counter(f['code'] for r in reports.values() for q in r['items'] for f in q['findings'])),
        'preparation_issues': dict(
            Counter(issue['code'] for r in reports.values() for q in r['items'] for issue in q['preparation_issues'])
        ),
        'index': index,
        'manual_semantic_review_complete': False,
        'auditor_sha256': file_digest(Path(__file__)),
        'resumed_with_version_source_asset_validation': resume,
    }
    write_json(output / 'manifest.json', summary)
    if scoring:
        write_json(output / 'scoring-report.json', score_all(exams, reports, output, database))
    print(json.dumps({k: v for k, v in summary.items() if k != 'index'}, ensure_ascii=False), flush=True)
    return summary
