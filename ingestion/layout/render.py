"""One image per question: its regions rendered in reading order and stacked, with the way back to the PDF.

A question can span columns and pages. Each region becomes a horizontal strip of the same image,
separated by a white gap; `placements` records where each strip came from, so any PDF box of the
question maps to pixels and back without ambiguity.
"""

import numpy as np
import pymupdf as fitz

DPI = 150
GAP = 16


def page_clip(doc, region):
    """The region inside its page; column regions may reach a little past the page edge."""
    page = doc[region['page'] - 1]
    return page, fitz.Rect(region['bbox']) & page.rect


def gray(pix):
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.stride)[:, : pix.width]


def text_extent(doc, parity, margin=6):
    """Horizontal extent (pt) of the readable horizontal text on the pages of one parity."""
    from ingestion.exam_pdf import watermark

    lefts, rights = [], []
    for page in doc:
        if page.number % 2 != parity:
            continue
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                if abs(line['dir'][0]) > 0.99 and not watermark(line) and any(s['size'] >= 6 for s in line['spans']):
                    lefts.append(line['bbox'][0])
                    rights.append(line['bbox'][2])
    if not lefts:
        return None
    return float(np.percentile(lefts, 1)) - margin, float(np.percentile(rights, 99)) + margin


def furniture(doc, dpi=DPI, share=0.5):
    """Ink that belongs to the page, not to a question: side tabs, footers, frames, security microtext.

    Two background models, per parity (booklets mirror odd and even pages): a pixel inked on at
    least `share` of the pages, and everything outside the horizontal extent of the readable text,
    where area tabs and microtext change position from page to page. Returns {parity: page mask}.
    """
    from .raster import ink

    counts, totals = {}, {}
    for page in doc:
        mask = ink(gray(page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY, alpha=False)))
        parity = page.number % 2
        if parity in counts:
            rows = min(counts[parity].shape[0], mask.shape[0])
            columns = min(counts[parity].shape[1], mask.shape[1])
            counts[parity] = counts[parity][:rows, :columns] + mask[:rows, :columns]
        else:
            counts[parity] = mask.astype(np.int32)
        totals[parity] = totals.get(parity, 0) + 1
    models = {}
    for parity, count in counts.items():
        model = count >= max(2, share * totals[parity])
        extent = text_extent(doc, parity)
        if extent:
            scale = dpi / 72
            model[:, : max(0, int(extent[0] * scale))] = True
            model[:, int(np.ceil(extent[1] * scale)) :] = True
        models[parity] = model
    return models


def render_question(doc, regions, dpi=DPI):
    """Grayscale image (rows × columns, uint8) of the regions stacked vertically, and their placements."""
    tiles, placements, top = [], [], 0
    for region in regions:
        page, clip = page_clip(doc, region)
        if clip.is_empty:
            raise ValueError('Região fora da página.')
        pix = page.get_pixmap(dpi=dpi, clip=clip, colorspace=fitz.csGRAY, alpha=False)
        tile = gray(pix)
        tiles.append(tile)
        placements.append(
            {
                'page': region['page'],
                'bbox': list(clip),
                'top': top,
                'size': [pix.width, pix.height],
                'scale': [pix.width / clip.width, pix.height / clip.height],
            }
        )
        top += pix.height + GAP
    image = np.full((top - GAP, max(t.shape[1] for t in tiles)), 255, np.uint8)
    for tile, placement in zip(tiles, placements):
        image[placement['top'] : placement['top'] + tile.shape[0], : tile.shape[1]] = tile
    return image, placements


def furniture_mask(shape, placements, background):
    """The page furniture of each strip, placed in the question image."""
    result = np.zeros(shape, bool)
    for placement in placements:
        model = background.get((placement['page'] - 1) % 2)
        if model is None:
            continue
        left = int(round(placement['bbox'][0] * placement['scale'][0]))
        upper = int(round(placement['bbox'][1] * placement['scale'][1]))
        width, height = placement['size']
        piece = model[upper : upper + height, left : left + width]
        result[placement['top'] : placement['top'] + piece.shape[0], : piece.shape[1]] = piece
    return result


def placement_of(placements, page, bbox):
    """The strip whose region contains the center of a PDF box, or None."""
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    for placement in placements:
        x0, y0, x1, y1 = placement['bbox']
        if placement['page'] == page and x0 <= cx <= x1 and y0 <= cy <= y1:
            return placement
    return None


def to_pixels(placements, page, bbox):
    """Pixel box (x0, y0, x1, y1) of a PDF box, clipped to its strip; None outside every region."""
    placement = placement_of(placements, page, bbox)
    if placement is None:
        return None
    x0, y0 = placement['bbox'][:2]
    sx, sy = placement['scale']
    width, height = placement['size']
    left = min(width, max(0, int((bbox[0] - x0) * sx)))
    right = min(width, max(0, int(np.ceil((bbox[2] - x0) * sx))))
    upper = min(height, max(0, int((bbox[1] - y0) * sy)))
    lower = min(height, max(0, int(np.ceil((bbox[3] - y0) * sy))))
    return left, placement['top'] + upper, right, placement['top'] + lower


def to_pdf(placements, box):
    """PDF page and box of a pixel box that lies in one strip."""
    for placement in placements:
        width, height = placement['size']
        if placement['top'] <= box[1] < placement['top'] + height:
            x0, y0 = placement['bbox'][:2]
            sx, sy = placement['scale']
            top = placement['top']
            return placement['page'], [
                x0 + box[0] / sx,
                y0 + (box[1] - top) / sy,
                x0 + min(box[2], width) / sx,
                y0 + (min(box[3], top + height) - top) / sy,
            ]
    return None


def save_png(image, path, color=None):
    """Write a grayscale image, or an RGB one when `color` (rows × columns × 3) is given."""
    data = image if color is None else color
    space = fitz.csGRAY if data.ndim == 2 else fitz.csRGB
    fitz.Pixmap(space, data.shape[1], data.shape[0], np.ascontiguousarray(data).tobytes(), False).save(path)
