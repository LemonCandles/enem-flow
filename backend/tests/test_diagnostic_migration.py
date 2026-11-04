"""Exercise Alembic against populated pre-diagnostic SQLite schema."""
import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import MetaData, create_engine, select



def test_populated_migration_preserves_legacy_events(tmp_path, exam_payload):
    root = Path(__file__).resolve().parents[2]
    url = f'sqlite:///{tmp_path / "migration.db"}'
    env = dict(os.environ, DATABASE_URL=url)

    def alembic(*args):
        subprocess.run([sys.executable, '-m', 'alembic', *args], cwd=root, env=env,
                       check=True, capture_output=True, text=True, timeout=30)

    alembic('upgrade', 'f831ef101a02')
    engine = create_engine(url)
    meta = MetaData()
    meta.reflect(engine)
    item = {'id': 'old:1', 'question_id': 'old', 'version': 1, 'content': exam_payload['questions'][0]['content']}
    with engine.begin() as conn:
        conn.execute(meta.tables['users'].insert(), dict(id='student', email='migration@example.com', name='Teste',
                     password_hash='not-a-login', role='student', preferences={}, created_at=1))
        conn.execute(meta.tables['exams'].insert(), dict(id='exam', title='Prova anterior', year=2024,
                     application='Regular', booklet='Azul', day=2, kind='collection', expected_items=1,
                     duration_minutes=3, source=exam_payload['source'], items=[], status='published', created_at=1))
        conn.execute(meta.tables['exam_runs'].insert(), dict(id='run', user_id='student', exam_id='exam',
                     start_key='old-attempt', exam_info={}, items=[item], answers={'old:1': 'B'},
                     started_at=1, finished_at=2, result={'percentage': 100}))
        conn.execute(meta.tables['learning_events'].insert(), dict(id='event', user_id='student', run_id='run',
                     item_id='old:1', position=1, answer='B', correct=True, created_at=2,
                     context={'schema_version': '1.0', 'content_version': 1, 'mode': 'exam', 'help_used': False,
                              'labels': item['content']['labels']}))
        old_event = dict(conn.execute(select(meta.tables['learning_events'])).mappings().one())
    engine.dispose()
    alembic('upgrade', 'head')
    alembic('check')
    engine = create_engine(url)
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
