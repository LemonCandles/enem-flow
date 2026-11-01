"""Curation routes under /admin; every route requires an administrator.

The curation role is checked once here. Routes that record who acted still
receive the user through AdminUser; FastAPI resolves it once per request.
"""
from fastapi import APIRouter, Depends

from ...core.security import admin_user
from . import archive, content

router = APIRouter(prefix="/admin", dependencies=[Depends(admin_user)])
router.include_router(content.router)
router.include_router(archive.router)
