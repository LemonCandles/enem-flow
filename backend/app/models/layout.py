"""Layout proposals converted by a versioned adapter; they never change published content by themselves."""

import time

from sqlalchemy import JSON, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base
from ._ids import uid


class LayoutProposal(Base):
    """`invalid` keeps the reasons of a refused conversion; `approved` points to the draft version it created."""

    __tablename__ = "layout_proposals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    question_version_id: Mapped[str] = mapped_column(ForeignKey("question_versions.id"), index=True)
    adapter_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))
    proposal: Mapped[dict] = mapped_column(JSON)
    converted: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    comparison: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_reason: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    result_version_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
