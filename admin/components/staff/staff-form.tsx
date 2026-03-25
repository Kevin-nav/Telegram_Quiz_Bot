"use client";

import type { AdminRole, StaffFormValue } from "@/lib/api";

type StaffFormProps = {
  value: StaffFormValue;
  roleOptions: AdminRole[];
  isSaving?: boolean;
  onChange: (next: StaffFormValue) => void;
  onSubmit: () => void;
  submitLabel: string;
};

function toggleValue(values: string[], value: string) {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

export function StaffForm({
  value,
  roleOptions,
  isSaving = false,
  onChange,
  onSubmit,
  submitLabel,
}: StaffFormProps) {
  return (
    <form
      className="form-shell"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="panel-header">
        <div>
          <p className="panel-kicker">Staff editor</p>
          <h2>Profile and lifecycle</h2>
        </div>
        <span className="panel-badge muted">Editable</span>
      </div>

      <div className="form-grid">
        <label className="field">
          <span>Email</span>
          <input
            type="email"
            value={value.email}
            onChange={(event) => onChange({ ...value, email: event.target.value })}
            placeholder="staff@example.com"
          />
        </label>

        <label className="field">
          <span>Display name</span>
          <input
            type="text"
            value={value.display_name}
            onChange={(event) => onChange({ ...value, display_name: event.target.value })}
            placeholder="Ada K."
          />
        </label>
      </div>

      <div className="field">
        <span>Role presets</span>
        <div className="toggle-row">
          {roleOptions.map((role) => {
            const isActive = value.role_codes.includes(role.code);
            return (
              <button
                className={`toggle-chip ${isActive ? "is-active" : ""}`}
                type="button"
                key={role.code}
                onClick={() =>
                  onChange({
                    ...value,
                    role_codes: toggleValue(value.role_codes, role.code),
                  })
                }
              >
                <strong>{role.name}</strong>
                <span>{role.code}</span>
              </button>
            );
          })}
        </div>
      </div>

      <label className="field field-inline">
        <input
          checked={value.is_active}
          type="checkbox"
          onChange={(event) => onChange({ ...value, is_active: event.target.checked })}
        />
        <div>
          <span>Active access</span>
          <p>Inactive staff keep their record but lose permissions at the guard layer.</p>
        </div>
      </label>

      <div className="form-actions">
        <span className="muted-text">
          Direct permissions are edited in the matrix beside this form.
        </span>
        <button className="primary-btn" disabled={isSaving} type="submit">
          {isSaving ? "Saving..." : submitLabel}
        </button>
      </div>
    </form>
  );
}
