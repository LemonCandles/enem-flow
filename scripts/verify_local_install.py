"""Check the fresh local catalog in CI; never modify the database."""

import _bootstrap  # noqa: F401
from sqlalchemy import select
from backend.app.core.db import SessionLocal
from backend.app.installers.local import AUTOMATIC, REVIEWED
from backend.app.models import Exam

with SessionLocal() as db:
    exams = list(db.scalars(select(Exam).where(Exam.status == 'published')))
    assert {exam.id for exam in exams} == {REVIEWED, *AUTOMATIC}
    assert sum(len(exam.items) for exam in exams) == 540
print('Catálogo local: seis provas, 540 posições.')
