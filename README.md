# AI Career Agent

Human-in-the-loop job application assistant: FastAPI + SQLAlchemy + Alembic + PostgreSQL.

- Backend: `backend/` (phases 1–10 complete; frontend next)
- Run: `cp .env.example .env && docker compose up --build` → http://localhost:8000/docs
- Tests: `cd backend && pytest -q` (SQLite) or `TEST_DATABASE_URL=postgresql+psycopg://... pytest -q`
- Docs: `docs/DEPLOYMENT.md`, `docs/PHASES_8_10.md`
