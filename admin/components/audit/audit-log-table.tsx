"use client";

import type { AuditLogEntry } from "@/lib/api";

type AuditLogTableProps = {
  rows: AuditLogEntry[];
};

export function AuditLogTable({ rows }: AuditLogTableProps) {
  return (
    <section className="table-shell">
      <div className="table-shell__header">
        <div>
          <p className="panel-kicker">Audit trail</p>
          <h2>Who changed what and when</h2>
        </div>
        <span className="panel-badge">{rows.length} entries</span>
      </div>

      <div className="table-wrap table-wrap--tall">
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Entity</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{new Date(row.created_at).toLocaleString()}</td>
                <td>{row.actor_staff_user_id ?? "System"}</td>
                <td>
                  <span className="status-pill is-active">{row.action}</span>
                </td>
                <td>
                  <div className="stack-mini">
                    <strong>{row.entity_type}</strong>
                    <span className="muted-text">{row.entity_id ?? "n/a"}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
