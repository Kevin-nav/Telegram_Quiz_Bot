# Admin Auth Design

## Goal

Replace the current scaffolded admin login with real staff authentication based on:

- `email + password`
- server-side cookie sessions
- super-admin-managed temporary passwords
- forced password change on first login or reset

This auth system must fit the existing admin UI language and avoid introducing generic auth screens that clash with the current product.

## Product Constraints

- The team is small, about five people.
- `staff_id` remains internal only and is not part of the login UX.
- `super_admin` creates staff accounts and resets passwords manually.
- Self-service email reset is intentionally out of scope for phase 1.
- The current admin frontend design should be preserved and extended carefully.

## Core Decisions

- Authentication uses `email + password` only.
- Sessions are server-side and stored in the database.
- The browser receives an HTTP-only session cookie.
- `super_admin` can issue temporary passwords.
- Temporary-password login forces a password change before normal access.
- Existing demo auth bridges such as `admin_session` and `X-Admin-User-Id` must be removed from the real auth path.

## Security Model

### Password Handling

- Passwords are stored only as secure hashes.
- Use `argon2` or `bcrypt`; prefer `argon2` if the dependency fits cleanly.
- Temporary passwords are treated like any other password and are never stored in plaintext after issue.
- Passwords must never be returned by APIs, logged, or written into audit payloads.

### Session Handling

- Create a new `admin_sessions` table for active sessions.
- Store only a hash of the session token in the database.
- Send the raw token only in a secure HTTP-only cookie.
- Support session revocation on logout and password reset.
- Support expiry using `expires_at`.

### Account State

Add to `staff_users`:

- `password_hash`
- `must_change_password`
- `password_updated_at`
- `last_login_at`
- optional later:
  - `failed_login_attempts`
  - `locked_until`

Phase 1 can omit lockout if that keeps scope tighter, but the schema should leave room for it.

## Database Design

### `staff_users`

Required additions:

- `password_hash: string | null`
- `must_change_password: bool`
- `password_updated_at: datetime | null`
- `last_login_at: datetime | null`

Meaning:

- newly created or reset users have a password hash for a temporary password
- `must_change_password = true` blocks full admin access until they set a new password

### `admin_sessions`

Recommended fields:

- `id`
- `staff_user_id`
- `session_token_hash`
- `created_at`
- `expires_at`
- `last_seen_at`
- `revoked_at`
- optional:
  - `ip_address`
  - `user_agent`

## Backend Flow

### 1. Create Staff User

- `super_admin` creates a staff account.
- They provide:
  - email
  - display name
  - roles
  - permissions
  - temporary password
- Backend hashes the temporary password.
- Backend sets `must_change_password = true`.
- Backend audit logs the action.

### 2. Login

- User submits `email + password`.
- Backend verifies:
  - account exists
  - account is active
  - password hash matches
- Backend creates a new session row.
- Backend sets HTTP-only cookie.
- If `must_change_password = true`, the frontend is redirected to `set-password`.

### 3. Force Password Change

- Authenticated but transitional user enters `set-password`.
- User submits:
  - current password
  - new password
- Backend verifies current password again.
- Backend updates password hash.
- Backend sets `must_change_password = false`.
- Backend updates `password_updated_at`.
- Backend keeps or rotates the session depending on implementation simplicity; either is acceptable if handled consistently.

### 4. Super-Admin Password Reset

- `super_admin` triggers reset for a staff user.
- Backend accepts a new temporary password.
- Backend hashes it and stores it.
- Backend sets `must_change_password = true`.
- Backend revokes all active sessions for that user.
- Backend audit logs the reset without storing plaintext password.

### 5. Logout

- Backend revokes current session.
- Backend clears session cookie.

## Frontend Flow

### Required Pages

- `/login`
- `/set-password`

The existing admin routes stay protected:

- `/`
- `/staff`
- `/catalog`
- `/questions`
- `/audit`

### Middleware / Route Guarding

- Unauthenticated users redirect to `/login`.
- Authenticated users with `must_change_password = true` redirect to `/set-password`.
- Authenticated users with a valid session and completed password setup can access normal admin pages.

### UI Constraints

New auth screens must follow the current UI language:

- reuse the current typography and spacing system
- avoid introducing excessive card stacking
- avoid adding gradients where they are not already justified by the design
- preserve the current shell’s visual intent
- keep the auth UI intentional and restrained

In practice:

- `set-password` should feel like part of the current admin UI, not a generic auth template
- use the same fonts, tone, spacing, and surface treatment already established

## API Surface

### Auth Routes

Required:

- `POST /admin/auth/login`
- `POST /admin/auth/logout`
- `GET /admin/auth/me`
- `POST /admin/auth/set-password`

Expected response behavior:

- `me` returns:
  - principal
  - permissions
  - `must_change_password`
- `login` sets the session cookie
- `logout` clears the session cookie

### Staff Routes

Required additions:

- `POST /admin/staff`
- `PATCH /admin/staff/{id}`
- `POST /admin/staff/{id}/reset-password`

Only `super_admin` or users with appropriate staff-management permissions should access these.

## Permissions

Auth-specific permissions should include at minimum:

- `staff.view`
- `staff.create`
- `staff.edit_permissions`

Resetting passwords should be limited to high-privilege staff. It can either:

- reuse `staff.edit_permissions`, or
- use a dedicated permission like `staff.reset_password`

Recommended: add `staff.reset_password` for clarity.

## Session Cookie Rules

Required:

- `HttpOnly`
- `SameSite=Lax`
- `Secure` in production
- explicit expiry
- clear cookie on logout

Optional later:

- session rotation on privilege changes
- sliding expiry

## Audit Requirements

Audit these actions:

- staff account created
- staff password reset
- password changed
- login success
- logout
- failed login attempts if you want more security visibility later

Do not store plaintext passwords in audit records.

## Local Development Shape

After this auth work, local flow should become:

1. run migrations
2. bootstrap a first super-admin with email and temporary password
3. log in through `/login`
4. hit forced `set-password`
5. continue into the admin UI normally

The following should be removed from the real auth flow:

- demo `admin_session` cookie
- `X-Admin-User-Id` request header bridge

## Review Checklist

- login uses `email + password`, not `staff_id`
- session cookie is server-side and HTTP-only
- `must_change_password` flow blocks access correctly
- super-admin password reset works
- existing admin pages respect real session auth
- auth UI matches the current admin design language
- no generic auth-card sprawl or unnecessary gradients
