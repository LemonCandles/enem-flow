"""Automatic publication of the exams generated from the official archive.

`scripts/build_archive_exams.py` extracts text and figures without curation.
This step imports and publishes them as they are; blocking preparation issues
are kept in each version's report instead of preventing publication.
"""
from fastapi import HTTPException

from .bundled_content import bundled_reviewer
from .content import import_exam, publish_exam
from .db import ROOT
from .models import Exam, QuestionVersion, Review
from .schemas import ExamImport

GENERATED = ROOT / 'data/derived/exams'
REASON = ('Publicação automática do acervo oficial: texto e figuras extraídos do PDF, sem curadoria. '
          'Layout e conferência ficam para as etapas 3 e 8 do roteiro.')


def generated_files(directory=GENERATED):
    return sorted(p for p in directory.glob('*.json') if not p.name.endswith('.report.json') and p.name != 'resumo.json')


def publish_generated(db, directory=GENERATED):
    """Publish every generated exam not yet installed; each exam succeeds or fails alone."""
    reviewer = bundled_reviewer(db)
    published, existing, failed = [], 0, []
    for path in generated_files(directory):
        payload = ExamImport.model_validate_json(path.read_text())
        if db.get(Exam, payload.id):
            existing += 1
            continue
        try:
            with db.begin_nested():
                exam = import_exam(db, payload)
                for key in exam.items:
                    db.get(QuestionVersion, key).status = 'approved'
                    db.add(Review(user_id=reviewer.id, target_id=key, action='approve', reason=REASON))
                publish_exam(db, exam, reviewer.id, REASON, allow_pending=True)
            published.append(payload.id)
        except (HTTPException, ValueError) as error:
            failed.append(dict(id=payload.id, reason=str(getattr(error, 'detail', error))))
    return dict(published=len(published), existing=existing, failed=failed)
