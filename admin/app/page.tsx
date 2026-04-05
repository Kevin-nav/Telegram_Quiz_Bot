"use client";

import { useQuery } from "@tanstack/react-query";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Users,
  MessageSquare,
  Target,
  Flame,
  ArrowRight,
  Loader2,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { AdminShell } from "@/components/admin-shell";
import { AdminLoadingState } from "@/components/admin-page-state";
import {
  fetchAnalyticsSummary,
  listQuestions,
  listReports,
  listStaffUsers,
  type AnalyticsSummaryResponse,
  type ReportListItem,
  type QuestionRecord,
  type AdminStaffUser,
} from "@/lib/api";
import { adminQueryKeys } from "@/lib/query-keys";
import { useAdminPrincipal } from "@/lib/use-admin-principal";

const trendIcons = {
  up: TrendingUp,
  down: TrendingDown,
  flat: Minus,
};

const kpiIcons = [Users, MessageSquare, Target, Flame];

function SectionError({ message, onRetry, isRetrying }: { message: string; onRetry: () => void; isRetrying: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
      <AlertTriangle className="size-5 text-muted-foreground/60" />
      <p className="text-xs text-muted-foreground">{message}</p>
      <Button variant="ghost" size="sm" onClick={onRetry} disabled={isRetrying}>
        <RefreshCw className={`mr-1 size-3 ${isRetrying ? "animate-spin" : ""}`} />
        Retry
      </Button>
    </div>
  );
}

function SectionLoading({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-8">
      <Loader2 className="size-4 animate-spin text-muted-foreground" />
      <p className="text-xs text-muted-foreground">{message}</p>
    </div>
  );
}

export default function DashboardPage() {
  const principalQuery = useAdminPrincipal();
  const principal = principalQuery.data ?? null;
  const activeBotId = principal?.active_bot_id ?? null;
  const hasBotSelected = Boolean(activeBotId);

  const analyticsQuery = useQuery<AnalyticsSummaryResponse>({
    queryKey: adminQueryKeys.analytics(activeBotId),
    queryFn: fetchAnalyticsSummary,
    enabled: hasBotSelected,
    staleTime: 60_000,
  });
  const staffQuery = useQuery<AdminStaffUser[]>({
    queryKey: adminQueryKeys.staffUsers(),
    queryFn: listStaffUsers,
    staleTime: 60_000,
  });
  const questionsQuery = useQuery<QuestionRecord[]>({
    queryKey: adminQueryKeys.questions(activeBotId),
    queryFn: listQuestions,
    enabled: hasBotSelected,
    staleTime: 120_000,
  });
  const reportsQuery = useQuery({
    queryKey: adminQueryKeys.reports(activeBotId),
    queryFn: () => listReports(),
    enabled: hasBotSelected,
    staleTime: 60_000,
  });

  const analytics = analyticsQuery.data ?? null;
  const staff = staffQuery.data ?? [];
  const questions = questionsQuery.data ?? [];
  const reports = reportsQuery.data?.items ?? [];
  const openReports = reports.filter((report: ReportListItem) => report.status === "open");
  const reviewQuestions = questions.filter((question) => question.status === "needs_review");
  const kpis = analytics?.kpis ?? [];
  const leaderboard = analytics?.leaderboard ?? [];

  // Only block on the principal itself — everything else loads independently
  if (principalQuery.isLoading) {
    return (
      <AdminLoadingState
        title="Dashboard"
        description="Monitor bot usage, content health, and student engagement."
        message="Loading dashboard..."
      />
    );
  }

  return (
    <AdminShell>
      <div className="space-y-6">
        {/* Page header */}
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Dashboard</h2>
          <p className="text-sm text-muted-foreground">
            Monitor bot usage, content health, and student engagement.
          </p>
        </div>

        {/* No workspace selected prompt */}
        {!hasBotSelected && (principal?.bot_access?.length ?? 0) > 0 && (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center gap-3 py-10 text-center">
              <div className="flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Target className="size-5" />
              </div>
              <div>
                <p className="text-sm font-medium">No workspace selected</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Select a bot workspace from the header to view analytics, questions, and reports.
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* KPI Cards — each skeleton independently */}
        {hasBotSelected && (
          analyticsQuery.isLoading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Card key={i}>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="size-4 rounded" />
                  </CardHeader>
                  <CardContent>
                    <Skeleton className="h-7 w-16 mb-1" />
                    <Skeleton className="h-3 w-28" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : analyticsQuery.isError ? (
            <Card>
              <CardContent>
                <SectionError
                  message="Unable to load analytics"
                  onRetry={() => void analyticsQuery.refetch()}
                  isRetrying={analyticsQuery.isFetching}
                />
              </CardContent>
            </Card>
          ) : kpis.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {kpis.map((kpi, i) => {
                const TrendIcon = trendIcons[kpi.trend];
                const KpiIcon = kpiIcons[i] ?? Users;
                return (
                  <Card key={kpi.label}>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        {kpi.label}
                      </CardTitle>
                      <KpiIcon className="size-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{kpi.value}</div>
                      <div className="mt-1 flex items-center gap-1 text-xs">
                        <TrendIcon
                          className={`size-3 ${
                            kpi.trend === "up"
                              ? "text-emerald-500"
                              : kpi.trend === "down"
                                ? "text-red-500"
                                : "text-muted-foreground"
                          }`}
                        />
                        <span
                          className={
                            kpi.trend === "up"
                              ? "text-emerald-600"
                              : kpi.trend === "down"
                                ? "text-red-500"
                                : "text-muted-foreground"
                          }
                        >
                          {kpi.change}
                        </span>
                        <span className="text-muted-foreground">from last week</span>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          ) : null
        )}

        {/* Bottom grid — operational stats + reports */}
        <div className="grid gap-4 lg:grid-cols-7">
          {/* Quick stats */}
          <Card className="lg:col-span-4">
            <CardHeader>
              <CardTitle className="text-base">At a Glance</CardTitle>
              <CardDescription>Quick operational stats</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Total Staff</p>
                  {staffQuery.isLoading ? (
                    <Skeleton className="h-6 w-10 mt-1" />
                  ) : staffQuery.isError ? (
                    <p className="text-sm text-destructive mt-1">—</p>
                  ) : (
                    <>
                      <p className="text-xl font-semibold">{staff.length}</p>
                      <p className="text-xs text-muted-foreground">
                        {staff.filter((s) => s.is_active).length} active
                      </p>
                    </>
                  )}
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Questions in Bank</p>
                  {questionsQuery.isLoading ? (
                    <Skeleton className="h-6 w-10 mt-1" />
                  ) : questionsQuery.isError ? (
                    <p className="text-sm text-destructive mt-1">—</p>
                  ) : (
                    <>
                      <p className="text-xl font-semibold">{questions.length}</p>
                      <p className="text-xs text-muted-foreground">
                        {reviewQuestions.length} need review
                      </p>
                    </>
                  )}
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Open Reports</p>
                  {reportsQuery.isLoading ? (
                    <Skeleton className="h-6 w-10 mt-1" />
                  ) : reportsQuery.isError ? (
                    <p className="text-sm text-destructive mt-1">—</p>
                  ) : (
                    <>
                      <p className="text-xl font-semibold">{openReports.length}</p>
                      <p className="text-xs text-muted-foreground">
                        from students
                      </p>
                    </>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Recent reports */}
          <Card className="lg:col-span-3">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base">Recent Reports</CardTitle>
                <CardDescription>Student-flagged questions</CardDescription>
              </div>
              <Button variant="ghost" size="sm" render={<Link href="/reports" />} nativeButton={false}>
                  View all
                  <ArrowRight className="ml-1 size-3" />
              </Button>
            </CardHeader>
            <CardContent className="grid gap-3">
              {reportsQuery.isLoading ? (
                <SectionLoading message="Loading reports..." />
              ) : reportsQuery.isError ? (
                <SectionError
                  message="Unable to load reports"
                  onRetry={() => void reportsQuery.refetch()}
                  isRetrying={reportsQuery.isFetching}
                />
              ) : openReports.length === 0 ? (
                <p className="text-sm text-muted-foreground">No open reports.</p>
              ) : (
                openReports.slice(0, 3).map((report) => (
                  <div
                    key={report.id}
                    className="flex items-start justify-between gap-3 rounded-lg border p-3"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">
                        {report.question_key}
                      </p>
                      <p className="truncate text-xs text-muted-foreground">
                        {report.student_reasoning}
                      </p>
                    </div>
                    <Badge variant="outline" className="shrink-0 text-xs">
                      {report.course_name}
                    </Badge>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        {/* Top Students */}
        {hasBotSelected && (
          analyticsQuery.isLoading ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Top Students</CardTitle>
                <CardDescription>By questions answered this term</CardDescription>
              </CardHeader>
              <CardContent>
                <SectionLoading message="Loading leaderboard..." />
              </CardContent>
            </Card>
          ) : leaderboard.length > 0 ? (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-base">Top Students</CardTitle>
                  <CardDescription>By questions answered this term</CardDescription>
                </div>
                <Button variant="ghost" size="sm" render={<Link href="/analytics" />} nativeButton={false}>
                    Full leaderboard
                    <ArrowRight className="ml-1 size-3" />
                </Button>
              </CardHeader>
              <CardContent>
                <div className="grid gap-2">
                  {leaderboard.slice(0, 5).map((entry) => (
                    <div
                      key={entry.rank}
                      className="flex items-center gap-3 rounded-lg border px-3 py-2"
                    >
                      <span className="flex size-6 items-center justify-center rounded-full bg-muted text-xs font-medium">
                        {entry.rank}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium">@{entry.telegram_username}</p>
                        <p className="text-xs text-muted-foreground">{entry.top_course}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium">{entry.questions_answered}</p>
                        <p className="text-xs text-muted-foreground">answered</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium">{entry.accuracy}%</p>
                        <p className="text-xs text-muted-foreground">accuracy</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : null
        )}
      </div>
    </AdminShell>
  );
}
