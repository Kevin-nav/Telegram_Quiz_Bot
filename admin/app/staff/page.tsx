"use client";

import { useEffect, useMemo, useState } from "react";

import { AdminShell } from "@/components/admin-shell";
import { PermissionMatrix } from "@/components/staff/permission-matrix";
import { StaffForm } from "@/components/staff/staff-form";
import { StaffTable } from "@/components/staff/staff-table";
import {
  adminApi,
  type AdminPermission,
  type AdminRole,
  type AdminStaffUser,
  type StaffFormValue,
} from "@/lib/api";

const roleOptions: AdminRole[] = [
  {
    code: "super_admin",
    name: "Super admin",
    description: "Full access across staff, catalog, content, and audit actions.",
  },
  {
    code: "content_editor",
    name: "Content editor",
    description: "Can revise questions and explanations, then queue them for review.",
  },
  {
    code: "catalog_manager",
    name: "Catalog manager",
    description: "Can maintain faculties, programs, levels, and offerings.",
  },
  {
    code: "analytics_viewer",
    name: "Analytics viewer",
    description: "Can inspect dashboards and performance trends without editing.",
  },
];

const permissionOptions: AdminPermission[] = [
  { code: "analytics.view", name: "View analytics", description: null },
  { code: "analytics.export", name: "Export analytics", description: null },
  { code: "audit.view", name: "View audit log", description: null },
  { code: "catalog.view", name: "View catalog", description: null },
  { code: "catalog.edit", name: "Edit catalog", description: null },
  { code: "questions.view", name: "View question bank", description: null },
  { code: "questions.edit", name: "Edit questions", description: null },
  { code: "questions.publish", name: "Publish questions", description: null },
  { code: "staff.view", name: "View staff", description: null },
  { code: "staff.create", name: "Create staff", description: null },
  { code: "staff.edit_permissions", name: "Edit permissions", description: null },
];

const fallbackStaff: AdminStaffUser[] = [
  {
    id: 101,
    email: "ops@adarkwa.study",
    display_name: "Ops Admin",
    is_active: true,
    roles: ["super_admin"],
    permissions: permissionOptions.map((permission) => permission.code),
  },
  {
    id: 102,
    email: "content@adarkwa.study",
    display_name: "Content Desk",
    is_active: true,
    roles: ["content_editor"],
    permissions: ["questions.view", "questions.edit", "questions.publish"],
  },
  {
    id: 103,
    email: "catalog@adarkwa.study",
    display_name: "Catalog Keeper",
    is_active: true,
    roles: ["catalog_manager"],
    permissions: ["catalog.view", "catalog.edit", "audit.view"],
  },
  {
    id: 104,
    email: "analytics@adarkwa.study",
    display_name: "Analytics Reader",
    is_active: false,
    roles: ["analytics_viewer"],
    permissions: ["analytics.view", "audit.view"],
  },
];

function createEmptyStaffForm(): StaffFormValue {
  return {
    email: "",
    display_name: "",
    is_active: true,
    role_codes: [],
  };
}

function toStaffFormValue(staff: AdminStaffUser | undefined): StaffFormValue {
  if (!staff) {
    return createEmptyStaffForm();
  }

  return {
    email: staff.email,
    display_name: staff.display_name ?? "",
    is_active: staff.is_active,
    role_codes: staff.roles,
  };
}

export default function StaffPage() {
  const [staffRows, setStaffRows] = useState<AdminStaffUser[]>(fallbackStaff);
  const [selectedId, setSelectedId] = useState<number | null>(fallbackStaff[0]?.id ?? null);
  const [form, setForm] = useState<StaffFormValue>(toStaffFormValue(fallbackStaff[0]));
  const [permissionCodes, setPermissionCodes] = useState<string[]>(fallbackStaff[0]?.permissions ?? []);
  const [query, setQuery] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let isMounted = true;

    void adminApi
      .listStaffUsers()
      .then((items) => {
        if (!isMounted || items.length === 0) {
          return;
        }

        setStaffRows(items);
      })
      .catch(() => undefined);

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (selectedId === null) {
      setForm(createEmptyStaffForm());
      setPermissionCodes([]);
      return;
    }

    const selected = staffRows.find((staff) => staff.id === selectedId);
    if (!selected) {
      if (staffRows.length > 0) {
        setSelectedId(staffRows[0].id);
      }
      return;
    }

    setForm(toStaffFormValue(selected));
    setPermissionCodes(selected.permissions);
  }, [selectedId, staffRows]);

  const visibleRows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return staffRows;
    }

    return staffRows.filter((staff) => {
      const haystack = [
        staff.email,
        staff.display_name ?? "",
        staff.roles.join(" "),
        staff.permissions.join(" "),
        staff.is_active ? "active" : "inactive",
      ]
        .join(" ")
        .toLowerCase();

      return haystack.includes(needle);
    });
  }, [query, staffRows]);

  const selectedStaff =
    selectedId === null ? null : staffRows.find((staff) => staff.id === selectedId) ?? null;

  async function handleSave() {
    setIsSaving(true);
    try {
      const saved = await adminApi.saveStaffUser(selectedId, form);
      const nextStaff: AdminStaffUser = {
        ...saved,
        roles: form.role_codes,
        permissions: permissionCodes,
      };

      setStaffRows((current) =>
        selectedId === null
          ? [nextStaff, ...current]
          : current.map((staff) => (staff.id === saved.id ? nextStaff : staff)),
      );
      setSelectedId(saved.id);
      setForm(toStaffFormValue(nextStaff));

      await adminApi.updateStaffPermissions(saved.id, permissionCodes);
    } catch {
      // Keep the admin UI usable with the seeded roster if the backend is not ready yet.
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <AdminShell>
      <div className="module-page">
        <section className="module-hero panel">
          <div className="module-hero__copy">
            <p className="eyebrow">Staff & permissions</p>
            <h1>Mix preset roles with direct grants for each operator.</h1>
            <p className="lead">
              Create new staff accounts, adjust what they can see or do, and keep every
              change auditable from the same editorial control surface.
            </p>
            <div className="module-toolbar">
              <button className="secondary-btn" type="button" onClick={() => setSelectedId(null)}>
                New staff
              </button>
              <button className="primary-btn" type="button" onClick={handleSave} disabled={isSaving}>
                {isSaving ? "Saving..." : "Save access"}
              </button>
            </div>
          </div>
          <div className="module-hero__aside">
            <div className="insight-grid">
              <article className="insight-card">
                <span>Accounts</span>
                <strong>{staffRows.length}</strong>
                <p>Database-backed staff identities with active and inactive states.</p>
              </article>
              <article className="insight-card">
                <span>Selected</span>
                <strong>{selectedStaff ? selectedStaff.display_name ?? selectedStaff.email : "New"}</strong>
                <p>{selectedStaff ? selectedStaff.roles.join(" / ") : "Create a new account and assign access."}</p>
              </article>
            </div>
          </div>
        </section>

        <section className="module-grid module-grid--staff">
          <StaffTable
            rows={visibleRows}
            selectedId={selectedId}
            onSelect={(staffUserId) => setSelectedId(staffUserId)}
          />

          <div className="module-stack">
            <StaffForm
              isSaving={isSaving}
              onChange={setForm}
              onSubmit={handleSave}
              roleOptions={roleOptions}
              submitLabel={selectedId === null ? "Create staff" : "Update staff"}
              value={form}
            />
            <PermissionMatrix
              onChange={setPermissionCodes}
              permissions={permissionOptions}
              value={permissionCodes}
            />
          </div>
        </section>

        <section className="module-panel panel">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Roster search</p>
              <h2>Find the right operator quickly</h2>
            </div>
            <label className="toolbar-search">
              <span>Search staff</span>
              <input
                placeholder="Search by name, email, role, or permission"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
          </div>
        </section>
      </div>
    </AdminShell>
  );
}
