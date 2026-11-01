"""Common configuration of every request schema."""
from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
