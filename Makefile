.PHONY: setup migrate seed acervo api web test lint format build experiments experiments-archive audit-archive audit-archive-browser experiments-all
PYTHON = .venv/bin/python
EXPERIMENT_OUTPUT ?= tmp/experiments/latest
AUDIT_OUTPUT ?= tmp/acervo-validacao/latest
AUDIT_URL ?= http://127.0.0.1:3100

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r backend/requirements-dev.lock
	cd frontend && npm ci
	$(MAKE) migrate seed

migrate:
	.venv/bin/alembic upgrade head

seed:
	$(PYTHON) -m backend.app.cli seed --publish-reviewed --refresh-bundled

# Provas do acervo extraídas sem curadoria; exige o espelho local (archive_enem.py sync).
acervo:
	$(PYTHON) scripts/build_archive_exams.py
	$(PYTHON) -m backend.app.cli archive

api:
	.venv/bin/uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

web:
	cd frontend && npm run dev

test:
	.venv/bin/pytest -q
	cd frontend && npm run typecheck
	cd frontend && npm run check:content

lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .
	cd frontend && npm run format:check

format:
	.venv/bin/ruff format .
	cd frontend && npm run format

build:
	cd frontend && npm run build

# Experimentos offline; não alteram o catálogo/banco nem chamam provedores.
experiments:
	$(PYTHON) scripts/run_experiments.py --output "$(EXPERIMENT_OUTPUT)"

experiments-archive:
	$(PYTHON) scripts/run_experiments.py --archive --ocr --output "$(EXPERIMENT_OUTPUT)"

# Auditoria local; correção em banco descartável. A base de uso fica somente para leitura.
audit-archive:
	$(PYTHON) scripts/audit_archive.py --output "$(AUDIT_OUTPUT)" --scoring --render-sources --resume

# Exige frontend construído/iniciado e o manifesto produzido pela auditoria.
audit-archive-browser:
	node scripts/audit_archive_browser.cjs --input "$(AUDIT_OUTPUT)" --url "$(AUDIT_URL)" --workers 1 --capture-issues

# Exige os modelos/relatórios de make experiments e o acervo histórico local.
experiments-all:
	$(PYTHON) scripts/experiment_archive_all.py --output "$(AUDIT_OUTPUT)/etapa3" --model "$(EXPERIMENT_OUTPUT)/classification-model.json"
