FROM python:3.13-slim
WORKDIR /app
COPY backend/requirements.lock backend/requirements.lock
RUN pip install --no-cache-dir -r backend/requirements.lock
COPY backend backend
COPY alembic.ini .
COPY data/enem-2024-dia2-azul.json data/enem-2024-dia2-azul.json
COPY data/sources data/sources
COPY data/assets /opt/enem-bundled-assets
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "python -m backend.app.assets && alembic upgrade head && python -m backend.app.cli seed --publish-reviewed --refresh-bundled && exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --log-level info"]
