"use client";

import type { CatalogNode, CatalogOfferingValue } from "@/lib/api";

type CatalogTreeProps = {
  nodes: CatalogNode[];
  selection: CatalogOfferingValue | null;
  onSelect: (node: CatalogNode, ancestors: CatalogNode[]) => void;
};

function matchesSelection(node: CatalogNode, selection: CatalogOfferingValue | null) {
  if (!selection) {
    return false;
  }

  switch (node.kind) {
    case "faculty":
      return selection.faculty_code === node.code;
    case "program":
      return selection.program_code === node.code;
    case "level":
      return selection.level_code === node.code;
    case "semester":
      return selection.semester_code === node.code;
    case "course":
      return selection.course_code === node.code;
    default:
      return false;
  }
}

function CatalogBranch({
  node,
  ancestors,
  selection,
  onSelect,
}: {
  node: CatalogNode;
  ancestors: CatalogNode[];
  selection: CatalogOfferingValue | null;
  onSelect: (node: CatalogNode, ancestors: CatalogNode[]) => void;
}) {
  const isSelected = matchesSelection(node, selection);

  return (
    <div className={`tree-node ${isSelected ? "is-selected" : ""}`}>
      <button
        className="tree-node__header"
        type="button"
        onClick={() => onSelect(node, ancestors)}
      >
        <span className="tree-node__kind">{node.kind}</span>
        <div>
          <strong>{node.name}</strong>
          <p>{node.code}</p>
        </div>
        <span className={`status-pill ${node.active === false ? "is-muted" : "is-active"}`}>
          {node.active === false ? "Inactive" : "Active"}
        </span>
      </button>

      {node.children.length > 0 ? (
        <div className="tree-node__children">
          {node.children.map((child) => (
            <CatalogBranch
              ancestors={[...ancestors, node]}
              key={`${node.kind}:${node.code}:${child.kind}:${child.code}`}
              node={child}
              onSelect={onSelect}
              selection={selection}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function CatalogTree({ nodes, selection, onSelect }: CatalogTreeProps) {
  return (
    <section className="tree-shell">
      <div className="panel-header">
        <div>
          <p className="panel-kicker">Catalog tree</p>
          <h2>Faculty to course hierarchy</h2>
        </div>
        <span className="panel-badge accent">{nodes.length} faculties</span>
      </div>

      <div className="tree-root">
        {nodes.map((node) => (
          <CatalogBranch
            ancestors={[]}
            key={`${node.kind}:${node.code}`}
            node={node}
            onSelect={onSelect}
            selection={selection}
          />
        ))}
      </div>
    </section>
  );
}
