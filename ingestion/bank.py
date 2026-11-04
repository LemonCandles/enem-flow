"""Text extraction of one downloaded PDF for the bank, without approving anything."""

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import unicodedata

import pymupdf as fitz

from ingestion.archive import SOURCE_ROOT, sha, write_json
from ingestion.pdf_headings import HEADING, QUESTION_WORD, heading_number

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/derived/archive'
VERSION = 'archive-text-v4'


def normalized(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text)).strip()


def page_lines(page):
    out = []
    for block in page.get_text('dict', flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)['blocks']:
        if block['type'] != 0:
            continue
        for line in block['lines']:
            text = ''.join(s['text'] for s in line['spans']).strip()
            out.append(
                dict(text=text, bbox=list(line['bbox']), font=line['spans'][0]['font'], size=line['spans'][0]['size'])
            )
    # Older PDFs split "Questão" and its number into adjacent text lines.
    for line in out:
        if re.fullmatch(QUESTION_WORD, line['text'], re.I):
            numbers = [
                other
                for other in out
                if re.fullmatch(r'\d{1,3}', other['text'])
                and 0 <= other['bbox'][0] - line['bbox'][2] < 45
                and abs(other['bbox'][1] - line['bbox'][1]) < 10
            ]
            if len(numbers) == 1:
                line['text'] += ' ' + numbers[0]['text']
    return out


def boundaries(doc, year):
    """Duas gerações de cabeçalho; variantes de língua nunca são descartadas."""
    pages = [page_lines(page) for page in doc]
    legacy = year < 2009 and sum(bool(HEADING.match(l['text'])) for ls in pages for l in ls) < 20
    candidates = []
    if legacy:
        # Font families support older files with 01/02 and files with plain 1/2.
        families = defaultdict(set)
        for ls in pages:
            for l in ls:
                if re.fullmatch(r'\d{1,2}\.?', l['text']) and 1 <= int(l['text'].rstrip('.')) <= 63:
                    family = re.sub(r'[ ,_-]', '', l['font']).lower().replace('mediumc', 'medium')
                    families[family].add(int(l['text'].rstrip('.')))
        if not families:
            return [], pages
        family = max(families, key=lambda k: len(families[k]))
        main = [
            l
            for ls in pages
            for l in ls
            if re.fullmatch(r'\d{1,2}\.?', l['text'])
            and re.sub(r'[ ,_-]', '', l['font']).lower().replace('mediumc', 'medium') == family
        ]
        starts = Counter(round(l['bbox'][0] / 8) * 8 for l in main)
        edges = [x for x, count in starts.items() if count >= 3]
        size = Counter(round(l['size'], 1) for l in main).most_common(1)[0][0]
    for pi, ls in enumerate(pages):
        page = doc[pi]
        found = []
        for l in ls:
            m = HEADING.match(l['text'])
            if m:
                number = heading_number(m)
            elif (
                legacy
                and re.fullmatch(r'\d{1,2}\.?', l['text'])
                and l['bbox'][1] < page.rect.height - 38
                and (
                    re.sub(r'[ ,_-]', '', l['font']).lower().replace('mediumc', 'medium') == family
                    or (
                        re.search(r'bold|heavy|demi', l['font'], re.I)
                        and l['size'] >= size * 0.95
                        and any(abs(l['bbox'][0] - x) < 8 for x in edges)
                    )
                )
            ):
                number = int(l['text'].rstrip('.'))
                if not 1 <= number <= 63:
                    continue
            else:
                continue
            found.append(dict(page=pi + 1, number=number, bbox=l['bbox']))
        # Question headings reveal column starts; prose width handles wide pages.
        wide = sum(l['bbox'][2] - l['bbox'][0] > page.rect.width * 0.68 for l in ls) > 3
        two = (
            not wide
            and any(h['bbox'][0] > page.rect.width * 0.45 for h in found)
            and any(h['bbox'][0] < page.rect.width * 0.35 for h in found)
        )
        # Most post-2009 standard exams have two columns even on sparse pages.
        if not legacy and page.rect.width < 700 and not wide:
            two = True
        columns = [(0, page.rect.width / 2), (page.rect.width / 2, page.rect.width)] if two else [(0, page.rect.width)]
        for ci, (left, right) in enumerate(columns):
            for h in sorted((h for h in found if left <= h['bbox'][0] < right), key=lambda h: h['bbox'][1]):
                candidates.append({**h, 'column': ci, 'column_bounds': [left, right]})
    if legacy:
        # Only a complete monotonic sequence is accepted as a boundary proposal.
        sequence = []
        want = 1
        for h in candidates:
            if h['number'] == want:
                sequence.append(h)
                want += 1
        if want != 64:
            return [], pages
        candidates = sequence
    return candidates, pages


def extract(record):
    path = SOURCE_ROOT / record['path']
    dest = OUTPUT / str(record['year']) / f'{record["id"]}.json'
    if dest.exists():
        previous = json.loads(dest.read_text())
        if (
            previous.get('source_sha256') == record['sha256']
            and previous.get('source_path') == record['path']
            and (
                previous.get('adapter') == VERSION
                or (previous.get('adapter') == 'archive-text-v3' and not previous.get('issues'))
            )
        ):
            return previous
    base = dict(
        source_id=record['id'],
        source_path=record['path'],
        source_sha256=record['sha256'],
        adapter=VERSION,
        year=record['year'],
        application=record['application'],
        day=record['day'],
        booklet=record['booklet'],
        variant=record['variant'],
        questions=[],
        issues=[],
    )
    try:
        if sha(path) != record['sha256']:
            raise ValueError('Hash divergente do catálogo.')
        if path.suffix == '.txt':
            raw = path.read_bytes()
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = raw.decode('cp1252')
            text = text.replace('\r\n', '\n')
            heads = list(re.finditer(r'(?im)^\s*QUEST[ÃA]O\s+(\d{1,3})\s*$', text))
            cycles = Counter()
            for i, h in enumerate(heads):
                number = int(h[1])
                cycles[number] += 1
                body = text[h.end() : heads[i + 1].start() if i + 1 < len(heads) else len(text)].strip()
                identity = hashlib.sha256(normalized(body).encode()).hexdigest()
                base['questions'].append(
                    dict(
                        occurrence_id=f'{record["id"]}-q{number}-{cycles[number]}',
                        canonical_id='enem-' + identity[:32],
                        identity_sha256=identity,
                        identity_method='text-exact-v1',
                        number=number,
                        language=record.get('language'),
                        page=None,
                        regions=[],
                        text=body,
                        has_visual=False,
                        status='extracted_unreviewed',
                        issues=[
                            'Transcrição acessível original; conferir fórmulas e marcadores antes de preparar alternativas.'
                        ],
                    )
                )
            base['pages'] = None
            if not heads:
                base['issues'].append('Nenhum cabeçalho textual de questão reconhecido no TXT.')
            write_json(dest, base)
            return base
        with fitz.open(path) as doc:
            heads, pages = boundaries(doc, record['year'])
            visual_cache = {}
            base['pages'] = len(doc)
            if not heads:
                base['issues'].append(
                    'Cabeçalhos não reconhecidos de forma completa; exige adaptação/OCR e conferência.'
                )
                write_json(dest, base)
                return base
            duplicates = Counter(h['number'] for h in heads)
            cycles = Counter()
            for index, head in enumerate(heads):
                number = head['number']
                cycles[number] += 1
                # Each region ends before the next heading in reading order.
                nxt = heads[index + 1] if index + 1 < len(heads) else None
                regions = []
                for pn in range(head['page'], (nxt['page'] if nxt else head['page']) + 1):
                    page = doc[pn - 1]
                    width = page.rect.width
                    left, right = head['column_bounds']
                    if pn == head['page']:
                        top = head['bbox'][3] + 0.1
                        end = (
                            nxt['bbox'][1] - 1
                            if nxt and nxt['page'] == pn and nxt['column'] == head['column']
                            else page.rect.height - 38
                        )
                        regions.append(dict(page=pn, bbox=[left, top, right, max(top + 1, end)]))
                        if nxt and nxt['page'] == pn and nxt['column'] > head['column']:
                            regions.append(dict(page=pn, bbox=[width / 2, 38, width, nxt['bbox'][1] - 1]))
                    else:
                        # Continuations are retained as proposals, never published.
                        stop = nxt['bbox'][1] - 1 if nxt and nxt['page'] == pn else page.rect.height - 38
                        endcol = nxt['column'] if nxt and nxt['page'] == pn else head['column']
                        regions.append(
                            dict(page=pn, bbox=[0, 38, width / 2 if endcol == 0 and right < width else width, stop])
                        )
                text = '\n\n'.join(doc[r['page'] - 1].get_text(clip=fitz.Rect(r['bbox'])) for r in regions)
                text = HEADING.sub('', text, count=1).strip()
                if record['year'] < 2009:
                    text = re.sub(r'^\s*0*' + str(number) + r'\b\s*', '', text, count=1)
                # Images/drawings are part of identity. Unresolved visual items are
                # kept separate across files rather than risk joining two graphs.
                visual = False
                for r in regions:
                    page = doc[r['page'] - 1]
                    rect = fitz.Rect(r['bbox'])
                    if r['page'] not in visual_cache:
                        visual_cache[r['page']] = (
                            [fitz.Rect(i['bbox']) for i in page.get_image_info()],
                            [d['rect'] for d in page.get_drawings()],
                        )
                    images, drawings = visual_cache[r['page']]
                    if any((i & rect).get_area() > 100 for i in images):
                        visual = True
                    # Ignore editorial horizontal rules, retain even tiny bonds,
                    # fraction bars and vector diagrams as visual dependencies.
                    if any(
                        not (d.width > rect.width * 0.75 and d.height < 12)
                        and max(d.width, d.height) > 6
                        and ((d + (-0.5, -0.5, 0.5, 0.5)) & rect).get_area() > 5
                        for d in drawings
                    ):
                        visual = True
                compact = normalized(text)
                identity = (
                    compact
                    if not visual and len(compact) >= 120
                    else f'{record["sha256"]}|{number}|{cycles[number]}|{compact}'
                )
                digest = hashlib.sha256(identity.encode()).hexdigest()
                issue = ['Texto e ordem de leitura aguardam conferência; não é conteúdo aprovado.']
                if record['year'] < 2009:
                    issue.append('Cabeçalhos numéricos e textos compartilhados exigem revisão por página.')
                if visual:
                    issue.append(
                        'Questão visual: deduplicação conservadora, conferir figuras antes de unir ocorrências.'
                    )
                language = record.get('language')
                if duplicates[number] > 1:
                    issue.append('Numeração repetida: conferir língua/versão; todas as ocorrências foram preservadas.')
                    language = language or f'variante-{cycles[number]}'
                base['questions'].append(
                    dict(
                        occurrence_id=f'{record["id"]}-q{number}-{cycles[number]}',
                        canonical_id='enem-' + digest[:32],
                        identity_sha256=digest,
                        identity_method='text-exact-v1' if not visual and len(compact) >= 120 else 'source-bound-v1',
                        number=number,
                        language=language,
                        page=head['page'],
                        regions=regions,
                        text=text,
                        has_visual=visual,
                        status='extracted_unreviewed',
                        issues=issue,
                    )
                )
            expected = (
                63
                if record['year'] < 2009
                else 45
                if record.get('section') in ('ciencias-humanas', 'ciencias-da-natureza', 'matematica', 'linguagens')
                else 90
            )
            if len({q['number'] for q in base['questions']}) != expected:
                base['issues'].append(
                    f'Quantidade de números distintos diferente da referência {expected}; conferir faltas, anulação e atendimento especializado.'
                )
    except Exception as error:
        base['issues'].append(f'{type(error).__name__}: {error}')
    write_json(dest, base)
    return base
