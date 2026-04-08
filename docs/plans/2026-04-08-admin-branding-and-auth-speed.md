# Admin Branding And Auth Speed Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rename the shared admin product UI to "Telegram Bot Console" and reduce perceived admin auth/session-validation latency.

**Architecture:** Keep bot workspace identities unchanged while updating only the shared admin brand surfaces. Speed up auth by removing avoidable frontend principal revalidation and throttling backend session `last_seen` writes so session validation does less work per request.

**Tech Stack:** Next.js 15, React 19, TanStack Query, FastAPI, SQLAlchemy, Python

---

### Task 1: Rename shared admin branding surfaces

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\admin\app\layout.tsx`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\admin\app\login\page.tsx`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\admin\app\set-password\page.tsx`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\admin\components\admin-shell.tsx`

**Step 1:** Replace `Adarkwa Admin` and related shared admin product copy with `Telegram Bot Console`.

**Step 2:** Keep workspace names such as `Adarkwa` and `Tanjah` unchanged.

### Task 2: Remove redundant frontend auth validation

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\admin\app\login\page.tsx`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\admin\middleware.ts`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\admin\lib\query-keys.ts`

**Step 1:** Stop the login page from doing an eager `/admin/auth/me` round-trip on every visit.

**Step 2:** Seed the shared `admin-principal` React Query cache from a successful login result so the next route does not immediately re-fetch the same principal.

**Step 3:** Let middleware handle simple cookie-based redirects for auth pages.

### Task 3: Throttle backend session touch writes

**Files:**
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\src\domains\admin\auth_service.py`
- Modify: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_admin_auth_service.py`

**Step 1:** Only update `last_seen_at` when the previous touch is stale enough to matter.

**Step 2:** Add/adjust tests to prove session validation still works and recent validations do not write repeatedly.

### Task 4: Verify

**Files:**
- Test: `C:\Users\Kevin\Projects\Telegram_Bots\Quizzers\Adarkwa_Study_Bot\tests\test_admin_auth_service.py`

**Step 1:** Run targeted auth tests.

**Step 2:** Run admin frontend `lint`.

**Step 3:** Run admin frontend `build`.
