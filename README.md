# Adarkwa Study Bot

`@Adarkwa_Study_Bot` is a Telegram study bot built as a webhook-first FastAPI application with a separate ARQ worker. The current focus is the launch foundation: secure configuration, resilient webhook handling, explicit Neon/Redis/R2 boundaries, and a structure that can absorb the adaptive learning engine next.

## Current Architecture

- `web`: FastAPI app that validates Telegram webhooks, dispatches lightweight Telegram updates inline for fast feedback, and enqueues heavyweight jobs
- `worker`: ARQ worker that handles durable/background jobs such as analytics and quiz persistence
- `Neon`: system-of-record database via async SQLAlchemy
- `Redis`: idempotency, hot profile/session cache, queueing, and transient operational state
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
- quiz entry asks for question count and starts a Telegram poll-backed quiz session
- quiz sessions now use Telegram polls with Redis-backed session and poll state so active quizzes can continue across pods

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
- `ARQ_QUEUE_NAME`
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

## Production Deployment

The repo now includes a GitHub-driven deployment path for a VPS-hosted Kubernetes cluster:

- `.github/workflows/ci.yml` runs tests on push and pull request
- `.github/workflows/deploy.yml` builds a Docker image, pushes it to GHCR, applies Kubernetes config, runs migrations, and rolls out web + worker on pushes to `main` or `master`
- `k8s/namespace.yaml` creates the `adarkwa-study-bot` namespace
- `k8s/config.yaml` contains non-secret runtime config
- GitHub Actions generates the Kubernetes secret from GitHub Secrets during deployment

For the full production checklist, see [docs/deployment_setup.md](C:/Users/Kevin/Projects/Telegram_Bots/Quizzers/Adarkwa_Study_Bot/docs/deployment_setup.md).

### GitHub Secrets

Add these repository secrets before enabling auto-deploy:

Required:

- `KUBE_CONFIG_B64`
- `TELEGRAM_BOT_TOKEN`
- `DATABASE_URL`
- `REDIS_URL`
- `WEBHOOK_URL`
- `WEBHOOK_SECRET`

Optional:

- `SENTRY_DSN`
- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`
- `R2_PUBLIC_BASE_URL`
- `GHCR_PULL_USERNAME`
- `GHCR_PULL_TOKEN`

`GHCR_PULL_USERNAME` and `GHCR_PULL_TOKEN` are only needed if the GHCR package stays private. If you make the package public, the cluster can pull the image without an image pull secret.

### Kubeconfig Secret

`KUBE_CONFIG_B64` should contain the base64-encoded kubeconfig for the target cluster.

Linux/macOS:

```bash
base64 -w 0 ~/.kube/config
```

PowerShell:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("$HOME\.kube\config"))
```

### First-Time Cluster Bootstrap

1. Create or confirm the VPS-hosted Kubernetes cluster is reachable from your local machine.
2. Make sure the cluster has a metrics server if you want the included HPAs to scale correctly.
3. Add all required GitHub Secrets to the repository.
4. Push to `main` or `master`, or trigger the `Deploy` workflow manually from GitHub Actions.
5. Confirm the `adarkwa-study-bot` namespace, web deployment, worker deployment, and migration job were created successfully.

### Image Registry

The deployment workflow publishes images to GitHub Container Registry using:

```text
ghcr.io/<github-owner>/adarkwa-study-bot:<git-sha>
ghcr.io/<github-owner>/adarkwa-study-bot:latest
```

The Kubernetes deployment always rolls to the immutable SHA-tagged image built by the deploy workflow.

### Cloudflare Tunnel Recommendation

For Telegram webhooks, use a named Cloudflare Tunnel and your own domain rather than a free quick tunnel.

Recommended production routing:

- public hostname at Cloudflare
- named Cloudflare Tunnel
- tunnel target pointing to your Kubernetes ingress or an in-cluster service bridge for `adarkwa-bot-service`

This gives you a stable HTTPS webhook URL for Telegram and a more production-like latency path than local quick tunnels.
