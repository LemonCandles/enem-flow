"""Raster channel: what the printed page shows, independently of the PDF's text and drawing objects.

Classical image processing only, on the grayscale image of a question: Otsu binarization, masks of
boxes, connected components on a coarse grid and a recursive XY-cut. The vector channel says what
the PDF declares; this channel checks that everything inked on the page is accounted for and how the
ink is arranged (stacked bands, side-by-side columns).
"""

from collections import deque

import numpy as np

# A gray lighter than this is shading behind text or figures, never ink of its own.
LIGHTEST_INK = 200


def otsu(gray):
    """Threshold that maximizes the between-class variance of the gray histogram."""
    histogram = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    total = histogram.sum()
    if not total:
        return LIGHTEST_INK
    levels = np.arange(256)
    weight = np.cumsum(histogram)
    mean = np.cumsum(histogram * levels)
    background = total - weight
    with np.errstate(divide='ignore', invalid='ignore'):
        between = (mean[-1] * weight - mean * total) ** 2 / (weight * background)
    between[~np.isfinite(between)] = 0
    return int(np.argmax(between))


def ink(gray):
    """Boolean mask of inked pixels."""
    return gray < min(otsu(gray), LIGHTEST_INK)


def box_mask(shape, boxes, pad=0):
    mask = np.zeros(shape, bool)
    for x0, y0, x1, y1 in boxes:
        mask[max(0, y0 - pad) : max(0, y1 + pad), max(0, x0 - pad) : max(0, x1 + pad)] = True
    return mask


def components(mask, cell=3):
    """Bounding boxes (x0, y0, x1, y1) and inked pixel counts of 8-connected groups of grid cells.

    The mask is reduced to cells of `cell` pixels first, so glyph fragments and anti-aliasing
    gaps join; the result is coarse by design and only used to locate unexplained ink.
    """
    rows, columns = -(-mask.shape[0] // cell), -(-mask.shape[1] // cell)
    padded = np.zeros((rows * cell, columns * cell), bool)
    padded[: mask.shape[0], : mask.shape[1]] = mask
    counts = padded.reshape(rows, cell, columns, cell).sum(axis=(1, 3))
    seen = np.zeros(counts.shape, bool)
    found = []
    for r, c in zip(*np.nonzero(counts)):
        if seen[r, c]:
            continue
        seen[r, c] = True
        queue, box, pixels = deque([(r, c)]), [c, r, c, r], 0
        while queue:
            y, x = queue.popleft()
            pixels += int(counts[y, x])
            box = [min(box[0], x), min(box[1], y), max(box[2], x), max(box[3], y)]
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < rows and 0 <= nx < columns and counts[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        queue.append((ny, nx))
        found.append(
            {
                'bbox': [
                    box[0] * cell,
                    box[1] * cell,
                    min(mask.shape[1], (box[2] + 1) * cell),
                    min(mask.shape[0], (box[3] + 1) * cell),
                ],
                'pixels': pixels,
            }
        )
    return found


def trim(mask, box):
    """The smallest box inside `box` holding all its ink, or None when it is blank."""
    x0, y0, x1, y1 = box
    zone = mask[y0:y1, x0:x1]
    rows, columns = np.nonzero(zone.any(axis=1))[0], np.nonzero(zone.any(axis=0))[0]
    if not len(rows):
        return None
    return [x0 + int(columns[0]), y0 + int(rows[0]), x0 + int(columns[-1]) + 1, y0 + int(rows[-1]) + 1]


def gaps(profile, minimum):
    """Inner runs of blank positions at least `minimum` long, as (start, end)."""
    runs, start = [], None
    for i, value in enumerate(profile):
        if not value and start is None:
            start = i
        elif value and start is not None:
            if start > 0 and i - start >= minimum:
                runs.append((start, i))
            start = None
    return runs


def split(mask, box, axis, minimum):
    """Cut a box at the blank runs of its rows (axis 'h') or columns (axis 'v')."""
    x0, y0, x1, y1 = box
    zone = mask[y0:y1, x0:x1]
    profile = zone.any(axis=1) if axis == 'h' else zone.any(axis=0)
    pieces, previous = [], 0
    for start, end in gaps(profile, minimum):
        pieces.append((previous, start))
        previous = end
    pieces.append((previous, len(profile)))
    boxes = [[x0, y0 + a, x1, y0 + b] if axis == 'h' else [x0 + a, y0, x0 + b, y1] for a, b in pieces]
    return [b for b in (trim(mask, box) for box in boxes) if b]


def xy_cut(mask, box=None, row_gap=8, column_gap=18, depth=0, max_depth=12):
    """Recursive XY-cut: alternate horizontal and vertical cuts at blank runs until no cut remains."""
    box = trim(mask, box or [0, 0, mask.shape[1], mask.shape[0]])
    if box is None:
        return None
    node = {'bbox': box, 'cut': None, 'children': []}
    if depth >= max_depth:
        return node
    for axis, minimum in (('h', row_gap), ('v', column_gap)):
        pieces = split(mask, box, axis, minimum)
        if len(pieces) > 1:
            node['cut'] = axis
            node['children'] = [
                child
                for piece in pieces
                if (child := xy_cut(mask, piece, row_gap, column_gap, depth + 1, max_depth)) is not None
            ]
            return node
    return node


def leaves(node):
    if node is None:
        return []
    if not node['children']:
        return [node]
    return [leaf for child in node['children'] for leaf in leaves(child)]


def bands(mask, row_gap=3, column_gap=18):
    """Rows of ink separated by blank lines, each with the side-by-side pieces it holds."""
    whole = trim(mask, [0, 0, mask.shape[1], mask.shape[0]])
    if whole is None:
        return []
    return [{'bbox': band, 'pieces': split(mask, band, 'v', column_gap)} for band in split(mask, whole, 'h', row_gap)]
