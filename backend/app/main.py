import copy
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models as m, schemas as s
from .content import exam_summary, import_exam, public_question, publish_exam, validate_assets
from .db import ROOT, get_db
from .scoring import aggregate, score
from .security import COOKIE, admin_user, current_user, digest, hash_password, new_session, user_data, verify_password

logger = logging.getLogger("enem_flow")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
logger.propagate = False


@asynccontextmanager
async def lifespan(app):
    # Schema management is explicit: alembic upgrade head.
    (ROOT / "data/assets").mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Enem Flow", version="0.1.0", lifespan=lifespan)
app.mount("/assets", StaticFiles(directory=ROOT / "data/assets"), name="assets")


@app.middleware("http")
async def request_policy(request: Request, call_next):
    request_id = secrets.token_hex(8)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        allowed = set(os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","))
        origin = request.headers.get("origin")
        if origin and origin not in allowed:
            return JSONResponse({"detail": "Origem da requisição não autorizada."}, status_code=403)
        if len(await request.body()) > 4_000_000:
            return JSONResponse({"detail": "O conteúdo excede o limite de 4 MB."}, status_code=413)
    start = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    logger.info("request=%s method=%s path=%s status=%s ms=%.1f", request_id, request.method,
                request.url.path, response.status_code, (time.monotonic() - start) * 1000)
    return response


@app.exception_handler(RequestValidationError)
async def invalid_input(_, exc):
    # Do not echo submitted credentials or private fields in validation errors.
    errors = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse({"detail": "Confira os campos informados.", "errors": errors}, status_code=422)


def throttle(db, request):
    key = digest(request.client.host if request.client else "unknown")
    now = time.time()
    # Atomic upsert is portable through an UPDATE-first loop; commit failures as well as successes.
    row = db.get(m.AuthAttempt, key)
    if row and row.window_start > now - 900 and row.count >= 30:
        raise HTTPException(429, "Muitas tentativas. Aguarde 15 minutos e tente novamente.")
    if not row:
        db.add(m.AuthAttempt(key=key, count=1, window_start=now))
    elif row.window_start <= now - 900:
        row.count, row.window_start = 1, now
    else:
        db.execute(update(m.AuthAttempt).where(m.AuthAttempt.key == key).values(count=m.AuthAttempt.count + 1))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        db.execute(update(m.AuthAttempt).where(m.AuthAttempt.key == key).values(count=m.AuthAttempt.count + 1))
        db.commit()


@app.get("/health")
def health(db: Session = Depends(get_db, scope="function")):
    db.execute(select(func.count()).select_from(m.User))
    return {"status": "ok", "version": app.version}


@app.post("/auth/register", status_code=201)
def register(payload: s.Register, response: Response, request: Request, db: Session = Depends(get_db, scope="function")):
    throttle(db, request)
    user = m.User(email=payload.email, name=payload.name, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Este e-mail já possui uma conta. Entre para continuar.")
    new_session(db, user, response)
    return user_data(user)


@app.post("/auth/login")
def login(payload: s.Login, response: Response, request: Request, db: Session = Depends(get_db, scope="function")):
    throttle(db, request)
    user = db.scalar(select(m.User).where(m.User.email == payload.email))
    # Run an equivalent hash even when the address is unknown.
    valid = verify_password(payload.password, user.password_hash) if user else bool(hash_password(payload.password)) and False
    if not valid:
        raise HTTPException(401, "E-mail ou senha incorretos.")
    old = request.cookies.get(COOKIE)
    if old:
        db.execute(delete(m.AuthSession).where(m.AuthSession.token_hash == digest(old)))
    new_session(db, user, response)
    return user_data(user)


@app.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db, scope="function")):
    token = request.cookies.get(COOKIE)
    if token:
        db.execute(delete(m.AuthSession).where(m.AuthSession.token_hash == digest(token)))
    response.delete_cookie(COOKIE, path="/")


@app.post("/auth/reset-password")
def reset_password(payload: s.ResetPassword, request: Request, db: Session = Depends(get_db, scope="function")):
    throttle(db, request)
    # Consume with a conditional DELETE so concurrent replays cannot both succeed.
    token = db.execute(delete(m.RecoveryToken).where(m.RecoveryToken.token_hash == digest(payload.token),
                       m.RecoveryToken.expires_at > time.time()).returning(m.RecoveryToken.user_id)).scalar_one_or_none()
    if not token:
        raise HTTPException(400, "Link de recuperação inválido ou expirado.")
    db.get(m.User, token).password_hash = hash_password(payload.password)
    db.execute(delete(m.AuthSession).where(m.AuthSession.user_id == token))
    return {"message": "Senha atualizada. Entre novamente."}


@app.get("/me")
def me(user: m.User = Depends(current_user)):
    return user_data(user)


@app.put("/me/preferences")
def preferences(payload: s.Preferences, user: m.User = Depends(current_user)):
    user.name = payload.name
    user.preferences = payload.model_dump(exclude={"name"})
    return user_data(user)


def visible_exam(db, exam_id):
    exam = db.get(m.Exam, exam_id)
    if not exam or exam.status != "published":
        raise HTTPException(404, "Prova não encontrada ou ainda em revisão.")
    return exam


def summary(db, exam):
    data = exam_summary(db, exam)
    data["source"] = {key: exam.source[key] for key in ("url", "sha256", "publisher", "notes")}
    return data


@app.get("/exams")
def exams(year: int | None = None, area: str | None = None, application: str | None = None,
          booklet: str | None = None, q: str = "", db: Session = Depends(get_db, scope="function")):
    query = select(m.Exam).where(m.Exam.status == "published").order_by(m.Exam.year.desc())
    if year:
        query = query.where(m.Exam.year == year)
    if application:
        query = query.where(m.Exam.application == application)
    if booklet:
        query = query.where(m.Exam.booklet == booklet)
    rows = [summary(db, exam) for exam in db.scalars(query)]
    return [row for row in rows if (not area or area in row["areas"]) and (not q or q.casefold() in row["title"].casefold())]


@app.get("/exams/{exam_id}")
def exam_detail(exam_id: str, db: Session = Depends(get_db, scope="function")):
    exam = visible_exam(db, exam_id)
    return {**summary(db, exam), "items": [public_question({"id": key,
            "question_id": (question := db.get(m.QuestionVersion, key)).question_id,
            "version": question.version, "content": question.content}, False) for key in exam.items]}


@app.post("/exam-runs", status_code=201)
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
                      "content": copy.deepcopy(question.content)})
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


@app.get("/exam-runs/{run_id}")
def get_run(run_id: str, user: m.User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return run_data(owned_run(db, run_id, user.id))


@app.put("/exam-runs/{run_id}/answers/{item_id}")
def save_answer(run_id: str, item_id: str, payload: s.Answer, user: m.User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    run = owned_run(db, run_id, user.id, lock=True)
    if run.finished_at is not None:
        raise HTTPException(409, "Esta prova já foi finalizada e não aceita alterações.")
    if item_id not in {item["id"] for item in run.items}:
        raise HTTPException(404, "Questão não pertence a esta execução.")
    run.answers = {**run.answers, item_id: payload.choice}
    return {"answers": run.answers, "saved_at": time.time()}


@app.post("/exam-runs/{run_id}/finish")
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
              context={"schema_version": "1.0", "content_version": item["version"], "mode": "exam",
                       "help_used": False, "labels": content["labels"]}))
    db.flush()
    return run_data(run)


@app.get("/me/history")
def history(user: m.User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    runs = db.scalars(select(m.ExamRun).where(m.ExamRun.user_id == user.id).order_by(m.ExamRun.started_at.desc()))
    return [{"id": r.id, "exam": r.exam_info, "started_at": r.started_at, "finished_at": r.finished_at,
             "answered": sum(v is not None for v in r.answers.values()), "result": r.result} for r in runs]


@app.get("/me/progress")
def progress(user: m.User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    runs = list(db.scalars(select(m.ExamRun).where(m.ExamRun.user_id == user.id, m.ExamRun.finished_at.is_not(None)).order_by(m.ExamRun.finished_at)))
    return {**aggregate(runs), "evolution": [{"id": r.id, "date": r.finished_at, "percentage": r.result["percentage"],
                                             "title": r.exam_info["title"]} for r in runs]}


@app.delete("/me/history", status_code=204)
def delete_history(user: m.User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    db.execute(delete(m.LearningEvent).where(m.LearningEvent.user_id == user.id))
    db.execute(delete(m.ExamRun).where(m.ExamRun.user_id == user.id))


@app.get("/admin/exams")
def admin_exams(user: m.User = Depends(admin_user), db: Session = Depends(get_db, scope="function")):
    return [exam_summary(db, e) for e in db.scalars(select(m.Exam).order_by(m.Exam.created_at.desc()))]


@app.post("/admin/imports", status_code=201)
def admin_import(payload: s.ExamImport, user: m.User = Depends(admin_user), db: Session = Depends(get_db, scope="function")):
    exam = import_exam(db, payload)
    db.add(m.Review(user_id=user.id, target_id=exam.id, action="import", reason="Importação validada pelo contrato 1.0; aguardando revisão humana."))
    return exam_summary(db, exam)


@app.get("/admin/exams/{exam_id}")
def admin_exam(exam_id: str, user: m.User = Depends(admin_user), db: Session = Depends(get_db, scope="function")):
    exam = db.get(m.Exam, exam_id)
    if not exam:
        raise HTTPException(404, "Prova não encontrada.")
    return {**exam_summary(db, exam), "items": [{"id": q.id, "question_id": q.question_id,
            "version": q.version, "status": q.status, "content": q.content}
            for key in exam.items if (q := db.get(m.QuestionVersion, key))]}


@app.put("/admin/questions/{version_id}")
def edit_question(version_id: str, payload: s.EditQuestion, user: m.User = Depends(admin_user), db: Session = Depends(get_db, scope="function")):
    previous = db.get(m.QuestionVersion, version_id)
    if not previous:
        raise HTTPException(404, "Versão não encontrada.")
    validate_assets(payload.content.model_dump())
    last = db.scalar(select(func.max(m.QuestionVersion.version)).where(m.QuestionVersion.question_id == previous.question_id))
    if last != previous.version:
        raise HTTPException(409, "Há uma versão mais recente. Atualize a tela antes de editar.")
    version = last + 1
    question = m.QuestionVersion(id=f"{previous.question_id}:{version}", question_id=previous.question_id,
                                version=version, content=payload.content.model_dump())
    db.add(question)
    # Published exams are withdrawn until the new version is reviewed and published again.
    for exam in db.scalars(select(m.Exam)):
        if previous.id in exam.items:
            exam.items = [question.id if key == previous.id else key for key in exam.items]
            exam.status = "in_review"
    db.add(m.Review(user_id=user.id, target_id=question.id, action="edit", reason=payload.reason))
    try:
        db.flush()
    except IntegrityError:
        raise HTTPException(409, "Outro revisor criou uma versão. Atualize a tela.")
    return {"id": question.id, "version": version, "status": "draft"}


@app.post("/admin/reviews/{target_id}")
def review(target_id: str, payload: s.ReviewRequest, user: m.User = Depends(admin_user), db: Session = Depends(get_db, scope="function")):
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
    question.status = "approved" if payload.action == "approve" else "in_review"
    if payload.action == "reject":
        for linked in db.scalars(select(m.Exam).where(m.Exam.status == "published")):
            if question.id in linked.items:
                linked.status = "in_review"
    db.add(m.Review(user_id=user.id, target_id=target_id, action=payload.action, reason=payload.reason))
    return {"id": question.id, "status": question.status}


@app.get("/admin/audit")
def audit(user: m.User = Depends(admin_user), db: Session = Depends(get_db, scope="function")):
    return [{"id": r.id, "target_id": r.target_id, "action": r.action, "reason": r.reason,
             "reviewer_id": r.user_id, "created_at": r.created_at}
            for r in db.scalars(select(m.Review).order_by(m.Review.created_at.desc()).limit(200))]
