# ── Stage 1: builder ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv (fast package manager)
RUN pip install --no-cache-dir uv

# Copy dependency spec first for layer caching
COPY pyproject.toml ./

# Install production deps into /opt/venv
RUN uv venv /opt/venv && \
    uv pip compile pyproject.toml -o requirements.txt && \
    uv pip install --python /opt/venv/bin/python -r requirements.txt

# ── Stage 2: runtime ─────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="IE221-BikeStore Team"
LABEL description="BikeStore B2B Sales Platform"

# Security: run as non-root
RUN groupadd --gid 1001 bikestore && \
    useradd --uid 1001 --gid bikestore --shell /bin/bash --no-create-home bikestore

WORKDIR /app

# Copy only the venv from builder (keeps image small)
COPY --from=builder /opt/venv /opt/venv

# Copy source code
COPY . .

# Ensure scripts are executable
RUN chmod +x /app/scripts/entrypoint.sh 2>/dev/null || true

# Collect static files (non-interactive)
ENV DJANGO_SETTINGS_MODULE=config.settings.prod \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Switch to non-root user
USER bikestore

EXPOSE 8000

# Health check for docker-compose
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')"

CMD ["gunicorn", "config.asgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "120", \
     "--access-logfile", "-"]
