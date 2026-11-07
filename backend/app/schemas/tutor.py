"""Tutor requests: help in practice and curation of the approved material."""

from typing import Literal

from pydantic import Field

from .base import Schema

Level = Literal['orientation', 'hint', 'solution']


class HelpRequest(Schema):
    level: Level
    idempotency_key: str = Field(min_length=8, max_length=80)


class MaterialLevels(Schema):
    orientation: str = Field(min_length=1, max_length=3000)
    hint: str = Field(min_length=1, max_length=3000)
    solution: str = Field(min_length=1, max_length=3000)


class MaterialReview(Schema):
    action: Literal['approve', 'reject']
    reason: str = Field(min_length=10, max_length=2000)
