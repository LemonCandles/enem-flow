"""Vector graphics and images of a page, including those beside alternatives."""

import pymupdf as fitz


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
