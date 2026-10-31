import copy
import json
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.app.main import app
from backend.app.models import AuthSession, ExamRun, LearningEvent, RecoveryToken, User
from backend.app.schemas import ExamImport
from backend.app.security import digest


def start(student):
    response = student.post('/exam-runs', json={"exam_id": "prova-teste", "idempotency_key": "test-key-00001"})
    assert response.status_code == 201
    return response.json()


def test_authentication_and_session_revocation(student, database):
    assert student.get('/me').json()['name'] == 'Aluno Teste'
    with database() as db:
        user = db.scalar(select(User).where(User.email == 'aluno@example.com'))
        assert user.password_hash.startswith('scrypt$')
        assert 'uma-senha-longa' not in user.password_hash
        assert db.scalar(select(AuthSession)).token_hash != student.cookies.get('enem_session')
    cookie = student.cookies.get('enem_session')
    assert student.post('/auth/logout').status_code == 204
    assert student.get('/me').status_code == 401
    student.cookies.set('enem_session', cookie)
    assert student.get('/me').status_code == 401


def test_registration_validation_csrf_and_roles(client):
    assert client.post('/auth/register', json={"name": "Pessoa", "email": "invalido", "password": "short"}).status_code == 422
    response = client.post('/auth/register', json={"name": "Pessoa", "email": "pessoa@example.com", "password": "senha-secreta-forte", "role": "admin"})
    assert response.status_code == 422
    assert 'senha-secreta-forte' not in response.text
    assert client.post('/auth/login', headers={"Origin": "https://evil.example"}, json={"email": "pessoa@example.com", "password": "senha-secreta-forte"}).status_code == 403
    assert client.get('/admin/exams').status_code == 401


def test_student_cannot_curate(student):
    assert student.get('/admin/exams').status_code == 403
    assert student.post('/admin/imports', json={}).status_code == 403


def test_draft_visibility_and_publication_gate(admin, student, exam_payload):
    assert admin.post('/admin/imports', json=exam_payload).status_code == 201
    assert student.get('/exams').json() == []
    assert student.get('/exams/prova-teste').status_code == 404
    assert student.post('/exam-runs', json={"exam_id": "prova-teste", "idempotency_key": "unpublished-key"}).status_code == 404
    assert admin.post('/admin/reviews/prova-teste', json={"action": "publish", "reason": "Tentar sem aprovação de itens"}).status_code == 409


def test_answer_key_never_leaks_before_finish(published, student):
    for payload in [student.get('/exams').json(), student.get('/exams/prova-teste').json(), start(student)]:
        serialized = json.dumps(payload)
        assert 'correct_answer' not in serialized
        assert 'answer_key_url' not in serialized
        assert 'annulled' not in serialized


def test_start_idempotency_and_draft_persistence(published, student):
    run = start(student)
    assert start(student)['id'] == run['id']
    endpoint = f"/exam-runs/{run['id']}/answers/teste-q1:1"
    assert student.put(endpoint, json={"choice": "A"}).status_code == 200
    assert student.put(endpoint, json={"choice": "B"}).status_code == 200
    assert student.get(f"/exam-runs/{run['id']}").json()['answers']['teste-q1:1'] == 'B'
    assert student.put(endpoint, json={"choice": None}).json()['answers']['teste-q1:1'] is None
    assert student.get('/me/progress').json()['completed_runs'] == 0


def test_scoring_annulment_blank_and_idempotent_finish(published, student, database):
    run = start(student)
    student.put(f"/exam-runs/{run['id']}/answers/teste-q1:1", json={"choice": "B"})
    student.put(f"/exam-runs/{run['id']}/answers/teste-q3:1", json={"choice": "E"})
    first = student.post(f"/exam-runs/{run['id']}/finish")
    assert first.status_code == 200
    data = first.json()
    assert data['result'] == {"correct": 1, "total": 2, "answered": 1, "unanswered": 1, "incorrect": 0, "annulled": 1, "percentage": 50.0}
    assert student.post(f"/exam-runs/{run['id']}/finish").json() == data
    assert student.put(f"/exam-runs/{run['id']}/answers/teste-q1:1", json={"choice": "A"}).status_code == 409
    assert len(student.get('/me/history').json()) == 1
    with database() as db:
        assert db.scalar(select(func.count()).select_from(LearningEvent)) == 3
    progress = student.get('/me/progress').json()
    assert progress['completed_runs'] == 1
    assert progress['summary']['annulled'] == 1
    assert progress['coverage']['theme'] == {"classified": 1, "total": 2, "percentage": 50.0}
    assert progress['coverage']['skill']['percentage'] == 0
    assert progress['breakdown']['theme'][0]['name'] == 'Ainda não classificado'


def test_user_isolation_including_finish_and_history(published, student):
    run = start(student)
    with TestClient(app) as other:
        other.post('/auth/register', json={"name": "Outra Pessoa", "email": "outra@example.com", "password": "outra-senha-longa"})
        assert other.get(f"/exam-runs/{run['id']}").status_code == 404
        assert other.put(f"/exam-runs/{run['id']}/answers/teste-q1:1", json={"choice": "B"}).status_code == 404
        assert other.post(f"/exam-runs/{run['id']}/finish").status_code == 404
        assert other.get('/me/history').json() == []
        assert other.get('/me/progress').json()['completed_runs'] == 0
        other.delete('/me/history')
    assert student.get(f"/exam-runs/{run['id']}").status_code == 200


def test_concurrent_finish_serializes_and_emits_once(published, student, database):
    run = start(student)
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: student.post(f"/exam-runs/{run['id']}/finish"), range(4)))
    assert all(r.status_code == 200 for r in responses)
    assert all(r.json() == responses[0].json() for r in responses)
    with database() as db:
        assert db.scalar(select(func.count()).select_from(LearningEvent)) == 3


def test_revisions_preserve_old_open_and_finished_runs(published, student, admin):
    run = start(student)
    original = admin.get('/admin/exams/prova-teste').json()['items'][0]['content']
    changed = {**original, 'statement': 'Enunciado corrigido em uma nova versão.', 'correct_answer': 'D'}
    assert admin.put('/admin/questions/teste-q1:1', json={"content": changed, "reason": "Correção de conteúdo para testar versões"}).json()['version'] == 2
    assert student.get('/exams').json() == []
    old = student.get(f"/exam-runs/{run['id']}").json()['items'][0]
    assert old['statement'] == original['statement'] and old['version'] == 1
    student.put(f"/exam-runs/{run['id']}/answers/teste-q1:1", json={"choice": "B"})
    result = student.post(f"/exam-runs/{run['id']}/finish").json()
    assert result['result']['correct'] == 1
    assert result['items'][0]['correct_answer'] == 'B'
    admin.post('/admin/reviews/teste-q1:2', json={"action": "approve", "reason": "Revisão da segunda versão para teste"})
    assert admin.post('/admin/reviews/prova-teste', json={"action": "publish", "reason": "Publicação com a versão corrigida"}).status_code == 200
    newer = student.post('/exam-runs', json={"exam_id": "prova-teste", "idempotency_key": "new-version-key"}).json()
    assert newer['items'][0]['version'] == 2
    assert student.get(f"/exam-runs/{run['id']}").json() == result


def test_import_rejects_duplicate_numbers_and_missing_assets(admin, exam_payload):
    payload = copy.deepcopy(exam_payload)
    payload['questions'][1]['content']['number'] = 1
    assert admin.post('/admin/imports', json=payload).status_code == 422
    payload = copy.deepcopy(exam_payload)
    payload['questions'][0]['content']['images'] = [{"path": "/assets/absent.png", "alt": "Imagem de teste ausente"}]
    assert admin.post('/admin/imports', json=payload).status_code == 422
    payload['questions'][0]['content']['images'][0]['path'] = '/assets/../private.png'
    assert admin.post('/admin/imports', json=payload).status_code == 422


def test_invalid_choice_and_foreign_item(published, student):
    run = start(student)
    assert student.put(f"/exam-runs/{run['id']}/answers/teste-q1:1", json={"choice": "Z"}).status_code == 422
    assert student.put(f"/exam-runs/{run['id']}/answers/foreign:1", json={"choice": "A"}).status_code == 404


def test_all_annulled_has_no_percentage(admin, student, exam_payload):
    for question in exam_payload['questions']:
        question['content']['annulled'] = True
        question['content']['correct_answer'] = None
    admin.post('/admin/imports', json=exam_payload)
    for question in exam_payload['questions']:
        admin.post(f"/admin/reviews/{question['question_id']}:1", json={"action": "approve", "reason": "Questões anuladas em cenário de teste"})
    admin.post('/admin/reviews/prova-teste', json={"action": "publish", "reason": "Coleção anulada para cenário de teste"})
    run = start(student)
    result = student.post(f"/exam-runs/{run['id']}/finish").json()['result']
    assert result['total'] == 0 and result['percentage'] is None and result['annulled'] == 3
    assert student.get('/me/progress').json()['coverage']['area']['total'] == 0


def test_deleting_history_removes_events(published, student, database):
    run = start(student)
    student.post(f"/exam-runs/{run['id']}/finish")
    assert student.delete('/me/history').status_code == 204
    assert student.get('/me/history').json() == []
    assert student.get('/me').status_code == 200
    with database() as db:
        assert db.scalar(select(func.count()).select_from(LearningEvent)) == 0
        assert db.scalar(select(func.count()).select_from(ExamRun)) == 0


def test_recovery_token_is_single_use_and_revokes_sessions(student, database):
    token = secrets.token_urlsafe(32)
    with database.begin() as db:
        user = db.scalar(select(User).where(User.email == 'aluno@example.com'))
        db.add(RecoveryToken(token_hash=digest(token), user_id=user.id, expires_at=time.time() + 100))
    body = {"token": token, "password": "nova-senha-segura"}
    assert student.post('/auth/reset-password', json=body).status_code == 200
    assert student.post('/auth/reset-password', json=body).status_code == 400
    assert student.get('/me').status_code == 401
    assert student.post('/auth/login', json={"email": "aluno@example.com", "password": "nova-senha-segura"}).status_code == 200


def test_login_throttle_counts_failed_requests(client):
    for _ in range(30):
        assert client.post('/auth/login', json={"email": "none@example.com", "password": "wrong-password"}).status_code == 401
    assert client.post('/auth/login', json={"email": "none@example.com", "password": "wrong-password"}).status_code == 429


def test_bundled_official_exam_integrity():
    import hashlib
    root = Path(__file__).resolve().parents[2]
    data = ExamImport.model_validate_json((root / 'data/enem-2024-dia2-azul.json').read_text())
    assert data.kind == 'complete' and len(data.questions) == data.expected_items == 90
    assert [q.content.number for q in data.questions] == list(range(91, 181))
    assert [q.content.number for q in data.questions if q.content.annulled] == [129]
    for q in data.questions:
        assert q.content.layout['blocks']
        for image in q.content.images:
            assert (root / 'data' / image.path.lstrip('/')).is_file()
    assert hashlib.sha256((root / 'data/sources/enem-2024-dia2-azul.pdf').read_bytes()).hexdigest() == data.source.sha256
    assert hashlib.sha256((root / 'data/sources/enem-2024-dia2-azul-gabarito.pdf').read_bytes()).hexdigest() == data.source.answer_key_sha256
