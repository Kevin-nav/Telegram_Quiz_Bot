"use client";

import {
  TrendingUp,
  TrendingDown,
  Minus,
  Users,
  MessageSquare,
  Target,
  Flame,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AdminShell } from "@/components/admin-shell";
import { MOCK_KPIS, MOCK_REPORTS, MOCK_LEADERBOARD, MOCK_QUESTIONS, MOCK_STAFF } from "@/lib/mock-data";

const trendIcons = {
  up: TrendingUp,
  down: TrendingDown,
  flat: Minus,
};

const kpiIcons = [Users, MessageSquare, Target, Flame];

export default function DashboardPage() {
  const openReports = MOCK_REPORTS.filter((r) => r.status === "open");
  const reviewQuestions = MOCK_QUESTIONS.filter((q) => q.status === "needs_review");

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

        {/* KPI Cards */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {MOCK_KPIS.map((kpi, i) => {
            const TrendIcon = trendIcons[kpi.trend];
            const KpiIcon = kpiIcons[i];
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

        {/* Bottom grid */}
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
                  <p className="text-xl font-semibold">{MOCK_STAFF.length}</p>
                  <p className="text-xs text-muted-foreground">
                    {MOCK_STAFF.filter((s) => s.is_active).length} active
                  </p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Questions in Bank</p>
                  <p className="text-xl font-semibold">{MOCK_QUESTIONS.length}</p>
                  <p className="text-xs text-muted-foreground">
                    {reviewQuestions.length} need review
                  </p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Open Reports</p>
                  <p className="text-xl font-semibold">{openReports.length}</p>
                  <p className="text-xs text-muted-foreground">
                    from students
                  </p>
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
              {openReports.length === 0 ? (
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
              {MOCK_LEADERBOARD.slice(0, 5).map((entry) => (
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
      </div>
    </AdminShell>
  );
}
