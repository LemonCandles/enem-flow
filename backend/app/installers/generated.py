"""Automatic publication of the exams generated from the official archive.

`scripts/build_archive_exams.py` extracts text and figures without curation.
This step imports and publishes them as they are; blocking preparation issues
are kept in each version's report instead of preventing publication.
"""

from ..services.content import import_exam
from ..services.lifecycle import approve_and_publish
from ..services.service_account import service_reviewer
from ..services.errors import DomainError
from ..core.config import ROOT
from ..models import Exam, QuestionVersion
from ..schemas import ExamImport
from ..preparation import blocking_issues

GENERATED = ROOT / 'data/derived/exams'
REASON = (
    'Publicação automática do acervo oficial: texto e figuras extraídos do PDF, sem curadoria. '
    'Conferência humana pendente; diagnósticos de preparação preservados.'
)


def generated_files(directory=GENERATED):
    return sorted(
        p for p in directory.glob('*.json') if not p.name.endswith('.report.json') and p.name != 'resumo.json'
    )


def publish_generated(db, directory=GENERATED, *, paths=None):
    """Publish generated exams not yet installed; an explicit file list limits local setup."""
    reviewer = service_reviewer(db)
    published, existing, failed = [], 0, []
    files = generated_files(directory) if paths is None else paths
    for path in files:
        try:
            payload = ExamImport.model_validate_json(path.read_text())
            previous = db.get(Exam, payload.id)
            if previous:
                # Older automatic installs had no visible provenance marker.
                # Metadata can be backfilled without replacing question versions.
                if (
                    not previous.source.get('automatic_archive')
                    and previous.source.get('sha256') == payload.source.sha256
                ):
                    pending = sum(len(blocking_issues(db.get(QuestionVersion, key).content)) for key in previous.items)
                    previous.source = {
                        **previous.source,
                        'automatic_archive': dict(version=1, review_status='pending', blocking_issues=pending),
                    }
                existing += 1
                continue
            with db.begin_nested():
                exam = import_exam(db, payload)
                pending = sum(len(blocking_issues(q.content.model_dump())) for q in payload.questions)
                exam.source = {
                    **exam.source,
                    'automatic_archive': dict(version=1, review_status='pending', blocking_issues=pending),
                }
                approve_and_publish(db, exam, reviewer.id, REASON, allow_pending=True)
            published.append(payload.id)
        except (DomainError, ValueError, OSError) as error:
            failed.append(dict(id=path.stem, reason=str(getattr(error, 'detail', error))))
    return dict(published=len(published), existing=existing, failed=failed)
