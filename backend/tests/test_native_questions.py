import copy
import hashlib
import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend.app.bundled_content import bundled_reviewer, refresh_bundle
from backend.app.content import public_question, validate_assets
from backend.app.models import Exam, ExamRun
from backend.app.presentation import readable_content
from backend.app.schemas import ExamImport, QuestionContent

ROOT = Path(__file__).resolve().parents[2]


def test_bundled_json_is_native_and_keeps_only_figures():
    payload = ExamImport.model_validate_json((ROOT / 'data/enem-2024-dia2-azul.json').read_text())
    for question in payload.questions:
        c = question.content
        assert not c.original_layout
        assert c.blocks and not c.images
        assert 'QUESTÃO' not in c.statement
        assert all('do enunciado original' not in a.text for a in c.alternatives)
        validate_assets(c.model_dump())
        for block in c.blocks:
            if block.type == 'image':
                assert '/native/' in block.asset.path
    by_number = {q.content.number: q.content for q in payload.questions}
    assert not any(b.type == 'image' for b in by_number[93].blocks)
    assert any(b.type == 'table' for b in by_number[139].blocks)
    assert any(b.type == 'math' for b in by_number[170].blocks)
    assert all(a.image for a in by_number[112].alternatives)
    assert by_number[91].alternatives[1].text == 'absorve a energia cinética do sistema.'
    assert r'\sqrt[3]{6}' in by_number[149].alternatives[3].text


def test_legacy_view_uses_json_without_changing_answers_or_snapshots():
    legacy = json.loads((ROOT / 'data/sources/enem-2024-dia2-azul-extraction.json').read_text())['questions'][0]
    before = copy.deepcopy(legacy['content'])
    public = public_question({'id': legacy['question_id'] + ':1', 'question_id': legacy['question_id'],
                              'version': 1, 'content': legacy['content']}, False)
    assert public['blocks'] and not public['original_layout']
    assert public['version'] == 1
    assert 'correct_answer' not in public
    assert legacy['content'] == before
    changed = {**before, 'statement': before['statement'] + ' Alteração própria.'}
    assert readable_content(legacy['question_id'], changed) == changed


def test_native_schema_rejects_malformed_tables_and_missing_block_assets():
    payload = json.loads((ROOT / 'data/enem-2024-dia2-azul.json').read_text())['questions'][0]['content']
    payload['blocks'] = [{'type': 'table', 'caption': 'Tabela de teste', 'headers': ['A', 'B'], 'rows': [['Uma célula']]}]
    with pytest.raises(ValueError):
        QuestionContent.model_validate(payload)
    payload['blocks'] = [{'type': 'image', 'asset': {'path': '/assets/not-found.png', 'alt': 'Figura ausente de teste'}}]
    with pytest.raises(HTTPException):
        validate_assets(payload)


def test_refresh_creates_versions_and_preserves_runs(admin, student, exam_payload, database):
    for q in exam_payload['questions']:
        q['content']['original_layout'] = True
    assert admin.post('/admin/imports', json=exam_payload).status_code == 201
    for q in exam_payload['questions']:
        admin.post(f"/admin/reviews/{q['question_id']}:1", json={'action': 'approve', 'reason': 'Conteúdo anterior de teste conferido'})
    admin.post('/admin/reviews/prova-teste', json={'action': 'publish', 'reason': 'Publicação do conjunto anterior de teste'})
    run = student.post('/exam-runs', json={'exam_id': 'prova-teste', 'idempotency_key': 'native-refresh-test'}).json()
    updated = copy.deepcopy(exam_payload)
    for q in updated['questions']:
        content = q['content']
        content['original_layout'] = False
        content['blocks'] = [{'type': 'paragraph', 'text': content['statement']}]
        content['layout'] = {'legacy_text_sha256': hashlib.sha256(content['statement'].encode()).hexdigest()}
    with database.begin() as db:
        exam = db.get(Exam, 'prova-teste')
        reviewer = bundled_reviewer(db)
        assert refresh_bundle(db, exam, ExamImport.model_validate(updated), reviewer) == 3
    with database.begin() as db:
        assert db.get(ExamRun, run['id']).items[0]['version'] == 1
        exam = db.get(Exam, 'prova-teste')
        assert exam.items == ['teste-q1:2', 'teste-q2:2', 'teste-q3:2']
        assert refresh_bundle(db, exam, ExamImport.model_validate(updated), bundled_reviewer(db)) == 0
    student.put(f"/exam-runs/{run['id']}/answers/teste-q1:1", json={'choice': 'B'})
    assert student.post(f"/exam-runs/{run['id']}/finish").json()['result']['correct'] == 1
