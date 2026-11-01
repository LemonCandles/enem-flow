"""Service health check."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db

router = APIRouter(tags=["saúde"])


@router.get("/health")
def health(request: Request, db: Session = Depends(get_db, scope="function")):
    db.execute(select(func.count()).select_from(m.User))
    return {"status": "ok", "version": request.app.version}
