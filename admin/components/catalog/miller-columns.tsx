"use client";

import { useState, useCallback } from "react";
import { ChevronRight, Circle, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MOCK_CATALOG, type CatalogEntry } from "@/lib/mock-data";

const LEVEL_LABELS = ["Faculty", "Program", "Level", "Semester", "Course"];

export function MillerColumns() {
  const [catalog, setCatalog] = useState(MOCK_CATALOG);
  const [selections, setSelections] = useState<string[]>([]);

  // Derive the columns from the selection path
  const columns: { label: string; items: CatalogEntry[]; selectedCode: string | null }[] = [];

  let currentItems = catalog;
  for (let depth = 0; depth < LEVEL_LABELS.length; depth++) {
    const selectedCode = selections[depth] ?? null;
    columns.push({
      label: LEVEL_LABELS[depth],
      items: currentItems,
      selectedCode,
    });

    if (!selectedCode) break;
    const selected = currentItems.find((item) => item.code === selectedCode);
    if (!selected?.children || selected.children.length === 0) break;
    currentItems = selected.children;
  }

  function handleSelect(depth: number, code: string) {
    setSelections((prev) => {
      const next = prev.slice(0, depth);
      next[depth] = code;
      return next;
    });
  }

  function handleToggleActive(path: string[], code: string) {
    setCatalog((prev) => {
      const next = JSON.parse(JSON.stringify(prev)) as CatalogEntry[];
      let items = next;
      for (const segment of path) {
        const parent = items.find((i) => i.code === segment);
        if (!parent?.children) return prev;
        items = parent.children;
      }
      const target = items.find((i) => i.code === code);
      if (!target) return prev;
      target.active = !target.active;
      toast.success(
        `${target.name} is now ${target.active ? "active" : "inactive"}`,
      );
      return next;
    });
  }

  // Derive the path for toggle (parent codes leading to current column)
  function getPathForDepth(depth: number) {
    return selections.slice(0, depth);
  }

  return (
    <div className="rounded-lg border bg-card">
      <div className="flex divide-x overflow-x-auto">
        {columns.map((col, depth) => (
          <div key={depth} className="min-w-[220px] flex-1">
            {/* Column header */}
            <div className="sticky top-0 border-b bg-muted/50 px-3 py-2">
              <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {col.label}
              </span>
              <Badge variant="secondary" className="ml-2 text-[10px]">
                {col.items.length}
              </Badge>
            </div>

            {/* Column items */}
            <ScrollArea className="h-[500px]">
              <div className="p-1">
                {col.items.length === 0 ? (
                  <p className="px-3 py-8 text-center text-xs text-muted-foreground">
                    No items
                  </p>
                ) : (
                  col.items.map((item) => {
                    const isSelected = col.selectedCode === item.code;
                    const hasChildren = item.children && item.children.length > 0;
                    const isLeaf = !hasChildren;

                    return (
                      <div
                        key={item.code}
                        className={cn(
                          "group flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors cursor-pointer",
                          isSelected
                            ? "bg-accent text-accent-foreground"
                            : "hover:bg-accent/50",
                        )}
                        onClick={() => handleSelect(depth, item.code)}
                      >
                        {/* Active indicator */}
                        {item.active ? (
                          <CheckCircle2 className="size-3.5 shrink-0 text-emerald-500" />
                        ) : (
                          <Circle className="size-3.5 shrink-0 text-muted-foreground/40" />
                        )}

                        {/* Name */}
                        <span className="flex-1 truncate">{item.name}</span>

                        {/* Toggle for leaf nodes */}
                        {isLeaf && (
                          <Switch
                            checked={item.active}
                            onCheckedChange={(e) => {
                              e; // consume
                              handleToggleActive(getPathForDepth(depth), item.code);
                            }}
                            onClick={(e) => e.stopPropagation()}
                            className="scale-75"
                          />
                        )}

                        {/* Chevron for parent nodes */}
                        {hasChildren && (
                          <ChevronRight
                            className={cn(
                              "size-4 shrink-0 text-muted-foreground transition-transform",
                              isSelected && "text-foreground",
                            )}
                          />
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </ScrollArea>
          </div>
        ))}

        {/* Empty placeholder columns */}
        {columns.length < LEVEL_LABELS.length && columns[columns.length - 1]?.selectedCode && (
          <div className="min-w-[220px] flex-1 flex items-center justify-center text-muted-foreground">
            <p className="text-xs">Select an item to expand</p>
          </div>
        )}
      </div>

      {/* Breadcrumb */}
      {selections.length > 0 && (
        <div className="border-t px-4 py-2">
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            {selections.map((code, i) => {
              let items = catalog;
              for (let j = 0; j < i; j++) {
                const parent = items.find((item) => item.code === selections[j]);
                if (parent?.children) items = parent.children;
              }
              const item = items.find((it) => it.code === code);
              return (
                <span key={i} className="flex items-center gap-1">
                  {i > 0 && <ChevronRight className="size-3" />}
                  <span className={i === selections.length - 1 ? "text-foreground font-medium" : ""}>
                    {item?.name ?? code}
                  </span>
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
