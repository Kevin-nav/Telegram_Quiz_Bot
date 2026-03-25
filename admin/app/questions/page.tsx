"use client";

import { useEffect, useMemo, useState } from "react";

import { AdminShell } from "@/components/admin-shell";
import { QuestionEditor } from "@/components/questions/question-editor";
import { QuestionTable } from "@/components/questions/question-table";
import { adminApi, type QuestionDraft, type QuestionRecord } from "@/lib/api";

const fallbackQuestions: QuestionRecord[] = [
  {
    id: 501,
    question_key: "MAT-001",
    course_id: "cpen101",
    course_slug: "intro-to-computing",
    question_text: "Which of the following best describes a compiler?",
    options: [
      "A tool that converts source code into machine code",
      "A storage system for compiled notes",
      "A text editor for source files",
      "A scheduler for operating systems",
    ],
    correct_option_text: "A tool that converts source code into machine code",
    short_explanation: "A compiler translates a high-level program into executable machine code.",
    question_type: "MCQ",
    option_count: 4,
    status: "ready",
    band: 2,
    topic_id: "programming-basics",
    cognitive_level: "Understand",
    updated_at: "2026-03-24T08:40:00Z",
  },
  {
    id: 502,
    question_key: "PHY-014",
    course_id: "stat205",
    course_slug: "probability-theory",
    question_text: "What is the probability of an event that cannot occur?",
    options: ["0", "1", "0.5", "Undefined"],
    correct_option_text: "0",
    short_explanation: "Impossible events have probability zero.",
    question_type: "MCQ",
    option_count: 4,
    status: "review",
    band: 1,
    topic_id: "probability",
    cognitive_level: "Remember",
    updated_at: "2026-03-24T10:15:00Z",
  },
  {
    id: 503,
    question_key: "ENG-019",
    course_id: "cpen103",
    course_slug: "engineering-mathematics",
    question_text: "Solve for x: 2x + 4 = 12.",
    options: ["3", "4", "5", "6"],
    correct_option_text: "4",
    short_explanation: "Subtract 4 from both sides and divide by 2.",
    question_type: "MCQ",
    option_count: 4,
    status: "draft",
    band: 1,
    topic_id: "algebra",
    cognitive_level: "Apply",
    updated_at: "2026-03-23T17:30:00Z",
  },
];

function toQuestionDraft(question: QuestionRecord | undefined): QuestionDraft {
  if (!question) {
    return {
      question_text: "",
      options_text: "",
      correct_option_text: "",
      short_explanation: "",
      question_type: "MCQ",
      status: "draft",
      band: 1,
      topic_id: "",
      cognitive_level: "",
    };
  }

  return {
    question_text: question.question_text,
    options_text: question.options.join("\n"),
    correct_option_text: question.correct_option_text,
    short_explanation: question.short_explanation ?? "",
    question_type: question.question_type,
    status: question.status,
    band: question.band,
    topic_id: question.topic_id,
    cognitive_level: question.cognitive_level ?? "",
  };
}

function toRecordFromDraft(
  draft: QuestionDraft,
  selected: QuestionRecord | undefined,
  id: number,
): QuestionRecord {
  const options = draft.options_text
    .split("\n")
    .map((option) => option.trim())
    .filter(Boolean);

  return {
    id,
    question_key: selected?.question_key ?? `NEW-${id}`,
    course_id: selected?.course_id ?? fallbackQuestions[0]?.course_id ?? "",
    course_slug: selected?.course_slug ?? fallbackQuestions[0]?.course_slug ?? "",
    question_text: draft.question_text,
    options,
    correct_option_text: draft.correct_option_text,
    short_explanation: draft.short_explanation || null,
    question_type: draft.question_type,
    option_count: options.length,
    status: draft.status,
    band: draft.band,
    topic_id: draft.topic_id,
    cognitive_level: draft.cognitive_level || null,
    updated_at: new Date().toISOString(),
  };
}

export default function QuestionsPage() {
  const [questions, setQuestions] = useState<QuestionRecord[]>(fallbackQuestions);
  const [selectedId, setSelectedId] = useState<number | null>(fallbackQuestions[0]?.id ?? null);
  const [draft, setDraft] = useState<QuestionDraft>(() => toQuestionDraft(fallbackQuestions[0]));
  const [query, setQuery] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let isMounted = true;

    void adminApi
      .listQuestions()
      .then((items) => {
        if (!isMounted || items.length === 0) {
          return;
        }

        setQuestions(items);
      })
      .catch(() => undefined);

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (selectedId === null) {
      setDraft(toQuestionDraft(undefined));
      return;
    }

    const selected = questions.find((question) => question.id === selectedId);
    if (!selected) {
      if (questions.length > 0) {
        setSelectedId(questions[0].id);
      }
      return;
    }

    setDraft(toQuestionDraft(selected));
  }, [questions, selectedId]);

  const selectedQuestion =
    selectedId === null ? null : questions.find((question) => question.id === selectedId) ?? null;

  const visibleQuestions = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return questions;
    }

    return questions.filter((question) => {
      const haystack = [
        question.question_key,
        question.question_text,
        question.course_slug,
        question.course_id,
        question.topic_id,
        question.cognitive_level ?? "",
        question.status,
      ]
        .join(" ")
        .toLowerCase();

      return haystack.includes(needle);
    });
  }, [query, questions]);

  const stats = useMemo(
    () => ({
      total: questions.length,
      ready: questions.filter((question) => question.status === "ready").length,
      review: questions.filter((question) => question.status === "review").length,
      draft: questions.filter((question) => question.status === "draft").length,
    }),
    [questions],
  );

  async function handleSave() {
    setIsSaving(true);
    try {
      const saved = await adminApi.saveQuestion(selectedId, draft);
      const nextRecord = toRecordFromDraft(draft, selectedQuestion ?? questions[0], saved.id);

      setQuestions((current) =>
        selectedId === null
          ? [nextRecord, ...current]
          : current.map((question) => (question.id === saved.id ? nextRecord : question)),
      );
      setSelectedId(saved.id);
      setDraft(toQuestionDraft(nextRecord));
    } catch {
      // Keep the editor usable against the local fallback records.
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <AdminShell>
      <div className="module-page">
        <section className="module-hero panel">
          <div className="module-hero__copy">
            <p className="eyebrow">Question bank</p>
            <h1>Correct answers, explanations, and the questions themselves.</h1>
            <p className="lead">
              Search the bank, open any item, and publish a clean revision without dropping
              the rest of the study flow.
            </p>
            <div className="module-toolbar">
              <button className="secondary-btn" type="button" onClick={() => setSelectedId(null)}>
                New question
              </button>
              <button className="primary-btn" type="button" onClick={handleSave} disabled={isSaving}>
                {isSaving ? "Saving..." : "Save question"}
              </button>
            </div>
          </div>
          <div className="module-hero__aside">
            <div className="insight-grid">
              <article className="insight-card">
                <span>Total</span>
                <strong>{stats.total}</strong>
                <p>Questions ready for editing or review.</p>
              </article>
              <article className="insight-card">
                <span>Ready</span>
                <strong>{stats.ready}</strong>
                <p>Items available to the student quiz path.</p>
              </article>
            </div>
          </div>
        </section>

        <section className="module-grid module-grid--questions">
          <QuestionTable
            onQueryChange={setQuery}
            onSelect={(questionId) => setSelectedId(questionId)}
            query={query}
            rows={visibleQuestions}
            selectedId={selectedId}
          />

          <div className="module-stack">
            <QuestionEditor
              isSaving={isSaving}
              onChange={setDraft}
              onSubmit={handleSave}
              value={draft}
            />
            <section className="module-panel panel">
              <div className="panel-header">
                <div>
                  <p className="panel-kicker">Status mix</p>
                  <h2>Review pressure at a glance</h2>
                </div>
                <span className="panel-badge muted">Live queue</span>
              </div>
              <div className="stats-grid stats-grid--compact">
                <article className="stat-card">
                  <span className="stat-label">Review</span>
                  <strong className="stat-value">{stats.review}</strong>
                  <span className="stat-detail">Items waiting on editorial sign-off.</span>
                </article>
                <article className="stat-card">
                  <span className="stat-label">Draft</span>
                  <strong className="stat-value">{stats.draft}</strong>
                  <span className="stat-detail">Still in the editing lane.</span>
                </article>
              </div>
            </section>
          </div>
        </section>
      </div>
    </AdminShell>
  );
}
