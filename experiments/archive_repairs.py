"""Source-backed correction candidates; does not mutate the installed DB."""

from collections import Counter
import copy
from pathlib import Path
import re

import pymupdf as fitz

from .archive_audit import installed_exams
from .common import ROOT, deadline, digest, read_json, source_path, write_json


def visible(content):
    return {k: content[k] for k in ('statement', 'blocks', 'images', 'alternatives', 'correct_answer', 'annulled')}


def canonical_review(plan, database):
    """A richer crop can reveal pixel differences hidden by the old extraction.

    Keep existing identity/history links, flag adjudication and do not replace
    canonical signatures when the active occurrences no longer match exactly.
    """
    from collections import defaultdict
    from backend.app.services.identity import signatures

    changes = {row['previous_version']: row for row in plan['changes']}
    exams = installed_exams(database)
    affected = {q['canonical_id'] for exam in exams for q in exam['items'] if q['id'] in changes}
    groups = defaultdict(list)
    for exam in exams:
        for q in exam['items']:
            if q['canonical_id'] in affected:
                content = changes.get(q['id'], {}).get('content', q['content'])
                groups[q['canonical_id']].append(
                    {
                        'version': q['id'],
                        'signature': signatures(content),
                        'source_sha256': exam['source']['sha256'],
                        'question_id': q['question_id'],
                    }
                )
    plan['canonical_review_required'] = [
        {
            'canonical_id': key,
            'occurrences': rows,
            'review_status': 'proposed',
            'reason': 'Extração ampliada revela assinaturas diferentes em ocorrências antes vinculadas. Preservar vínculos históricos; conferir equivalência com as fontes antes de adjudicar.',
        }
        for key, rows in groups.items()
        if len({tuple(row['signature']) for row in rows}) > 1
    ]
    return plan


def repair_text_options(content, positioned):
    """Fast exact-text case: five printed markers, no graphics in the options.

    Only removes the proven first option from the end of the old stem. More
    complex cases go through the complete geometric extractor instead.
    """
    if any(a.get('image') for a in content['alternatives']):
        return None
    markers = [(i, line) for i, line in enumerate(positioned) if line.get('option')]
    if ''.join(line['option'] for _, line in markers) != 'ABCDE':
        return None
    first = markers[0][1]
    for figure in content['layout'].get('extraction', {}).get('figures', []):
        if figure['page'] > first['_page'] or figure['page'] == first['_page'] and figure['bbox'][3] > first['bbox'][1]:
            return None
    choices = []
    for j, (index, line) in enumerate(markers):
        chunk = positioned[index : markers[j + 1][0] if j < 4 else len(positioned)]
        if any(l.get('uncertain') for l in chunk):
            return None
        text = ' '.join(l['text'] for l in chunk)
        text = re.sub(r'^[ABCDE](?:[.)]\s*|\s+)', '', text).strip()
        if not text:
            return None
        choices.append({'letter': line['option'], 'text': text, 'image': None})
    a_text = re.sub(r'^[ABCDE](?:[.)]\s*|\s+)', '', first['text']).strip()
    if not a_text:
        return None
    end = re.compile(r'\s*' + r'\s+'.join(re.escape(word) for word in a_text.split()) + r'\s*$')
    fixed = copy.deepcopy(content)
    if not fixed['blocks'] or fixed['blocks'][-1]['type'] != 'paragraph' or not end.search(fixed['blocks'][-1]['text']):
        return None
    fixed['blocks'][-1]['text'] = end.sub('', fixed['blocks'][-1]['text']).strip()
    if not fixed['blocks'][-1]['text']:
        fixed['blocks'].pop()
    fixed['alternatives'] = choices
    fixed['statement'] = (
        '\n\n'.join(b['text'] for b in fixed['blocks'] if b['type'] == 'paragraph') or fixed['statement']
    )
    fixed['layout']['extraction']['issues'] = [
        i for i in fixed['layout']['extraction'].get('issues', []) if i['code'] != 'alternative_layout'
    ]
    return fixed


def propose_exam(job):
    from backend.app.preparation import prepare_content, blocking_issues
    from backend.app.schemas import QuestionContent
    from ingestion.exam_pdf import (
        align_option_lines,
        discover_regions,
        extract_exam,
        lines,
        mark_bare_options,
        shared_numbers,
        section_break,
        auto_columns,
        textual_table,
    )

    exam, report, output = job
    record = next(
        r
        for r in read_json(ROOT / 'data/sources/catalogo/acervo.json')['files']
        if r.get('sha256') == exam['source']['sha256']
    )
    pdf = source_path('data/sources/' + record['path'], exam['source']['sha256'])
    changes, proposals = [], []
    if exam['source'].get('automatic_archive', {}).get('review_status') != 'pending':
        return {'exam_id': exam['id'], 'changes': [], 'proposals': [], 'reviewed_content_preserved': True}
    old_regions = {q['content']['number']: q['content']['layout']['blocks'] for q in exam['items']}
    all_regions = [r for regions in old_regions.values() for r in regions]
    with fitz.open(pdf) as doc:
        shared = any(
            shared_numbers(line) or section_break(line) for page in doc for line in page.get_text().splitlines()
        )
        partial_pages = {
            r['page'] for r in all_regions if r['bbox'][2] - r['bbox'][0] < doc[r['page'] - 1].rect.width * 0.6
        }
        column_change = any(
            len(auto_columns(lines(doc[pn - 1], doc[pn - 1].rect), doc[pn - 1].rect.width)) == 1 for pn in partial_pages
        )
        discovered = None
        if shared or column_change:
            from ingestion.archive_exams import scan

            margins = scan(pdf)
            # Automatic manifests start after the cover. A Spanish subset may
            # start on page 3 while English 94/95 continue there; keep page 2
            # so the language section is known before those reused numbers.
            config = {
                'layout': {
                    'pages': [min(2, min(r['page'] for r in all_regions)), max(r['page'] for r in all_regions)],
                    'top': margins['top'],
                    'bottom': max(r['bbox'][3] for r in all_regions),
                    'columns': 'auto',
                }
            }
            if report['language']:
                config['language'] = report['language']
            discovered = discover_regions(doc, config)
        for old, audited in zip(exam['items'], report['items']):
            c = QuestionContent.model_validate(old['content']).model_dump()
            number = c['number']
            reasons = []
            errors = blocking_issues(c)
            target = copy.deepcopy(c)
            if not audited['key_matches']:
                target.update(correct_answer=audited['official_answer'], annulled=audited['official_answer'] is None)
                reasons.append(
                    'Gabarito corrigido pela coluna da cor declarada, com dois extratores independentes concordantes.'
                )
            corrected_regions = discovered.get(number) if discovered else None
            region_change = corrected_regions is not None and corrected_regions != old_regions[number]
            joined = 0
            mismatched_lines = 0
            positioned = []
            for region in target['layout']['blocks']:
                raw = lines(doc[region['page'] - 1], fitz.Rect(region['bbox']))
                mark_bare_options(raw)
                before = len(raw)
                align_option_lines(raw)
                joined += before - len(raw)
                for line in sorted(raw, key=lambda l: (round(l['bbox'][1], 1), l['bbox'][0])):
                    positioned.append({**line, '_page': region['page']})
                for line in raw:
                    letter = line.get('option')
                    if letter and '\t' in line['text']:
                        from .archive_audit import plain

                        words = plain(line['text'].split('\t', 1)[1])[:4]
                        installed = plain(c['alternatives']['ABCDE'.index(letter)]['text'])
                        if words and installed[: len(words)] != words:
                            mismatched_lines += 1
            codes = {issue['code'] for issue in errors}
            baseline_shift = joined and mismatched_lines >= 2
            sparse = any(b['type'] == 'table' and not textual_table([b['headers'], *b['rows']]) for b in c['blocks'])
            reextract = (
                region_change or baseline_shift or sparse or bool(codes & {'alternative_layout', 'missing_alternative'})
            )
            if reextract:
                safe_target = copy.deepcopy(target)
                if region_change:
                    target['layout']['blocks'] = corrected_regions
                candidate = repair_text_options(target, positioned) if baseline_shift and not region_change else None
                if candidate is None:
                    source = {
                        'id': exam['id'],
                        'source': exam['source'],
                        'questions': [{'question_id': old['question_id'], 'content': target}],
                    }
                    try:
                        with deadline(15):
                            candidate = extract_exam(source, pdf, ROOT / 'data/assets', document=doc)['questions'][0][
                                'content'
                            ]
                    except (TimeoutError, ValueError) as error:
                        proposals.append(
                            {
                                'question_id': old['question_id'],
                                'number': number,
                                'status': 'unresolved',
                                'reason': str(error),
                            }
                        )
                        candidate = target = safe_target
                try:
                    with deadline(10):
                        candidate = prepare_content(candidate)
                except (TimeoutError, ValueError) as error:
                    proposals.append(
                        {
                            'question_id': old['question_id'],
                            'number': number,
                            'status': 'unresolved',
                            'reason': str(error),
                        }
                    )
                    candidate = target = safe_target
                remaining = blocking_issues(candidate)
                new_codes = {i['code'] for i in remaining}
                # Source coordinates must yield all five complete alternatives.
                # Ambiguous segmentation stays a proposal and is never applied.
                if (
                    not new_codes
                    & {
                        'alternative_layout',
                        'missing_alternative',
                        'garbled_text',
                        'whole_region_image',
                        'control_character',
                        'invalid_latex',
                    }
                    and not new_codes - codes
                ):
                    target = candidate
                    if region_change:
                        reasons.append(
                            'Limites recompostos na fonte, separando seções alheias e preservando os contextos explicitamente compartilhados.'
                        )
                    if baseline_shift:
                        reasons.append(
                            'Letra A–E e texto alinhados pela mesma linha impressa, eliminando deslocamento de alternativas.'
                        )
                    if codes & {'alternative_layout', 'missing_alternative'}:
                        reasons.append('Cinco alternativas recuperadas com marcadores inequívocos e figuras da fonte.')
                    if sparse:
                        reasons.append(
                            'Grade gráfica ou tabela esparsa preservada como figura da fonte, sem inferir células vazias.'
                        )
                else:
                    proposals.append(
                        {
                            'question_id': old['question_id'],
                            'number': number,
                            'status': 'unresolved',
                            'before': sorted(codes),
                            'after': sorted(new_codes),
                            'source_sha256': exam['source']['sha256'],
                            'regions': candidate['layout']['blocks'],
                        }
                    )
            if visible(target) != visible(c) and reasons:
                with deadline(10):
                    target = prepare_content(target)
                changes.append(
                    {
                        'exam_id': exam['id'],
                        'question_id': old['question_id'],
                        'previous_version': old['id'],
                        'previous_sha256': digest(c),
                        'source_sha256': exam['source']['sha256'],
                        'answer_key_sha256': exam['source']['answer_key_sha256'],
                        'content': target,
                        'reason': ' '.join(reasons),
                        'evidence': {
                            'page': c['page'],
                            'official_answer': audited['official_answer'],
                            'key_extractors_agree': report['answer_key_extractors_agree'],
                            'aligned_option_lines': joined,
                            'source_regions_corrected': region_change,
                            'shared_context': bool(
                                region_change and any(r.get('shared_for') for r in target['layout']['blocks'])
                            ),
                            'remaining_technical_issues': len(blocking_issues(target)),
                        },
                    }
                )
    result = {'exam_id': exam['id'], 'changes': changes, 'proposals': proposals}
    write_json(Path(output) / 'repair-proposals' / f'{exam["id"]}.json', result)
    return result


def run(database, audit, output, workers=4, retry_failed=False):
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from backend.app.schemas import QuestionContent

    output.mkdir(parents=True, exist_ok=True)
    results = []
    failures = []
    jobs = []
    for exam in installed_exams(database):
        reference = read_json(audit / 'sources' / f'{exam["id"]}.json')
        if [(q['id'], digest(QuestionContent.model_validate(q['content']).model_dump())) for q in exam['items']] != [
            (q['id'], q['content_sha256']) for q in reference['items']
        ]:
            raise ValueError('O banco mudou desde a auditoria; gere novas evidências antes de propor correções.')
        cached = output / 'repair-proposals' / f'{exam["id"]}.json'
        if retry_failed and cached.is_file():
            result = read_json(cached)
            expected = {q['id']: q for q in reference['items']}
            if result['exam_id'] != exam['id'] or any(
                row['previous_version'] not in expected
                or row['previous_sha256'] != expected[row['previous_version']]['content_sha256']
                for row in result['changes']
            ):
                raise ValueError('Candidato retomado diverge da versão auditada.')
            results.append(result)
        else:
            jobs.append((exam, reference, str(output)))
    total = len(results) + len(jobs)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        pending = {pool.submit(propose_exam, job): job[0]['id'] for job in jobs}
        for future in as_completed(pending):
            try:
                result = future.result()
            except Exception as error:
                failures.append({'exam_id': pending[future], 'reason': str(error)})
                print(f'Falha: {pending[future]}: {error}', flush=True)
                continue
            results.append(result)
            print(
                f'{len(results)}/{total}: {result["exam_id"]}, {len(result["changes"])} correções, {len(result["proposals"])} pendências.',
                flush=True,
            )
    changes = [c for result in sorted(results, key=lambda r: r['exam_id']) for c in result['changes']]
    plan = {
        'schema_version': '1.0',
        'audit_sha256': digest(read_json(audit / 'manifest.json')),
        'changes': changes,
        'failures': failures,
    }
    canonical_review(plan, database)
    write_json(output / 'corrections-plan.json', plan)
    write_json(
        output / 'corrections-summary.json',
        {
            'changes': len(changes),
            'exams': len({c['exam_id'] for c in changes}),
            'reasons': dict(Counter(c['reason'] for c in changes)),
            'unresolved_candidates': sum(len(r['proposals']) for r in results),
            'applied': False,
            'complete': not failures,
            'failures': failures,
            'independent_pedagogical_review': False,
        },
    )
    return plan
