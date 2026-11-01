"""Exam attempts and the learning events recorded when they finish."""
import time

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base
from ._ids import uid


class ExamRun(Base):
    __tablename__ = "exam_runs"
    __table_args__ = (UniqueConstraint("user_id", "start_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id"))
    start_key: Mapped[str] = mapped_column(String(80))
    exam_info: Mapped[dict] = mapped_column(JSON)
    items: Mapped[list] = mapped_column(JSON)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[float] = mapped_column(Float, default=time.time)
    finished_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class LearningEvent(Base):
    __tablename__ = "learning_events"
    __table_args__ = (UniqueConstraint("run_id", "item_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("exam_runs.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[str] = mapped_column(String(100))
    position: Mapped[int] = mapped_column(Integer)
    answer: Mapped[str | None] = mapped_column(String(1), nullable=True)
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    context: Mapped[dict] = mapped_column(JSON)
