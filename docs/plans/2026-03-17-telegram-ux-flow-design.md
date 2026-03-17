# Telegram UX Flow Design

## Goal

Design the first real Telegram product flow for `@Adarkwa_Study_Bot` so students can move from `/start` to a usable study home, manage their academic context, and start quizzes with minimal friction.

## Scope

This design covers the first UX slice only:

- `/start` routing
- first-time profile setup
- returning-student home screen
- course/context management
- quiz entry from the home screen
- lightweight performance and help entry points

This design does not cover:

- advanced adaptive engine UX
- admin/dashboard flows
- gamification
- long-form analytics reporting
- rich issue-report workflows

## Current Constraints

- The current bot implementation only has a basic `/start` command and no real study navigation.
- The academic hierarchy remains the same as documented in `docs/academic_structure.md`.
- The active academic dataset for now is **first semester**, and that should shape future seeding and filtering.
- `AskTheSage` is a useful reference for patterns, but not something to replicate directly.

## Recommended Approach

Use a **home-first Telegram UX**:

- first-time users are guided through a one-time academic setup flow
- returning users land on a study home screen
- the home screen becomes the main interaction hub
- academic drill-down happens only when needed

This is preferred over a fully conversation-first model because it keeps repeat usage fast and makes the bot feel like a lightweight study app instead of a repeated setup wizard.

## Lessons Borrowed From AskTheSage

Useful patterns to reuse:

- remembered faculty/program preferences
- inline-keyboard drill-down
- quiz resume path
- concise result messaging
- issue-report affordance during a quiz

Patterns to avoid copying:

- long repeated setup conversations
- large handler files mixing transport, business logic, and persistence
- verbose default performance output
- too much durable flow state living only in Telegram conversation memory

## Product Flow

### 1. Welcome Screen

Entry point: `/start`

If the student has no completed study profile:

- show a short welcome message
- present:
  - `Set Up Study Profile`
  - `Help`

If the student already has a completed study profile:

- route directly to the home screen

### 2. Study Profile Setup

Setup is a guided drill-down using inline keyboards:

1. Faculty
2. Program
3. Level
4. Semester
5. Course

Each setup screen should include:

- a short summary of selections made so far
- `Back`
- `Cancel`

The selected semester is explicitly stored, even though first semester is the only active seeded dataset for now.

### 3. Home Screen

The home screen is the default destination after:

- successful setup
- `/start` for returning users
- quiz completion
- quiz cancellation

Primary actions:

- `Start Quiz`
- `Continue Quiz` when an active session exists
- `Performance`
- `Change Course`
- `Study Settings`
- `Help`

The home message should show:

- faculty/program
- level/semester
- selected course

### 4. Quiz Entry Mini-Flow

`Start Quiz` should never force a full academic re-selection.

It should:

- use the saved course if present
- request a course only if missing
- ask for question count

Suggested question count choices:

- `10 Questions`
- `20 Questions`
- `30 Questions`

### 5. In-Quiz Actions

The first UX slice should keep in-quiz controls minimal:

- `Skip`
- `Stop Quiz`
- `Report Issue`

### 6. Completion Screen

After quiz completion, show:

- score
- short encouragement
- next-step buttons:
  - `Review Performance`
  - `Start Another Quiz`
  - `Home`

## UX State Model

### Persistent State In Neon

- Telegram identity
- selected faculty
- selected program
- selected level
- selected semester
- preferred course
- onboarding completion flag

### Short-Lived State In Redis

- current setup step
- temporary selections during profile editing
- active menu/message context if needed for edits
- active quiz session pointer cache

### Durable Quiz State In Neon

- active quiz session
- course context
- quiz status
- current progress

## Service Boundaries

To keep handlers thin, the UX flow should be split into focused services:

- `profile_navigation_service`
  - faculties
  - programs
  - levels
  - semesters
  - courses
- `profile_service`
  - load/update saved academic profile
- `home_service`
  - build home screen message and available actions
- `quiz_entry_service`
  - decide whether to start fresh, continue, or request missing context

## Callback Data Strategy

Callback namespaces should be explicit from the start:

- `home:start_quiz`
- `home:continue_quiz`
- `home:performance`
- `home:change_course`
- `profile:faculty:<id>`
- `profile:program:<id>`
- `profile:level:<id>`
- `profile:semester:first`
- `profile:course:<id>`
- `profile:back`
- `profile:cancel`
- `quiz:length:10`

## Rollout Plan

Implement in this order:

1. user academic profile persistence
2. profile setup flow
3. home screen
4. `/start` routing to setup or home
5. quiz entry from home
6. continue/performance placeholders if needed
7. copy and button polish

## Acceptance Criteria

The UX slice is complete when:

- a new student can go from `/start` to a valid home screen without extra commands
- a student can set faculty, program, level, semester, and course through inline keyboards
- a returning student lands on the home screen directly
- `Start Quiz` uses saved course context
- the academic structure remains consistent with the current faculty/program model
- first semester is modeled explicitly in the profile and can be used during future seed/import work
- the code structure supports later upgrades without another UX rewrite

## Notes

- Future upgrades are expected around the home screen and quiz entry, so the first implementation should stay modular and avoid hard-coding copy or button arrangements across handlers.
- There are unrelated untracked script files in the repo at the time of writing this design; they are outside the scope of this UX plan.
