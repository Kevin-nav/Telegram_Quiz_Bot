# Question Bank Ingestion And Asset Pipeline Design

## Goal

Define a reusable workflow for importing course question banks from `q_and_a/*/scored_cleaned.json` into Postgres, generating LaTeX-derived media for image questions, storing those assets in Cloudflare R2, and serving question data in a shape that matches the adaptive learning algorithm.

## Current Context

- The source of truth before upload is the per-course `scored_cleaned.json` file under `q_and_a/`.
- `general-psychology` does not currently have a `scored_cleaned.json` file and is out of scope for the first pass.
- The adaptive selector expects rich question metadata including `scaled_score`, `band`, `topic_id`, `cognitive_level`, `processing_complexity`, `distractor_complexity`, `note_reference`, `question_type`, and `option_count`.
- The current runtime `QuizQuestion` model is still placeholder-oriented and does not persist a production question bank in Postgres yet.
- LaTeX question images should be rendered from `scripts/latex_iterations/iteration_13_original_font.py`.
- LaTeX explanation images should be rendered from `scripts/latex_iterations/iteration_14_explanation.py`.

## Requirements

### Functional

- Import one canonical question record per logical question into Postgres.
- Preserve original source content in Postgres for recovery and future edits:
  - `question_text`
  - `options`
  - `correct_option_text`
  - `short_explanation`
- Preserve algorithm-facing metadata in Postgres.
- For `has_latex = true`, generate four option-arrangement variants of the question image.
- For `has_latex = true`, generate one explanation image shared by all four variants.
- Upload generated images to R2 and store both keys and URLs in Postgres.
- For non-LaTeX questions, keep one canonical record and generate option shuffles dynamically at runtime.
- Support repeatable imports for future courses without bespoke per-course code.

### Operational

- The importer must be idempotent.
- Re-imports must detect whether a question changed and only regenerate assets when needed.
- Invalid rows should fail independently rather than blocking an entire course import.
- Questions should only become selectable by the quiz engine when all required validation and asset steps have completed.

## Recommended Architecture

Use a canonical question-bank model in Postgres with derived media in R2.

### Postgres

Create a canonical `question_bank` table that stores:

- stable question identity
- course identity
- raw source content
- adaptive-algorithm metadata
- LaTeX/media flags
- render/version status
- timestamps and content hash

For LaTeX questions, store derived variant metadata under the same logical question instead of creating four sibling questions. The logical question remains one adaptive item; only its presentation varies.

Suggested companion tables:

- `question_bank`
  - one row per logical question
- `question_asset_variants`
  - one row per LaTeX question-image variant
  - stores `variant_index`, option ordering map, R2 key, public URL, and asset hash
- `student_course_state`
  - stores `overall_skill`, `topic_skills`, `cognitive_profile`, `processing_profile`, `phase`, `misconception_flags`, totals, and exam date
- `question_attempts`
  - stores runtime attempt facts including `arrangement_hash` for non-LaTeX and `config_index` for LaTeX
- optional `question_srs_state`
  - if SRS state is normalized instead of derived from attempts

### R2

R2 stores derived artifacts only. The key structure should be stable and versionable, for example:

- `questions/<course_slug>/<question_key>/<version>/question_variant_0.png`
- `questions/<course_slug>/<question_key>/<version>/question_variant_1.png`
- `questions/<course_slug>/<question_key>/<version>/question_variant_2.png`
- `questions/<course_slug>/<question_key>/<version>/question_variant_3.png`
- `questions/<course_slug>/<question_key>/<version>/explanation.png`

This avoids overwriting older assets unintentionally and allows safe cache busting after edits.

## Canonical Question Shape

Each imported question should preserve source data and algorithm metadata together.

Minimum canonical fields:

- `question_key`
- `course_id`
- `course_slug`
- `question_text`
- `options`
- `correct_option_text`
- `short_explanation`
- `question_type`
- `option_count`
- `has_latex`
- `scaled_score`
- `raw_score`
- `base_score`
- `band`
- `topic_id`
- `cognitive_level`
- `processing_complexity`
- `distractor_complexity`
- `note_reference`
- `negative_stem`
- `source_checksum`
- `render_checksum`
- `status`

For LaTeX questions, the canonical row should also expose:

- `explanation_asset_key`
- `explanation_asset_url`
- `variant_count`

Variant rows should expose:

- `question_id`
- `variant_index`
- `option_order`
- `question_asset_key`
- `question_asset_url`
- `render_checksum`

## Import Workflow

### 1. Discovery

- scan `q_and_a/*/scored_cleaned.json`
- skip directories without the file
- support importing one course or all discovered courses

### 2. Normalization

- read JSON rows into a canonical importer schema
- derive a stable `question_key`
- normalize option text and string formatting
- validate `option_count` against the options array

### 3. Validation

Per-row validation should confirm:

- required fields exist
- `correct_option_text` matches one of the options
- algorithm fields have valid types and ranges
- `has_latex` rows can be rendered with the approved templates
- topic and course slugs are normalized consistently

Validation failures should be captured in an import report and should not stop unrelated rows from importing.

### 4. Upsert Canonical Question

- upsert the logical question row into Postgres
- compare source checksum to determine whether content changed
- if only scoring metadata changed, update metadata without regenerating assets

### 5. Generate LaTeX Variants

For `has_latex = true` only:

- build four deterministic option orders
- render four question images using the question template
- render one explanation image using the explanation template
- upload all generated artifacts to R2
- upsert variant rows and explanation asset metadata

The explanation image is shared across all four variants because it displays the correct answer text rather than a letter.

### 6. Publish Readiness

Mark the logical question as `ready` only when:

- canonical validation has passed
- required assets exist for LaTeX questions
- the database transaction storing the canonical row and asset metadata has succeeded

Questions in an error state must not be selectable by the adaptive engine.

## Re-Import And Edit Semantics

The importer should distinguish between source-content changes and metadata-only changes.

### Regenerate Assets When

- `question_text` changes
- `options` change
- `correct_option_text` changes
- `short_explanation` changes
- `has_latex` flips from false to true

### Update Metadata Only When

- `scaled_score` changes
- `band` changes
- `topic_id` changes
- `cognitive_level` changes
- `processing_complexity` changes
- `distractor_complexity` changes
- `note_reference` changes
- `negative_stem` changes

### Retire Or Replace Assets When

- a LaTeX question becomes non-LaTeX
- a question is deleted or superseded

Old assets can be retained until cleanup to avoid serving broken links during deployment windows.

## Runtime Serving Rules

### Non-LaTeX

- store one canonical question
- shuffle options dynamically each time
- log `arrangement_hash` on the attempt

### LaTeX

- store one canonical question
- choose one stored variant index per attempt
- log `config_index` on the attempt
- keep explanation media shared across variants

This matches the adaptive algorithm document without duplicating full question rows for non-LaTeX content.

## Failure Handling

- A bad row should not abort an entire course import.
- A LaTeX render failure should leave the canonical row in a non-ready error state.
- Import reports should include course, question key, stage, and error reason.
- Retry should be safe and should reuse the same logical identifiers.

## Recommended Implementation Order

1. Add canonical Postgres schema for question bank, asset variants, student state, and attempts.
2. Add importer schema and validators for `scored_cleaned.json`.
3. Extract reusable LaTeX render helpers from the current iteration scripts.
4. Add R2 upload integration to the import pipeline.
5. Add idempotent import command for one course or all courses.
6. Update quiz-serving code to read ready questions from Postgres instead of placeholder cache data.

## Accepted Decisions

- Postgres is the canonical question bank.
- JSON is the authoring/intake format only.
- R2 stores generated media.
- LaTeX questions have four stored question-image variants and one shared explanation image.
- Non-LaTeX questions do not store four expanded copies; option arrangement stays runtime-generated.
- Canonical records must keep both original source content and derived asset references so production edits can regenerate assets safely.
