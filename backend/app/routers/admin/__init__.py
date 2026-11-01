"""Curation routes under /admin; every route requires an administrator."""
from fastapi import APIRouter

from . import archive, content

router = APIRouter(prefix="/admin")
router.include_router(content.router)
router.include_router(archive.router)
