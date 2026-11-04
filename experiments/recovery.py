"""Recuperações experimentais: alternativas, células, fontes e gabarito visual.

Os resultados são propostas com a evidência geométrica original. Não removem
diagnósticos existentes e não atualizam provas, versões ou gabaritos no banco.
"""

from collections import Counter, defaultdict
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

import pymupdf as fitz

from .common import ROOT, digest, file_digest, read_json, source_path, write_json
from .layout import table_structure


def grid_integrity(structure):
    coverage = Counter(
        (row, col)
        for cell in structure['cells']
        for row in range(cell['row'], cell['row'] + cell['rowspan'])
        for col in range(cell['column'], cell['column'] + cell['colspan'])
    )
    slots = structure['rows'] * structure['columns']
    return bool(slots) and len(coverage) == slots and all(n == 1 for n in coverage.values())


def alternative_regions(doc, regions):
    """Agrupa todas as partes da alternativa, sem descartar a segunda figura."""
    from scripts.exam_pdf import lines, mark_bare_options

    markers = []
    for ri, region in enumerate(regions):
        page = doc[region['page'] - 1]
        found = lines(page, fitz.Rect(region['bbox']))
        mark_bare_options(found)
        markers += [(ri, line) for line in found if line.get('option')]
    if sorted(line['option'] for _, line in markers) != list('ABCDE'):
        return {'status': 'unresolved', 'reason': 'Não há cinco marcadores únicos A–E.'}
    columns = defaultdict(list)
    for ri, line in markers:
        # Marcadores na mesma coluna diferem no máximo 18 pontos em x.
        key = next(
            (key for key in columns if key[0] == ri and abs(key[1] - line['bbox'][0]) < 18), (ri, line['bbox'][0])
        )
        columns[key].append(line)
    choices = []
    for (ri, x), found in sorted(columns.items()):
        page = doc[regions[ri]['page'] - 1]
        clip = fitz.Rect(regions[ri]['bbox'])
        found.sort(key=lambda line: line['bbox'][1])
        centers = [(line['bbox'][1] + line['bbox'][3]) / 2 for line in found]
        gap = min([b - a for a, b in zip(centers, centers[1:])] or [80])
        other_x = sorted(k[1] for k in columns if k[0] == ri and k[1] > x + 18)
        for index, line in enumerate(found):
            top = (centers[index - 1] + centers[index]) / 2 if index else centers[index] - 0.65 * gap
            bottom = (
                (centers[index] + centers[index + 1]) / 2
                if index + 1 < len(found)
                else min(clip.y1, centers[index] + 0.65 * gap)
            )
            box = fitz.Rect(x, top, other_x[0] if other_x else clip.x1, bottom) & clip
            if box.is_empty:
                return {'status': 'unresolved', 'reason': 'Célula de alternativa fora da região.'}
            choices.append(
                {
                    'letter': line['option'],
                    'regions': [{'page': regions[ri]['page'], 'bbox': list(box)}],
                    'text_preview': page.get_text(clip=box).strip(),
                    'representation': 'original_region; all raster/vector components retained',
                }
            )
    return {
        'status': 'proposed',
        'needs_review': True,
        'alternatives': sorted(choices, key=lambda choice: choice['letter']),
        'reason': 'Agrupamento por marcador; recortes podem conter vizinhos. Conferir limites, fórmulas e ordem antes de transcrever.',
    }


def embedded_font_candidates(doc, page_number):
    """Contrasta mapas dos arquivos de fonte. Ambiguidades nunca viram texto aprovado."""
    page = doc[page_number - 1]
    maps = defaultdict(list)
    for xref, _, _, name, *_ in page.get_fonts():
        try:
            buffer = doc.extract_font(xref)[3]
            if not buffer:
                continue
            font = fitz.Font(fontbuffer=buffer)
            by_glyph = defaultdict(set)
            for codepoint in font.valid_codepoints():
                by_glyph[font.has_glyph(codepoint)].add(chr(codepoint))
            maps[name.split('+')[-1]].append(
                {glyph: next(iter(chars)) for glyph, chars in by_glyph.items() if len(chars) == 1}
            )
        except (ValueError, RuntimeError):
            continue
    results = []
    for span in page.get_texttrace():
        original = ''.join(chr(char[0]) for char in span['chars'])
        if '\ufffd' not in original:
            continue
        candidates = []
        for mapping in maps.get(span['font'], []):
            text = ''.join(mapping.get(char[1], chr(char[0])) for char in span['chars'])
            if text != original and text not in candidates:
                candidates.append(text)
        # Hipótese clássica de deslocamento do mapa: busca limitada por glifos,
        # nunca por número/ano. Mantém hipóteses concorrentes e os caracteres
        # já decodificados; não declara reparo de acentos/ligaturas por palpite.
        hypotheses = []
        common = {'de', 'do', 'da', 'a', 'o', 'que', 'e', 'em', 'um', 'uma', 'eu', 'bom', 'para', 'na', 'no'}
        if len(span['chars']) >= 12:
            for offset in range(-64, 65):
                text = ''.join(
                    chr(glyph + offset) if cp == 65533 and 0 < glyph + offset <= 0x10FFFF else chr(cp)
                    for cp, glyph, *_ in span['chars']
                )
                words = re.findall(r'\w+', text.lower())
                score = (
                    sum(word in common for word in words)
                    - sum(not c.isprintable() and not c.isspace() for c in text)
                    - text.count('\ufffd')
                )
                if score >= 2:
                    hypotheses.append((score, offset, text))
            for score, offset, text in sorted(hypotheses, reverse=True)[:5]:
                if text not in candidates:
                    candidates.append(text)
        results.append(
            {
                'page': page_number,
                'bbox': list(span['bbox']),
                'font': span['font'],
                'original': original,
                'candidates': candidates,
                'shift_hypotheses': [
                    {'offset': offset, 'legibility_score': score}
                    for score, offset, _ in sorted(hypotheses, reverse=True)[:5]
                ],
                'status': 'proposed' if candidates else 'unresolved',
                'needs_review': True,
                'reason': 'Mapa de glifos sem autenticação semântica; mesmo nome pode designar subconjuntos diferentes.',
            }
        )
    return results


def ocr_capabilities():
    """Descoberta local explícita; não chama a descoberta que baixa tessdata."""
    folders = [
        Path('/usr/share/tesseract/tessdata'),
        Path('/usr/share/tesseract-ocr/5/tessdata'),
        Path('/usr/share/tessdata'),
        Path('/opt/homebrew/share/tessdata'),
    ]
    if os.getenv('TESSDATA_PREFIX'):
        folders.insert(0, Path(os.environ['TESSDATA_PREFIX']))
    for folder in folders:
        if folder.is_dir():
            languages = sorted(path.stem for path in folder.glob('*.traineddata'))
            if languages:
                return {'engine': 'pymupdf-tesseract', 'tessdata': str(folder), 'languages': languages}
    return {'engine': 'tesseract-cli' if shutil.which('tesseract') else None, 'languages': []}


def ocr_page(pdf, page_number, language, timeout, bbox=None):
    """OCR local opcional e limitado; sem download automático ou provedor externo."""
    capabilities = ocr_capabilities()
    executable = shutil.which('tesseract')
    if not capabilities['engine']:
        return {
            'status': 'unavailable',
            'reason': 'Executável tesseract ausente; instale também os idiomas desejados para comparar OCR.',
        }
    started = time.perf_counter()
    if capabilities['engine'] == 'pymupdf-tesseract':
        requested = language.split('+')
        available = [name for name in requested if name in capabilities['languages']]
        if not available:
            return {
                'status': 'unavailable',
                'reason': 'Idiomas solicitados não estão instalados.',
                'capabilities': capabilities,
            }
        effective = '+'.join(available)
        command = [
            sys.executable,
            '-m',
            'experiments.ocr_worker',
            '--pdf',
            str(pdf),
            '--page',
            str(page_number),
            '--language',
            effective,
            '--tessdata',
            capabilities['tessdata'],
        ]
        if bbox:
            command += ['--bbox', *[str(value) for value in bbox]]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False, cwd=ROOT)
        except subprocess.TimeoutExpired:
            return {'status': 'timeout', 'timeout_seconds': timeout}
        text = result.stdout.strip()
        return {
            'status': 'proposed' if result.returncode == 0 else 'failed',
            'text': text if result.returncode == 0 else '',
            'error': result.stderr[-1000:] if result.returncode else None,
            'engine': capabilities['engine'],
            'requested_language': language,
            'effective_language': effective,
            'missing_languages': sorted(set(requested) - set(available)),
            'traineddata_sha256': {
                name: file_digest(Path(capabilities['tessdata']) / (name + '.traineddata')) for name in available
            },
            'latency_ms': (time.perf_counter() - started) * 1000,
            'needs_review': True,
        }
    with tempfile.TemporaryDirectory(prefix='enem-ocr-') as temporary:
        image = Path(temporary) / 'page.png'
        with fitz.open(pdf) as doc:
            doc[page_number - 1].get_pixmap(matrix=fitz.Matrix(3, 3), clip=fitz.Rect(bbox) if bbox else None).save(
                image
            )
        try:
            result = subprocess.run(
                [executable, str(image), 'stdout', '-l', language, '--psm', '3'],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {'status': 'timeout', 'timeout_seconds': timeout}
    return {
        'status': 'proposed' if result.returncode == 0 else 'failed',
        'text': result.stdout if result.returncode == 0 else '',
        'error': result.stderr[-1000:] if result.returncode else None,
        'latency_ms': (time.perf_counter() - started) * 1000,
        'needs_review': True,
    }


def visual_answer_key(doc, language=None):
    """Círculos verdes explícitos + cinco marcadores vetoriais na região da questão.

    Não infere anuladas, não usa o gabarito de outra cor e recusa grupos que
    não tenham exatamente cinco círculos de alternativa e uma marca verde.
    """
    from scripts.exam_pdf import LANGUAGE, language_key, lines
    from scripts.pdf_headings import HEADING, heading_number

    groups, current, section = defaultdict(lambda: {'markers': [], 'marks': [], 'regions': []}), None, None
    for pn, page in enumerate(doc, 1):
        drawings = page.get_drawings()
        dark = [
            d['rect']
            for d in drawings
            if d.get('fill')
            and max(d['fill']) < 0.3
            and len(d['items']) == 4
            and 5 < d['rect'].width < 13
            and 0.8 < d['rect'].width / max(1, d['rect'].height) < 1.2
        ]
        green = [
            d['rect']
            for d in drawings
            if d.get('color')
            and d['color'][1] > d['color'][0] + 0.2
            and d['color'][2] <= d['color'][1] + 0.1
            and 8 < d['rect'].width < 30
            and 6 < d['rect'].height < 25
        ]
        source_lines = lines(page, page.rect)
        for left, right in [(0, page.rect.width / 2), (page.rect.width / 2, page.rect.width)]:
            headings = []
            for line in source_lines:
                if not left <= line['bbox'][0] < right:
                    continue
                if match := HEADING.match(line['text']):
                    headings.append((line['bbox'][1], 'question', heading_number(match), line['bbox'][0]))
                elif match := LANGUAGE.match(line['text']):
                    headings.append(
                        (
                            line['bbox'][1],
                            'language',
                            (int(match[1]), int(match[2]), language_key(match[3])),
                            line['bbox'][0],
                        )
                    )
            cursor = 55
            for y, kind, value, x in [*sorted(headings), (page.rect.height - 35, 'end', None, left + 32)]:
                if current is not None and y > cursor:
                    group = groups[current]
                    group['markers'] += [
                        (pn, list(rect))
                        for rect in dark
                        if left <= rect.x0 < right
                        and cursor <= rect.y0 < y
                        and abs(rect.x0 - left - group['x_offset']) < 12
                    ]
                    group['marks'] += [
                        (pn, list(rect)) for rect in green if left <= rect.x0 < right and cursor <= rect.y0 < y
                    ]
                    group['regions'].append({'page': pn, 'bbox': [left, cursor, right, y]})
                if kind == 'language':
                    section, current = value, None
                elif kind == 'question':
                    if section and not section[0] <= value <= section[1]:
                        section = None
                    current = (value, section[2] if section else None)
                    groups[current]['x_offset'] = x - left
                cursor = y
    results = []
    for (number, item_language), group in sorted(groups.items(), key=lambda pair: (pair[0][0], pair[0][1] or '')):
        if item_language and item_language != language:
            continue
        markers = sorted(
            set((page, tuple(box)) for page, box in group['markers']),
            key=lambda item: (item[0], item[1][1], item[1][0]),
        )
        hits = [
            (i, page, box, mark)
            for i, (page, box) in enumerate(markers)
            for mp, mark in group['marks']
            if page == mp and fitz.Rect(mark).contains((fitz.Rect(box).tl + fitz.Rect(box).br) * 0.5)
        ]
        valid = len(markers) == 5 and len(group['marks']) == 1 and len(hits) == 1
        results.append(
            {
                'number': number,
                'language': item_language,
                'answer': 'ABCDE'[hits[0][0]] if valid else None,
                'status': 'proposed' if valid else 'unresolved',
                'needs_review': True,
                'marker_count': len(markers),
                'mark_count': len(group['marks']),
                'evidence': {'markers': markers, 'marks': group['marks']},
                'reason': 'Conferir o círculo destacado no caderno com gabarito; saída não é gabarito publicado.',
            }
        )
    return results


def edit_distance(a, b):
    previous = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        current = [i]
        for j, right in enumerate(b, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
        previous = current
    return previous[-1]


def run_archive(config, output, use_ocr=False):
    """Acervo opcional: sem as fontes locais registra ausência, sem baixar/publicar."""
    from backend.app.schemas import ExamImport
    from backend.app.preparation import blocking_issues
    from backend.app.services.presentation import content_fingerprint

    catalog = read_json(ROOT / 'data/sources/catalogo/acervo.json')['files']
    by_hash = {r.get('sha256'): r for r in catalog if r.get('sha256') and r['role'] == 'prova'}
    counts, candidates = Counter(), Counter()
    proposals, failures = [], []
    paths = [
        p for p in sorted((ROOT / 'data/derived/exams').glob('enem-*.json')) if not p.name.endswith('.report.json')
    ]
    processed = 0
    for path in paths:
        exam = ExamImport.model_validate(read_json(path))
        record = by_hash.get(exam.source.sha256)
        if record is None:
            failures.append({'id': exam.id, 'reason': 'Fonte não registrada no catálogo.'})
            continue
        try:
            pdf = source_path('data/sources/' + record['path'], exam.source.sha256)
        except (OSError, ValueError) as error:
            failures.append({'id': exam.id, 'reason': str(error)})
            continue
        with fitz.open(pdf) as doc:
            for question in exam.questions:
                content = question.content.model_dump()
                issues = blocking_issues(content)
                if not issues:
                    continue
                codes = Counter(issue['code'] for issue in issues)
                counts.update(codes)
                regions = content['layout']['blocks']
                row = {
                    'question_id': question.question_id,
                    'source_sha256': exam.source.sha256,
                    'content_sha256': content_fingerprint(content),
                    'review_status': 'proposed',
                    'needs_review': True,
                    'original_issues': issues,
                    'repairs': {},
                }
                if 'alternative_layout' in codes:
                    row['repairs']['alternatives'] = alternative_regions(doc, regions)
                    if row['repairs']['alternatives']['status'] == 'proposed':
                        candidates['alternative_layout'] += codes['alternative_layout']
                if 'merged_table_cells' in codes:
                    tables = []
                    for region in regions:
                        page = doc[region['page'] - 1]
                        for table in page.find_tables(clip=fitz.Rect(region['bbox']), use_layout=False).tables:
                            structure = table_structure(page, table)
                            structure['grid_integrity'] = grid_integrity(structure)
                            tables.append({'page': region['page'], 'bbox': list(table.bbox), **structure})
                    row['repairs']['tables'] = tables
                    if any(table['has_spans'] and table['grid_integrity'] for table in tables):
                        candidates['merged_table_cells'] += codes['merged_table_cells']
                if 'spatial_layout' in codes:
                    row['repairs']['spatial'] = {
                        'status': 'unresolved',
                        'regions': regions,
                        'reason': 'Preservar o original; recorte não equivale à reconstrução semântica da fórmula/tabela.',
                    }
                proposals.append(row)
        processed += 1
        if processed % 12 == 0:
            print(f'Layout do acervo: {processed}/{len(paths)} cadernos examinados.', flush=True)
    challenges = evaluate_challenges(config, output, use_ocr)
    report = {
        'requested': True,
        'available': bool(paths),
        'exam_files': len(paths),
        'processed_exams': processed,
        'affected_questions': len(proposals),
        'original_issues': dict(counts),
        'candidate_coverage': dict(candidates),
        'resolved_or_published': 0,
        'remaining_without_candidate': {key: value - candidates[key] for key, value in counts.items()},
        'failures': failures,
        'challenges': challenges,
        'interpretation': 'Cobertura de propostas não significa erros corrigidos. Nenhum diagnóstico ou conteúdo publicado foi alterado.',
    }
    write_json(output / 'archive-layout-proposals.json', proposals)
    write_json(output / 'archive-layout-report.json', report)
    return report


def evaluate_challenges(config, output, use_ocr):
    reference = read_json(ROOT / 'data/datasets/recovery-reference-v1.json')
    results, predictions = [], []
    for case in reference['cases']:
        try:
            pdf = source_path(case['source_path'], case['source_sha256'])
        except FileNotFoundError:
            results.append({'id': case['id'], 'status': 'source_unavailable'})
            continue
        if case['kind'] == 'visual_answer_key':
            with fitz.open(pdf) as doc:
                proposed = visual_answer_key(doc, case.get('language'))
            by_number = {p['number']: p for p in proposed}
            expected = case['answers']
            correct = sum(by_number.get(int(n), {}).get('answer') == answer for n, answer in expected.items())
            results.append(
                {
                    'id': case['id'],
                    'status': 'evaluated',
                    'reference_items': len(expected),
                    'correct': correct,
                    'accuracy': correct / len(expected),
                    'proposed_total': sum(p['status'] == 'proposed' for p in proposed),
                    'unresolved_total': sum(p['status'] != 'proposed' for p in proposed),
                    'independent_review': False,
                }
            )
            predictions.append({'id': case['id'], 'source_sha256': case['source_sha256'], 'proposals': proposed})
        elif case['kind'] == 'font_encoding':
            with fitz.open(pdf) as doc:
                proposed = embedded_font_candidates(doc, case['page'])
                raw = doc[case['page'] - 1].get_text(clip=fitz.Rect(case['bbox'])).strip()
            overlapping = [r for r in proposed if fitz.Rect(r['bbox']).intersects(fitz.Rect(case['bbox']))]
            expected = case['text']

            # A escolha de candidato usa só legibilidade; a referência só mede depois.
            def readability(text):
                words = re.findall(r'\w+', text.lower())
                return sum(
                    w in {'de', 'do', 'da', 'a', 'o', 'que', 'e', 'em', 'um', 'uma', 'eu', 'bom', 'para', 'na', 'no'}
                    for w in words
                ) - text.count('\ufffd')

            choices = [text for row in overlapping for text in row['candidates']]
            selected = max(choices, key=readability) if choices else raw
            normal = lambda text: ' '.join(text.split())
            denom = max(1, len(normal(expected)))
            results.append(
                {
                    'id': case['id'],
                    'status': 'evaluated',
                    'raw_character_error_rate': edit_distance(normal(raw), normal(expected)) / denom,
                    'font_character_error_rate': edit_distance(normal(selected), normal(expected)) / denom,
                    'exact_recovery': normal(selected) == normal(expected),
                    'independent_review': False,
                }
            )
            ocr = (
                ocr_page(pdf, case['page'], config['ocr_language'], config['ocr_timeout_seconds'], case['bbox'])
                if use_ocr
                else {'status': 'not_run', 'reason': 'Use --ocr para comparar com Tesseract local.'}
            )
            if ocr.get('status') == 'proposed':
                ocr['character_error_rate'] = edit_distance(normal(ocr['text']), normal(expected)) / denom
            predictions.append(
                {
                    'id': case['id'],
                    'original': raw,
                    'selected_font_candidate': selected,
                    'font_proposals': overlapping,
                    'ocr': ocr,
                    'needs_review': True,
                }
            )
        else:
            with fitz.open(pdf) as doc:
                proposed = embedded_font_candidates(doc, case['page'])
            results.append(
                {
                    'id': case['id'],
                    'status': 'diagnostic_only',
                    'unmapped_spans': len(proposed),
                    'spans_with_font_candidate': sum(bool(row['candidates']) for row in proposed),
                    'accuracy': None,
                    'reason': 'Sem transcrição adjudicada; legibilidade não é acurácia.',
                }
            )
            ocr = (
                ocr_page(pdf, case['page'], config['ocr_language'], config['ocr_timeout_seconds'])
                if use_ocr
                else {'status': 'not_run'}
            )
            predictions.append({'id': case['id'], 'font_proposals': proposed, 'ocr': ocr, 'needs_review': True})
    write_json(output / 'recovery-proposals.json', predictions)
    return {
        'reference_version': reference['version'],
        'reference_sha256': digest(reference),
        'cases': results,
        'ocr_available': bool(ocr_capabilities()['engine']),
        'ocr_requested': use_ocr,
    }
