#!/bin/sh
# Apply migrations (unless disabled), then serve.
# With several replicas, set RUN_MIGRATIONS=0 on them and run `alembic upgrade head` once as a release step.
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    echo "Running database migrations..."
    alembic upgrade head
fi

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-1}" \
    --proxy-headers \
    --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
