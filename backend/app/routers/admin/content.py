"""Curation of versioned content: import, preview, edit, review, publish and audit."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from ... import models as m, schemas as s
from ...dependencies import AdminUser, SessionDep
from ...preparation import prepare_exam
from ...services.content import exam_summary, import_exam
from ...services.lifecycle import EXAM_ACTIONS, QUESTION_ACTIONS
from ...services.revisions import revise_question

router = APIRouter(tags=["curadoria"])


@router.get("/exams")
def admin_exams(db: SessionDep):
    return [exam_summary(db, e) for e in db.scalars(select(m.Exam).order_by(m.Exam.created_at.desc()))]


@router.post("/imports", status_code=201)
def admin_import(payload: s.ExamImport, user: AdminUser, db: SessionDep):
    try:
        prepared, report = prepare_exam(payload)
    except ValueError as error:
        raise HTTPException(422, str(error))
    exam = import_exam(db, prepared)
    db.add(
        m.Review(
            user_id=user.id,
            target_id=exam.id,
            action="import",
            reason=f"Preparação {report['version']}: {report['changes']} operações, {report['warnings']} avisos, {report['errors']} pendências bloqueantes; aguardando revisão humana.",
        )
    )
    return {**exam_summary(db, exam), 'preparation': report}


@router.post("/imports/prepare")
def preview_import(payload: s.ExamImport):
    """Read-only preview uses the exact same preparation as the actual import."""
    try:
        prepared, report = prepare_exam(payload)
    except ValueError as error:
        raise HTTPException(422, str(error))
    return {'exam': prepared.model_dump(), 'report': report}


@router.get("/exams/{exam_id}")
def admin_exam(exam_id: str, db: SessionDep):
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise HTTPException(404, "Prova não encontrada.")
    return {
        **exam_summary(db, exam),
        "items": [
            {"id": q.id, "question_id": q.question_id, "version": q.version, "status": q.status, "content": q.content}
            for key in exam.items
            if (q := db.get(m.QuestionVersion, key))
        ],
    }


@router.put("/questions/{version_id}")
def edit_question(version_id: str, payload: s.EditQuestion, user: AdminUser, db: SessionDep):
    previous = db.get(m.QuestionVersion, version_id)
    if not previous:
        raise HTTPException(404, "Versão não encontrada.")
    question = revise_question(db, previous, payload.content.model_dump(), user.id, payload.reason)
    return {"id": question.id, "version": question.version, "status": "draft"}


@router.post("/reviews/{target_id}")
def review(target_id: str, payload: s.ReviewRequest, user: AdminUser, db: SessionDep):
    exam = db.get(m.Exam, target_id)
    if exam:
        action = EXAM_ACTIONS.get(payload.action)
        if not action:
            raise HTTPException(422, "Para provas, use publicar ou retirar.")
        action(db, exam, user.id, payload.reason)
        return {"id": exam.id, "status": exam.status}
    question = db.get(m.QuestionVersion, target_id)
    if not question:
        raise HTTPException(404, "Alvo da revisão não encontrado.")
    action = QUESTION_ACTIONS.get(payload.action)
    if not action:
        raise HTTPException(422, "Para questões, use aprovar ou rejeitar.")
    action(db, question, user.id, payload.reason)
    return {"id": question.id, "status": question.status}


@router.get("/audit")
def audit(db: SessionDep):
    return [
        {
            "id": r.id,
            "target_id": r.target_id,
            "action": r.action,
            "reason": r.reason,
            "reviewer_id": r.user_id,
            "created_at": r.created_at,
        }
        for r in db.scalars(select(m.Review).order_by(m.Review.created_at.desc()).limit(200))
    ]
