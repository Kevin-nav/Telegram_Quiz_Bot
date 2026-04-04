# Timetable Shared Course Mapping Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand shared course availability from the timetable and generate a faculty/programme/course markdown reference.

**Architecture:** Add timetable-derived shared course mappings to the static catalog seed, reseed the DB, and generate markdown documentation from the updated in-code catalog. Keep only courses with existing question-bank slugs active in bot course pickers.

**Tech Stack:** Python, SQLAlchemy, openpyxl, existing catalog seed scripts.

---

### Task 1: Add Timetable-Derived Shared Course Offerings

**Files:**
- Modify: `src/domains/catalog/data.py`
- Modify: `scripts/seed_catalog.py`

**Steps:**
1. Add a class-prefix to programme-code map for timetable prefixes that already exist in the catalog.
2. Add normalized timetable course aliases for imported question-bank slugs.
3. Expand Level 100/200 first-semester offerings for imported courses to every mapped programme that takes them.
4. Run `venv\Scripts\python.exe scripts\seed_catalog.py`.

### Task 2: Generate Markdown Catalog Reference

**Files:**
- Create: `scripts/export_catalog_markdown.py`
- Create: `docs/academic_catalog_from_timetable.md`

**Steps:**
1. Build markdown from `build_catalog_seed_payload()` grouped by faculty, programme, level, and semester.
2. Include a section for timetable prefixes that are not yet mapped into the catalog.
3. Save the generated markdown file under `docs/`.

### Task 3: Verify Bot-Relevant Offerings and Tests

**Files:**
- Modify tests only if existing assertions need the updated Engineering course list.

**Steps:**
1. Query representative shared courses in Postgres and confirm programme coverage.
2. Run `venv\Scripts\python.exe -m pytest tests\test_catalog_navigation.py tests\test_profile_setup_flow.py tests\test_home_actions.py -q`.
