# Bot-Tagged Admin Analytics Design

## Goal

Eliminate the remaining bot-scoping gap in learner analytics/reporting by persisting `bot_id` on learner telemetry tables, backfilling legacy rows where the bot can be inferred, and finishing the remaining mock-backed admin surfaces such as the dashboard.

## Approved Product Behavior

- Admin analytics, reports, and dashboard must filter by the selected admin bot workspace using row-level `bot_id`, not only course-derived inference.
- Existing learner telemetry should be backfilled to a bot when that mapping is reliable from current course rules.
- Ambiguous or unmappable legacy rows should be marked as `unknown`, not forced into the wrong bot.
- All new attempts, reports, adaptive state rows, and analytics events must persist the runtime `bot_id` directly.
- Super admins continue to use the single shared admin URL and switch workspaces from the header.
- Remaining mock-backed admin views should move onto real data in the same slice, starting with `/`.

## Existing Repo Context

The repo already has:

- runtime bot identifiers and course constraints in `src/bot/runtime_config.py`
- worker-based persistence for quiz attempts, question reports, quiz session progress, and analytics events in `src/workers/background_jobs.py`
- learner telemetry tables:
  - `question_attempts`
  - `question_reports`
  - `student_course_state`
  - `student_question_srs`
  - `analytics_events`
- real admin analytics/report routes and pages added in the previous slice
- a remaining mock-backed overview dashboard in `admin/app/page.tsx`

The main gap is that learner telemetry rows do not yet persist `bot_id`, so admin reporting is still forced to scope by course rules rather than exact bot identity.

## Architecture

### 1. Row-Level Bot Attribution

Add nullable `bot_id` columns to these tables:

- `question_attempts`
- `question_reports`
- `student_course_state`
- `student_question_srs`
- `analytics_events`

Use a small shared set of allowed values:

- `tanjah`
- `adarkwa`
- `unknown`

`unknown` is only for legacy backfill cases where the true bot cannot be inferred safely.

### 2. Legacy Backfill Strategy

Backfill rules:

- if a row has a course that belongs to exactly one configured bot, assign that bot
- if a row matches multiple bots or no bots, assign `unknown`
- if an `analytics_event` carries `course_id` in metadata, use that course to infer bot
- if an `analytics_event` has no reliable course signal, assign `unknown`

This preserves continuity for reliable historical data without corrupting history by force-mapping ambiguous rows.

### 3. New Runtime Writes

All new learner telemetry writes must persist `bot_id` from the active runtime bot:

- quiz attempt persistence
- quiz session progress persistence
- question report persistence
- analytics event persistence
- student adaptive state persistence (`student_course_state`, `student_question_srs`)

The write path should never rely on later inference once this is in place.

### 4. Admin Query Enforcement

Admin analytics/report/dashboard queries should change from:

1. infer by course set

to:

1. filter rows by selected `bot_id`
2. apply staff catalog/course grants inside that bot
3. exclude `unknown` from normal bot views

This keeps admin data aligned with the workspace switcher and the permission model already in place.

### 5. Dashboard Completion

The dashboard at `/` should move to real data and reuse existing analytics/report/question/staff APIs instead of creating a second reporting surface.

Recommended composition:

- KPI cards from `/admin/analytics`
- staff count from `/admin/staff`
- question counts from `/admin/questions`
- recent open reports from `/admin/reports`
- top students from `/admin/analytics`

This keeps the dashboard thin and avoids a large new dashboard-only backend contract unless a performance issue appears later.

### 6. Report Surface Completion

The reports page should remain real-data-backed and avoid dead mock actions.

For this slice:

- keep resolve/dismiss fully functional
- remove or hide inactive actions that do not yet have a backend flow
- keep read-only browsing available to staff with `audit.view`
- keep mutation controls limited to staff with `questions.edit`

### 7. Deployment Integration

Deployment should remain straightforward:

- add one Alembic migration for the new `bot_id` columns and backfill
- ensure the migration is idempotent at the data level
- no extra manual production step beyond running migrations
- updated admin queries should tolerate legacy `unknown` rows cleanly

## Data Integrity and Edge Cases

- Never coerce an ambiguous legacy row into a concrete bot.
- Treat `unknown` as excluded from normal workspace analytics so super admins are not shown mixed history accidentally.
- If bot allowed-course config changes later, previously persisted row-level `bot_id` remains the source of truth.
- Adaptive state rows should be bot-specific going forward, even when the same user/course pair exists under multiple bots historically.
- Query services must not accidentally mix `unknown` rows into `tanjah` or `adarkwa` workspace views.

## Testing Strategy

Backend:

- migration/backfill tests for unique-match and ambiguous `unknown`
- worker tests that new attempt/report/event/state rows persist `bot_id`
- admin API tests for analytics/report/dashboard filtering by selected bot
- repository/model tests for the new columns

Frontend:

- dashboard renders real API-backed metrics
- workspace switch invalidates dashboard, analytics, and reports queries
- reports only show mutation controls when allowed
- admin build passes

## Rollout Order

1. Add schema migration and backfill logic.
2. Update runtime persistence to write `bot_id`.
3. Update admin analytics/report/dashboard services to filter by row-level `bot_id`.
4. Wire the dashboard and remove remaining mock-backed production behavior.
5. Run focused backend tests and admin build.
