# Backend Suggestions: Student Analytics Enhancements

## Implemented

### `users.current_streak`, `users.longest_streak`, `users.last_active_date`

- Status: implemented on `users`
- Logic: learner activity advances the streak when the previous active date was yesterday, resets to `1` after a gap, and keeps `longest_streak` as the max observed value
- Why: admins can rank engagement without rebuilding streaks from raw attempts

### `users.last_active_at`

- Status: implemented on `users`
- Logic: background persistence updates the latest seen timestamp directly
- Why: admin queries no longer need `MAX(created_at)` scans on `question_attempts`

### `student_course_state.total_correct`

- Status: implemented on `student_course_state`
- Logic: incremented during attempt persistence when the answer is correct
- Why: course accuracy is available without recounting raw attempts

### `student_course_state.avg_time_per_question`

- Status: implemented on `student_course_state`
- Logic: maintained as a running average during attempt persistence
- Why: performance views can show pace without loading every timed attempt

### `student_session_summary`

- Status: implemented as a dedicated summary table
- Logic: written at quiz completion from the persisted session attempts
- Why: weekly/session analytics can use session rows before falling back to raw attempt scans

## Operational Notes

- Postgres remains the canonical store for attempts, learner state, and session summaries.
- Redis should cache hot analytics payloads and selector snapshots, not replace the primary database.
- Admin analytics summary caching should be stale-while-revalidate so the last good payload is served while a worker refresh runs.

## Backfill Notes

- `student_course_state.total_correct`: backfill from `question_attempts`
- `student_course_state.avg_time_per_question`: backfill from timed attempts grouped by learner and course
- `users.last_active_at`: backfill from the latest learner activity timestamp
- `users` streak fields: backfill from distinct activity dates per learner
- `student_session_summary`: backfill from grouped `question_attempts` by `session_id`
