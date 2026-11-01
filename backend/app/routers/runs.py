"""Exam attempts: start, resume, save answers and finish with scoring."""
import copy
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models as m, schemas as s
from ..content import public_question
from ..db import get_db
from ..scoring import score
from ..security import current_user
from .exams import summary, visible_exam

router = APIRouter(prefix="/exam-runs", tags=["execuções"])


def owned_run(db, run_id, user_id, lock=False):
    if lock:
        # A write lock works in SQLite too, where SELECT FOR UPDATE is ignored.
        found = db.execute(update(m.ExamRun).where(m.ExamRun.id == run_id, m.ExamRun.user_id == user_id)
                           .values(started_at=m.ExamRun.started_at)).rowcount
        if not found:
            raise HTTPException(404, "Execução não encontrada.")
    run = db.scalar(select(m.ExamRun).where(m.ExamRun.id == run_id, m.ExamRun.user_id == user_id).execution_options(populate_existing=True))
    if not run:
        raise HTTPException(404, "Execução não encontrada.")
    return run


def run_data(run):
    finished = run.finished_at is not None
    return {"id": run.id, "exam": run.exam_info, "started_at": run.started_at, "finished_at": run.finished_at,
            "answers": run.answers, "result": run.result,
            "items": [public_question(item, finished) for item in run.items]}


@router.post("", status_code=201)
def start_run(payload: s.StartRun, user: m.User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    previous = db.scalar(select(m.ExamRun).where(m.ExamRun.user_id == user.id, m.ExamRun.start_key == payload.idempotency_key))
    if previous:
        if previous.exam_id != payload.exam_id:
            raise HTTPException(409, "Esta chave já foi usada para outra prova.")
        return run_data(previous)
    exam = visible_exam(db, payload.exam_id)
    items = []
    for key in exam.items:
        question = db.get(m.QuestionVersion, key)
        items.append({"id": key, "question_id": question.question_id, "version": question.version,
                      "canonical_id": question.canonical_id, "content": copy.deepcopy(question.content)})
    run = m.ExamRun(user_id=user.id, exam_id=exam.id, start_key=payload.idempotency_key,
                    exam_info=summary(db, exam), items=items, answers={})
    db.add(run)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        run = db.scalar(select(m.ExamRun).where(m.ExamRun.user_id == user.id, m.ExamRun.start_key == payload.idempotency_key))
        if run.exam_id != payload.exam_id:
            raise HTTPException(409, "Esta chave já foi usada para outra prova.")
    return run_data(run)


@router.get("/{run_id}")
def get_run(run_id: str, user: m.User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return run_data(owned_run(db, run_id, user.id))


@router.put("/{run_id}/answers/{item_id}")
def save_answer(run_id: str, item_id: str, payload: s.Answer, user: m.User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    run = owned_run(db, run_id, user.id, lock=True)
    if run.finished_at is not None:
        raise HTTPException(409, "Esta prova já foi finalizada e não aceita alterações.")
    if item_id not in {item["id"] for item in run.items}:
        raise HTTPException(404, "Questão não pertence a esta execução.")
    run.answers = {**run.answers, item_id: payload.choice}
    return {"answers": run.answers, "saved_at": time.time()}


@router.post("/{run_id}/finish")
def finish_run(run_id: str, user: m.User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    run = owned_run(db, run_id, user.id, lock=True)
    if run.finished_at is not None:
        return run_data(run)
    run.finished_at = time.time()
    run.result = score(run.items, run.answers)
    for position, item in enumerate(run.items, 1):
        content = item["content"]
        answer = run.answers.get(item["id"])
        db.add(m.LearningEvent(user_id=user.id, run_id=run.id, item_id=item["id"], position=position,
              answer=answer, correct=None if content["annulled"] else answer == content["correct_answer"],
              context={"schema_version": "1.0", "content_version": item["version"], "canonical_id": item.get('canonical_id') or item['question_id'], "mode": "exam",
                       "help_used": False, "labels": content["labels"]}))
    db.flush()
    return run_data(run)
