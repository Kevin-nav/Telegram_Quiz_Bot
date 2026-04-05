# Bot-Tagged Admin Analytics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Persist exact bot identity on learner analytics/reporting rows, backfill reliable legacy history, and finish the remaining mock-backed admin reporting surfaces.

**Architecture:** Add `bot_id` to learner telemetry tables and backfill by unique course-to-bot matches, then update all new write paths to store runtime `bot_id` directly. Switch admin analytics/report/dashboard queries to row-level bot filtering and wire the dashboard to existing real APIs.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, Next.js App Router, TypeScript, TanStack Query.

---

### Task 1: Add Bot Columns and Backfill Migration

**Files:**
- Modify: `src/infra/db/models/question_attempt.py`
- Modify: `src/infra/db/models/question_report.py`
- Modify: `src/infra/db/models/student_course_state.py`
- Modify: `src/infra/db/models/student_question_srs.py`
- Modify: `src/infra/db/models/analytics_event.py`
- Create: `migrations/versions/<new_revision>_add_bot_id_to_learner_telemetry.py`
- Test: `tests/test_database_models.py`

**Step 1: Write failing model assertions**

Cover:
- each learner telemetry model exposes nullable `bot_id`
- model metadata still registers cleanly

**Step 2: Run the focused tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_database_models.py tests/test_db_metadata_registration.py -v`

**Step 3: Implement the model changes and migration**

Migration requirements:
- add nullable `bot_id` columns
- backfill `tanjah` / `adarkwa` by unique course match
- backfill ambiguous rows as `unknown`
- keep migration rerunnable-safe at the SQL/data level

**Step 4: Re-run the focused tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_database_models.py tests/test_db_metadata_registration.py -v`

**Step 5: Commit**

Commit only the migration/model slice.

---

### Task 2: Persist Runtime Bot ID on New Learner Telemetry Writes

**Files:**
- Modify: `src/workers/background_jobs.py`
- Modify: `src/domains/quiz/service.py`
- Modify: `src/domains/quiz_reporting/service.py`
- Modify: `src/domains/analytics/service.py`
- Modify: `src/infra/db/repositories/question_attempt_repository.py`
- Modify: `src/infra/db/repositories/question_report_repository.py`
- Modify: `src/infra/db/repositories/student_course_state_repository.py`
- Modify: `src/infra/db/repositories/student_question_srs_repository.py`
- Modify: `src/infra/db/repositories/analytics_repository.py`
- Test: `tests/test_background_jobs.py`
- Test: `tests/test_quiz_reporting_service.py`

**Step 1: Write failing persistence tests**

Cover:
- quiz attempt payload stores `bot_id`
- question report payload stores `bot_id`
- analytics events store `bot_id`
- adaptive state updates/upserts include `bot_id`

**Step 2: Run the focused tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_background_jobs.py tests/test_quiz_reporting_service.py -v`

**Step 3: Implement write-path propagation**

Propagate runtime `bot_id` from the active quiz/reporting/runtime context all the way to the repositories.

**Step 4: Re-run the focused tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_background_jobs.py tests/test_quiz_reporting_service.py -v`

**Step 5: Commit**

Commit only the write-path slice.

---

### Task 3: Switch Admin Analytics and Reports to Row-Level Bot Filtering

**Files:**
- Modify: `src/domains/admin/scope_service.py`
- Modify: `src/domains/admin/analytics_service.py`
- Modify: `src/domains/admin/report_service.py`
- Modify: `src/api/admin_analytics.py`
- Modify: `src/api/admin_reports.py`
- Test: `tests/test_admin_api.py`

**Step 1: Write failing admin API assertions**

Cover:
- selected bot filters by row-level `bot_id`
- `unknown` rows do not appear in normal workspace views
- staff course grants still apply inside the selected bot

**Step 2: Run the focused tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`

**Step 3: Implement row-level filtering**

Keep the existing catalog grant filtering, but make row-level `bot_id` the first filter in analytics and reports.

**Step 4: Re-run the focused tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`

**Step 5: Commit**

Commit only the analytics/report query slice.

---

### Task 4: Wire the Overview Dashboard to Real Data

**Files:**
- Modify: `admin/app/page.tsx`
- Modify: `admin/lib/api.ts`
- Optionally modify: `admin/components/bot-workspace-switcher.tsx`

**Step 1: Replace dashboard mock reads**

Use existing real endpoints:
- `/admin/analytics`
- `/admin/staff`
- `/admin/questions`
- `/admin/reports`

**Step 2: Keep the page thin**

Do not add a dashboard-specific backend endpoint unless existing endpoints prove insufficient.

**Step 3: Run the admin build**

Run: `npm run build`

**Step 4: Commit**

Commit only the dashboard slice.

---

### Task 5: Finish the Reports Surface and Remove Dead Mock UX

**Files:**
- Modify: `admin/app/reports/page.tsx`
- Modify: `admin/lib/api.ts`

**Step 1: Remove or hide nonfunctional actions**

Leave only actions that have real backend support in this slice.

**Step 2: Verify permission-sensitive rendering**

Users with `audit.view` can browse; only users with `questions.edit` can mutate.

**Step 3: Run the admin build**

Run: `npm run build`

**Step 4: Commit**

Commit only the reports UX cleanup slice if it is separate.

---

### Task 6: Final Verification

**Files:**
- No planned edits unless verification exposes defects.

**Step 1: Run focused backend verification**

Run:
- `venv\Scripts\python.exe -m pytest tests/test_database_models.py tests/test_db_metadata_registration.py tests/test_background_jobs.py tests/test_quiz_reporting_service.py tests/test_admin_api.py -v`

**Step 2: Run frontend verification**

Run:
- `npm run build`

**Step 3: Smoke-check behavior**

Verify:
- new learner telemetry rows persist `bot_id`
- legacy rows appear in the correct bot when backfilled confidently
- ambiguous legacy rows stay out of normal bot views
- `/`, `/analytics`, and `/reports` all switch cleanly with the bot workspace selector

**Step 4: Commit final fixups**

Commit any verification-driven fixes separately.

---

## Subagent-Driven Execution Map

- Worker A: schema migration + model/repository updates for `bot_id`
- Worker B: runtime write-path propagation and tests
- Worker C: dashboard/report frontend completion and build verification

Each worker must respect existing dirty files, avoid reverting unrelated changes, and report exact files changed.
