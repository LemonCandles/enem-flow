"""Account creation, sign-in, sign-out and password recovery."""
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models as m, schemas as s
from ..db import get_db
from ..security import COOKIE, digest, hash_password, new_session, user_data, verify_password

router = APIRouter(prefix="/auth", tags=["autenticação"])


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


@router.post("/register", status_code=201)
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


@router.post("/login")
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


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db, scope="function")):
    token = request.cookies.get(COOKIE)
    if token:
        db.execute(delete(m.AuthSession).where(m.AuthSession.token_hash == digest(token)))
    response.delete_cookie(COOKIE, path="/")


@router.post("/reset-password")
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
