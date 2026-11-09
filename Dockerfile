ARG PYTHON_VERSION=3.14-slim

FROM python:${PYTHON_VERSION} AS runtime

LABEL org.opencontainers.image.title="AI Infrastructure Copilot"
LABEL org.opencontainers.image.description="Linux infrastructure monitoring and AI diagnostics"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    INITIALIZE_DATABASE=true \
    DATABASE_INIT_MAX_ATTEMPTS=30 \
    DATABASE_INIT_RETRY_SECONDS=2

WORKDIR /app

RUN groupadd \
        --system \
        --gid 10001 \
        app \
    && useradd \
        --system \
        --uid 10001 \
        --gid app \
        --home-dir /app \
        --shell /usr/sbin/nologin \
        app

COPY requirements.txt ./requirements.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install \
        --requirement requirements.txt

COPY --chown=app:app app ./app
COPY --chown=app:app knowledge ./knowledge
COPY --chown=app:app copilot_v0.py ./copilot_v0.py
COPY docker/entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh \
    && mkdir -p /app/data/qdrant \
    && chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=15s \
    --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

ENTRYPOINT ["docker-entrypoint.sh"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
