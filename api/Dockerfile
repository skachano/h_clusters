# Build context: the repository root (compose.yaml), so that the worker's pyproject is visible.
FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /usr/local/bin/uv

# Dependencies live in /opt/venv. The hclust package itself is not installed: its source is
# bind-mounted at /hclust/src, like the API's at /app/src (compose.yaml).
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
COPY worker/pyproject.toml /build/worker/
COPY api/pyproject.toml api/uv.lock /build/api/
RUN cd /build/api && uv sync --frozen --no-install-project --no-install-package hclust

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/src:/hclust/src \
    PYTHONUNBUFFERED=1 \
    HCLUST_DATA=/data

WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "--factory", "hclust_api.main:create_app", "--host", "0.0.0.0", "--port", "8000"]
