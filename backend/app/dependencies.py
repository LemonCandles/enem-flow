"""Reusable route dependencies, declared once with Annotated.

SessionDep commits the unit of work before the response is sent (function scope).
CurrentUser requires a valid session; AdminUser also requires the curation role.
"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from .core.db import get_db
from .core.security import admin_user, current_user
from .models import User

SessionDep = Annotated[Session, Depends(get_db, scope="function")]
CurrentUser = Annotated[User, Depends(current_user)]
AdminUser = Annotated[User, Depends(admin_user)]
