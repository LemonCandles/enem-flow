"""Install source-curated lots and labels through immutable, guarded versions."""

import copy
import json

from ..services.errors import Conflict
from sqlalchemy import func, select

from ..core.config import ROOT
from ..services.content import import_exam, validate_assets
from ..services.lifecycle import approve_and_publish, send_to_review
from ..services.service_account import service_reviewer
from ..models import CanonicalQuestion, Exam, QuestionVersion, Review
from ..schemas import ExamImport, QuestionContent
from ..services.presentation import content_fingerprint, is_previous_bundled_content
from ..services.identity import identify
from ..services.versioning import new_version
from ..preparation import fingerprint as preparation_fingerprint


def classified(payload, *, refresh_preparation_audit=True):
    """Labels apply only to the exact reviewed content and declared source."""
    data = copy.deepcopy(payload.model_dump() if isinstance(payload, ExamImport) else payload)
    records = json.loads((ROOT / 'data/classification/annotations-v1.json').read_text())
    annotations = {a['question_id']: a for a in records['annotations']}
    for q in data['questions']:
        a = annotations.get(q['question_id'])
        if (
            not a
            or a['source_sha256'] != data['source']['sha256']
            or a['content_sha256'] != content_fingerprint(q['content'])
        ):
            raise ValueError(f'Anotação não corresponde à versão e fonte de {q["question_id"]}.')
        if a['status'] != 'curated':
            raise ValueError('Anotação sem curadoria não pode ser instalada como lote revisado.')
        q['content']['labels'] = dict(
            discipline=a['discipline'],
            themes=a['themes'],
            skills=[],
            taxonomy_version=a['taxonomy_version'],
            provenance='reference-v1: curadoria técnica assistida; segunda revisão independente pendente.',
        )
        q['content']['layout'] = {
            **(q['content'].get('layout') or {}),
            'classification': dict(
                version=records['version'],
                status=a['status'],
                independent_review=False,
                evidence=a['evidence'],
                rationale=a['rationale'],
                skill_candidates=a['skill_candidates'],
            ),
        }
        preparation = q['content']['layout'].get('preparation')
        if preparation and refresh_preparation_audit:
            # Labels change the full-content fingerprint, although source-reviewed
            # prose/formulas did not change. Retain the original audit and link
            # the classified output so import does not reinterpret it again.
            q['content']['layout']['classification']['source_preparation_output_sha256'] = preparation['output_sha256']
            preparation['output_sha256'] = preparation_fingerprint(q['content'])
    return ExamImport.model_validate(data)


def review_state(db, exam):
    """What the current exam already says about human decisions, read before any change."""
    was_withdrawn = bool(exam and exam.status == 'withdrawn')
    previous_items = [db.get(QuestionVersion, key) for key in exam.items] if exam else []
    previous_drafts = [q.id for q in previous_items if q.status == 'draft']
    held_for_review = any(q.status == 'in_review' for q in previous_items) or bool(
        previous_drafts
        and db.scalar(select(Review.id).where(Review.target_id.in_(previous_drafts), Review.action == 'edit').limit(1))
    )
    return was_withdrawn, held_for_review


def replaceable(old, exam_id, original, previous_target):
    """Only content that came from this catalog can be replaced automatically."""
    fingerprint = content_fingerprint(old.content)
    if fingerprint == content_fingerprint(original.content.model_dump()):
        return True
    if fingerprint == content_fingerprint(previous_target.content.model_dump()):
        return True
    return exam_id == 'enem-2024-dia2-azul' and is_previous_bundled_content(old.question_id, old.content)


def update_versions(db, exam, base, desired, previous_profile, stats):
    """Create a version for each item that differs; returns whether anything changed."""
    if len(exam.items) != len(desired.questions):
        raise Conflict('Lote existente foi reorganizado; exige revisão manual.')
    changed = False
    new_keys = []
    for key, original, target, previous_target in zip(
        exam.items, base.questions, desired.questions, previous_profile.questions
    ):
        old = db.get(QuestionVersion, key)
        wanted = target.content.model_dump()
        if old.question_id != target.question_id:
            raise Conflict('Ordem do lote existente foi alterada.')
        validate_assets(wanted)
        if QuestionContent.model_validate(old.content).model_dump() == wanted:
            if old.canonical_id is None:
                old.canonical_id = identify(db, wanted, (desired.source.sha256, target.content.number))
            new_keys.append(old.id)
            continue
        if not replaceable(old, base.id, original, previous_target):
            raise Conflict(f'{old.question_id} tem edição própria; nenhuma substituição automática permitida.')
        # Source curation changes labels/presentation, never assessment.
        if any(old.content[k] != wanted[k] for k in ('number', 'area', 'page', 'correct_answer', 'annulled')):
            raise Conflict('Mudança de avaliação exige revisão manual.')
        canonical_id = old.canonical_id or identify(db, wanted, (desired.source.sha256, target.content.number))
        new_keys.append(new_version(db, old, wanted, canonical_id=canonical_id).id)
        stats['new_versions'] += 1
        changed = True
    db.flush()
    exam.items = new_keys
    return changed


def backfill_identity(db, exam, desired):
    """Backfill identity only; do not rewrite old content or run snapshots."""
    for q, key in zip(desired.questions, exam.items):
        current = db.get(QuestionVersion, key)
        canonical_id = current.canonical_id or identify(
            db, q.content.model_dump(), (desired.source.sha256, q.content.number)
        )
        for previous in db.scalars(
            select(QuestionVersion).where(
                QuestionVersion.question_id == q.question_id, QuestionVersion.canonical_id.is_(None)
            )
        ):
            previous.canonical_id = canonical_id


def settle_status(db, exam, reviewer, reason, *, changed, publish, was_withdrawn, held_for_review):
    """Explicit publication also handles a previous install without publication.

    Repeated runs never override a human rejection, pending edit or withdrawal.
    """
    pending = [db.get(QuestionVersion, key) for key in exam.items]
    if changed and held_for_review:
        for question in pending:
            if question.status == 'draft':
                question.status = 'in_review'
    can_publish = (
        publish
        and not was_withdrawn
        and not held_for_review
        and (
            changed
            or (exam.status in {'draft', 'in_review'} and all(q.status in {'draft', 'approved'} for q in pending))
        )
    )
    if can_publish:
        approve_and_publish(db, exam, reviewer.id, reason)
    elif changed and was_withdrawn:
        exam.status = 'withdrawn'
    elif changed:
        send_to_review(exam)


def install_catalog(db, publish=False, *, exam_ids=None):
    manifest = json.loads((ROOT / 'data/catalog/manifest.json').read_text())
    reviewer = service_reviewer(db)
    stats = dict(imported_exams=0, new_versions=0, canonical_questions=0)
    reason = (
        f'{manifest["version"]}: lote conferido com a fonte e taxonomia reference-v1; '
        'habilidades apenas propostas e revisão independente pendente.'
    )
    for entry in manifest['exams']:
        path = (ROOT / entry['path']).resolve()
        if not path.is_relative_to(ROOT.resolve()):
            raise ValueError('Caminho do catálogo fora do projeto.')
        base = ExamImport.model_validate_json(path.read_text())
        if exam_ids is not None and base.id not in exam_ids:
            continue
        desired = classified(base)
        previous_profile = classified(base, refresh_preparation_audit=False)
        exam = db.get(Exam, desired.id)
        was_withdrawn, held_for_review = review_state(db, exam)
        if exam:
            changed = update_versions(db, exam, base, desired, previous_profile, stats)
        else:
            exam = import_exam(db, desired)
            stats['imported_exams'] += 1
            changed = True
        backfill_identity(db, exam, desired)
        settle_status(
            db,
            exam,
            reviewer,
            reason,
            changed=changed,
            publish=publish,
            was_withdrawn=was_withdrawn,
            held_for_review=held_for_review,
        )
    stats['canonical_questions'] = db.scalar(select(func.count()).select_from(CanonicalQuestion))
    return stats
