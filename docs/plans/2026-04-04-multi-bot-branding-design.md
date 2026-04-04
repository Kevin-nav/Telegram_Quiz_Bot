# Multi-Bot Branding Design

## Summary

Run one backend process for two Telegram bots, `tanjah` and `adarkwa`, against the same user/question database. Keep user profile and onboarding data shared, but isolate active quiz/runtime state per bot and render brand-specific LaTeX images per bot.

## Architecture

Introduce a bot configuration registry keyed by `bot_id`. Each bot config owns its Telegram token, webhook path/secret, UI text and button labels, allowed-course filter, and LaTeX branding theme.

FastAPI exposes one webhook endpoint per bot. Each endpoint validates that bot's webhook secret, claims idempotency with a bot-scoped Redis key, then dispatches the update into that bot's own `python-telegram-bot` `Application` instance.

Redis quiz/session/report keys are namespaced by `bot_id` so a student can have a separate active quiz in each bot. Database user rows remain keyed by Telegram user ID, so profile setup and onboarding stay shared across both bots.

## Data Model

Keep `question_bank` as the canonical question source shared by both bots.

Store rendered LaTeX assets per bot theme. Question image variants and explanation images need a `bot_id` dimension so `tanjah` and `adarkwa` can serve different PNG branding for the same canonical question row. Asset object keys should also include `bot_id` to avoid collisions in R2.

Shared user profile remains unchanged initially. If a user selects a preferred course in `tanjah` that is not exposed in `adarkwa`, the Adarkwa bot should ask the user to choose one of Adarkwa's allowed courses instead of reusing the hidden course.

## UI and Branding

Move hardcoded copy and LaTeX theme constants behind per-bot config. At minimum, this includes welcome/help/home text, button labels, quiz prompts, report labels, and LaTeX title/footer/watermark/colors.

Each Telegram handler reads its bot config from `context.application.bot_data`, keeping the handler logic shared while making the presentation bot-specific.

## Error Handling

Unknown webhook paths return 404 via routing. Wrong webhook secrets return 401 using the matching bot config. Missing bot asset variants should degrade to the canonical question row's current asset URL if available, then to text fallback.

If a shared preferred course is hidden by the current bot's course filter, quiz start should fail closed and prompt the user to pick a visible course.

## Testing

Add tests for:
- loading two bot configs and building one `Application` per bot
- webhook secret validation and dispatch by `bot_id`
- bot-scoped Redis idempotency and active-quiz keys
- bot-specific course filtering while shared profile remains intact
- bot-specific LaTeX templates and bot-specific asset key generation
- quiz question assembly selecting the current bot's branded asset variant
