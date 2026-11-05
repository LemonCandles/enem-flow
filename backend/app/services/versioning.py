"""New immutable versions of a question; earlier versions and attempts stay as they are."""

from sqlalchemy import func, select

from ..models import QuestionVersion


def latest_version(db, question_id):
    return db.scalar(select(func.max(QuestionVersion.version)).where(QuestionVersion.question_id == question_id))


def new_version(db, previous, content, *, number=None, canonical_id=None, status='draft'):
    """Add the next version of `previous`; it keeps the same identity unless told otherwise."""
    number = number if number is not None else latest_version(db, previous.question_id) + 1
    version = QuestionVersion(
        id=f'{previous.question_id}:{number}',
        question_id=previous.question_id,
        canonical_id=canonical_id if canonical_id is not None else previous.canonical_id,
        version=number,
        content=content,
        status=status,
    )
    db.add(version)
    return version
