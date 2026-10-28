# Phases 8–10: tracking, interview agent, production readiness

## Phase 8 – Tracking & analytics

**Pipeline.** `DRAFT → PREPARED → PENDING_APPROVAL → APPROVED → SUBMITTED` (unchanged, human approval still required) then,
tracked by *you* after you apply: `SUBMITTED → SCREENING → INTERVIEW → OFFER → ACCEPTED`. `REJECTED` and `WITHDRAWN` are
reachable from any active stage; `ACCEPTED`, `REJECTED`, `WITHDRAWN` are final. Screening can be skipped.
Nothing in this phase talks to an employer; the agent never submits or advances anything on its own after approval.

Use the existing `POST /applications/{id}/status {"status": "...", "note": "..."}`. Every change is recorded in
`application_events` (`GET /applications/{id}/events`) and the audit log.

**Follow-ups.** Submitting an application creates a reminder `DEFAULT_FOLLOW_UP_DAYS` (7) later. Reaching a final state cancels open reminders.

| Endpoint | |
|---|---|
| `GET /follow-ups?status=&due_within_days=` | reminder inbox, soonest first, each flagged `overdue` |
| `GET /applications/{id}/follow-ups` | reminders for one application |
| `POST /applications/{id}/follow-ups` | add one (existing) |
| `PATCH /follow-ups/{id}` | `{"status":"DONE"\|"CANCELLED", "due_at":..., "note":...}` |

**Analytics** (all derived from event history, so an application that reached INTERVIEW and was later rejected still counts as an interview):

| Endpoint | Returns |
|---|---|
| `GET /analytics/overview` | one-call dashboard: totals, funnel, response stats, follow-ups, needs-attention |
| `GET /analytics/funnel` | stage counts + conversion from previous stage and from submitted |
| `GET /analytics/response` | response rate, positive response rate, average/median days to response, awaiting, ghosted (no reply after `GHOSTED_AFTER_DAYS`) |
| `GET /analytics/breakdown?by=source\|company\|role\|work_mode\|match_band` | per-group applications, responses, interviews, offers and rates |
| `GET /analytics/timeline?weeks=12` | weekly created / submitted / responses |

A *response* means the employer moved the application to SCREENING, INTERVIEW, OFFER, ACCEPTED or REJECTED after submission.
Withdrawing, or rejecting a draft that was never submitted, is not a response.

## Phase 9 – Interview agent

Practice interviews for a job (or an application's job). Advisory only: it changes no application status.

| Endpoint | |
|---|---|
| `POST /interviews/sessions` | `{job_id \| application_id, mode: technical\|behavioral\|mixed, difficulty: easy\|medium\|hard, num_questions: 3-15}` |
| `GET /interviews/sessions[?application_id=&job_id=&status=]` | history |
| `GET /interviews/sessions/{id}` | session with questions (rubric hidden until answered) |
| `POST /interviews/sessions/{id}/questions/{qid}/answer` | `{"answer": "..."}` → score 0-100, strengths, improvements, covered/missed points. Can be revised until the session is completed |
| `POST /interviews/sessions/{id}/complete` | freezes the session and builds the report |
| `GET /interviews/sessions/{id}/report` | overall score, readiness, by category/skill, weak/strong skills, improvement themes, next steps |

**How questions are made.** From the job's skills, your candidate intelligence (strengths, gaps from the latest job match, your real
projects), a per-skill question bank, a STAR behavioural bank and a system-design question that fits the role. A new session for the same job avoids questions
you've already seen. With `GROQ_API_KEY` (or `OPENAI_API_KEY`) set, the LLM proposes tailored questions first
and the bank fills any remainder; invalid LLM output is discarded.

**How answers are scored.** Rule-based and explainable: 60% coverage of the rubric points, 20% depth, 10% specificity
(numbers, a concrete example), 10% reasoning. If an LLM is configured, its score is averaged with the rule score and its comments are merged in.
With no key everything still works. Set `INTERVIEW_USE_LLM=false` to force rule-based.
Treat scores as practice feedback, not a prediction of interview outcomes.

## Phase 10 – Production readiness

- `/health` (liveness), `/health/ready` (database check, 503 when down), `/version`.
- Request pipeline: `X-Request-ID` in/out, security headers, global per-IP rate limit (probes exempt), JSON 500s that never leak stack traces, structured logs.
- Production config guards (see `docs/DEPLOYMENT.md`), `ALLOWED_HOSTS`, `DOCS_ENABLED`.
- Resume upload: client file name is sanitised (it previously went straight into the saved path), 5 MB limit (`MAX_UPLOAD_MB`), parser errors no longer echoed to the client.
- Docker image (non-root, healthcheck, entrypoint that migrates then serves), `docker-compose.yml` (Postgres 16 + API), GitHub Actions CI.

## Fixes to existing code found along the way

- Migrations: `f1f2_phase5_8` created `application_packages.application_id` as a non-unique index and omitted two indexes the models declare → the existing `test_migrations_match_models` was failing. Fixed in `a8b1c2d3e4f5`.
- Running on real PostgreSQL exposed more drift that SQLite hides: `candidate_intelligence` timestamps were created without a time zone, `jobs.posted_at` model/migration disagreed, and two tables had both a UNIQUE constraint and a unique index on the same column. All reconciled in `a8b1c2d3e4f5`.
- `ba74851bf6a6` had an empty `downgrade()`, so `alembic downgrade base` failed on Postgres. It now drops the table.
- `GET /applications/analytics/summary` compared naive and aware datetimes (would crash on SQLite data); `GET /applications/{id}/events` returned raw ORM objects without a response model.
- Existing production-secret test updated: a "valid" production config now also needs a Postgres URL.

## Known limitations

- Rate limiting is per process (see deployment guide).
- `conversion_rate` in the older `/applications/analytics/summary` is `submitted / (submitted + rejected)`, which is not meaningful with the longer pipeline; it's kept for compatibility. Use `/analytics/funnel`.
- The cover letter / answers produced by `prepare` (Phase 7) are still template-based; only the interview agent can use an LLM.
- The Docker image could not be built in the environment this was developed in (no Docker daemon). The Dockerfile, compose file and CI container smoke-test are written but untested; the Python code, migrations and full test suite were verified on SQLite and PostgreSQL 16.
