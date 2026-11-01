"""Request policy applied to every request: origin and size checks, security headers and access log.

It stays a single middleware so the order is fixed: reject before the route
runs, then add headers and log after it answers.
"""
import logging
import secrets
import time

from fastapi import Request
from fastapi.responses import JSONResponse

from .core.config import allowed_origins

logger = logging.getLogger("enem_flow")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
logger.propagate = False


async def rejection(request: Request):
    """Writes from another origin or with a body over 4 MB are refused before reaching a route."""
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        allowed = allowed_origins()
        origin = request.headers.get("origin")
        if origin and origin not in allowed:
            return JSONResponse({"detail": "Origem da requisição não autorizada."}, status_code=403)
        if len(await request.body()) > 4_000_000:
            return JSONResponse({"detail": "O conteúdo excede o limite de 4 MB."}, status_code=413)
    return None


def add_security_headers(response, request_id):
    response.headers["X-Request-ID"] = request_id
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"


async def request_policy(request: Request, call_next):
    request_id = secrets.token_hex(8)
    refused = await rejection(request)
    if refused:
        return refused
    start = time.monotonic()
    response = await call_next(request)
    add_security_headers(response, request_id)
    logger.info("request=%s method=%s path=%s status=%s ms=%.1f", request_id, request.method,
                request.url.path, response.status_code, (time.monotonic() - start) * 1000)
    return response
