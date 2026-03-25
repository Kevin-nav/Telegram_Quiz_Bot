# Adaptive Learning Algorithm Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the full adaptive quiz engine end to end with a fast hot path, async adaptive updates, SRS, misconception handling, and scalable caching and persistence boundaries.

**Architecture:** Keep Postgres as the source of truth and use Redis for sessions, locks, idempotency, and hot caches. Put adaptive logic in a dedicated `src/domains/adaptive/` package, keep the Telegram quiz service thin, and split the system into a responsive quiz path plus a background adaptive-update pipeline.

**Tech Stack:** Python, SQLAlchemy async, Postgres, Redis, ARQ workers, pytest, Telegram bot runtime

---

### Task 1: Add adaptive runtime tables

**Files:**
- Create: `src/infra/db/models/student_question_srs.py`
- Create: `src/infra/db/models/adaptive_review_flag.py`
- Modify: `src/infra/db/models/__init__.py`
- Create: `migrations/versions/20260325_000001_add_adaptive_runtime_tables.py`
- Test: `tests/test_database_models.py`

**Step 1: Write the failing test**

```python
def test_adaptive_runtime_models_exist():
    from src.infra.db.models import AdaptiveReviewFlag, StudentQuestionSrs

    assert AdaptiveReviewFlag.__tablename__ == "adaptive_review_flags"
    assert StudentQuestionSrs.__tablename__ == "student_question_srs"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database_models.py -v`
Expected: FAIL because the tables do not exist yet.

**Step 3: Write minimal implementation**

- Add the models and indexes required for normalized SRS state and review flags.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/infra/db/models migrations/versions tests/test_database_models.py
git commit -m "feat: add adaptive runtime tables"
```

### Task 2: Add adaptive repositories

**Files:**
- Create: `src/infra/db/repositories/student_course_state_repository.py`
- Create: `src/infra/db/repositories/student_question_srs_repository.py`
- Create: `src/infra/db/repositories/adaptive_review_repository.py`
- Modify: `src/infra/db/repositories/question_attempt_repository.py`
- Modify: `src/infra/db/repositories/question_bank_repository.py`
- Test: `tests/test_adaptive_repositories.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_student_course_state_get_or_create_returns_defaults():
    assert False, "Implement adaptive repositories"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_adaptive_repositories.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add get-or-create adaptive state.
- Add batched question metadata reads.
- Add batched attempt-history queries.
- Add SRS batch lookup and transition methods.
- Add review-flag persistence helpers.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_adaptive_repositories.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/infra/db/repositories tests/test_adaptive_repositories.py
git commit -m "feat: add adaptive repositories"
```

### Task 3: Build adaptive core helpers

**Files:**
- Create: `src/domains/adaptive/__init__.py`
- Create: `src/domains/adaptive/models.py`
- Create: `src/domains/adaptive/timing.py`
- Create: `src/domains/adaptive/srs.py`
- Create: `src/domains/adaptive/ordering.py`
- Create: `src/domains/adaptive/arrangement.py`
- Test: `tests/test_adaptive_core.py`

**Step 1: Write the failing test**

```python
def test_time_limit_increases_with_processing_complexity():
    assert False, "Implement adaptive core helpers"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_adaptive_core.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add pure helper logic for:
  - time limits
  - time classifications
  - SRS transitions
  - quiz ordering
  - arrangement hashes
  - memorization detection

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_adaptive_core.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/adaptive tests/test_adaptive_core.py
git commit -m "feat: add adaptive core helpers"
```

### Task 4: Implement selection engine

**Files:**
- Create: `src/domains/adaptive/selection.py`
- Test: `tests/test_adaptive_selection.py`

**Step 1: Write the failing test**

```python
def test_new_question_score_prefers_slightly_above_skill():
    assert False, "Implement adaptive selection engine"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_adaptive_selection.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Implement:
  - phase detection
  - cold start
  - weakness/new/SRS/ZPD/coverage/misconception scoring
  - exam modifiers
  - weighted top-3 selection

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_adaptive_selection.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/adaptive/selection.py tests/test_adaptive_selection.py
git commit -m "feat: implement adaptive selection"
```

### Task 5: Implement adaptive updater

**Files:**
- Create: `src/domains/adaptive/updater.py`
- Test: `tests/test_adaptive_updater.py`

**Step 1: Write the failing test**

```python
def test_mastered_attempt_updates_topic_skill_more_than_overall_skill():
    assert False, "Implement adaptive updater"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_adaptive_updater.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Implement:
  - Elo-style updates
  - K modifiers by classification
  - misconception logging and resolution
  - phase updates
  - lazy topic decay helpers

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_adaptive_updater.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/adaptive/updater.py tests/test_adaptive_updater.py
git commit -m "feat: implement adaptive updater"
```

### Task 6: Add adaptive orchestration service

**Files:**
- Create: `src/domains/adaptive/service.py`
- Test: `tests/test_adaptive_service.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_adaptive_service_uses_batched_inputs_for_selection():
    assert False, "Implement adaptive orchestration service"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_adaptive_service.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Orchestrate batched repository reads for selection and updates.
- Keep pure scoring and pure update functions separate from IO.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_adaptive_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/adaptive/service.py tests/test_adaptive_service.py
git commit -m "feat: add adaptive service"
```

### Task 7: Expand quiz runtime model and selection wiring

**Files:**
- Modify: `src/domains/quiz/models.py`
- Modify: `src/domains/quiz/service.py`
- Modify: `src/infra/redis/state_store.py`
- Test: `tests/test_quiz_models.py`
- Test: `tests/test_quiz_session_service.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_start_quiz_uses_adaptive_selector():
    assert False, "Wire adaptive selection into quiz runtime"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_quiz_models.py tests/test_quiz_session_service.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Expand `QuizQuestion` to carry adaptive metadata.
- Replace first-`N` selection with adaptive selection.
- Store presentation timestamps and arrangement/config data in Redis session state.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_quiz_models.py tests/test_quiz_session_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/quiz src/infra/redis tests/test_quiz_models.py tests/test_quiz_session_service.py
git commit -m "feat: wire adaptive quiz runtime"
```

### Task 8: Add background adaptive update pipeline

**Files:**
- Modify: `src/workers/background_jobs.py`
- Modify: `src/tasks/arq_client.py`
- Modify: `src/infra/redis/idempotency.py`
- Modify: `src/infra/redis/keys.py`
- Test: `tests/test_background_jobs.py`
- Test: `tests/test_redis_idempotency.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_duplicate_attempt_event_does_not_double_apply_update():
    assert False, "Implement adaptive background update pipeline"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_background_jobs.py tests/test_redis_idempotency.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Persist attempts canonically.
- Trigger adaptive updates asynchronously.
- Add idempotency and `(user, course)` adaptive update locks.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_background_jobs.py tests/test_redis_idempotency.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/workers src/tasks src/infra/redis tests/test_background_jobs.py tests/test_redis_idempotency.py
git commit -m "feat: add adaptive background pipeline"
```

### Task 9: Add adaptive snapshot caching

**Files:**
- Modify: `src/infra/redis/state_store.py`
- Modify: `src/domains/adaptive/service.py`
- Create: `tests/test_adaptive_cache.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_adaptive_snapshot_cache_invalidates_after_update():
    assert False, "Implement adaptive snapshot caching"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_adaptive_cache.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add short-lived adaptive snapshot cache helpers.
- Refresh or invalidate after successful adaptive updates.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_adaptive_cache.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/infra/redis/state_store.py src/domains/adaptive/service.py tests/test_adaptive_cache.py
git commit -m "feat: cache adaptive snapshots"
```

### Task 10: Add review analytics and rollout controls

**Files:**
- Create: `src/domains/adaptive/review.py`
- Modify: `src/workers/background_jobs.py`
- Modify: `src/tasks/worker.py`
- Modify: `src/config.py`
- Test: `tests/test_background_jobs.py`
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

```python
def test_config_exposes_adaptive_feature_flags():
    assert False, "Implement review analytics and rollout controls"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_background_jobs.py tests/test_config.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add review jobs for:
  - difficulty divergence
  - distractor concentration
  - time allocation review
- Add rollout flags for selector, updater, and review jobs.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_background_jobs.py tests/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/adaptive/review.py src/workers src/tasks/worker.py src/config.py tests/test_background_jobs.py tests/test_config.py
git commit -m "feat: add adaptive review jobs and rollout flags"
```

### Task 11: Add end-to-end and performance guardrail tests

**Files:**
- Create: `tests/test_adaptive_integration.py`
- Create: `tests/test_adaptive_performance.py`
- Create: `docs/adaptive_runtime_architecture.md`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_completed_quiz_changes_future_selection():
    assert False, "Implement adaptive integration coverage"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_adaptive_integration.py tests/test_adaptive_performance.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add integration coverage for quiz completion and future selection changes.
- Add performance guardrails against obvious N+1 regressions.
- Document the final runtime architecture for operators and developers.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_adaptive_integration.py tests/test_adaptive_performance.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_adaptive_integration.py tests/test_adaptive_performance.py docs/adaptive_runtime_architecture.md
git commit -m "test: add adaptive integration and performance guardrails"
```
