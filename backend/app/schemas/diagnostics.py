"""Diagnostic creation contract."""

from typing import Literal
from pydantic import Field
from .base import Schema


class StartDiagnostic(Schema):
    objective: str = Field(min_length=1, max_length=120)
    area: Literal['Matemática', 'Ciências da Natureza', 'Ciências Humanas', 'Linguagens']
    available_minutes: int = Field(ge=3, le=180)
    idempotency_key: str = Field(min_length=8, max_length=80)
