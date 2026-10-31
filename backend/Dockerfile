FROM python:3.13-slim
WORKDIR /app
COPY backend/requirements.lock backend/requirements.lock
RUN pip install --no-cache-dir -r backend/requirements.lock
COPY backend backend
COPY alembic.ini .
COPY data data
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m backend.app.cli seed --publish-reviewed --refresh-bundled && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --log-level info"]
