"""Adaptive practice: pure policy decisions, then the API contract and its audit trail."""

import copy
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json

import pytest
from sqlalchemy import func, select

from backend.app.models import LearningEvent, RecommendationEvent
from backend.app.services.adaptive import ADAPTIVE_V1, PolicyInput, recommend

NOW = 1_800_000_000.0
DAY = 86_400
TAXONOMY = 'enem-content-v1'


def item(number, theme, skills=()):
    return {
        'id': f'q{number}:1',
        'question_id': f'q{number}',
        'canonical_id': f'c{number}',
        'version': 1,
        'content': {
            'area': 'Matemática',
            'labels': {
                'discipline': 'Matemática',
                'themes': [theme],
                'skills': list(skills),
                'taxonomy_version': TAXONOMY,
            },
            'correct_answer': 'A',
        },
    }


def row(theme, attempts, correct, days_ago=1):
    return {
        'area': 'Matemática',
        'discipline': 'Matemática',
        'taxonomy_version': TAXONOMY,
        'name': theme,
        'independent_attempts': attempts,
        'independent_correct': correct,
        'estimate': (1 + correct) / (2 + attempts) if attempts else None,
        'last_practice': NOW - days_ago * DAY if attempts else None,
    }


def pool(themes=('Álgebra', 'Geometria', 'Estatística'), each=10):
    return [item(10 * t + n, theme) for t, theme in enumerate(themes) for n in range(each)]


def choose(items=None, rows=(), exposures=None, minutes=30, seed='semente', difficulty=None, policy='adaptive-v1'):
    data = PolicyInput(
        pool=items if items is not None else pool(),
        state={'themes': list(rows), 'skills': []},
        exposures=Counter(exposures or {}),
        minutes=minutes,
        seed=seed,
        now=NOW,
        difficulty=difficulty or {},
    )
    return recommend(data, policy)


def themes_of(entries):
    return Counter(e['item']['content']['labels']['themes'][0] for e in entries)


def test_new_student_explores_without_concluding_anything():
    entries, summary = choose()
    assert {e['function'] for e in entries} == {'exploracao'}
    assert all('nenhuma resposta independente' in e['reason'] for e in entries)
    assert set(themes_of(entries)) == {'Álgebra', 'Geometria', 'Estatística'}
    assert summary['requested_items'] == summary['selected_items'] == 10


def test_a_few_wrong_answers_are_exploration_and_enough_of_them_are_reinforcement():
    few, _ = choose(rows=[row('Álgebra', 4, 0), row('Geometria', 20, 18), row('Estatística', 20, 18)])
    assert next(e for e in few if e['group'] == 'Álgebra')['function'] == 'exploracao'
    enough, summary = choose(rows=[row('Álgebra', 8, 1), row('Geometria', 20, 18), row('Estatística', 20, 18)])
    first = enough[0]
    assert first['group'] == 'Álgebra' and first['function'] == 'reforco'
    assert first['reason'] == 'Reforço do tema Álgebra: 1 acerto em 8 respostas independentes.'
    assert summary['functions']['reforco'] >= 1


def test_strong_theme_returns_for_review_only_after_time_has_passed():
    rows = [
        row('Álgebra', 20, 18, days_ago=30),
        row('Geometria', 20, 18, days_ago=1),
        row('Estatística', 20, 18, days_ago=1),
    ]
    entries, _ = choose(rows=rows, minutes=3)
    assert entries[0]['group'] == 'Álgebra' and entries[0]['function'] == 'revisao'
    assert 'última prática há 30 dias' in entries[0]['reason']


def test_practice_is_not_concentrated_on_the_weakest_theme():
    rows = [row('Álgebra', 10, 0), row('Geometria', 20, 18), row('Estatística', 20, 18)]
    entries, summary = choose(rows=rows, minutes=30)
    assert max(themes_of(entries).values()) <= 5
    assert summary['relaxed_theme_cap'] == 0
    baseline, _ = choose(rows=rows, minutes=30, policy='reinforcement-simple-v1')
    assert themes_of(baseline)['Álgebra'] == 10


def test_single_theme_relaxes_the_cap_and_records_it():
    entries, summary = choose(items=pool(('Álgebra',)), minutes=30)
    assert len(entries) == 10
    assert summary['relaxed_theme_cap'] == 5


def test_exposure_prefers_new_items_and_removes_those_seen_too_often():
    items = pool(('Álgebra',), each=6)
    exposures = {'c0': ADAPTIVE_V1['max_item_exposures'], 'c1': 1}
    entries, summary = choose(items=items, exposures=exposures, minutes=12)
    chosen = [e['item']['canonical_id'] for e in entries]
    assert 'c0' not in chosen and summary['filtered']['exposicao'] == 1
    assert 'c1' not in chosen
    assert len(set(chosen)) == len(chosen)
    longer, _ = choose(items=items, exposures=exposures, minutes=60)
    assert longer[-1]['item']['canonical_id'] == 'c1'
    assert longer[-1]['components']['exposicao'] < 0
    _, summary = choose(items=items, exposures=exposures, minutes=60)
    assert summary['repeated_items'] == ['q1:1']


def test_provisional_difficulty_filters_only_while_the_session_keeps_its_size():
    items = pool(('Álgebra',), each=6)
    hard = {'c0': {'success_rate': 0.1, 'responses': 9}}
    entries, summary = choose(items=items, difficulty=hard, minutes=15)
    assert 'c0' not in [e['item']['canonical_id'] for e in entries] and summary['filtered']['dificuldade'] == 1
    entries, summary = choose(items=items, difficulty=hard, minutes=60)
    assert 'c0' in [e['item']['canonical_id'] for e in entries] and summary['filtered']['dificuldade'] == 0


def test_published_skills_join_the_decision():
    items = [item(1, 'Álgebra', ['MT.H12']), item(2, 'Álgebra')]
    data = PolicyInput(
        items,
        {'themes': [row('Álgebra', 20, 18)], 'skills': [{**row('MT.H12', 8, 1), 'discipline': None}]},
        Counter(),
        3,
        'semente',
        NOW,
    )
    entries, summary = recommend(data)
    assert entries[0]['item']['id'] == 'q1:1' and entries[0]['function'] == 'reforco'
    assert 'habilidade MT.H12' in entries[0]['reason']
    assert {'theme', 'skill'} == {group['kind'] for group in summary['evidence']}


@pytest.mark.parametrize('policy', ['adaptive-v1', 'random-v1', 'reinforcement-simple-v1'])
def test_the_same_input_gives_the_same_selection(policy):
    rows = [row('Álgebra', 8, 1), row('Geometria', 3, 1)]
    assert choose(rows=rows, policy=policy) == choose(rows=rows, policy=policy)
    first, _ = choose(rows=rows, policy=policy, seed='outra')
    if policy == 'random-v1':
        assert first != choose(rows=rows, policy=policy)[0]


def test_every_choice_logs_function_reason_priority_and_candidates():
    entries, summary = choose(rows=[row('Álgebra', 8, 1)])
    assert summary['version'] == 'adaptive-v1' and summary['parameters'] == ADAPTIVE_V1
    for entry in entries:
        assert entry['function'] in {'reforco', 'revisao', 'exploracao'} and entry['reason']
        assert set(entry['components']) == {
            'reforco',
            'revisao',
            'exploracao',
            'exposicao',
            'concentracao',
            'dificuldade',
            'total',
        }
        assert 0 < len(entry['candidates']) <= ADAPTIVE_V1['logged_candidates'] <= entry['candidates_total'] + 25
        assert entry['candidates'][0]['item_id'] == entry['item']['id']
    assert entries[0]['candidates_total'] == 30 and entries[-1]['candidates_total'] == 21


@pytest.fixture
def thematic(admin, exam_payload):
    payload = copy.deepcopy(exam_payload)
    payload['expected_items'] = 12
    template = payload['questions'][0]
    payload['questions'] = []
    for n in range(1, 13):
        q = copy.deepcopy(template)
        q['question_id'] = f'adaptive-q{n}'
        q['content'].update(number=n, statement=f'Questão sintética adaptativa {n}: calcule o resultado solicitado.')
        q['content']['labels']['themes'] = ['Álgebra' if n % 2 else 'Geometria']
        payload['questions'].append(q)
    assert admin.post('/admin/imports', json=payload).status_code == 201
    reason = {'action': 'approve', 'reason': 'Referência sintética para a prática'}
    for q in payload['questions']:
        assert admin.post(f"/admin/reviews/{q['question_id']}:1", json=reason).status_code == 200
    published = {'action': 'publish', 'reason': 'Referência temática para a prática'}
    assert admin.post('/admin/reviews/prova-teste', json=published).status_code == 200
    return payload


def begin(client, key='practice-key-001', **kwargs):
    body = {'objective': 'Praticar', 'area': 'Matemática', 'available_minutes': 15, 'idempotency_key': key, **kwargs}
    return client.post('/practice-sessions', json=body)


def test_session_carries_reasons_without_revealing_answers(student, thematic):
    response = begin(student)
    assert response.status_code == 201
    session = response.json()
    assert session['kind'] == 'practice' and session['selection']['version'] == 'adaptive-v1'
    assert len(session['items']) == 5
    assert all(
        i['recommendation']['reason'] and i['recommendation']['function'] == 'exploracao' for i in session['items']
    )
    audit = student.get(f"/practice-sessions/{session['id']}/recommendations").json()
    for text in (json.dumps(session), json.dumps(audit)):
        assert 'correct_answer' not in text and 'annulled' not in text
    assert [r['position'] for r in audit['recommendations']] == [1, 2, 3, 4, 5]
    assert audit['recommendations'][0]['candidates'][0]['item_id'] == session['items'][0]['id']


def test_start_is_idempotent_and_keys_do_not_cross_kinds(student, thematic, database):
    first = begin(student).json()
    assert begin(student).json()['id'] == first['id']
    assert begin(student, objective='Outro objetivo').status_code == 409
    diagnostic = {
        'objective': 'Praticar',
        'area': 'Matemática',
        'available_minutes': 15,
        'idempotency_key': 'practice-key-001',
    }
    assert student.post('/sessions', json=diagnostic).status_code == 409
    with database() as db:
        assert db.scalar(select(func.count()).select_from(RecommendationEvent)) == 5


def test_sessions_are_private_and_separate_from_diagnostics(student, thematic, client):
    session = begin(student).json()
    assert student.get(f"/sessions/{session['id']}").status_code == 404
    assert student.get('/me/sessions').json()[0]['kind'] == 'practice'
    client.cookies.clear()
    assert client.get(f"/practice-sessions/{session['id']}").status_code == 401


def test_other_student_cannot_read_or_answer(student, thematic, database):
    from fastapi.testclient import TestClient
    from backend.app.main import app

    session = begin(student).json()
    with TestClient(app) as other:
        body = {'name': 'Outra Pessoa', 'email': 'outra@example.com', 'password': 'uma-senha-longa'}
        assert other.post('/auth/register', json=body).status_code == 201
        path = f"/practice-sessions/{session['id']}"
        assert other.get(path).status_code == 404
        assert other.get(path + '/recommendations').status_code == 404
        assert other.post(path + '/finish').status_code == 404
        assert other.get('/me/recommendations').json() == []


def test_finished_practice_feeds_the_state_and_the_next_selection(student, thematic, database):
    session = begin(student, available_minutes=36).json()
    path = f"/practice-sessions/{session['id']}"
    for i in session['items']:
        assert student.put(f"{path}/answers/{i['id']}", json={'choice': 'A'}).status_code == 200
    item = session['items'][0]
    assert student.put(f"{path}/answers/nada", json={'choice': 'A'}).status_code == 404
    finished = student.post(path + '/finish').json()
    assert finished['result']['total'] == 12 and finished['result']['correct'] == 0
    assert finished['items'][0]['correct_answer'] == 'B'
    assert student.post(path + '/finish').json()['finished_at'] == finished['finished_at']
    assert student.put(f"{path}/answers/{item['id']}", json={'choice': 'B'}).status_code == 409
    with database() as db:
        events = list(db.scalars(select(LearningEvent).where(LearningEvent.session_id == session['id'])))
    assert len(events) == 12
    assert all(
        e.context['mode'] == 'practice'
        and e.context['policy_version'] == 'adaptive-v1'
        and e.context['recommendation'] == 'exploracao'
        for e in events
    )
    state = student.get('/me/knowledge-state').json()
    assert {g['independent_attempts'] for g in state['themes']} == {6}
    assert {r['mode'] for g in state['themes'] for r in g['recent']} == {'practice'}
    following = begin(student, key='practice-key-002').json()
    assert {i['recommendation']['function'] for i in following['items']} == {'reforco'}
    assert following['selection']['repeated_items'] == [i['id'] for i in following['items']]
    assert 'em 6 respostas independentes' in following['items'][0]['recommendation']['reason']


def test_exhausted_area_explains_itself(student, thematic):
    for n in range(2):
        session = begin(student, key=f'practice-exhaust-{n}', available_minutes=36)
        assert session.status_code == 201
    third = begin(student, key='practice-exhaust-9')
    assert third.status_code == 422 and 'máximo de vezes' in third.json()['detail']
    assert begin(student, key='practice-other-area', area='Linguagens').status_code == 422


def test_concurrent_start_keeps_one_session_and_one_audit(student, thematic, database):
    with ThreadPoolExecutor(4) as pool_:
        ids = {r.json()['id'] for r in pool_.map(lambda _: begin(student, key='practice-race-01'), range(4))}
    assert len(ids) == 1
    with database() as db:
        assert db.scalar(select(func.count()).select_from(RecommendationEvent)) == 5


def test_deleting_history_removes_recommendations(student, thematic, database):
    begin(student)
    assert student.get('/me/recommendations').json()
    assert student.delete('/me/history').status_code == 204
    assert student.get('/me/recommendations').json() == [] and student.get('/me/sessions').json() == []
    with database() as db:
        assert db.scalar(select(func.count()).select_from(RecommendationEvent)) == 0
