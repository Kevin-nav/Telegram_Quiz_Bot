# Question Bank Ingestion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a reusable ingestion pipeline that imports canonical questions from `q_and_a/*/scored_cleaned.json` into Postgres, renders LaTeX question/explanation assets to R2, and exposes a ready question bank for the adaptive quiz engine.

**Architecture:** Add canonical database tables for the question bank and runtime learning state, build an idempotent importer that validates source JSON and generates derived media only when needed, then switch quiz selection to read ready questions from Postgres instead of placeholder cache content. Keep one logical record per question; represent LaTeX presentation variants as child asset records rather than duplicate questions.

**Tech Stack:** Python, SQLAlchemy async, Postgres, boto3/Cloudflare R2, Redis, pytest, existing LaTeX rendering scripts

---

### Task 1: Define canonical question-bank database models

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\models\__init__.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\models\question_bank.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\models\question_asset_variant.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\models\student_course_state.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\models\question_attempt.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\infra\db\models\test_question_bank_models.py`

**Step 1: Write the failing test**

```python
def test_question_bank_model_exposes_algorithm_fields():
    from src.infra.db.models.question_bank import QuestionBank

    column_names = {column.name for column in QuestionBank.__table__.columns}
    assert "topic_id" in column_names
    assert "scaled_score" in column_names
    assert "has_latex" in column_names
    assert "status" in column_names
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/infra/db/models/test_question_bank_models.py -v`
Expected: FAIL because the new models do not exist yet.

**Step 3: Write minimal implementation**

- Add SQLAlchemy models for:
  - canonical logical questions
  - LaTeX asset variants
  - student adaptive state
  - question attempts
- Include fields needed by the algorithm and ingestion workflow.
- Export the new models from the DB models package.

**Step 4: Run test to verify it passes**

Run: `pytest tests/infra/db/models/test_question_bank_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/infra/db/models tests/infra/db/models
git commit -m "feat: add question bank database models"
```

### Task 2: Add migrations or schema bootstrap coverage for the new tables

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\base.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\session.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\infra\db\test_metadata_registration.py`

**Step 1: Write the failing test**

```python
def test_question_bank_tables_are_registered():
    from src.infra.db.base import Base

    table_names = set(Base.metadata.tables)
    assert "question_bank" in table_names
    assert "question_asset_variants" in table_names
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/infra/db/test_metadata_registration.py -v`
Expected: FAIL if the new models are not registered in metadata.

**Step 3: Write minimal implementation**

- Ensure model imports register the new tables.
- If the project uses explicit startup bootstrap, confirm the metadata path includes the new models.

**Step 4: Run test to verify it passes**

Run: `pytest tests/infra/db/test_metadata_registration.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/infra/db tests/infra/db
git commit -m "feat: register question bank metadata"
```

### Task 3: Build importer domain schema and validation

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\question_bank\schemas.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\question_bank\validation.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\question_bank\__init__.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\domains\question_bank\test_validation.py`

**Step 1: Write the failing test**

```python
def test_validation_rejects_correct_option_not_in_options():
    from src.domains.question_bank.schemas import ImportedQuestion
    from src.domains.question_bank.validation import validate_imported_question

    question = ImportedQuestion(
        question_text="Q",
        options=["A", "B", "C", "D"],
        correct_option_text="Z",
        short_explanation="Because",
        raw_score=2.0,
        scaled_score=2.0,
        band=2,
        has_latex=False,
        base_score=1.5,
        note_reference=1.0,
        distractor_complexity=1.0,
        processing_complexity=1.0,
        negative_stem=1.0,
        cognitive_level="Understanding",
        option_count=4,
        topic_id="topic",
        question_type="MCQ",
    )

    errors = validate_imported_question(question)
    assert any("correct_option_text" in error for error in errors)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/domains/question_bank/test_validation.py -v`
Expected: FAIL because importer schema/validator does not exist yet.

**Step 3: Write minimal implementation**

- Add importer-facing schema for rows from `scored_cleaned.json`.
- Add validators for:
  - required fields
  - option count consistency
  - correct option membership
  - supported question type
  - score/complexity ranges
- Add stable question-key generation and content checksum helpers.

**Step 4: Run test to verify it passes**

Run: `pytest tests/domains/question_bank/test_validation.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/question_bank tests/domains/question_bank
git commit -m "feat: add question bank import validation"
```

### Task 4: Extract reusable LaTeX rendering helpers

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\question_bank\latex_renderer.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\scripts\latex_iterations\iteration_13_original_font.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\scripts\latex_iterations\iteration_14_explanation.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\domains\question_bank\test_latex_renderer.py`

**Step 1: Write the failing test**

```python
def test_build_question_variants_returns_four_distinct_option_orders():
    from src.domains.question_bank.latex_renderer import build_latex_option_variants

    variants = build_latex_option_variants(["A", "B", "C", "D"])
    assert len(variants) == 4
    assert len({tuple(variant) for variant in variants}) == 4
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/domains/question_bank/test_latex_renderer.py -v`
Expected: FAIL because the helper does not exist yet.

**Step 3: Write minimal implementation**

- Extract reusable rendering/template helpers from the iteration scripts.
- Add deterministic generation of four option arrangements.
- Add shared explanation rendering that uses `correct_option_text` instead of option letters.
- Keep the iteration scripts usable as manual test harnesses if needed.

**Step 4: Run test to verify it passes**

Run: `pytest tests/domains/question_bank/test_latex_renderer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/question_bank scripts/latex_iterations tests/domains/question_bank
git commit -m "feat: extract reusable latex rendering helpers"
```

### Task 5: Add question-bank repositories for canonical questions and variants

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\repositories\question_bank_repository.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\db\repositories\__init__.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\infra\db\repositories\test_question_bank_repository.py`

**Step 1: Write the failing test**

```python
def test_upsert_question_bank_returns_existing_row_for_same_question_key():
    assert False, "Implement repository upsert coverage"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/infra/db/repositories/test_question_bank_repository.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add repository methods for:
  - upsert canonical question rows
  - replace variant rows for a question
  - list ready questions by course
  - update status/checksum fields

**Step 4: Run test to verify it passes**

Run: `pytest tests/infra/db/repositories/test_question_bank_repository.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/infra/db/repositories tests/infra/db/repositories
git commit -m "feat: add question bank repositories"
```

### Task 6: Integrate R2 upload for question and explanation assets

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\r2\storage.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\question_bank\asset_service.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\domains\question_bank\test_asset_service.py`

**Step 1: Write the failing test**

```python
def test_asset_service_builds_versioned_r2_keys():
    from src.domains.question_bank.asset_service import build_question_asset_key

    key = build_question_asset_key(
        course_slug="differential-equations",
        question_key="q-001",
        version="abc123",
        asset_name="question_variant_0.png",
    )
    assert key == "questions/differential-equations/q-001/abc123/question_variant_0.png"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/domains/question_bank/test_asset_service.py -v`
Expected: FAIL because the service does not exist yet.

**Step 3: Write minimal implementation**

- Add helpers to build stable R2 object keys.
- Add upload methods for question variants and explanation images.
- Return both object key and public URL.

**Step 4: Run test to verify it passes**

Run: `pytest tests/domains/question_bank/test_asset_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/question_bank src/infra/r2 tests/domains/question_bank
git commit -m "feat: add question asset upload service"
```

### Task 7: Build the course importer application service

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\question_bank\import_service.py`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\question_bank\reporting.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\domains\question_bank\test_import_service.py`

**Step 1: Write the failing test**

```python
def test_import_service_continues_after_one_question_fails_validation():
    assert False, "Implement import continuation coverage"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/domains/question_bank/test_import_service.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add course-level import orchestration:
  - discover rows
  - normalize and validate
  - upsert canonical row
  - render/upload LaTeX assets when required
  - mark question ready/error
  - emit per-question and per-course report data
- Ensure retries and unchanged rows are handled idempotently.

**Step 4: Run test to verify it passes**

Run: `pytest tests/domains/question_bank/test_import_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/question_bank tests/domains/question_bank
git commit -m "feat: add question bank import service"
```

### Task 8: Add operator entrypoints for importing one course or all courses

**Files:**
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\scripts\import_question_bank.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\scripts\test_import_question_bank.py`

**Step 1: Write the failing test**

```python
def test_import_script_skips_courses_without_scored_cleaned_json():
    assert False, "Implement import script discovery coverage"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/scripts/test_import_question_bank.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add a script or CLI entrypoint that:
  - imports one named course
  - imports all discovered courses
  - skips missing `scored_cleaned.json` files
  - prints a report summary with success/error counts

**Step 4: Run test to verify it passes**

Run: `pytest tests/scripts/test_import_question_bank.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/import_question_bank.py tests/scripts
git commit -m "feat: add question bank import command"
```

### Task 9: Expand runtime quiz models to serve canonical questions

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\quiz\models.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\domains\quiz\test_models.py`

**Step 1: Write the failing test**

```python
def test_quiz_question_supports_runtime_arrangement_metadata():
    from src.domains.quiz.models import QuizQuestion

    question = QuizQuestion(
        question_id="q1",
        prompt="Q",
        options=["A", "B", "C", "D"],
        correct_option_id=0,
        explanation="E",
        arrangement_hash="A-B-C-D",
    )

    assert question.arrangement_hash == "A-B-C-D"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/domains/quiz/test_models.py -v`
Expected: FAIL because the model does not support arrangement metadata yet.

**Step 3: Write minimal implementation**

- Expand the runtime quiz model to carry:
  - canonical question metadata needed at presentation time
  - non-LaTeX `arrangement_hash`
  - LaTeX `config_index`
  - asset URLs when applicable

**Step 4: Run test to verify it passes**

Run: `pytest tests/domains/quiz/test_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/quiz/models.py tests/domains/quiz
git commit -m "feat: expand quiz runtime question model"
```

### Task 10: Replace placeholder question selection with Postgres-backed ready questions

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\quiz\service.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\infra\redis\state_store.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\domains\quiz\test_service.py`

**Step 1: Write the failing test**

```python
async def test_select_questions_reads_ready_question_bank_before_placeholder():
    assert False, "Implement service selection coverage"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/domains/quiz/test_service.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Replace placeholder fallback with Postgres-backed loading.
- Cache ready questions in Redis after loading from Postgres.
- Keep the placeholder path only as an explicit temporary fallback if absolutely necessary.

**Step 4: Run test to verify it passes**

Run: `pytest tests/domains/quiz/test_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/quiz src/infra/redis tests/domains/quiz
git commit -m "feat: load quiz questions from canonical question bank"
```

### Task 11: Persist attempt fields required by the adaptive algorithm

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\quiz\service.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\tasks\arq_client.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\workers\background_jobs.py`
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\workers\test_background_jobs.py`

**Step 1: Write the failing test**

```python
def test_persisted_attempt_includes_arrangement_hash_or_config_index():
    assert False, "Implement adaptive attempt payload coverage"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/workers/test_background_jobs.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Extend attempt payloads to include:
  - `arrangement_hash` for non-LaTeX
  - `config_index` for LaTeX
  - selected option identifiers
  - correctness
  - course/question identifiers
- Persist them into the canonical attempt table.

**Step 4: Run test to verify it passes**

Run: `pytest tests/workers/test_background_jobs.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/domains/quiz src/tasks src/workers tests/workers
git commit -m "feat: persist adaptive question attempt metadata"
```

### Task 12: Document operator workflow and validation expectations

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\README.md`
- Create: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\docs\question_bank_import.md`

**Step 1: Write the failing test**

There may be no automated test for operator documentation. Use a manual acceptance checklist instead.

**Step 2: Run manual verification**

Run:
- verify the README points operators to the import command
- verify the new document explains:
  - JSON intake location
  - LaTeX asset generation
  - R2 requirements
  - re-import behavior
  - ready/error statuses

Expected: the workflow is documented end-to-end.

**Step 3: Write minimal implementation**

- Add operator documentation for importing a course and understanding error reports.

**Step 4: Re-run manual verification**

Expected: documentation is complete and accurate.

**Step 5: Commit**

```bash
git add README.md docs/question_bank_import.md
git commit -m "docs: add question bank import workflow"
```
