# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.5.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache
WORKDIR /app

FROM base AS builder
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"
COPY pyproject.toml poetry.lock ./
RUN --mount=type=cache,target=${POETRY_CACHE_DIR} \
    poetry install --without dev --no-root
COPY src ./src
RUN --mount=type=cache,target=${POETRY_CACHE_DIR} \
    poetry install --without dev

FROM base AS runtime
COPY --from=builder /app/.venv ./.venv
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
ENV PATH="/app/.venv/bin:${PATH}"
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request as u; import sys; sys.exit(0 if u.urlopen('http://localhost:8000/health', timeout=2).getcode() == 200 else 1)"
CMD ["uvicorn", "mercado_jogadores.main:app", "--host", "0.0.0.0", "--port", "8000"]
