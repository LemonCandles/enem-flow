"""Status changes of exams and question versions, each one recorded as a review.

Exam: draft, in_review, published, withdrawn. Question version: draft, in_review, approved.
Every exam status can reach any other today, so there is no transition table: these
functions are the single place that changes a status and states what each change requires.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Exam, QuestionVersion, Review
from ..preparation import blocking_issues
from .content import validate_assets
from .errors import Conflict
from .identity import validate_exam_identities


def publish_exam(db: Session, exam: Exam, user_id: str, reason: str, allow_pending: bool = False):
    """`allow_pending` is reserved for the automatic archive publication, which has no curation step."""
    if allow_pending and not exam.source.get('automatic_archive'):
        raise Conflict('Publicação automática exige a origem e o estado de revisão registrados.')
    if len(exam.items) != exam.expected_items:
        raise Conflict("A prova está incompleta para o total declarado.")
    identities = []
    for key in exam.items:
        question = db.get(QuestionVersion, key)
        if not question or question.status != "approved":
            raise Conflict("Todas as versões precisam de aprovação antes da publicação.")
        if not allow_pending and blocking_issues(question.content):
            raise Conflict("Há pendências bloqueantes de preparação. Corrija e revise as versões antes de publicar.")
        validate_assets(question.content)
        identities.append((question.canonical_id, question.content))
    validate_exam_identities(identities)
    if not allow_pending and exam.source.get('automatic_archive'):
        exam.source = {
            **exam.source,
            'automatic_archive': {
                **exam.source['automatic_archive'],
                'review_status': 'reviewed',
                'blocking_issues': 0,
            },
        }
    exam.status = "published"
    db.add(Review(user_id=user_id, target_id=exam.id, action="publish", reason=reason))


def approve_and_publish(db, exam, user_id, reason, allow_pending=False):
    """Install path: every version of the exam is approved with the same reason, then published."""
    for key in exam.items:
        db.get(QuestionVersion, key).status = 'approved'
        db.add(Review(user_id=user_id, target_id=key, action='approve', reason=reason))
    publish_exam(db, exam, user_id, reason, allow_pending=allow_pending)


def withdraw_exam(db, exam, user_id, reason):
    exam.status = 'withdrawn'
    db.add(Review(user_id=user_id, target_id=exam.id, action='withdraw', reason=reason))


def approve_question(db, question, user_id, reason):
    if blocking_issues(question.content):
        raise Conflict('Corrija as pendências bloqueantes da preparação e salve uma nova versão antes de aprovar.')
    question.status = 'approved'
    db.add(Review(user_id=user_id, target_id=question.id, action='approve', reason=reason))


def reject_question(db, question, user_id, reason):
    """A rejected version also suspends every published exam that uses it."""
    question.status = 'in_review'
    for linked in db.scalars(select(Exam).where(Exam.status == 'published')):
        if question.id in linked.items:
            linked.status = 'in_review'
    db.add(Review(user_id=user_id, target_id=question.id, action='reject', reason=reason))


def send_to_review(exam):
    exam.status = 'in_review'


# Actions accepted by the curation review endpoint, per kind of target.
EXAM_ACTIONS = {'publish': publish_exam, 'withdraw': withdraw_exam}
QUESTION_ACTIONS = {'approve': approve_question, 'reject': reject_question}
