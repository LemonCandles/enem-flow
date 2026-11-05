"""Controlled updates of the bundled JSON; existing attempts remain immutable."""

from ..services.errors import Conflict

from ..services.content import validate_assets
from ..services.lifecycle import publish_exam
from ..models import QuestionVersion, Review
from ..schemas import QuestionContent
from ..services.presentation import ASSESSMENT_FIELDS, is_previous_bundled_content
from ..services.versioning import new_version


def refresh_bundle(db, exam, payload, reviewer):
    if len(exam.items) != len(payload.questions):
        raise Conflict("A prova existente foi reorganizada. Revise a atualização manualmente.")
    keys, count = [], 0
    reason = "Revisão de apresentação conferida com o caderno fonte: LaTeX matemático/químico, legendas e equações vinculadas às figuras; gabaritos e execuções preservados."
    for key, question in zip(exam.items, payload.questions):
        old = db.get(QuestionVersion, key)
        desired = question.content.model_dump()
        validate_assets(desired)
        if old.question_id != question.question_id:
            raise Conflict("A ordem das questões foi alterada. Revise a atualização manualmente.")
        if QuestionContent.model_validate(old.content).model_dump() == desired:
            keys.append(old.id)
            continue
        normalized_old = QuestionContent.model_validate(old.content).model_dump()
        if not is_previous_bundled_content(old.question_id, old.content):
            raise Conflict(f"A questão {question.question_id} possui edição própria. A atualização não foi aplicada.")
        if any(normalized_old[field] != desired[field] for field in ASSESSMENT_FIELDS):
            raise Conflict(f"A questão {question.question_id} alterou dados de avaliação. Exige revisão manual.")
        new = new_version(db, old, desired, status="approved")
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
