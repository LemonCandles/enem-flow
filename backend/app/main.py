"""Application assembly: lifespan, request policy, validation errors, static assets and feature routers."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .core.config import ROOT
from .middleware import request_policy
from .routers import account, admin, auth, exams, health, progress, runs

# Documentation only: groups shown in /docs, in this order.
TAGS = [
    {"name": "saúde", "description": "Verificação de funcionamento da API e do banco."},
    {"name": "autenticação", "description": "Cadastro, entrada, saída e redefinição de senha por link de uso único. Limitado por tentativas."},
    {"name": "conta", "description": "Dados e preferências da conta conectada."},
    {"name": "provas", "description": "Catálogo público de provas publicadas, sem gabarito."},
    {"name": "execuções", "description": "Tentativas de prova: início idempotente, respostas salvas e finalização com correção."},
    {"name": "desempenho", "description": "Histórico e agregações de desempenho da própria conta."},
    {"name": "curadoria", "description": "Importação, edição versionada, revisão, publicação e auditoria. Exige papel de curadoria."},
    {"name": "acervo", "description": "Consulta somente leitura às extrações do acervo oficial e à taxonomia. Exige papel de curadoria."},
]


@asynccontextmanager
async def lifespan(app):
    # Schema management is explicit: alembic upgrade head.
    (ROOT / "data/assets").mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Enem Flow", version="0.1.0", lifespan=lifespan, openapi_tags=TAGS)
app.mount("/assets", StaticFiles(directory=ROOT / "data/assets"), name="assets")
app.middleware("http")(request_policy)


@app.exception_handler(RequestValidationError)
async def invalid_input(_, exc):
    # Do not echo submitted credentials or private fields in validation errors.
    errors = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse({"detail": "Confira os campos informados.", "errors": errors}, status_code=422)


# Same registration order as the routes had in a single module.
for feature in (health, auth, account, exams, runs, progress, admin):
    app.include_router(feature.router)
