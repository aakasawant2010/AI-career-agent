# Deployment guide

## 1. Run it locally with Docker

```bash
cp .env.example .env          # set JWT_SECRET and POSTGRES_PASSWORD at minimum
docker compose up --build
curl localhost:8000/health/ready   # {"status":"ready","database":"ok"}
```

- API docs: http://localhost:8000/docs
- Migrations run automatically on container start (`RUN_MIGRATIONS=1`).
- First build downloads CPU PyTorch for local embeddings (~1 GB). For a small image set
  `WITH_EMBEDDINGS=false` in `.env`; RAG then uses the built-in hashing fallback (lower retrieval quality).

Without Docker: `cd backend && pip install -r requirements.txt && alembic upgrade head && uvicorn app.main:app --reload`
(SQLite by default, so no database setup is needed for development).

## 2. Going to production

Set `ENVIRONMENT=production`. The app then **refuses to start** unless:

| Requirement | Why |
|---|---|
| `JWT_SECRET` is 32+ characters and not the default | tokens can be forged otherwise |
| `DATABASE_URL` points at PostgreSQL | SQLite isn't safe for concurrent writers |
| `DEBUG=false` | no debug output |
| `CORS_ORIGINS` lists explicit origins (no `*`) | |

Recommended on top of that:

- `ALLOWED_HOSTS=api.yourdomain.com` (Host-header allow-list).
- `DOCS_ENABLED=false` if you don't want public API docs.
- Terminate TLS at a reverse proxy / load balancer (Caddy, nginx, a cloud LB) and set
  `FORWARDED_ALLOW_IPS` to its address so rate limits see real client IPs.
- Use a managed Postgres (or keep the compose volume backed up: `pg_dump`).
- Inject secrets from your platform's secret store, not from a committed `.env`.

### Probes

| Endpoint | Use | Behaviour |
|---|---|---|
| `GET /health` | liveness | always 200 while the process runs |
| `GET /health/ready` | readiness / container HEALTHCHECK | 200 if the DB answers, else 503 |
| `GET /version` | deploy verification | name, version, environment |

### Scaling notes (read before running more than one process)

- **Rate limits are in memory.** With `WEB_CONCURRENCY>1` or several replicas each process counts separately.
  Move `app/core/rate_limit.py` to Redis (`REDIS_URL` is already in the settings) before relying on it for abuse protection.
- **Migrations:** with several replicas set `RUN_MIGRATIONS=0` on them and run `alembic upgrade head` once as a release step.
- **Uploads** live on the `uploads` volume. On a multi-host setup use shared/object storage.

### Releasing

1. CI (`.github/workflows/ci.yml`) runs the tests on SQLite *and* PostgreSQL, checks that the migrations match the models,
   round-trips `upgrade → downgrade base → upgrade`, and smoke-tests the container.
2. Tag, build the image, run migrations, roll out, then watch `/health/ready`.
3. Rollback: redeploy the previous image; `alembic downgrade -1` only if the new migration must be undone
   (Phase 8/9 migrations are additive, so rolling back the app alone is normally safe).

### Observability

Logs are JSON on stdout, one line per request with `request_id`, `method`, `path`, `status`, `ms`, `client`.
Send `X-Request-ID` from your proxy to correlate; the API echoes it on every response, including 429 and 500 errors.
Unhandled errors return `{"detail": "Internal server error", "request_id": "..."}`; the stack trace is only in the logs.

## 3. Configuration reference

See `.env.example` for every variable with comments.
