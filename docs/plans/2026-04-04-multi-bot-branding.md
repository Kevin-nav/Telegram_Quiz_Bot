# Multi-Bot Branding Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Run one backend process for `tanjah` and `adarkwa` Telegram bots with shared user/question data, bot-scoped runtime state, bot-specific course visibility, and bot-specific image/UI branding.

**Architecture:** Add a bot config registry and build one Telegram `Application` per bot inside the same FastAPI runtime. Namespace Redis runtime keys by `bot_id`, filter catalogs per bot, and store/select LaTeX image assets per bot theme while keeping canonical question rows shared.

**Tech Stack:** FastAPI, python-telegram-bot, Redis, SQLAlchemy, Alembic, pytest, LaTeX-to-PNG rendering, Cloudflare R2.

---

### Task 1: Add Bot Config Registry

**Files:**
- Create: `src/bot/runtime_config.py`
- Modify: `src/core/config.py`
- Modify: `src/config.py`
- Test: `tests/test_config.py`

**Steps:**
1. Write tests that parse `TANJAH_*` and `ADARKWA_*` environment variables into a bot registry with defaults.
2. Run `python -m pytest tests/test_config.py -q` and verify the new tests fail.
3. Implement bot config dataclasses plus settings parsing/validation.
4. Re-run `python -m pytest tests/test_config.py -q` and verify the config tests pass.

### Task 2: Build One Telegram Application Per Bot

**Files:**
- Modify: `src/bot/application.py`
- Modify: `src/app/bootstrap.py`
- Modify: `src/api/webhooks.py`
- Modify: `src/workers/telegram_update.py`
- Test: `tests/test_telegram_dispatcher.py`
- Test: `tests/test_webhook.py`

**Steps:**
1. Write tests proving each `bot_id` has its own `Application`, token, webhook secret, and route.
2. Run the webhook/dispatcher tests and verify they fail on the current single-bot implementation.
3. Refactor app bootstrap and webhook dispatch to select the matching bot runtime by `bot_id`.
4. Re-run the webhook/dispatcher tests.

### Task 3: Namespace Redis Runtime State By Bot

**Files:**
- Modify: `src/infra/redis/keys.py`
- Modify: `src/infra/redis/idempotency.py`
- Modify: `src/infra/redis/state_store.py`
- Modify: `src/domains/quiz/service.py`
- Test: `tests/test_redis_idempotency.py`
- Test: `tests/test_interactive_state_store.py`
- Test: `tests/test_quiz_session_service.py`

**Steps:**
1. Add failing tests showing `tanjah` and `adarkwa` do not collide on active quiz, poll maps, report drafts, and webhook update IDs.
2. Implement `bot_id`-aware Redis keys and thread `bot_id` into the state store and quiz session service.
3. Run the targeted Redis and quiz tests.

### Task 4: Add Bot-Specific Course Visibility

**Files:**
- Modify: `src/domains/catalog/service.py`
- Modify: `src/domains/catalog/navigation_service.py`
- Modify: `src/bot/handlers/home.py`
- Modify: `src/bot/handlers/profile_setup.py`
- Test: `tests/test_catalog_navigation.py`
- Test: `tests/test_home_actions.py`
- Test: `tests/test_profile_setup_flow.py`

**Steps:**
1. Write tests showing Adarkwa only exposes configured course codes while Tanjah still exposes the full catalog.
2. Implement a bot-course filter sourced from the current bot config.
3. Add fallback behavior when a shared preferred course is hidden in Adarkwa.
4. Run the catalog/home/profile tests.

### Task 5: Move UI Copy and Button Labels Behind Bot Themes

**Files:**
- Modify: `src/bot/copy.py`
- Modify: `src/bot/keyboards.py`
- Modify: `src/bot/handlers/start.py`
- Modify: `src/bot/handlers/commands.py`
- Modify: `src/bot/handlers/home.py`
- Modify: `src/bot/handlers/reporting.py`
- Test: `tests/test_bot_copy.py`
- Test: `tests/test_keyboards.py`
- Test: `tests/test_start_flow.py`
- Test: `tests/test_home_actions.py`

**Steps:**
1. Write tests for different welcome/help/home labels for `tanjah` and `adarkwa`.
2. Refactor copy and keyboards to accept the current bot theme from `application.bot_data`.
3. Run the bot copy, keyboard, start, and home tests.

### Task 6: Render and Select Bot-Specific LaTeX Assets

**Files:**
- Modify: `src/domains/question_bank/latex_renderer.py`
- Modify: `src/domains/question_bank/asset_service.py`
- Modify: `src/domains/question_bank/import_service.py`
- Modify: `src/infra/db/models/question_asset_variant.py`
- Modify: `src/infra/db/models/question_bank.py`
- Create: `migrations/versions/<revision>_add_bot_scoped_question_assets.py`
- Modify: `src/domains/quiz/service.py`
- Test: `tests/test_question_bank_latex_renderer.py`
- Test: `tests/test_question_bank_asset_service.py`
- Test: `tests/test_question_bank_import_service.py`
- Test: `tests/test_quiz_session_service.py`

**Steps:**
1. Write failing tests for bot-specific LaTeX templates, bot-specific R2 keys, and quiz selection of the current bot's asset URL.
2. Add `bot_id` to asset records and object keys, then regenerate/upload assets per configured bot theme.
3. Thread current `bot_id` into quiz question assembly and LaTeX variant resolution.
4. Run the question-bank and quiz-session tests.

### Task 7: Documentation and Rollout Checks

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docs/deployment_setup.md`
- Modify: `docs/question_bank_import.md`

**Steps:**
1. Document the `tanjah` and `adarkwa` environment variables, webhook routes, and course filters.
2. Add a short migration/backfill note for regenerating bot-specific LaTeX assets.
3. Run the full targeted test set and summarize any manual deployment steps.
