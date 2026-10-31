"""Controlled updates of the bundled JSON; existing attempts remain immutable."""
import secrets

from fastapi import HTTPException
from sqlalchemy import func, select

from .content import publish_exam, validate_assets
from .models import QuestionVersion, Review, User
from .schemas import QuestionContent
from .security import hash_password
from .presentation import ASSESSMENT_FIELDS, is_previous_bundled_content


def bundled_reviewer(db):
    reviewer = db.scalar(select(User).where(User.email == "content-bootstrap@invalid.local"))
    if not reviewer:
        reviewer = User(name="Importação conferida", email="content-bootstrap@invalid.local",
                        password_hash=hash_password(secrets.token_urlsafe(64)), role="service")
        db.add(reviewer)
        db.flush()
    return reviewer


def refresh_bundle(db, exam, payload, reviewer):
    if len(exam.items) != len(payload.questions):
        raise HTTPException(409, "A prova existente foi reorganizada. Revise a atualização manualmente.")
    keys, count = [], 0
    reason = "Revisão de apresentação conferida com o caderno fonte: LaTeX matemático/químico, legendas e equações vinculadas às figuras; gabaritos e execuções preservados."
    for key, question in zip(exam.items, payload.questions):
        old = db.get(QuestionVersion, key)
        desired = question.content.model_dump()
        validate_assets(desired)
        if old.question_id != question.question_id:
            raise HTTPException(409, "A ordem das questões foi alterada. Revise a atualização manualmente.")
        if QuestionContent.model_validate(old.content).model_dump() == desired:
            keys.append(old.id)
            continue
        normalized_old = QuestionContent.model_validate(old.content).model_dump()
        if not is_previous_bundled_content(old.question_id, old.content):
            raise HTTPException(409, f"A questão {question.question_id} possui edição própria. A atualização não foi aplicada.")
        if any(normalized_old[field] != desired[field] for field in ASSESSMENT_FIELDS):
            raise HTTPException(409, f"A questão {question.question_id} alterou dados de avaliação. Exige revisão manual.")
        latest = db.scalar(select(func.max(QuestionVersion.version)).where(QuestionVersion.question_id == old.question_id))
        version = latest + 1
        new = QuestionVersion(id=f"{old.question_id}:{version}", question_id=old.question_id,
                              version=version, content=desired, status="approved")
        db.add(new)
        review = (desired.get('layout') or {}).get('presentation_review', {})
        detail = f"Questão {desired['number']}, página {desired['page']}: {review.get('reason', reason)}"
        db.add(Review(user_id=reviewer.id, target_id=new.id, action="approve", reason=detail))
        keys.append(new.id)
        count += 1
    if count:
        db.flush()
        exam.items = keys
        exam.source = payload.source.model_dump()
        publish_exam(db, exam, reviewer.id, reason)
    return count
