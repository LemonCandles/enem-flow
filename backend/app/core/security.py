import hashlib
import hmac
import secrets
import time

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuthSession, User
from .config import cookie_secure
from .db import get_db

COOKIE = "enem_session"
SESSION_AGE = 60 * 60 * 24 * 30


def digest(value: str):
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password: str):
    salt = secrets.token_hex(16)
    key = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return f"scrypt${salt}${key.hex()}"


def verify_password(password: str, stored: str):
    try:
        _, salt, expected = stored.split("$")
        key = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(key.hex(), expected)
    except (ValueError, TypeError):
        return False


def new_session(db: Session, user: User, response: Response):
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=digest(token), user_id=user.id, expires_at=time.time() + SESSION_AGE))
    response.set_cookie(COOKIE, token, max_age=SESSION_AGE, httponly=True,
                        secure=cookie_secure(), samesite="strict", path="/")


def current_user(request: Request, db: Session = Depends(get_db, scope="function")):
    token = request.cookies.get(COOKIE)
    session = db.get(AuthSession, digest(token)) if token else None
    if not session or session.expires_at <= time.time():
        raise HTTPException(401, "Entre na sua conta para continuar.")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, "Sessão inválida.")
    return user


def admin_user(user: User = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Esta ação exige acesso de curadoria.")
    return user


def user_data(user: User):
    return {"id": user.id, "name": user.name, "email": user.email,
            "role": user.role, "preferences": user.preferences}
