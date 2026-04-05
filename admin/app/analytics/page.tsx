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
  Trophy,
  Medal,
  ChevronRight,
} from "lucide-react";
import { useRouter } from "next/navigation";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
} from "recharts";

import { AdminShell } from "@/components/admin-shell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AdminErrorState, AdminLoadingState, AdminRetryButton } from "@/components/admin-page-state";
import { fetchAnalyticsSummary, type AnalyticsSummaryResponse } from "@/lib/api";
import { adminQueryKeys } from "@/lib/query-keys";
import { useAdminPrincipal } from "@/lib/use-admin-principal";

const trendIcons = {
  up: TrendingUp,
  down: TrendingDown,
  flat: Minus,
};

const kpiIcons = [Users, MessageSquare, Target, Flame];

function phaseDot(phase: string) {
  const colors: Record<string, string> = {
    cold_start: "bg-blue-500",
    warm: "bg-amber-500",
    established: "bg-emerald-500",
  };
  return <span className={`inline-block size-2 rounded-full ${colors[phase] ?? colors.cold_start}`} />;
}

export default function AnalyticsPage() {
  const router = useRouter();
  const principalQuery = useAdminPrincipal();
  const activeBotId = principalQuery.data?.active_bot_id ?? null;
  const analyticsQuery = useQuery<AnalyticsSummaryResponse>({
    queryKey: adminQueryKeys.analytics(activeBotId),
    queryFn: fetchAnalyticsSummary,
    enabled: Boolean(activeBotId),
    retry: false,
  });

  if ((principalQuery.isLoading || analyticsQuery.isLoading) && !analyticsQuery.data) {
    return (
      <AdminLoadingState
        title="Analytics"
        description="Telegram bot usage and student performance data."
        message="Loading analytics..."
      />
    );
  }

  if (principalQuery.isError || analyticsQuery.isError || !analyticsQuery.data) {
    return (
      <AdminErrorState
        title="Analytics"
        description="Telegram bot usage and student performance data."
        message="Unable to load analytics right now."
        action={
          <AdminRetryButton
            onClick={() => {
              void analyticsQuery.refetch();
            }}
            isPending={analyticsQuery.isFetching}
          />
        }
      />
    );
  }

  const { kpis, daily_usage, leaderboard } = analyticsQuery.data;

  return (
    <AdminShell>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Analytics</h2>
          <p className="text-sm text-muted-foreground">
            Telegram bot usage and student performance data.
          </p>
        </div>

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
                    <span className="text-muted-foreground">vs last week</span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Daily Usage</CardTitle>
              <CardDescription>Users and questions this week</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={daily_usage}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="date" className="text-xs" tick={{ fontSize: 12 }} />
                    <YAxis className="text-xs" tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        borderRadius: "8px",
                        border: "1px solid hsl(var(--border))",
                        backgroundColor: "hsl(var(--card))",
                        fontSize: "12px",
                      }}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="users"
                      stroke="hsl(var(--chart-1))"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      name="Active Users"
                    />
                    <Line
                      type="monotone"
                      dataKey="questions"
                      stroke="hsl(var(--chart-2))"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      name="Questions"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Questions Served</CardTitle>
              <CardDescription>Distribution by day</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={daily_usage}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="date" className="text-xs" tick={{ fontSize: 12 }} />
                    <YAxis className="text-xs" tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        borderRadius: "8px",
                        border: "1px solid hsl(var(--border))",
                        backgroundColor: "hsl(var(--card))",
                        fontSize: "12px",
                      }}
                    />
                    <Bar
                      dataKey="questions"
                      fill="hsl(var(--chart-1))"
                      radius={[4, 4, 0, 0]}
                      name="Questions"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Trophy className="size-4 text-amber-500" />
              Student Leaderboard
            </CardTitle>
            <CardDescription>
              Click a student to view their full performance profile
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">#</TableHead>
                    <TableHead>Username</TableHead>
                    <TableHead>Top Course</TableHead>
                    <TableHead className="text-center">Phase</TableHead>
                    <TableHead className="text-right">Skill</TableHead>
                    <TableHead className="text-right">Answered</TableHead>
                    <TableHead className="text-right">Streak</TableHead>
                    <TableHead className="text-right">Accuracy</TableHead>
                    <TableHead className="w-8"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {leaderboard.map((entry) => (
                    <TableRow
                      key={entry.rank}
                      className="cursor-pointer group"
                      onClick={() => router.push(`/analytics/students/${entry.user_id}`)}
                    >
                      <TableCell>
                        {entry.rank <= 3 ? (
                          <Medal
                            className={`size-4 ${
                              entry.rank === 1
                                ? "text-amber-500"
                                : entry.rank === 2
                                  ? "text-zinc-400"
                                  : "text-orange-600"
                            }`}
                          />
                        ) : (
                          <span className="text-muted-foreground">{entry.rank}</span>
                        )}
                      </TableCell>
                      <TableCell className="font-medium">
                        @{entry.telegram_username}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {entry.top_course}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          {phaseDot(entry.phase)}
                          <span className="text-xs text-muted-foreground capitalize">
                            {entry.phase.replace("_", " ")}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {entry.overall_skill.toFixed(1)}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {entry.questions_answered}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Flame className="size-3 text-orange-500" />
                          {entry.daily_streak}
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {entry.accuracy}%
                      </TableCell>
                      <TableCell>
                        <ChevronRight className="size-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </AdminShell>
  );
}
