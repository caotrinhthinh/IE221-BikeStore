FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv (fast package manager)
RUN pip install --no-cache-dir uv

# Copy dependency spec first for layer caching
COPY pyproject.toml ./

RUN uv venv /opt/venv && \
    uv pip compile pyproject.toml -o requirements.txt && \
    uv pip install --python /opt/venv/bin/python -r requirements.txt

FROM python:3.12-slim AS runtime

LABEL maintainer="IE221-BikeStore Team"
LABEL description="BikeStore B2B Sales Platform"

RUN groupadd --gid 1001 bikestore && \
    useradd --uid 1001 --gid bikestore --shell /bin/bash --no-create-home bikestore

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

ENV DJANGO_SETTINGS_MODULE=config.settings.dev \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

USER bikestore

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')"

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
