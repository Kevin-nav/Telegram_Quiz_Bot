# Admin Platform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first production-ready slice of the `@Adarkwa_Study_Bot` admin platform with staff auth foundations, granular permissions, a database-backed catalog, Redis-backed catalog reads, and a new `Next.js` admin app on a separate subdomain.

**Architecture:** Keep the existing `FastAPI` service as the canonical backend and add a new `admin/` `Next.js` application for the staff UI. Move catalog truth into Postgres, expose purpose-built `/admin/*` APIs, and use Redis invalidation for hot catalog reads so both the bot and admin UI stay responsive.

**Tech Stack:** FastAPI, async SQLAlchemy, Alembic, Redis, pytest, Next.js, TypeScript, Tailwind CSS, React Query, TanStack Table

---

### Task 1: Add admin database models for staff access and audit logs

**Files:**
- Create: `src/infra/db/models/staff_user.py`
- Create: `src/infra/db/models/staff_role.py`
- Create: `src/infra/db/models/permission.py`
- Create: `src/infra/db/models/staff_user_role.py`
- Create: `src/infra/db/models/staff_user_permission.py`
- Create: `src/infra/db/models/staff_role_permission.py`
- Create: `src/infra/db/models/audit_log.py`
- Modify: `src/infra/db/models/__init__.py`
- Test: `tests/test_database_models.py`

**Step 1: Write the failing test**

```python
def test_staff_user_model_has_expected_columns():
    from src.infra.db.models.staff_user import StaffUser

    column_names = {column.name for column in StaffUser.__table__.columns}
    assert {"id", "email", "is_active"} <= column_names
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_database_models.py -v`
Expected: FAIL because the admin models do not exist yet.

**Step 3: Write minimal implementation**

- Add the staff access and audit-log SQLAlchemy models.
- Register them in `src/infra/db/models/__init__.py`.
- Keep fields minimal but sufficient for staff auth, role assignment, direct permissions, and audit logging.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_database_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/infra/db/models tests/test_database_models.py
git commit -m "feat: add admin access and audit models"
```

### Task 2: Add Alembic migration for admin access tables

**Files:**
- Create: `migrations/versions/20260325_000002_add_admin_access_tables.py`
- Test: `tests/test_db_metadata_registration.py`

**Step 1: Write the failing test**

```python
def test_admin_access_tables_are_registered_in_metadata():
    from src.infra.db.base import Base

    assert "staff_users" in Base.metadata.tables
    assert "audit_logs" in Base.metadata.tables
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_db_metadata_registration.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Create the Alembic migration for the new access-control and audit-log tables.
- Keep constraints explicit for uniqueness and foreign keys.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_db_metadata_registration.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add migrations/versions/20260325_000002_add_admin_access_tables.py tests/test_db_metadata_registration.py
git commit -m "feat: add migration for admin access tables"
```

### Task 3: Add catalog database models and offering relationships

**Files:**
- Create: `src/infra/db/models/catalog_faculty.py`
- Create: `src/infra/db/models/catalog_program.py`
- Create: `src/infra/db/models/catalog_level.py`
- Create: `src/infra/db/models/catalog_semester.py`
- Create: `src/infra/db/models/catalog_course.py`
- Create: `src/infra/db/models/program_course_offering.py`
- Modify: `src/infra/db/models/__init__.py`
- Test: `tests/test_database_models.py`

**Step 1: Write the failing test**

```python
def test_program_course_offering_model_has_lookup_fields():
    from src.infra.db.models.program_course_offering import ProgramCourseOffering

    column_names = {column.name for column in ProgramCourseOffering.__table__.columns}
    assert {"program_code", "level_code", "semester_code", "course_code"} <= column_names
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_database_models.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add canonical catalog models and the offering join model.
- Make codes unique and indexed where they are lookup keys.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_database_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/infra/db/models tests/test_database_models.py
git commit -m "feat: add canonical catalog database models"
```

### Task 4: Add catalog migration and seed script from the current static dataset

**Files:**
- Create: `migrations/versions/20260325_000003_add_catalog_tables.py`
- Create: `scripts/seed_catalog.py`
- Modify: `src/domains/catalog/data.py`
- Test: `tests/test_catalog_navigation.py`

**Step 1: Write the failing test**

```python
def test_static_catalog_data_can_be_exported_for_database_seed():
    from src.domains.catalog.data import FACULTIES, PROGRAM_COURSES

    assert FACULTIES
    assert PROGRAM_COURSES
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_catalog_navigation.py -v`
Expected: FAIL once the static module is reshaped for export but not yet wired correctly.

**Step 3: Write minimal implementation**

- Add the Alembic migration for catalog tables.
- Add a seed script that reads the current static catalog dataset and inserts canonical rows into the new tables.
- Keep the static dataset only as a temporary seed source.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_catalog_navigation.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add migrations/versions/20260325_000003_add_catalog_tables.py scripts/seed_catalog.py src/domains/catalog/data.py tests/test_catalog_navigation.py
git commit -m "feat: add catalog migration and seed script"
```

### Task 5: Add repositories and services for staff permissions and audit logging

**Files:**
- Create: `src/infra/db/repositories/staff_user_repository.py`
- Create: `src/infra/db/repositories/permission_repository.py`
- Create: `src/infra/db/repositories/audit_log_repository.py`
- Create: `src/domains/admin/auth_service.py`
- Create: `src/domains/admin/permission_service.py`
- Modify: `src/infra/db/repositories/__init__.py`
- Test: `tests/test_admin_permission_service.py`

**Step 1: Write the failing test**

```python
import pytest

@pytest.mark.asyncio
async def test_super_admin_can_hold_multiple_permissions():
    from src.domains.admin.permission_service import PermissionService

    service = PermissionService(...)
    assert await service.user_has_permission(user_id=1, permission_code="staff.create") is True
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_permission_service.py -v`
Expected: FAIL because the admin permission service does not exist yet.

**Step 3: Write minimal implementation**

- Add repositories for staff users, permissions, and audit logs.
- Add a permission service that merges role-derived and direct user permissions.
- Add a minimal auth service contract for future session handling.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_permission_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/infra/db/repositories src/domains/admin tests/test_admin_permission_service.py
git commit -m "feat: add admin permission and audit services"
```

### Task 6: Add database-backed catalog repositories, service, and Redis caching

**Files:**
- Create: `src/infra/db/repositories/catalog_repository.py`
- Create: `src/domains/catalog/service.py`
- Modify: `src/domains/catalog/navigation_service.py`
- Modify: `src/infra/redis/state_store.py`
- Test: `tests/test_catalog_navigation.py`
- Test: `tests/test_interactive_state_store.py`

**Step 1: Write the failing test**

```python
def test_catalog_service_returns_courses_from_repository():
    from src.domains.catalog.service import CatalogService

    service = CatalogService(...)
    assert service is not None
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_catalog_navigation.py tests/test_interactive_state_store.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add a DB-backed catalog repository.
- Add a catalog service that caches common lookups in Redis.
- Update the existing navigation service to delegate to the new catalog service boundary.
- Add explicit cache invalidation helpers for catalog writes.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_catalog_navigation.py tests/test_interactive_state_store.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/infra/db/repositories/catalog_repository.py src/domains/catalog src/infra/redis/state_store.py tests/test_catalog_navigation.py tests/test_interactive_state_store.py
git commit -m "feat: add database-backed catalog service with redis cache"
```

### Task 7: Replace bot profile and quiz catalog reads with the DB-backed catalog service

**Files:**
- Modify: `src/bot/handlers/home.py`
- Modify: `src/bot/handlers/profile_setup.py`
- Modify: `src/app/bootstrap.py`
- Test: `tests/test_profile_setup_flow.py`
- Test: `tests/test_home_actions.py`

**Step 1: Write the failing test**

```python
import pytest

@pytest.mark.asyncio
async def test_profile_setup_uses_catalog_service_from_runtime():
    assert False, "Wire DB-backed catalog service into Telegram handlers"
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_profile_setup_flow.py tests/test_home_actions.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Inject the catalog service during app bootstrap.
- Update profile setup and home handlers to use the shared runtime service.
- Remove assumptions that catalog data lives only in static Python structures.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_profile_setup_flow.py tests/test_home_actions.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/handlers/home.py src/bot/handlers/profile_setup.py src/app/bootstrap.py tests/test_profile_setup_flow.py tests/test_home_actions.py
git commit -m "feat: wire bot catalog reads to database-backed service"
```

### Task 8: Add admin auth and permission-checked API routes in FastAPI

**Files:**
- Create: `src/api/admin_auth.py`
- Create: `src/api/admin_staff.py`
- Create: `src/api/admin_catalog.py`
- Create: `src/api/admin_questions.py`
- Create: `src/api/admin_audit.py`
- Modify: `src/main.py`
- Test: `tests/test_admin_api.py`

**Step 1: Write the failing test**

```python
import pytest

@pytest.mark.asyncio
async def test_admin_staff_endpoint_rejects_user_without_permission():
    assert False, "Add permission-checked admin routes"
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add auth/session endpoints for the admin app.
- Add permission-checked routes for staff management, catalog reads and writes, question edits, and audit views.
- Register the routers in `src/main.py`.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/api src/main.py tests/test_admin_api.py
git commit -m "feat: add admin auth and permission-checked routes"
```

### Task 9: Scaffold the Next.js admin application and shared shell

**Files:**
- Create: `admin/package.json`
- Create: `admin/next.config.ts`
- Create: `admin/tsconfig.json`
- Create: `admin/app/layout.tsx`
- Create: `admin/app/page.tsx`
- Create: `admin/app/login/page.tsx`
- Create: `admin/components/admin-shell.tsx`
- Create: `admin/lib/api.ts`
- Create: `admin/middleware.ts`
- Test: `admin/app/page.tsx`

**Step 1: Write the failing test**

```tsx
// Create a minimal smoke test or typecheck target for the admin shell.
```

**Step 2: Run test to verify it fails**

Run: `cd admin && npm run lint`
Expected: FAIL because the admin app does not exist yet.

**Step 3: Write minimal implementation**

- Scaffold the `Next.js` app.
- Add a login page and authenticated shell layout.
- Add a minimal API client for the FastAPI backend.

**Step 4: Run test to verify it passes**

Run: `cd admin && npm run lint`
Expected: PASS

**Step 5: Commit**

```bash
git add admin
git commit -m "feat: scaffold nextjs admin app"
```

### Task 10: Build the Staff & Permissions UI

**Files:**
- Create: `admin/app/staff/page.tsx`
- Create: `admin/components/staff/staff-table.tsx`
- Create: `admin/components/staff/staff-form.tsx`
- Create: `admin/components/staff/permission-matrix.tsx`
- Modify: `admin/lib/api.ts`
- Test: `admin/components/staff/staff-table.tsx`

**Step 1: Write the failing test**

```tsx
// Add a basic component test or typechecked usage example for staff table rendering.
```

**Step 2: Run test to verify it fails**

Run: `cd admin && npm run lint`
Expected: FAIL until the staff page and components exist.

**Step 3: Write minimal implementation**

- Add staff list, create-user form, activate/deactivate action, and permission assignment UI.
- Support preset roles plus direct permission toggles.

**Step 4: Run test to verify it passes**

Run: `cd admin && npm run lint`
Expected: PASS

**Step 5: Commit**

```bash
git add admin/app/staff admin/components/staff admin/lib/api.ts
git commit -m "feat: add staff and permissions admin ui"
```

### Task 11: Build the Catalog UI and invalidation flow

**Files:**
- Create: `admin/app/catalog/page.tsx`
- Create: `admin/components/catalog/catalog-tree.tsx`
- Create: `admin/components/catalog/course-offering-form.tsx`
- Modify: `admin/lib/api.ts`
- Test: `tests/test_admin_api.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_catalog_write_invalidates_cached_program_courses():
    assert False, "Invalidate Redis after catalog writes"
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add the catalog management page in the admin app.
- Complete backend catalog write endpoints with cache invalidation.
- Surface create and edit flows for faculties, programs, courses, and offerings.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add admin/app/catalog admin/components/catalog admin/lib/api.ts tests/test_admin_api.py
git commit -m "feat: add catalog management ui and cache invalidation"
```

### Task 12: Build the Question Bank and Audit Log UI

**Files:**
- Create: `admin/app/questions/page.tsx`
- Create: `admin/app/audit/page.tsx`
- Create: `admin/components/questions/question-table.tsx`
- Create: `admin/components/questions/question-editor.tsx`
- Create: `admin/components/audit/audit-log-table.tsx`
- Modify: `admin/lib/api.ts`
- Test: `tests/test_admin_api.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_question_edit_creates_audit_log_entry():
    assert False, "Audit admin content edits"
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add question listing, filtering, and editor UI.
- Add audit log UI.
- Ensure question edits create audit-log records and invalidate affected caches.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_admin_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add admin/app/questions admin/app/audit admin/components/questions admin/components/audit admin/lib/api.ts tests/test_admin_api.py
git commit -m "feat: add question bank and audit log admin ui"
```
