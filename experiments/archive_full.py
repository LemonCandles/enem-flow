"""Run the selected experiments on every published item and audit raw coverage."""

from collections import Counter
from pathlib import Path
import time

from .common import ROOT, deadline, digest, file_digest, read_json, source_path, write_json


def inventory(output):
    """The historical extraction is not a second published question catalog."""
    from scripts.exam_pdf import garbled

    catalog = read_json(ROOT / 'data/sources/catalogo/acervo.json')
    files = catalog['files']
    findings = []
    verified = 0
    unavailable = []
    for record in files:
        if record['status'] != 'downloaded':
            unavailable.append({'path': record.get('path'), 'url': record['url'], 'status': record['status']})
            continue
        try:
            source_path('data/sources/' + record['path'], record['sha256'])
            verified += 1
        except (OSError, ValueError) as error:
            findings.append({'code': 'source_integrity', 'path': record['path'], 'reason': str(error)})
    base = ROOT / 'data/bank'
    coverage = read_json(base / 'coverage.json')
    for raw in coverage['raw_files']:
        try:
            source_path(raw['path'], raw['sha256'])
        except (OSError, ValueError) as error:
            findings.append({'code': 'raw_integrity', 'path': raw['path'], 'reason': str(error)})
    occurrences = read_json(base / 'occurrences.json')
    canonical = read_json(base / 'canonical.json')
    canonical_ids = {row['id'] for row in canonical}
    ids = {row['occurrence_id'] for row in occurrences}
    indexed = {row['occurrence_id']: row for row in occurrences}
    if len(ids) != len(occurrences):
        findings.append({'code': 'duplicate_occurrence_id'})
    for identity in canonical:
        if any(key not in ids for key in identity['occurrences']):
            findings.append({'code': 'dangling_identity', 'id': identity['id']})
    by_source = {row['source_id']: row for row in read_json(base / 'sources.json')}
    paths = sorted(
        {f'data/derived/archive/{source["year"]}/{source["source_id"]}.json' for source in by_source.values()}
    )
    counts = Counter()
    triage = []
    for relative in paths:
        extracted = read_json(ROOT / relative)
        source = by_source[extracted['source_id']]
        for item in extracted['questions']:
            counts['questions'] += 1
            reasons = []
            occurrence = indexed.get(item['occurrence_id'])
            if (
                occurrence is None
                or occurrence['canonical_id'] not in canonical_ids
                or item['canonical_id'] not in {occurrence['canonical_id'], occurrence.get('extraction_identity_id')}
            ):
                reasons.append('missing_identity')
            if not item.get('text', '').strip():
                reasons.append('empty_text')
            if '\ufffd' in item.get('text', '') or any(garbled(line) for line in item.get('text', '').splitlines()):
                reasons.append('encoding_requires_recovery')
            if not item.get('regions') and source['source_path'].endswith('.pdf'):
                reasons.append('missing_regions')
            if source.get('pages') and any(not 1 <= r['page'] <= source['pages'] for r in item.get('regions', [])):
                reasons.append('invalid_page')
            if reasons:
                counts.update(reasons)
                triage.append(
                    {
                        'occurrence_id': item['occurrence_id'],
                        'source_id': source['source_id'],
                        'page': item['page'],
                        'reasons': reasons,
                        'review_status': 'proposed',
                    }
                )
    report = {
        'source_records': len(files),
        'verified_downloaded_sources': verified,
        'unavailable_sources': unavailable,
        'raw_files': len(coverage['raw_files']),
        'occurrences': len(occurrences),
        'canonical_questions': len(canonical),
        'extracted_source_files': len(paths),
        'counts': dict(counts),
        'integrity_findings': findings,
        'historical_content_published': False,
        'historical_answer_keys_semantically_validated': False,
        'interpretation': 'Integridade e triagem de todo o banco histórico. Sem publicação ou aprovação; OCR/codificação e gabaritos visuais exigem conferência específica.',
    }
    write_json(output / 'historical-inventory.json', report)
    write_json(output / 'historical-recovery-queue.json', triage)
    return report


def experiment_exam(job):
    import pymupdf as fitz
    from backend.app.schemas import QuestionContent
    from backend.app.preparation import blocking_issues
    from .classification import proposal, visible_text
    from .layout import assemble, extract_candidates
    from .contracts import LayoutProposal

    exam, model, output, files, code_hash, layout_context = job
    fingerprint = digest([code_hash, model, layout_context, [(q['id'], q['content']) for q in exam['items']]])
    target = Path(output) / 'all-proposals' / f'{exam["id"]}.json'
    if target.exists():
        previous = read_json(target)
        if previous['fingerprint'] == fingerprint:
            return previous['summary']
    record = next(r for r in files if r.get('sha256') == exam['source']['sha256'])
    pdf = source_path('data/sources/' + record['path'], exam['source']['sha256'])
    document = fitz.open(pdf)
    rows = []
    total_blocks = 0
    themes = 0
    fallbacks = 0
    for q in exam['items']:
        c = QuestionContent.model_validate(q['content']).model_dump()
        regions = [{key: r[key] for key in ('page', 'bbox')} for r in c['layout']['blocks']]
        start = time.perf_counter()
        method = layout_context['method']
        failure = None
        try:
            with deadline(15):
                candidates, tables = extract_candidates(pdf, regions, method != 'coordinates', document=document)
        except (TimeoutError, ValueError) as error:
            method = 'coordinates'
            failure = str(error)
            fallbacks += 1
            candidates, tables = extract_candidates(pdf, regions, False, document=document)
        layout = LayoutProposal.model_validate(
            {
                **assemble(candidates, method, layout_context['tree']),
                'id': q['question_id'],
                'source_sha256': exam['source']['sha256'],
                'regions': regions,
                'content_sha256': digest(c),
                'origin': {'method': method, 'experiment': 'data-ai-v1'},
                'table_structures': tables,
            }
        ).model_dump()
        classification = {
            'status': 'not_applicable',
            'reason': 'A referência temática disponível cobre Matemática; não há validação para esta área.',
        }
        if c['area'] == 'Matemática' and not c['annulled']:
            classification = proposal(
                {
                    'question_id': q['question_id'],
                    'canonical_id': q['canonical_id'],
                    'content_sha256': digest(c),
                    'source_sha256': exam['source']['sha256'],
                    'text': visible_text(c),
                    'visual': any(b['type'] == 'image' for b in c['blocks'])
                    or any(a.get('image') for a in c['alternatives']),
                },
                model,
            )
            themes += 1
        elif c['annulled']:
            classification = {
                'status': 'not_applicable',
                'reason': 'Questão anulada; não integra a avaliação temática de itens válidos.',
            }
        total_blocks += len(layout['blocks'])
        rows.append(
            {
                'question_id': q['question_id'],
                'version_id': q['id'],
                'number': c['number'],
                'content_sha256': digest(c),
                'layout': layout,
                'classification': classification,
                'preparation_issues': blocking_issues(c),
                'latency_ms': (time.perf_counter() - start) * 1000,
                'review_status': 'proposed',
                'geometry_failure': failure,
            }
        )
    document.close()
    summary = {
        'exam_id': exam['id'],
        'questions': len(rows),
        'layout_blocks': total_blocks,
        'theme_proposals': themes,
        'not_applicable': len(rows) - themes,
        'geometry_fallbacks': fallbacks,
        'failed': False,
    }
    write_json(
        target,
        {'fingerprint': fingerprint, 'source_sha256': exam['source']['sha256'], 'items': rows, 'summary': summary},
    )
    return summary


def run(database, output, model_path, workers=2, retry_failed=False):
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from backend.app.schemas import QuestionContent
    from .archive_audit import installed_exams

    model = read_json(model_path)
    files = read_json(ROOT / 'data/sources/catalogo/acervo.json')['files']
    layout_report = model_path.with_name('layout-report.json')
    layout_context = {
        'method': read_json(layout_report)['selection']['method'],
        'tree': read_json(model_path.with_name('layout-model.json'))['tree'],
    }
    code_hash = digest(
        {
            str(p.relative_to(ROOT)): file_digest(p)
            for p in [
                ROOT / 'experiments/archive_full.py',
                ROOT / 'experiments/layout.py',
                ROOT / 'experiments/classification.py',
                ROOT / 'experiments/common.py',
                ROOT / 'scripts/exam_pdf.py',
            ]
        }
    )
    exams = installed_exams(database)
    results = []
    jobs = []
    reused = {}
    prior_path = output / 'all-experiments-report.json'
    prior = read_json(prior_path) if retry_failed and prior_path.exists() else None
    compatible = (
        prior
        and prior.get('layout_evaluation_sha256') == file_digest(layout_report)
        and prior.get('layout_method') == layout_context['method']
    )
    successful = {r['exam_id'] for r in prior['exams_summary'] if not r['failed']} if compatible else set()
    for exam in exams:
        path = output / 'all-proposals' / f'{exam["id"]}.json'
        cached = read_json(path) if exam['id'] in successful and path.exists() else None
        expected = [(q['id'], digest(QuestionContent.model_validate(q['content']).model_dump())) for q in exam['items']]
        if (
            cached
            and cached['source_sha256'] == exam['source']['sha256']
            and [(q['version_id'], q['content_sha256']) for q in cached['items']] == expected
            and all(
                q['classification'].get('origin', {}).get('model_sha256', digest(model)) == digest(model)
                for q in cached['items']
            )
        ):
            record = next(r for r in files if r.get('sha256') == exam['source']['sha256'])
            source_path('data/sources/' + record['path'], exam['source']['sha256'])
            results.append(cached['summary'])
            reused[exam['id']] = file_digest(path)
        else:
            jobs.append(exam)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        pending = {
            pool.submit(experiment_exam, (e, model, str(output), files, code_hash, layout_context)): e['id']
            for e in jobs
        }
        for future in as_completed(pending):
            try:
                result = future.result()
            except Exception as error:
                result = {
                    'exam_id': pending[future],
                    'questions': 0,
                    'layout_blocks': 0,
                    'theme_proposals': 0,
                    'not_applicable': 0,
                    'geometry_fallbacks': 0,
                    'failed': True,
                    'reason': str(error),
                }
            results.append(result)
            print(f'Etapa 3 integral: {len(results)}/{len(exams)}, {result["exam_id"]}', flush=True)
    report = {
        'exams': len(results),
        'questions': sum(r['questions'] for r in results),
        'complete': not any(r['failed'] for r in results),
        'failures': [r for r in results if r['failed']],
        'layout_blocks': sum(r['layout_blocks'] for r in results),
        'theme_proposals': sum(r['theme_proposals'] for r in results),
        'theme_not_applicable': sum(r['not_applicable'] for r in results),
        'model_sha256': digest(model),
        'code_sha256': code_hash,
        'geometry_fallbacks': sum(r['geometry_fallbacks'] for r in results),
        'resumed_artifacts_sha256': reused,
        'prior_code_sha256': prior.get('code_sha256') if prior else None,
        'proposed_only': True,
        'independent_review': False,
        'external_cost_usd': 0,
        'human_correction_time': None,
        'layout_method': layout_context['method'],
        'layout_evaluation_sha256': file_digest(layout_report),
        'exams_summary': results,
        'interpretation': 'Aplicação integral dos métodos selecionados. Métricas de acurácia permanecem restritas à referência anotada; propostas do acervo não são novos acertos medidos.',
    }
    write_json(output / 'all-experiments-report.json', report)
    return report
