#!/usr/bin/env python3
"""Gera provas do acervo oficial em JSON nativo e figuras, sem curadoria.

Para cada ano, aplicação, dia e língua a partir de 2009, escolhe um caderno
padrão legível (azul quando possível), monta o manifesto (áreas da época,
margens, páginas e língua), extrai texto e figuras e aplica a preparação
generalizada. Itens já conferidos no catálogo não são gerados de novo.

Saídas locais, fora do Git: `data/derived/exams/<id>.json`, o relatório
`<id>.report.json`, o resumo `resumo.json` e as figuras em `data/assets/<id>/`.
A publicação no site é feita por `python -m backend.app.cli archive`.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pymupdf
from scripts.archive_enem import CATALOG, SOURCE_ROOT

OUTPUT = ROOT / 'data/derived/exams'
ASSETS = ROOT / 'data/assets'
APPLICATIONS = {
    'regular': 'Regular', 'reaplicacao-ppl': 'Reaplicação/PPL', 'digital': 'Digital', 'reaplicacao': 'Reaplicação',
    'segunda-aplicacao': '2ª aplicação', 'terceira-aplicacao': '3ª aplicação', 'belem-ananindeua-marituba': 'Belém, Ananindeua e Marituba',
}
LANGUAGES = {'ingles': 'Inglês', 'espanhol': 'Espanhol'}


def areas(year, day):
    """Até 2016: Humanas e Natureza no 1º dia; Linguagens e Matemática no 2º. Desde 2017, Linguagens e Humanas no 1º."""
    names = (('Linguagens', 'Ciências Humanas'), ('Ciências da Natureza', 'Matemática')) if year >= 2017 else \
            (('Ciências Humanas', 'Ciências da Natureza'), ('Linguagens', 'Matemática'))
    first = 1 if day == 1 else 91
    result = [dict(first=first, last=first + 44, area=names[day - 1][0]), dict(first=first + 45, last=first + 89, area=names[day - 1][1])]
    for area in result:
        if area['area'] == 'Matemática':
            area['discipline'] = 'Matemática'
    return result


def duration(year, day):
    if year >= 2017:
        return 330 if day == 1 else 300
    return 270 if day == 1 else 330


def booklet_label(booklet):
    match = re.match(r'caderno-(\d+)-(.+)', booklet)
    if not match:
        return booklet
    return f'Caderno {match[1]} · ' + ' · '.join(LANGUAGES.get(part, part.capitalize()) for part in match[2].split('-'))


def curated_numbers():
    """(ano, aplicação, dia) -> números já conferidos no catálogo."""
    covered = defaultdict(set)
    manifest = json.loads((ROOT / 'data/catalog/manifest.json').read_text())
    for entry in manifest['exams']:
        exam = json.loads((ROOT / entry['path']).read_text())
        key = (exam['year'], exam['application'].strip().lower(), exam['day'])
        covered[key] |= {q['content']['number'] for q in exam['questions']}
    return covered


def scan(pdf):
    """Margem superior, última página com questões, línguas oferecidas e linhas ilegíveis."""
    from scripts.exam_pdf import HEADING, LANGUAGE, garbled, language_key, lines
    tops, last, offered, total, broken = [], 1, set(), 0, 0
    with pymupdf.open(pdf) as doc:
        height = doc[min(1, len(doc) - 1)].rect.height
        for number, page in enumerate(doc, start=1):
            for line in lines(page, page.rect):
                total += 1
                broken += garbled(line['text'])
                if HEADING.match(line['text']):
                    last = number
                    if number > 1: tops.append(line['bbox'][1])
                elif match := LANGUAGE.match(line['text']):
                    offered.add(language_key(match[3]))
                    if number > 1: tops.append(line['bbox'][1])
    return dict(top=max(30, min(tops) - 3) if tops else 55, last=last, height=height, offered=sorted(offered),
                garbled=broken / max(1, total))


def candidates(files, only_years=None):
    """Um caderno legível por ano, aplicação, modalidade, dia e língua do arquivo."""
    groups = defaultdict(list)
    for record in files:
        if record['role'] == 'prova' and record['variant'] == 'padrao' and record['status'] == 'downloaded' and record['year'] >= 2009 \
                and record['path'].endswith('.pdf') and record.get('day') in (1, 2) and (not only_years or record['year'] in only_years):
            groups[(record['year'], record['application'], record.get('modality'), record['day'], record.get('language'))].append(record)
    keys = {}
    for record in files:
        if record['role'] == 'gabarito' and record['status'] == 'downloaded':
            keys.setdefault((record['year'], record['application'], record.get('modality'), record.get('day'), record['booklet'], record['variant']), record)
    order = lambda r: (0 if 'azul' in r['booklet'] else 1, int(re.search(r'\d+', r['booklet'])[0]) if re.search(r'\d+', r['booklet']) else 99)
    for key, records in sorted(groups.items()):
        yield key, [(r, keys.get((r['year'], r['application'], r.get('modality'), r['day'], r['booklet'], r['variant']))) for r in sorted(records, key=order)]


def exam_id(year, application, day, booklet, language):
    suffix = f'-{language}' if language and not booklet.endswith(language) else ''
    return f'enem-{year}-{application}-dia{day}-{booklet}{suffix}'


KEY_MISMATCH = ('gabarito', 'Informe answers')


def build(job):
    """Tenta cada cor legível até o gabarito corresponder à prova; devolve o resumo."""
    alternatives, language, section, info = job
    tried = []
    for index, (record, key_record) in enumerate(alternatives):
        current = info if index == 0 else scan(SOURCE_ROOT / record['path'])
        if current['garbled'] > 0.02:
            continue
        summary = build_one((record, key_record, language, section, current))
        if summary['status'] == 'gerada' or not any(word in summary.get('reason', '') for word in KEY_MISMATCH):
            if tried:
                summary['tentativas'] = tried
            return summary
        tried.append(dict(caderno=record['booklet'], motivo=summary['reason'][:160]))
    return dict(summary, tentativas=tried)


def build_one(job):
    """Prepara uma prova a partir de um caderno e seu gabarito."""
    from backend.app.preparation import prepare_exam
    from backend.app.schemas import ExamImport
    from scripts.exam_pdf import extract_exam, from_manifest
    record, key_record, language, section, info = job
    year, application, day = record['year'], record['application'], record['day']
    identifier = exam_id(year, application, day, record['booklet'], language)
    target, report_path = OUTPUT / f'{identifier}.json', OUTPUT / f'{identifier}.report.json'
    summary = dict(id=identifier, source=record['path'])
    title = f'ENEM {year} · {day}º dia' + (f' · {APPLICATIONS.get(application, application)}' if application != 'regular' else '') + \
            (f' · {LANGUAGES[language]}' if language and language in LANGUAGES else '')
    manifest = dict(id=identifier, title=title + (' · Ciências da Natureza' if section else ''), year=year,
                    application=APPLICATIONS.get(application, application), booklet=booklet_label(record['booklet']), day=day,
                    kind='section' if section else 'complete', expected_items=0, duration_minutes=duration(year, day),
                    source=dict(url=record['url'], answer_key_url=key_record['url'], publisher='Inep'),
                    layout=dict(pages=[2, info['last']], top=info['top'], bottom=round(info['height']) - 35, columns='auto'),
                    areas=areas(year, day))
    if language and info['offered']:
        manifest['language'] = language
    if section:
        manifest['range'] = section
    try:
        pdf, key = SOURCE_ROOT / record['path'], SOURCE_ROOT / key_record['path']
        from scripts.exam_pdf import answer_key_rows
        with pymupdf.open(key) as document:
            covered = {n for area in manifest['areas'] for n in range(area['first'], area['last'] + 1)}
            answers = answer_key_rows('\n'.join(page.get_text() for page in document), manifest.get('language'), covered)
        if section:
            answers = {n: a for n, a in answers.items() if section[0] <= n <= section[1]}
        manifest['expected_items'] = len(answers)
        data = ExamImport.model_validate(from_manifest(manifest, pdf, key)).model_dump()
        data = extract_exam(data, pdf, ASSETS)
        prepared, report = prepare_exam(data)
        checked = subprocess.run(['node', str(ROOT / 'frontend/scripts/validate-latex.cjs'), '--stdin'], input=prepared.model_dump_json(),
                                 capture_output=True, text=True)
        if checked.returncode:
            raise ValueError('LaTeX não compila: ' + checked.stderr.strip()[:300])
        OUTPUT.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(prepared.model_dump(), ensure_ascii=False, indent=1) + '\n')
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
        issues = Counter(i['code'] for q in report['questions'] for i in q['issues'] if i['severity'] == 'error')
        summary.update(status='gerada', questions=len(prepared.questions), blocking=report['errors'], by_code=dict(issues.most_common()))
    except Exception as error:  # Each exam fails alone; the summary keeps the reason.
        summary.update(status='falhou', reason=str(error)[:400])
    return summary


def jobs(files, only_years=None):
    covered = curated_numbers()
    skipped = []
    for (year, application, modality, day, file_language), options in candidates(files, only_years):
        chosen = None
        with_key = [(record, key_record) for record, key_record in options if key_record]
        for index, (record, key_record) in enumerate(with_key):
            info = scan(SOURCE_ROOT / record['path'])
            if info['garbled'] <= 0.02:
                chosen = (with_key[index:], info)
                break
        label = f'{year} {application} {modality} dia {day}' + (f' {file_language}' if file_language else '')
        if not chosen:
            reason = 'sem gabarito' if not any(k for _, k in options) else 'nenhuma cor com texto legível'
            skipped.append(dict(id=label, status='ignorada', reason=reason))
            continue
        alternatives, info = chosen
        numbers = covered.get((year, APPLICATIONS.get(application, application).lower(), day), set())
        section = None
        if numbers:
            full = set(range(1, 91) if day == 1 else range(91, 181))
            rest = sorted(full - numbers)
            if not rest:
                skipped.append(dict(id=label, status='ignorada', reason='já conferida no catálogo'))
                continue
            section = [rest[0], rest[-1]]
        languages = [file_language] if file_language else (info['offered'] or [None])
        for language in languages:
            yield (alternatives, language, section, info)
    yield from ({'skip': row} for row in skipped)


def from_report(identifier):
    """Resumo de uma prova já gerada, refeito a partir do relatório gravado."""
    report = json.loads((OUTPUT / f'{identifier}.report.json').read_text())
    exam = json.loads((OUTPUT / f'{identifier}.json').read_text())
    issues = Counter(i['code'] for q in report['questions'] for i in q['issues'] if i['severity'] == 'error')
    return dict(id=identifier, source=exam['source']['url'], status='gerada', questions=len(exam['questions']),
                blocking=report['errors'], by_code=dict(issues.most_common()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--years', type=int, nargs='*', help='Limita a estes anos.')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--force', action='store_true', help='Gera de novo provas já existentes.')
    args = parser.parse_args()
    files = json.loads(CATALOG.read_text())['files']
    summary_path = OUTPUT / 'resumo.json'
    previous = {row['id']: row for row in json.loads(summary_path.read_text())} if summary_path.exists() else {}
    pending, results = [], []
    for job in jobs(files, args.years):
        if isinstance(job, dict):
            results.append(job['skip'])
            continue
        alternatives, language = job[0], job[1]
        ids = [exam_id(r['year'], r['application'], r['day'], r['booklet'], language) for r, _ in alternatives]
        existing = next((i for i in ids if (OUTPUT / f'{i}.json').exists()), None)
        if existing and not args.force:
            results.append(previous[existing] if previous.get(existing, {}).get('status') == 'gerada' else from_report(existing))
            continue
        pending.append(job)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(build, job) for job in pending]):
            row = future.result()
            results.append(row)
            print(f"{row['status']:9} {row['id']}" + (f" — {row.get('reason', '')}" if row['status'] != 'gerada' else f" — {row['questions']} questões, {row['blocking']} pendências"), flush=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    # Runs limited by --years keep the other years' rows; failures replaced by a generated booklet disappear.
    merged = {row['id']: row for row in previous.values() if not args.years or not any(row['id'].startswith(f'enem-{y}-') or row['id'].startswith(f'{y} ') for y in args.years)}
    merged.update({row['id']: row for row in results})
    summary_path.write_text(json.dumps(sorted(merged.values(), key=lambda r: r['id']), ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(Counter(r['status'] for r in results), ensure_ascii=False))


if __name__ == '__main__':
    main()
