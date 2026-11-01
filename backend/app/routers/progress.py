"""The student's attempt history and performance summary."""
from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db
from ..scoring import aggregate
from ..security import current_user

router = APIRouter(prefix="/me", tags=["desempenho"])


@router.get("/history")
def history(user: m.User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    runs = db.scalars(select(m.ExamRun).where(m.ExamRun.user_id == user.id).order_by(m.ExamRun.started_at.desc()))
    return [{"id": r.id, "exam": r.exam_info, "started_at": r.started_at, "finished_at": r.finished_at,
             "answered": sum(v is not None for v in r.answers.values()), "result": r.result} for r in runs]


@router.get("/progress")
def progress(user: m.User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    runs = list(db.scalars(select(m.ExamRun).where(m.ExamRun.user_id == user.id, m.ExamRun.finished_at.is_not(None)).order_by(m.ExamRun.finished_at)))
    return {**aggregate(runs), "evolution": [{"id": r.id, "date": r.finished_at, "percentage": r.result["percentage"],
                                             "title": r.exam_info["title"]} for r in runs]}


@router.delete("/history", status_code=204)
def delete_history(user: m.User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    db.execute(delete(m.LearningEvent).where(m.LearningEvent.user_id == user.id))
    db.execute(delete(m.ExamRun).where(m.ExamRun.user_id == user.id))
