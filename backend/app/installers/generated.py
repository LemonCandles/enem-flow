"""Automatic publication of the exams generated from the official archive.

`scripts/build_archive_exams.py` extracts text and figures without curation.
This step imports and publishes them as they are; blocking preparation issues
are kept in each version's report instead of preventing publication. A human
verification recorded in the catalog profile is applied by `confirm_generated`.
"""

from collections import defaultdict

from sqlalchemy import select

from ..services.content import import_exam, validate_assets
from ..services.identity import signatures, validate_revision_identity
from ..services.lifecycle import approve_and_publish, publish_exam
from ..services.service_account import service_reviewer
from ..services.versioning import latest_version, new_version
from ..services.errors import DomainError
from ..core.config import ROOT
from ..models import CanonicalQuestion, Exam, QuestionVersion, Review
from ..schemas import ExamImport, QuestionContent
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


# Fields that decide a result; a confirmed update never changes them.
ASSESSMENT = ('number', 'area', 'correct_answer', 'annulled')


def confirm_generated(db, paths, reason):
    """Register a human verification of generated exams whose files carry no pending issue.

    Installed versions that differ from the verified file receive a new approved version;
    attempts keep the versions they used. An exam withdrawn, held for review or edited
    after installation keeps that decision and stays pending.
    """
    reviewer = service_reviewer(db)
    confirmed, skipped, versions, affected = [], [], 0, set()
    for path in paths:
        payload = ExamImport.model_validate_json(path.read_text())
        exam = db.get(Exam, payload.id)
        automatic = (exam.source.get('automatic_archive') or {}) if exam else {}
        if not exam or exam.status != 'published' or automatic.get('review_status') != 'pending':
            continue
        current = [db.get(QuestionVersion, key) for key in exam.items]
        targets = [q.content.model_dump() for q in payload.questions]
        if (exam.source.get('sha256'), exam.source.get('answer_key_sha256')) != (
            payload.source.sha256,
            payload.source.answer_key_sha256,
        ) or [q.question_id for q in current] != [q.question_id for q in payload.questions]:
            skipped.append(dict(id=exam.id, reason='Fonte ou ordem das questões difere da prova conferida.'))
            continue
        if any(q.status != 'approved' or latest_version(db, q.question_id) != q.version for q in current):
            skipped.append(dict(id=exam.id, reason='Há edição ou decisão manual posterior à instalação.'))
            continue
        if any(old.content[k] != new[k] for old, new in zip(current, targets) for k in ASSESSMENT):
            skipped.append(dict(id=exam.id, reason='A prova conferida altera número, área ou gabarito.'))
            continue
        if any(blocking_issues(content) for content in targets):
            skipped.append(dict(id=exam.id, reason='A prova conferida ainda tem pendências bloqueantes.'))
            continue
        items = []
        for old, content in zip(current, targets):
            if QuestionContent.model_validate(old.content).model_dump() == content:
                items.append(old.id)
                continue
            validate_assets(content)
            validate_revision_identity(db, content, old.canonical_id)
            new = new_version(db, old, content, status='approved')
            db.add(Review(user_id=reviewer.id, target_id=new.id, action='approve', reason=reason))
            items.append(new.id)
            affected.add(old.canonical_id)
            versions += 1
        db.flush()
        exam.items = items
        publish_exam(db, exam, reviewer.id, reason)
        confirmed.append(exam.id)
    refresh_signatures(db, affected - {None})
    return dict(confirmed=confirmed, new_versions=versions, skipped=skipped)


def refresh_signatures(db, canonical_ids):
    """Follow corrected content when every published occurrence agrees; never merge identities."""
    found = defaultdict(set)
    for exam in db.scalars(select(Exam).where(Exam.status == 'published')):
        for key in exam.items:
            question = db.get(QuestionVersion, key)
            if question.canonical_id in canonical_ids:
                found[question.canonical_id].add(signatures(question.content))
    for canonical_id, values in found.items():
        if len(values) == 1:
            identity = db.get(CanonicalQuestion, canonical_id)
            identity.signature, identity.answer_signature = next(iter(values))
