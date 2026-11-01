"""Exam attempts: starting a run and answering."""
from typing import Literal

from pydantic import Field

from .base import Schema


class StartRun(Schema):
    exam_id: str = Field(max_length=80)
    idempotency_key: str = Field(min_length=8, max_length=80)


class Answer(Schema):
    choice: Literal["A", "B", "C", "D", "E"] | None
