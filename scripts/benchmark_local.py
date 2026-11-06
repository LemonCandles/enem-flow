"""Measure read-only catalog/state queries against an existing SQLite installation."""

import _bootstrap  # noqa: F401
import argparse
import json
from pathlib import Path
import sqlite3
import statistics
import time
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from backend.app.models import Exam, User
from backend.app.services.content import exam_summary
from backend.app.services.knowledge import reconstruct
from backend.app.routers.practice import provisional_difficulty


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    args = parser.parse_args()
    uri = args.database.resolve().as_uri() + '?mode=ro'
    engine = create_engine('sqlite://', creator=lambda: sqlite3.connect(uri, uri=True))
    with Session(engine) as db:
        exams = list(db.scalars(select(Exam).where(Exam.status == 'published')))
        user = db.scalar(select(User.id).where(User.role == 'student').limit(1)) or 'benchmark-without-history'
        operations = {
            'catalog': lambda: [exam_summary(db, exam) for exam in exams],
            'state': lambda: reconstruct(db, user),
            'difficulty': lambda: provisional_difficulty(db),
        }
        result = {
            'published_exams': len(exams),
            'positions': sum(len(e.items) for e in exams),
            'student_history_available': user != 'benchmark-without-history',
            'median_ms': {},
        }
        for name, operation in operations.items():
            durations = []
            for _ in range(5):
                start = time.perf_counter()
                operation()
                durations.append((time.perf_counter() - start) * 1000)
            result['median_ms'][name] = round(statistics.median(durations), 2)
        print(json.dumps(result, indent=2))
    engine.dispose()


if __name__ == '__main__':
    main()
