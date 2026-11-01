"""Application assembly: logging, request policy, static assets and feature routers."""
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .db import ROOT
from .routers import account, admin, auth, exams, health, progress, runs

logger = logging.getLogger("enem_flow")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
logger.propagate = False


@asynccontextmanager
async def lifespan(app):
    # Schema management is explicit: alembic upgrade head.
    (ROOT / "data/assets").mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Enem Flow", version="0.1.0", lifespan=lifespan)
app.mount("/assets", StaticFiles(directory=ROOT / "data/assets"), name="assets")


@app.middleware("http")
async def request_policy(request: Request, call_next):
    request_id = secrets.token_hex(8)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        allowed = set(os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","))
        origin = request.headers.get("origin")
        if origin and origin not in allowed:
            return JSONResponse({"detail": "Origem da requisição não autorizada."}, status_code=403)
        if len(await request.body()) > 4_000_000:
            return JSONResponse({"detail": "O conteúdo excede o limite de 4 MB."}, status_code=413)
    start = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    logger.info("request=%s method=%s path=%s status=%s ms=%.1f", request_id, request.method,
                request.url.path, response.status_code, (time.monotonic() - start) * 1000)
    return response


@app.exception_handler(RequestValidationError)
async def invalid_input(_, exc):
    # Do not echo submitted credentials or private fields in validation errors.
    errors = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse({"detail": "Confira os campos informados.", "errors": errors}, status_code=422)


# Same registration order as the routes had in a single module.
for feature in (health, auth, account, exams, runs, progress, admin):
    app.include_router(feature.router)
