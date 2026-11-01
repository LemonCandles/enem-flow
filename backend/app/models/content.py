"""Versioned content: canonical identities, question versions, exams and review decisions."""
import time

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base
from ._ids import uid


class CanonicalQuestion(Base):
    __tablename__ = "canonical_questions"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    signature: Mapped[str] = mapped_column(String(64), unique=True)
    answer_signature: Mapped[str | None] = mapped_column(String(64), nullable=True)


class QuestionVersion(Base):
    __tablename__ = "question_versions"
    __table_args__ = (UniqueConstraint("question_id", "version"),)
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    question_id: Mapped[str] = mapped_column(String(80), index=True)
    canonical_id: Mapped[str | None] = mapped_column(ForeignKey("canonical_questions.id"), nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class Exam(Base):
    __tablename__ = "exams"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    year: Mapped[int] = mapped_column(Integer, index=True)
    application: Mapped[str] = mapped_column(String(80))
    booklet: Mapped[str] = mapped_column(String(80))
    day: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20))
    expected_items: Mapped[int] = mapped_column(Integer)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    source: Mapped[dict] = mapped_column(JSON)
    items: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    target_id: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
