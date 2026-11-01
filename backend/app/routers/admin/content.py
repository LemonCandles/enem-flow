"""Curation of versioned content: import, preview, edit, review, publish and audit."""
from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ... import models as m, schemas as s
from ...dependencies import AdminUser, SessionDep
from ...preparation import blocking_issues, prepare_content, prepare_exam
from ...services.content import exam_summary, import_exam, publish_exam, validate_assets
from ...services.identity import identify, validate_exam_identities, validate_revision_identity

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
    db.add(m.Review(user_id=user.id, target_id=exam.id, action="import", reason=f"Preparação {report['version']}: {report['changes']} operações, {report['warnings']} avisos, {report['errors']} pendências bloqueantes; aguardando revisão humana."))
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
    return {**exam_summary(db, exam), "items": [{"id": q.id, "question_id": q.question_id,
            "version": q.version, "status": q.status, "content": q.content}
            for key in exam.items if (q := db.get(m.QuestionVersion, key))]}


@router.put("/questions/{version_id}")
def edit_question(version_id: str, payload: s.EditQuestion, user: AdminUser, db: SessionDep):
    previous = db.get(m.QuestionVersion, version_id)
    if not previous:
        raise HTTPException(404, "Versão não encontrada.")
    try:
        content = prepare_content(payload.content.model_dump())
    except ValueError as error:
        raise HTTPException(422, str(error))
    validate_assets(content)
    last = db.scalar(select(func.max(m.QuestionVersion.version)).where(m.QuestionVersion.question_id == previous.question_id))
    if last != previous.version:
        raise HTTPException(409, "Há uma versão mais recente. Atualize a tela antes de editar.")
    canonical_id = previous.canonical_id or identify(db, previous.content)
    validate_revision_identity(db, content, canonical_id)
    linked_exams = [exam for exam in db.scalars(select(m.Exam)) if previous.id in exam.items]
    for exam in linked_exams:
        items = [(canonical_id, content) if key == previous.id else
                 (q.canonical_id, q.content) for key in exam.items
                 if (q := db.get(m.QuestionVersion, key))]
        validate_exam_identities(items)
    version = last + 1
    question = m.QuestionVersion(id=f"{previous.question_id}:{version}", question_id=previous.question_id,
                                canonical_id=canonical_id, version=version, content=content)
    db.add(question)
    # Published exams are withdrawn until the new version is reviewed and published again.
    for exam in linked_exams:
        exam.items = [question.id if key == previous.id else key for key in exam.items]
        exam.status = "in_review"
    db.add(m.Review(user_id=user.id, target_id=question.id, action="edit", reason=payload.reason))
    try:
        db.flush()
    except IntegrityError:
        raise HTTPException(409, "Outro revisor criou uma versão. Atualize a tela.")
    return {"id": question.id, "version": version, "status": "draft"}


@router.post("/reviews/{target_id}")
def review(target_id: str, payload: s.ReviewRequest, user: AdminUser, db: SessionDep):
    exam = db.get(m.Exam, target_id)
    if exam:
        if payload.action == "publish":
            publish_exam(db, exam, user.id, payload.reason)
        elif payload.action == "withdraw":
            exam.status = "withdrawn"
            db.add(m.Review(user_id=user.id, target_id=target_id, action=payload.action, reason=payload.reason))
        else:
            raise HTTPException(422, "Para provas, use publicar ou retirar.")
        return {"id": exam.id, "status": exam.status}
    question = db.get(m.QuestionVersion, target_id)
    if not question:
        raise HTTPException(404, "Alvo da revisão não encontrado.")
    if payload.action not in {"approve", "reject"}:
        raise HTTPException(422, "Para questões, use aprovar ou rejeitar.")
    if payload.action == 'approve' and blocking_issues(question.content):
        raise HTTPException(409, 'Corrija as pendências bloqueantes da preparação e salve uma nova versão antes de aprovar.')
    question.status = "approved" if payload.action == "approve" else "in_review"
    if payload.action == "reject":
        for linked in db.scalars(select(m.Exam).where(m.Exam.status == "published")):
            if question.id in linked.items:
                linked.status = "in_review"
    db.add(m.Review(user_id=user.id, target_id=target_id, action=payload.action, reason=payload.reason))
    return {"id": question.id, "status": question.status}


@router.get("/audit")
def audit(db: SessionDep):
    return [{"id": r.id, "target_id": r.target_id, "action": r.action, "reason": r.reason,
             "reviewer_id": r.user_id, "created_at": r.created_at}
            for r in db.scalars(select(m.Review).order_by(m.Review.created_at.desc()).limit(200))]
