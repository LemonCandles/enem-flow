"""Geometry-based PDF adapter. No exam year or question number is special-cased."""

import hashlib
from contextlib import nullcontext
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf as fitz
from scripts.pdf_headings import HEADING, QUESTION_WORD, heading_number

SUB = str.maketrans('0123456789+-−', '₀₁₂₃₄₅₆₇₈₉₊₋₋')
SUP = str.maketrans('0123456789+-−', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻')
LANGUAGE = re.compile(r'^Quest[õo]es\s+de\s+(\d+)\s+a\s+(\d+)\s*\(\s*op[çc][ãa]o\s*:?\s*([^)]+?)\s*\)', re.I)
# Glyphs that Portuguese, Spanish and English text practically never uses; a font
# without a character map turns ordinary letters into them ("fÜ éîèÜèê").
SUSPECT = re.compile(r'[\x00-\x08\x0b-\x1f†‡¶§¤¢£•™ÜÛÙîìèòùåæøßÆØÅ]')


def garbled(text):
    """A line whose glyphs come from a font without a usable character map."""
    letters = [c for c in text if c.isalpha() or ord(c) < 32 or c in '†‡¶§¤¢£•™']
    return len(letters) >= 8 and sum(bool(SUSPECT.fullmatch(c)) for c in letters) / len(letters) > 0.2


def diagnostic(code, message, location, severity='warning', excerpt=''):
    return dict(code=code, message=message, location=location, severity=severity, excerpt=excerpt[:500])


def literal(text):
    """PDF text never carries LaTeX: escape a dollar sign unless a currency code precedes it (R$, US$)."""
    return re.sub(r'(?<![A-Z\\])\$', r'\\$', text)


def watermark(line):
    """Rotated text repeating a short unit, such as a vertical exam name between columns."""
    if abs(line['dir'][0]) > 0.99:
        return False
    compact = re.sub(r'\s+', '', ''.join(s['text'] for s in line['spans']))
    if len(compact) < 12 or not re.search(r'[A-Za-z]', compact):
        return False
    return any(
        all(compact[i] == compact[i % size] for i in range(len(compact))) for size in range(3, len(compact) // 3 + 1)
    )


def lines(page, rect):
    result = []
    for bi, b in enumerate(
        page.get_text('dict', clip=rect, flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)['blocks']
    ):
        if b['type'] != 0:
            continue
        for line in b['lines']:
            if watermark(line):
                continue
            spans = line['spans']
            weights = Counter()
            for s in spans:
                weights[round(s['size'], 1)] += len(s['text'].strip())
            size = weights.most_common(1)[0][0] if weights else 10
            normal = [s for s in spans if s['size'] >= size * 0.9]
            baseline = sorted(s['origin'][1] for s in normal)[len(normal) // 2] if normal else line['bbox'][3]
            parts, uncertain = [], False
            for s in spans:
                text = s['text']
                offset = s['origin'][1] - baseline
                if s['size'] < size * 0.85 and abs(offset) > 1:
                    if re.fullmatch(r'[0-9+−-]+', text):
                        text = text.translate(SUB if offset > 0 else SUP)
                    else:
                        uncertain = True
                parts.append(text)
            marker = re.match(r'^([ABCDE])(?:\t|[.)]\s)', spans[0]['text']) if spans else None
            result.append(
                dict(
                    text=''.join(parts).strip(),
                    bbox=list(line['bbox']),
                    group=bi,
                    size=size,
                    uncertain=uncertain,
                    option=marker[1] if marker else None,
                    font=spans[0]['font'] if spans else '',
                )
            )
    # Some official PDFs overlay an accessible A–E text layer on the visible
    # option glyph. Keep the complete line once, without turning A A B B into
    # ten alternatives. Only remove a single-letter line inside its rich peer.
    result = [
        line
        for line in result
        if not (
            line.get('option')
            and line['text'] == line['option']
            and any(
                other is not line
                and other.get('option') == line['option']
                and len(other['text']) > 2
                and abs(other['bbox'][0] - line['bbox'][0]) < 3
                and fitz.Rect(other['bbox']).intersects(fitz.Rect(line['bbox']))
                for other in result
            )
        )
    ]
    # Accessible layers may repeat a line at the same position; keep one copy.
    unique = {}
    for line in result:
        unique.setdefault((line['text'], *(round(v) for v in line['bbox'])), line)
    result = list(unique.values())
    # Some layouts print "Questão" and its number as separate lines on the same baseline.
    for line in [l for l in result if re.fullmatch(QUESTION_WORD, l['text'], re.I)]:
        number = next(
            (
                n
                for n in result
                if re.fullmatch(r'\d{1,3}', n['text'])
                and abs(n['bbox'][1] - line['bbox'][1]) < 3
                and 0 <= n['bbox'][0] - line['bbox'][2] < 60
            ),
            None,
        )
        if number:
            line['text'] = f"{line['text']} {number['text']}"
            line['bbox'] = [
                min(line['bbox'][0], number['bbox'][0]),
                min(line['bbox'][1], number['bbox'][1]),
                max(line['bbox'][2], number['bbox'][2]),
                max(line['bbox'][3], number['bbox'][3]),
            ]
            result.remove(number)
    return sorted(result, key=lambda l: (round(l['bbox'][1], 1), l['bbox'][0]))


def mark_bare_options(source_lines):
    """Bare letters become option markers when one font prints exactly A–E once.

    Option glyphs often use their own font; figure labels such as points A, B
    and C use the text font, so they never complete the set.
    """
    if sorted(l['option'] for l in source_lines if l.get('option')) == list('ABCDE'):
        return
    fonts = {}
    for line in source_lines:
        if not line.get('option') and re.fullmatch(r'[ABCDE]', line['text']):
            fonts.setdefault(line['font'], []).append(line)
    found = [group for group in fonts.values() if sorted(l['text'] for l in group) == list('ABCDE')]
    if len(found) == 1:
        for line in found[0]:
            line['option'] = line['text']


def align_option_lines(source_lines):
    """Join a separate A–E glyph to its text on the same printed baseline.

    A glyph's font can put its bounding box two points below the option text.
    Sorting those boxes by y alone shifts every answer to the following letter.
    Require a unique right-hand neighbour with substantial vertical overlap.
    """
    for marker in list(source_lines):
        if not marker.get('option') or marker['text'] != marker['option']:
            continue
        mr = fitz.Rect(marker['bbox'])
        peers = []
        for line in source_lines:
            if line is marker or line.get('option'):
                continue
            r = fitz.Rect(line['bbox'])
            overlap = max(0, min(mr.y1, r.y1) - max(mr.y0, r.y0))
            if 0 <= r.x0 - mr.x1 < 60 and overlap > min(mr.height, r.height) * 0.55:
                peers.append(line)
        if len(peers) == 1:
            peer = peers[0]
            marker.update(
                text=marker['option'] + '\t' + peer['text'],
                bbox=list(mr | fitz.Rect(peer['bbox'])),
                group=peer['group'],
                uncertain=peer['uncertain'],
            )
            source_lines.remove(peer)
    return sorted(source_lines, key=lambda l: (round(l['bbox'][1], 1), l['bbox'][0]))


def language_key(name):
    """'Inglês' -> 'ingles': the key a manifest uses to choose a language option."""
    return ''.join(c for c in unicodedata.normalize('NFKD', name.strip().lower()) if not unicodedata.combining(c))


def shared_numbers(text):
    """Explicit shared passages; never infer targets from a topic or proximity."""
    match = re.match(
        r'^(?:textos?|figura|tabela|grafico|informacoes|dados)\b.*?\bpara\s+(?:as?\s+)?questoes(?:\s+de)?\s+(\d{1,3})\s+(e|a|[-–])\s+(\d{1,3})\b',
        language_key(text),
    )
    if not match:
        return None
    first, last = int(match[1]), int(match[3])
    if not 0 < first < last <= first + 10:
        return None
    return [first, last] if match[2] == 'e' else list(range(first, last + 1))


def section_break(text):
    return language_key(text).strip() in {'proposta de redacao', 'instrucoes para a redacao'}


def auto_columns(source_lines, width):
    wide = sum(l['bbox'][2] - l['bbox'][0] > width * 0.65 for l in source_lines)
    crossing = sum(
        l['bbox'][0] < width / 2 - 12 and l['bbox'][2] > width / 2 + 12 and len(l['text']) > 25 for l in source_lines
    )
    heading_columns = {l['bbox'][0] >= width / 2 for l in source_lines if HEADING.match(l['text'])}
    return (
        [[0, width]]
        if wide >= 2 or crossing >= 3 and len(heading_columns) <= 1
        else [[0, width / 2], [width / 2, width]]
    )


def textual_table(rows):
    cells = [str(cell or '').strip() for row in rows for cell in row]
    return len(cells) >= 4 and sum(bool(cell) for cell in cells) >= max(3, len(cells) * 0.5)


def discover_regions(doc, config, languages=None):
    """Discover question boundaries in one/two columns; overrides describe layout.

    Foreign-language options are printed sections ("Questões de 01 a 05 (opção
    inglês)") that reuse the same numbers. Only the option declared in
    `language` is kept; `languages` receives number -> language for those items.
    """
    layout = config.get('layout', {})
    chosen = language_key(config['language']) if config.get('language') else None
    regions, current, section, offered = {}, None, None, set()
    shared = []
    start, end = layout.get('pages', [1, len(doc)])
    if not (1 <= start <= end <= len(doc)):
        raise ValueError('Intervalo de páginas inválido.')
    for pn in range(start, end + 1):
        page = doc[pn - 1]
        options = {**layout, **layout.get('page_overrides', {}).get(str(pn), {})}
        top, bottom = options.get('top', 55), options.get('bottom', page.rect.height - 48)
        all_lines = lines(page, fitz.Rect(0, top, page.rect.width, bottom))
        columns = options.get('columns', 'auto')
        if columns == 'auto':
            columns = auto_columns(all_lines, page.rect.width)
        if not isinstance(columns, list) or not columns:
            raise ValueError('columns deve ser auto ou uma lista de intervalos [x0, x1].')
        for x0, x1 in columns:
            events = []
            for l in all_lines:
                if not x0 <= l['bbox'][0] < x1:
                    continue
                if m := HEADING.match(l['text']):
                    events.append((l['bbox'][1], 'question', heading_number(m)))
                elif m := LANGUAGE.match(l['text']):
                    events.append((l['bbox'][1], 'language', (int(m[1]), int(m[2]), language_key(m[3]))))
                elif targets := shared_numbers(l['text']):
                    events.append((l['bbox'][1], 'shared', targets))
                elif section_break(l['text']):
                    events.append((l['bbox'][1], 'break', None))
            cursor = top
            for y, kind, value in sorted(events):
                if current is not None and y > cursor + 3:
                    clip = fitz.Rect(x0, cursor, x1, y - 1)
                    if page.get_text(clip=clip).strip():
                        regions[current].append({'page': pn, 'bbox': list(clip)})
                current, cursor = None, y
                if kind == 'break':
                    continue
                if kind == 'language':
                    section = value
                    offered.add(value[2])
                    continue
                if kind == 'shared':
                    if section and section[2] != chosen and section[0] <= value[0] <= section[1]:
                        continue
                    current = ('shared', len(shared))
                    shared.append((current, value))
                    regions[current] = []
                    continue
                number = value
                if section and not section[0] <= number <= section[1]:
                    section = None
                if section:
                    if not chosen:
                        raise ValueError(
                            f'Questões {section[0]}–{section[1]} têm opções de língua estrangeira: declare "language" no manifesto ({", ".join(sorted(offered))}).'
                        )
                    if section[2] != chosen:
                        continue
                    if languages is not None:
                        languages[number] = chosen
                if number in regions:
                    raise ValueError(f'Cabeçalho duplicado {number}: confira idioma, páginas e colunas no manifesto.')
                regions[number] = []
                current = number
            if current is not None and bottom > cursor:
                clip = fitz.Rect(x0, cursor, x1, bottom)
                if page.get_text(clip=clip).strip():
                    regions[current].append({'page': pn, 'bbox': list(clip)})
    if chosen and chosen not in offered:
        raise ValueError(
            f'Língua "{config["language"]}" não encontrada nas opções do caderno ({", ".join(sorted(offered)) or "nenhuma"}).'
        )
    for key, targets in shared:
        pieces = regions.pop(key)
        if not pieces or any(number not in regions for number in targets):
            raise ValueError(f'Texto compartilhado sem todas as questões {targets}; confira as margens e a língua.')
        for number in targets:
            regions[number] = [{**piece, 'shared_for': targets} for piece in pieces] + regions[number]
    return regions


def margin_headings(doc, config, numbers):
    """Headings of missing questions printed above `top` or below `bottom`."""
    layout = config.get('layout', {})
    start, end = layout.get('pages', [1, len(doc)])
    found = []
    for pn in range(start, end + 1):
        page = doc[pn - 1]
        options = {**layout, **layout.get('page_overrides', {}).get(str(pn), {})}
        top, bottom = options.get('top', 55), options.get('bottom', page.rect.height - 48)
        for line in lines(page, page.rect):
            m = HEADING.match(line['text'])
            if m and heading_number(m) in numbers and not top <= line['bbox'][1] < bottom:
                found.append(f'{heading_number(m)} (página {pn}, y={line["bbox"][1]:.0f})')
    return found[:8]


def answer_key_rows(text, language=None, numbers=None, booklet=None):
    """Number -> answer. Language options print one column per language ("1 C D").

    "*A" marks an answer rectified by the Inep. `numbers` limits the key to the
    booklet's questions, since some keys also list the other day.
    """
    text = text.replace('\xa0', ' ')
    columns = [
        key
        for _, key in sorted((m.start(), language_key(m[0])) for m in re.finditer(r'INGL[ÊE]S|ESPANHOL', text, re.I))
    ]
    columns = list(dict.fromkeys(columns))
    chosen = language_key(language) if language else None
    colors = list(
        dict.fromkeys(
            value.casefold()
            for value in re.findall(r'Gab[_ -]+(Azul|Amarelo|Branco|Rosa|Cinza|Verde|Laranja|Roxo)\b', text, re.I)
        )
    )
    selected_color = next(
        (color for color in colors if re.search(r'\b' + color + r'\b', (booklet or '').casefold())), None
    )
    if len(colors) > 1 and selected_color is None:
        raise ValueError('O gabarito reúne várias cores: informe o caderno/cor no manifesto.')
    rows = {}
    for n, first, second in re.findall(
        r'\b(\d{1,3})\s+\*?(ANULAD[AO]|[ABCDE])\b(?:[ \t]*\n?[ \t]*\*?(ANULAD[AO]|[ABCDE])(?=[ \t]*(?:\n|$)))?',
        text,
        re.I,
    ):
        if numbers is not None and int(n) not in numbers:
            continue
        value = first
        if second:
            if len(columns) != 2:
                raise ValueError(
                    f'Gabarito com duas respostas na questão {int(n)} sem colunas de língua identificadas.'
                )
            if not chosen:
                raise ValueError(
                    f'O gabarito tem colunas por língua ({", ".join(columns)}): declare "language" no manifesto.'
                )
            if chosen not in columns:
                raise ValueError(f'Língua "{language}" ausente no gabarito ({", ".join(columns)}).')
            value = (first, second)[columns.index(chosen)]
        value = value.upper()
        rows.setdefault(int(n), []).append(None if value.startswith('ANULAD') else value)
    answers = {}
    for number, values in rows.items():
        if len(colors) > 1:
            if len(values) != len(colors):
                raise ValueError(f'Questão {number}: quantidade de respostas difere das colunas de cor.')
            answers[number] = values[colors.index(selected_color)]
        elif len(set(values)) > 1:
            raise ValueError(f'Gabaritos conflitantes na questão {number}; confira as colunas da fonte.')
        else:
            answers[number] = values[0]
    return answers


def from_manifest(manifest, pdf, answer_key=None):
    """Metadata/area ranges are explicit; answer keys never come from heuristics."""
    config = dict(manifest)
    answers = {int(k): v for k, v in config.get('answers', {}).items()}
    if answer_key:
        with fitz.open(answer_key) as doc:
            text = '\n'.join(p.get_text() for p in doc)
        covered = {n for area in config.get('areas', []) for n in range(area['first'], area['last'] + 1)} or None
        for n, answer in answer_key_rows(text, config.get('language'), covered, config.get('booklet')).items():
            if n in answers and answers[n] != answer:
                raise ValueError(f'Gabaritos conflitantes na questão {n}.')
            answers[n] = answer
    if not answers:
        raise ValueError('Informe answers no manifesto ou --answer-key com gabarito textual.')
    if any(v not in [None, *'ABCDE'] for v in answers.values()):
        raise ValueError('Gabarito deve conter A–E ou null para anuladas.')
    with fitz.open(pdf) as doc:
        languages = {}
        regions = discover_regions(doc, config, languages)
        if config.get('range'):
            # A section of the booklet: only these numbers are prepared.
            first, last = config['range']
            regions = {n: r for n, r in regions.items() if first <= n <= last}
            answers = {n: a for n, a in answers.items() if first <= n <= last}
        if not regions:
            raise ValueError(
                'Nenhum cabeçalho textual encontrado: confira páginas e margens. Sem camada de texto, o PDF exige OCR; com codificação quebrada, use outra cor legível da mesma aplicação.'
            )
        if set(regions) != set(answers):
            missing = sorted(set(answers) - set(regions))
            hint = ''
            outside = margin_headings(doc, config, missing)
            if outside:
                hint = f' Cabeçalhos fora das margens do layout (ajuste layout.top/bottom): {", ".join(outside)}.'
            raise ValueError(
                f'Questões e gabarito não coincidem: sem gabarito {sorted(set(regions) - set(answers))}; sem questão {missing}.{hint}'
            )
        questions = []
        for number, pieces in sorted(regions.items()):
            matches = [r for r in config['areas'] if r['first'] <= number <= r['last']]
            if len(matches) != 1:
                raise ValueError(f'Área ausente ou sobreposta para a questão {number}.')
            area = matches[0]
            questions.append(
                {
                    'question_id': f"{config['id']}-q{number}",
                    'content': {
                        'number': number,
                        'area': area['area'],
                        'statement': '\n\n'.join(
                            doc[r['page'] - 1].get_text(clip=fitz.Rect(r['bbox'])) for r in pieces
                        ),
                        'blocks': [],
                        'images': [],
                        'alternatives': [{'letter': a, 'text': 'Transcrição pendente de preparação.'} for a in 'ABCDE'],
                        'correct_answer': answers[number],
                        'annulled': answers[number] is None,
                        'labels': {
                            'discipline': area.get('discipline'),
                            'provenance': 'Área declarada no manifesto; classificação aguarda revisão.',
                        },
                        'page': pieces[0]['page'],
                        'original_layout': False,
                        'layout': {
                            'blocks': pieces,
                            **({'language': languages[number]} if number in languages else {}),
                        },
                    },
                }
            )
    fields = ['id', 'title', 'year', 'application', 'booklet', 'day', 'kind', 'expected_items', 'duration_minutes']
    result = {key: config[key] for key in fields}
    result['source'] = {**config['source'], 'sha256': hashlib.sha256(Path(pdf).read_bytes()).hexdigest()}
    if answer_key:
        result['source']['answer_key_sha256'] = hashlib.sha256(Path(answer_key).read_bytes()).hexdigest()
    if not result['source'].get('answer_key_sha256'):
        raise ValueError('Informe o hash SHA-256 do gabarito ou o arquivo --answer-key.')
    result['questions'] = questions
    if len(questions) != result['expected_items']:
        raise ValueError('Quantidade extraída diferente de expected_items.')
    return result


def graphics(page, clip):
    candidates = [fitz.Rect(i['bbox']) & clip for i in page.get_image_info() if fitz.Rect(i['bbox']).intersects(clip)]
    candidates += [fitz.Rect(r) & clip for r in page.cluster_drawings(clip=clip, x_tolerance=7, y_tolerance=7)]
    candidates = [r for r in candidates if r.width > 14 and r.height > 12 and r.get_area() > 350]
    # Thin bars spanning most of the page height are section decorations, not figures.
    candidates = [r for r in candidates if not (r.height > page.rect.height * 0.5 and r.width < page.rect.width * 0.08)]
    merged = []
    for rect in candidates:
        for i, old in enumerate(merged):
            grown = old + (-8, -8, 8, 8)
            if grown.intersects(rect):
                merged[i] |= rect
                break
        else:
            merged.append(rect)
    # Merge transitively; raster and vector layers often overlap one figure.
    changed = True
    while changed:
        changed = False
        for i in range(len(merged)):
            for j in range(i + 1, len(merged)):
                if (merged[i] + (-8, -8, 8, 8)).intersects(merged[j]):
                    merged[i] |= merged.pop(j)
                    changed = True
                    break
            if changed:
                break
    return sorted(merged, key=lambda r: (r.y0, r.x0))


def alternative_graphics(rects, source_lines, clip):
    """Split drawing groups by printed option markers, including two-column grids."""
    markers = [l for l in source_lines if l.get('option')]
    if sorted(l['option'] for l in markers) != list('ABCDE'):
        return [(r, None) for r in rects]
    columns = []
    for line in sorted(markers, key=lambda l: l['bbox'][0]):
        x = line['bbox'][0]
        if not columns or abs(x - columns[-1][0]) > 18:
            columns.append((x, [line]))
        else:
            columns[-1][1].append(line)
    cells = []
    for ci, (x, items) in enumerate(columns):
        items.sort(key=lambda l: l['bbox'][1])
        centers = [(l['bbox'][1] + l['bbox'][3]) / 2 for l in items]
        gap = min([b - a for a, b in zip(centers, centers[1:])] or [80])
        for j, line in enumerate(items):
            top = (centers[j - 1] + centers[j]) / 2 if j else centers[j] - gap * 0.65
            bottom = (centers[j] + centers[j + 1]) / 2 if j + 1 < len(items) else min(clip.y1, centers[j] + gap * 0.65)
            right = columns[ci + 1][0] if ci + 1 < len(columns) else clip.x1
            cells.append((line['option'], fitz.Rect(x, top, right, bottom) & clip))
    result = []
    for rect in rects:
        # A drawing beside a single marker belongs to it whole; only groups
        # spanning several markers are split, so separate graphs are never cut.
        beside = [
            l['option']
            for l in markers
            if rect.y0 - 4 <= (l['bbox'][1] + l['bbox'][3]) / 2 <= rect.y1 + 4
            and l['bbox'][0] < rect.x1
            and rect.x0 - l['bbox'][2] < 60
        ]
        if len(beside) == 1:
            result.append((rect, beside[0]))
            continue
        pieces = []
        for letter, cell in cells:
            overlap = rect & cell
            if (
                not overlap.is_empty
                and overlap.get_area() > 350
                and overlap.get_area() > min(rect.get_area(), cell.get_area()) * 0.25
            ):
                pieces.append((overlap, letter))
        if pieces and sum(r.get_area() for r, _ in pieces) > rect.get_area() * 0.65:
            result.extend(pieces)
        else:
            result.append((rect, None))
    return result


def extract_exam(data, pdf, assets_root, document=None):
    """Rebuild native blocks from positioned regions in an arbitrary exam JSON."""
    if document is not None and Path(document.name).resolve() != Path(pdf).resolve():
        raise ValueError('Documento aberto difere da fonte declarada.')
    with nullcontext(document) if document is not None else fitz.open(pdf) as doc:
        source_hash = hashlib.sha256(Path(pdf).read_bytes()).hexdigest()
        if source_hash != data['source']['sha256']:
            raise ValueError('Hash do PDF diferente da origem declarada no JSON.')
        for question in data['questions']:
            c = question['content']
            regions = (c.get('layout') or {}).get('blocks', [])
            if not regions:
                raise ValueError(f"Questão {c['number']}: faltam regiões page/bbox. Use --manifest para descobri-las.")
            entries, issues, positions = [], [], []
            for region in regions:
                pn = region['page']
                if not 1 <= pn <= len(doc):
                    raise ValueError('Página fora do PDF.')
                page, clip = doc[pn - 1], fitz.Rect(region['bbox'])
                if clip.is_empty or not page.rect.contains(clip):
                    raise ValueError('Região fora da página.')
                source_lines = lines(page, clip)
                mark_bare_options(source_lines)
                source_lines = align_option_lines(source_lines)
                figs = []
                for candidate in graphics(page, clip):
                    if candidate.get_area() >= clip.get_area() * 0.9:
                        issues.append(
                            diagnostic(
                                'whole_region_image',
                                'Imagem ocupa o recorte integral: separe os diagramas ou faça OCR e confira o texto antes de aprovar.',
                                f'page:{pn}',
                                'error',
                            )
                        )
                    else:
                        figs.append(candidate)
                tables = []
                # Tables with a rectangular cell grid become HTML data. Never
                # infer missing cells from prose or replace a table with OCR guesses.
                for table in page.find_tables(clip=clip, use_layout=False).tables:
                    if any(
                        l.get('option') and fitz.Rect(table.bbox).contains(fitz.Point(l['bbox'][:2]))
                        for l in source_lines
                    ):
                        continue
                    rows = table.extract()
                    if (
                        len(rows) > 1
                        and 1 < len(rows[0]) <= 12
                        and all(len(r) == len(rows[0]) for r in rows)
                        and textual_table(rows)
                    ):
                        if any(cell is None for row in rows for cell in row):
                            issues.append(
                                diagnostic(
                                    'merged_table_cells',
                                    'Tabela com células mescladas ou ausentes: confira a estrutura antes de aprovar.',
                                    f'page:{pn}',
                                    'error',
                                )
                            )
                        tables.append(
                            (
                                fitz.Rect(table.bbox),
                                {
                                    'type': 'table',
                                    'caption': 'Tabela extraída da prova; conferir cabeçalhos.',
                                    'headers': [literal(str(v or '')) for v in rows[0]],
                                    'rows': [[literal(str(v or '')) for v in row] for row in rows[1:]],
                                },
                            )
                        )
                figs = [
                    r
                    for r in figs
                    if not any(t[0].intersects(r) and (t[0] & r).get_area() > r.get_area() * 0.8 for t in tables)
                ]
                for r, block in tables:
                    entries.append(dict(type='block', block=block, page=pn, bbox=list(r), text=''))
                labelled_figs = alternative_graphics(figs, source_lines, clip)
                expanded = []
                for r, alternative in labelled_figs:
                    # Include labels touching the drawing, without absorbing nearby prose.
                    anchor = fitz.Rect(r)
                    for line in source_lines:
                        if line.get('option'):
                            continue
                        lr = fitz.Rect(line['bbox'])
                        if line['size'] <= 8.5 and lr.y0 >= anchor.y1:
                            continue
                        if not anchor.intersects(lr) and len(line['text']) > 50:
                            continue
                        if (anchor + (-3, -3, 3, 3)).intersects(lr) and len(line['text']) < 100:
                            r |= lr
                    r = (r + (-2, -2, 2, 2)) & clip
                    expanded.append(r)
                    digest = hashlib.sha256(f'{source_hash}:{pn}:{list(r)}'.encode()).hexdigest()[:16]
                    relative = Path(data['id']) / 'prepared' / f'{digest}.png'
                    target = Path(assets_root) / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), clip=r).save(target)
                    block = {
                        'type': 'image',
                        'asset': {
                            'path': '/assets/' + relative.as_posix(),
                            'alt': f"Figura extraída da questão {c['number']}, página {pn}; descrição detalhada pendente.",
                        },
                    }
                    entries.append(
                        dict(type='block', block=block, page=pn, bbox=list(r), text='', alternative=alternative)
                    )
                    positions.append({'asset': block['asset']['path'], 'page': pn, 'bbox': list(r)})
                excluded = expanded + [r for r, _ in tables]
                uncontained = [
                    l for l in source_lines if not any(r.contains(fitz.Rect(l['bbox']).tl) for r in excluded)
                ]
                aligned = Counter(round(l['bbox'][1] / 3) for l in uncontained)
                if sum(count >= 3 for count in aligned.values()) >= 2:
                    issues.append(
                        diagnostic(
                            'spatial_layout',
                            'Linhas com múltiplas colunas fora de uma tabela reconhecida: confira tabela, fórmula ou diagrama e estruture os blocos.',
                            f'page:{pn}',
                            'error',
                        )
                    )
                broken = [l['text'] for l in source_lines if garbled(l['text'])]
                if broken:
                    issues.append(
                        diagnostic(
                            'garbled_text',
                            f'{len(broken)} linha(s) com codificação de texto quebrada: a fonte do PDF não informa as letras. Prepare por outra cor legível da mesma aplicação ou corrija a codificação; não aprove.',
                            f'page:{pn}',
                            'error',
                            broken[0],
                        )
                    )
                for line in source_lines:
                    center = (
                        fitz.Rect(line['bbox']).tl + (fitz.Rect(line['bbox']).br - fitz.Rect(line['bbox']).tl) * 0.5
                    )
                    if not line.get('option') and any(r.contains(center) for r in excluded):
                        continue
                    if HEADING.match(line['text']):
                        continue
                    if not line['text']:
                        continue
                    if line['uncertain']:
                        issues.append(
                            diagnostic(
                                'spatial_math',
                                'Índice/expoente não numérico precisa de transcrição LaTeX.',
                                f'page:{pn}',
                                excerpt=line['text'],
                            )
                        )
                    if re.search(r'[√∫∑]|\b\d+\s+\d+\s*/', line['text']):
                        issues.append(
                            diagnostic(
                                'complex_math',
                                'Expressão espacial precisa de conferência e transcrição LaTeX; expoentes e frações não são inferidos de texto achatado.',
                                f'page:{pn}',
                                excerpt=line['text'],
                            )
                        )
                    entries.append({**line, 'text': literal(line['text']), 'type': 'text', 'page': pn})
            # Regions already encode column/page reading order. Do not globally
            # sort columns by y, which would interleave independent questions.
            ordered = []
            for region in regions:
                r = fitz.Rect(region['bbox'])
                pn = region['page']
                group = [
                    e
                    for e in entries
                    if e['page'] == pn
                    and r.contains(fitz.Point(e['bbox'][0] + 0.1, e['bbox'][1] + 0.1))
                    and e not in ordered
                ]
                ordered.extend(sorted(group, key=lambda e: (round(e['bbox'][1], 1), e['bbox'][0])))
            explicit = [(i, e['option']) for i, e in enumerate(ordered) if e.get('option')]
            markers = (
                explicit
                if sorted(letter for _, letter in explicit) == list('ABCDE')
                else [
                    (i, m[1])
                    for i, e in enumerate(ordered)
                    if e['type'] == 'text' and (m := re.match(r'^([ABCDE])(?:\s|$)', e['text']))
                ]
            )
            sequences = [k for k in range(len(markers) - 4) if ''.join(x[1] for x in markers[k : k + 5]) == 'ABCDE']
            choices, body = [], ordered
            graphical = {letter: [e for e in ordered if e.get('alternative') == letter] for letter in 'ABCDE'}
            if sorted(letter for _, letter in explicit) == list('ABCDE') and all(
                len(items) == 1 for items in graphical.values()
            ):
                cutoff = min(i for i, e in enumerate(ordered) if e.get('alternative') or e.get('option'))
                body = ordered[:cutoff]
                choices = [
                    {
                        'letter': letter,
                        'text': re.sub(
                            r'^[ABCDE]\s*', '', ordered[next(i for i, a in explicit if a == letter)]['text']
                        ).strip(),
                        'image': graphical[letter][0]['block']['asset'],
                    }
                    for letter in 'ABCDE'
                ]
                issues.append(
                    diagnostic(
                        'graphical_options',
                        'Alternativas gráficas segmentadas pela posição das letras A–E; confira contornos, rótulos e correspondência.',
                        'alternatives',
                    )
                )
            elif len(sequences) == 1:
                found = markers[sequences[0] : sequences[0] + 5]
                body = ordered[: found[0][0]]
                for j, (start, letter) in enumerate(found):
                    chunk = ordered[start : found[j + 1][0] if j < 4 else len(ordered)]
                    text = ' '.join(e['text'] for e in chunk if e['type'] == 'text')
                    text = re.sub(r'^[ABCDE]\s*', '', text).strip()
                    images = [
                        e['block']['asset'] for e in chunk if e['type'] == 'block' and e['block']['type'] == 'image'
                    ]
                    if len(images) > 1:
                        issues.append(
                            diagnostic(
                                'alternative_layout',
                                'Múltiplas figuras em uma alternativa: agrupe e confira manualmente.',
                                f'alternative:{letter}',
                                'error',
                            )
                        )
                    choices.append(
                        {
                            'letter': letter,
                            'text': text or ('' if images else 'Alternativa não extraída; conferir original.'),
                            'image': images[0] if images else None,
                        }
                    )
            else:
                issues.append(
                    diagnostic(
                        'alternative_layout',
                        'Não foi encontrada uma sequência inequívoca A–E. Transcreva as alternativas e remova os fragmentos do enunciado.',
                        'alternatives',
                        'error',
                    )
                )
                choices = [{'letter': a, 'text': 'Alternativa não extraída; conferir original.'} for a in 'ABCDE']
            blocks = []
            for e in body:
                if e['type'] == 'block':
                    blocks.append(e['block'])
                    continue
                text = e['text']
                # Same PDF block, ordinary body text: join physical lines. Equations
                # and small bibliography remain separate to preserve their roles.
                previous = blocks[-1] if blocks else None
                is_reaction = bool(re.search(r'→|⇌|->', text))
                if (
                    previous
                    and previous.get('_group') == (e['page'], e['group'])
                    and not is_reaction
                    and not previous.get('_reaction')
                ):
                    previous['text'] += ' ' + text
                else:
                    blocks.append(
                        {'type': 'paragraph', 'text': text, '_group': (e['page'], e['group']), '_reaction': is_reaction}
                    )
            for b in blocks:
                b.pop('_group', None)
                b.pop('_reaction', None)
            c.update(blocks=blocks, images=[], alternatives=choices, original_layout=False)
            c['statement'] = (
                '\n\n'.join(b['text'] for b in blocks if b['type'] == 'paragraph')
                or 'Conteúdo visual; conferir a figura e o original.'
            )
            c['layout'] = {
                **(c.get('layout') or {}),
                'extraction': {
                    'adapter': 'pdf-geometry-v1',
                    'source_sha256': source_hash,
                    'figures': positions,
                    'issues': issues,
                },
            }
    return data
