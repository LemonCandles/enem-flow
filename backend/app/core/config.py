"""Paths and environment settings in one place.

The `.env` file at the project root is read once, without replacing variables
already set by the shell or by Docker Compose. DATABASE_URL is read once, when
the engine is created. Cookie security, allowed origins and the tutor settings
are read on each use, so a changed environment takes effect without reloading
the module.
"""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / '.env', override=False)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'enem-flow.db'}")


def cookie_secure():
    return os.getenv("COOKIE_SECURE", "false").lower() == "true"


def allowed_origins():
    return set(os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","))


@dataclass(frozen=True)
class TutorSettings:
    """OpenAI-compatible provider (Groq by default) and the limits of each call."""

    api_key: str
    base_url: str
    model: str
    timeout_seconds: float
    max_output_tokens: int
    daily_limit: int
    price_input_per_mtok: float | None
    price_output_per_mtok: float | None
    max_cost_usd: float | None

    @property
    def missing(self):
        """Settings without which the provider is not called; approved material still works."""
        required = {
            'GROQ_API_KEY': self.api_key,
            'TUTOR_MODEL': self.model,
            'TUTOR_PRICE_INPUT_PER_MTOK': self.price_input_per_mtok,
            'TUTOR_PRICE_OUTPUT_PER_MTOK': self.price_output_per_mtok,
            'TUTOR_MAX_COST_USD': self.max_cost_usd,
        }
        return [name for name, value in required.items() if value in (None, '')]

    @property
    def enabled(self):
        return not self.missing


def _number(name, default=None, kind=float):
    value = os.getenv(name, '').strip()
    if not value:
        return default
    try:
        return kind(value)
    except ValueError:
        return default


def tutor_settings():
    return TutorSettings(
        api_key=os.getenv('GROQ_API_KEY', '').strip(),
        base_url=os.getenv('TUTOR_BASE_URL', '').strip() or 'https://api.groq.com/openai/v1',
        model=os.getenv('TUTOR_MODEL', '').strip(),
        timeout_seconds=max(1.0, min(60.0, _number('TUTOR_TIMEOUT_SECONDS', 10.0))),
        max_output_tokens=max(50, min(4000, _number('TUTOR_MAX_OUTPUT_TOKENS', 500, int))),
        daily_limit=max(0, _number('TUTOR_DAILY_LIMIT', 40, int)),
        price_input_per_mtok=_number('TUTOR_PRICE_INPUT_PER_MTOK'),
        price_output_per_mtok=_number('TUTOR_PRICE_OUTPUT_PER_MTOK'),
        max_cost_usd=_number('TUTOR_MAX_COST_USD'),
    )
