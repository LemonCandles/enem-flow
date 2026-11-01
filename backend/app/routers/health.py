"""Service health check."""
from fastapi import APIRouter, Request
from sqlalchemy import func, select

from .. import models as m
from ..dependencies import SessionDep

router = APIRouter(tags=["saúde"])


@router.get("/health")
def health(request: Request, db: SessionDep):
    db.execute(select(func.count()).select_from(m.User))
    return {"status": "ok", "version": request.app.version}
