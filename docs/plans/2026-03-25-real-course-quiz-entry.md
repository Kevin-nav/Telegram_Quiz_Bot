# Real Course Quiz Entry Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace placeholder-based quiz entry with a real course picker that uses the user's study profile, starts only from canonical question-bank content, and clearly handles empty courses.

**Architecture:** Keep quiz-entry UX in Telegram handlers and keyboards, not in `QuizSessionService`. The home flow should read the saved study profile, show only matching catalog courses, collect the user's course and quiz length choices, and then call the quiz service only if canonical ready questions exist. The adaptive selector remains the source of question choice and keeps its existing cold-start behavior for new users.

**Tech Stack:** python-telegram-bot, Python, pytest, Redis-backed profile/session state, question-bank repository, adaptive selector

---

### Task 1: Add quiz course-picker callbacks and keyboard helpers

**Files:**
- Modify: `src/bot/callbacks.py`
- Modify: `src/bot/keyboards.py`
- Test: `tests/test_keyboards.py`

**Step 1: Write the failing test**

```python
def test_quiz_course_callback_is_namespaced():
    assert quiz_course_callback("linear-electronics") == "quiz:course:linear-electronics"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_keyboards.py -v`
Expected: FAIL because the callback helper does not exist yet.

**Step 3: Write minimal implementation**

- Add a `quiz_course_callback(course_code)` helper.
- Add a keyboard builder that renders course choices plus a back action to home.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_keyboards.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/callbacks.py src/bot/keyboards.py tests/test_keyboards.py
git commit -m "feat: add quiz course picker callbacks"
```

### Task 2: Add profile-scoped course-picker flow in the home handler

**Files:**
- Modify: `src/bot/handlers/home.py`
- Modify: `src/bot/copy.py`
- Test: `tests/test_home_actions.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_start_quiz_from_home_shows_profile_courses():
    assert False, "Implement real course picker from the study profile"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_home_actions.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Replace the immediate quiz-length prompt on `home:start_quiz`.
- Load profile-scoped courses from the catalog using the saved faculty/program/level/semester.
- If the profile is incomplete, reuse the existing study-setup redirection pattern.
- If the profile has no matching courses, show a clear message instead of starting a quiz.
- Render the available courses as inline buttons.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_home_actions.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/handlers/home.py src/bot/copy.py tests/test_home_actions.py
git commit -m "feat: add profile-scoped quiz course picker"
```

### Task 3: Add selected-course quiz length flow

**Files:**
- Modify: `src/bot/handlers/home.py`
- Test: `tests/test_home_actions.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_selecting_quiz_course_prompts_for_length():
    assert False, "Implement quiz course selection callback"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_home_actions.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Handle `quiz:course:<course_code>` callbacks.
- Persist the selected course in `context.user_data`.
- Show the quiz-length keyboard for the chosen course.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_home_actions.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/handlers/home.py tests/test_home_actions.py
git commit -m "feat: add quiz course selection flow"
```

### Task 4: Remove placeholder fallback from live quiz startup

**Files:**
- Modify: `src/domains/quiz/service.py`
- Test: `tests/test_quiz_session_service.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_start_quiz_raises_when_no_canonical_questions_exist():
    assert False, "Remove placeholder fallback from real quiz startup"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_quiz_session_service.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Change live selection so it returns only canonical questions.
- Raise a domain-level error when no canonical ready questions are available.
- Keep malformed canonical rows skipped, but do not backfill with placeholders.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_quiz_session_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/quiz/service.py tests/test_quiz_session_service.py
git commit -m "feat: require canonical questions for live quizzes"
```

### Task 5: Handle empty-course messaging before quiz start

**Files:**
- Modify: `src/bot/handlers/home.py`
- Modify: `src/bot/copy.py`
- Test: `tests/test_home_actions.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_starting_selected_course_without_questions_shows_empty_message():
    assert False, "Implement empty-course handling"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_home_actions.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Catch the no-canonical-question condition in the home handler.
- Show a clear user-facing message such as “No questions are available for this course yet.”
- Do not create a quiz session in that case.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_home_actions.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/handlers/home.py src/bot/copy.py tests/test_home_actions.py
git commit -m "feat: handle empty quiz courses gracefully"
```

### Task 6: Add real-course start coverage for the quiz handler path

**Files:**
- Modify: `tests/test_home_actions.py`
- Modify: `tests/test_quiz_session_service.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_selected_profile_course_starts_real_quiz():
    assert False, "Cover end-to-end handler handoff for real quiz entry"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_home_actions.py tests/test_quiz_session_service.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add coverage that the chosen catalog course is passed through to `QuizSessionService`.
- Assert no placeholder question creation path is used in the live flow.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_home_actions.py tests/test_quiz_session_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_home_actions.py tests/test_quiz_session_service.py
git commit -m "test: cover real course quiz entry flow"
```
