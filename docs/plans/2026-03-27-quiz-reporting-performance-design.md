# Quiz Reporting And Performance Design

**Date:** 2026-03-27

## Goal

Improve the learner quiz experience in `@Adarkwa_Study_Bot` by:
- adding question reporting during quiz sessions
- adding answer-validity reporting after feedback
- replacing placeholder performance views with real learner stats
- upgrading end-of-quiz scoring logic and summary UI

## Current State

The current Telegram quiz flow is poll-based. Each quiz question is sent as a Telegram poll, and answer handling is driven by `PollAnswerHandler`. Question attempts already persist correctness, timing, and adaptive metadata into `question_attempts`. The home screen `Performance` entry is still a placeholder, and the end-of-quiz experience is a plain text score line.

The quiz UI currently has no support for learner issue reports, and the poll format means action buttons cannot be embedded inside the poll itself. Any reporting flow must therefore be implemented with companion inline messages and explicit interaction state.

## Design Summary

The feature will use a two-stage reporting model:

1. Question report flow while the learner is viewing the active question.
2. Answer report flow after answer feedback is shown.

The pre-answer report flow will only include reasons the learner can judge from the question prompt itself. The post-answer report flow will only include reasons that depend on the revealed answer or explanation. This keeps the UI intuitive and makes report data more actionable.

Performance and end scoring will use existing persisted quiz attempt data instead of placeholder copy. Session summaries will continue to use accuracy as the primary score while adding pace, topic, and recommendation layers for a stronger learner-facing result.

## Interaction Design

### Active Question Actions

After the bot sends each poll, it will send a companion inline-action message for the active question. This message is the control surface for per-question actions because Telegram polls do not support custom inline buttons.

The active question action message will include:
- `Report Question`

The `Report Question` flow will present these reasons:
- `Not related to course`
- `Question unclear`
- `Image/LaTeX issue`
- `Duplicate question`
- `Other`
- `Cancel`

After the learner chooses a reason, the bot will prompt for an optional free-text note as the learner's next text message and show a `Skip note` button. The learner can submit the report with only the structured reason or add more context in plain text.

### Post-Answer Actions

After feedback is sent for an answered question, the bot will show a separate answer-report action message. This is the only place where answer-validity complaints appear.

The post-answer action message will include:
- `Not correct? Report`

The answer-report flow will present these reasons:
- `Marked wrong but my answer is right`
- `Correct answer shown is wrong`
- `Explanation is wrong`
- `Other`
- `Cancel`

As with question reports, the learner can optionally send a follow-up text note or skip it.

### State And Staleness Rules

Reports are only valid for the currently active interaction target:
- question reports attach to the current unanswered or active question
- answer reports attach to the most recently answered question feedback target

If the learner taps an older report button after the quiz advances, the bot will reject it as stale and clear outdated inline controls, matching the stale callback behavior already used in the home flow.

If the learner is in a `waiting_for_report_note` state:
- the next text message is consumed as the note
- non-text messages are rejected with a short retry prompt
- the learner can tap `Skip note` or `Cancel`

Reporting never blocks quiz progress and never requires the learner to stop the session.

## Data Model

### Question Reports Table

A new `question_reports` table will persist learner issue reports as first-class operational data.

Planned fields:
- `id`
- `user_id`
- `session_id`
- `course_id`
- `question_id` nullable canonical database id when available
- `question_key`
- `question_index`
- `report_scope` with values `question` or `answer`
- `report_reason`
- `report_note` nullable
- `report_status` default `open`
- `report_metadata` JSON
- `created_at`

`report_metadata` should capture enough frozen context for later review:
- selected option ids or text if already answered
- correct option label or text
- whether the user was marked correct
- whether the item had LaTeX or rendered assets
- arrangement hash or config index
- time taken and time allocated if available
- explanation text presence

This data should remain queryable by course, question, reason, and scope without requiring analytics event replay.

## Application Architecture

### Quiz State

The interactive quiz state will be extended to track:
- active question action message id
- active answer action message id
- pending report draft context
- pending report note state

The draft context should include:
- session id
- question identifier
- question index
- report scope
- chosen reason
- whether a note is still pending

This state fits naturally in Redis alongside existing quiz session state because it is short-lived, user-specific, and conversation-scoped.

### Services

New or expanded services:
- `QuestionReportService`
  - validates report scope and reason
  - builds persistence payloads from session/question context
  - stores and clears pending report-note state
- `PerformanceService`
  - aggregates learner-friendly metrics from `question_attempts` and course progress
  - builds summary objects for home/performance screens
- `QuizSessionService`
  - emits companion action messages
  - stores enough recent-answer context for answer reporting
  - produces richer completion summaries

### Repository Layer

A dedicated `QuestionReportRepository` will handle inserts and future admin queries. Performance read logic can initially live in a service layer on top of `QuestionAttemptRepository` and `StudentCourseStateRepository`.

## Performance Experience

### Home Performance View

The `Performance` screen should replace the placeholder with a concise study dashboard built from real attempt history.

Suggested content:
- quizzes completed
- questions answered
- overall accuracy
- average response time
- strongest recent course
- weakest recent course
- one short recommendation line

If the learner has little or no history, the view should degrade cleanly:
- show core counters that exist
- explain that more detail appears after more quiz sessions

### Metrics

Initial performance metrics should be simple and reliable:
- overall accuracy from all attempts
- course accuracy from attempts grouped by course
- average pace from `time_taken_seconds`
- recent trend from last N completed sessions or last N attempts
- weak topics from repeated misses in the most recent window

The design deliberately avoids premature complex mastery scoring in the learner-facing UI. Adaptive difficulty remains internal; the UI should expose stable, explainable measures.

## End-Of-Quiz Scoring And Summary

### Scoring Principles

Accuracy remains the primary displayed score:
- `score / total answered`
- percentage

Secondary interpretation layers:
- pace compared to allocated time
- topic breakdown within the session
- recommendation based on weak areas

### Completion Summary

When a quiz completes, the result message should include:
- course name
- answered count and total count
- score and percentage
- result tier such as `Excellent`, `Solid`, `Needs Review`
- average response time
- pace interpretation
- strongest topic
- weakest topic
- next-step recommendation

The copy should read like a study coach summary rather than a raw counter.

### Early-Finish Compatibility

The summary builder should support partial sessions so the same polished UI can be reused if an early-stop path is added. It should clearly distinguish:
- completed session
- partial session with `answered X of Y`

## Error Handling

The reporting flow should fail safely:
- if report persistence fails, the learner gets a short retry message
- quiz progression continues even if report logging fails
- stale report callbacks are rejected
- missing note state is treated as cancelled or expired

The performance screen should tolerate sparse data:
- avoid divide-by-zero or empty-history failures
- return a minimal but valid summary

## Testing Strategy

Tests should cover:
- question action message emission after sending a poll
- answer action message emission after feedback
- question-scope report reason flow
- answer-scope report reason flow
- optional note capture from the next text message
- skip-note and cancel flows
- stale callback rejection for outdated report messages
- report persistence payload correctness
- performance summary generation from attempt history
- richer end-of-quiz summary copy and metrics

## Out Of Scope

This design does not include:
- admin UI for reviewing reports
- automated moderation of submitted reports
- advanced learner charts or graphs
- changes to adaptive selection logic beyond surfacing better summaries

Those can follow after learner-side reporting and performance flows are stable.
