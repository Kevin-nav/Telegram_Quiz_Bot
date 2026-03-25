"use client";

import { useDeferredValue } from "react";

import type { QuestionRecord } from "@/lib/api";

type QuestionTableProps = {
  rows: QuestionRecord[];
  selectedId: number | null;
  query: string;
  onQueryChange: (value: string) => void;
  onSelect: (questionId: number) => void;
};

export function QuestionTable({
  rows,
  selectedId,
  query,
  onQueryChange,
  onSelect,
}: QuestionTableProps) {
  const deferredQuery = useDeferredValue(query);
  const needle = deferredQuery.trim().toLowerCase();
  const visibleRows = needle
    ? rows.filter((row) => {
        const haystack = [
          row.question_text,
          row.course_id,
          row.topic_id,
          row.cognitive_level ?? "",
          row.status,
          row.question_key,
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(needle);
      })
    : rows;

  return (
    <section className="table-shell">
      <div className="table-shell__header">
        <div>
          <p className="panel-kicker">Question queue</p>
          <h2>Corrections, explanations, and answer checks</h2>
        </div>
        <span className="panel-badge accent">{visibleRows.length} questions</span>
      </div>

      <div className="toolbar-row">
        <label className="toolbar-search">
          <span>Search questions</span>
          <input
            placeholder="Search by topic, course, or text"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </label>
      </div>

      <div className="table-wrap table-wrap--tall">
        <table className="data-table">
          <thead>
            <tr>
              <th>Question</th>
              <th>Course</th>
              <th>Topic</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row) => {
              const isSelected = row.id === selectedId;
              return (
                <tr className={isSelected ? "is-selected" : ""} key={row.id}>
                  <td>
                    <button
                      className="row-button"
                      type="button"
                      onClick={() => onSelect(row.id)}
                    >
                      <strong>{row.question_key}</strong>
                      <span>{row.question_text}</span>
                    </button>
                  </td>
                  <td>
                    <div className="stack-mini">
                      <strong>{row.course_slug}</strong>
                      <span className="muted-text">{row.question_type}</span>
                    </div>
                  </td>
                  <td>{row.topic_id}</td>
                  <td>
                    <span className={`status-pill ${row.status === "ready" ? "is-active" : "is-muted"}`}>
                      {row.status}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
