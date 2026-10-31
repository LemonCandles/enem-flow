.PHONY: setup migrate seed api web test build
PYTHON = .venv/bin/python

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r backend/requirements-dev.lock
	cd frontend && npm ci
	$(MAKE) migrate seed

migrate:
	.venv/bin/alembic upgrade head

seed:
	$(PYTHON) -m backend.app.cli seed --publish-reviewed --refresh-bundled

api:
	.venv/bin/uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

web:
	cd frontend && npm run dev

test:
	.venv/bin/pytest -q
	cd frontend && npm run typecheck
	cd frontend && npm run check:content

build:
	cd frontend && npm run build
