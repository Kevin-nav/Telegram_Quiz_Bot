# Admin Platform Design

## Goal

Build a staff-facing admin platform for `@Adarkwa_Study_Bot` that supports analytics, question-bank corrections, database-driven academic catalog management, and granular staff permissions without tying catalog changes to code deploys.

## Architecture

- `admin.<domain>` hosts a separate `Next.js` admin application for staff operations.
- The existing `FastAPI` application remains the system-of-record backend and exposes `/admin/*` APIs.
- Postgres/Neon is the canonical store for staff access, catalog data, questions, analytics, and audit history.
- Redis remains the speed layer for hot catalog reads, selected course summaries, and cached analytics snapshots.
- The Telegram bot and the admin app both read the same canonical catalog domain through backend services, not static code data.

## Core Decisions

- The admin must support real staff accounts with mixed permissions, not a single internal-operator role.
- `super_admin` owns staff lifecycle and permission assignment.
- Roles are convenience presets, but direct permission grants must also be supported.
- Academic structure moves from code-level configuration to database-backed catalog tables.
- Question and catalog edits must take effect without redeploying the bot.
- Every privileged write must create an audit log record.

## Staff Access Model

Recommended tables:

- `staff_users`
- `permissions`
- `staff_roles`
- `staff_role_permissions`
- `staff_user_roles`
- `staff_user_permissions`

Recommended built-in role presets:

- `super_admin`
- `content_editor`
- `catalog_manager`
- `analytics_viewer`

Recommended permissions:

- `analytics.view`
- `questions.view`
- `questions.edit`
- `questions.publish`
- `catalog.view`
- `catalog.edit`
- `staff.view`
- `staff.create`
- `staff.edit_permissions`
- `audit.view`

Rules:

- `super_admin` can create, deactivate, and update staff accounts.
- Non-super-admin users must never assign permissions above their own scope.
- Staff accounts should support `active` or `inactive` status instead of destructive deletion.
- Permission changes must be audit logged.

## Catalog Data Model

Recommended canonical tables:

- `faculties`
- `programs`
- `levels`
- `semesters`
- `courses`
- `program_course_offerings`

Relationship model:

- A faculty owns many programs.
- A course exists once canonically.
- `program_course_offerings` maps `program + level + semester + course`.
- User study profiles continue to store selected catalog codes such as `faculty_code`, `program_code`, `level_code`, `semester_code`, and `preferred_course_code`.
- Question-bank rows continue to belong to canonical course codes.

Operational rules:

- Catalog rows should support `active` or `inactive` status for safe rollout.
- The existing static catalog service should be replaced by a database-backed catalog domain service.
- The bot should read catalog data through that service so future semester expansion does not require Telegram handler rewrites.

## Content Management

Phase 1 question editing should support:

- question text
- options
- correct answer
- short explanation
- status transitions such as `draft`, `review`, `ready`, and `archived`

Recommended metadata additions:

- `last_edited_by`
- `last_edited_at`
- `review_status`

Phase 2 can add a dedicated `question_revisions` table if full revision history becomes necessary. Phase 1 is still safe if every mutation is audit logged with before or after payloads.

## Admin Product Surface

Recommended Phase 1 modules:

- `Dashboard`
  - active users
  - quiz starts and completions
  - question inventory by course
  - draft or flagged content counts
  - recent staff activity
- `Question Bank`
  - search and filter by course, topic, status, and cognitive level
  - edit question text, options, answer, and explanation
  - publish-state controls
- `Catalog`
  - create and edit faculties, programs, levels, semesters, courses, and offerings
  - activate or deactivate offerings without code changes
- `Staff & Permissions`
  - create staff accounts
  - assign preset roles and direct permissions
  - deactivate or reactivate staff access
- `Audit Log`
  - actor
  - action
  - entity type
  - entity id
  - timestamp
  - before and after snapshots where appropriate
- `Analytics`
  - course-level performance
  - question accuracy
  - weak-topic trends
  - user progress summaries

## Runtime and Performance

### Fast Reads

- Postgres remains canonical.
- Redis stores:
  - full catalog tree
  - offering lists by `program + level + semester`
  - course summary counts
  - analytics snapshots
- Backend writes must invalidate only the affected cache keys.

### Consistency

- Catalog writes commit to Postgres first, then invalidate Redis.
- Question writes commit to Postgres first, then invalidate question or course-level cache entries.
- Audit log records should be written in the same request path as the mutation.

### Query Strategy

- Build purpose-specific admin endpoints rather than generic full-table fetches.
- Paginate large datasets such as questions, staff users, and audit logs.
- Add indexes for:
  - question-bank filtering by course, status, topic, and cognitive level
  - offering lookup by program, level, and semester
  - audit-log filtering by actor, entity type, and time
  - analytics aggregation paths

## Security and Safety

- Staff auth must be separate from Telegram user identity.
- Backend permission checks are mandatory for every admin route.
- Frontend role gating is UX only and must not be treated as security.
- Sensitive actions should be auditable from day one.
- Destructive deletes should be avoided in favor of soft deletion or inactive flags for staff and catalog entities.

## Testing

Required coverage:

- permission evaluation
- staff account lifecycle
- catalog CRUD plus cache invalidation
- question editing and publication rules
- audit log creation on privileged writes
- bot catalog reads after the static service is replaced
- admin API permission enforcement
- basic admin UI flows for login, staff creation, question editing, and catalog updates

## Recommended Stack

- frontend: `Next.js`, TypeScript, Tailwind, `shadcn/ui`, TanStack Table, React Query
- backend: existing `FastAPI` app with new `/admin/*` APIs
- database: existing Postgres/Neon
- cache: existing Redis
- charts: Recharts or ECharts

## Build Order

1. Add staff auth, permissions, and audit-log backend foundations.
2. Add canonical catalog tables and migrate static catalog data into the database.
3. Replace static bot catalog reads with DB-backed catalog service plus Redis caching.
4. Create the `Next.js` admin shell on the admin subdomain.
5. Implement `Staff & Permissions`.
6. Implement `Catalog`.
7. Implement `Question Bank`.
8. Implement `Dashboard` and `Analytics`.
