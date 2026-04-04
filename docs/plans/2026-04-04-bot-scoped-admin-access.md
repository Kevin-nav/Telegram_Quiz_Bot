# Bot-Scoped Admin Access Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire the current admin frontend to real backend auth/data and enforce bot-scoped plus optional course/level-scoped admin access from one shared admin URL.

**Architecture:** Extend staff/auth schema with bot assignments, optional catalog grants, and session-backed active-bot selection. Replace header-based demo auth with cookie-backed sessions, then wire `admin/` pages to real `/admin/*` APIs and add a super-admin-only top-bar bot workspace switcher.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, Next.js App Router, TypeScript, Tailwind, shadcn/ui.

---

### Task 1: Add Bot-Scope and Catalog-Grant Database Schema

**Files:**
- Create: `src/infra/db/models/staff_bot_access.py`
- Create: `src/infra/db/models/staff_catalog_access.py`
- Modify: `src/infra/db/models/staff_user.py`
- Modify: `src/infra/db/models/__init__.py`
- Create: `migrations/versions/<new_revision>_add_staff_bot_and_catalog_access.py`
- Test: `tests/test_database_models.py`
- Test: `tests/test_db_metadata_registration.py`

**Step 1: Write failing schema/model tests**

Cover:
- `staff_users` has password/session fields and a last-selected bot field
- `staff_bot_access` exists with unique `(staff_user_id, bot_id)`
- `staff_catalog_access` exists and supports nullable program/level/course scopes

**Step 2: Run tests and verify they fail**

Run: `venv\\Scripts\\python.exe -m pytest tests/test_database_models.py tests/test_db_metadata_registration.py -v`

**Step 3: Implement models and migration**

Add:
- password/session fields to `StaffUser` if missing
- `last_selected_bot_id` to `StaffUser`
- `StaffBotAccess`
- `StaffCatalogAccess`
- Alembic migration for the new tables/column

**Step 4: Run tests and verify they pass**

Run: `venv\\Scripts\\python.exe -m pytest tests/test_database_models.py tests/test_db_metadata_registration.py -v`

**Step 5: Commit**

Commit only files touched by this task.

---

### Task 2: Implement Session-Based Auth and Bot-Aware Principal Resolution

**Files:**
- Modify: `src/domains/admin/auth_service.py`
- Modify: `src/domains/admin/password_service.py`
- Modify: `src/domains/admin/session_service.py`
- Modify: `src/infra/db/repositories/staff_user_repository.py`
- Modify: `src/infra/db/repositories/admin_session_repository.py`
- Create: `src/infra/db/repositories/staff_bot_access_repository.py`
- Test: `tests/test_admin_auth_service.py`

**Step 1: Write failing auth-service tests**

Cover:
- password verification
- session token issue/hash/expiry
- login resolves principal with roles, permissions, bot access, active bot, and `must_change_password`
- normal admins resolve exactly one active bot
- super admins resolve last-selected bot when present

**Step 2: Run tests and verify they fail**

Run: `venv\\Scripts\\python.exe -m pytest tests/test_admin_auth_service.py -v`

**Step 3: Implement services/repositories**

Add:
- authenticate-by-email/password
- create/revoke/touch admin sessions
- resolve principal from session token hash
- list bot assignments for a staff user
- persist/update `last_selected_bot_id` for super-admin switching

**Step 4: Run tests and verify they pass**

Run: `venv\\Scripts\\python.exe -m pytest tests/test_admin_auth_service.py -v`

**Step 5: Commit**

Commit only files touched by this task.

---

### Task 3: Replace Header-Based Admin Auth with Cookie Sessions in API Routers

**Files:**
- Modify: `src/api/admin_auth.py`
- Modify: `src/api/admin_staff.py`
- Modify: `src/api/admin_catalog.py`
- Modify: `src/api/admin_questions.py`
- Modify: `src/api/admin_audit.py`
- Test: `tests/test_admin_api.py`

**Step 1: Write failing API tests**

Cover:
- `POST /admin/auth/login` sets HTTP-only session cookie
- `GET /admin/auth/me` uses session cookie, not `X-Admin-User-Id`
- `POST /admin/auth/logout` revokes and clears cookie
- `POST /admin/auth/set-password` clears `must_change_password`
- requests without a valid session return 401
- requests lacking a permission return 403

**Step 2: Run tests and verify they fail**

Run: `venv\\Scripts\\python.exe -m pytest tests/test_admin_api.py -v`

**Step 3: Implement API auth flow**

Add:
- login/logout/set-password routes
- cookie-based principal dependency
- remove `X-Admin-User-Id` from the real auth path
- include permissions, bot access, active bot, and `must_change_password` in `/me`

**Step 4: Run tests and verify they pass**

Run: `venv\\Scripts\\python.exe -m pytest tests/test_admin_api.py -v`

**Step 5: Commit**

Commit only files touched by this task.

---

### Task 4: Implement Staff Bot Assignments, Optional Catalog Grants, and Password Reset

**Files:**
- Modify: `src/domains/admin/staff_service.py`
- Modify: `src/api/admin_staff.py`
- Modify: `src/domains/admin/permission_service.py`
- Create: `src/infra/db/repositories/staff_catalog_access_repository.py`
- Test: `tests/test_admin_api.py`
- Test: `tests/test_admin_staff_service.py`

**Step 1: Write failing staff-management tests**

Cover:
- create normal admin with exactly one bot
- reject normal admin with zero or multiple bots
- create super admin with both bots
- update staff bot assignments and catalog grants
- reset-password stores a new hash, sets `must_change_password=true`, and revokes sessions

**Step 2: Run tests and verify they fail**

Run: `venv\\Scripts\\python.exe -m pytest tests/test_admin_api.py tests/test_admin_staff_service.py -v`

**Step 3: Implement validation and persistence**

Add:
- `bot_access` and `catalog_access` handling in create/update flows
- role-aware validation for one-bot-only normal admins
- password reset endpoint/service logic
- audit logs for bot-scope and catalog-grant updates

**Step 4: Run tests and verify they pass**

Run: `venv\\Scripts\\python.exe -m pytest tests/test_admin_api.py tests/test_admin_staff_service.py -v`

**Step 5: Commit**

Commit only files touched by this task.

---

### Task 5: Enforce Active-Bot and Course/Level Scope on Catalog and Question APIs

**Files:**
- Modify: `src/api/admin_catalog.py`
- Modify: `src/api/admin_questions.py`
- Modify: `src/domains/admin/catalog_service.py`
- Modify: `src/domains/admin/question_service.py`
- Modify: `src/domains/admin/permission_service.py`
- Modify: `src/infra/db/repositories/permission_repository.py`
- Modify: `src/infra/db/repositories/question_bank_repository.py`
- Test: `tests/test_admin_api.py`
- Test: `tests/test_admin_catalog_service.py`
- Test: `tests/test_admin_question_service.py`

**Step 1: Write failing scope-enforcement tests**

Cover:
- normal admins only see their assigned bot's catalog/questions
- super admins see the selected bot workspace and can switch
- normal admins with catalog grants only see matching program/level/course slices
- writes to out-of-scope questions/catalog rows are rejected

**Step 2: Run tests and verify they fail**

Run: `venv\\Scripts\\python.exe -m pytest tests/test_admin_api.py tests/test_admin_catalog_service.py tests/test_admin_question_service.py -v`

**Step 3: Implement scope checks**

Add:
- principal-aware active-bot selection in admin catalog/question services
- filtering against bot runtime config and catalog grants
- defensive write-time validation before mutating questions or offerings
- `POST /admin/auth/select-bot` for super admins

**Step 4: Run tests and verify they pass**

Run: `venv\\Scripts\\python.exe -m pytest tests/test_admin_api.py tests/test_admin_catalog_service.py tests/test_admin_question_service.py -v`

**Step 5: Commit**

Commit only files touched by this task.

---

### Task 6: Wire Frontend Auth and Remove Demo Header/Cookie Bridges

**Files:**
- Modify: `admin/lib/api.ts`
- Modify: `admin/app/login/page.tsx`
- Modify: `admin/app/set-password/page.tsx`
- Modify: `admin/middleware.ts`
- Modify: `admin/components/admin-shell.tsx`
- Create: `admin/components/bot-workspace-switcher.tsx`

**Step 1: Typecheck current frontend entrypoints**

Run: `cd admin; npm run lint`

**Step 2: Implement real auth client flow**

Add:
- `loginAdmin`, `logoutAdmin`, `setAdminPassword`, `selectAdminBot`, `fetchAdminPrincipal`
- no `X-Admin-User-Id` header injection
- login and set-password forms call real APIs
- shell fetches principal, renders current user, and shows bot switcher only for multi-bot principals
- normal admins never see the bot switcher

**Step 3: Run lint/build**

Run:
- `cd admin; npm run lint`
- `cd admin; npm run build`

**Step 4: Commit**

Commit only files touched by this task.

---

### Task 7: Wire Staff Management UI to Real Staff, Bot Scope, and Catalog Grants

**Files:**
- Modify: `admin/lib/api.ts`
- Modify: `admin/app/staff/page.tsx`
- Modify: `admin/components/staff/staff-sheet.tsx`
- Optionally create: `admin/components/staff/catalog-access-editor.tsx`

**Step 1: Implement real staff API integration**

Load staff rows from `/admin/staff`, save create/update/reset-password to the backend, and remove mock-only local mutations.

**Step 2: Add bot assignment and catalog grant controls**

In the staff sheet:
- normal admins can be assigned one bot
- super admins can be assigned both bots
- optional catalog grants can capture program/level/course scopes under the selected bot

**Step 3: Run lint/build**

Run:
- `cd admin; npm run lint`
- `cd admin; npm run build`

**Step 4: Commit**

Commit only files touched by this task.

---

### Task 8: Wire Catalog and Questions Pages to Real Bot-Scoped Data

**Files:**
- Modify: `admin/lib/api.ts`
- Modify: `admin/app/catalog/page.tsx`
- Modify: `admin/components/catalog/miller-columns.tsx`
- Modify: `admin/app/questions/page.tsx`
- Modify: `admin/components/questions/question-editor-dialog.tsx`

**Step 1: Replace mock catalog/questions reads**

Use real `/admin/catalog` and `/admin/questions` calls and reload when the active bot changes.

**Step 2: Apply write flows**

Persist offering activation and question edits through backend APIs and show success/error toasts.

**Step 3: Run lint/build**

Run:
- `cd admin; npm run lint`
- `cd admin; npm run build`

**Step 4: Commit**

Commit only files touched by this task.

---

### Task 9: Update Bootstrap Script, Env Files, and Deployment Docs

**Files:**
- Modify: `scripts/bootstrap_admin.py`
- Modify: `.env.example`
- Modify: `admin/.env.example`
- Modify: `README.md`
- Modify: `docs/deployment_setup.md`

**Step 1: Update bootstrap behavior**

Ensure the first super-admin is created with:
- a hashed temporary password
- `must_change_password=true`
- both `tanjah` and `adarkwa` bot assignments
- default roles/permissions

**Step 2: Document deployment order**

Document:
- run Alembic migrations
- run `scripts/bootstrap_admin.py`
- configure admin frontend API base URL
- configure admin CORS origins and cookie domain
- build/deploy backend and admin frontend

**Step 3: Verify bootstrap help and docs-sensitive commands**

Run:
- `venv\\Scripts\\python.exe scripts/bootstrap_admin.py --help`
- `cd admin; npm run build`

**Step 4: Commit**

Commit only files touched by this task.

---

### Task 10: Final Integration Verification

**Files:**
- No planned source edits unless a verification failure exposes a bug.

**Step 1: Run backend tests**

Run targeted admin/catalog/question tests first, then the broader relevant suite.

**Step 2: Run frontend lint/build**

Run:
- `cd admin; npm run lint`
- `cd admin; npm run build`

**Step 3: Smoke-check end-to-end admin flow**

Verify:
- bootstrap super admin
- login with temporary password
- forced password change
- super-admin bot switcher toggles between `tanjah` and `adarkwa`
- normal admin sees only one bot and no switcher
- catalog/questions respect bot scope and optional catalog grants

**Step 4: Commit**

Commit any final fixups separately with a clear summary.

---

## Subagent-Driven Execution Map

Use subagents in parallel with disjoint file ownership after Tasks 1-2 establish the backend schema/auth base:

- Worker A: backend staff/bot/catalog-grant APIs and services
- Worker B: frontend auth, shell, staff, and catalog/question wiring
- Worker C: deployment docs, env docs, bootstrap verification, and focused test sweeps

Each worker must not revert edits made by others and must list modified files in its final response.

