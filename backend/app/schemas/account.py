"""Sign-in, registration, preferences and password recovery."""
import re

from pydantic import Field, field_validator

from .base import Schema


class Login(Schema):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def email_address(cls, value):
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Informe um e-mail válido.")
        return value.casefold()


class Register(Login):
    name: str = Field(min_length=2, max_length=80)


class Preferences(Schema):
    name: str = Field(min_length=2, max_length=80)
    target_course: str = Field(default="", max_length=120)
    daily_goal: int = Field(default=10, ge=1, le=100)


class ResetPassword(Schema):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=10, max_length=128)
