# Poll-Limit LaTeX Promotion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Promote oversized Telegram poll questions/options to LaTeX during import and reprocess existing non-LaTeX rows safely.

**Architecture:** Apply poll-length promotion in the question-bank import service before checksum generation, then rely on the existing checksum/upsert flow to regenerate assets for changed rows. Generalize LaTeX option variant generation for non-4-option rows while preserving the current 4-option permutations.

**Tech Stack:** Python, SQLAlchemy async repositories, pytest.

---

### Task 1: Add Oversized Poll Promotion Tests

**Files:**
- Modify: `tests/test_question_bank_import_service.py`

**Step 1: Write failing tests**
- Add one test proving a non-LaTeX row with a >300-character question is imported as `has_latex=True` with variants generated.
- Add one test proving an existing ready non-LaTeX row is re-upserted when an option now exceeds 100 characters.

**Step 2: Run tests and verify they fail**
- Run: `.\\venv\\Scripts\\python.exe -m pytest tests/test_question_bank_import_service.py -q`
- Expected: the new tests fail because no promotion rule exists yet.

### Task 2: Implement Promotion Logic

**Files:**
- Modify: `src/domains/question_bank/import_service.py`

**Step 1: Add a small helper**
- Introduce Telegram poll text limits as constants and one helper that mutates `question.has_latex` when the question/options exceed those limits.

**Step 2: Apply the helper before key/checksum generation**
- Ensure `build_question_source_checksum(question)` sees the promoted `has_latex=True` value.

**Step 3: Run import-service tests**
- Run: `.\\venv\\Scripts\\python.exe -m pytest tests/test_question_bank_import_service.py -q`
- Expected: all tests pass except any renderer limitation on non-4-option promoted rows.

### Task 3: Support Non-4-Option LaTeX Variants

**Files:**
- Modify: `src/domains/question_bank/latex_renderer.py`
- Modify: `tests/test_question_bank_latex_renderer.py`

**Step 1: Write renderer tests**
- Add tests for 2-option and 5-option variant generation.
- Keep one test asserting the 4-option behavior remains unchanged.

**Step 2: Implement generic fallback permutations**
- Preserve `VARIANT_ORDERS` for 4 options.
- For any other positive option count, generate one cyclic rotation per option index for both rendered variants and option-order maps.

**Step 3: Run renderer tests**
- Run: `.\\venv\\Scripts\\python.exe -m pytest tests/test_question_bank_latex_renderer.py -q`
- Expected: all renderer tests pass.

### Task 4: Run Focused Regression Tests

**Files:**
- Modify: none

**Step 1: Run the relevant test slice**
- Run: `.\\venv\\Scripts\\python.exe -m pytest tests/test_question_bank_import_service.py tests/test_question_bank_latex_renderer.py -q`

**Step 2: Verify the importer can rewrite an existing course**
- Re-run one course import and confirm oversized questions become LaTeX.
