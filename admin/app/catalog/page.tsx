"use client";

import { useEffect, useMemo, useState } from "react";

import { AdminShell } from "@/components/admin-shell";
import { CatalogTree } from "@/components/catalog/catalog-tree";
import { CourseOfferingForm } from "@/components/catalog/course-offering-form";
import {
  adminApi,
  type CatalogNode,
  type CatalogOfferingValue,
} from "@/lib/api";

const fallbackTree: CatalogNode[] = [
  {
    kind: "faculty",
    code: "eng",
    name: "Faculty of Engineering",
    active: true,
    children: [
      {
        kind: "program",
        code: "cpen",
        name: "Computer Engineering",
        active: true,
        children: [
          {
            kind: "level",
            code: "l100",
            name: "Level 100",
            active: true,
            children: [
              {
                kind: "semester",
                code: "sem1",
                name: "Semester One",
                active: true,
                children: [
                  {
                    kind: "course",
                    code: "cpen101",
                    name: "Introduction to Computing",
                    active: true,
                    children: [],
                  },
                  {
                    kind: "course",
                    code: "cpen103",
                    name: "Engineering Mathematics",
                    active: true,
                    children: [],
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  },
  {
    kind: "faculty",
    code: "sci",
    name: "Faculty of Sciences",
    active: true,
    children: [
      {
        kind: "program",
        code: "stat",
        name: "Statistics",
        active: true,
        children: [
          {
            kind: "level",
            code: "l200",
            name: "Level 200",
            active: true,
            children: [
              {
                kind: "semester",
                code: "sem2",
                name: "Semester Two",
                active: true,
                children: [
                  {
                    kind: "course",
                    code: "stat205",
                    name: "Probability Theory",
                    active: true,
                    children: [],
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  },
];

function findFirstCoursePath(node: CatalogNode, ancestors: CatalogNode[] = []): CatalogNode[] | null {
  const path = [...ancestors, node];

  if (node.kind === "course") {
    return path;
  }

  for (const child of node.children) {
    const childPath = findFirstCoursePath(child, path);
    if (childPath) {
      return childPath;
    }
  }

  return null;
}

function buildDraftFromPath(path: CatalogNode[]): CatalogOfferingValue {
  const findCode = (kind: CatalogNode["kind"]) =>
    path.find((node) => node.kind === kind)?.code ?? "";
  const course = path.at(-1);

  return {
    faculty_code: findCode("faculty"),
    program_code: findCode("program"),
    level_code: findCode("level"),
    semester_code: findCode("semester"),
    course_code: findCode("course"),
    is_active: course?.active ?? true,
  };
}

function deriveInitialDraft(tree: CatalogNode[]): CatalogOfferingValue {
  for (const node of tree) {
    const path = findFirstCoursePath(node);
    if (path) {
      return buildDraftFromPath(path);
    }
  }

  return {
    faculty_code: tree[0]?.code ?? "",
    program_code: tree[0]?.children[0]?.code ?? "",
    level_code: tree[0]?.children[0]?.children[0]?.code ?? "",
    semester_code: tree[0]?.children[0]?.children[0]?.children[0]?.code ?? "",
    course_code: tree[0]?.children[0]?.children[0]?.children[0]?.children[0]?.code ?? "",
    is_active: true,
  };
}

function resolveBranch(tree: CatalogNode[], selection: CatalogOfferingValue) {
  const faculty =
    tree.find((node) => node.kind === "faculty" && node.code === selection.faculty_code) ??
    tree[0] ??
    null;
  const programs = faculty?.children.filter((node) => node.kind === "program") ?? [];
  const program = programs.find((node) => node.code === selection.program_code) ?? programs[0] ?? null;
  const levels = program?.children.filter((node) => node.kind === "level") ?? [];
  const level = levels.find((node) => node.code === selection.level_code) ?? levels[0] ?? null;
  const semesters = level?.children.filter((node) => node.kind === "semester") ?? [];
  const semester = semesters.find((node) => node.code === selection.semester_code) ?? semesters[0] ?? null;
  const courses = semester?.children.filter((node) => node.kind === "course") ?? [];
  const course = courses.find((node) => node.code === selection.course_code) ?? courses[0] ?? null;

  return {
    faculty,
    programs,
    program,
    levels,
    level,
    semesters,
    semester,
    courses,
    course,
  };
}

function buildDraftFromBranch(tree: CatalogNode[], selection: CatalogOfferingValue) {
  const branch = resolveBranch(tree, selection);

  return {
    faculty_code: branch.faculty?.code ?? "",
    program_code: branch.program?.code ?? "",
    level_code: branch.level?.code ?? "",
    semester_code: branch.semester?.code ?? "",
    course_code: branch.course?.code ?? "",
    is_active: branch.course?.active ?? true,
  };
}

function buildOptionGroups(tree: CatalogNode[], selection: CatalogOfferingValue) {
  const branch = resolveBranch(tree, selection);

  return {
    faculties: tree.map((node) => ({ code: node.code, name: node.name, active: node.active })),
    programs: branch.programs.map((node) => ({ code: node.code, name: node.name, active: node.active })),
    levels: branch.levels.map((node) => ({ code: node.code, name: node.name, active: node.active })),
    semesters: branch.semesters.map((node) => ({ code: node.code, name: node.name, active: node.active })),
    courses: branch.courses.map((node) => ({ code: node.code, name: node.name, active: node.active })),
  };
}

function getBranchLabel(tree: CatalogNode[], selection: CatalogOfferingValue) {
  const branch = resolveBranch(tree, selection);

  return [
    branch.faculty?.name,
    branch.program?.name,
    branch.level?.name,
    branch.semester?.name,
    branch.course?.name,
  ]
    .filter(Boolean)
    .join(" / ");
}

export default function CatalogPage() {
  const [tree, setTree] = useState<CatalogNode[]>(fallbackTree);
  const [draft, setDraft] = useState<CatalogOfferingValue>(() => deriveInitialDraft(fallbackTree));
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let isMounted = true;

    void adminApi
      .fetchCatalogTree()
      .then((nodes) => {
        if (!isMounted || nodes.length === 0) {
          return;
        }

        setTree(nodes);
      })
      .catch(() => undefined);

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    setDraft((current) => buildDraftFromBranch(tree, current));
  }, [tree]);

  const optionGroups = useMemo(() => buildOptionGroups(tree, draft), [draft, tree]);
  const branchLabel = useMemo(() => getBranchLabel(tree, draft), [draft, tree]);

  async function handleSave() {
    setIsSaving(true);
    try {
      await adminApi.saveCatalogOffering(draft);
    } catch {
      // Keep the editor responsive even if the live catalog endpoint is not ready yet.
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <AdminShell>
      <div className="module-page">
        <section className="module-hero panel">
          <div className="module-hero__copy">
            <p className="eyebrow">Catalog management</p>
            <h1>Keep faculties, programs, levels, and offerings database-owned.</h1>
            <p className="lead">
              Edit the academic structure without redeploys, then sync it back into the bot
              path through cached read endpoints.
            </p>
            <div className="module-toolbar">
              <button className="primary-btn" type="button" onClick={handleSave} disabled={isSaving}>
                {isSaving ? "Saving..." : "Save offering"}
              </button>
            </div>
          </div>
          <div className="module-hero__aside">
            <div className="insight-grid">
              <article className="insight-card">
                <span>Branch</span>
                <strong>{branchLabel || "No selection"}</strong>
                <p>Current faculty to course route reflected in the editor.</p>
              </article>
              <article className="insight-card">
                <span>Faculties</span>
                <strong>{tree.length}</strong>
                <p>Hierarchies can be refreshed without touching application code.</p>
              </article>
            </div>
          </div>
        </section>

        <section className="module-grid module-grid--catalog">
          <CatalogTree
            nodes={tree}
            onSelect={(node, ancestors) => {
              const path = findFirstCoursePath(node, ancestors) ?? [...ancestors, node];
              setDraft(buildDraftFromPath(path));
            }}
            selection={draft}
          />

          <CourseOfferingForm
            isSaving={isSaving}
            onChange={(next) => setDraft(buildDraftFromBranch(tree, next))}
            onSubmit={handleSave}
            options={optionGroups}
            value={draft}
          />
        </section>
      </div>
    </AdminShell>
  );
}
