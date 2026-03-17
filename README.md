# Adarkwa Study Bot

`@Adarkwa_Study_Bot` is a Telegram study bot built as a webhook-first FastAPI application with a separate ARQ worker. The current focus is the launch foundation: secure configuration, resilient webhook handling, explicit Neon/Redis/R2 boundaries, and a structure that can absorb the adaptive learning engine next.

## Current Architecture

- `web`: FastAPI app that validates Telegram webhooks, exposes health endpoints, and enqueues jobs
- `worker`: ARQ worker that processes Telegram updates and background tasks
- `Neon`: system-of-record database via async SQLAlchemy
- `Redis`: idempotency, rate limiting, queueing, and transient operational state
- `R2`: storage abstraction for future LaTeX/media assets

Code is organized as a modular monolith under `src/`:

- `src/app`: bootstrap, logging, observability
- `src/core`: typed settings and safety checks
- `src/api`: webhook and health HTTP endpoints
- `src/infra`: database, Redis, and R2 integrations
- `src/domains`: business services
- `src/bot`: Telegram application wiring
- `src/workers`: background job handlers

## Telegram UX Slice

The current bot UX now supports the first home-first student flow:

- `/start` routes new students into study profile setup
- profile setup drills through faculty, program, level, semester, and course
- returning students land on a study home screen
- home actions include `Start Quiz`, `Change Course`, `Performance`, `Help`, and `Continue Quiz` placeholders
- quiz entry currently asks for question count and keeps the final quiz launch as a placeholder until the session wiring is connected

The active catalog is modeled as **first semester** for the UX flow, while the detailed course offering map remains a temporary placeholder until the first-semester seed dataset is finalized.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and fill in the required values.

Required foundation variables:

- `TELEGRAM_BOT_TOKEN`
- `DATABASE_URL`
- `REDIS_URL`
- `WEBHOOK_SECRET`

Optional foundation variables:

- `WEBHOOK_URL`
- `SENTRY_DSN`
- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`
- `R2_PUBLIC_BASE_URL`

## Running Locally

Start the web process:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Start the worker in a second terminal:

```bash
arq src.tasks.worker.WorkerSettings
```

Run the test suite:

```bash
python -m pytest tests -q
```

Run the migration against the configured database:

```bash
alembic upgrade head
```

## Health Endpoints

- `GET /health`
- `GET /health/live`
- `GET /health/ready`

`/health/ready` checks the Redis and database dependencies used by the web process.

## Migrations

Alembic scaffolding is included for the launch-foundation schema:

```bash
alembic upgrade head
```

## Notes

- The adaptive learning engine is intentionally not implemented yet in this foundation phase.
- Kubernetes manifests now include separate web, worker, and migration job roles under `k8s/`.
- Telegram UX design docs live in `docs/plans/2026-03-17-telegram-ux-flow-design.md` and `docs/plans/2026-03-17-telegram-ux-flow.md`.
