"use client";

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
} from "lucide-react";
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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import {
  MOCK_KPIS,
  MOCK_DAILY_USAGE,
  MOCK_LEADERBOARD,
  type LeaderboardEntry,
} from "@/lib/mock-data";
import { useState } from "react";

const trendIcons = {
  up: TrendingUp,
  down: TrendingDown,
  flat: Minus,
};

const kpiIcons = [Users, MessageSquare, Target, Flame];

export default function AnalyticsPage() {
  const [selectedStudent, setSelectedStudent] = useState<LeaderboardEntry | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  function handleStudentClick(student: LeaderboardEntry) {
    setSelectedStudent(student);
    setSheetOpen(true);
  }

  return (
    <AdminShell>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Analytics</h2>
          <p className="text-sm text-muted-foreground">
            Telegram bot usage and student performance data.
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
                    <span className="text-muted-foreground">vs last week</span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Charts */}
        <div className="grid gap-4 lg:grid-cols-2">
          {/* Usage Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Daily Usage</CardTitle>
              <CardDescription>Users and questions this week</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={MOCK_DAILY_USAGE}>
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

          {/* Questions by Day */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Questions Served</CardTitle>
              <CardDescription>Distribution by day</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={MOCK_DAILY_USAGE}>
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

        {/* Leaderboard */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Trophy className="size-4 text-amber-500" />
              Student Leaderboard
            </CardTitle>
            <CardDescription>
              Ranked by questions answered, streak, and accuracy
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
                    <TableHead className="text-right">Answered</TableHead>
                    <TableHead className="text-right">Streak</TableHead>
                    <TableHead className="text-right">Accuracy</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {MOCK_LEADERBOARD.map((entry) => (
                    <TableRow
                      key={entry.rank}
                      className="cursor-pointer"
                      onClick={() => handleStudentClick(entry)}
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
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Student Detail Sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>
              @{selectedStudent?.telegram_username}
            </SheetTitle>
            <SheetDescription>
              Telegram ID: {selectedStudent?.telegram_id}
            </SheetDescription>
          </SheetHeader>
          {selectedStudent && (
            <div className="mt-6 space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Questions Answered</p>
                  <p className="text-xl font-bold">{selectedStudent.questions_answered}</p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Daily Streak</p>
                  <p className="text-xl font-bold flex items-center gap-1">
                    <Flame className="size-4 text-orange-500" />
                    {selectedStudent.daily_streak}
                  </p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Accuracy</p>
                  <p className="text-xl font-bold">{selectedStudent.accuracy}%</p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Most Active Course</p>
                  <p className="text-sm font-medium mt-1">{selectedStudent.top_course}</p>
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <Button variant="outline" size="sm" className="flex-1">
                  Award Student
                </Button>
                <Button variant="outline" size="sm" className="flex-1 text-destructive hover:text-destructive">
                  Flag Student
                </Button>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </AdminShell>
  );
}
