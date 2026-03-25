# Adaptive Runtime Architecture

## Runtime Shape

The adaptive system is split into two paths.

### Hot Path

- quiz start
- poll delivery
- answer receipt
- session progression
- minimal Redis state updates

This path should stay fast and should not wait on skill recomputation or review analytics.

### Background Path

- canonical attempt persistence
- adaptive skill updates
- SRS updates
- misconception handling
- review-flag generation
- cache invalidation

This path can lag a little without hurting the user experience, as long as it remains idempotent and retry-safe.

## Source Of Truth

- Postgres stores canonical question data, attempts, student adaptive state, SRS state, and review flags.
- Redis stores active sessions, locks, idempotency keys, and short-lived adaptive snapshots.

## Rollout Controls

- `ADAPTIVE_SELECTOR_ENABLED` gates broader rollout of the adaptive selector.
- `ADAPTIVE_UPDATER_ENABLED` gates attempt-state updates in the worker path.
- `ADAPTIVE_REVIEW_JOBS_ENABLED` gates background quality-review jobs.
- `ADAPTIVE_SNAPSHOT_CACHE_ENABLED` controls cache usage for adaptive snapshots.

These flags default conservatively so the new runtime can be enabled gradually by cohort or environment.

## Performance Rules

- The selector must use batched repository reads.
- The worker must be safe to retry.
- Redis locks must prevent duplicate quiz and adaptive updates from racing.
- Question presentation must stay content-neutral: LaTeX affects rendering only, not scoring.

## Operational Notes

- If Redis is unavailable, the system should still preserve canonical data in Postgres where possible.
- If background jobs lag, the next question should still be delivered.
- Because Postgres is canonical, adaptive state can be rebuilt from attempts if the algorithm changes later.
