FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Workspace skeleton first — copy every member's pyproject.toml so `uv sync`
# can resolve the workspace lock without needing the package sources yet.
# This keeps the dependency install in its own cacheable layer.
COPY pyproject.toml uv.lock ./
COPY packages/connhex-sdk/pyproject.toml ./packages/connhex-sdk/
COPY packages/connhex-mcp/pyproject.toml ./packages/connhex-mcp/
COPY packages/connhex-cli/pyproject.toml ./packages/connhex-cli/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-workspace

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked


FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

COPY --from=builder --chown=nonroot:nonroot /app /app

ENV PATH="/app/.venv/bin:$PATH"

USER nonroot

WORKDIR /app

# Default to remote mode, overridable at run-time:
#   docker run <image> # → connhex-mcp --mode remote
#   docker run <image> --mode local --transport streamable-http
ENTRYPOINT ["connhex-mcp"]
CMD ["--mode", "remote"]
