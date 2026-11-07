"""Tutor: approved help material per question and each help request of a practice."""

import time

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base
from ._ids import uid


class TutorMaterial(Base):
    """Three levels of help written for one exact content; only `approved` reaches students.

    `content_sha256` ties the material to the question text, alternatives and answer key it
    was written for: a corrected version needs new material.
    """

    __tablename__ = "tutor_materials"
    __table_args__ = (UniqueConstraint("question_id", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    question_id: Mapped[str] = mapped_column(String(100), index=True)
    canonical_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    content_sha256: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default='proposal')
    origin: Mapped[str] = mapped_column(String(20))
    levels: Mapped[dict] = mapped_column(JSON)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_reason: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class HelpEvent(Base):
    """One help request: attempt + item + content version + level, with what was delivered.

    `outcome` is `requested` until a message reaches the student; only `delivered` counts as
    help used. The provider fields describe the call even when the approved text was shown.
    """

    __tablename__ = "help_events"
    __table_args__ = (UniqueConstraint("user_id", "request_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[str] = mapped_column(String(100))
    content_version: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(20))
    request_key: Mapped[str] = mapped_column(String(80))
    material_id: Mapped[str] = mapped_column(ForeignKey("tutor_materials.id"))
    outcome: Mapped[str] = mapped_column(String(20), default='requested')
    mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[dict] = mapped_column(JSON, default=dict)
    requested_at: Mapped[float] = mapped_column(Float, default=time.time)
    delivered_at: Mapped[float | None] = mapped_column(Float, nullable=True)
