# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Local sentence-transformers embeddings pull in PyTorch (large). Build with
#   --build-arg WITH_EMBEDDINGS=false
# for a much smaller image; RAG then uses the built-in hashing fallback (lower quality).
ARG WITH_EMBEDDINGS=true

COPY requirements.txt .
RUN if [ "$WITH_EMBEDDINGS" = "true" ]; then \
        pip install torch --index-url https://download.pytorch.org/whl/cpu && \
        pip install -r requirements.txt; \
    else \
        grep -vi '^sentence-transformers' requirements.txt > /tmp/requirements.txt && \
        pip install -r /tmp/requirements.txt; \
    fi

COPY . .

# Normalise the entrypoint: zips/git on Windows can drop the exec bit or add CRLF line endings.
RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/uploads/resumes \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Readiness (checks the database), not just "process is up".
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os,sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/health/ready' % os.environ.get('PORT','8000'), timeout=4).status == 200 else 1)"

ENTRYPOINT ["sh", "./docker-entrypoint.sh"]
