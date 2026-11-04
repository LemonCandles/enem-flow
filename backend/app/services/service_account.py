"""Identity recorded on reviews made by automated installs; it has no usable password."""

import secrets

from sqlalchemy import select

from ..core.security import hash_password
from ..models import User


def service_reviewer(db):
    reviewer = db.scalar(select(User).where(User.email == "content-bootstrap@invalid.local"))
    if not reviewer:
        reviewer = User(
            name="Importação conferida",
            email="content-bootstrap@invalid.local",
            password_hash=hash_password(secrets.token_urlsafe(64)),
            role="service",
        )
        db.add(reviewer)
        db.flush()
    return reviewer
