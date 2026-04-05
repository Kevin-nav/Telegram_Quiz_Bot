# Admin Platform: UI/UX Flow & Architecture Master Plan

## 1. Core Tech Stack & Design Language
*   **Frontend:** Next.js (App Router), React Query (data fetching & caching), Tailwind CSS, shadcn/ui.
*   **Backend:** FastAPI, PostgreSQL (custom `admin_sessions` and `staff_users` tables).
*   **Design Vibe (SaaS Grade):** Strict, minimalist, and highly legible. 
    *   *Palette:* `Zinc` or `Slate` neutral tones. Pure white (`bg-white` or `bg-zinc-50`) backgrounds.
    *   *Typography:* **Geist** or **Plus Jakarta Sans** for the UI, with a highly legible serif (or system sans) for question previews.
    *   *Anti-Patterns to Avoid:* No generic "auth-card sprawl", no unnecessary gradients, no heavy drop-shadows.

---

## 2. Security & Authentication Architecture (Offline-First)

The auth system relies strictly on `email + password` with secure server-side sessions, fully managed in-house without external providers.

### Backend/Database Specs (FastAPI)
*   **Hashing:** Passwords hashed via `argon2` (never stored/logged in plaintext).
*   **Sessions:** Stored in an `admin_sessions` table (containing `session_token_hash`, `expires_at`, `user_agent`).
*   **Transport:** FastAPI issues a cryptographically secure, `HttpOnly`, `SameSite=Lax`, `Secure` (in prod) cookie. 
*   **Account State:** `staff_users` table includes a critical `must_change_password` boolean.

### Frontend Flow & Middleware (Next.js)
*   **Route Guarding:** Next.js Middleware checks for the presence of the session cookie. Unauthenticated users are hard-redirected to `/login`.
*   **The Login Screen (`/login`):** A severe, minimalist form centered on the screen. Email and password only. No "Forgot Password" or "Sign Up" links. 
*   **The Forced Transition (`/set-password`):** 
    *   If React Query fetches `/admin/auth/me` and returns `must_change_password: true`, the user is locked to `/set-password`. 
    *   **UX Rule:** This page must visually match the login screen perfectly (same container width, same typography) so it feels like a seamless security step, not a disjointed template.

---

## 3. Global App Shell & Navigation

*   **Layout:** A collapsible shadcn `<Sidebar>` paired with a clean, low-profile top header.
*   **Command Palette (`Cmd + K`):** A global search overlay allowing super-admins to instantly jump to specific courses, staff profiles, or student IDs without clicking through menus.
*   **User Dropdown:** Minimalist. Shows Name, Role, and two actions: "Revoke All Other Sessions" (a great security feature utilizing your `admin_sessions` table) and "Log Out".

---

## 4. Core Workflow: Staff Management (`/staff`)

*   **List View:** A dense `TanStack Table` showing Staff Name, Email, Status, and Roles.
*   **Creation & Editing (`<Sheet>` Slide-out):**
    *   Clicking "Create Staff" slides a panel in from the right. This prevents context-loss.
    *   The Super-Admin sets the email, name, selects permissions (checkbox matrix), and sets the *Temporary Password*.
*   **Password Resets:** Triggered via a row-action `[...]` menu. Opens an aggressive, red-tinted `<Dialog>` warning the admin that active sessions will be revoked.

---

## 5. Core Workflow: Catalog Management (`/catalog`)

Because the catalog is deeply nested (Faculty -> Program -> Level -> Semester -> Course), traditional clicking gets tedious.
*   **Miller Columns UI:** We will use shadcn's `<Resizable />` panels to create a multi-pane horizontal layout (like macOS Finder).
    *   *Column 1:* Faculties. Clicking one opens its Programs in Column 2.
    *   *Column 2:* Programs. Clicking one opens Levels in Column 3, etc.
*   **Instant Updates:** Toggling a Semester/Course "Active" state updates the UI instantly (Optimistic UI via React Query) and fires a minimalist `<Sonner>` toast confirming the database sync.

---

## 6. The Question Engine (`/questions`)

Since questions contain complex JSON, LaTeX formatting, and rigid logic rules, the UX here must be flawless.

*   **The Editor UI (Split-Pane Mode):**
    *   **Top Toggle:** A switch between "Visual Editor" (UI inputs) and "Raw JSON" (a Monaco/CodeMirror text area for developers to paste direct payloads).
    *   **Visual Editor Logic Constraint:** You have fields for Question Text, Options (Dynamic list), and Explanation. 
    *   **Crucial Validation Rule:** If a user clicks a radio button to change the `correct_option`, the UI **must immediately clear the `short_explanation` field** and highlight it in red. This forces the editor to write a new explanation matching the new correct answer, preventing logical desyncs.
    *   **Live Preview:** The right side of the screen constantly renders the question text and LaTeX (using `react-latex-next` or KaTeX) exactly as it will appear in the Telegram Bot.

*   **Bulk Import (`/questions/import`):**
    *   A massive dropzone area. Dropping a JSON array triggers a client-side validation check (Ensuring all keys like `cognitive_level`, `has_latex`, and `band` exist).
    *   Shows a summary ("45 Valid, 2 Errors") before committing to FastAPI.

---

## 7. Telegram Bot Analytics & Student Reports (`/analytics`)

Replacing the "Audit Logs" with actionable data about the Telegram bot's usage.

*   **Overview Dashboard:**
    *   Built with Recharts + shadcn `<Card>` components.
    *   KPIs: Active Bot Users (24h), Total Questions Served, Global Accuracy Rate.
*   **Student Leaderboard & CRM:**
    *   Since students take different courses, we rank them by normalized metrics: **"Questions Answered"**, **"Current Daily Streak"**, and **"Overall Accuracy %"**.
    *   Clicking a student opens a `<Sheet>` showing their Telegram ID/Username, their most active course, and a button to "Award / Flag" them.
*   **The "Reported Inbox" (`/reports`):**
    *   When a student flags a question in the Telegram bot (e.g., "Math is wrong"), it lands here.
    *   UI resembles an email inbox. Left side: list of reports. Right side: The specific question, the student's reasoning, and quick-action buttons: `[Edit Question]`, `[Hide Question]`, `[Dismiss Report]`.
