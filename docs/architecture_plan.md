# @Adarkwa_Study_Bot Architecture Plan

This document tracks the current implementation direction for the launch foundation. The bot is intentionally being built as a modular monolith first so the fundamentals are stable before the adaptive learning engine and content-management layers are added.

## Current Direction

- one codebase
- one web process (`FastAPI`)
- one worker process (`ARQ`)
- Neon as the durable data store
- Redis for idempotency, queueing, rate limiting, and short-lived operational state
- Cloudflare R2 for media storage abstractions

## Phase 1: Launch Foundation

The immediate goal is to make the application safe to deploy and easy to extend.

### Code Structure

```text
src/
  app/        # bootstrap, logging, observability
  core/       # typed settings, security checks, shared primitives
  api/        # webhook and health routes
  infra/      # Neon, Redis, R2 integrations
  domains/    # business services
  bot/        # Telegram bot wiring
  workers/    # background job handlers
```

### Foundation Controls

- typed settings with environment validation
- no insecure default webhook secret
- Redis-backed Telegram update idempotency
- readiness and liveness endpoints
- shared bootstrap for web and worker lifecycle
- minimal database schema and repository layer
- analytics domain service
- R2 storage abstraction for future LaTeX/media work
- explicit migration path via Alembic and a Kubernetes migration job

## Deferred Until After Foundation

These are intentionally not part of the current execution slice:

- adaptive question selection and scoring logic
- full quiz session domain modeling
- admin dashboard and CMS
- large-scale Kubernetes rollout work

## Current Telegram UX Slice

The current Telegram implementation is moving toward a home-first student flow:

- new users: `/start` -> study profile setup
- setup path: faculty -> program -> level -> semester -> course
- returning users: `/start` -> study home
- home actions: start quiz, continue placeholder, performance placeholder, change course, help

This UX slice is intentionally lightweight and is meant to stabilize navigation and profile context before deeper adaptive-learning and quiz-session behavior is layered in.

## Supporting Docs

- `docs/adaptive_learning_algorithm.md`
- `docs/plans/2026-03-16-launch-foundation-design.md`
- `docs/plans/2026-03-16-launch-foundation.md`
- `docs/plans/2026-03-17-telegram-ux-flow-design.md`
- `docs/plans/2026-03-17-telegram-ux-flow.md`
