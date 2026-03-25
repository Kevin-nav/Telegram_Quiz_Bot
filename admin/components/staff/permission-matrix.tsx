"use client";

import type { AdminPermission } from "@/lib/api";

type PermissionMatrixProps = {
  permissions: AdminPermission[];
  value: string[];
  onChange: (next: string[]) => void;
};

function toggleValue(values: string[], value: string) {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

export function PermissionMatrix({ permissions, value, onChange }: PermissionMatrixProps) {
  const grouped = permissions.reduce<Record<string, AdminPermission[]>>((acc, permission) => {
    const group = permission.code.split(".")[0] ?? "other";
    (acc[group] ??= []).push(permission);
    return acc;
  }, {});

  return (
    <section className="matrix-shell">
      <div className="panel-header">
        <div>
          <p className="panel-kicker">Permission matrix</p>
          <h2>Direct grants</h2>
        </div>
        <span className="panel-badge">Scoped</span>
      </div>

      <div className="matrix-grid">
        {Object.entries(grouped).map(([group, grants]) => (
          <article className="matrix-card" key={group}>
            <div className="matrix-card__head">
              <strong>{group}</strong>
              <span>{grants.length} actions</span>
            </div>
            <div className="chip-row chip-row--wrap">
              {grants.map((permission) => {
                const isActive = value.includes(permission.code);
                return (
                  <button
                    className={`toggle-chip toggle-chip--compact ${isActive ? "is-active" : ""}`}
                    key={permission.code}
                    type="button"
                    onClick={() => onChange(toggleValue(value, permission.code))}
                  >
                    <strong>{permission.name}</strong>
                    <span>{permission.code}</span>
                  </button>
                );
              })}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
