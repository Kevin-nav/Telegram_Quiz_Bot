# Admin Auth Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace scaffolded admin authentication with real email-and-password staff auth using server-side sessions, super-admin-managed temporary passwords, and a forced password-change flow that fits the current admin UI language.

**Architecture:** Keep authentication in the existing `FastAPI` backend and use database-backed session storage with an HTTP-only cookie. Extend `staff_users`, add `admin_sessions`, replace the current `X-Admin-User-Id` bridge, and add a restrained auth UI in the `Next.js` admin app that reuses the current visual system instead of introducing generic auth templates.

**Tech Stack:** FastAPI, async SQLAlchemy, Alembic, secure password hashing (`argon2` or `bcrypt`), HTTP-only cookies, Next.js App Router, TypeScript

---

### Task 1: Add password and session database schema

**Files:**
- Modify: `src/infra/db/models/staff_user.py`
- Create: `src/infra/db/models/admin_session.py`
- Modify: `src/infra/db/models/__init__.py`
- Create: `migrations/versions/20260326_000001_add_admin_auth_tables.py`
- Test: `tests/test_database_models.py`
- Test: `tests/test_db_metadata_registration.py`

**Step 1: Write the failing test**

```python
def test_staff_user_model_has_password_auth_columns():
    from src.infra.db.models.staff_user import StaffUser

    columns = {column.name for column in StaffUser.__table__.columns}
    assert {"password_hash", "must_change_password", "password_updated_at"} <= columns
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_database_models.py tests/test_db_metadata_registration.py -v`
Expected: FAIL because password/session auth schema does not exist yet.

**Step 3: Write minimal implementation**

- Add password fields to `staff_users`.
- Add `admin_sessions`.
- Register the model and create the Alembic migration.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_database_models.py tests/test_db_metadata_registration.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/infra/db/models migrations/versions tests/test_database_models.py tests/test_db_metadata_registration.py
git commit -m "feat: add admin password and session schema"
```

### Task 2: Add password hashing and session services

**Files:**
- Create: `src/domains/admin/password_service.py`
- Create: `src/domains/admin/session_service.py`
- Create: `src/infra/db/repositories/admin_session_repository.py`
- Modify: `src/domains/admin/__init__.py`
- Test: `tests/test_admin_auth_service.py`

**Step 1: Write the failing test**

```python
def test_password_service_verifies_hashed_password():
    from src.domains.admin.password_service import PasswordService

    service = PasswordService()
    digest = service.hash_password("temp-password")
    assert service.verify_password("temp-password", digest) is True
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_auth_service.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add password hash and verify helpers.
- Add session token issue, hash, lookup, and revoke helpers.
- Keep token storage hashed-only.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_auth_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/admin src/infra/db/repositories/admin_session_repository.py tests/test_admin_auth_service.py
git commit -m "feat: add admin password and session services"
```

### Task 3: Replace header-based auth with cookie-based session auth

**Files:**
- Modify: `src/api/admin_auth.py`
- Modify: `src/api/admin_staff.py`
- Modify: `src/api/admin_catalog.py`
- Modify: `src/api/admin_questions.py`
- Modify: `src/api/admin_audit.py`
- Test: `tests/test_admin_api.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_admin_me_uses_session_cookie_instead_of_header():
    assert False, "Replace header bridge with session auth"
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Read the session cookie in auth dependency.
- Resolve the current principal from `admin_sessions`.
- Remove `X-Admin-User-Id` as the real auth path.
- Keep permission checks layered on the resolved principal.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/api tests/test_admin_api.py
git commit -m "feat: use cookie-based admin sessions"
```

### Task 4: Add login, logout, and current-session endpoints

**Files:**
- Modify: `src/api/admin_auth.py`
- Modify: `src/domains/admin/auth_service.py`
- Test: `tests/test_admin_api.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_admin_login_sets_session_cookie_for_valid_credentials():
    assert False, "Implement real admin login endpoint"
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add `POST /admin/auth/login`.
- Add `POST /admin/auth/logout`.
- Update `GET /admin/auth/me` to return `must_change_password`.
- Set and clear secure session cookies consistently.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/api/admin_auth.py src/domains/admin/auth_service.py tests/test_admin_api.py
git commit -m "feat: add admin login and logout endpoints"
```

### Task 5: Add forced password change flow

**Files:**
- Modify: `src/api/admin_auth.py`
- Modify: `src/domains/admin/auth_service.py`
- Modify: `src/domains/admin/staff_service.py`
- Test: `tests/test_admin_api.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_temporary_password_login_requires_password_change():
    assert False, "Implement must-change-password flow"
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add `POST /admin/auth/set-password`.
- Require current password.
- Clear `must_change_password` on success.
- Update password hash and timestamps.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/api/admin_auth.py src/domains/admin/auth_service.py src/domains/admin/staff_service.py tests/test_admin_api.py
git commit -m "feat: add forced admin password change flow"
```

### Task 6: Add super-admin temporary password reset flow

**Files:**
- Modify: `src/api/admin_staff.py`
- Modify: `src/domains/admin/staff_service.py`
- Modify: `src/domains/admin/audit_service.py`
- Test: `tests/test_admin_api.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_super_admin_reset_password_sets_temporary_password_and_revokes_sessions():
    assert False, "Implement admin-driven reset flow"
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add `POST /admin/staff/{id}/reset-password`.
- Accept a temporary password from the super-admin flow.
- Set `must_change_password = true`.
- Revoke active sessions for that user.
- Audit log the reset without exposing plaintext password.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/api/admin_staff.py src/domains/admin/staff_service.py src/domains/admin/audit_service.py tests/test_admin_api.py
git commit -m "feat: add super-admin password reset flow"
```

### Task 7: Replace scaffolded frontend login with real auth

**Files:**
- Modify: `admin/app/login/page.tsx`
- Modify: `admin/lib/api.ts`
- Modify: `admin/middleware.ts`
- Test: `admin/app/login/page.tsx`

**Step 1: Write the failing test**

```tsx
// Add a typechecked path or lightweight validation target for real login wiring.
```

**Step 2: Run test to verify it fails**

Run: `cd admin && npm run lint`
Expected: FAIL until login uses real auth and middleware is updated.

**Step 3: Write minimal implementation**

- Replace demo cookie handling.
- Post credentials to backend login endpoint.
- Load session from backend cookie.
- Redirect unauthenticated users correctly.

**Step 4: Run test to verify it passes**

Run: `cd admin && npm run lint`
Expected: PASS

**Step 5: Commit**

```bash
git add admin/app/login/page.tsx admin/lib/api.ts admin/middleware.ts
git commit -m "feat: wire admin frontend to real auth"
```

### Task 8: Add `set-password` screen and forced-password routing

**Files:**
- Create: `admin/app/set-password/page.tsx`
- Modify: `admin/middleware.ts`
- Modify: `admin/components/admin-shell.tsx`
- Test: `admin/app/set-password/page.tsx`

**Step 1: Write the failing test**

```tsx
// Add typechecked validation path for set-password route existence and props.
```

**Step 2: Run test to verify it fails**

Run: `cd admin && npm run lint`
Expected: FAIL until the route and guards exist.

**Step 3: Write minimal implementation**

- Add restrained password-change UI using the current admin design language.
- Redirect `must_change_password` users there.
- Keep layout intentional and avoid excess card or gradient use.

**Step 4: Run test to verify it passes**

Run: `cd admin && npm run lint`
Expected: PASS

**Step 5: Commit**

```bash
git add admin/app/set-password/page.tsx admin/middleware.ts admin/components/admin-shell.tsx
git commit -m "feat: add admin set-password screen"
```

### Task 9: Update staff admin UI for temporary-password issuance and reset

**Files:**
- Modify: `admin/app/staff/page.tsx`
- Modify: `admin/components/staff/staff-form.tsx`
- Modify: `admin/components/staff/staff-table.tsx`
- Modify: `admin/lib/api.ts`
- Test: `admin/app/staff/page.tsx`

**Step 1: Write the failing test**

```tsx
// Add typechecked path for temporary-password reset controls.
```

**Step 2: Run test to verify it fails**

Run: `cd admin && npm run lint`
Expected: FAIL until the UI exposes reset functionality.

**Step 3: Write minimal implementation**

- Let super-admin create staff with a temporary password.
- Add reset-password action for existing staff.
- Present the temporary password flow clearly without overdesigning the screen.

**Step 4: Run test to verify it passes**

Run: `cd admin && npm run lint`
Expected: PASS

**Step 5: Commit**

```bash
git add admin/app/staff/page.tsx admin/components/staff admin/lib/api.ts
git commit -m "feat: add temporary password staff controls"
```

### Task 10: Document real local auth setup

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `admin/.env.example`
- Modify: `scripts/bootstrap_admin.py`

**Step 1: Write the failing test**

There is no automated test for this task. Use a manual verification checklist.

**Step 2: Run manual verification to confirm docs are incomplete**

Run:
- `venv\Scripts\python.exe scripts/bootstrap_admin.py --help`
- `cd admin && npm run build`

Expected: confirm docs/examples need to match the real auth flow.

**Step 3: Write minimal implementation**

- Update docs and examples to describe the real auth path.
- Remove references to demo header-based auth where no longer true.

**Step 4: Run manual verification**

Run:
- `venv\Scripts\python.exe scripts/bootstrap_admin.py --help`
- `cd admin && npm run build`

Expected: commands succeed and docs match actual setup.

**Step 5: Commit**

```bash
git add README.md .env.example admin/.env.example scripts/bootstrap_admin.py
git commit -m "docs: document real admin auth setup"
```
