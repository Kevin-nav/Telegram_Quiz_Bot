"use client";

import { useEffect, useMemo, useState } from "react";

import { AdminShell } from "@/components/admin-shell";
import { AuditLogTable } from "@/components/audit/audit-log-table";
import { adminApi, type AuditLogEntry } from "@/lib/api";

const fallbackLogs: AuditLogEntry[] = [
  {
    id: 1,
    actor_staff_user_id: 101,
    action: "question.updated",
    entity_type: "question",
    entity_id: "501",
    before_data: { status: "review" },
    after_data: { status: "ready" },
    created_at: "2026-03-25T06:42:00Z",
  },
  {
    id: 2,
    actor_staff_user_id: 102,
    action: "staff.created",
    entity_type: "staff_user",
    entity_id: "105",
    before_data: null,
    after_data: { role: "analytics_viewer" },
    created_at: "2026-03-25T05:31:00Z",
  },
  {
    id: 3,
    actor_staff_user_id: 103,
    action: "catalog.updated",
    entity_type: "offering",
    entity_id: "cpen101-sem1",
    before_data: { active: false },
    after_data: { active: true },
    created_at: "2026-03-25T04:17:00Z",
  },
];

export default function AuditPage() {
  const [rows, setRows] = useState<AuditLogEntry[]>(fallbackLogs);
  const [query, setQuery] = useState("");

  useEffect(() => {
    let isMounted = true;

    void adminApi
      .listAuditLogs()
      .then((items) => {
        if (!isMounted || items.length === 0) {
          return;
        }

        setRows(items);
      })
      .catch(() => undefined);

    return () => {
      isMounted = false;
    };
  }, []);

  const filteredRows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return rows;
    }

    return rows.filter((row) => {
      const haystack = [
        row.action,
        row.entity_type,
        row.entity_id ?? "",
        String(row.actor_staff_user_id ?? "system"),
        JSON.stringify(row.before_data ?? {}),
        JSON.stringify(row.after_data ?? {}),
      ]
        .join(" ")
        .toLowerCase();

      return haystack.includes(needle);
    });
  }, [query, rows]);

  const stats = useMemo(
    () => ({
      total: rows.length,
      content: rows.filter((row) => row.entity_type === "question").length,
      catalog: rows.filter((row) => row.entity_type === "offering").length,
      staff: rows.filter((row) => row.entity_type === "staff_user").length,
    }),
    [rows],
  );

  return (
    <AdminShell>
      <div className="module-page">
        <section className="module-hero panel">
          <div className="module-hero__copy">
            <p className="eyebrow">Audit log</p>
            <h1>Trace every sensitive edit from the staff desk to the database.</h1>
            <p className="lead">
              Permission changes, catalog edits, and question revisions all land here with
              before-and-after context for quick review.
            </p>
          </div>
          <div className="module-hero__aside">
            <label className="toolbar-search">
              <span>Search the log</span>
              <input
                placeholder="Search by action, entity, or actor"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
          </div>
        </section>

        <section className="stats-grid stats-grid--compact">
          <article className="stat-card">
            <span className="stat-label">Entries</span>
            <strong className="stat-value">{stats.total}</strong>
            <span className="stat-detail">Total rows currently in view.</span>
          </article>
          <article className="stat-card">
            <span className="stat-label">Content edits</span>
            <strong className="stat-value">{stats.content}</strong>
            <span className="stat-detail">Question bank changes captured.</span>
          </article>
          <article className="stat-card">
            <span className="stat-label">Catalog ops</span>
            <strong className="stat-value">{stats.catalog}</strong>
            <span className="stat-detail">Faculty, program, and offering updates.</span>
          </article>
          <article className="stat-card">
            <span className="stat-label">Staff ops</span>
            <strong className="stat-value">{stats.staff}</strong>
            <span className="stat-detail">Account creation and permission edits.</span>
          </article>
        </section>

        <AuditLogTable rows={filteredRows} />
      </div>
    </AdminShell>
  );
}
