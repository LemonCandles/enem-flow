.PHONY: dev doctor check-distribution setup migrate seed acervo api web test lint format clean build experiments experiments-archive audit-archive audit-archive-browser experiments-all ml-setup ml-train ml-test
PYTHON = .venv/bin/python
EXPERIMENT_OUTPUT ?= tmp/experiments/latest
AUDIT_OUTPUT ?= tmp/acervo-validacao/latest
AUDIT_URL ?= http://127.0.0.1:3100
ML_OUTPUT ?= tmp/experiments/layout-neural-latest

setup:
	python3 scripts/local.py setup

dev:
	python3 scripts/local.py dev

doctor:
	python3 scripts/local.py doctor

check-distribution:
	$(PYTHON) scripts/check_distribution.py

migrate:
	.venv/bin/alembic upgrade head

seed:
	$(PYTHON) -m backend.app.cli local-catalog

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
	$(PYTHON) scripts/check_distribution.py

lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .
	cd frontend && npm run format:check

format:
	.venv/bin/ruff format .
	cd frontend && npm run format

clean:
	find backend experiments ingestion scripts -type d -name __pycache__ -prune -exec rm -rf -- {} +
	rm -rf -- .pytest_cache .ruff_cache frontend/test-results frontend/playwright-report frontend/blob-report
	rm -f -- frontend/tsconfig.tsbuildinfo

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

# Rede de tipos de layout: ambiente próprio em ml/ (uv), fora dos lockfiles do backend e do frontend.
ml-setup:
	cd ml && uv sync

# A saída precisa estar em tmp/ e vazia; três seeds, o teste é medido só depois da escolha.
ml-train:
	cd ml && .venv/bin/python -m layout_types.train --output "../$(ML_OUTPUT)"

ml-test:
	cd ml && .venv/bin/python -m pytest -q
