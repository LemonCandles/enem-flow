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
from backend.app import presentation
from backend.app.presentation import content_fingerprint, readable_content
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
    legacy = json.loads((ROOT / 'data/derived/baselines/enem-2024-dia2-azul-extraction.json').read_text())['questions'][0]
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


def test_refresh_creates_versions_and_preserves_runs(admin, student, exam_payload, database, monkeypatch):
    for q in exam_payload['questions']:
        q['content']['original_layout'] = True
    # Import now prepares every new JSON; this fixture trusts that exact input.
    from backend.app.preparation import prepare_content
    for q in exam_payload['questions']:
        q['content'] = prepare_content(q['content'])
    trusted = {q['question_id']: {content_fingerprint(q['content'])} for q in exam_payload['questions']}
    monkeypatch.setattr(presentation, 'previous_fingerprints', lambda: trusted)
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


def test_review_is_reproducible_and_changes_only_the_reported_questions():
    from scripts.review_presentation import apply_review, REASONS
    baseline = json.loads((ROOT / 'data/derived/baselines/enem-2024-dia2-azul-native-v1.json').read_text())
    current = json.loads((ROOT / 'data/enem-2024-dia2-azul.json').read_text())
    assert apply_review(copy.deepcopy(baseline)) == current
    assert apply_review(copy.deepcopy(current)) == current
    changed = []
    for before, after in zip(baseline['questions'], current['questions']):
        if before == after:
            continue
        c, old = after['content'], before['content']
        changed.append(c['number'])
        assert all(c[key] == old[key] for key in presentation.ASSESSMENT_FIELDS)
        assert [a['letter'] for a in c['alternatives']] == [a['letter'] for a in old['alternatives']]
        assert c['layout']['presentation_review']['previous_content_sha256'] == hashlib.sha256(json.dumps(old, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    assert changed == sorted(REASONS)
    by_number = {q['content']['number']: q['content'] for q in current['questions']}
    figure91 = next(b for b in by_number[91]['blocks'] if b['type'] == 'image')
    assert figure91['caption'] == 'Momentum and Car safety. GCSE Physics Revision.'
    assert 'shalom-education.com' in figure91['credit']
    assert 'Momentum and Car safety' not in by_number[91]['statement']
    figure92 = next(b for b in by_number[92]['blocks'] if b['type'] == 'image')
    assert len(figure92['equations']) == 2
    assert r'\ce{CH3COO- (aq)} + \ce{2 H2O (l)}' in figure92['equations'][0]
    assert 'QUINTO,' in figure92['credit'] and 'CH₃COO' not in figure92['credit']
    assert all(r'\ce{' in a['text'] for a in by_number[92]['alternatives'])
    assert by_number[92]['correct_answer'] == 'C'
    assert by_number[116]['blocks'][1]['type'] == 'math'


def test_previous_native_snapshot_adapts_without_rewriting_or_overriding_edits():
    question = json.loads((ROOT / 'data/derived/baselines/enem-2024-dia2-azul-native-v1.json').read_text())['questions'][0]
    original = copy.deepcopy(question['content'])
    adapted = readable_content(question['question_id'], original)
    assert any(b.get('caption', '').startswith('Momentum') for b in adapted['blocks'])
    assert question['content'] == original
    for field, value in [('correct_answer', 'A'), ('labels', {'themes': ['Edição própria']})]:
        edited = {**original, field: value}
        assert readable_content(question['question_id'], edited) == edited
    edited = copy.deepcopy(original)
    edited['blocks'][0]['text'] += ' Edição própria do bloco.'
    assert readable_content(question['question_id'], edited) == edited


def test_refresh_native_v1_publishes_only_fifteen_versions(database):
    from backend.app.content import import_exam
    from backend.app.models import QuestionVersion, Review
    before = ExamImport.model_validate_json((ROOT / 'data/derived/baselines/enem-2024-dia2-azul-native-v1.json').read_text())
    after = ExamImport.model_validate_json((ROOT / 'data/enem-2024-dia2-azul.json').read_text())
    with database.begin() as db:
        exam = import_exam(db, before)
        snapshots = {key: copy.deepcopy(db.get(QuestionVersion, key).content) for key in exam.items}
        for key in exam.items:
            db.get(QuestionVersion, key).status = 'approved'
        assert refresh_bundle(db, exam, after, bundled_reviewer(db)) == 15
        assert len([key for key in exam.items if key.endswith(':2')]) == 15
        assert all(db.get(QuestionVersion, key).content == content for key, content in snapshots.items())
        reviews = db.scalars(select(Review).where(Review.target_id.like('%:2'))).all()
        assert len(reviews) == 15 and all('página' in r.reason for r in reviews)
        assert refresh_bundle(db, exam, after, bundled_reviewer(db)) == 0


@pytest.mark.parametrize('edit', ['block', 'answer'])
def test_refresh_refuses_custom_content_even_if_statement_is_unchanged(database, edit):
    from backend.app.content import import_exam
    from backend.app.models import QuestionVersion
    before = ExamImport.model_validate_json((ROOT / 'data/derived/baselines/enem-2024-dia2-azul-native-v1.json').read_text())
    after = ExamImport.model_validate_json((ROOT / 'data/enem-2024-dia2-azul.json').read_text())
    with database.begin() as db:
        exam = import_exam(db, before)
        version = db.get(QuestionVersion, exam.items[0])
        own = copy.deepcopy(version.content)
        if edit == 'block': own['blocks'][0]['text'] += ' Edição própria.'
        else: own['correct_answer'] = 'A'
        version.content = own
        with pytest.raises(HTTPException, match='409'):
            refresh_bundle(db, exam, after, bundled_reviewer(db))


def test_figure_contract_bounds_equations_and_retains_caption_credit():
    from backend.app.schemas import ImageBlock
    figure = dict(type='image', asset={'path': '/assets/figura.png', 'alt': 'Diagrama da questão'},
                  caption='Legenda da figura', credit='Fonte da figura', equations=[r'\ce{H+}'])
    assert ImageBlock.model_validate(figure).model_dump() == figure
    for invalid in [[''], ['a' * 8001], ['x'] * 11]:
        with pytest.raises(ValueError):
            ImageBlock.model_validate({**figure, 'equations': invalid})
