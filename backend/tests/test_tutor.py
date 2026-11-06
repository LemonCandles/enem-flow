"""Tutor in practice: approved material, help levels, provider failures and the evidence they leave."""

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from backend.app.main import app
from backend.app.models import HelpEvent, LearningEvent, TutorMaterial
from backend.app.services import tutor_provider
from backend.app.services.tutor_provider import ProviderResult

LEVELS = {
    'orientation': 'Identifique o que a questão pede e organize os dados antes de calcular.',
    'hint': 'Compare o resultado de cada passo com as unidades informadas no enunciado.',
    'solution': 'Calculando passo a passo, chega-se ao valor da alternativa B.',
}


def begin(client, key='tutor-practice-001'):
    body = {'objective': 'Praticar', 'area': 'Matemática', 'available_minutes': 15, 'idempotency_key': key}
    response = client.post('/practice-sessions', json=body)
    assert response.status_code == 201
    return response.json()


def approve_material(admin, version_id, levels=LEVELS):
    created = admin.post(f'/admin/tutor/questions/{version_id}/materials', json=levels)
    assert created.status_code == 201, created.text
    reviewed = admin.post(
        f"/admin/tutor/materials/{created.json()['id']}/review",
        json={'action': 'approve', 'reason': 'Material conferido com a questão'},
    )
    assert reviewed.status_code == 200, reviewed.text
    return reviewed.json()


def ask(client, session, item, level, key):
    return client.post(
        f"/practice-sessions/{session['id']}/items/{item['id']}/help",
        json={'level': level, 'idempotency_key': key},
    )


@pytest.fixture
def provider(monkeypatch):
    """A configured provider whose answers each test decides; counts every call."""
    for name, value in {
        'GROQ_API_KEY': 'chave-de-teste',
        'TUTOR_MODEL': 'modelo-teste',
        'TUTOR_PRICE_INPUT_PER_MTOK': '0.5',
        'TUTOR_PRICE_OUTPUT_PER_MTOK': '0.8',
        'TUTOR_MAX_COST_USD': '0.05',
    }.items():
        monkeypatch.setenv(name, value)
    calls = []
    answers = []

    def complete(settings, messages):
        calls.append(messages)
        return answers.pop(0) if answers else ProviderResult('ok', {'mensagem': 'Releia o enunciado.'}, 100, 20, 12)

    monkeypatch.setattr(tutor_provider, 'complete_json', complete)
    return calls, answers


@pytest.fixture
def practice(student, admin, thematic):
    session = begin(student)
    item = session['items'][0]
    assert item['help'] == {'available': False, 'next_level': None, 'delivered': []}
    approve_material(admin, item['id'])
    return student, student.get(f"/practice-sessions/{session['id']}").json(), item


def test_help_comes_in_order_from_approved_material_and_is_idempotent(practice, provider, database):
    client, session, item = practice
    calls, _ = provider
    assert session['items'][0]['help']['available'] and session['items'][0]['help']['next_level'] == 'orientation'
    assert ask(client, session, item, 'hint', 'tutor-hint-0001').status_code == 409
    first = ask(client, session, item, 'orientation', 'tutor-orientation-1')
    assert first.status_code == 200
    data = first.json()
    assert data['outcome'] == 'delivered' and data['mode'] == 'tutor' and data['message'] == 'Releia o enunciado.'
    assert data['provider']['model'] == 'modelo-teste' and data['provider']['cost_usd'] == pytest.approx(0.000066)
    assert data['provider']['latency_ms'] == 12 and data['provider']['prompt_version'] == 'tutor-prompt-v1'
    # Same key or same level: the delivered help returns, without a new call or charge.
    assert ask(client, session, item, 'orientation', 'tutor-orientation-1').json()['id'] == data['id']
    assert ask(client, session, item, 'orientation', 'tutor-orientation-2').json()['id'] == data['id']
    assert len(calls) == 1
    # Lower levels never send the solution to the provider.
    assert LEVELS['solution'] not in calls[0][1]['content'] and LEVELS['orientation'] in calls[0][1]['content']
    assert 'correct_answer' not in str(calls[0])
    with database() as db:
        assert db.scalar(select(func.count()).select_from(HelpEvent)) == 1


def test_provider_failures_deliver_the_approved_text(practice, provider):
    client, session, item = practice
    _, answers = provider
    answers.append(ProviderResult('timeout', latency_ms=10000, error='Tempo limite do provedor excedido.'))
    timed_out = ask(client, session, item, 'orientation', 'tutor-timeout-01').json()
    assert timed_out['mode'] == 'material' and timed_out['message'] == LEVELS['orientation']
    assert timed_out['provider']['status'] == 'timeout' and timed_out['outcome'] == 'delivered'
    # A hint that names the answer is refused and replaced by the approved hint.
    answers.append(ProviderResult('ok', {'mensagem': 'A alternativa correta é B.'}, 100, 20, 30))
    leaked = ask(client, session, item, 'hint', 'tutor-leak-0001').json()
    assert leaked['mode'] == 'material' and leaked['message'] == LEVELS['hint']
    assert leaked['provider']['status'] == 'invalid'
    answers.append(ProviderResult('ok', {'outra': 'chave'}, 100, 20, 30))
    malformed = ask(client, session, item, 'solution', 'tutor-malformed-1').json()
    assert malformed['mode'] == 'material' and malformed['message'] == LEVELS['solution']


def test_without_configuration_the_material_is_delivered(practice):
    client, session, item = practice
    data = ask(client, session, item, 'orientation', 'tutor-disabled-1').json()
    assert data['mode'] == 'material' and data['provider']['status'] == 'disabled'
    assert 'GROQ_API_KEY' in data['provider']['missing']


def test_limits_keep_the_provider_out(practice, provider, monkeypatch):
    client, session, item = practice
    calls, _ = provider
    monkeypatch.setenv('TUTOR_MAX_COST_USD', '0.0000001')
    data = ask(client, session, item, 'orientation', 'tutor-cost-0001').json()
    assert data['provider']['status'] == 'cost_limit' and data['mode'] == 'material'
    monkeypatch.setenv('TUTOR_MAX_COST_USD', '0.05')
    monkeypatch.setenv('TUTOR_DAILY_LIMIT', '0')
    data = ask(client, session, item, 'hint', 'tutor-daily-0001').json()
    assert data['provider']['status'] == 'daily_limit' and not calls


def test_request_that_never_returns_is_not_help(practice, provider, database, monkeypatch):
    client, session, item = practice

    def broken(settings, messages):
        raise RuntimeError('conexão interrompida')

    monkeypatch.setattr(tutor_provider, 'complete_json', broken)
    with pytest.raises(RuntimeError):
        ask(client, session, item, 'orientation', 'tutor-broken-001')
    with database() as db:
        event = db.scalar(select(HelpEvent))
        assert event.outcome == 'requested' and event.delivered_at is None
    state = client.get(f"/practice-sessions/{session['id']}").json()
    assert state['items'][0]['help']['delivered'] == []
    # Retrying the same key completes the same request.
    monkeypatch.setattr(tutor_provider, 'complete_json', lambda s, m: ProviderResult('ok', {'mensagem': 'Ok.'}))
    retried = ask(client, session, item, 'orientation', 'tutor-broken-001').json()
    assert retried['id'] == event.id and retried['outcome'] == 'delivered'


def test_assisted_items_leave_the_independent_evidence(practice, database):
    client, session, item = practice
    path = f"/practice-sessions/{session['id']}"
    assert ask(client, session, item, 'orientation', 'tutor-evidence-1').status_code == 200
    for entry in session['items']:
        assert client.put(f"{path}/answers/{entry['id']}", json={'choice': 'B'}).status_code == 200
    finished = client.post(path + '/finish').json()
    assert all(not i['help']['available'] for i in finished['items'])
    with database() as db:
        events = {e.item_id: e.context for e in db.scalars(select(LearningEvent))}
    assert events[item['id']]['help_used'] is True and events[item['id']]['help']['levels'] == ['orientation']
    assert all(c['help_used'] is False for key, c in events.items() if key != item['id'])
    state = client.get('/me/knowledge-state').json()
    assert sum(g['assisted_attempts'] for g in state['themes']) == 1
    assert sum(g['independent_attempts'] for g in state['themes']) == len(session['items']) - 1
    assert ask(client, session, item, 'hint', 'tutor-after-finish').status_code == 409


def test_help_is_private_exported_and_erased(practice):
    client, session, item = practice
    assert ask(client, session, item, 'orientation', 'tutor-private-01').status_code == 200
    with TestClient(app) as other:
        body = {'name': 'Outra Pessoa', 'email': 'outra@example.com', 'password': 'uma-senha-longa'}
        assert other.post('/auth/register', json=body).status_code == 201
        assert ask(other, session, item, 'orientation', 'tutor-other-001').status_code == 404
        assert other.get('/me/help-events').json() == []
    exported = client.get('/me/help-events').json()
    assert [e['level'] for e in exported] == ['orientation']
    assert client.delete('/me/history').status_code == 204
    assert client.get('/me/help-events').json() == []


def test_exams_and_diagnostics_have_no_help(student, admin, thematic):
    exam = student.post('/exam-runs', json={'exam_id': 'prova-teste', 'idempotency_key': 'tutor-exam-0001'}).json()
    item = exam['items'][0]
    approve_material(admin, item['id'])
    assert ask(student, exam, item, 'orientation', 'tutor-exam-help-1').status_code == 404
    diagnostic = student.post(
        '/sessions',
        json={'objective': 'Medir', 'area': 'Matemática', 'available_minutes': 15, 'idempotency_key': 'tutor-diag-01'},
    ).json()
    assert ask(student, diagnostic, diagnostic['items'][0], 'orientation', 'tutor-diag-help').status_code == 404
    assert 'help' not in diagnostic['items'][0]


def test_material_rules_and_outdated_content(student, admin, thematic, database):
    session = begin(student)
    item = session['items'][0]
    leaking = dict(LEVELS, hint='Marque a alternativa B sem calcular.')
    refused = admin.post(f"/admin/tutor/questions/{item['id']}/materials", json=leaking)
    assert refused.status_code == 422 and 'revela o gabarito' in refused.json()['detail']
    proposal = admin.post(f"/admin/tutor/questions/{item['id']}/materials", json=LEVELS).json()
    # A proposal is not served until a human approves it.
    data = student.get(f"/practice-sessions/{session['id']}").json()
    assert not data['items'][0]['help']['available']
    assert admin.get('/admin/tutor/exams/prova-teste').json()['items'][0]['material'] in {'proposal', 'none'}
    # Content corrected after the proposal: approval is refused and old material is not served.
    content = admin.get("/admin/exams/prova-teste").json()['items']
    version = next(q for q in content if q['id'] == item['id'])
    edited = dict(version['content'], statement=version['content']['statement'] + ' Versão corrigida.')
    assert (
        admin.put(
            f"/admin/questions/{item['id']}", json={'content': edited, 'reason': 'Correção do enunciado da questão'}
        ).status_code
        == 200
    )
    with database.begin() as db:
        db.get(TutorMaterial, proposal['id']).content_sha256 = '0' * 64
    review = admin.post(
        f"/admin/tutor/materials/{proposal['id']}/review", json={'action': 'approve', 'reason': 'Tentativa de aprovar'}
    )
    assert review.status_code == 409


GOOD = {
    'orientacao': 'Pense na proporção entre as grandezas.',
    'pista': 'Monte a regra de três com os valores do enunciado.',
    'resolucao': 'Resolvendo a proporção, chega-se ao valor pedido. Alternativa B.',
}


def test_generated_material_is_approved_automatically(student, admin, thematic, provider, database):
    _, answers = provider
    session = begin(student)
    item = session['items'][0]
    answers.append(ProviderResult('ok', GOOD, 300, 200, 50))
    created = admin.post(f"/admin/tutor/questions/{item['id']}/generate")
    assert created.status_code == 201, created.text
    data = created.json()
    assert data['status'] == 'approved' and data['origin'] == 'llm'
    assert data['provenance']['approval'] == 'automatic' and data['provenance']['model'] == 'modelo-teste'
    assert 'sem revisão humana' in data['review_reason']
    assert student.get(f"/practice-sessions/{session['id']}").json()['items'][0]['help']['available']
    status = admin.get('/admin/tutor/status').json()
    assert status['enabled'] and 'chave' not in str(status)


@pytest.mark.parametrize(
    'levels, reason',
    [
        (dict(GOOD, pista='A alternativa B é a correta.'), 'revela o gabarito'),
        (dict(GOOD, resolucao='Resolvendo a proporção. Alternativa C.'), 'não chega ao gabarito'),
        ({'orientacao': 'Só orientação.'}, 'fora do formato'),
    ],
)
def test_generated_material_outside_the_rules_is_not_approved(admin, thematic, provider, database, levels, reason):
    _, answers = provider
    answers.append(ProviderResult('ok', levels))
    version = admin.get('/admin/exams/prova-teste').json()['items'][0]['id']
    response = admin.post(f'/admin/tutor/questions/{version}/generate')
    assert response.status_code == 503 and reason in response.json()['detail']
    with database() as db:
        assert db.scalar(select(func.count()).select_from(TutorMaterial)) == 0


def test_generation_without_provider_explains_the_configuration(admin, thematic):
    version = admin.get('/admin/exams/prova-teste').json()['items'][0]['id']
    response = admin.post(f'/admin/tutor/questions/{version}/generate')
    assert response.status_code == 503 and 'GROQ_API_KEY' in response.json()['detail']


def test_batch_covers_every_published_question_once_and_resumes(admin, thematic, provider, database):
    from backend.app.services.tutor import generate_all

    calls, answers = provider
    answers.extend([ProviderResult('error', error='RateLimitError'), *[ProviderResult('ok', GOOD)] * 3])
    waits = []
    with database() as db:
        first = generate_all(db, limit=2, pause=0, log=lambda _: None, sleep=waits.append)
    assert first['approved'] == 2 and first['remaining'] == 10 and len(waits) >= 1
    answers.extend([ProviderResult('ok', GOOD)] * 40)
    with database() as db:
        second = generate_all(db, pause=0, log=lambda _: None, sleep=lambda _: None)
    assert second['remaining'] == 0 and second['approved'] == 10 and not second['failed']
    with database() as db:
        third = generate_all(db, pause=0, log=lambda _: None, sleep=lambda _: None)
    assert third == {'approved': 0, 'failed': [], 'remaining': 0}
    with database() as db:
        assert db.scalar(select(func.count()).select_from(TutorMaterial)) == 12
