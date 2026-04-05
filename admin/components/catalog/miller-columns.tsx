"use client";

import { useEffect, useState } from "react";
import { ChevronRight, Circle, CheckCircle2, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  fetchCatalogTree,
  type CatalogNode,
} from "@/lib/api";
import { adminQueryKeys } from "@/lib/query-keys";
import { useAdminPrincipal } from "@/lib/use-admin-principal";

const LEVEL_LABELS = ["Faculty", "Program", "Level", "Semester", "Course"];

export function MillerColumns() {
  const principalQuery = useAdminPrincipal();
  const activeBotId = principalQuery.data?.active_bot_id ?? null;
  const catalogQuery = useQuery({
    queryKey: adminQueryKeys.catalogTree(activeBotId),
    queryFn: fetchCatalogTree,
    enabled: Boolean(activeBotId),
    staleTime: 5 * 60_000,
  });
  const [catalog, setCatalog] = useState<CatalogNode[]>([]);
  const [selections, setSelections] = useState<string[]>([]);

  useEffect(() => {
    setCatalog(catalogQuery.data ?? []);
    setSelections([]);
  }, [catalogQuery.data]);

  // Derive the columns from the selection path
  const columns: { label: string; items: CatalogNode[]; selectedCode: string | null }[] = [];

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
  return (
    <div className="rounded-lg border bg-card">
      {catalogQuery.isLoading ? (
        <div className="flex h-[500px] items-center justify-center text-sm text-muted-foreground">
          <Loader2 className="mr-2 size-4 animate-spin" />
          Loading catalog...
        </div>
      ) : catalogQuery.isError ? (
        <div className="flex h-[500px] items-center justify-center text-sm text-destructive">
          Unable to load catalog.
        </div>
      ) : (
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

                        {/* Chevron for parent nodes / spacer for leaves */}
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
      )}

      {/* Breadcrumb */}
      {!catalogQuery.isError && selections.length > 0 && (
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
