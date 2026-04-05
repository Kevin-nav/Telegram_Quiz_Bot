# Admin Platform UI/UX Flow & Architecture Plan

## Goal

Establish a highly functional, secure, and purely administrative internal tool UI/UX flow. The design prioritizes speed, clarity, and safety over consumer-facing flashiness. It respects the constraints of a small team, requires intentional and restrained design (no generic auth-card sprawl), and enforces distinct boundary zones for different permission levels.

## 1. The Authentication Journey (Security-First UX)

The authentication flow is the gatekeeper. It feels strictly internal and secure.

*   **The Login Screen (`/login`)**
    *   **UX Flow:** A minimalist, centered form on a solid background (matching the app's neutral palette—no unnecessary gradients or illustrations).
    *   **Inputs:** Email and Password.
    *   **Behavior:** No "Sign Up" or "Forgot Password" links (as self-service resets are explicitly out of scope for Phase 1). Features a clear, disabled-while-loading "Log In" button.
*   **The Forced Transition (`/set-password`)**
    *   **UX Flow:** If `must_change_password` is true (new account or admin reset), the user is immediately routed here. They cannot bypass this page to see the dashboard.
    *   **Inputs:** Current Password (the temporary one provided by the super-admin), New Password, and Confirm New Password.
    *   **Behavior:** The UI layout remains identical to the login screen to maintain visual continuity. Upon success, they are smoothly transitioned into the authenticated Shell.

## 2. The Global App Shell

Provides a persistent navigation frame that adapts to the user's permission level.

*   **Layout Structure:** A collapsible side navigation (Sidebar) paired with a clean, low-profile top header.
*   **Top Header:** Contains context (e.g., Breadcrumbs: *Catalog / Engineering / BSc Computer Science*), the current environment (Production), and a minimal User dropdown (Display Name, Role, and a "Log Out" action).
*   **Sidebar Navigation:** Role-gated visibility. A `content_editor` won't even see the "Staff & Permissions" menu item.
    *   Dashboard
    *   Question Bank
    *   Catalog
    *   Staff Access
    *   Audit Logs
    *   *(Analytics - can be a separate tab or merged into the dashboard initially)*

## 3. Core Workflow: Staff Management (`/staff`)

*Visibility: `super_admin` or users with `staff.view`/`staff.create`.*

*   **List View:** A dense data table (using TanStack Table) showing Staff Name, Email, Status (Active/Inactive toggle badge), and Assigned Roles.
*   **The "Create Staff" Modal (or Slide-out Panel):**
    *   A right-side slide-out panel (Drawer) is used since creating a staff member involves multiple steps (Profile -> Roles -> Direct Permissions -> Temp Password). It allows the user to reference the main table while filling out the form.
    *   **Permissions Matrix UX:** Permissions are grouped logically (e.g., a "Catalog" section with View/Edit toggles, a "Questions" section). Clicking a preset Role (like `content_editor`) auto-checks the respective boxes, but allows for granular overrides.
*   **The "Reset Password" Flow:**
    *   Accessed via an action menu (`...`) on a user's table row.
    *   Pops a small, dangerous-action modal confirming the reset and providing an input for the Super Admin to set the new temporary password.

## 4. Core Workflow: Catalog Management (`/catalog`)

*The catalog is deeply nested (Faculty -> Program -> Level -> Semester -> Course).*

*   **UX Flow:** A dual-pane layout or a Drill-down Breadcrumb interface.
    *   **Left Pane (Tree/List):** A vertical list of Faculties. Clicking one reveals its Programs, and so on.
    *   **Right Pane (Details):** When a specific "Offering" (Program + Level + Semester + Course) is selected, the right pane shows its details.
*   **Activation Toggles:** Since catalog changes take effect immediately via Redis invalidation, "Active / Inactive" states are prominently displayed as toggle switches right on the detail pane, perhaps with a confirmation toast: *"BSc CompSci Semester 1 activated. App clients will reflect this change shortly."*

## 5. Core Workflow: Content Operations (`/questions`)

*The most heavily used section by content editors.*

*   **List View (The Inventory):**
    *   A high-density table featuring a sticky filter bar at the top.
    *   **Crucial Filters:** Course Dropdown (searchable), Status (Draft, Review, Ready, Archived) as quick-toggle pill buttons, and Cognitive Level.
*   **The Editor (`/questions/[id]` or full-screen Modal):**
    *   Provides ample screen real estate.
    *   **Top Action Bar:** Shows the current status prominently with a dropdown to transition state (e.g., moving from "Draft" to "Review").
    *   **Content Area:** Rich text or Markdown editor for the Question.
    *   **Options Area:** A dynamic list of inputs for choices. A clear radio button next to each to mark the "Correct" answer.
    *   **Explanation:** A secondary text area for the rationale.
    *   **Metadata Sidebar:** Showing `last_edited_by`, `last_edited_at`, and an audit-trail preview of recent changes to this specific question.

## 6. Visibility & Accountability: Audit Logs (`/audit`)

*The source of truth for all mutations.*

*   **UX Flow:** A purely chronological, read-only feed.
*   **Table Design:** Actor, Action (badge colored by mutation type, e.g., green for create, yellow for update, red for deactivate), Entity, and Timestamp.
*   **Detail View:** Clicking a row expands it down (Accordion style) or opens a right-side drawer to display a raw JSON diff (Before & After payloads) of what exactly changed. This is highly readable for a developer or super-admin auditing an issue.

## 7. Dashboard (`/`)

*The landing zone. It should be highly actionable.*

*   **Actionable Widgets:**
    *   "Content Awaiting Review" (with a direct link to the Question Bank filtered to `status=review`).
    *   "Recent Staff Activity" (a mini feed of the Audit Log).
    *   "Catalog Health" (e.g., courses with fewer than 10 active questions).

## UX Principles to Enforce During Rebuild

1.  **No destructive deletes:** Everywhere there is a "Delete" concept, the UI should frame it as "Deactivate" or "Archive" with visual indicators (grayed out rows).
2.  **Slide-outs over Modals for complex forms:** Staff creation and complex question editing should use right-side slide-out panels so the user doesn't lose the context of the list they were looking at.
3.  **Keyboard efficiency:** For the Question Editor specifically, saving and adding a new option should be achievable via keyboard shortcuts to speed up data entry.
4.  **Optimistic UI with clear Toast notifications:** When a catalog status is toggled, update the UI instantly, but show a clear success/error toast in the corner since it's mutating a live DB and invalidating Redis.
