"""Adapter to an OpenAI-compatible chat API (Groq by default), the only code that calls the provider.

The adapter receives only the context of one help request: the question as text, the
alternatives and the approved material allowed for the level. It returns a structured
proposal or a failure, never raises for provider problems, and never runs code or tools:
the approved material is given in the context and is the only "tool" consulted.
"""

from dataclasses import dataclass, field
import json
import time

from openai import APITimeoutError, OpenAI, OpenAIError

PROMPT_VERSION = 'tutor-prompt-v1'
DRAFT_PROMPT_VERSION = 'tutor-material-prompt-v1'
TOOLS = ('approved_material',)


@dataclass
class ProviderResult:
    status: str  # ok, timeout, error, invalid
    data: dict = field(default_factory=dict)
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int = 0
    error: str = ''


def estimate_tokens(messages):
    """Conservative estimate before the call: about 3 characters per token in Portuguese."""
    return sum(len(m['content']) for m in messages) // 3 + 20


def cost_usd(settings, input_tokens, output_tokens):
    if input_tokens is None or output_tokens is None:
        return None
    return round(
        (input_tokens * settings.price_input_per_mtok + output_tokens * settings.price_output_per_mtok) / 1_000_000, 8
    )


def maximum_cost(settings, messages):
    return cost_usd(settings, estimate_tokens(messages), settings.max_output_tokens)


def complete_json(settings, messages):
    """One chat completion in JSON mode, with the configured timeout and no retries."""
    started = time.perf_counter()
    try:
        client = OpenAI(
            base_url=settings.base_url, api_key=settings.api_key, timeout=settings.timeout_seconds, max_retries=0
        )
        response = client.chat.completions.create(
            model=settings.model,
            messages=messages,
            max_tokens=settings.max_output_tokens,
            temperature=0.2,
            response_format={'type': 'json_object'},
        )
    except APITimeoutError:
        return ProviderResult('timeout', latency_ms=elapsed(started), error='Tempo limite do provedor excedido.')
    except OpenAIError as error:
        return ProviderResult('error', latency_ms=elapsed(started), error=type(error).__name__)
    usage = getattr(response, 'usage', None)
    result = ProviderResult(
        'ok',
        input_tokens=getattr(usage, 'prompt_tokens', None),
        output_tokens=getattr(usage, 'completion_tokens', None),
        latency_ms=elapsed(started),
    )
    try:
        data = json.loads(response.choices[0].message.content or '')
    except (IndexError, ValueError, TypeError):
        data = None
    if not isinstance(data, dict):
        result.status, result.error = 'invalid', 'Resposta fora do formato JSON combinado.'
        return result
    result.data = data
    return result


def elapsed(started):
    return round((time.perf_counter() - started) * 1000)
