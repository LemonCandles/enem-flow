"""Tutor IDs fit canonical question IDs, including in populated databases."""

import os
from pathlib import Path
import subprocess
import sys
import uuid

import pytest
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from backend.app.models import DiagnosticSession, HelpEvent, TutorMaterial, User


@pytest.fixture(params=['sqlite', 'postgres'])
def tutor_migration_url(request, tmp_path):
    if request.param == 'sqlite':
        yield f'sqlite:///{tmp_path / "tutor-migration.db"}'
        return

    url = os.getenv('TEST_DATABASE_URL', '')
    if not url.startswith('postgresql'):
        pytest.skip('TEST_DATABASE_URL PostgreSQL não configurada')
    if 'test' not in make_url(url).database:
        raise RuntimeError("TEST_DATABASE_URL deve apontar para um banco com 'test' no nome")
    engine = create_engine(url)
    schema = 'tutor_migration_' + uuid.uuid4().hex
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    try:
        options = (make_url(url).query.get('options', '') + f' -csearch_path={schema}').strip()
        yield make_url(url).update_query_dict({'options': options}).render_as_string(hide_password=False)
    finally:
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()


def test_tutor_migration_preserves_material_and_help_events(tutor_migration_url):
    root = Path(__file__).resolve().parents[2]
    env = dict(os.environ, DATABASE_URL=tutor_migration_url)

    def alembic(*args):
        result = subprocess.run(
            [sys.executable, '-m', 'alembic', *args],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    alembic('upgrade', 'b8d4f0c3e521')
    engine = create_engine(tutor_migration_url)
    if engine.dialect.name == 'sqlite':

        @event.listens_for(engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')

    with Session(engine) as db, db.begin():
        db.add(User(id='student', name='Aluno', email='migration@example.com', password_hash='not-a-login'))
        db.flush()
        db.add(
            DiagnosticSession(
                id='practice',
                user_id='student',
                start_key='migration-practice',
                kind='practice',
                objective='Praticar',
                area='Matemática',
                available_minutes=15,
                selection={},
                items=[],
            )
        )
        db.add_all(
            TutorMaterial(
                id=key,
                question_id=key,
                canonical_id=canonical_id,
                content_sha256='a' * 64,
                version=1,
                status='approved',
                origin='human',
                levels={'orientation': 'Material preservado'},
                created_by='student',
            )
            for key, canonical_id in [('material', 'a' * 36), ('without-identity', None)]
        )
        db.flush()
        db.add(
            HelpEvent(
                id='help',
                user_id='student',
                session_id='practice',
                item_id='question:1',
                content_version=1,
                level='orientation',
                request_key='migration-help',
                material_id='material',
                outcome='delivered',
                message='Ajuda preservada',
            )
        )
        db.flush()
        tables = [TutorMaterial.__table__, HelpEvent.__table__]
        before = [db.execute(select(table).order_by(table.c.id)).mappings().all() for table in tables]

    alembic('upgrade', 'head')
    alembic('check')
    with Session(engine) as db, db.begin():
        after = [db.execute(select(table).order_by(table.c.id)).mappings().all() for table in tables]
        assert before == after
        db.get(TutorMaterial, 'material').canonical_id = 'enem-' + 'b' * 75
    with Session(engine) as db, db.begin():
        assert db.get(TutorMaterial, 'material').canonical_id == 'enem-' + 'b' * 75
        assert db.get(TutorMaterial, 'without-identity').canonical_id is None
        db.get(TutorMaterial, 'material').canonical_id = 'a' * 36
        if engine.dialect.name == 'sqlite':
            assert db.connection().exec_driver_sql('PRAGMA foreign_key_check').all() == []

    alembic('downgrade', 'b8d4f0c3e521')
    columns = {column['name']: column for column in inspect(engine).get_columns('tutor_materials')}
    assert columns['canonical_id']['type'].length == 36
    alembic('upgrade', 'head')
    alembic('check')
    with Session(engine) as db:
        assert before == [db.execute(select(table).order_by(table.c.id)).mappings().all() for table in tables]
    engine.dispose()
