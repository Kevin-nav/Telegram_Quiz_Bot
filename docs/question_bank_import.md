# Question Bank Import Workflow

## Source Of Truth

Question authoring happens outside the bot package in the shared [`q_and_a`](C:/Users/Kevin/Projects/Telegram_Bots/Quizzers/q_and_a) directory.

Each importable course should contain:

- `q_and_a/<course-slug>/scored_cleaned.json`

Courses without `scored_cleaned.json` are skipped by the importer. At the moment that includes `general-psychology`.

## What Gets Stored

### Postgres

The importer stores one canonical row per logical question in the question bank, including:

- original `question_text`
- original `options`
- `correct_option_text`
- `short_explanation`
- algorithm metadata such as `scaled_score`, `band`, `topic_id`, and complexity fields
- lifecycle fields such as checksums and status

For LaTeX questions, Postgres also stores:

- four question-image variant records
- one shared explanation image reference

### R2

For `has_latex = true`, the importer renders PNG assets and uploads them to R2 with versioned keys like:

- `questions/<course>/<question>/<version>/question_variant_0.png`
- `questions/<course>/<question>/<version>/explanation.png`

The version segment is based on the source checksum, so content changes produce new asset paths.

## Import Command

Import one course:

```bash
python scripts/import_question_bank.py --course linear-electronics
```

Import all discovered courses:

```bash
python scripts/import_question_bank.py --all
```

Override the shared `q_and_a` root if needed:

```bash
python scripts/import_question_bank.py --all --q-and-a-root C:\path\to\q_and_a
```

## Import Behavior

The importer processes rows independently.

- invalid rows are marked as failed without aborting the rest of the course
- non-LaTeX questions are validated and stored without asset generation
- LaTeX questions generate four question-image variants and one explanation image
- successful rows are marked `ready`
- LaTeX render or upload failures mark the row `error`

## Status Meanings

- `processing`: the canonical row exists but LaTeX asset work is still in progress
- `ready`: the question is available for quiz selection
- `error`: the row exists but should not be served until the source issue is fixed and the import is rerun
- `invalid`: the source row failed validation before canonical persistence completed

## Re-Import Rules

Re-import is intended to be safe and repeatable.

- metadata-only changes update the canonical question row
- source-content changes produce a new checksum and regenerate LaTeX assets
- non-LaTeX questions do not store duplicated arrangement variants
- runtime option shuffling for non-LaTeX questions happens during quiz delivery

## Runtime Notes

- quiz selection now prefers `ready` questions from the canonical question bank
- if no ready questions are available for a course, the existing placeholder fallback remains in place
- attempt payloads now include arrangement/config metadata so the adaptive algorithm can use them later

## Operational Caveats

- the current local environment still has some bootstrap issues in the shared test harness, including missing dependencies like `arq`
- the current environment also emits existing `.env` parse warnings on some imports
- those issues do not change the import workflow itself, but they do affect full-suite local verification
