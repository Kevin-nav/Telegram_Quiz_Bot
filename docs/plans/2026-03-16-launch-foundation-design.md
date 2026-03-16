# Launch Foundation Design

## Goal

Bring `@Adarkwa_Study_Bot` to a launch-worthy foundation by hardening the runtime, configuration, infrastructure boundaries, and operational behavior before building the adaptive quiz engine or content/admin workflows.

## Scope

This design covers only the first top-level milestone:

- modular monolith application structure
- production-safe configuration and secret handling
- secure webhook and worker flow
- Neon, Redis, and R2 infrastructure abstractions
- health checks, logging, and observability
- baseline persistence and analytics plumbing
- launch-critical test coverage

This design explicitly excludes:

- adaptive learning and question selection implementation
- full quiz domain modeling
- CMS/admin dashboard work
- LaTeX rendering pipeline beyond storage abstraction

## Recommended Approach

Use a modular monolith with one FastAPI web process and one ARQ worker process, sharing the same codebase and bootstrap layer. This keeps launch velocity high while creating clean boundaries for later extraction into separate services if needed.

Alternative options were considered:

1. Minimal refactor of the current skeleton. Rejected because the current layout couples framework and infrastructure concerns too early.
2. Service-oriented split now. Rejected because it adds operational complexity before the product fundamentals are stable.

## Runtime Model

The application runs as a single deployable image with two roles:

- `web`: owns FastAPI startup, webhook validation, health/readiness endpoints, and enqueueing jobs
- `worker`: owns Telegram update processing, background analytics writes, and other heavy asynchronous work

Both roles share a common bootstrap path for configuration, DB, Redis, R2, queue clients, logging, and observability.

## Code Structure

```text
src/
  app/
    bootstrap.py
    logging.py
    observability.py
  core/
    config.py
    security.py
    enums.py
    exceptions.py
    clock.py
  infra/
    db/
      base.py
      session.py
      models/
      repositories/
    redis/
      client.py
      keys.py
      idempotency.py
      rate_limit.py
    r2/
      client.py
      storage.py
    queue/
      arq.py
  domains/
    analytics/
    users/
    quiz/
    progress/
  bot/
    application.py
    handlers/
    middleware/
  api/
    webhooks.py
    health.py
  workers/
    telegram_update.py
    analytics.py
```

Principles:

- `core` is framework-light and import-safe
- `infra` contains all vendor-specific integration code
- `domains` contains business logic, not transport or persistence concerns
- `api`, `bot`, and `workers` are delivery layers over shared services

## Security and Operational Hardening

Phase 1 introduces launch-first controls:

- typed settings via `pydantic-settings`
- fail-fast validation for unsafe production configuration
- no insecure default webhook secret
- TLS enforcement for production webhook URLs
- Redis-backed idempotency for duplicate Telegram updates
- Redis-backed rate limiting for abuse-prone actions
- structured logging with correlation IDs
- centralized exception handling with sanitized responses
- liveness and readiness endpoints
- graceful startup and shutdown for DB, Redis, R2, queue, and Telegram resources
- explicit worker timeout and retry policy

## Infrastructure Design

### Neon

Neon is the system of record. SQLAlchemy async remains the access layer, but all queries move behind repositories. Schema discipline starts immediately with migrations.

Phase-1 tables should stay minimal:

- `users`
- `telegram_identities`
- `analytics_events`
- `webhook_events` or `job_audit`
- optional minimal `courses` placeholder only if required by current bootstrapping

### Redis

Redis is operational infrastructure, not durable storage. It is used for:

- webhook idempotency
- rate limiting
- short-lived bot/session state
- cache entries such as Telegram file references

All keys are namespaced and generated from a single module.

### R2

R2 is introduced now only through a storage abstraction. It must define:

- object key strategy
- content-type and size validation
- object existence checks
- upload and signed download access helpers

The initial naming convention should be stable enough for future LaTeX/media workflows, for example:

`latex/{course_id}/{question_id}/{sha256}.png`

## Implementation Sequence

Execution order for phase 1:

1. Restructure the package layout without changing outward behavior
2. Replace config loading with typed settings and environment validation
3. Add shared bootstrap and lifecycle management
4. Harden webhook handling with secret validation, idempotency, and error handling
5. Add liveness/readiness endpoints
6. Introduce Neon, Redis, and R2 infrastructure abstractions
7. Move analytics behind a proper service boundary
8. Harden worker execution and logging
9. Expand launch-critical test coverage
10. Update Docker/runtime defaults for safer deployment

## Testing Boundaries

Phase-1 tests focus on launch-critical behavior:

- config validation and environment safety rules
- webhook authorization and duplicate suppression
- readiness behavior for dependency failures
- Redis key/idempotency logic
- worker retry/error handling
- bootstrap lifecycle correctness
- R2 key generation and storage validation

Use unit and mocked integration tests as the CI baseline. Real Neon/Redis integration tests can be added later or behind a separate workflow.

## Acceptance Criteria

The foundation milestone is complete when:

- the app boots through a shared bootstrap path with validated settings
- the webhook safely rejects invalid requests and deduplicates repeats
- Redis, Neon, and R2 access live behind explicit infrastructure modules
- web and worker processes can run independently but share the same lifecycle primitives
- readiness checks reflect real dependency state
- launch-critical tests cover failure paths, not just happy paths
- the project structure is ready for phase 2 adaptive learning work without another architectural rewrite

## Constraints and Notes

- This workspace does not currently appear to be a Git repository, so the design doc cannot be committed as part of this step.
- Phase 2 and phase 3 work should not start until the foundation plan is executed and stabilized.
