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
from .preparation import blocking_issues

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
        try:
            payload = ExamImport.model_validate_json(path.read_text())
            previous=db.get(Exam,payload.id)
            if previous:
                # Older automatic installs had no visible provenance marker.
                # Metadata can be backfilled without replacing question versions.
                if not previous.source.get('automatic_archive') and previous.source.get('sha256')==payload.source.sha256:
                    pending=sum(len(blocking_issues(db.get(QuestionVersion,key).content)) for key in previous.items)
                    previous.source={**previous.source,'automatic_archive':dict(version=1,review_status='pending',blocking_issues=pending)}
                existing += 1
                continue
            with db.begin_nested():
                exam = import_exam(db, payload)
                pending=sum(len(blocking_issues(q.content.model_dump())) for q in payload.questions)
                exam.source={**exam.source,'automatic_archive':dict(version=1,review_status='pending',blocking_issues=pending)}
                for key in exam.items:
                    db.get(QuestionVersion, key).status = 'approved'
                    db.add(Review(user_id=reviewer.id, target_id=key, action='approve', reason=REASON))
                publish_exam(db, exam, reviewer.id, REASON, allow_pending=True)
            published.append(payload.id)
        except (HTTPException, ValueError, OSError) as error:
            failed.append(dict(id=path.stem, reason=str(getattr(error, 'detail', error))))
    return dict(published=len(published), existing=existing, failed=failed)
