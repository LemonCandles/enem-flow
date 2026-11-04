"""Exam attempts: start, resume, save answers and finish with scoring."""

import copy

from fastapi import APIRouter

from .. import models as m, schemas as s
from ..dependencies import CurrentUser, SessionDep
from ..services import attempts
from ..services.attempts import EXAM_RUN
from ..services.content import public_exam_summary, public_question, visible_exam

router = APIRouter(prefix="/exam-runs", tags=["execuções"])


def run_data(run):
    finished = run.finished_at is not None
    return {
        "id": run.id,
        "exam": run.exam_info,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "answers": run.answers,
        "result": run.result,
        "items": [public_question(item, finished) for item in run.items],
    }


@router.post("", status_code=201)
def start_run(payload: s.StartRun, user: CurrentUser, db: SessionDep):
    def build():
        exam = visible_exam(db, payload.exam_id)
        items = []
        for key in exam.items:
            question = db.get(m.QuestionVersion, key)
            items.append(
                {
                    "id": key,
                    "question_id": question.question_id,
                    "version": question.version,
                    "canonical_id": question.canonical_id,
                    "content": copy.deepcopy(question.content),
                }
            )
        return m.ExamRun(
            user_id=user.id,
            exam_id=exam.id,
            start_key=payload.idempotency_key,
            exam_info=public_exam_summary(db, exam),
            items=items,
            answers={},
        )

    run = attempts.start(
        db, EXAM_RUN, user.id, payload.idempotency_key, lambda run: run.exam_id == payload.exam_id, build
    )
    return run_data(run)


@router.get("/{run_id}")
def get_run(run_id: str, user: CurrentUser, db: SessionDep):
    return run_data(attempts.owned(db, EXAM_RUN, run_id, user.id))


@router.put("/{run_id}/answers/{item_id}")
def save_answer(run_id: str, item_id: str, payload: s.Answer, user: CurrentUser, db: SessionDep):
    return attempts.save_answer(db, EXAM_RUN, run_id, item_id, payload.choice, user.id)


@router.post("/{run_id}/finish")
def finish_run(run_id: str, user: CurrentUser, db: SessionDep):
    return run_data(attempts.finish(db, EXAM_RUN, run_id, user.id))
