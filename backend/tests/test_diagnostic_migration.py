"""Exercise Alembic against populated pre-diagnostic SQLite schema."""

import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import MetaData, create_engine, select
from sqlalchemy.orm import Session

from backend.app.services.knowledge import reconstruct


def test_populated_migration_preserves_legacy_events(tmp_path, exam_payload):
    root = Path(__file__).resolve().parents[2]
    url = f'sqlite:///{tmp_path / "migration.db"}'
    env = dict(os.environ, DATABASE_URL=url)

    def alembic(*args):
        subprocess.run(
            [sys.executable, '-m', 'alembic', *args],
            cwd=root,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

    alembic('upgrade', 'f831ef101a02')
    engine = create_engine(url)
    meta = MetaData()
    meta.reflect(engine)
    item = {'id': 'old:1', 'question_id': 'old', 'version': 1, 'content': exam_payload['questions'][0]['content']}
    with engine.begin() as conn:
        conn.execute(
            meta.tables['users'].insert(),
            dict(
                id='student',
                email='migration@example.com',
                name='Teste',
                password_hash='not-a-login',
                role='student',
                preferences={},
                created_at=1,
            ),
        )
        conn.execute(
            meta.tables['exams'].insert(),
            dict(
                id='exam',
                title='Prova anterior',
                year=2024,
                application='Regular',
                booklet='Azul',
                day=2,
                kind='collection',
                expected_items=1,
                duration_minutes=3,
                source=exam_payload['source'],
                items=[],
                status='published',
                created_at=1,
            ),
        )
        conn.execute(
            meta.tables['exam_runs'].insert(),
            dict(
                id='run',
                user_id='student',
                exam_id='exam',
                start_key='old-attempt',
                exam_info={},
                items=[item],
                answers={'old:1': 'B'},
                started_at=1,
                finished_at=2,
                result={'percentage': 100},
            ),
        )
        conn.execute(
            meta.tables['learning_events'].insert(),
            dict(
                id='event',
                user_id='student',
                run_id='run',
                item_id='old:1',
                position=1,
                answer='B',
                correct=True,
                created_at=2,
                context={
                    'schema_version': '1.0',
                    'content_version': 1,
                    'mode': 'exam',
                    'help_used': False,
                    'labels': item['content']['labels'],
                },
            ),
        )
        old_event = dict(conn.execute(select(meta.tables['learning_events'])).mappings().one())
    engine.dispose()
    alembic('upgrade', 'head')
    alembic('check')
    engine = create_engine(url)
    with Session(engine) as db:
        state = reconstruct(db, 'student')
        group = state['themes'][0]
        assert group['independent_attempts'] == group['independent_correct'] == 1
        assert group['estimate'] == 2 / 3
        assert group['last_practice'] == 2
    meta = MetaData()
    meta.reflect(engine)
    with engine.connect() as conn:
        new_event = dict(conn.execute(select(meta.tables['learning_events'])).mappings().one())
    assert new_event.pop('session_id') is None
    assert new_event == old_event
    engine.dispose()
    alembic('downgrade', 'f831ef101a02')
    alembic('upgrade', 'head')
    alembic('check')


def test_practice_migration_keeps_diagnostics_and_downgrade_removes_only_practice(tmp_path, exam_payload):
    root = Path(__file__).resolve().parents[2]
    url = f'sqlite:///{tmp_path / "practice.db"}'
    env = dict(os.environ, DATABASE_URL=url)

    def alembic(*args):
        subprocess.run(
            [sys.executable, '-m', 'alembic', *args], cwd=root, env=env, check=True, capture_output=True, timeout=30
        )

    alembic('upgrade', 'd410a4e02001')
    engine = create_engine(url)
    meta = MetaData()
    meta.reflect(engine)
    session = dict(
        user_id='student',
        objective='Objetivo',
        area='Matemática',
        available_minutes=15,
        selection={},
        items=[],
        answers={},
        started_at=1.0,
    )
    with engine.begin() as conn:
        conn.execute(
            meta.tables['users'].insert(),
            dict(
                id='student',
                email='practice@example.com',
                name='Teste',
                password_hash='not-a-login',
                role='student',
                preferences={},
                created_at=1,
            ),
        )
        conn.execute(meta.tables['diagnostic_sessions'].insert(), dict(session, id='antiga', start_key='chave-antiga'))
    engine.dispose()
    alembic('upgrade', 'head')
    engine = create_engine(url)
    meta = MetaData()
    meta.reflect(engine)
    sessions, events = meta.tables['diagnostic_sessions'], meta.tables['recommendation_events']
    with engine.begin() as conn:
        assert conn.execute(select(sessions.c.kind)).scalars().all() == ['diagnostic']
        conn.execute(sessions.insert(), dict(session, id='pratica', start_key='chave-pratica', kind='practice'))
        conn.execute(
            events.insert(),
            dict(
                id='evento',
                user_id='student',
                session_id='pratica',
                position=1,
                item_id='old:1',
                policy_version='adaptive-v1',
                function='exploracao',
                reason='Motivo',
                components={},
                candidates_total=1,
                candidates=[],
                created_at=1.0,
            ),
        )
    engine.dispose()
    alembic('downgrade', 'd410a4e02001')
    engine = create_engine(url)
    meta = MetaData()
    meta.reflect(engine)
    assert 'recommendation_events' not in meta.tables and 'kind' not in meta.tables['diagnostic_sessions'].c
    with engine.begin() as conn:
        assert conn.execute(select(meta.tables['diagnostic_sessions'].c.id)).scalars().all() == ['antiga']
    engine.dispose()
    alembic('upgrade', 'head')
