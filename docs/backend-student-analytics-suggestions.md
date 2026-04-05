# Backend Suggestions: Student Analytics Enhancements

> **Context**: The admin dashboard now has a full student performance page that models these fields with mock data. When these backend changes are made, the frontend is already wired up — just swap mock data for API calls.

---

## 1. Daily Streak Tracking

**Option A — New table `student_daily_streak`:**

```sql
CREATE TABLE student_daily_streak (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    current_streak   INT NOT NULL DEFAULT 0,
    longest_streak   INT NOT NULL DEFAULT 0,
    last_active_date DATE,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id)
);
CREATE INDEX ix_student_daily_streak_user_id ON student_daily_streak(user_id);
```

**Option B — Add columns to `users` table:**

```sql
ALTER TABLE users ADD COLUMN current_streak INT NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN longest_streak INT NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN last_active_date DATE;
```

**Logic**: On each quiz completion, check if `last_active_date = today - 1` → increment `current_streak`. If `last_active_date < today - 1` → reset to 1. Update `longest_streak = MAX(longest_streak, current_streak)`. Set `last_active_date = today`.

**Why**: Streak is one of the strongest engagement signals for admins and powers the leaderboard ranking.

---

## 2. `users.last_active_at` Column

```sql
ALTER TABLE users ADD COLUMN last_active_at TIMESTAMPTZ;
CREATE INDEX ix_users_last_active_at ON users(last_active_at);
```

**Logic**: Update on every bot interaction (quiz start, answer submission). Can use a background job or a trigger.

**Why**: Currently requires `MAX(created_at) FROM question_attempts WHERE user_id = ?` which is expensive at scale. A denormalized column makes dashboard queries instant.

---

## 3. `student_course_state.total_correct` Column

```sql
ALTER TABLE student_course_state ADD COLUMN total_correct INT NOT NULL DEFAULT 0;
```

**Logic**: Increment alongside `total_attempts` in the adaptive update flow (`AdaptiveLearningService.apply_attempt_update`). Only increment when `is_correct = True`.

**Why**: Accuracy (`total_correct / total_attempts`) is the most-viewed metric on the admin dashboard. Currently requires `COUNT(*) FROM question_attempts WHERE user_id = ? AND course_id = ? AND is_correct = true`.

---

## 4. `student_course_state.avg_time_per_question` Column

```sql
ALTER TABLE student_course_state ADD COLUMN avg_time_per_question FLOAT;
```

**Logic**: Maintain a running average. On each attempt: `new_avg = ((old_avg * (n-1)) + time_taken_seconds) / n` where `n = total_attempts`.

**Why**: Lets admins spot students who are rushing (very fast) or struggling (very slow) without querying all attempts.

---

## 5. `student_session_summary` Table

```sql
CREATE TABLE student_session_summary (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL,
    session_id      VARCHAR(255) NOT NULL,
    course_id       VARCHAR(128) NOT NULL,
    questions_count INT NOT NULL,
    correct_count   INT NOT NULL,
    accuracy        FLOAT NOT NULL,
    total_time_seconds FLOAT,
    started_at      TIMESTAMPTZ NOT NULL,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(session_id)
);
CREATE INDEX ix_student_session_summary_user_id ON student_session_summary(user_id);
CREATE INDEX ix_student_session_summary_course_id ON student_session_summary(course_id);
CREATE INDEX ix_student_session_summary_started_at ON student_session_summary(started_at);
```

**Logic**: Populate at quiz completion (already have a `increment_completed_quizzes` hook). Aggregate from `question_attempts` grouped by `session_id`.

**Why**: Avoids expensive `GROUP BY session_id` aggregation queries. Powers the "Performance Over Time" chart and session-level analytics. Each row is ~100 bytes vs scanning potentially thousands of attempt rows.

---

## Priority Order

| Priority | Change | Effort | Impact |
|----------|--------|--------|--------|
| 🔴 High | `total_correct` column | ~30 min | Enables accuracy without full table scan |
| 🔴 High | `last_active_at` column | ~30 min | Instant last-seen queries |
| 🟡 Medium | Daily streak tracking | ~2 hrs | Core engagement metric |
| 🟡 Medium | `student_session_summary` | ~3 hrs | Powers performance charts |
| 🟢 Low | `avg_time_per_question` | ~30 min | Nice-to-have speed metric |

---

## Migration Notes

- All changes are **additive** (new columns with defaults, new tables) — no breaking changes
- Existing data can be backfilled with one-time scripts:
  - `total_correct`: `UPDATE student_course_state SET total_correct = (SELECT COUNT(*) FROM question_attempts WHERE ... AND is_correct = true)`
  - `last_active_at`: `UPDATE users SET last_active_at = (SELECT MAX(created_at) FROM question_attempts WHERE ...)`
  - `student_session_summary`: `INSERT INTO ... SELECT session_id, ... GROUP BY session_id FROM question_attempts`
  - Streaks: Compute from ordered `DISTINCT DATE(created_at) FROM question_attempts WHERE user_id = ? ORDER BY date`
