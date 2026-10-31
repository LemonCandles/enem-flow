import copy
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.db import Base, get_db
from backend.app.main import app
from backend.app.models import User
from backend.app.security import hash_password


@pytest.fixture
def database(tmp_path):
    url = os.getenv("TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    if os.getenv("TEST_DATABASE_URL") and "test" not in url.rsplit("/", 1)[-1]:
        raise RuntimeError("TEST_DATABASE_URL deve apontar para um banco com 'test' no nome")
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {})
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def configure(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    def override():
        with factory() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
    app.dependency_overrides[get_db] = override
    yield factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(database):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def student(client):
    response = client.post('/auth/register', json={"name": "Aluno Teste", "email": "aluno@example.com", "password": "uma-senha-longa"})
    assert response.status_code == 201
    return client


@pytest.fixture
def admin(database):
    with database.begin() as db:
        db.add(User(name="Revisor", email="curador@example.com", password_hash=hash_password("senha-admin-teste"), role="admin"))
    with TestClient(app) as client:
        assert client.post('/auth/login', json={"email": "curador@example.com", "password": "senha-admin-teste"}).status_code == 200
        yield client


@pytest.fixture
def exam_payload():
    def question(number, answer, annulled=False):
        return {"question_id": f"teste-q{number}", "content": {
            "number": number, "area": "Matemática", "statement": f"Questão sintética {number} exclusiva para teste: escolha a alternativa.",
            "images": [], "alternatives": [{"letter": l, "text": f"Opção {l}"} for l in "ABCDE"],
            "correct_answer": answer, "annulled": annulled, "page": 2,
            "labels": {"discipline": "Matemática", "themes": ["Teste"] if number == 1 else [], "skills": []}
        }}
    return {"schema_version": "1.0", "id": "prova-teste", "title": "Prova sintética de teste", "year": 2024,
            "application": "Regular", "booklet": "Azul", "day": 2, "kind": "collection", "expected_items": 3,
            "duration_minutes": 10, "source": {"url": "https://example.com/original.pdf", "answer_key_url": "https://example.com/key.pdf",
            "sha256": "a" * 64, "answer_key_sha256": "b" * 64, "publisher": "Fixture"},
            "questions": [question(1, "B"), question(2, "C"), question(3, None, True)]}


@pytest.fixture
def published(admin, exam_payload):
    assert admin.post('/admin/imports', json=exam_payload).status_code == 201
    for question in exam_payload['questions']:
        response = admin.post(f"/admin/reviews/{question['question_id']}:1", json={"action": "approve", "reason": "Conferida para teste automatizado"})
        assert response.status_code == 200
    assert admin.post('/admin/reviews/prova-teste', json={"action": "publish", "reason": "Conjunto sintético validado para teste"}).status_code == 200
    return exam_payload
