# Snappy Webhook + Redis Hot-State Plan

## Summary

Refactor `@Adarkwa_Study_Bot` into a hybrid webhook architecture: Telegram updates are accepted by the web pod and lightweight user-facing interactions are dispatched inline in-process for fast feedback, while ARQ is reserved for heavyweight work only. Neon remains the durable source of truth. Redis becomes the shared hot-state layer for multi-pod scale: idempotency, profile cache, active quiz pointers, poll/session state, locks, and short-lived operational data.

Target outcome: normal callback and quiz interactions feel sub-second, even with two or more web pods, and the upcoming poll-heavy quiz flow no longer depends on a full Redis queue hop plus a slow Neon read before every response.

## Implementation Changes

### 1. Update Delivery Model

- Replace the current “all webhook updates go to ARQ first” flow with a dispatcher in the web process.
- `POST /webhook` should do only: secret validation, payload parse, Redis idempotency claim, dispatch classification, immediate `200 OK`.
- Dispatch classification should be decision-complete:
  - Inline fast path: `callback_query`, `poll_answer`, simple commands, short text interactions, quiz navigation, home/profile interactions.
  - ARQ-only path: analytics writes, quiz generation/scoring jobs, backfills, report building, large media generation, retryable persistence work.
- Inline processing should be scheduled with `asyncio.create_task(...)` behind a bounded semaphore so the HTTP response does not wait for handler completion and one pod cannot overrun itself under burst traffic.
- Keep `query.answer()` as the first awaited Telegram call in every callback-based handler and preserve that rule for poll interactions.

### 2. Shared Redis Hot-State Design

- Introduce a dedicated state/cache service layer instead of ad hoc direct Redis usage from handlers.
- Keep Neon durable; Redis is the hot shared read model and coordination layer.
- Define these shared Redis records:
  - `telegram-update:{update_id}` for webhook idempotency, TTL 5 minutes.
  - `user-profile:{user_id}` for the minimal home/quiz routing profile, TTL 30 minutes, refreshed on read and overwritten on profile changes.
  - `active-quiz:{user_id}` for current session pointer, TTL 24 hours, refreshed on every quiz interaction.
  - `quiz-session:{session_id}` for live quiz state needed by any web pod to continue the session, TTL 24 hours.
  - `poll-map:{poll_id}` for Telegram poll-to-session/question lookup, TTL until poll close plus 1 hour.
  - `lock:quiz-session:{session_id}` for short distributed locks during answer processing or poll transitions, TTL 15 seconds.
- Use cache-aside for reads and write-through/update-on-write for profile and session mutations so normal traffic hits Redis first and DB fallback is the exception.
- For multi-pod correctness, no interactive flow should depend on process-local memory for quiz progress or active poll state.

### 3. Quiz/Poll Flow Read Model

- Build the first quiz execution path around Telegram polls, with Redis holding all live state required to react instantly to `poll_answer` updates.
- A quiz session record should include at minimum: `session_id`, `user_id`, `course_id`, ordered question ids, current index, current poll id, answer metadata needed for grading, status, and expiry.
- When a quiz question is sent as a poll:
  - Persist the durable quiz/session event in Neon asynchronously.
  - Store the live poll mapping and current question state in Redis immediately.
- On `poll_answer`:
  - Resolve `poll_id` from Redis.
  - Grade/update live session state without waiting on Neon.
  - Send the next poll or feedback immediately.
  - Persist attempt history, selector signals, and analytics in ARQ after the user-facing Telegram action is already sent.
- The adaptive selector should be designed to read from Neon but be wrapped with Redis cache for reusable hot data:
  - question-bank metadata by course
  - per-student selector input snapshot
  - generated quiz plan for a session
- Do not make Redis the long-term academic record; it is the acceleration layer.

### 4. Persistence and Background Jobs

- Remove synchronous analytics writes from `/start` and any other interactive path.
- Move all analytics/event logging and non-user-blocking persistence to ARQ jobs with idempotent payloads.
- Split profile/session persistence into two classes:
  - synchronous only when correctness requires it
  - asynchronous when it only affects reporting, history, or downstream learning signals
- Add explicit job types for:
  - `record_analytics_event`
  - `persist_quiz_attempt`
  - `persist_quiz_session_progress`
  - `generate_quiz_session`
  - `rebuild_profile_cache` when needed after DB fallback or repair
- Keep ARQ in the system, but it should no longer sit in front of every Telegram update.

### 5. Infrastructure and Operations

- Run web pods and Redis/Neon in the same region. Current measurements show the remote network hop is a major part of the latency budget.
- Keep at least 2 web pods and increase worker deployment to at least 2 replicas once ARQ jobs are idempotent.
- Add a worker HPA or at minimum separate scaling guidance for workers; web-only autoscaling is not enough once heavy quiz jobs start.
- Add instrumentation and dashboards for:
  - webhook ack latency
  - inline dispatch queue depth/semaphore saturation
  - Redis hit rate and command latency
  - DB fallback rate from cache misses
  - Telegram API latency
  - ARQ enqueue latency and job lag
  - end-to-end “update received to Telegram reply sent” latency
- Define SLOs for this slice:
  - webhook ack p95 under 150 ms inside cluster
  - callback/poll answer to visible Telegram reaction p95 under 700 ms
  - DB fallback rate under 5% for hot interactive flows after warm-up

## Public Interfaces / Internal Contracts

- Add an internal `TelegramUpdateDispatcher` interface with `dispatch(payload)` and deterministic routing between inline and background processing.
- Add an internal `InteractiveStateStore` interface for `get/set/invalidate profile`, `get/set active quiz`, `map poll`, `claim update`, and `acquire/release lock`.
- Add typed quiz state records for Redis payloads so web pods and workers share one schema for profile cache, session state, and poll mapping.
- Keep the external HTTP interface unchanged: `POST /webhook` stays the Telegram entrypoint.

## Test Plan

- Webhook tests:
  - authorized webhook returns `200` without waiting on ARQ for fast-path updates
  - duplicate updates are suppressed across two simulated app instances using shared Redis
  - heavy-job-classified updates are enqueued and not processed inline
- Cache/state tests:
  - profile read hits Redis first and falls back to DB once, then warms cache
  - active quiz and poll mappings can be read by a different simulated pod
  - distributed quiz lock prevents double-processing of the same poll answer
- Quiz flow tests:
  - starting a quiz creates Redis session state and sends the first poll
  - `poll_answer` resolves entirely from Redis and advances to the next question without synchronous DB reads
  - session resume after pod change uses Redis state correctly
- Performance checks:
  - benchmark mocked inline webhook path versus current ARQ-first path
  - measure Redis hit-path latency and DB fallback latency separately
  - verify `/start` no longer waits on analytics
- Failure-mode tests:
  - Redis unavailable returns a controlled failure mode rather than partial duplicate processing
  - ARQ unavailable does not break inline callback/poll responsiveness for fast-path updates
  - Telegram API failure does not corrupt Redis session state

## Assumptions and Defaults

- First slice is `fast path + cache`, not full adaptive-engine implementation.
- Neon remains the durable source of truth; Redis is the hot shared layer.
- Telegram poll-heavy quizzes are the primary interaction model to optimize for.
- A cache miss may still be slower; the goal is to make steady-state interactive traffic fast.
- The selector algorithm can stay logically separate from this refactor, but its future inputs/outputs should be shaped to use Redis-backed hot reads and async persistence from day one.
