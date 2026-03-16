# Launch Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor `@Adarkwa_Study_Bot` into a launch-safe modular monolith with hardened configuration, secure webhook processing, explicit Neon/Redis/R2 infrastructure boundaries, and launch-critical test coverage.

**Architecture:** Keep one codebase and one container image, but separate concerns into `core`, `infra`, `api`, `bot`, `workers`, and `domains`. The FastAPI web process handles validation and enqueueing; the ARQ worker handles update processing and background work. Shared bootstrap initializes configuration, observability, and infrastructure clients in one place.

**Tech Stack:** Python, FastAPI, python-telegram-bot, ARQ, Redis, SQLAlchemy async, Neon Postgres, Cloudflare R2, pydantic-settings, pytest

---

### Task 1: Create The New Package Layout And Compatibility Shims

**Files:**
- Create: `Adarkwa_Study_Bot/src/app/__init__.py`
- Create: `Adarkwa_Study_Bot/src/core/__init__.py`
- Create: `Adarkwa_Study_Bot/src/infra/__init__.py`
- Create: `Adarkwa_Study_Bot/src/api/__init__.py`
- Create: `Adarkwa_Study_Bot/src/bot/__init__.py`
- Create: `Adarkwa_Study_Bot/src/workers/__init__.py`
- Modify: `Adarkwa_Study_Bot/src/main.py`
- Modify: `Adarkwa_Study_Bot/src/bot.py`
- Modify: `Adarkwa_Study_Bot/src/database.py`
- Modify: `Adarkwa_Study_Bot/src/cache.py`

**Step 1: Write the failing tests**

Add a smoke test file such as `Adarkwa_Study_Bot/tests/test_imports.py` that imports the new modules and asserts the app object is still importable:

```python
def test_app_import():
    from src.main import app
    assert app is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest Adarkwa_Study_Bot/tests/test_imports.py -v`

Expected: FAIL because the new packages do not exist yet.

**Step 3: Write minimal implementation**

- Create empty package initializers.
- Move no behavior yet.
- Keep current top-level modules working as compatibility shims that delegate into the new layout.

**Step 4: Run test to verify it passes**

Run: `pytest Adarkwa_Study_Bot/tests/test_imports.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add Adarkwa_Study_Bot/src Adarkwa_Study_Bot/tests/test_imports.py
git commit -m "refactor: create modular package layout"
```

### Task 2: Replace Ad Hoc Env Loading With Typed Settings

**Files:**
- Create: `Adarkwa_Study_Bot/src/core/config.py`
- Create: `Adarkwa_Study_Bot/src/core/security.py`
- Modify: `Adarkwa_Study_Bot/src/config.py`
- Modify: `Adarkwa_Study_Bot/tests/conftest.py`
- Create: `Adarkwa_Study_Bot/tests/test_config.py`
- Modify: `Adarkwa_Study_Bot/requirements.txt`
- Modify: `Adarkwa_Study_Bot/.env.example`

**Step 1: Write the failing tests**

Add tests for strict config validation:

```python
import pytest

from src.core.config import Settings


def test_production_requires_non_default_webhook_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:token")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@host/db?sslmode=require")
    monkeypatch.setenv("WEBHOOK_SECRET", "super-secret-default-token")

    with pytest.raises(ValueError):
        Settings()
```

**Step 2: Run test to verify it fails**

Run: `pytest Adarkwa_Study_Bot/tests/test_config.py -v`

Expected: FAIL because `Settings` does not exist or does not validate correctly.

**Step 3: Write minimal implementation**

- Introduce a typed `Settings` object using `pydantic-settings`.
- Validate:
  - required Telegram token
  - required async Postgres URL
  - required non-default webhook secret outside local/test
  - HTTPS webhook URL outside local development
- Keep `src/config.py` as a compatibility import layer for existing code.

**Step 4: Run test to verify it passes**

Run: `pytest Adarkwa_Study_Bot/tests/test_config.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add Adarkwa_Study_Bot/src/core/config.py Adarkwa_Study_Bot/src/core/security.py Adarkwa_Study_Bot/src/config.py Adarkwa_Study_Bot/tests/test_config.py Adarkwa_Study_Bot/tests/conftest.py Adarkwa_Study_Bot/requirements.txt Adarkwa_Study_Bot/.env.example
git commit -m "feat: add typed settings and config validation"
```

### Task 3: Add Shared Bootstrap, Logging, And Observability

**Files:**
- Create: `Adarkwa_Study_Bot/src/app/bootstrap.py`
- Create: `Adarkwa_Study_Bot/src/app/logging.py`
- Create: `Adarkwa_Study_Bot/src/app/observability.py`
- Modify: `Adarkwa_Study_Bot/src/main.py`
- Modify: `Adarkwa_Study_Bot/src/tasks/worker.py`
- Create: `Adarkwa_Study_Bot/tests/test_bootstrap.py`

**Step 1: Write the failing tests**

Add a lifecycle test:

```python
import pytest


@pytest.mark.asyncio
async def test_bootstrap_initializes_shared_services():
    from src.app.bootstrap import create_app_state

    state = await create_app_state()
    assert state.settings is not None
    assert state.redis is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest Adarkwa_Study_Bot/tests/test_bootstrap.py -v`

Expected: FAIL because shared bootstrap does not exist.

**Step 3: Write minimal implementation**

- Create a central bootstrap module returning initialized shared services.
- Move Sentry setup and logging setup out of module import side effects.
- Ensure web and worker use the same bootstrap primitives.

**Step 4: Run test to verify it passes**

Run: `pytest Adarkwa_Study_Bot/tests/test_bootstrap.py -v`

Expected: PASS with mocks or test doubles for external clients.

**Step 5: Commit**

```bash
git add Adarkwa_Study_Bot/src/app Adarkwa_Study_Bot/src/main.py Adarkwa_Study_Bot/src/tasks/worker.py Adarkwa_Study_Bot/tests/test_bootstrap.py
git commit -m "refactor: centralize bootstrap and observability"
```

### Task 4: Build Redis Infrastructure For Idempotency And Rate Limiting

**Files:**
- Create: `Adarkwa_Study_Bot/src/infra/redis/client.py`
- Create: `Adarkwa_Study_Bot/src/infra/redis/keys.py`
- Create: `Adarkwa_Study_Bot/src/infra/redis/idempotency.py`
- Create: `Adarkwa_Study_Bot/src/infra/redis/rate_limit.py`
- Modify: `Adarkwa_Study_Bot/src/cache.py`
- Create: `Adarkwa_Study_Bot/tests/test_redis_idempotency.py`

**Step 1: Write the failing tests**

```python
import pytest


@pytest.mark.asyncio
async def test_duplicate_update_is_rejected_by_idempotency_store(fake_redis):
    from src.infra.redis.idempotency import TelegramUpdateIdempotencyStore

    store = TelegramUpdateIdempotencyStore(fake_redis, ttl_seconds=300)
    assert await store.claim_update(1001) is True
    assert await store.claim_update(1001) is False
```

**Step 2: Run test to verify it fails**

Run: `pytest Adarkwa_Study_Bot/tests/test_redis_idempotency.py -v`

Expected: FAIL because the store does not exist.

**Step 3: Write minimal implementation**

- Add a dedicated Redis client factory.
- Centralize Redis key construction.
- Implement `claim_update()` using `SET NX EX`.
- Add a reusable rate limiter abstraction for later bot actions.

**Step 4: Run test to verify it passes**

Run: `pytest Adarkwa_Study_Bot/tests/test_redis_idempotency.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add Adarkwa_Study_Bot/src/infra/redis Adarkwa_Study_Bot/src/cache.py Adarkwa_Study_Bot/tests/test_redis_idempotency.py
git commit -m "feat: add redis idempotency and rate limiting primitives"
```

### Task 5: Harden The Webhook API And Health Endpoints

**Files:**
- Create: `Adarkwa_Study_Bot/src/api/webhooks.py`
- Create: `Adarkwa_Study_Bot/src/api/health.py`
- Modify: `Adarkwa_Study_Bot/src/main.py`
- Modify: `Adarkwa_Study_Bot/src/tasks/arq_client.py`
- Modify: `Adarkwa_Study_Bot/tests/test_webhook.py`

**Step 1: Write the failing tests**

Extend webhook tests:

```python
@pytest.mark.asyncio
async def test_duplicate_webhook_returns_200_without_enqueue(async_client, monkeypatch):
    ...


@pytest.mark.asyncio
async def test_ready_endpoint_returns_503_when_dependency_down(async_client, monkeypatch):
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest Adarkwa_Study_Bot/tests/test_webhook.py -v`

Expected: FAIL because duplicate suppression and readiness are not implemented.

**Step 3: Write minimal implementation**

- Move routes into `src/api`.
- Enforce webhook secret using validated settings.
- Deduplicate updates before enqueueing.
- Add `/health/live` and `/health/ready`.
- Return sanitized error responses and structured logs with correlation IDs.

**Step 4: Run test to verify it passes**

Run: `pytest Adarkwa_Study_Bot/tests/test_webhook.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add Adarkwa_Study_Bot/src/api Adarkwa_Study_Bot/src/main.py Adarkwa_Study_Bot/src/tasks/arq_client.py Adarkwa_Study_Bot/tests/test_webhook.py
git commit -m "feat: harden webhook flow and health endpoints"
```

### Task 6: Introduce Database Base, Models, Repositories, And Migrations

**Files:**
- Create: `Adarkwa_Study_Bot/src/infra/db/base.py`
- Create: `Adarkwa_Study_Bot/src/infra/db/session.py`
- Create: `Adarkwa_Study_Bot/src/infra/db/models/__init__.py`
- Create: `Adarkwa_Study_Bot/src/infra/db/models/user.py`
- Create: `Adarkwa_Study_Bot/src/infra/db/models/telegram_identity.py`
- Create: `Adarkwa_Study_Bot/src/infra/db/models/analytics_event.py`
- Create: `Adarkwa_Study_Bot/src/infra/db/models/webhook_event.py`
- Create: `Adarkwa_Study_Bot/src/infra/db/repositories/__init__.py`
- Create: `Adarkwa_Study_Bot/src/infra/db/repositories/analytics_repository.py`
- Modify: `Adarkwa_Study_Bot/src/database.py`
- Create: `Adarkwa_Study_Bot/tests/test_database_models.py`

**Step 1: Write the failing tests**

```python
def test_analytics_event_model_has_expected_columns():
    from src.infra.db.models.analytics_event import AnalyticsEvent

    columns = {column.name for column in AnalyticsEvent.__table__.columns}
    assert {"id", "event_type", "user_id", "metadata", "created_at"} <= columns
```

**Step 2: Run test to verify it fails**

Run: `pytest Adarkwa_Study_Bot/tests/test_database_models.py -v`

Expected: FAIL because the models do not exist.

**Step 3: Write minimal implementation**

- Introduce shared declarative base and session factory.
- Add minimal phase-1 models.
- Add repository interfaces for analytics and operational event persistence.
- If Alembic is not present, add it now and create the initial migration scaffold.

**Step 4: Run test to verify it passes**

Run: `pytest Adarkwa_Study_Bot/tests/test_database_models.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add Adarkwa_Study_Bot/src/infra/db Adarkwa_Study_Bot/src/database.py Adarkwa_Study_Bot/tests/test_database_models.py
git commit -m "feat: add database models and repositories"
```

### Task 7: Move Analytics Behind A Real Domain Service

**Files:**
- Create: `Adarkwa_Study_Bot/src/domains/analytics/service.py`
- Modify: `Adarkwa_Study_Bot/src/analytics/internal_analytics.py`
- Modify: `Adarkwa_Study_Bot/src/bot.py`
- Create: `Adarkwa_Study_Bot/tests/test_analytics_service.py`

**Step 1: Write the failing tests**

```python
import pytest


@pytest.mark.asyncio
async def test_track_event_persists_via_repository():
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest Adarkwa_Study_Bot/tests/test_analytics_service.py -v`

Expected: FAIL because the service/repository wiring does not exist.

**Step 3: Write minimal implementation**

- Replace stub-only logging with a domain service that delegates persistence through a repository.
- Keep logging as a side effect, but persistence becomes the primary path.
- Update bot handlers to depend on the domain service abstraction.

**Step 4: Run test to verify it passes**

Run: `pytest Adarkwa_Study_Bot/tests/test_analytics_service.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add Adarkwa_Study_Bot/src/domains/analytics/service.py Adarkwa_Study_Bot/src/analytics/internal_analytics.py Adarkwa_Study_Bot/src/bot.py Adarkwa_Study_Bot/tests/test_analytics_service.py
git commit -m "feat: add analytics domain service"
```

### Task 8: Add R2 Storage Abstraction And Worker Hardening

**Files:**
- Create: `Adarkwa_Study_Bot/src/infra/r2/client.py`
- Create: `Adarkwa_Study_Bot/src/infra/r2/storage.py`
- Create: `Adarkwa_Study_Bot/src/workers/telegram_update.py`
- Modify: `Adarkwa_Study_Bot/src/tasks/worker.py`
- Modify: `Adarkwa_Study_Bot/tests/test_worker.py`
- Create: `Adarkwa_Study_Bot/tests/test_r2_storage.py`

**Step 1: Write the failing tests**

```python
def test_latex_object_key_generation():
    from src.infra.r2.storage import build_latex_object_key

    key = build_latex_object_key("math101", "q42", "abc123")
    assert key == "latex/math101/q42/abc123.png"
```

**Step 2: Run test to verify it fails**

Run: `pytest Adarkwa_Study_Bot/tests/test_worker.py Adarkwa_Study_Bot/tests/test_r2_storage.py -v`

Expected: FAIL because the storage abstraction and hardened worker module do not exist.

**Step 3: Write minimal implementation**

- Add an R2 client wrapper and storage validation helpers.
- Move Telegram update job logic into `src/workers/telegram_update.py`.
- Define explicit timeout, retry, and failure logging behavior in the worker settings.

**Step 4: Run test to verify it passes**

Run: `pytest Adarkwa_Study_Bot/tests/test_worker.py Adarkwa_Study_Bot/tests/test_r2_storage.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add Adarkwa_Study_Bot/src/infra/r2 Adarkwa_Study_Bot/src/workers/telegram_update.py Adarkwa_Study_Bot/src/tasks/worker.py Adarkwa_Study_Bot/tests/test_worker.py Adarkwa_Study_Bot/tests/test_r2_storage.py
git commit -m "feat: add r2 abstraction and harden worker jobs"
```

### Task 9: Update Runtime, Docker, And Launch Docs

**Files:**
- Modify: `Adarkwa_Study_Bot/Dockerfile`
- Modify: `Adarkwa_Study_Bot/README.md`
- Modify: `Adarkwa_Study_Bot/docs/architecture_plan.md`
- Modify: `Adarkwa_Study_Bot/.dockerignore`

**Step 1: Write the failing tests**

Add or extend a documentation/runtime smoke test only if the repo already uses one. Otherwise skip a code test here and verify manually.

**Step 2: Run test to verify it fails**

Run: `pytest -q`

Expected: No new test required for documentation-only changes.

**Step 3: Write minimal implementation**

- Update Docker defaults for safer runtime behavior.
- Document `web` and `worker` process roles.
- Update setup instructions to reflect typed settings and new health endpoints.
- Remove stale architecture claims such as PostHog if no longer applicable.

**Step 4: Run test to verify it passes**

Run: `pytest -q`

Expected: Existing suite remains green.

**Step 5: Commit**

```bash
git add Adarkwa_Study_Bot/Dockerfile Adarkwa_Study_Bot/README.md Adarkwa_Study_Bot/docs/architecture_plan.md Adarkwa_Study_Bot/.dockerignore
git commit -m "docs: update launch foundation runtime documentation"
```

### Task 10: Run Final Verification

**Files:**
- Modify as needed: any files touched by the tasks above

**Step 1: Run focused tests**

Run:

```bash
pytest Adarkwa_Study_Bot/tests/test_imports.py Adarkwa_Study_Bot/tests/test_config.py Adarkwa_Study_Bot/tests/test_bootstrap.py Adarkwa_Study_Bot/tests/test_redis_idempotency.py Adarkwa_Study_Bot/tests/test_webhook.py Adarkwa_Study_Bot/tests/test_database_models.py Adarkwa_Study_Bot/tests/test_analytics_service.py Adarkwa_Study_Bot/tests/test_worker.py Adarkwa_Study_Bot/tests/test_r2_storage.py -v
```

Expected: PASS.

**Step 2: Run the full suite**

Run: `pytest Adarkwa_Study_Bot/tests -v`

Expected: PASS.

**Step 3: Manual verification**

Run:

```bash
uvicorn src.main:app --reload
```

Verify:

- `GET /health/live` returns 200
- `GET /health/ready` reflects dependency state
- `POST /webhook` rejects invalid secret tokens
- duplicate authorized webhook payloads do not enqueue twice

**Step 4: Commit**

```bash
git add Adarkwa_Study_Bot
git commit -m "chore: verify launch foundation baseline"
```

## Notes

- This workspace did not expose a Git repository during planning, so the commit steps may need to be skipped or adapted if version control is initialized elsewhere.
- Do not start phase 2 adaptive learning implementation until this plan is complete and stable.
