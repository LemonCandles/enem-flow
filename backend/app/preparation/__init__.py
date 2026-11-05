"""Reusable JSON preparation for any exam, without question-number overrides."""

import copy
import hashlib
import json
import re

from ..schemas import ExamImport, QuestionContent
from .notation import explicit_issues, tex_shape_issue
from .rules import MESSAGES
from .steps import STEPS, Preparation

VERSION = 'generic-v1'


def fingerprint(content):
    data = copy.deepcopy(content)
    if data.get('layout'):
        data['layout'].pop('preparation', None)
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    ).hexdigest()


def content_issues(content):
    """Validate rendered content independently of an imported preparation report."""
    found = []

    def add(code, location, excerpt=''):
        row = dict(code=code, severity='error', location=location, message=MESSAGES[code], excerpt=excerpt[:500])
        if row not in found:
            found.append(row)

    def text(value, location):
        if any(ord(char) < 32 and char not in '\n\t\r' for char in value):
            add('control_character', location, value)
        if '\ufffd' in value:
            add('replacement_character', location, value)
        for code, excerpt in explicit_issues(value):
            if code == 'invalid_latex':
                add(code, location, excerpt)

    blocks = content.get('blocks', [])
    if not blocks:
        text(content['statement'], 'statement')
    for i, block in enumerate(blocks):
        loc = f'blocks[{i}]'
        if block['type'] == 'paragraph':
            text(block['text'], loc)
        elif block['type'] == 'math':
            if tex_shape_issue(block['tex']):
                add('invalid_latex', loc, block['tex'])
        elif block['type'] == 'image':
            text(block.get('caption') or block['asset']['alt'], loc + '.caption')
            text(block.get('credit', ''), loc + '.credit')
            for j, tex in enumerate(block.get('equations', [])):
                if tex_shape_issue(tex):
                    add('invalid_latex', loc + f'.equations[{j}]', tex)
        elif block['type'] == 'table':
            for value in block['headers']:
                text(value, loc + '.headers')
            for row in block['rows']:
                for value in row:
                    text(value, loc + '.rows')
    for i, option in enumerate(content['alternatives']):
        text(option['text'], f'alternatives[{i}].text')
        if re.search(r'Alternativa não extraída|Transcrição pendente de preparação', option['text'], re.I):
            add('missing_alternative', f'alternatives[{i}].text', option['text'])
    if content.get('images'):
        add('unlocated_images', 'images')
    if content.get('original_layout') and content.get('images'):
        add('original_layout', 'original_layout')
    for row in ((content.get('layout') or {}).get('extraction') or {}).get('issues', []):
        if row.get('severity') == 'error' and row not in found:
            found.append(row)
    return found


def prepare_content(source):
    c = QuestionContent.model_validate(source).model_dump()
    original = copy.deepcopy(c)
    previous = (c.get('layout') or {}).get('preparation', {})
    if (
        previous.get('version') == VERSION
        and previous.get('output_sha256') == fingerprint(c)
        and isinstance(previous.get('changes'), list)
        and isinstance(previous.get('issues'), list)
    ):
        # A checksum permits presentation reuse, never skipping validation.
        for row in content_issues(c):
            if row not in previous['issues']:
                previous['issues'].append(row)
        return c
    context = Preparation(c)
    for step in STEPS:
        step(context)
    # A prepared document is never an approval. Keep the audit next to its source.
    c['layout'] = {
        **(c['layout'] or {}),
        'preparation': {
            'version': VERSION,
            'input_sha256': fingerprint(original),
            'changes': context.changes,
            'issues': context.issues,
            'review_required': True,
        },
    }
    # Preserve extraction diagnostics until a curator corrects the version.
    for row in (c['layout'].get('extraction') or {}).get('issues', []):
        if row not in context.issues:
            context.issues.append(row)
    c = QuestionContent.model_validate(c).model_dump()
    c['layout']['preparation']['output_sha256'] = fingerprint(c)
    return c


def prepare_exam(payload):
    data = payload.model_dump() if isinstance(payload, ExamImport) else copy.deepcopy(payload)
    for q in data['questions']:
        q['content'] = prepare_content(q['content'])
    prepared = ExamImport.model_validate(data)
    report = {'version': VERSION, 'exam_id': prepared.id, 'questions': [], 'changes': 0, 'warnings': 0, 'errors': 0}
    for q in prepared.questions:
        audit = q.content.layout['preparation']
        report['questions'].append({'question_id': q.question_id, 'number': q.content.number, **audit})
        report['changes'] += len(audit['changes'])
        for issue in audit['issues']:
            report[issue['severity'] + 's'] += 1
    return prepared, report


def blocking_issues(content):
    issues = [
        i
        for i in ((content.get('layout') or {}).get('preparation') or {}).get('issues', [])
        if i.get('severity') == 'error'
    ]
    for row in content_issues(content):
        if row not in issues:
            issues.append(row)
    return issues
