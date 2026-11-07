"""Geometry shared by the layout adapter and the experiments: overlap, option markers, block rules and tables.

Only observable properties of the PDF enter here (text, font size, boxes, table cells); question
numbers, years and annotations never do.
"""

import re

import pymupdf as fitz


def iou(a, b):
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    overlap = max(0, right - left) * max(0, bottom - top)
    area = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - overlap
    return overlap / area if area > 0 else 0.0


def match_blocks(expected, predicted, threshold):
    """Pareamento geométrico um-a-um, sem usar classes para escolher os pares."""
    pairs = sorted(
        (
            (iou(a['bbox'], b['bbox']), i, j)
            for i, a in enumerate(expected)
            for j, b in enumerate(predicted)
            if a['page'] == b['page']
        ),
        reverse=True,
    )
    used_a, used_b, matches = set(), set(), []
    for overlap, i, j in pairs:
        if overlap >= threshold and i not in used_a and j not in used_b:
            used_a.add(i)
            used_b.add(j)
            matches.append((i, j, overlap))
    return matches


def option_letter(text):
    match = re.match(r'^\s*([ABCDE])(?:\t|\s+[ABCDE]\s|[.)]\s|\s+|$)', text)
    return match[1] if match else None


def rule_type(text, size):
    if option_letter(text):
        return 'alternative'
    if re.search(r'Dispon[ií]vel em|Acesso em|adaptado|Fonte:|https?://', text) or (size < 8.5 and ',' in text):
        return 'credit'
    if re.match(r'^(Figura|Gr[aá]fico|Esquema)\b', text):
        return 'caption'
    if len(text) < 100 and re.search(r'[=∑∫√]', text) and len(text.split()) < 14:
        return 'math'
    return 'paragraph'


def table_structure(page, table):
    """Preserva a geometria real das células mescladas; não propaga texto por palpite."""
    rects = [fitz.Rect(cell) for cell in table.cells if cell]
    xs = sorted({round(v, 1) for rect in rects for v in (rect.x0, rect.x1)})
    ys = sorted({round(v, 1) for rect in rects for v in (rect.y0, rect.y1)})
    cells = []
    for rect in rects:
        x0, x1, y0, y1 = map(lambda v: round(v, 1), [rect.x0, rect.x1, rect.y0, rect.y1])
        cells.append(
            {
                'bbox': list(rect),
                'row': ys.index(y0),
                'column': xs.index(x0),
                'rowspan': ys.index(y1) - ys.index(y0),
                'colspan': xs.index(x1) - xs.index(x0),
                'text': page.get_text(clip=rect).strip(),
            }
        )
    return {
        'rows': max(0, len(ys) - 1),
        'columns': max(0, len(xs) - 1),
        'cells': cells,
        'has_spans': any(c['rowspan'] > 1 or c['colspan'] > 1 for c in cells),
        'review_status': 'proposed',
    }
