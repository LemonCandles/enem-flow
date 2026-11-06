import copy
import json
import sys

import pytest
from sqlalchemy import func, select

from backend.app import cli
from backend.app.installers import local
from backend.app.installers.curated import install_catalog
from backend.app.models import Exam, ExamRun, QuestionVersion, Review
from backend.app.services.errors import InvalidContent

EXPECTED = {
    'enem-2024-dia2-azul',
    'enem-2024-regular-dia1-caderno-1-azul-ingles',
    'enem-2024-regular-dia1-caderno-1-azul-espanhol',
    'enem-2025-regular-dia1-caderno-1-azul-ingles',
    'enem-2025-regular-dia1-caderno-1-azul-espanhol',
    'enem-2025-regular-dia2-caderno-7-azul',
}


def test_local_cli_installs_six_bundled_exams_and_stays_idempotent(
    database, client, monkeypatch, capsys, tmp_path, exam_payload
):
    directory = tmp_path / 'generated'
    directory.mkdir()
    for exam_id in local.AUTOMATIC:
        source = local.GENERATED / f'{exam_id}.json'
        (directory / source.name).write_bytes(source.read_bytes())
    # A separately generated archive exam must not be published by local setup.
    (directory / 'prova-teste.json').write_text(json.dumps(exam_payload))
    monkeypatch.setattr(local, 'GENERATED', directory)
    monkeypatch.setattr(cli, 'SessionLocal', database)
    monkeypatch.setattr(sys, 'argv', ['cli', 'local-catalog'])
    cli.main()
    assert json.loads(capsys.readouterr().out)['automatic']['published'] == 5
    catalog = client.get('/exams').json()
    assert {exam['id'] for exam in catalog} == EXPECTED
    assert sum(exam['item_count'] for exam in catalog) == 540
    assert all(exam['kind'] == 'complete' and exam['approved_items'] == 90 for exam in catalog)
    automatic = [exam for exam in catalog if exam['id'] != 'enem-2024-dia2-azul']
    assert all(exam['content_quality']['origin'] == 'automatic' for exam in automatic)
    assert all(exam['content_quality']['review_status'] == 'pending' for exam in automatic)
    assert all(exam['content_quality']['blocking_issues'] == 0 for exam in automatic)
    assert 'correct_answer' not in json.dumps(client.get('/exams/' + automatic[0]['id']).json())
    with database() as db:
        versions = {exam.id: list(exam.items) for exam in db.scalars(select(Exam))}
        reviews = db.scalar(select(func.count()).select_from(Review))
    cli.main()
    assert json.loads(capsys.readouterr().out)['automatic']['published'] == 0
    with database() as db:
        assert {exam.id: exam.items for exam in db.scalars(select(Exam))} == versions
        assert db.scalar(select(func.count()).select_from(Review)) == reviews


def test_local_upgrade_withdraws_legacy_bootstrap_and_keeps_attempts(database, student):
    with database.begin() as db:
        install_catalog(db, publish=True)
        section = db.get(Exam, local.LEGACY_SECTION)
        contents = {key: copy.deepcopy(db.get(QuestionVersion, key).content) for key in section.items}
    started = student.post('/exam-runs', json=dict(exam_id=local.LEGACY_SECTION, idempotency_key='legacy-section-test'))
    assert started.status_code == 201
    run = started.json()
    assert (
        student.put(f'/exam-runs/{run["id"]}/answers/{run["items"][0]["id"]}', json=dict(choice='B')).status_code == 200
    )
    assert student.post(f'/exam-runs/{run["id"]}/finish').status_code == 200
    with database() as db:
        attempt = db.get(ExamRun, run['id'])
        before = {column.name: copy.deepcopy(getattr(attempt, column.name)) for column in ExamRun.__table__.columns}
    for _ in range(2):
        with database.begin() as db:
            local.install_local_catalog(db)
        with database() as db:
            assert db.get(Exam, local.LEGACY_SECTION).status == 'withdrawn'
            assert all(db.get(QuestionVersion, key).content == content for key, content in contents.items())
            attempt = db.get(ExamRun, run['id'])
            assert {column.name: getattr(attempt, column.name) for column in ExamRun.__table__.columns} == before
        assert {exam['id'] for exam in student.get('/exams').json()} == EXPECTED
        assert student.get(f'/exam-runs/{run["id"]}').status_code == 200


def test_local_upgrade_respects_manual_publication_withdrawal_and_rejection(database, admin):
    with database.begin() as db:
        install_catalog(db, publish=True)
        local.install_local_catalog(db)
    for exam_id, action in [(local.LEGACY_SECTION, 'publish'), (local.REVIEWED, 'withdraw')]:
        assert (
            admin.post(
                '/admin/reviews/' + exam_id,
                json=dict(action=action, reason='Decisão manual que a instalação deve preservar'),
            ).status_code
            == 200
        )
    with database() as db:
        automatic = db.get(Exam, local.AUTOMATIC[0])
        key = automatic.items[0]
    assert (
        admin.post(
            '/admin/reviews/' + key,
            json=dict(action='reject', reason='Conferência manual pendente da versão automática'),
        ).status_code
        == 200
    )
    with database.begin() as db:
        local.install_local_catalog(db)
        assert db.get(Exam, local.LEGACY_SECTION).status == 'published'
        assert db.get(Exam, local.REVIEWED).status == 'withdrawn'
        assert db.get(Exam, local.AUTOMATIC[0]).status == 'in_review'
        assert db.get(QuestionVersion, key).status == 'in_review'


@pytest.mark.parametrize('failure', ['missing_file', 'missing_asset'])
def test_local_upgrade_fails_without_installing_a_partial_catalog(database, tmp_path, monkeypatch, failure):
    with database.begin() as db:
        install_catalog(db, publish=True)
        original = {exam.id: (exam.status, list(exam.items)) for exam in db.scalars(select(Exam))}
        reviews = db.scalar(select(func.count()).select_from(Review))
        versions = db.scalar(select(func.count()).select_from(QuestionVersion))
    directory = tmp_path / 'generated'
    directory.mkdir()
    for exam_id in local.AUTOMATIC:
        source = local.GENERATED / f'{exam_id}.json'
        (directory / source.name).write_bytes(source.read_bytes())
    broken = directory / f'{local.AUTOMATIC[-1]}.json'
    if failure == 'missing_file':
        broken.unlink()
    else:
        payload = json.loads(broken.read_text())
        payload['questions'][0]['content']['images'].append(dict(path='/assets/missing-test.png', alt='Figura ausente'))
        broken.write_text(json.dumps(payload))
    monkeypatch.setattr(local, 'GENERATED', directory)
    with database.begin() as db:
        with pytest.raises((FileNotFoundError, InvalidContent)):
            local.install_local_catalog(db)
    with database() as db:
        assert {exam.id: (exam.status, exam.items) for exam in db.scalars(select(Exam))} == original
        assert db.scalar(select(func.count()).select_from(Review)) == reviews
        assert db.scalar(select(func.count()).select_from(QuestionVersion)) == versions
