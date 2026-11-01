"""Public catalog of published exams."""
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from .. import models as m
from ..dependencies import SessionDep
from ..services.content import exam_summary, public_question

router = APIRouter(prefix="/exams", tags=["provas"])


def visible_exam(db, exam_id):
    exam = db.get(m.Exam, exam_id)
    if not exam or exam.status != "published":
        raise HTTPException(404, "Prova não encontrada ou ainda em revisão.")
    return exam


def summary(db, exam):
    data = exam_summary(db, exam)
    data["source"] = {key: exam.source[key] for key in ("url", "sha256", "publisher", "notes")}
    return data


@router.get("")
def exams(db: SessionDep, year: int | None = None, area: str | None = None, application: str | None = None,
          booklet: str | None = None, q: str = ""):
    query = select(m.Exam).where(m.Exam.status == "published").order_by(m.Exam.year.desc())
    if year:
        query = query.where(m.Exam.year == year)
    if application:
        query = query.where(m.Exam.application == application)
    if booklet:
        query = query.where(m.Exam.booklet == booklet)
    rows = [summary(db, exam) for exam in db.scalars(query)]
    return [row for row in rows if (not area or area in row["areas"]) and (not q or q.casefold() in row["title"].casefold())]


@router.get("/{exam_id}")
def exam_detail(exam_id: str, db: SessionDep):
    exam = visible_exam(db, exam_id)
    return {**summary(db, exam), "items": [public_question({"id": key,
            "question_id": (question := db.get(m.QuestionVersion, key)).question_id,
            "canonical_id": question.canonical_id, "version": question.version, "content": question.content}, False) for key in exam.items]}
