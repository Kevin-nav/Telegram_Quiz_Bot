# Admin Frontend Review Spec

## Purpose

This document is the review target for the `Next.js` admin frontend built for `@Adarkwa_Study_Bot`.

Use it to:

- verify that the current implementation matches the intended product surface
- identify missing pieces or regressions
- hand off review or follow-up implementation to another agent

The current frontend lives in:

- `admin/`

The backend admin API it depends on lives in:

- `src/api/admin_*.py`

## Product Goal

Build a staff-facing admin web app on a separate subdomain that allows operators to:

- manage staff access and mixed permissions
- manage faculties, programs, levels, semesters, courses, and offerings at the database level
- correct questions, answers, and explanations
- inspect audit history
- support future analytics expansion

The admin should feel like an operator console, not a generic SaaS dashboard.

## Required Stack

- `Next.js` App Router
- TypeScript
- separate frontend app under `admin/`
- API integration through `/admin/*` backend endpoints

## Current Frontend Scope

The implementation is expected to include:

- app shell and navigation
- login page
- staff page
- catalog page
- questions page
- audit page

Current route targets:

- `/`
- `/login`
- `/staff`
- `/catalog`
- `/questions`
- `/audit`

## UX Direction

The visual direction should be:

- editorial
- operations-focused
- deliberate and high-contrast
- not default-template looking

Review for:

- clear typography hierarchy
- purposeful spacing
- route-level consistency
- shell/nav coherence
- no broken encoding artifacts
- no obvious placeholder-only visual treatment

## Functional Spec

### 1. App Shell

Expected:

- persistent shell layout
- real route navigation, not hash links
- active route indication
- consistent topbar
- shared styling foundation

Review against:

- `admin/components/admin-shell.tsx`
- `admin/app/globals.css`

### 2. Login

Expected:

- dedicated `/login` page
- current scaffold may use a demo session cookie until full auth is wired
- page must build successfully in production `next build`

Review against:

- `admin/app/login/page.tsx`
- `admin/middleware.ts`

Checks:

- no App Router build errors
- no unsafe client-only routing patterns without proper suspense handling

### 3. Staff & Permissions

Expected:

- staff roster view
- create/edit staff form
- role assignment
- direct permission assignment
- save flow through admin API helper

Review against:

- `admin/app/staff/page.tsx`
- `admin/components/staff/staff-table.tsx`
- `admin/components/staff/staff-form.tsx`
- `admin/components/staff/permission-matrix.tsx`
- `admin/lib/api.ts`

Checks:

- can represent mixed roles/permissions
- supports new staff creation
- supports updating an existing staff user
- does not assume rigid single-role access only

### 4. Catalog

Expected:

- display of catalog hierarchy or offering structure
- course/offering editing surface
- integration path to catalog read/write endpoints

Review against:

- `admin/app/catalog/page.tsx`
- `admin/components/catalog/catalog-tree.tsx`
- `admin/components/catalog/course-offering-form.tsx`
- `admin/lib/api.ts`

Checks:

- reflects DB-backed catalog concept
- does not imply code-level catalog editing
- supports offerings-oriented operations

### 5. Questions

Expected:

- question list/table
- question editor
- editing path for question text, answer, and explanation

Review against:

- `admin/app/questions/page.tsx`
- `admin/components/questions/question-table.tsx`
- `admin/components/questions/question-editor.tsx`
- `admin/lib/api.ts`

Checks:

- supports operator correction workflow
- editing surface maps to backend question update capability
- reasonable fallback behavior if backend data is sparse

### 6. Audit

Expected:

- audit log listing page
- table rendering for audit entries
- basic integration path to backend audit endpoint

Review against:

- `admin/app/audit/page.tsx`
- `admin/components/audit/audit-log-table.tsx`
- `admin/lib/api.ts`

Checks:

- displays actor/action/entity/time clearly
- suitable for admin review workflows

## API Contract Expectations

The frontend should use a central API helper layer.

Review against:

- `admin/lib/api.ts`

Expected capabilities:

- fetch current admin principal
- fetch staff users
- save staff user
- update staff permissions
- fetch catalog slices
- create/update offerings
- fetch questions
- update questions
- fetch audit logs

Review questions:

- are endpoint paths aligned with backend routes?
- are payload shapes internally consistent?
- are failures handled without crashing the UI?

## Build and Quality Gates

The frontend should satisfy:

- `npm run lint`
- `npm run build`

Review should confirm both still pass after any changes.

## Known Scaffold Limits

These are acceptable for now if clearly understood:

- login/session may still be scaffolded rather than production auth
- some pages may use fallback/demo data when backend data is unavailable
- analytics page is not yet a dedicated route in the current frontend slice

These are not acceptable:

- broken route navigation
- build failures
- obvious mismatch between page intent and backend capability
- shell/layout regressions
- hardcoded visual junk or placeholder-only dead ends with no API path

## Reviewer Checklist

- confirm the app exists under `admin/`
- confirm the routes `/`, `/login`, `/staff`, `/catalog`, `/questions`, `/audit`
- confirm shell navigation uses real routes
- confirm `npm run lint` passes
- confirm `npm run build` passes
- confirm `admin/lib/api.ts` matches current backend `/admin/*` routes
- confirm staff page supports mixed role + direct permission management
- confirm catalog page reflects DB-backed catalog editing
- confirm questions page supports correction workflow
- confirm audit page renders backend audit history coherently
- confirm visual design is intentional and non-generic

## Handoff Notes

If another agent is reviewing or continuing the frontend, their first steps should be:

1. Read this spec.
2. Inspect `admin/`.
3. Run:
   - `npm install`
   - `npm run lint`
   - `npm run build`
4. Compare `admin/lib/api.ts` with `src/api/admin_*.py`.
5. Call out any mismatch between this spec and the current implementation.

## Reference Paths

- `admin/app/layout.tsx`
- `admin/app/page.tsx`
- `admin/app/login/page.tsx`
- `admin/app/staff/page.tsx`
- `admin/app/catalog/page.tsx`
- `admin/app/questions/page.tsx`
- `admin/app/audit/page.tsx`
- `admin/components/admin-shell.tsx`
- `admin/components/staff/staff-table.tsx`
- `admin/components/staff/staff-form.tsx`
- `admin/components/staff/permission-matrix.tsx`
- `admin/components/catalog/catalog-tree.tsx`
- `admin/components/catalog/course-offering-form.tsx`
- `admin/components/questions/question-table.tsx`
- `admin/components/questions/question-editor.tsx`
- `admin/components/audit/audit-log-table.tsx`
- `admin/lib/api.ts`
- `src/api/admin_auth.py`
- `src/api/admin_staff.py`
- `src/api/admin_catalog.py`
- `src/api/admin_questions.py`
- `src/api/admin_audit.py`
