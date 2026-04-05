"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Inbox,
  CheckCircle2,
  XCircle,
  Clock,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { AdminShell } from "@/components/admin-shell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AdminErrorState, AdminLoadingState, AdminRetryButton } from "@/components/admin-page-state";
import { cn } from "@/lib/utils";
import {
  fetchAdminPrincipal,
  listReports,
  updateReportStatus,
  type ReportListItem,
} from "@/lib/api";

const statusConfig = {
  open: { label: "Open", icon: Clock, color: "text-amber-600 bg-amber-50 border-amber-200" },
  resolved: { label: "Resolved", icon: CheckCircle2, color: "text-emerald-600 bg-emerald-50 border-emerald-200" },
  dismissed: { label: "Dismissed", icon: XCircle, color: "text-zinc-500 bg-zinc-50 border-zinc-200" },
};

export default function ReportsPage() {
  const queryClient = useQueryClient();
  const principalQuery = useQuery({
    queryKey: ["admin-principal"],
    queryFn: fetchAdminPrincipal,
    retry: false,
  });
  const reportsQuery = useQuery({
    queryKey: ["reports"],
    queryFn: () => listReports(),
    retry: false,
  });

  const canEditReports = principalQuery.data?.permission_codes?.includes("questions.edit") ?? false;
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const updateStatusMutation = useMutation({
    mutationFn: ({ reportId, status }: { reportId: number; status: "resolved" | "dismissed" }) =>
      updateReportStatus(reportId, status),
    onSuccess: async (updated) => {
      toast.success(updated.status === "resolved" ? "Report resolved" : "Report dismissed");
      await queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Unable to update report.");
    },
  });

  useEffect(() => {
    const nextReports = reportsQuery.data?.items ?? [];
    setReports(nextReports);
    if (nextReports.length === 0) {
      setSelectedId(null);
      return;
    }
    if (selectedId === null || !nextReports.some((report) => report.id === selectedId)) {
      setSelectedId(nextReports.find((report) => report.status === "open")?.id ?? nextReports[0].id);
    }
  }, [reportsQuery.data, selectedId]);

  const selected = useMemo(
    () => reports.find((report) => report.id === selectedId) ?? null,
    [reports, selectedId],
  );

  const openCount = reportsQuery.data?.open_count ?? reports.filter((r) => r.status === "open").length;

  if (reportsQuery.isLoading && !reportsQuery.data) {
    return (
      <AdminLoadingState
        title="Reports"
        description="Student-flagged questions from the Telegram bot."
        message="Loading reports..."
      />
    );
  }

  if (reportsQuery.isError && !reportsQuery.data) {
    return (
      <AdminErrorState
        title="Reports"
        description="Student-flagged questions from the Telegram bot."
        message="Unable to load reports right now."
        action={
          <AdminRetryButton
            onClick={() => {
              void principalQuery.refetch();
              void reportsQuery.refetch();
            }}
            isPending={principalQuery.isFetching || reportsQuery.isFetching}
          />
        }
      />
    );
  }

  function handleAction(id: number, action: "resolve" | "dismiss") {
    updateStatusMutation.mutate({
      reportId: id,
      status: action === "resolve" ? "resolved" : "dismissed",
    });
  }

  return (
    <AdminShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Reports</h2>
            <p className="text-sm text-muted-foreground">
              Student-flagged questions from the Telegram bot.
            </p>
          </div>
          {openCount > 0 ? <Badge variant="secondary">{openCount} open</Badge> : null}
        </div>

        <div className="rounded-lg border bg-card">
          <div className="grid min-h-[550px] md:grid-cols-[320px_1fr] divide-x">
            <ScrollArea className="h-[550px]">
              <div className="p-1">
                {reports.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <Inbox className="mb-2 size-8" />
                    <p className="text-sm">No reports</p>
                  </div>
                ) : (
                  reports.map((report) => {
                    const config = statusConfig[report.status];
                    const isActive = selectedId === report.id;

                    return (
                      <button
                        key={report.id}
                        onClick={() => setSelectedId(report.id)}
                        className={cn(
                          "w-full rounded-md px-3 py-3 text-left transition-colors",
                          isActive ? "bg-accent text-accent-foreground" : "hover:bg-accent/50",
                        )}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate text-sm font-medium">
                            {report.question_key}
                          </span>
                          <Badge
                            variant="outline"
                            className={cn("shrink-0 text-[10px] border", config.color)}
                          >
                            {config.label}
                          </Badge>
                        </div>
                        <p className="mt-1 truncate text-xs text-muted-foreground">
                          {report.course_name}
                        </p>
                        <p className="mt-0.5 truncate text-xs text-muted-foreground">
                          @{report.student_username} · {new Date(report.created_at).toLocaleDateString()}
                        </p>
                      </button>
                    );
                  })
                )}
              </div>
            </ScrollArea>

            <div className="p-6">
              {selected ? (
                <div className="space-y-6">
                  <div>
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-semibold">{selected.question_key}</h3>
                      <Badge
                        variant="outline"
                        className={cn("text-xs border", statusConfig[selected.status].color)}
                      >
                        {statusConfig[selected.status].label}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {selected.course_name} · Reported by @{selected.student_username}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(selected.created_at).toLocaleString()}
                    </p>
                  </div>

                  <Separator />

                  <div>
                    <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Question
                    </span>
                    <div className="mt-2 rounded-lg border bg-muted/30 p-4">
                      <p className="text-sm leading-relaxed">{selected.question_text}</p>
                    </div>
                  </div>

                  <div>
                    <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Student&apos;s Reasoning
                    </span>
                    <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-4">
                      <p className="text-sm leading-relaxed text-amber-900">
                        &ldquo;{selected.student_reasoning}&rdquo;
                      </p>
                      <p className="mt-2 text-xs text-amber-600">
                        — @{selected.student_username}
                      </p>
                    </div>
                  </div>

                  {selected.status === "open" && canEditReports ? (
                    <div className="flex flex-wrap gap-2 pt-2">
                      <Button size="sm" onClick={() => handleAction(selected.id, "resolve")}>
                        <CheckCircle2 className="mr-2 size-3.5" />
                        Resolve
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="ml-auto text-muted-foreground"
                        onClick={() => handleAction(selected.id, "dismiss")}
                      >
                        <Trash2 className="mr-2 size-3.5" />
                        Dismiss
                      </Button>
                    </div>
                  ) : selected.status === "open" ? (
                    <div className="rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground">
                      You can review this report, but you do not have permission to resolve it.
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="flex h-full flex-col items-center justify-center text-muted-foreground">
                  <Inbox className="mb-2 size-10 text-muted-foreground/30" />
                  <p className="text-sm">Select a report to view details</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AdminShell>
  );
}
