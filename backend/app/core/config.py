"""Paths and environment settings in one place.

DATABASE_URL is read once, when the engine is created. Cookie security and
allowed origins are read on each use, as before, so a changed environment
takes effect without reloading the module.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'enem-flow.db'}")


def cookie_secure():
    return os.getenv("COOKIE_SECURE", "false").lower() == "true"


def allowed_origins():
    return set(os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","))
