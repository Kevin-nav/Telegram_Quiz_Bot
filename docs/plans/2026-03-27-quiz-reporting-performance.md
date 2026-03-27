# Quiz Reporting And Performance Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build two-stage quiz question reporting, real learner performance summaries, and richer end-of-quiz scoring/results UI for `@Adarkwa_Study_Bot`.

**Architecture:** Extend the existing Telegram poll quiz flow with companion inline action messages and short-lived Redis-backed report state, persist reports into a new SQL table, and compute learner-facing performance/result summaries from existing `question_attempts` data plus course progress state.

**Tech Stack:** Python, python-telegram-bot, SQLAlchemy, Alembic, Redis, pytest

---

### Task 1: Add Question Report Persistence

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\models\question_report.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\repositories\question_report_repository.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\models\__init__.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\migrations\versions\20260327_000001_add_question_reports.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_question_report_repository.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_database_models.py`

**Step 1: Write the failing repository/model tests**

Add tests that:
- create a report row with `report_scope`, `report_reason`, and optional `report_note`
- verify persisted metadata fields round-trip
- verify the new model is registered in metadata

**Step 2: Run the targeted tests to verify failure**

Run:
```powershell
pytest tests/test_question_report_repository.py tests/test_database_models.py -v
```

Expected:
- FAIL because `QuestionReport` model and repository do not exist yet

**Step 3: Write the minimal model, repository, and migration**

Implement:
- SQLAlchemy model with indexed query fields and JSON metadata
- repository insert method
- Alembic migration creating `question_reports`
- metadata registration export

**Step 4: Run the targeted tests to verify pass**

Run:
```powershell
pytest tests/test_question_report_repository.py tests/test_database_models.py -v
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add src/infra/db/models/question_report.py src/infra/db/repositories/question_report_repository.py src/infra/db/models/__init__.py migrations/versions/20260327_000001_add_question_reports.py tests/test_question_report_repository.py tests/test_database_models.py
git commit -m "feat: add question report persistence"
```

### Task 2: Add Redis Report Interaction State

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\redis\keys.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\redis\state_store.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\quiz\models.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_interactive_state_store.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_quiz_models.py`

**Step 1: Write the failing state tests**

Add tests for:
- saving/loading pending report draft state
- saving/loading pending note capture state
- serializing extra quiz session fields for action message ids and recent answered question context

**Step 2: Run the targeted tests to verify failure**

Run:
```powershell
pytest tests/test_interactive_state_store.py tests/test_quiz_models.py -v
```

Expected:
- FAIL because the new keys/state methods and quiz model fields do not exist

**Step 3: Implement Redis keys and state helpers**

Add:
- report draft key helpers
- note-waiting state helpers
- new serializable session fields for question and answer action messages plus last answered question context

**Step 4: Run the targeted tests to verify pass**

Run:
```powershell
pytest tests/test_interactive_state_store.py tests/test_quiz_models.py -v
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add src/infra/redis/keys.py src/infra/redis/state_store.py src/domains/quiz/models.py tests/test_interactive_state_store.py tests/test_quiz_models.py
git commit -m "feat: add report interaction state"
```

### Task 3: Build Question Report Service And Background Job

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\quiz_reporting\__init__.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\quiz_reporting\service.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\tasks\arq_client.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\workers\background_jobs.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\tasks\worker.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_quiz_reporting_service.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_background_jobs.py`

**Step 1: Write the failing service/job tests**

Add tests that:
- validate allowed reasons for `question` scope and `answer` scope
- build payloads from quiz session context
- persist report rows through a background job handler

**Step 2: Run the targeted tests to verify failure**

Run:
```powershell
pytest tests/test_quiz_reporting_service.py tests/test_background_jobs.py -v
```

Expected:
- FAIL because the service, enqueue helper, and background job do not exist

**Step 3: Implement the service and worker wiring**

Add:
- allowed reason maps
- payload builders from current question / last answered question context
- enqueue helper and worker handler for report persistence

**Step 4: Run the targeted tests to verify pass**

Run:
```powershell
pytest tests/test_quiz_reporting_service.py tests/test_background_jobs.py -v
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add src/domains/quiz_reporting src/tasks/arq_client.py src/workers/background_jobs.py src/tasks/worker.py tests/test_quiz_reporting_service.py tests/test_background_jobs.py
git commit -m "feat: add quiz report service"
```

### Task 4: Add Report Callbacks, Keyboards, And Message Capture Flow

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\bot\callbacks.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\bot\keyboards.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\bot\application.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\bot\handlers\reporting.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\bot\copy.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_keyboards.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_reporting_flow.py`

**Step 1: Write the failing callback and flow tests**

Add tests for:
- question-report keyboard
- answer-report keyboard
- reason selection flow
- skip-note flow
- stale callback rejection
- note capture from the next text message

**Step 2: Run the targeted tests to verify failure**

Run:
```powershell
pytest tests/test_keyboards.py tests/test_reporting_flow.py -v
```

Expected:
- FAIL because report callbacks, keyboards, handlers, and copy do not exist

**Step 3: Implement the reporting handlers and bot wiring**

Add:
- callback builders/parsers for `report:*`
- inline keyboards for scope-specific reasons
- callback handler for choosing a reason and skip/cancel actions
- message handler that consumes the next text note when note capture is pending
- user-facing confirmation and retry copy

**Step 4: Run the targeted tests to verify pass**

Run:
```powershell
pytest tests/test_keyboards.py tests/test_reporting_flow.py -v
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add src/bot/callbacks.py src/bot/keyboards.py src/bot/application.py src/bot/handlers/reporting.py src/bot/copy.py tests/test_keyboards.py tests/test_reporting_flow.py
git commit -m "feat: add quiz reporting telegram flow"
```

### Task 5: Extend Quiz Session Flow With Action Messages And Rich Results

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\quiz\service.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\quiz\models.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\bot\handlers\quiz.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\bot\copy.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_quiz_session_service.py`

**Step 1: Write the failing quiz session tests**

Add tests for:
- sending a question action message after the poll
- sending an answer action message after feedback
- storing last answered question context for answer reports
- richer completion summary content with percentage, pace, and topic callouts

**Step 2: Run the targeted tests to verify failure**

Run:
```powershell
pytest tests/test_quiz_session_service.py -v
```

Expected:
- FAIL because the new action messages and richer summary builder are not implemented

**Step 3: Implement the quiz flow changes**

Add:
- companion message send/edit behavior for question and answer actions
- last answered question tracking
- summary builder that computes session percentage, average time, topic strengths, and recommendation

**Step 4: Run the targeted tests to verify pass**

Run:
```powershell
pytest tests/test_quiz_session_service.py -v
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add src/domains/quiz/service.py src/domains/quiz/models.py src/bot/handlers/quiz.py src/bot/copy.py tests/test_quiz_session_service.py
git commit -m "feat: improve quiz actions and end summaries"
```

### Task 6: Build Learner Performance Service And Replace Placeholder UI

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\performance\__init__.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\performance\service.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\repositories\question_attempt_repository.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\bot\handlers\home.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\bot\handlers\commands.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\bot\application.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\bot\copy.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_performance_service.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_home_actions.py`

**Step 1: Write the failing performance tests**

Add tests that:
- aggregate learner stats from attempts
- produce minimal summaries for sparse histories
- replace the home and `/performance` placeholder output with real summary copy

**Step 2: Run the targeted tests to verify failure**

Run:
```powershell
pytest tests/test_performance_service.py tests/test_home_actions.py -v
```

Expected:
- FAIL because the service and real performance rendering do not exist

**Step 3: Implement the performance service and UI integration**

Add:
- repository queries or grouping helpers for learner attempts
- performance summary calculation
- home flow and `/performance` command rendering using the new service

**Step 4: Run the targeted tests to verify pass**

Run:
```powershell
pytest tests/test_performance_service.py tests/test_home_actions.py -v
```

Expected:
- PASS

**Step 5: Commit**

```powershell
git add src/domains/performance src/infra/db/repositories/question_attempt_repository.py src/bot/handlers/home.py src/bot/handlers/commands.py src/bot/application.py src/bot/copy.py tests/test_performance_service.py tests/test_home_actions.py
git commit -m "feat: add learner performance summaries"
```

### Task 7: Run End-To-End Verification

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_telegram_dispatcher.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_worker.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_telegram_dispatcher.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_worker.py`

**Step 1: Write the failing integration tests**

Add coverage for:
- callback dispatch to report handlers
- text-message note capture routing
- worker registration for report persistence

**Step 2: Run the targeted tests to verify failure**

Run:
```powershell
pytest tests/test_telegram_dispatcher.py tests/test_worker.py -v
```

Expected:
- FAIL until the full flow is wired through

**Step 3: Implement any missing integration wiring**

Fix any missing handler registrations, imports, or worker bindings discovered by the tests.

**Step 4: Run the focused suite and then the broader safety suite**

Run:
```powershell
pytest tests/test_question_report_repository.py tests/test_quiz_reporting_service.py tests/test_reporting_flow.py tests/test_quiz_session_service.py tests/test_performance_service.py tests/test_home_actions.py tests/test_background_jobs.py tests/test_worker.py tests/test_telegram_dispatcher.py -v
```

Expected:
- PASS

Then run:
```powershell
pytest -q
```

Expected:
- PASS, or capture any unrelated pre-existing failures separately

**Step 5: Commit**

```powershell
git add tests/test_telegram_dispatcher.py tests/test_worker.py
git commit -m "test: verify reporting and performance flow"
```
