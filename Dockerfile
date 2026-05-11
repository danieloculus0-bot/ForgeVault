FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY backend /app/backend
COPY frontend /app/frontend
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini
RUN python -m pip install --no-cache-dir -e .

EXPOSE 8000
CMD ["uvicorn", "forgevault.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]
