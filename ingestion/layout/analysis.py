"""Deterministic layout of one question: typed blocks, structural signature and invariants (`pdf-geometry-v3`).

The vector channel reuses the decisions of `extract_question` (regions, lines, figures, tables,
alternatives) and types each body block by typography and position: paragraph, credit, caption,
figure, table, numbered lines. The raster channel renders the question and checks, by image
processing alone, that every inked pixel is explained by some block and that text is not arranged
in columns the vector channel read as running text. A question is eligible for automatic approval
only when both channels agree and no invariant fails; question numbers and years are never used.
"""

from collections import Counter
import copy
import re

import numpy as np

from backend.app.preparation.rules import CAPTION, CREDIT
from ingestion.exam_pdf import extract_question, lines
from ingestion.exam_pdf.text import diagnostic
from ingestion.pdf_headings import HEADING

from . import raster
from .render import furniture_mask, page_clip, render_question, to_pixels

ADAPTER = 'pdf-geometry-v3'

# Extraction diagnostics that already mean the vector channel could not structure the question.
EXTRACTION_ERRORS = {'whole_region_image', 'merged_table_cells', 'spatial_layout', 'garbled_text', 'alternative_layout'}
# Structures the content contract cannot represent yet: their questions stay in the residual queue.
UNSUPPORTED = {
    'P#': 'Texto com linhas numeradas: o contrato de conteúdo não representa a numeração das linhas.',
    'P|P': 'Textos lado a lado: o contrato de conteúdo não representa colunas de texto.',
}
# Raster thresholds, in pixels at the render resolution (150 dpi: 1 pt ≈ 2.1 px).
MIN_COMPONENT = 30
COLUMN_GAP = 18
NEAR_TABLE = 25
# Vector thresholds, in PDF points.
GUTTER = 8  # blank space between blocks printed side by side; a line split by an inline fraction has none
NUMBER_COLUMN = 3  # x tolerance of a column of line numbers


def union(boxes):
    boxes = list(boxes)
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def body_style(entries):
    """(font, size) that prints most characters of the question."""
    weights = Counter()
    for entry in entries:
        if entry['type'] == 'text':
            weights[(entry.get('font', ''), round(entry.get('size', 0), 1))] += len(entry['text'])
    return weights.most_common(1)[0][0] if weights else ('', 0)


def numbered(entries):
    return all(entry['type'] == 'text' and re.fullmatch(r'\d{1,3}', entry['text'].strip()) for entry in entries)


def line_numbers(blocks):
    """Keep `numbers` only for a column of increasing integers beside the text they number.

    Line numbering is at least three integers aligned in x, increasing downwards, next to a paragraph
    whose height they cover. An isolated digit (numerator, exponent, table cell) is ordinary text.
    """
    candidates = [b for b in blocks if b['type'] == 'numbers']
    demoted = []
    for block in candidates:
        column = sorted(
            (
                other
                for other in candidates
                if other['page'] == block['page'] and abs(other['bbox'][0] - block['bbox'][0]) <= NUMBER_COLUMN
            ),
            key=lambda other: other['bbox'][1],
        )
        values = [int(e['text'].strip()) for other in column for e in other['entries']]
        top, bottom = column[0]['bbox'][1], column[-1]['bbox'][3]
        beside = any(
            other['type'] == 'paragraph'
            and other['page'] == block['page']
            and other['bbox'][0] >= block['bbox'][2]
            and other['bbox'][1] < bottom
            and other['bbox'][3] > top
            for other in blocks
        )
        if len(values) < 3 or values != sorted(set(values)) or not beside:
            demoted.append(block)
    for block in demoted:
        block['type'] = 'paragraph'


def vertical_overlap(a, b):
    return max(0, min(a[3], b[3]) - max(a[1], b[1])) / max(1e-6, min(a[3] - a[1], b[3] - b[1]))


def horizontal_overlap(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) / max(1e-6, min(a[2] - a[0], b[2] - b[0]))


def side_by_side(a, b):
    """Blocks on the same lines, each to one side of the other."""
    return (
        a['page'] == b['page']
        and vertical_overlap(a['bbox'], b['bbox']) > 0.5
        and horizontal_overlap(a['bbox'], b['bbox']) < 0.1
    )


def printed_beside(a, b):
    """Side by side with a blank gutter and content on both sides.

    A line split around an inline fraction has no gutter, and the loose glyphs of a formula
    (digits, brackets, single letters) are not text printed in columns.
    """

    def substantial(block):
        return block['type'] in {'image', 'table'} or len(re.sub(r'\s', '', block.get('text', ''))) >= 3

    gap = max(a['bbox'][0], b['bbox'][0]) - min(a['bbox'][2], b['bbox'][2])
    return side_by_side(a, b) and gap >= GUTTER and substantial(a) and substantial(b)


def runs_by_size(entries, tolerance=0.8):
    """Consecutive lines of one PDF text block split where the font size changes (credit, then body)."""
    runs = []
    for entry in entries:
        if runs and abs(runs[-1][-1].get('size', 0) - entry.get('size', 0)) <= tolerance:
            runs[-1].append(entry)
        else:
            runs.append([entry])
    return runs


def typed_blocks(extraction):
    """Body and alternative blocks in reading order, each with page, box and the entries it came from."""
    blocks = []
    _, body_size = body_style(extraction['ordered'])
    for block, entries in extraction['parts']:
        if block['type'] == 'image':
            box, page = union(e['bbox'] for e in entries), entries[0]['page']
            blocks.append(dict(type='image', page=page, bbox=box, asset=block['asset']['path'], entries=entries))
            continue
        if block['type'] == 'table':
            box, page = union(e['bbox'] for e in entries), entries[0]['page']
            blocks.append(dict(type='table', page=page, bbox=box, table=block, entries=entries))
            continue
        for run in runs_by_size(entries):
            text = ' '.join(e['text'] for e in run)
            size = max(e.get('size', 0) for e in run)
            previous = blocks[-1] if blocks else None
            kind = 'paragraph'
            if numbered(run):
                kind = 'numbers'
            elif CREDIT.match(text):
                kind = 'credit'
            elif (
                previous
                and previous['type'] == 'credit'
                and size < body_size - 0.5
                and abs(size - previous['size']) <= 0.8
                and len(text) < 160
            ):
                kind = 'credit'  # the second line of a reference printed as its own text block
            elif CAPTION.match(text) and len(text) < 160:
                kind = 'caption'
            blocks.append(
                dict(
                    type=kind,
                    page=run[0]['page'],
                    bbox=union(e['bbox'] for e in run),
                    text=text,
                    size=size,
                    entries=run,
                )
            )
    for choice in extraction['choices']:
        letter, entries = choice['letter'], extraction['options'].get(choice['letter'], [])
        texts = [e for e in entries if e['type'] == 'text']
        images = [e for e in entries if e['type'] == 'block' and e['block']['type'] == 'image']
        if texts or not images:
            blocks.append(
                dict(
                    type='alternative',
                    alternative=letter,
                    page=(texts or entries or [{'page': 0}])[0]['page'],
                    bbox=union(e['bbox'] for e in texts) if texts else [0, 0, 0, 0],
                    text=f'{letter} {choice["text"]}'.strip(),
                    entries=texts,
                )
            )
        for image in images:
            blocks.append(
                dict(
                    type='image',
                    alternative=letter,
                    page=image['page'],
                    bbox=image['bbox'],
                    asset=image['block']['asset']['path'],
                    entries=[image],
                )
            )
        if images and not texts:
            # A graphical alternative still needs its letter marker; the figure carries the content.
            blocks.append(
                dict(
                    type='alternative', alternative=letter, page=images[0]['page'], bbox=images[0]['bbox'], text=letter
                )
            )
    line_numbers([b for b in blocks if not b.get('alternative')])
    for order, block in enumerate(blocks):
        block['id'], block['order'] = f'b{order}', order
        block.setdefault('alternative', None)
    return blocks


def figure_links(blocks, gap=40):
    """Captions and credits printed next to a figure, by reading order and geometry together."""
    body = [b for b in blocks if not b['alternative']]
    links, used = [], set()
    for i, block in enumerate(body):
        if block['type'] not in {'caption', 'credit'}:
            continue
        candidates = []
        for direction in (-1, 1):
            j = i + direction
            while 0 <= j < len(body) and body[j]['type'] in {'caption', 'credit'}:
                j += direction
            if not 0 <= j < len(body) or body[j]['type'] != 'image':
                continue
            figure = body[j]
            if figure['page'] != block['page'] or horizontal_overlap(figure['bbox'], block['bbox']) < 0.3:
                continue
            distance = max(figure['bbox'][1] - block['bbox'][3], block['bbox'][1] - figure['bbox'][3])
            if distance <= gap:
                candidates.append((distance, direction, figure))
        if candidates:
            _, _, figure = min(candidates, key=lambda c: (c[0], c[1]))
            links.append({'source': block['id'], 'target': figure['id'], 'relation': block['type'] + '_of'})
            used.add(block['id'])
    return links


def alternatives_token(blocks):
    figures = [b for b in blocks if b['alternative'] and b['type'] == 'image']
    markers = [b for b in blocks if b['alternative'] and b['type'] == 'alternative']
    if sorted(b['alternative'] for b in markers) != list('ABCDE'):
        return 'ALT:?'
    if not figures:
        rows = len({round(b['bbox'][1] / 4) for b in markers})
        return 'ALT:texto' if rows == 5 else 'ALT:linha'
    columns = []
    for figure in sorted(figures, key=lambda b: b['bbox'][0]):
        if not columns or figure['bbox'][0] - columns[-1] > 40:
            columns.append(figure['bbox'][0])
    if len(figures) != 5:
        return 'ALT:misto'
    return 'ALT:grade' if len(columns) > 1 else 'ALT:figura'


TOKENS = {'paragraph': 'P', 'credit': 'Cr', 'caption': 'Cap', 'image': 'F', 'table': 'T', 'numbers': 'N'}


def signature(blocks, links, regions):
    """Canonical structural string: body tokens in reading order, side by side joined by '|'."""
    linked = {link['source'] for link in links}
    body = [b for b in blocks if not b['alternative'] and b['id'] not in linked]
    tokens = []
    for i, block in enumerate(body):
        token = TOKENS[block['type']]
        if block['type'] == 'image' and any(link['target'] == block['id'] for link in links):
            relations = {link['relation'] for link in links if link['target'] == block['id']}
            token += ''.join(
                suffix for relation, suffix in (('caption_of', '+Cap'), ('credit_of', '+Cr')) if relation in relations
            )
        previous = body[i - 1] if i else None
        if previous and printed_beside(previous, block):
            tokens[-1] = tokens[-1] + '|' + token
        else:
            tokens.append(token)
    # Canonical form: line numbers and the text they number are one 'P#'; text beside text is 'P|P';
    # repetitions do not change the layout (two paragraphs or ten are 'P').
    canonical = []
    for token in tokens:
        parts = set(token.split('|'))
        if 'N' in parts and parts <= {'P', 'N', 'Cr'}:
            token = 'P#'
        elif '|' in token and parts <= {'P', 'Cr'}:
            token = 'P|P'
        if token == 'P' and canonical and canonical[-1] == 'P#':
            continue
        if token == 'P#' and canonical and canonical[-1] == 'P':
            canonical[-1] = 'P#'
        if not canonical or canonical[-1] != token:
            canonical.append(token)
    shared = any(region.get('shared_for') for region in regions)
    return ' '.join((['S'] if shared else []) + canonical + [alternatives_token(blocks)])


def raster_channel(doc, regions, extraction, blocks, background):
    """Image, placements and the raster findings: unexplained ink, stray rules and text columns."""
    image, placements = render_question(doc, regions)
    mask = raster.ink(image)
    if background is not None:
        mask &= ~furniture_mask(image.shape, placements, background)
    text_boxes, headings = [], []
    for region in regions:
        page, clip = page_clip(doc, region)
        for block in page.get_text('dict', clip=clip)['blocks']:
            for line in block.get('lines', []):
                box = to_pixels(placements, region['page'], line['bbox'])
                if box is None:
                    continue
                text_boxes.append(box)
                if HEADING.match(''.join(span['text'] for span in line['spans']).strip()):
                    headings.append(box)
    solid = [
        box
        for e in extraction['ordered']
        if e['type'] == 'block' and (box := to_pixels(placements, e['page'], e['bbox'])) is not None
    ]
    tables = [
        box for b in blocks if b['type'] == 'table' and (box := to_pixels(placements, b['page'], b['bbox'])) is not None
    ]
    explained = raster.box_mask(mask.shape, text_boxes + solid, pad=2)
    residual = mask & ~explained
    blobs, near_tables, rules = [], [], []
    height, width = mask.shape
    for component in raster.components(residual):
        if component['pixels'] <= MIN_COMPONENT:
            continue
        x0, y0, x1, y1 = component['bbox']
        if any(y0 < h[3] and y1 > h[1] for h in headings):
            continue  # the rule printed beside "QUESTÃO n"
        w, h = x1 - x0, y1 - y0
        if max(w, h) >= 15 * min(w, h) or min(w, h) <= 4:
            if w >= 0.4 * width or y0 <= 3 or y1 >= height - 3:
                continue  # separators between questions and rules cut at the region edge
            if any(
                x0 < t[2] + NEAR_TABLE and x1 > t[0] - NEAR_TABLE and y0 < t[3] + NEAR_TABLE and y1 > t[1] - NEAR_TABLE
                for t in tables
            ):
                near_tables.append(component)
            else:
                rules.append(component)
        else:
            blobs.append(component)
    # Columns of text: bands of text ink cut by wide blank gaps, outside figures, tables and headings.
    text_mask = mask & ~raster.box_mask(mask.shape, solid + headings, pad=3)
    markers = [
        box
        for b in blocks
        for e in b.get('entries', [])
        if b['type'] in {'alternative', 'numbers'}
        and e['type'] == 'text'
        and (box := to_pixels(placements, e['page'], e['bbox'])) is not None
    ]
    beside = [
        box
        for b in blocks
        if b['type'] != 'alternative'
        for box in [to_pixels(placements, b['page'], b['bbox'])]
        if box is not None and any(o is not b and side_by_side(o, b) for o in blocks if o['type'] != 'alternative')
    ]
    columns = []
    for band in raster.bands(text_mask, row_gap=2, column_gap=COLUMN_GAP):
        # Vertical rules between page columns are not text; a column of text is wider than a stroke.
        if sum(piece[2] - piece[0] >= 6 for piece in band['pieces']) < 2:
            continue
        x0, y0, x1, y1 = band['bbox']
        if any(y0 < m[3] and y1 > m[1] for m in markers + beside):
            continue
        columns.append(band['bbox'])
    return image, placements, mask, dict(blobs=blobs, near_tables=near_tables, rules=rules, columns=columns)


def invariants(doc, regions, extraction, blocks, links, sig, findings):
    """Every check that must pass for automatic approval; `error` blocks it, `warning` is recorded."""
    issues = []
    for issue in extraction['issues']:
        if issue['code'] in EXTRACTION_ERRORS and issue.get('severity') == 'error':
            issues.append(issue)
    if findings['blobs']:
        issues.append(
            diagnostic(
                'unassigned_ink',
                f'{len(findings["blobs"])} área(s) impressa(s) fora de qualquer bloco: figura, símbolo ou seta não recortados.',
                'raster',
                'error',
            )
        )
    if findings['near_tables']:
        issues.append(
            diagnostic(
                'table_incomplete',
                'Traços de grade fora do recorte da tabela: linhas ou colunas podem ter ficado de fora.',
                'raster',
                'error',
            )
        )
    if findings['rules']:
        issues.append(
            diagnostic(
                'stray_rule',
                f'{len(findings["rules"])} traço(s) curto(s) fora de blocos: sublinhado, barra de fração ou seta.',
                'raster',
            )
        )
    if len(findings['columns']) >= 2:
        issues.append(
            diagnostic(
                'channel_disagreement',
                'A imagem mostra texto em colunas que a camada de texto lê como corrido.',
                'raster',
                'error',
            )
        )
    # Text conservation: every positioned line reaches exactly one block.
    assigned = Counter(id(e) for _, entries in extraction['parts'] for e in entries)
    assigned.update(id(e) for entries in extraction['options'].values() for e in entries)
    lost = [e for e in extraction['ordered'] if e['type'] == 'text' and assigned[id(e)] != 1]
    if lost:
        issues.append(
            diagnostic(
                'text_not_assigned',
                f'{len(lost)} linha(s) de texto sem bloco ou em mais de um bloco.',
                'text',
                'error',
                lost[0]['text'],
            )
        )
    # A figure crop must not swallow running text in the body style.
    font, size = body_style(extraction['ordered'])
    for figure in [b for b in blocks if b['type'] == 'image']:
        page, clip = page_clip(doc, {'page': figure['page'], 'bbox': figure['bbox']})
        inside = [
            line
            for line in lines(page, clip)
            if line.get('font') == font
            and abs(line.get('size', 0) - size) < 0.6
            and (line['bbox'][2] - line['bbox'][0]) > 0.5 * (figure['bbox'][2] - figure['bbox'][0])
            and len(line['text']) > 40
        ]
        if len(inside) >= 3:
            issues.append(
                diagnostic(
                    'figure_swallows_text',
                    'Recorte de figura contém parágrafos no estilo do texto: o texto ficaria só na imagem.',
                    figure['id'],
                    'error',
                    inside[0]['text'],
                )
            )
    for token, message in UNSUPPORTED.items():
        if token in sig.split():
            issues.append(diagnostic('unsupported_layout', message, token, 'error'))
    if 'ALT:?' in sig or 'ALT:misto' in sig:
        issues.append(
            diagnostic('alternative_layout', 'Alternativas sem estrutura A–E reconhecida.', 'alternatives', 'error')
        )
    return issues


def analyze(doc, content, exam_id, source_hash, assets_root, background=None):
    """Layout of one question: blocks, links, signature, findings and issues, plus its image."""
    regions = (content.get('layout') or {}).get('blocks', [])
    extraction = extract_question(doc, copy.deepcopy(content), source_hash, exam_id, assets_root)
    blocks = typed_blocks(extraction)
    links = figure_links(blocks)
    sig = signature(blocks, links, regions)
    image, placements, mask, findings = raster_channel(doc, regions, extraction, blocks, background)
    issues = invariants(doc, regions, extraction, blocks, links, sig, findings)
    math = sorted({i['code'] for i in extraction['issues'] if i['code'] in {'spatial_math', 'complex_math'}})
    return dict(
        number=content['number'],
        regions=regions,
        extraction=extraction,
        blocks=blocks,
        links=links,
        signature=sig,
        findings=findings,
        issues=issues,
        residual_for_humans=math,
        image=image,
        placements=placements,
        ink=mask,
    )


def overlay(result):
    """RGB image of the question with block boxes and the raster findings drawn over it."""
    image, placements = result['image'], result['placements']
    color = np.stack([image] * 3, axis=-1).copy()
    palette = {
        'paragraph': (40, 90, 200),
        'credit': (120, 120, 120),
        'caption': (0, 150, 150),
        'image': (0, 160, 60),
        'table': (150, 90, 0),
        'alternative': (160, 0, 160),
        'numbers': (220, 120, 0),
    }

    def frame(box, rgb, width=2):
        x0, y0, x1, y1 = box
        color[y0 : y0 + width, x0:x1] = rgb
        color[max(y0, y1 - width) : y1, x0:x1] = rgb
        color[y0:y1, x0 : x0 + width] = rgb
        color[y0:y1, max(x0, x1 - width) : x1] = rgb

    for block in result['blocks']:
        box = to_pixels(placements, block['page'], block['bbox']) if block['page'] else None
        if box:
            frame(box, palette[block['type']])
    for key, rgb in (('blobs', (230, 0, 0)), ('near_tables', (230, 120, 0)), ('rules', (230, 200, 0))):
        for component in result['findings'][key]:
            x0, y0, x1, y1 = component['bbox']
            color[y0:y1, x0:x1, 1:] //= 3
            frame(component['bbox'], rgb, 1)
    for box in result['findings']['columns']:
        frame(box, (255, 0, 120), 1)
    return color
