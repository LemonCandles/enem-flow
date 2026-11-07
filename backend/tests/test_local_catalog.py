import copy
import json
import sys

import pytest
from sqlalchemy import func, select

from backend.app import cli
from backend.app.installers import local
from backend.app.installers.curated import install_catalog
from backend.app.installers.generated import GENERATED
from backend.app.models import CanonicalQuestion, Exam, ExamRun, QuestionVersion, Review
from backend.app.services.identity import signatures
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
    # The team verified the bundled automatic exams; the origin stays visible.
    assert all(exam['content_quality']['review_status'] == 'reviewed' for exam in automatic)
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


def copy_generated(directory, change=None):
    directory.mkdir()
    for exam_id in local.AUTOMATIC:
        payload = json.loads((GENERATED / f'{exam_id}.json').read_text())
        if change:
            change(payload)
        (directory / f'{exam_id}.json').write_text(json.dumps(payload, ensure_ascii=False))
    return directory


def test_verification_updates_an_older_install_with_new_versions(database, student, monkeypatch, tmp_path):
    shared, first, last = local.AUTOMATIC[2], local.AUTOMATIC[0], local.AUTOMATIC[-1]

    def older(payload):
        # Older files leaked the booklet microtext into the text of the questions.
        for question in payload['questions']:
            if payload['id'] in (shared, local.AUTOMATIC[3], last) and question['content']['number'] in (20, 91):
                question['content']['alternatives'][4]['text'] += ' ENEM2025ENEM2025ENEM2025'
        if payload['id'] == first:
            content = payload['questions'][0]['content']
            content['correct_answer'] = 'A' if content['correct_answer'] != 'A' else 'B'

    monkeypatch.setattr(local, 'GENERATED', copy_generated(tmp_path / 'older', older))
    monkeypatch.setattr(local, 'VERIFIED', ())
    with database.begin() as db:
        install_catalog(db, publish=True)
        local.install_local_catalog(db)
        old_key = next(key for key in db.get(Exam, last).items if key.endswith('-q91:1'))
    started = student.post('/exam-runs', json=dict(exam_id=last, idempotency_key='verificacao-teste'))
    run = started.json()
    item = next(i for i in run['items'] if i['id'] == old_key)
    assert student.put(f'/exam-runs/{run["id"]}/answers/{item["id"]}', json=dict(choice='C')).status_code == 200
    with database() as db:
        before = {
            column.name: copy.deepcopy(getattr(db.get(ExamRun, run['id']), column.name))
            for column in ExamRun.__table__.columns
        }

    monkeypatch.setattr(local, 'GENERATED', copy_generated(tmp_path / 'verified'))
    monkeypatch.setattr(local, 'VERIFIED', local.AUTOMATIC)
    with database.begin() as db:
        result = local.install_local_catalog(db)['verified']
    assert result['new_versions'] == 3
    assert set(result['confirmed']) == set(local.AUTOMATIC) - {first}
    assert [entry['id'] for entry in result['skipped']] == [first]
    with database() as db:
        exam = db.get(Exam, last)
        assert exam.source['automatic_archive']['review_status'] == 'reviewed'
        assert old_key not in exam.items and db.get(QuestionVersion, old_key).status == 'approved'
        new = next(db.get(QuestionVersion, key) for key in exam.items if key.endswith('-q91:2'))
        assert 'ENEM2025' not in new.content['alternatives'][4]['text']
        # Both booklets carry the same corrected item, so its identity follows the correction.
        both = [
            next(db.get(QuestionVersion, key) for key in db.get(Exam, exam_id).items if key.endswith('-q20:2'))
            for exam_id in (shared, local.AUTOMATIC[3])
        ]
        assert both[0].canonical_id == both[1].canonical_id
        assert db.get(CanonicalQuestion, both[0].canonical_id).signature == signatures(both[0].content)[0]
        assert db.get(Exam, first).source['automatic_archive']['review_status'] == 'pending'
        attempt = db.get(ExamRun, run['id'])
        assert {column.name: getattr(attempt, column.name) for column in ExamRun.__table__.columns} == before
        reviews = db.scalar(select(func.count()).select_from(Review))
    with database.begin() as db:
        assert local.install_local_catalog(db)['verified'] == dict(
            confirmed=[], new_versions=0, skipped=[dict(id=first, reason=result['skipped'][0]['reason'])]
        )
    with database() as db:
        assert db.scalar(select(func.count()).select_from(Review)) == reviews


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
