"""Lines of text from a PDF page, without layout decisions."""

import re
from collections import Counter

import pymupdf as fitz

from ingestion.pdf_headings import QUESTION_WORD

SUB = str.maketrans('0123456789+-−', '₀₁₂₃₄₅₆₇₈₉₊₋₋')

SUP = str.maketrans('0123456789+-−', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻')

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


# Below this size a line cannot be read on paper: booklets print security microtext
# ("ENEM2025ENEM2025…") as the rules under the header and above the footer.
MICROTEXT = 3


def watermark(line):
    """Text repeating a short unit: a vertical exam name between columns or a microtext rule.

    The microtext of a booklet may misspell one repetition ("ENEN2025"), so a few
    differing characters are tolerated. A question region may clip only part of
    the vertical line, so two repetitions are enough ("2024ENEM2024ENEM2024").
    """
    if abs(line['dir'][0]) > 0.99 and max((s['size'] for s in line['spans']), default=MICROTEXT) >= MICROTEXT:
        return False
    compact = re.sub(r'\s+', '', ''.join(s['text'] for s in line['spans']))
    if len(compact) < 12 or not re.search(r'[A-Za-z]', compact):
        return False
    return any(
        sum(compact[i] != compact[i % size] for i in range(len(compact))) <= len(compact) // 40
        for size in range(3, len(compact) // 2 + 1)
    )


# A list number followed by an unmapped bullet glyph: "1.\t\x07\u202f\u202f\x07Genética".
LIST_BULLET = re.compile(r'^(\d{1,2}[.)])[\s\u202f\u2003]*(?:[\x00-\x08\x0b\x0c\x0e-\x1f][\s\u202f\u2003]*)+')


def list_marker(text):
    return LIST_BULLET.sub(r'\1 ', text)


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
                    text=list_marker(''.join(parts).strip()),
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


def textual_table(rows):
    cells = [str(cell or '').strip() for row in rows for cell in row]
    return len(cells) >= 4 and sum(bool(cell) for cell in cells) >= max(3, len(cells) * 0.5)
