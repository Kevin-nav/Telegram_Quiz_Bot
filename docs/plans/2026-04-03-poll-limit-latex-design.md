# Poll-Limit LaTeX Promotion Design

## Goal
Automatically render oversized Telegram poll questions/options as LaTeX image questions during question-bank import, including already-imported rows that were previously stored as non-LaTeX.

## Architecture
Normalize each imported question once, then promote `has_latex` to `True` when the poll question exceeds Telegram's 300-character limit or any poll option exceeds the 100-character limit. Compute the source checksum after that promotion so re-importing an existing oversized non-LaTeX row invalidates the old checksum and regenerates LaTeX assets against the same `question_key`.

## Components
- `src/domains/question_bank/import_service.py`
  - add one helper that applies Telegram poll-length rules before checksum generation
  - keep question-key generation unchanged
- `src/domains/question_bank/latex_renderer.py`
  - keep current 4-option arrangements unchanged
  - add a safe fallback arrangement strategy for non-4-option LaTeX questions so promoted 2-option or 5-option rows do not fail import
- `tests/test_question_bank_import_service.py`
  - cover new oversized non-LaTeX rows
  - cover re-import of an existing non-LaTeX row that must now become LaTeX
- `tests/test_question_bank_latex_renderer.py`
  - cover non-4-option variant generation

## Data Flow
1. Load row JSON.
2. Build `ImportedQuestion`.
3. Promote `has_latex` when poll text exceeds Telegram limits.
4. Validate and compute `question_key` plus `source_checksum`.
5. Skip only when an existing row is already `ready` with the same checksum.
6. Otherwise upsert and render LaTeX assets when `has_latex=True`.

## Error Handling
- Existing invalid-row behavior remains unchanged.
- If LaTeX rendering fails, the row is marked `error` as it is today.
- Oversized non-4-option questions should no longer fail merely because of variant generation.

## Testing
- Unit tests for promotion logic and checksum-driven re-import behavior.
- Unit tests for generic LaTeX option variant generation.
- Run the importer service tests and renderer tests.
