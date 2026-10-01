# The API half — Cloud Run, or the `api` service in docker-compose.yml.
#
# One image, one process: uvicorn serving main:app from /app/api. main.py uses
# flat imports (`import auth`, `from config import ...`), so uvicorn must run
# with api/ as the working directory, exactly as run.sh does — `api.main:app`
# from /app fails at import time.
#
# The client's data files ship inside the image (data/source, including the
# three 29th-Sept xlsx workbooks storyline.py reads) so a revision is a
# complete, reproducible statement of "this code over this data". Everything
# environment-dependent is read from the environment by api/config.py:
# NTT_GEMINI_KEYS, NTT_OPENROUTER_KEY, GROQ_API_KEY, NTT_ANTHROPIC_KEY,
# NTT_ALLOWED_ORIGINS, NTT_AS_OF, NTT_DEMO_ACCOUNTS_FILE. None of it is baked in.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY api ./api
COPY data/source ./data/source
# The refined closure-action cache; closure_actions.py rewrites it at runtime.
COPY data/generated ./data/generated
ENV NTT_DATA_DIR=/app/data/source

# Run unprivileged; only data/generated needs to be writable.
RUN useradd --system --uid 10001 --no-create-home ntt \
    && chown -R ntt /app/data/generated
USER ntt

WORKDIR /app/api

# Cloud Run injects PORT; 8080 is its default. On Azure App Service set
# WEBSITES_PORT=8080 so the platform routes to it.
ENV PORT=8080
EXPOSE 8080

# The first request trains the closure model, so give it a generous start period.
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8080\")}/healthz', timeout=4)" || exit 1

# Behind App Service / Cloud Run / nginx TLS terminates upstream; trust the
# X-Forwarded-* headers so the scheme and client IP are reported correctly.
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1 \
    --proxy-headers --forwarded-allow-ips "*"
