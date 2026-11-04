"""The life of an attempt, shared by exam runs and diagnostic sessions.

Both keep a snapshot of their items and the answers of one student. They differ
only in the table and the messages, which each one declares in its `AttemptKind`,
and in how a new attempt is built, which `start` receives from the caller.
"""

from dataclasses import dataclass
import time

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from ..models import DiagnosticSession, ExamRun
from .errors import Conflict, NotFound
from .learning import record_learning_events
from .scoring import score


@dataclass(frozen=True)
class AttemptKind:
    model: type
    mode: str
    not_found: str
    key_reused: str
    closed: str
    foreign_item: str


EXAM_RUN = AttemptKind(
    ExamRun,
    'exam',
    not_found='Execução não encontrada.',
    key_reused='Esta chave já foi usada para outra prova.',
    closed='Esta prova já foi finalizada e não aceita alterações.',
    foreign_item='Questão não pertence a esta execução.',
)
DIAGNOSTIC = AttemptKind(
    DiagnosticSession,
    'diagnostic',
    not_found='Diagnóstico não encontrado.',
    key_reused='Esta chave já foi usada para outro diagnóstico.',
    closed='Este diagnóstico já foi finalizado e não aceita alterações.',
    foreign_item='Questão não pertence a este diagnóstico.',
)


def owned(db, kind, attempt_id, user_id, lock=False):
    """The attempt of this student, or 404 even when it belongs to someone else."""
    model = kind.model
    mine = (model.id == attempt_id, model.user_id == user_id)
    if lock:
        # A write lock works in SQLite too, where SELECT FOR UPDATE is ignored.
        found = db.execute(update(model).where(*mine).values(started_at=model.started_at)).rowcount
        if not found:
            raise NotFound(kind.not_found)
    attempt = db.scalar(select(model).where(*mine).execution_options(populate_existing=True))
    if attempt is None:
        raise NotFound(kind.not_found)
    return attempt


def _by_key(db, kind, user_id, key):
    return db.scalar(select(kind.model).where(kind.model.user_id == user_id, kind.model.start_key == key))


def start(db, kind, user_id, key, same_request, build):
    """Idempotent start: a repeated key returns the same attempt, also under concurrency."""

    def reuse(attempt):
        if not same_request(attempt):
            raise Conflict(kind.key_reused)
        return attempt

    previous = _by_key(db, kind, user_id, key)
    if previous is not None:
        return reuse(previous)
    attempt = build()
    db.add(attempt)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        winner = _by_key(db, kind, user_id, key)
        if winner is None:
            raise
        return reuse(winner)
    return attempt


def save_answer(db, kind, attempt_id, item_id, choice, user_id):
    attempt = owned(db, kind, attempt_id, user_id, lock=True)
    if attempt.finished_at is not None:
        raise Conflict(kind.closed)
    if item_id not in {item['id'] for item in attempt.items}:
        raise NotFound(kind.foreign_item)
    attempt.answers = {**attempt.answers, item_id: choice}
    return {'answers': attempt.answers, 'saved_at': time.time()}


def finish(db, kind, attempt_id, user_id):
    """Scoring and events are written together; finishing again changes nothing."""
    attempt = owned(db, kind, attempt_id, user_id, lock=True)
    if attempt.finished_at is None:
        attempt.finished_at = time.time()
        attempt.result = score(attempt.items, attempt.answers)
        record_learning_events(db, attempt, kind.mode)
        db.flush()
    return attempt
