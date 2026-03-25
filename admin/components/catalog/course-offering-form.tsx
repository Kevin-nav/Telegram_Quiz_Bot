"use client";

import type { CatalogItem, CatalogOfferingValue } from "@/lib/api";

type OptionGroups = {
  faculties: CatalogItem[];
  programs: CatalogItem[];
  levels: CatalogItem[];
  semesters: CatalogItem[];
  courses: CatalogItem[];
};

type CourseOfferingFormProps = {
  value: CatalogOfferingValue;
  options: OptionGroups;
  isSaving?: boolean;
  onChange: (next: CatalogOfferingValue) => void;
  onSubmit: () => void;
};

function updateField(
  value: CatalogOfferingValue,
  onChange: (next: CatalogOfferingValue) => void,
  key: keyof CatalogOfferingValue,
  nextValue: string | boolean,
) {
  onChange({
    ...value,
    [key]: nextValue,
  });
}

export function CourseOfferingForm({
  value,
  options,
  isSaving = false,
  onChange,
  onSubmit,
}: CourseOfferingFormProps) {
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
          <p className="panel-kicker">Offering editor</p>
          <h2>Publish or revise course access</h2>
        </div>
        <span className="panel-badge muted">Syncs to DB</span>
      </div>

      <div className="form-grid">
        <label className="field">
          <span>Faculty</span>
          <select
            value={value.faculty_code}
            onChange={(event) => updateField(value, onChange, "faculty_code", event.target.value)}
          >
            {options.faculties.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Program</span>
          <select
            value={value.program_code}
            onChange={(event) => updateField(value, onChange, "program_code", event.target.value)}
          >
            {options.programs.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Level</span>
          <select
            value={value.level_code}
            onChange={(event) => updateField(value, onChange, "level_code", event.target.value)}
          >
            {options.levels.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Semester</span>
          <select
            value={value.semester_code}
            onChange={(event) => updateField(value, onChange, "semester_code", event.target.value)}
          >
            {options.semesters.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field field-span">
          <span>Course</span>
          <select
            value={value.course_code}
            onChange={(event) => updateField(value, onChange, "course_code", event.target.value)}
          >
            {options.courses.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="field field-inline">
        <input
          checked={value.is_active}
          type="checkbox"
          onChange={(event) => updateField(value, onChange, "is_active", event.target.checked)}
        />
        <div>
          <span>Active offering</span>
          <p>Inactive offerings remain in the database but disappear from the student path.</p>
        </div>
      </label>

      <div className="form-actions">
        <span className="muted-text">
          Changes should invalidate cached catalog lookups immediately.
        </span>
        <button className="primary-btn" disabled={isSaving} type="submit">
          {isSaving ? "Saving..." : "Save offering"}
        </button>
      </div>
    </form>
  );
}
