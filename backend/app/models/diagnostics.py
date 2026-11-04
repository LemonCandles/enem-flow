"""Fixed diagnostic sessions with immutable content snapshots."""

import time

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base
from ._ids import uid


class DiagnosticSession(Base):
    __tablename__ = "diagnostic_sessions"
    __table_args__ = (UniqueConstraint("user_id", "start_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    start_key: Mapped[str] = mapped_column(String(80))
    objective: Mapped[str] = mapped_column(String(120))
    area: Mapped[str] = mapped_column(String(80))
    available_minutes: Mapped[int] = mapped_column(Integer)
    selection: Mapped[dict] = mapped_column(JSON)
    items: Mapped[list] = mapped_column(JSON)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[float] = mapped_column(Float, default=time.time)
    finished_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
