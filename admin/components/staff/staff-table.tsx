"use client";

import type { AdminStaffUser } from "@/lib/api";

type StaffTableProps = {
  rows: AdminStaffUser[];
  selectedId: number | null;
  onSelect: (staffUserId: number) => void;
};

export function StaffTable({ rows, selectedId, onSelect }: StaffTableProps) {
  return (
    <div className="table-shell">
      <div className="table-shell__header">
        <div>
          <p className="panel-kicker">Staff roster</p>
          <h2>Access and mixed permissions</h2>
        </div>
        <span className="panel-badge accent">{rows.length} accounts</span>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Roles</th>
              <th>Permissions</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((staff) => {
              const isSelected = staff.id === selectedId;
              return (
                <tr className={isSelected ? "is-selected" : ""} key={staff.id}>
                  <td>
                    <button
                      className="row-button"
                      type="button"
                      onClick={() => onSelect(staff.id)}
                    >
                      <strong>{staff.display_name || staff.email}</strong>
                      <span>{staff.email}</span>
                    </button>
                  </td>
                  <td>
                    <div className="chip-row">
                      {staff.roles.length > 0 ? (
                        staff.roles.map((role) => (
                          <span className="chip" key={role}>
                            {role}
                          </span>
                        ))
                      ) : (
                        <span className="muted-text">No roles</span>
                      )}
                    </div>
                  </td>
                  <td>
                    <span className="muted-text">{staff.permissions.length} grants</span>
                  </td>
                  <td>
                    <span
                      className={`status-pill ${staff.is_active ? "is-active" : "is-muted"}`}
                    >
                      {staff.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
