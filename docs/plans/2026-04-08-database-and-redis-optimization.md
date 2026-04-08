# Database And Redis Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce Postgres compute and query volume across the admin portal, adaptive quiz selection, and learner analytics by pushing filtering and aggregation into SQL, denormalizing hot metrics, and using Redis only for hot read models and coordination.

**Architecture:** Keep Postgres as the canonical source of truth for questions, attempts, learner state, and admin data. Add denormalized SQL tables and columns for admin-facing summaries, use composite indexes for real access paths, and add Redis caches for the adaptive selector's stable course manifest and per-learner hot snapshot. Avoid turning Redis into a second source of truth or a binary asset store.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Redis, ARQ, PostgreSQL/Neon, pytest, Next.js admin frontend

---

### Task 1: Add Composite Indexes For Hot Query Paths

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\migrations\versions\20260408_000001_add_hot_path_indexes.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\models\question_bank.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\models\question_attempt.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\models\question_report.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\models\program_course_offering.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_db_metadata_registration.py`

**Step 1: Write the failing metadata test**

```python
def test_hot_path_indexes_are_registered():
    from src.infra.db.models.question_attempt import QuestionAttempt
    indexes = {index.name for index in QuestionAttempt.__table__.indexes}
    assert "ix_question_attempts_bot_user_created_desc" in indexes
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_db_metadata_registration.py -v`
Expected: FAIL because the composite index names are not present.

**Step 3: Add the minimal implementation**

```python
Index(
    "ix_question_attempts_bot_user_created_desc",
    QuestionAttempt.bot_id,
    QuestionAttempt.user_id,
    QuestionAttempt.created_at.desc(),
)
```

Add comparable indexes for:
- `question_bank (course_id, status, id)`
- `question_attempts (bot_id, user_id, question_id, created_at desc)`
- `question_reports (bot_id, report_status, created_at desc)`
- `program_course_offerings (program_code, level_code, semester_code, is_active, course_code)`

Then create the matching Alembic migration.

**Step 4: Run tests and migration smoke check**

Run: `venv\Scripts\python.exe -m pytest tests/test_db_metadata_registration.py tests/test_database.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add migrations/versions/20260408_000001_add_hot_path_indexes.py src/infra/db/models/question_bank.py src/infra/db/models/question_attempt.py src/infra/db/models/question_report.py src/infra/db/models/program_course_offering.py tests/test_db_metadata_registration.py
git commit -m "perf: add composite indexes for hot database paths"
```

### Task 2: Move Admin Reports Filtering, Counting, And Pagination Into SQL

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\admin\report_service.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\redis\admin_cache_store.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_admin_api.py`

**Step 1: Write the failing API test**

```python
async def test_reports_endpoint_uses_sql_filtered_count(client, seeded_reports):
    response = await client.get("/admin/reports?status=open&limit=2&offset=0")
    payload = response.json()
    assert payload["count"] == 2
    assert payload["open_count"] >= 2
    assert all(item["status"] == "open" for item in payload["items"])
```

**Step 2: Run test to verify it fails or exposes the wrong shape**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -k reports -v`
Expected: FAIL or show current behavior still counts after loading the full report set.

**Step 3: Write the minimal implementation**

```python
base_stmt = select(QuestionReport)
count_stmt = select(func.count()).select_from(filtered_subquery)
open_count_stmt = select(func.count()).select_from(open_filtered_subquery)
items_stmt = filtered_stmt.order_by(...).limit(limit).offset(offset)
```

Keep Redis caching, but cache the SQL-produced payload instead of Python-postprocessed lists.

**Step 4: Run tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py tests/test_admin_cache_store.py -k "reports or cache" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/admin/report_service.py src/infra/redis/admin_cache_store.py tests/test_admin_api.py
git commit -m "perf: push admin report filtering and paging into sql"
```

### Task 3: Replace Per-Item Admin Question Scope Checks With SQL-Scoped Reads

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\api\admin_questions.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\admin\question_service.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\admin\scope_service.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\repositories\question_bank_repository.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_admin_api.py`

**Step 1: Write the failing scoped-list test**

```python
async def test_question_list_only_returns_allowed_course_rows(client, scoped_principal):
    response = await client.get("/admin/questions")
    payload = response.json()
    assert all(item["course_id"] in {"course-a", "course-b"} for item in payload["items"])
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -k questions -v`
Expected: FAIL because filtering still happens after the list is fetched.

**Step 3: Write the minimal implementation**

```python
questions = await service.list_questions(
    course_codes=course_codes,
    course_id=course_id,
    status=status_filter,
    limit=limit,
    offset=offset,
)
```

Implement repository support for `course_codes` and remove item-by-item permission checks from the listing path.

**Step 4: Run tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py tests/test_admin_permission_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/api/admin_questions.py src/domains/admin/question_service.py src/domains/admin/scope_service.py src/infra/db/repositories/question_bank_repository.py tests/test_admin_api.py
git commit -m "perf: scope admin question queries before loading rows"
```

### Task 4: Add A Dedicated Admin Dashboard Summary Read Model

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\admin\analytics_service.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\api\admin_analytics.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\admin\lib\api.ts`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\admin\app\page.tsx`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_admin_analytics_service.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_admin_api.py`

**Step 1: Write the failing service test**

```python
async def test_dashboard_summary_returns_counts_without_full_question_lists():
    payload = await service.get_dashboard_summary(active_bot_id="adarkwa")
    assert "question_count" in payload
    assert "open_reports_count" in payload
    assert "recent_reports" in payload
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_analytics_service.py tests/test_admin_api.py -k dashboard -v`
Expected: FAIL because no dashboard summary endpoint exists.

**Step 3: Write the minimal implementation**

```python
@router.get("/dashboard")
async def get_dashboard_summary(...):
    return await service.get_dashboard_summary(...)
```

Return:
- KPI block
- staff count
- question count
- review count
- open report count
- recent reports
- top leaderboard slice

Update the frontend dashboard page to call only this endpoint plus the principal query.

**Step 4: Run tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_analytics_service.py tests/test_admin_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/admin/analytics_service.py src/api/admin_analytics.py admin/lib/api.ts admin/app/page.tsx tests/test_admin_analytics_service.py tests/test_admin_api.py
git commit -m "feat: add dashboard summary read model"
```

### Task 5: Add Redis Course Manifest Cache For Adaptive Selection

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\redis\keys.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\redis\state_store.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\adaptive\service.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\repositories\question_bank_repository.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_adaptive_service.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_interactive_state_store.py`

**Step 1: Write the failing selector cache test**

```python
async def test_select_questions_uses_cached_course_manifest_before_db():
    await state_store.set_course_question_manifest("course-1", [{"question_key": "q1"}])
    selection = await service.select_questions(user_id=1, bot_id="adarkwa", course_id="course-1", quiz_length=5)
    assert selection.question_rows
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_adaptive_service.py tests/test_interactive_state_store.py -k manifest -v`
Expected: FAIL because no course manifest cache helpers exist.

**Step 3: Write the minimal implementation**

```python
cached_manifest = await self.state_store.get_course_question_manifest(course_id)
if cached_manifest is None:
    manifest = await self.question_bank_repository.list_ready_question_manifest(course_id)
    await self.state_store.set_course_question_manifest(course_id, manifest)
```

Create a lightweight manifest query that returns only selector fields. Keep full question-row fetch separate for the final selected question IDs.

**Step 4: Run tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_adaptive_service.py tests/test_interactive_state_store.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/infra/redis/keys.py src/infra/redis/state_store.py src/domains/adaptive/service.py src/infra/db/repositories/question_bank_repository.py tests/test_adaptive_service.py tests/test_interactive_state_store.py
git commit -m "feat: cache adaptive course manifests in redis"
```

### Task 6: Add Redis Learner Selector Snapshot Cache

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\redis\keys.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\redis\state_store.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\adaptive\service.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\workers\background_jobs.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_adaptive_cache.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_background_jobs.py`

**Step 1: Write the failing snapshot test**

```python
async def test_selector_snapshot_updates_after_attempt_persist():
    await persist_quiz_attempt(payload, runtime=runtime)
    snapshot = await runtime.state_store.get_selector_snapshot(user_id=1, course_id="course-1")
    assert snapshot["questions"]["q-1"]["attempt_count"] == 1
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_adaptive_cache.py tests/test_background_jobs.py -k snapshot -v`
Expected: FAIL because the snapshot key and update flow do not exist.

**Step 3: Write the minimal implementation**

```python
snapshot = await state_store.get_selector_snapshot(user_id, course_id) or {"questions": {}}
question_state = snapshot["questions"].setdefault(question_key, {"attempt_count": 0, "correct_count": 0})
question_state["attempt_count"] += 1
```

Store:
- attempted question IDs
- last_correct_at
- last_wrong_at
- attempt_count
- correct_count
- current SRS box

Read this snapshot before falling back to `question_attempts` and `student_question_srs`.

**Step 4: Run tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_adaptive_cache.py tests/test_background_jobs.py tests/test_adaptive_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/infra/redis/keys.py src/infra/redis/state_store.py src/domains/adaptive/service.py src/workers/background_jobs.py tests/test_adaptive_cache.py tests/test_background_jobs.py
git commit -m "feat: cache learner selector snapshots in redis"
```

### Task 7: Denormalize Learner Metrics For Admin And Performance Views

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\migrations\versions\20260408_000002_add_denormalized_learner_metrics.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\models\student_course_state.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\models\user.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\repositories\student_course_state_repository.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\adaptive\service.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\workers\background_jobs.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\admin\analytics_service.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\performance\service.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_adaptive_repositories.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_admin_analytics_service.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_performance_service.py`

**Step 1: Write the failing denormalized-metric tests**

```python
async def test_attempt_update_increments_total_correct_and_avg_time():
    state = await repo.get(user_id=1, course_id="course-1", bot_id="adarkwa")
    assert state.total_correct == 1
```

```python
async def test_admin_student_detail_prefers_denormalized_metrics():
    payload = await service.get_student_detail(1, active_bot_id="adarkwa")
    assert payload["courses"][0]["total_correct"] == 3
```

**Step 2: Run tests to verify they fail**

Run: `venv\Scripts\python.exe -m pytest tests/test_adaptive_repositories.py tests/test_admin_analytics_service.py tests/test_performance_service.py -v`
Expected: FAIL because the denormalized columns do not exist.

**Step 3: Write the minimal implementation**

```python
total_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
avg_time_per_question: Mapped[float | None] = mapped_column(Float, nullable=True)
```

Also add:
- `users.last_active_at`
- `users.current_streak`
- `users.longest_streak`
- `users.last_active_date`

Update worker/adaptive code so these metrics change on attempt persist and quiz completion.

**Step 4: Run tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_adaptive_repositories.py tests/test_admin_analytics_service.py tests/test_performance_service.py tests/test_background_jobs.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add migrations/versions/20260408_000002_add_denormalized_learner_metrics.py src/infra/db/models/student_course_state.py src/infra/db/models/user.py src/infra/db/repositories/student_course_state_repository.py src/domains/adaptive/service.py src/workers/background_jobs.py src/domains/admin/analytics_service.py src/domains/performance/service.py tests/test_adaptive_repositories.py tests/test_admin_analytics_service.py tests/test_performance_service.py
git commit -m "feat: denormalize learner analytics metrics"
```

### Task 8: Add Session-Level Summary Table For Admin Analytics

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\migrations\versions\20260408_000003_add_student_session_summary.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\models\student_session_summary.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\repositories\student_session_summary_repository.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\models\__init__.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\workers\background_jobs.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\admin\analytics_service.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_admin_analytics_service.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_background_jobs.py`

**Step 1: Write the failing summary-table tests**

```python
async def test_completed_quiz_persists_student_session_summary():
    await persist_quiz_session_progress(payload, runtime=runtime)
    summary = await repo.get_by_session_id(payload["session_id"])
    assert summary.correct_count == 4
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_background_jobs.py tests/test_admin_analytics_service.py -k session_summary -v`
Expected: FAIL because no session summary model or writer exists.

**Step 3: Write the minimal implementation**

```python
await student_session_summary_repository.upsert_from_session(
    session_id=payload["session_id"],
    user_id=payload["user_id"],
    ...
)
```

Use this table for weekly progress and session-based charts before falling back to raw `question_attempts`.

**Step 4: Run tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_background_jobs.py tests/test_admin_analytics_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add migrations/versions/20260408_000003_add_student_session_summary.py src/infra/db/models/student_session_summary.py src/infra/db/repositories/student_session_summary_repository.py src/infra/db/models/__init__.py src/workers/background_jobs.py src/domains/admin/analytics_service.py tests/test_background_jobs.py tests/test_admin_analytics_service.py
git commit -m "feat: persist session-level learner summaries"
```

### Task 9: Switch Admin Analytics Cache To Stale-While-Revalidate

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\redis\admin_cache_store.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\admin\analytics_service.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\workers\background_jobs.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\tasks\worker.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\tasks\arq_client.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_admin_cache_store.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_worker.py`

**Step 1: Write the failing cache freshness tests**

```python
async def test_analytics_summary_returns_stale_payload_while_refresh_is_pending():
    await cache_store.set_json("analytics-summary", {"kpis": []}, bot_id="adarkwa", ttl_seconds=300)
    payload = await service.get_summary(active_bot_id="adarkwa")
    assert payload == {"kpis": []}
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_cache_store.py tests/test_worker.py -k analytics -v`
Expected: FAIL because cache invalidation currently bumps versions aggressively and forces full recompute on miss.

**Step 3: Write the minimal implementation**

```python
await cache_store.mark_dirty("analytics-summary", bot_id=bot_id)
if cached is not None:
    enqueue_precompute_admin_analytics(...)
    return cached
```

Do not version-bump analytics caches on every attempt. Keep the last good payload until the background refresh completes.

**Step 4: Run tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_cache_store.py tests/test_worker.py tests/test_background_jobs.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/infra/redis/admin_cache_store.py src/domains/admin/analytics_service.py src/workers/background_jobs.py src/tasks/worker.py src/tasks/arq_client.py tests/test_admin_cache_store.py tests/test_worker.py
git commit -m "perf: refresh admin analytics caches in background"
```

### Task 10: Update Docs And Add Rollout Notes

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\docs\ideas\optimization.md`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\docs\adaptive_runtime_architecture.md`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\docs\backend-student-analytics-suggestions.md`

**Step 1: Write the docs delta**

```markdown
- Redis stores selector manifests and learner hot snapshots, not binary image assets.
- Postgres remains canonical.
- Admin analytics caches are stale-while-revalidate.
```

**Step 2: Review docs against the implementation**

Run: `rg -n "Redis|analytics|selector|image" docs`
Expected: clear alignment between runtime docs and the new behavior.

**Step 3: Apply the minimal edits**

```markdown
Replace "cache images in Redis" guidance with "cache asset URLs/metadata in Redis and keep binaries in R2/CDN".
```

**Step 4: Run docs sanity check**

Run: `git diff -- docs/ideas/optimization.md docs/adaptive_runtime_architecture.md docs/backend-student-analytics-suggestions.md`
Expected: only intended wording and rollout notes changed.

**Step 5: Commit**

```bash
git add docs/ideas/optimization.md docs/adaptive_runtime_architecture.md docs/backend-student-analytics-suggestions.md
git commit -m "docs: align optimization guidance with cache architecture"
```

## Rollout Order

1. Task 1
2. Task 2
3. Task 3
4. Task 4
5. Task 9
6. Task 5
7. Task 6
8. Task 7
9. Task 8
10. Task 10

## Notes For Execution

- Do not store image bytes in Redis. Keep binary assets in R2 and cache only URLs and variant metadata.
- Treat all Redis caches as disposable. Every optimization here must tolerate Redis loss and rebuild from Postgres.
- Use short-lived, versioned, or explicitly invalidated Redis keys for course manifests and selector snapshots.
- Prefer SQL-side filtering and aggregation before adding new caches. Several current hotspots are query-shape problems, not missing-cache problems.
