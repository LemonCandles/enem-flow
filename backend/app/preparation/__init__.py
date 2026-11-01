"""Reusable JSON preparation for any exam, without question-number overrides."""
import copy
import hashlib
import json
import re

from ..schemas import ExamImport, QuestionContent
from .notation import CHEM_CONTEXT, LATEX, explicit_issues, normalize, tex_shape_issue

VERSION = 'generic-v1'
CREDIT = re.compile(r'^(?:Dispon[ií]vel em|Acesso em|Fonte\s*:|https?://|[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ -]{2,},\s)')
CAPTION = re.compile(r'^(?:Figura|Gr[aá]fico|Esquema|Fotografia|Ilustra[çc][aã]o)\s*(?:\d+|[–—:-])', re.I)
MESSAGES = {
    'ambiguous_charge': 'Carga sem posição inequívoca: confira se o número é índice ou carga e use LaTeX explícito.',
    'ambiguous_generic_ion': 'Íon genérico ou símbolo de elemento ambíguo: confira a posição de m/n no PDF.',
    'ambiguous_liquid_state': 'Estado físico (I) ambíguo: confira no PDF se é l minúsculo.',
    'ambiguous_exponent': 'Expoente sem posição preservada: confira no PDF antes de converter.',
    'unbalanced_formula': 'Parênteses da fórmula incompletos na extração.',
    'unreadable_reaction': 'Reação não interpretada com segurança; preserve o original e transcreva em LaTeX.',
    'replacement_character': 'Há caractere não reconhecido na extração.',
    'figure_association_inferred': 'Legenda/referência associada por proximidade; confira o vínculo com a figura.',
    'original_layout': 'O conteúdo ainda contém recorte integral. Prepare o PDF para separar texto e figuras.',
    'unlocated_images': 'Imagens sem posição: informe blocos image na ordem de leitura para associar suas legendas.',
    'missing_description': 'Descrição genérica da figura: substitua por uma descrição de seu conteúdo.',
    'invalid_latex': 'Delimitadores ou agrupamentos LaTeX incompletos; corrija antes de aprovar.',
}


def fingerprint(content):
    data = copy.deepcopy(content)
    if data.get('layout'): data['layout'].pop('preparation', None)
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def content_issues(content):
    """Validate rendered content independently of an imported preparation report."""
    found = []
    def add(code, location, excerpt=''):
        row = dict(code=code, severity='error', location=location,
                   message=MESSAGES[code], excerpt=excerpt[:500])
        if row not in found: found.append(row)
    def text(value, location):
        for code, excerpt in explicit_issues(value):
            if code == 'invalid_latex': add(code, location, excerpt)
    blocks = content.get('blocks', [])
    if not blocks: text(content['statement'], 'statement')
    for i, block in enumerate(blocks):
        loc = f'blocks[{i}]'
        if block['type'] == 'paragraph': text(block['text'], loc)
        elif block['type'] == 'math':
            if tex_shape_issue(block['tex']): add('invalid_latex', loc, block['tex'])
        elif block['type'] == 'image':
            text(block.get('caption') or block['asset']['alt'], loc+'.caption')
            text(block.get('credit', ''), loc+'.credit')
            for j, tex in enumerate(block.get('equations', [])):
                if tex_shape_issue(tex): add('invalid_latex', loc+f'.equations[{j}]', tex)
        elif block['type'] == 'table':
            for value in block['headers']: text(value, loc+'.headers')
            for row in block['rows']:
                for value in row: text(value, loc+'.rows')
    for i, option in enumerate(content['alternatives']): text(option['text'], f'alternatives[{i}].text')
    if content.get('images'): add('unlocated_images', 'images')
    if content.get('original_layout') and content.get('images'): add('original_layout', 'original_layout')
    for row in ((content.get('layout') or {}).get('extraction') or {}).get('issues', []):
        if row.get('severity') == 'error' and row not in found: found.append(row)
    return found


def split_options(statement):
    markers = list(re.finditer(r'(?m)^\s*([ABCDE])[ \t.)]*(?:\n|[ \t])', statement))
    groups = [i for i in range(len(markers)-4) if ''.join(m[1] for m in markers[i:i+5]) == 'ABCDE']
    if len(groups) != 1:
        raise ValueError('Não foi possível identificar uma única sequência de alternativas A–E. Informe blocos/alternativas revisados.')
    found = markers[groups[0]:groups[0]+5]
    body = statement[:found[0].start()].strip()
    choices = [statement[m.end():found[i+1].start() if i < 4 else len(statement)].strip() for i,m in enumerate(found)]
    if not all(choices): raise ValueError('Alternativa sem texto: confira se contém uma figura ou fórmula não extraída.')
    return body, choices


def prepare_content(source):
    c = QuestionContent.model_validate(source).model_dump()
    original = copy.deepcopy(c)
    previous = (c.get('layout') or {}).get('preparation', {})
    if (previous.get('version') == VERSION and previous.get('output_sha256') == fingerprint(c)
            and isinstance(previous.get('changes'), list) and isinstance(previous.get('issues'), list)):
        # A checksum permits presentation reuse, never skipping validation.
        for row in content_issues(c):
            if row not in previous['issues']: previous['issues'].append(row)
        return c
    issues, changes = [], []
    def issue(code, location, excerpt='', severity='warning'):
        row = dict(code=code, severity=severity, location=location, message=MESSAGES.get(code, code), excerpt=excerpt[:500])
        if row not in issues: issues.append(row)
    def convert(text, location):
        result, found = normalize(text, chemistry)
        for code, excerpt in found: issue(code, location, excerpt, 'error' if code == 'invalid_latex' else 'warning')
        if result != text: changes.append({'location': location, 'operation': 'latex', 'before': text[:1000], 'after': result[:1000]})
        return result
    def inspect_tex(tex, location):
        if tex_shape_issue(tex): issue('invalid_latex', location, tex, 'error')
        if r'\ce{' in tex and '(I)' in tex: issue('ambiguous_liquid_state', location, tex)

    chemistry = bool(CHEM_CONTEXT.search(c['statement'] + ' ' + (c['labels']['discipline'] or '')))
    blocks = c['blocks']
    if c['images']: issue('unlocated_images', 'images', severity='error')
    if c['original_layout'] and c['images']: issue('original_layout', 'original_layout', severity='error')
    if not blocks:
        statement = c['statement']
        if c['original_layout']:
            statement = re.sub(r'^\s*QUEST[ÃA]O\s+\d+\s*', '', statement)
            if re.search(r'(?m)^\s*A(?:[ \t.)]|$)', statement):
                statement, choices = split_options(statement)
                for a, text in zip(c['alternatives'], choices): a['text'] = text
        blocks = [{'type': 'paragraph', 'text': p} for p in re.split(r'\n\s*\n', statement) if p.strip()]
    rebuilt = []
    for i, block in enumerate(blocks):
        b = copy.deepcopy(block)
        loc = f'blocks[{i}]'
        if b['type'] == 'paragraph':
            # Keep separate equation/reference lines, even when extraction put them
            # in the same paragraph. Reflow ordinary line breaks only.
            pieces = re.split(r'\n(?=(?:[^\n]*(?:→|⇌|->)|Dispon[ií]vel em|Acesso em|https?://|[A-ZÁÉÍÓÚÇ]{3,},))', b['text'])
            for piece in pieces:
                raw = re.sub(r'\s*\n\s*', ' ', piece).strip()
                text = raw if CREDIT.match(raw) or b.get('role') == 'credit' else convert(raw, loc)
                if LATEX.fullmatch(text) and text.startswith('$'):
                    delimiter = 2 if text.startswith('$$') else 1
                    rebuilt.append({'type': 'math', 'tex': text[delimiter:-delimiter]})
                else:
                    rebuilt.append({**b, 'text': text})
        elif b['type'] == 'image':
            b['caption'] = convert(b.get('caption', ''), loc+'.caption')
            # Credits are bibliographic prose; do not convert abbreviations CO/NO.
            b.setdefault('credit', '')
            b.setdefault('equations', [])
            for j,tex in enumerate(b['equations']): inspect_tex(tex, loc+f'.equations[{j}]')
            if re.match(r'^(Figura|Imagem) (extra[ií]da|da questão)', b['asset']['alt']): issue('missing_description', loc+'.asset.alt', b['asset']['alt'])
            rebuilt.append(b)
        elif b['type'] == 'table':
            b['headers'] = [convert(value, loc+'.headers') for value in b['headers']]
            b['rows'] = [[convert(cell, loc+'.rows') for cell in row] for row in b['rows']]
            rebuilt.append(b)
        else:
            if b['type'] == 'math': inspect_tex(b['tex'], loc)
            rebuilt.append(b)  # Authored LaTeX is already explicit; never reinterpret it.
    blocks = rebuilt
    removed = set()
    for i, figure in enumerate(blocks):
        if figure['type'] != 'image': continue
        for direction in [1, -1]:
            collected, j = [], i + direction
            while 0 <= j < len(blocks) and len(collected) < 8:
                b = blocks[j]
                if j in removed: break
                if b['type'] == 'math' and r'\ce{' in b['tex']:
                    collected.append(j)
                elif b['type'] == 'paragraph' and b.get('role') != 'body' and (CREDIT.match(b['text']) or CAPTION.match(b['text']) or b.get('role') in {'credit', 'caption'}):
                    collected.append(j)
                elif direction == 1 and b['type'] == 'paragraph' and b.get('role') is None and len(b['text']) < 120 and j+1 < len(blocks) and blocks[j+1]['type'] == 'paragraph' and CREDIT.match(blocks[j+1]['text']):
                    collected.append(j)
                else: break
                j += direction
            # A short title immediately before a source URL belongs to the same
            # citation group. This is inferred and explicitly marked for review.
            if direction == -1 and collected and 0 <= j < len(blocks):
                b = blocks[j]
                if b['type'] == 'paragraph' and b.get('role') is None and len(b['text']) < 120 and b['text'].endswith('.'):
                    collected.append(j)
            if not collected: continue
            for index in sorted(collected):
                b = blocks[index]
                if b['type'] == 'math': figure['equations'].append(b['tex'])
                elif CAPTION.match(b['text']) or (index == min(collected) and not CREDIT.match(b['text'])):
                    figure['caption'] = '\n'.join(filter(None, [figure['caption'], b['text']]))
                else: figure['credit'] = '\n'.join(filter(None, [figure['credit'], b['text']]))
                removed.add(index)
            changes.append({'location': f'blocks[{i}]', 'operation': 'associate_figure', 'source_blocks': sorted(collected)})
            issue('figure_association_inferred', f'blocks[{i}]')
    c['blocks'] = [b for i,b in enumerate(blocks) if i not in removed]
    for i, a in enumerate(c['alternatives']):
        fraction = re.fullmatch(r'\s*(\d+)\s*/\s*(\d+)\s*', a['text'])
        if fraction:
            a['text'] = r'$\frac{' + fraction[1] + '}{' + fraction[2] + '}$'
            changes.append({'location':f'alternatives[{i}].text','operation':'fraction'})
        else: a['text'] = convert(a['text'], f'alternatives[{i}].text')
    c['statement'] = '\n\n'.join(b['text'] for b in c['blocks'] if b['type'] == 'paragraph') or c['statement']
    for i,b in enumerate(c['blocks']):
        if b['type'] == 'paragraph' and b.get('role') is None: b['role'] = 'credit' if CREDIT.match(b['text']) else 'body'
    # A prepared document is never an approval. Keep the audit next to its source.
    c['layout'] = {**(c['layout'] or {}), 'preparation': {
        'version': VERSION, 'input_sha256': fingerprint(original), 'changes': changes,
        'issues': issues, 'review_required': True,
    }}
    # Preserve extraction diagnostics until a curator corrects the version.
    for row in (c['layout'].get('extraction') or {}).get('issues', []):
        if row not in issues: issues.append(row)
    c = QuestionContent.model_validate(c).model_dump()
    c['layout']['preparation']['output_sha256'] = fingerprint(c)
    return c


def prepare_exam(payload):
    data = payload.model_dump() if isinstance(payload, ExamImport) else copy.deepcopy(payload)
    for q in data['questions']: q['content'] = prepare_content(q['content'])
    prepared = ExamImport.model_validate(data)
    report = {'version': VERSION, 'exam_id': prepared.id, 'questions': [], 'changes': 0, 'warnings': 0, 'errors': 0}
    for q in prepared.questions:
        audit = q.content.layout['preparation']
        report['questions'].append({'question_id': q.question_id, 'number': q.content.number, **audit})
        report['changes'] += len(audit['changes'])
        for issue in audit['issues']: report[issue['severity']+'s'] += 1
    return prepared, report


def blocking_issues(content):
    issues = [i for i in ((content.get('layout') or {}).get('preparation') or {}).get('issues', []) if i.get('severity') == 'error']
    for row in content_issues(content):
        if row not in issues: issues.append(row)
    return issues
