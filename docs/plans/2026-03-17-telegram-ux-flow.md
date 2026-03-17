# Telegram UX Flow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first real Telegram user experience for `@Adarkwa_Study_Bot`, centered on a study home screen, one-time academic profile setup, and fast quiz entry using saved study context.

**Architecture:** Keep Telegram handlers thin and move UX decisions into focused services for profile navigation, home rendering, and quiz entry. Persist durable academic profile and quiz state in Neon, use Redis only for short-lived interaction state, and preserve the modular monolith structure introduced in the launch-foundation work.

**Tech Stack:** Python, python-telegram-bot, FastAPI webhook runtime, SQLAlchemy async, Redis, Neon Postgres, pytest

---

### Task 1: Add User Academic Profile Fields To The Schema And Models

**Files:**
- Modify: `Adarkwa_Study_Bot/src/infra/db/models/user.py`
- Modify: `Adarkwa_Study_Bot/src/database.py`
- Create: `Adarkwa_Study_Bot/migrations/versions/20260317_000001_add_user_study_profile.py`
- Create: `Adarkwa_Study_Bot/tests/test_user_profile_model.py`

**Step 1: Write the failing test**

```python
def test_user_model_has_study_profile_columns():
    from src.infra.db.models.user import User

    columns = {column.name for column in User.__table__.columns}
    assert {
        "faculty_code",
        "program_code",
        "level_code",
        "semester_code",
        "preferred_course_code",
        "onboarding_completed",
    } <= columns
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_user_profile_model.py -v`

Expected: FAIL because the study profile columns do not exist yet.

**Step 3: Write minimal implementation**

- Add the study profile columns to `User`.
- Keep the values simple and explicit with string codes for the first UX slice.
- Add an Alembic migration for the new columns.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_user_profile_model.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/infra/db/models/user.py src/database.py migrations/versions/20260317_000001_add_user_study_profile.py tests/test_user_profile_model.py
git commit -m "feat: add user study profile fields"
```

### Task 2: Introduce Static Academic Catalog And Navigation Service

**Files:**
- Create: `Adarkwa_Study_Bot/src/domains/catalog/__init__.py`
- Create: `Adarkwa_Study_Bot/src/domains/catalog/data.py`
- Create: `Adarkwa_Study_Bot/src/domains/catalog/navigation_service.py`
- Create: `Adarkwa_Study_Bot/tests/test_catalog_navigation.py`
- Reference: `Adarkwa_Study_Bot/docs/academic_structure.md`

**Step 1: Write the failing test**

```python
def test_first_semester_catalog_returns_program_courses():
    from src.domains.catalog.navigation_service import CatalogNavigationService

    service = CatalogNavigationService()
    courses = service.get_courses(
        faculty_code="engineering",
        program_code="mechanical-engineering",
        level_code="100",
        semester_code="first",
    )
    assert courses
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_catalog_navigation.py -v`

Expected: FAIL because the catalog service does not exist.

**Step 3: Write minimal implementation**

- Encode the current faculty/program structure in a dedicated catalog data module.
- Use first semester as the active seeded semester.
- Expose lookup methods for faculties, programs, levels, semesters, and courses.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_catalog_navigation.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/domains/catalog tests/test_catalog_navigation.py
git commit -m "feat: add academic catalog navigation service"
```

### Task 3: Add Profile Service For Persistent Study Context

**Files:**
- Create: `Adarkwa_Study_Bot/src/domains/profile/__init__.py`
- Create: `Adarkwa_Study_Bot/src/domains/profile/service.py`
- Create: `Adarkwa_Study_Bot/tests/test_profile_service.py`

**Step 1: Write the failing test**

```python
import pytest


@pytest.mark.asyncio
async def test_profile_service_marks_onboarding_complete():
    ...
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_profile_service.py -v`

Expected: FAIL because the profile service does not exist.

**Step 3: Write minimal implementation**

- Create a profile service that can:
  - load or initialize a Telegram user profile
  - update faculty/program/level/semester/course
  - mark onboarding complete
- Keep it independent from Telegram handler code.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_profile_service.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/domains/profile tests/test_profile_service.py
git commit -m "feat: add profile persistence service"
```

### Task 4: Build Home Screen Service And Button Contract

**Files:**
- Create: `Adarkwa_Study_Bot/src/domains/home/__init__.py`
- Create: `Adarkwa_Study_Bot/src/domains/home/service.py`
- Create: `Adarkwa_Study_Bot/tests/test_home_service.py`

**Step 1: Write the failing test**

```python
def test_home_service_includes_continue_when_active_quiz_exists():
    ...
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_home_service.py -v`

Expected: FAIL because the home service does not exist.

**Step 3: Write minimal implementation**

- Build a service that returns:
  - home message text
  - button definitions
  - visibility rules for `Continue Quiz`
- Keep callback data namespaced.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_home_service.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/domains/home tests/test_home_service.py
git commit -m "feat: add home screen service"
```

### Task 5: Create Telegram Callback Schema And Menu Builders

**Files:**
- Create: `Adarkwa_Study_Bot/src/bot/callbacks.py`
- Create: `Adarkwa_Study_Bot/src/bot/keyboards.py`
- Create: `Adarkwa_Study_Bot/tests/test_keyboards.py`

**Step 1: Write the failing test**

```python
def test_profile_course_callback_is_namespaced():
    from src.bot.callbacks import profile_course_callback

    assert profile_course_callback("calc-101") == "profile:course:calc-101"
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_keyboards.py -v`

Expected: FAIL because the callback helpers do not exist.

**Step 3: Write minimal implementation**

- Centralize callback creation/parsing helpers.
- Add keyboard builders for:
  - welcome screen
  - setup drill-down
  - home screen
  - quiz length picker

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_keyboards.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/bot/callbacks.py src/bot/keyboards.py tests/test_keyboards.py
git commit -m "feat: add telegram callback and keyboard builders"
```

### Task 6: Implement `/start` Routing And Welcome/Home Flow

**Files:**
- Modify: `Adarkwa_Study_Bot/src/bot/application.py`
- Create: `Adarkwa_Study_Bot/src/bot/handlers/start.py`
- Create: `Adarkwa_Study_Bot/tests/test_start_flow.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_start_routes_new_user_to_setup():
    ...
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_start_flow.py -v`

Expected: FAIL because `/start` still only sends a static welcome message.

**Step 3: Write minimal implementation**

- Move `/start` into a dedicated handler module.
- Route to:
  - welcome/setup for incomplete users
  - home for returning users
- Keep analytics tracking intact.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_start_flow.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/bot/application.py src/bot/handlers/start.py tests/test_start_flow.py
git commit -m "feat: route start command into welcome and home flow"
```

### Task 7: Implement Profile Setup Drill-Down Flow

**Files:**
- Create: `Adarkwa_Study_Bot/src/bot/handlers/profile_setup.py`
- Modify: `Adarkwa_Study_Bot/src/bot/application.py`
- Create: `Adarkwa_Study_Bot/tests/test_profile_setup_flow.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_profile_setup_advances_from_faculty_to_program():
    ...
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_profile_setup_flow.py -v`

Expected: FAIL because the setup callback flow does not exist.

**Step 3: Write minimal implementation**

- Add callback handlers for:
  - faculty
  - program
  - level
  - semester
  - course
  - back
  - cancel
- Persist final selection via the profile service.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_profile_setup_flow.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/bot/handlers/profile_setup.py src/bot/application.py tests/test_profile_setup_flow.py
git commit -m "feat: add study profile setup flow"
```

### Task 8: Implement Home Actions And Quiz Entry Flow

**Files:**
- Create: `Adarkwa_Study_Bot/src/domains/quiz_entry/__init__.py`
- Create: `Adarkwa_Study_Bot/src/domains/quiz_entry/service.py`
- Create: `Adarkwa_Study_Bot/src/bot/handlers/home.py`
- Modify: `Adarkwa_Study_Bot/src/bot/application.py`
- Create: `Adarkwa_Study_Bot/tests/test_home_actions.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_start_quiz_from_home_prompts_for_length():
    ...
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_home_actions.py -v`

Expected: FAIL because home actions and quiz entry callbacks do not exist.

**Step 3: Write minimal implementation**

- Handle:
  - `Start Quiz`
  - `Continue Quiz`
  - `Change Course`
  - `Help`
  - `Performance`
- For this slice, `Start Quiz` should ask only for question count if course context already exists.
- Allow placeholder responses for unfinished quiz/performance logic if needed, but keep the flow contract stable.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_home_actions.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/domains/quiz_entry src/bot/handlers/home.py src/bot/application.py tests/test_home_actions.py
git commit -m "feat: add study home actions and quiz entry flow"
```

### Task 9: Add Copy, Help, And Performance Placeholder UX

**Files:**
- Create: `Adarkwa_Study_Bot/src/bot/copy.py`
- Modify: `Adarkwa_Study_Bot/src/bot/handlers/start.py`
- Modify: `Adarkwa_Study_Bot/src/bot/handlers/home.py`
- Create: `Adarkwa_Study_Bot/tests/test_bot_copy.py`

**Step 1: Write the failing test**

```python
def test_home_copy_mentions_current_course():
    ...
```

**Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_bot_copy.py -v`

Expected: FAIL because copy generation is still inline and not reusable.

**Step 3: Write minimal implementation**

- Centralize welcome/home/help/result copy.
- Keep messages short and Telegram-friendly.
- Make sure home copy references current course and semester when available.

**Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_bot_copy.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/bot/copy.py src/bot/handlers/start.py src/bot/handlers/home.py tests/test_bot_copy.py
git commit -m "feat: refine bot ux copy and placeholders"
```

### Task 10: Update Docs And Run Final Verification

**Files:**
- Modify: `Adarkwa_Study_Bot/README.md`
- Modify: `Adarkwa_Study_Bot/docs/architecture_plan.md`
- Modify: `Adarkwa_Study_Bot/docs/plans/2026-03-17-telegram-ux-flow-design.md`
- Modify as needed: files from prior tasks

**Step 1: Run focused tests**

Run:

```bash
venv\Scripts\python.exe -m pytest tests/test_user_profile_model.py tests/test_catalog_navigation.py tests/test_profile_service.py tests/test_home_service.py tests/test_keyboards.py tests/test_start_flow.py tests/test_profile_setup_flow.py tests/test_home_actions.py tests/test_bot_copy.py -v
```

Expected: PASS.

**Step 2: Run the full suite**

Run:

```bash
venv\Scripts\python.exe -m pytest tests -q
```

Expected: PASS.

**Step 3: Manual verification**

Run:

```bash
uvicorn src.main:app --reload
```

Verify manually in Telegram:

- `/start` routes a new user into setup
- completing setup lands on home
- returning `/start` lands on home directly
- `Change Course` reopens the academic drill-down
- `Start Quiz` asks for question count and uses saved course context

**Step 4: Commit**

```bash
git add README.md docs/architecture_plan.md docs/plans/2026-03-17-telegram-ux-flow-design.md src tests migrations
git commit -m "feat: add telegram study home ux flow"
```

## Notes

- Use first semester as the active seeded semester in this slice, but model semester explicitly so second semester can be added later without a handler rewrite.
- Do not start redesigning the adaptive engine during this work; the goal is UX entry and navigation, not question selection sophistication.
- The repo currently contains unrelated untracked script files. Leave them untouched unless the user explicitly includes them in scope.
