"use client";

import type { QuestionDraft } from "@/lib/api";

type QuestionEditorProps = {
  value: QuestionDraft;
  isSaving?: boolean;
  onChange: (next: QuestionDraft) => void;
  onSubmit: () => void;
};

function updateField(
  value: QuestionDraft,
  onChange: (next: QuestionDraft) => void,
  key: keyof QuestionDraft,
  nextValue: string | number,
) {
  onChange({
    ...value,
    [key]: nextValue,
  });
}

export function QuestionEditor({
  value,
  isSaving = false,
  onChange,
  onSubmit,
}: QuestionEditorProps) {
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
          <p className="panel-kicker">Question editor</p>
          <h2>Text, options, and explanation</h2>
        </div>
        <span className="panel-badge muted">Audit logged</span>
      </div>

      <div className="form-grid">
        <label className="field field-span">
          <span>Question text</span>
          <textarea
            rows={6}
            value={value.question_text}
            onChange={(event) => updateField(value, onChange, "question_text", event.target.value)}
          />
        </label>

        <label className="field field-span">
          <span>Options, one per line</span>
          <textarea
            rows={6}
            value={value.options_text}
            onChange={(event) => updateField(value, onChange, "options_text", event.target.value)}
          />
        </label>

        <label className="field">
          <span>Correct answer</span>
          <input
            type="text"
            value={value.correct_option_text}
            onChange={(event) =>
              updateField(value, onChange, "correct_option_text", event.target.value)
            }
          />
        </label>

        <label className="field">
          <span>Status</span>
          <select
            value={value.status}
            onChange={(event) => updateField(value, onChange, "status", event.target.value)}
          >
            <option value="draft">draft</option>
            <option value="review">review</option>
            <option value="ready">ready</option>
            <option value="archived">archived</option>
          </select>
        </label>

        <label className="field">
          <span>Band</span>
          <input
            type="number"
            min={0}
            max={10}
            value={value.band}
            onChange={(event) =>
              updateField(value, onChange, "band", Number(event.target.value || 0))
            }
          />
        </label>

        <label className="field">
          <span>Cognitive level</span>
          <input
            type="text"
            value={value.cognitive_level}
            onChange={(event) =>
              updateField(value, onChange, "cognitive_level", event.target.value)
            }
            placeholder="Applying"
          />
        </label>

        <label className="field">
          <span>Topic id</span>
          <input
            type="text"
            value={value.topic_id}
            onChange={(event) => updateField(value, onChange, "topic_id", event.target.value)}
            placeholder="topic-01"
          />
        </label>

        <label className="field">
          <span>Question type</span>
          <input
            type="text"
            value={value.question_type}
            onChange={(event) => updateField(value, onChange, "question_type", event.target.value)}
            placeholder="MCQ"
          />
        </label>

        <label className="field field-span">
          <span>Short explanation</span>
          <textarea
            rows={4}
            value={value.short_explanation}
            onChange={(event) =>
              updateField(value, onChange, "short_explanation", event.target.value)
            }
          />
        </label>
      </div>

      <div className="form-actions">
        <span className="muted-text">Saving writes an audit log entry and refreshes caches.</span>
        <button className="primary-btn" disabled={isSaving} type="submit">
          {isSaving ? "Saving..." : "Save question"}
        </button>
      </div>
    </form>
  );
}
