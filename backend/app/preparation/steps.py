"""The steps of preparing one question, applied in order over a shared `Preparation`.

Each step receives what the previous ones left and may add changes and issues. The
order matters: figures are associated only after the blocks are normalized.
"""

import copy
import re

from .notation import CHEM_CONTEXT, LATEX, normalize, tex_shape_issue
from .rules import CAPTION, CREDIT, MESSAGES


class Preparation:
    def __init__(self, content):
        self.content = content
        self.blocks = content['blocks']
        self.issues = []
        self.changes = []
        self.chemistry = bool(CHEM_CONTEXT.search(content['statement'] + ' ' + (content['labels']['discipline'] or '')))

    def issue(self, code, location, excerpt='', severity='warning'):
        row = dict(
            code=code, severity=severity, location=location, message=MESSAGES.get(code, code), excerpt=excerpt[:500]
        )
        if row not in self.issues:
            self.issues.append(row)

    def convert(self, text, location):
        result, found = normalize(text, self.chemistry)
        for code, excerpt in found:
            self.issue(code, location, excerpt, 'error' if code == 'invalid_latex' else 'warning')
        if result != text:
            self.changes.append(
                {'location': location, 'operation': 'latex', 'before': text[:1000], 'after': result[:1000]}
            )
        return result

    def inspect_tex(self, tex, location):
        if tex_shape_issue(tex):
            self.issue('invalid_latex', location, tex, 'error')
        if r'\ce{' in tex and '(I)' in tex:
            self.issue('ambiguous_liquid_state', location, tex)


def split_options(statement):
    markers = list(re.finditer(r'(?m)^\s*([ABCDE])[ \t.)]*(?:\n|[ \t])', statement))
    groups = [i for i in range(len(markers) - 4) if ''.join(m[1] for m in markers[i : i + 5]) == 'ABCDE']
    if len(groups) != 1:
        raise ValueError(
            'Não foi possível identificar uma única sequência de alternativas A–E. Informe blocos/alternativas revisados.'
        )
    found = markers[groups[0] : groups[0] + 5]
    body = statement[: found[0].start()].strip()
    choices = [
        statement[m.end() : found[i + 1].start() if i < 4 else len(statement)].strip() for i, m in enumerate(found)
    ]
    if not all(choices):
        raise ValueError('Alternativa sem texto: confira se contém uma figura ou fórmula não extraída.')
    return body, choices


def flag_unlocated_images(p):
    c = p.content
    if c['images']:
        p.issue('unlocated_images', 'images', severity='error')
    if c['original_layout'] and c['images']:
        p.issue('original_layout', 'original_layout', severity='error')


def blocks_from_statement(p):
    if p.blocks:
        return
    c = p.content
    statement = c['statement']
    if c['original_layout']:
        statement = re.sub(r'^\s*QUEST[ÃA]O\s+\d+\s*', '', statement)
        if re.search(r'(?m)^\s*A(?:[ \t.)]|$)', statement):
            statement, choices = split_options(statement)
            for a, text in zip(c['alternatives'], choices):
                a['text'] = text
    p.blocks = [{'type': 'paragraph', 'text': part} for part in re.split(r'\n\s*\n', statement) if part.strip()]


def normalize_blocks(p):
    rebuilt = []
    for i, block in enumerate(p.blocks):
        b = copy.deepcopy(block)
        loc = f'blocks[{i}]'
        if b['type'] == 'paragraph':
            # Keep separate equation/reference lines, even when extraction put them
            # in the same paragraph. Reflow ordinary line breaks only.
            pieces = re.split(
                r'\n(?=(?:[^\n]*(?:→|⇌|->)|Dispon[ií]vel em|Acesso em|https?://|[A-ZÁÉÍÓÚÇ]{3,},))', b['text']
            )
            for piece in pieces:
                raw = re.sub(r'\s*\n\s*', ' ', piece).strip()
                text = raw if CREDIT.match(raw) or b.get('role') == 'credit' else p.convert(raw, loc)
                if LATEX.fullmatch(text) and text.startswith('$'):
                    delimiter = 2 if text.startswith('$$') else 1
                    rebuilt.append({'type': 'math', 'tex': text[delimiter:-delimiter]})
                else:
                    rebuilt.append({**b, 'text': text})
        elif b['type'] == 'image':
            b['caption'] = p.convert(b.get('caption', ''), loc + '.caption')
            # Credits are bibliographic prose; do not convert abbreviations CO/NO.
            b.setdefault('credit', '')
            b.setdefault('equations', [])
            for j, tex in enumerate(b['equations']):
                p.inspect_tex(tex, loc + f'.equations[{j}]')
            if re.match(r'^(Figura|Imagem) (extra[ií]da|da questão)', b['asset']['alt']):
                p.issue('missing_description', loc + '.asset.alt', b['asset']['alt'])
            rebuilt.append(b)
        elif b['type'] == 'table':
            b['headers'] = [p.convert(value, loc + '.headers') for value in b['headers']]
            b['rows'] = [[p.convert(cell, loc + '.rows') for cell in row] for row in b['rows']]
            rebuilt.append(b)
        else:
            if b['type'] == 'math':
                p.inspect_tex(b['tex'], loc)
            rebuilt.append(b)  # Authored LaTeX is already explicit; never reinterpret it.
    p.blocks = rebuilt


def adjacent_to_figure(blocks, i, direction, removed):
    """Indexes of the blocks next to figure `i` that belong to it, walking in one direction."""
    collected, j = [], i + direction
    while 0 <= j < len(blocks) and len(collected) < 8:
        b = blocks[j]
        if j in removed:
            break
        if b['type'] == 'math' and r'\ce{' in b['tex']:
            collected.append(j)
        elif (
            b['type'] == 'paragraph'
            and b.get('role') != 'body'
            and (CREDIT.match(b['text']) or CAPTION.match(b['text']) or b.get('role') in {'credit', 'caption'})
        ):
            collected.append(j)
        elif (
            direction == 1
            and b['type'] == 'paragraph'
            and b.get('role') is None
            and len(b['text']) < 120
            and j + 1 < len(blocks)
            and blocks[j + 1]['type'] == 'paragraph'
            and CREDIT.match(blocks[j + 1]['text'])
        ):
            collected.append(j)
        else:
            break
        j += direction
    # A short title immediately before a source URL belongs to the same
    # citation group. This is inferred and explicitly marked for review.
    if direction == -1 and collected and 0 <= j < len(blocks):
        b = blocks[j]
        if b['type'] == 'paragraph' and b.get('role') is None and len(b['text']) < 120 and b['text'].endswith('.'):
            collected.append(j)
    return collected


def associate_figures(p):
    blocks = p.blocks
    removed = set()
    for i, figure in enumerate(blocks):
        if figure['type'] != 'image':
            continue
        for direction in [1, -1]:
            collected = adjacent_to_figure(blocks, i, direction, removed)
            if not collected:
                continue
            for index in sorted(collected):
                b = blocks[index]
                if b['type'] == 'math':
                    figure['equations'].append(b['tex'])
                elif CAPTION.match(b['text']) or (index == min(collected) and not CREDIT.match(b['text'])):
                    figure['caption'] = '\n'.join(filter(None, [figure['caption'], b['text']]))
                else:
                    figure['credit'] = '\n'.join(filter(None, [figure['credit'], b['text']]))
                removed.add(index)
            p.changes.append(
                {'location': f'blocks[{i}]', 'operation': 'associate_figure', 'source_blocks': sorted(collected)}
            )
            p.issue('figure_association_inferred', f'blocks[{i}]')
    p.content['blocks'] = [b for i, b in enumerate(blocks) if i not in removed]


def normalize_alternatives(p):
    for i, a in enumerate(p.content['alternatives']):
        fraction = re.fullmatch(r'\s*(\d+)\s*/\s*(\d+)\s*', a['text'])
        if fraction:
            a['text'] = r'$\frac{' + fraction[1] + '}{' + fraction[2] + '}$'
            p.changes.append({'location': f'alternatives[{i}].text', 'operation': 'fraction'})
        else:
            a['text'] = p.convert(a['text'], f'alternatives[{i}].text')


def rebuild_statement(p):
    c = p.content
    c['statement'] = '\n\n'.join(b['text'] for b in c['blocks'] if b['type'] == 'paragraph') or c['statement']
    for b in c['blocks']:
        if b['type'] == 'paragraph' and b.get('role') is None:
            b['role'] = 'credit' if CREDIT.match(b['text']) else 'body'


STEPS = (
    flag_unlocated_images,
    blocks_from_statement,
    normalize_blocks,
    associate_figures,
    normalize_alternatives,
    rebuild_statement,
)
