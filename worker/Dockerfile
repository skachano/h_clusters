FROM python:3.12-slim-bookworm

ARG XTB_VERSION=6.7.1

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl xz-utils ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://github.com/grimme-lab/xtb/releases/download/v${XTB_VERSION}/xtb-${XTB_VERSION}-linux-x86_64.tar.xz" \
    | tar -xJ -C /opt \
 && ln -s /opt/xtb-dist /opt/xtb \
 && /opt/xtb/bin/xtb --version | grep -i version

COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /usr/local/bin/uv

# Dependencies live in /opt/venv; the source is bind-mounted at /app.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock /build/
RUN cd /build && uv sync --frozen --no-install-project

# /opt/orca is bind-mounted read-only at runtime (see compose.yaml).
ENV PATH=/opt/venv/bin:/opt/orca:/opt/xtb/bin:$PATH \
    PYTHONPATH=/app/src \
    LD_LIBRARY_PATH=/opt/orca/lib \
    XTBPATH=/opt/xtb/share/xtb \
    XTBEXE=/opt/xtb/bin/xtb \
    OMP_NUM_THREADS=1 \
    OMP_STACKSIZE=1G \
    PYTHONUNBUFFERED=1 \
    HCLUST_DATA=/data

WORKDIR /app
