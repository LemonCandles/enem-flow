"""Versioned conversion of an experimental layout proposal into the published content blocks.

The adapter is a pure function of the proposal, the target version and its source. It refuses
a different source or version, a missing asset, an invalid link, an incomplete order, missing
alternatives or merged table cells, and never guesses. A refused proposal changes nothing:
the published blocks stay as they are.
"""

from collections import Counter
import copy
import hashlib
import json
import re
import unicodedata

from pydantic import ValidationError

from ..core.config import ROOT
from ..preparation import content_issues
from ..preparation.notation import tex_shape_issue
from ..schemas import QuestionContent

ADAPTER_VERSION = 'layout-adapter-v1'


class LayoutRejected(Exception):
    def __init__(self, errors):
        super().__init__('; '.join(errors))
        self.errors = errors


def version_fingerprint(content):
    """The content a proposal was made for, without the layout audit."""
    data = QuestionContent.model_validate(content).model_dump()
    data.pop('layout', None)
    return hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    ).hexdigest()


def words(content):
    """Normalized words of everything a student reads, for the comparison with the published text."""
    parts = [content.get('statement') or '']
    for block in content.get('blocks') or []:
        parts += [block.get('text', ''), block.get('tex', ''), block.get('caption', ''), block.get('credit', '')]
        parts += [cell for row in [block.get('headers', []), *block.get('rows', [])] for cell in row]
    parts += [a['text'] for a in content['alternatives']]
    text = unicodedata.normalize('NFKD', ' '.join(parts)).encode('ascii', 'ignore').decode().lower()
    return Counter(re.findall(r'[a-z0-9]+', text))


def figures(content):
    blocks = sum(b['type'] == 'image' for b in content.get('blocks') or [])
    return blocks + len(content.get('images') or []) + sum(bool(a.get('image')) for a in content['alternatives'])


def compare(published, proposed):
    before, after = words(published), words(proposed)
    total = sum(before.values()) or 1
    missing, extra = before - after, after - before
    return {
        'published_words': sum(before.values()),
        'proposed_words': sum(after.values()),
        'missing_words': sum(missing.values()),
        'extra_words': sum(extra.values()),
        'preserved_ratio': round(1 - sum(missing.values()) / total, 4),
        'missing_sample': sorted(missing)[:30],
        'extra_sample': sorted(extra)[:30],
        'blocks_before': len(published.get('blocks') or []),
        'blocks_after': len(proposed.get('blocks') or []),
        'figures_before': figures(published),
        'figures_after': figures(proposed),
    }


def asset_exists(path):
    root = (ROOT / 'data/assets').resolve()
    target = (ROOT / 'data' / path.lstrip('/')).resolve()
    return path.startswith('/assets/') and target.is_relative_to(root) and target.is_file()


def table_block(block, structures, caption):
    structure = next(
        (s for s in structures if s.get('page') == block['page'] and _same_box(s.get('bbox'), block['bbox'])), None
    )
    if structure is None:
        return None, f'Tabela {block["id"]} sem estrutura correspondente.'
    if structure.get('has_spans'):
        return None, f'Tabela {block["id"]} tem células mescladas; a conversão exige revisão manual.'
    rows, columns = structure.get('rows', 0), structure.get('columns', 0)
    grid = [[None] * columns for _ in range(rows)]
    for cell in structure.get('cells', []):
        r, c = cell.get('row'), cell.get('column')
        if (
            not (isinstance(r, int) and isinstance(c, int) and 0 <= r < rows and 0 <= c < columns)
            or grid[r][c] is not None
        ):
            return None, f'Tabela {block["id"]} com células fora da grade ou repetidas.'
        grid[r][c] = cell.get('text', '').strip()
    if rows < 2 or columns < 1 or any(v is None for row in grid for v in row):
        return None, f'Tabela {block["id"]} incompleta.'
    return {'type': 'table', 'headers': grid[0], 'rows': grid[1:], 'caption': caption or 'Tabela'}, None


def _same_box(a, b, tolerance=2):
    return a is not None and len(a) == 4 and all(abs(x - y) <= tolerance for x, y in zip(a, b))


def convert(proposal, content, source_sha256):
    """New content for the version, or LayoutRejected with every reason found."""
    errors = []
    if proposal['source_sha256'] != source_sha256:
        errors.append('A fonte da proposta difere do caderno da prova.')
    if proposal['content_sha256'] != version_fingerprint(content):
        errors.append('A proposta foi feita para outro conteúdo da questão.')
    blocks = proposal['blocks']
    ids = [b['id'] for b in blocks]
    if len(set(ids)) != len(ids):
        errors.append('Há blocos com o mesmo identificador.')
    if sorted(b['order'] for b in blocks) != list(range(len(blocks))):
        errors.append('A ordem de leitura está incompleta ou repetida.')
    by_id = {b['id']: b for b in blocks}
    attached = {}
    for link in proposal['links']:
        source, target = by_id.get(link['source']), by_id.get(link['target'])
        expected = 'caption' if link['relation'] == 'caption_of' else 'credit'
        if source is None or target is None or source['type'] != expected or target['type'] != 'image':
            errors.append(f'Vínculo inválido: {link["source"]} → {link["target"]}.')
            continue
        if source['id'] in attached:
            errors.append(f'O bloco {source["id"]} está vinculado a mais de uma figura.')
        attached[source['id']] = (target['id'], link['relation'])
    for block in blocks:
        if block['type'] == 'image':
            if not block.get('asset') or not asset_exists(block['asset']):
                errors.append(f'Figura {block["id"]} sem recurso salvo em data/assets.')
        elif block['type'] == 'math' and (not block['text'].strip() or tex_shape_issue(block['text'])):
            errors.append(f'Fórmula {block["id"]} com LaTeX vazio ou incompleto.')
        elif block['type'] != 'table' and not block['text'].strip():
            errors.append(f'Bloco {block["id"]} sem texto.')
        if block['alternative'] and block['type'] not in {'alternative', 'image'}:
            errors.append(f'Bloco {block["id"]} de alternativa precisa ser marcador ou figura.')
    letters = Counter(b['alternative'] for b in blocks if b['type'] == 'alternative' and b['alternative'])
    if sorted(letters) != list('ABCDE') or any(n != 1 for n in letters.values()):
        errors.append('As alternativas precisam aparecer uma vez cada, de A a E.')
    if errors:
        raise LayoutRejected(errors)

    ordered = sorted(blocks, key=lambda b: b['order'])
    images = {b['id']: b for b in ordered if b['type'] == 'image' and not b['alternative']}
    captions = {target: [] for target in images}
    credits = {target: [] for target in images}
    for source_id, (target_id, relation) in attached.items():
        if target_id in images:
            (captions if relation == 'caption_of' else credits)[target_id].append(by_id[source_id]['text'])
    previous_alt = {}
    for block in content.get('blocks') or []:
        if block['type'] == 'image':
            previous_alt[block['asset']['path']] = block['asset'].get('alt', '')
    new_blocks = []
    for block in ordered:
        if block['alternative'] or block['id'] in attached:
            continue
        kind = block['type']
        if kind in {'paragraph', 'caption'}:
            new_blocks.append({'type': 'paragraph', 'text': block['text'].strip(), 'role': 'body'})
        elif kind == 'credit':
            new_blocks.append({'type': 'paragraph', 'text': block['text'].strip(), 'role': 'credit'})
        elif kind == 'math':
            new_blocks.append({'type': 'math', 'tex': block['text'].strip()})
        elif kind == 'image':
            alt = block['alt'] or previous_alt.get(block['asset']) or f'Figura da questão {content["number"]}.'
            new_blocks.append(
                {
                    'type': 'image',
                    'asset': {'path': block['asset'], 'alt': alt},
                    'caption': ' '.join(captions[block['id']]),
                    'credit': ' '.join(credits[block['id']]),
                    'equations': [],
                }
            )
        elif kind == 'table':
            table, error = table_block(block, proposal['table_structures'], '')
            if error:
                errors.append(error)
            else:
                new_blocks.append(table)
    published_images = {a['letter']: bool(a.get('image')) for a in content['alternatives']}
    alternatives = []
    for letter in 'ABCDE':
        marker = next(b for b in ordered if b['type'] == 'alternative' and b['alternative'] == letter)
        figures = [b for b in ordered if b['type'] == 'image' and b['alternative'] == letter]
        if len(figures) > 1:
            errors.append(f'A alternativa {letter} tem mais de uma figura.')
        text = re.sub(rf'^\s*\(?{letter}\)?(?:[\s.)\t]+|$)', '', marker['text']).strip()
        image = {'path': figures[0]['asset'], 'alt': figures[0]['alt'] or f'Alternativa {letter}.'} if figures else None
        if not text and image is None:
            errors.append(f'A alternativa {letter} ficou vazia.')
        if image is None and published_images.get(letter):
            errors.append(f'A alternativa {letter} tem figura no conteúdo publicado e nenhuma na proposta.')
        alternatives.append({'letter': letter, 'text': text, 'image': image})
    if errors:
        raise LayoutRejected(errors)
    statement = '\n\n'.join(
        b.get('text') or b.get('tex') or '' for b in new_blocks if b['type'] in {'paragraph', 'math'}
    ).strip()
    result = copy.deepcopy(content)
    result.update(
        blocks=new_blocks,
        alternatives=alternatives,
        images=[],
        original_layout=False,
        statement=statement if len(statement) >= 5 else content['statement'],
    )
    result['layout'] = {
        **(content.get('layout') or {}),
        'adapter': {'version': ADAPTER_VERSION, 'origin': proposal['origin'], 'source_sha256': source_sha256},
    }
    result['layout'].pop('preparation', None)
    extraction = result['layout'].get('extraction')
    if extraction and any(i.get('severity') == 'error' for i in extraction.get('issues', [])):
        # The new blocks replace the extraction they diagnosed; the record stays, marked as resolved
        # by this adapter. It only takes effect if a curator approves the proposal.
        resolution = f'Blocos substituídos por {ADAPTER_VERSION}; vale somente após aprovação humana.'
        result['layout']['extraction'] = {
            **extraction,
            'issues': [i for i in extraction['issues'] if i.get('severity') != 'error'],
            'resolved': [
                *extraction.get('resolved', []),
                *(dict(i, resolution=resolution) for i in extraction['issues'] if i.get('severity') == 'error'),
            ],
        }
    try:
        result = QuestionContent.model_validate(result).model_dump()
    except ValidationError as error:
        raise LayoutRejected([e['msg'] for e in error.errors()])
    blocking = [f'{i["code"]}: {i["message"]}' for i in content_issues(result) if i.get('severity') == 'error']
    if blocking:
        raise LayoutRejected(blocking)
    return result, compare(content, result)
