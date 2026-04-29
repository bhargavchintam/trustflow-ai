# syntax=docker/dockerfile:1.7

# ===== Stage 1: build the Next.js static export =====
FROM node:20-alpine AS frontend-build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9 --activate

# Public env vars are inlined into the JS bundle at build time by Next.js,
# so they MUST be passed as build args (not runtime env on App Runner).
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ARG NEXT_PUBLIC_API_BASE
ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL \
    NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY \
    NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE

COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile=false
COPY frontend/ ./
RUN pnpm build

# ===== Stage 2: Python backend with bundled static frontend =====
FROM python:3.12-slim AS backend
WORKDIR /app

# System deps for psycopg + healthchecks
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# uv for fast deterministic installs
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

# Python deps
COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv pip install --system --no-cache -r pyproject.toml

# App code
COPY backend/app ./app

# Static frontend (output: "export" produces /app/out)
COPY --from=frontend-build /app/out ./static

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8080/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
