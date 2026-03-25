# Adaptive Learning Algorithm Design

## Goal

Build a scalable adaptive quiz engine for `Adarkwa_Study_Bot` that implements the algorithm in `docs/adaptive_learning_algorithm.md` while keeping the Telegram quiz flow fast and reactive.

## Architecture

- Postgres is the source of truth for:
  - question metadata
  - question variants
  - attempts
  - adaptive state
  - SRS state
  - review flags
- Redis is the speed layer for:
  - active quiz sessions
  - poll maps
  - locks
  - idempotency
  - hot question caches
  - short-lived adaptive snapshots
- The runtime is split into:
  - a thin hot path for quiz delivery
  - a background path for adaptive updates and review analytics

## Core Decisions

- Selection must not discriminate between LaTeX and non-LaTeX questions.
- `has_latex` only affects presentation and arrangement strategy.
- Heavy adaptive computation must not block next-question delivery.
- Adaptive logic belongs in a dedicated `src/domains/adaptive/` package, not inside Telegram handlers.
- The system must be recomputable from canonical attempts if the algorithm changes later.

## New Components

### Adaptive Domain

Create `src/domains/adaptive/` with:

- `models.py`
- `service.py`
- `selection.py`
- `ordering.py`
- `updater.py`
- `timing.py`
- `arrangement.py`
- `srs.py`
- `review.py`

### Persistence

Keep:

- `question_bank`
- `question_asset_variants`
- `question_attempts`
- `student_course_state`

Add:

- `student_question_srs`
- `adaptive_review_flags`

## Runtime Flow

### Quiz Start

1. Load or create adaptive snapshot for `(user, course)`.
2. Load course question metadata from Redis or Postgres.
3. Run adaptive selection:
   - phase
   - cold start when needed
   - candidate filters
   - weakness/new/SRS/ZPD/coverage/misconception scores
   - exam modifier
   - weighted random top-3 choice
4. Order selected questions warm-up to challenge to cool-down.
5. Prepare presentation arrangement for each question.
6. Store session state in Redis.
7. Send first question immediately.

### Answer Processing

1. Read session and acquire session lock.
2. Compute correctness from session payload.
3. Compute `time_taken_seconds` from stored presentation timestamp.
4. Enqueue background adaptive update.
5. Advance session and send next question immediately.

### Background Update

1. Idempotency check.
2. Persist canonical attempt.
3. Acquire `(user, course)` adaptive update lock.
4. Classify the attempt from correctness and time ratio.
5. Update:
   - topic skill
   - cognitive profile
   - processing profile
   - overall skill
6. Update SRS.
7. Track or resolve misconceptions.
8. Detect memorization effects.
9. Recompute phase and counters.
10. Refresh or invalidate adaptive snapshot cache.

## Performance Rules

- No N+1 history reads in the selector.
- No per-candidate ORM queries.
- No synchronous adaptive recomputation in the hot path.
- Use batched repositories for attempts, question metadata, and SRS state.
- Use Redis locks and idempotency keys for duplicate update safety.
- Scale by adding workers and tightening query shape, not by moving truth into Redis.

## Rollout

1. Add missing tables and repositories.
2. Implement adaptive updater behind the background pipeline.
3. Compute real state while current selector still exists.
4. Enable adaptive selection behind feature flags.
5. Add review analytics after the core path is stable.
