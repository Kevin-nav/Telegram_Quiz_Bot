# Bot-Scoped Admin Access Design

## Goal

Connect the current `admin/` frontend to real backend data and authentication, while restricting each non-super-admin to exactly one bot workspace and allowing only super admins to switch between `tanjah` and `adarkwa` inside the same shared admin URL.

## Approved Product Behavior

- The admin site stays on one shared URL.
- Super admins can access both bot workspaces and switch from a top-header workspace switcher.
- Super admins land on their last-used bot workspace after login.
- Normal admins are pinned to one bot workspace and never see the switcher.
- Backend authorization is the source of truth; frontend visibility is only UX.
- Within a selected bot workspace, normal admins can optionally be constrained further to specific course offerings or level/course scopes.

## Existing Repo Context

The backend already has:

- two runtime bot identifiers: `tanjah` and `adarkwa`
- bot-specific course visibility in `src/bot/runtime_config.py`
- admin staff/role/permission tables and catalog tables
- an unfinished session/password auth direction in `docs/plans/2026-03-26-admin-auth-design.md`
- a super-admin bootstrap script at `scripts/bootstrap_admin.py`

The frontend currently has:

- a usable admin shell in `admin/components/admin-shell.tsx`
- mock-driven staff/catalog/questions/analytics pages
- demo-cookie login and set-password screens that are not yet wired to real backend auth
- a central API helper in `admin/lib/api.ts` that still includes the old `X-Admin-User-Id` bridge

## Architecture

### 1. Staff Identity and Sessions

Use real `email + password` staff login backed by server-side admin sessions and an HTTP-only cookie.

Session resolution must stop relying on `X-Admin-User-Id` and instead load the staff principal from `admin_sessions`.

The principal returned by `GET /admin/auth/me` should include:

- staff identity
- effective permissions
- assigned bot ids
- active bot id
- `must_change_password`

### 2. Bot Access Scope

Add a dedicated bot-assignment model instead of encoding bot scope in free-form permission codes.

Recommended table:

- `staff_bot_access`
  - `id`
  - `staff_user_id`
  - `bot_id`
  - `is_active`
  - `created_at`
  - unique constraint on `(staff_user_id, bot_id)`

Rules:

- users with `super_admin` role may hold both `tanjah` and `adarkwa`
- all other users must have exactly one active `bot_id`
- every admin read/write must validate that the requested or selected bot belongs to the current principal
- if a user has one bot only, that bot becomes their active workspace automatically
- if a super admin has multiple bots, use a persisted last-selected bot preference, falling back to `adarkwa` and then any assigned bot

### 3. Optional Course/Level Grants Inside a Bot

Bot scope answers “which bot can this admin manage?” and should stay separate from “which academic content inside that bot can this admin touch?”.

For course/level restrictions, add assignment rows tied to a staff user, a bot, and a catalog scope:

- `staff_catalog_access`
  - `id`
  - `staff_user_id`
  - `bot_id`
  - `program_code` nullable
  - `level_code` nullable
  - `course_code` nullable
  - `is_active`
  - `created_at`

Interpretation:

- no rows for a normal admin means full access within their one bot
- one row with `program_code + level_code` grants all courses in that level/program for that bot
- one row with `program_code + level_code + course_code` grants one exact course offering slice for that bot
- super admins bypass catalog-scope restrictions

Backend services should enforce those grants when listing catalog nodes, questions, and analytics, and when mutating questions/catalog rows.

### 4. Active Bot Selection for Super Admins

Add a small workspace switcher in the top header of `AdminShell`.

Behavior:

- render only when the principal has more than one assigned bot
- display the active bot name
- switching calls a backend endpoint that updates the current session's active bot or the user preference used by that session
- refresh page data after switching so catalog/questions/analytics immediately reflect the new bot workspace

Normal admins should never be asked to pick a bot during login because their account has one fixed bot scope.

### 5. Frontend Data Wiring

Replace mock-first state on staff/catalog/auth flows with real API calls while preserving the current visual shell.

Priority wiring order:

1. `/login`, `/set-password`, and `AdminShell` auth state
2. `/staff` staff list, create/edit, password reset, bot assignment, and optional catalog grants
3. `/catalog` tree/loading and offering activation against real catalog APIs filtered by active bot
4. `/questions` list/edit against real question APIs filtered by active bot and catalog grants
5. `/analytics` and `/reports` should remain stable, with bot scoping applied where backend coverage exists and mock fallback kept only for still-missing data slices

### 6. Deployment Integration

Keep deployment operational by updating:

- Alembic migrations for new auth/bot-scope tables
- `scripts/bootstrap_admin.py` so the first super admin is created with both bot access records and a temporary password
- environment/documentation for admin frontend API base URL, allowed origins, and session cookie settings
- deployment docs to include migration and bootstrap order for a fresh environment

## API Shape

### Auth

- `POST /admin/auth/login`
- `POST /admin/auth/logout`
- `POST /admin/auth/set-password`
- `GET /admin/auth/me`
- `POST /admin/auth/select-bot`

`GET /admin/auth/me` should return at least:

```json
{
  "staff_user_id": 1,
  "email": "admin@example.com",
  "display_name": "Admin User",
  "roles": ["super_admin"],
  "permissions": ["staff.view", "catalog.edit"],
  "bot_access": ["tanjah", "adarkwa"],
  "active_bot_id": "adarkwa",
  "must_change_password": false
}
```

### Staff

Extend staff create/update payloads to accept:

- `role_codes`
- `permission_codes`
- `bot_access`
- `catalog_access`
- `temporary_password` on create/reset flows

### Catalog and Questions

Admin catalog/question endpoints should use the current principal's active bot by default, optionally accepting an explicit `bot_id` only when the principal is authorized for that bot.

## Data Integrity and Edge Cases

- Never allow a non-super-admin staff user to save more than one bot scope.
- Never leave a non-super-admin with zero active bot assignments.
- If a super admin switches to a bot they are no longer assigned to, reject and fall back to an allowed bot.
- If a normal admin has stale catalog grants outside their assigned bot, ignore those rows and prevent edits through validation.
- If `must_change_password=true`, block all non-auth pages until password is updated.
- Password reset must revoke all sessions for that staff user.

## Testing Strategy

Backend:

- session-cookie login/logout/me
- forced password change
- super-admin bootstrap
- bot-scope assignment and enforcement
- course/level-scope enforcement
- catalog/question filtering by active bot and catalog grants
- super-admin bot switching

Frontend:

- login and set-password submit real auth requests
- admin shell renders current principal and super-admin-only bot switcher
- staff page loads/saves real users, bot scope, and catalog grants
- catalog page reads real catalog data for the active bot
- question page reads/updates real question data for the active bot
- lint/build pass

## Rollout Order

1. Add backend schema and session/bot-scope services.
2. Update bootstrap script and auth/staff APIs.
3. Wire frontend auth and admin shell principal state.
4. Wire staff management with bot scope and catalog grants.
5. Wire catalog/questions to bot-scoped real data.
6. Update deployment docs and run backend/frontend verification.

