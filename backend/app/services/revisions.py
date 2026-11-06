"""A new draft version of a question, shared by manual edits and approved layout proposals.

Every path that changes content goes through here: preparation, assets, identity collision and
duplicates in each linked exam. Linked exams leave publication until the new version is reviewed.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..models import Exam, QuestionVersion, Review
from ..preparation import prepare_content
from .content import validate_assets
from .errors import Conflict, InvalidContent
from .identity import identify, validate_exam_identities, validate_revision_identity
from .lifecycle import send_to_review
from .versioning import latest_version, new_version


def revise_question(db, previous, content, user_id, reason, action='edit'):
    try:
        content = prepare_content(content)
    except ValueError as error:
        raise InvalidContent(str(error))
    validate_assets(content)
    if latest_version(db, previous.question_id) != previous.version:
        raise Conflict("Há uma versão mais recente. Atualize a tela antes de editar.")
    canonical_id = previous.canonical_id or identify(db, previous.content)
    validate_revision_identity(db, content, canonical_id)
    linked_exams = [exam for exam in db.scalars(select(Exam)) if previous.id in exam.items]
    for exam in linked_exams:
        items = [
            (canonical_id, content) if key == previous.id else (q.canonical_id, q.content)
            for key in exam.items
            if (q := db.get(QuestionVersion, key))
        ]
        validate_exam_identities(items)
    question = new_version(db, previous, content, canonical_id=canonical_id)
    # Published exams are withdrawn until the new version is reviewed and published again.
    for exam in linked_exams:
        exam.items = [question.id if key == previous.id else key for key in exam.items]
        send_to_review(exam)
    db.add(Review(user_id=user_id, target_id=question.id, action=action, reason=reason))
    try:
        db.flush()
    except IntegrityError:
        raise Conflict("Outro revisor criou uma versão. Atualize a tela.")
    return question
