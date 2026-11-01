"""Curation requests: review decisions and new question versions."""
from typing import Literal

from pydantic import Field

from .base import Schema
from .content import QuestionContent


class ReviewRequest(Schema):
    action: Literal["approve", "reject", "withdraw", "publish"]
    reason: str = Field(min_length=10, max_length=2000)


class EditQuestion(Schema):
    content: QuestionContent
    reason: str = Field(min_length=10, max_length=2000)
