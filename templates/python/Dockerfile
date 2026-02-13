# Multi-stage Docker build for Python MCP server
FROM python:3.12-slim AS builder

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1
WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

COPY src/ /app/src/
RUN uv sync --frozen

# Production image
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# {{SYSTEM_DEPS}} — AI factory adds system packages if needed
# RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["mcp-server-{{SERVER_NAME}}"]
