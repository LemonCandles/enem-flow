"""Fixed diagnostic sessions and their immutable learning events."""
import copy
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select

from backend.app.models import DiagnosticSession, Exam, ExamRun, LearningEvent, QuestionVersion
from backend.app.services.diagnostics import identity, select_items


@pytest.fixture
def thematic(admin, exam_payload):
    payload = copy.deepcopy(exam_payload)
    payload['expected_items'] = 8
    template = payload['questions'][0]
    payload['questions'] = []
    for n in range(1, 9):
        q = copy.deepcopy(template)
        q['question_id'] = f'theme-q{n}'
        q['content'].update(number=n, statement=f'Questão sintética temática {n}: calcule o resultado solicitado.')
        q['content']['labels']['themes'] = ['Álgebra' if n % 2 else 'Geometria']
        payload['questions'].append(q)
    assert admin.post('/admin/imports', json=payload).status_code == 201
    for q in payload['questions']:
        assert admin.post(f"/admin/reviews/{q['question_id']}:1", json={'action': 'approve', 'reason': 'Referência sintética para diagnóstico'}).status_code == 200
    assert admin.post('/admin/reviews/prova-teste', json={'action': 'publish', 'reason': 'Referência temática para testes'}).status_code == 200
    return payload


def start(student, key='diagnostic-key-001', **kwargs):
    return student.post('/sessions', json={'objective': 'Verificar conhecimentos', 'area': 'Matemática',
        'available_minutes': 15, 'idempotency_key': key, **kwargs})




def test_diagnostic_lifecycle_and_exam_compatibility(thematic, student, database):
    options = student.get('/diagnostic-options').json()['areas']
    assert options == [{'area': 'Matemática', 'eligible_items': 8, 'themes': {'Geometria': 4, 'Álgebra': 4}}]
    s = start(student).json()
    assert s['selection']['selected_items'] == 5
    assert abs(s['selection']['themes']['Álgebra'] - s['selection']['themes']['Geometria']) == 1
    assert 'correct_answer' not in str(s) and 'answer_key_url' not in str(s)
    assert all(i['source_url'] == thematic['source']['url'] for i in s['items'])
    assert start(student).json() == s
    assert start(student, objective='Outro objetivo').status_code == 409
    endpoint = f"/sessions/{s['id']}"
    item = s['items'][0]
    assert student.put(f"{endpoint}/answers/unknown", json={'choice': 'A'}).status_code == 404
    for choice in ['A', None, 'B']:
        assert student.put(f"{endpoint}/answers/{item['id']}", json={'choice': choice}).status_code == 200
    first = student.post(f'{endpoint}/finish').json()
    assert first['result']['correct'] == 1 and first['result']['unanswered'] == 4
    assert student.post(f'{endpoint}/finish').json() == first
    assert student.put(f"{endpoint}/answers/{item['id']}", json={'choice': 'C'}).status_code == 409
    assert student.get('/me/progress').json()['completed_runs'] == 0
    assert len(student.get('/me/sessions').json()) == 1
    with database() as db:
        assert db.scalar(select(func.count()).select_from(LearningEvent)) == 5
    assert student.delete('/me/history').status_code == 204
    assert student.get('/me/sessions').json() == []
    with database() as db:
        assert db.scalar(select(func.count()).select_from(LearningEvent)) == 0


def test_eligibility_and_empty_areas(thematic, student, database):
    assert start(student, area='Linguagens').status_code == 422
    for params in ({'available_minutes': 2}, {'available_minutes': 181}, {'objective': '   '}, {'area': 'Outra'}):
        assert start(student, **params).status_code == 422
    with database.begin() as db:
        for q in db.scalars(select(QuestionVersion)):
            c = copy.deepcopy(q.content)
            if q.id == 'theme-q1:1':
                c.update(annulled=True, correct_answer=None)
            elif q.id == 'theme-q2:1':
                c['labels']['themes'] = []
            elif q.id == 'theme-q3:1':
                c['blocks'] = [{'type': 'paragraph', 'text': 'Texto com caractere \ufffd inválido.'}]
            else:
                q.status = 'draft'
            q.content = c
    assert student.get('/diagnostic-options').json() == {'areas': []}
    assert start(student).status_code == 422


def test_concurrent_start_finish_and_owned_access(thematic, student, client, database):
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(lambda _: start(student), range(3)))
    assert {r.status_code for r in responses} == {201}
    ids = {r.json()['id'] for r in responses}
    assert len(ids) == 1
    endpoint = f'/sessions/{ids.pop()}'
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(lambda _: student.post(f'{endpoint}/finish'), range(3)))
    assert all(r.status_code == 200 for r in responses)
    with database() as db:
        assert db.scalar(select(func.count()).select_from(LearningEvent)) == 5
    student.post('/auth/logout')
    assert student.get(endpoint).status_code == 401
    student.post('/auth/register', json={'name': 'Outra Pessoa', 'email': 'outra@example.com', 'password': 'senha-longa-isolada'})
    assert student.get(endpoint).status_code == 404
    assert student.post(f'{endpoint}/finish').status_code == 404
    assert student.put(f'{endpoint}/answers/theme-q1:1', json={'choice': 'B'}).status_code == 404
    assert student.get('/me/sessions').json() == []




def test_selector_dedup_unseen_and_reproducibility(thematic, student, database):
    from backend.app.services.diagnostics import eligible_items
    with database.begin() as db:
        q = db.get(QuestionVersion, 'theme-q1:1')
        db.add(QuestionVersion(id='alternate-color:1', question_id='alternate-color', canonical_id=q.canonical_id,
                               version=1, content=q.content, status='approved', created_at=q.created_at + 1))
        db.flush()
        exam = db.get(Exam, 'prova-teste')
        exam.items = [*exam.items, 'alternate-color:1']
        pool = eligible_items(db)
        assert len(pool) == 8
        assert any(i['id'] == 'alternate-color:1' for i in pool)
    selected, config = select_items(pool, set(), 180, 'fixed-seed')
    assert len(selected) == 8 and config['requested_items'] == 20
    assert select_items(pool, set(), 180, 'fixed-seed') == (selected, config)
    seen = {identity(i) for i in selected[:2]}
    first, _ = select_items(pool, seen, 6, 'fixed-seed')
    assert not any(identity(i) in seen for i in first)
