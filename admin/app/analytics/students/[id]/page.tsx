"use client";

import { useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Flame,
  Trophy,
  Target,
  BookOpen,
  GraduationCap,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Calendar,
  Zap,
  Brain,
  TrendingUp,
  BarChart3,
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
  ComposedChart,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";
import { useQuery } from "@tanstack/react-query";

import { AdminShell } from "@/components/admin-shell";
import { AdminErrorState, AdminLoadingState, AdminRetryButton } from "@/components/admin-page-state";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  fetchStudentAnalytics,
  type StudentDetailResponse,
} from "@/lib/api";
import { adminQueryKeys } from "@/lib/query-keys";
import { useAdminPrincipal } from "@/lib/use-admin-principal";

function phaseBadge(phase: string) {
  const map: Record<string, { label: string; cls: string }> = {
    cold_start: { label: "Cold Start", cls: "border-blue-500/30 bg-blue-500/10 text-blue-600" },
    warm: { label: "Warm", cls: "border-amber-500/30 bg-amber-500/10 text-amber-600" },
    established: { label: "Established", cls: "border-emerald-500/30 bg-emerald-500/10 text-emerald-600" },
  };
  const p = map[phase] ?? map.cold_start;
  return <Badge variant="outline" className={`text-xs ${p.cls}`}>{p.label}</Badge>;
}

function skillColor(skill: number) {
  if (skill >= 3.5) return "text-emerald-600";
  if (skill >= 2.5) return "text-blue-600";
  if (skill >= 1.5) return "text-amber-600";
  return "text-red-600";
}

function skillLabel(skill: number) {
  if (skill >= 3.5) return "Expert";
  if (skill >= 2.5) return "Proficient";
  if (skill >= 1.5) return "Developing";
  return "Novice";
}

function skillBarColor(skill: number) {
  if (skill >= 3.5) return "bg-emerald-500";
  if (skill >= 2.5) return "bg-blue-500";
  if (skill >= 1.5) return "bg-amber-500";
  return "bg-red-500";
}

function formatTopicName(id: string) {
  return id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function formatSeconds(s: number) {
  if (s < 60) return `${Math.round(s)}s`;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}

function daysUntil(iso: string) {
  const diff = new Date(iso).getTime() - Date.now();
  return Math.max(0, Math.ceil(diff / 86400000));
}

const tooltipStyle = {
  borderRadius: "8px",
  border: "1px solid hsl(var(--border))",
  backgroundColor: "hsl(var(--card))",
  fontSize: "12px",
};

export default function StudentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const userId = Number(params.id);
  const hasValidUserId = Number.isFinite(userId);
  const principalQuery = useAdminPrincipal();
  const activeBotId = principalQuery.data?.active_bot_id ?? null;

  const studentQuery = useQuery<StudentDetailResponse>({
    queryKey: adminQueryKeys.studentAnalytics(activeBotId, userId),
    queryFn: () => fetchStudentAnalytics(userId),
    enabled: hasValidUserId && Boolean(activeBotId),
    retry: false,
  });

  const data = studentQuery.data ?? null;
  const leaderboardEntry = data?.leaderboard_entry ?? null;

  const accuracy = useMemo(() => {
    const profile = data?.profile;
    if (!profile || profile.total_questions_answered <= 0) {
      return 0;
    }
    return Math.round((profile.total_correct / profile.total_questions_answered) * 1000) / 10;
  }, [data?.profile]);

  if ((principalQuery.isLoading || studentQuery.isLoading) && !data) {
    return (
      <AdminLoadingState
        title="Student analytics"
        description="Detailed learner performance, activity, and retention."
        message="Loading student analytics..."
      />
    );
  }

  if (!hasValidUserId) {
    return (
      <AdminErrorState
        title="Student analytics"
        description="Detailed learner performance, activity, and retention."
        message="The requested student id is invalid."
        action={
          <Button variant="ghost" onClick={() => router.push("/analytics")}>
            <ArrowLeft className="mr-2 size-4" /> Back to Analytics
          </Button>
        }
      />
    );
  }

  if (principalQuery.isError || studentQuery.isError) {
    return (
      <AdminErrorState
        title="Student analytics"
        description="Detailed learner performance, activity, and retention."
        message="Unable to load student analytics right now."
        action={
          <div className="flex flex-wrap justify-center gap-2">
            <AdminRetryButton
              onClick={() => {
                void studentQuery.refetch();
              }}
              isPending={studentQuery.isFetching}
            />
            <Button variant="ghost" onClick={() => router.push("/analytics")}>
              <ArrowLeft className="mr-2 size-4" /> Back to Analytics
            </Button>
          </div>
        }
      />
    );
  }

  if (!data) {
    return (
      <AdminErrorState
        title="Student analytics"
        description="Detailed learner performance, activity, and retention."
        message="Student not found in the current workspace."
        action={
          <Button variant="ghost" onClick={() => router.push("/analytics")}>
            <ArrowLeft className="mr-2 size-4" /> Back to Analytics
          </Button>
        }
      />
    );
  }

  const { profile: p, courses, srs, weekly_progress, daily_activity, recent_attempts } = data;

  return (
    <AdminShell>
      <div className="space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => router.push("/analytics")}>
              <ArrowLeft className="size-4" />
            </Button>
            <div className="flex size-10 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-semibold">
              {p.display_name.split(" ").map((n) => n[0]).join("").slice(0, 2)}
            </div>
            <div>
              <h2 className="text-xl font-semibold tracking-tight">{p.display_name}</h2>
              <p className="text-sm text-muted-foreground">@{p.telegram_username}</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {leaderboardEntry ? (
              <Badge variant="outline" className="gap-1">
                <Trophy className="size-3 text-amber-500" /> Rank #{leaderboardEntry.rank}
              </Badge>
            ) : null}
            {phaseBadge(courses[0]?.phase ?? "cold_start")}
            <Badge variant="outline" className="gap-1 text-xs">
              <GraduationCap className="size-3" /> {p.program_name}
            </Badge>
            <Badge variant="outline" className="gap-1 text-xs">
              {p.level_code} · {p.semester_code}
            </Badge>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Answered</CardTitle>
              <Target className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{p.total_questions_answered.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground mt-1">{p.total_correct} correct</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Accuracy</CardTitle>
              <BarChart3 className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${accuracy >= 75 ? "text-emerald-600" : accuracy >= 60 ? "text-amber-600" : "text-red-600"}`}>
                {accuracy}%
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {accuracy >= 75 ? "Above average" : accuracy >= 60 ? "Average" : "Needs attention"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Streak</CardTitle>
              <Flame className="size-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold flex items-center gap-1">
                <Flame className="size-5 text-orange-500" /> {p.current_streak}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Longest: {p.longest_streak} days</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Quizzes</CardTitle>
              <BookOpen className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{p.total_quizzes_completed}</div>
              <p className="text-xs text-muted-foreground mt-1">completed</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Member Since</CardTitle>
              <Calendar className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {new Date(p.created_at).toLocaleDateString("en-GB", { month: "short", day: "numeric" })}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Last seen {timeAgo(p.last_active_at)}</p>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="size-4 text-chart-1" /> Performance Over Time
            </CardTitle>
            <CardDescription>Weekly accuracy and question volume (12 weeks)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={weekly_progress}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="week" tick={{ fontSize: 12 }} />
                  <YAxis yAxisId="left" tick={{ fontSize: 12 }} />
                  <YAxis yAxisId="right" orientation="right" domain={[0, 100]} tick={{ fontSize: 12 }} unit="%" />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                  <Bar yAxisId="left" dataKey="attempts" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} name="Attempts" opacity={0.7} />
                  <Line yAxisId="right" type="monotone" dataKey="accuracy" stroke="hsl(var(--chart-2))" strokeWidth={2} dot={{ r: 3 }} name="Accuracy %" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <BookOpen className="size-4" /> Course Performance
            </CardTitle>
            <CardDescription>Adaptive skill level and progress per enrolled course</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {courses.map((c) => {
                const acc = c.total_attempts > 0 ? Math.round((c.total_correct / c.total_attempts) * 1000) / 10 : 0;
                return (
                  <div key={c.course_id} className="rounded-lg border p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold">{c.course_name}</h4>
                      {phaseBadge(c.phase)}
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex-1">
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="text-muted-foreground">Skill Level</span>
                          <span className={`font-semibold ${skillColor(c.overall_skill)}`}>
                            {c.overall_skill.toFixed(1)} · {skillLabel(c.overall_skill)}
                          </span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${skillBarColor(c.overall_skill)}`}
                            style={{ width: `${Math.min(100, (c.overall_skill / 5) * 100)}%` }}
                          />
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div>
                        <p className="text-lg font-semibold">{c.total_attempts}</p>
                        <p className="text-[10px] text-muted-foreground">Attempts</p>
                      </div>
                      <div>
                        <p className={`text-lg font-semibold ${acc >= 75 ? "text-emerald-600" : acc >= 60 ? "text-amber-600" : "text-red-600"}`}>{acc}%</p>
                        <p className="text-[10px] text-muted-foreground">Accuracy</p>
                      </div>
                      <div>
                        <p className="text-lg font-semibold">{formatSeconds(c.avg_time_per_question)}</p>
                        <p className="text-[10px] text-muted-foreground">Avg Time</p>
                      </div>
                    </div>
                    {c.exam_date ? (
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground border-t pt-2">
                        <Calendar className="size-3" />
                        Exam in {daysUntil(c.exam_date)} days
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Brain className="size-4" /> Topic Mastery
            </CardTitle>
            <CardDescription>Per-topic skill levels across all courses</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue={courses[0]?.course_id ?? ""}>
              <TabsList>
                {courses.map((c) => (
                  <TabsTrigger key={c.course_id} value={c.course_id}>{c.course_name}</TabsTrigger>
                ))}
              </TabsList>
              {courses.map((c) => (
                <TabsContent key={c.course_id} value={c.course_id}>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 mt-4">
                    {Object.entries(c.topic_skills).map(([topic, skill]) => (
                      <div key={topic} className="rounded-lg border p-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">{formatTopicName(topic)}</span>
                          <Badge variant="outline" className={`text-[10px] ${skillColor(skill)}`}>
                            {skillLabel(skill)}
                          </Badge>
                        </div>
                        <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${skillBarColor(skill)}`}
                            style={{ width: `${Math.min(100, (skill / 5) * 100)}%` }}
                          />
                        </div>
                        <p className="text-xs text-muted-foreground text-right">{skill.toFixed(1)} / 5.0</p>
                      </div>
                    ))}
                  </div>
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Cognitive Profile</CardTitle>
              <CardDescription>Bloom&apos;s taxonomy performance</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={Object.entries(courses[0]?.cognitive_profile ?? {}).map(([k, v]) => ({ subject: k, score: v, fullMark: 5 }))}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 5]} tick={{ fontSize: 10 }} />
                    <Radar name="Skill" dataKey="score" stroke="hsl(var(--chart-1))" fill="hsl(var(--chart-1))" fillOpacity={0.3} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Zap className="size-4" /> Retention (SRS Boxes)
              </CardTitle>
              <CardDescription>Spaced repetition box distribution per course</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={srs}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="course_name" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Legend />
                    <Bar dataKey="box_0" stackId="a" fill="#ef4444" name="New (0)" />
                    <Bar dataKey="box_1" stackId="a" fill="#f97316" name="Learning (1)" />
                    <Bar dataKey="box_2" stackId="a" fill="#eab308" name="Review (2)" />
                    <Bar dataKey="box_3" stackId="a" fill="#3b82f6" name="Known (3)" />
                    <Bar dataKey="box_4" stackId="a" fill="#22c55e" name="Strong (4)" />
                    <Bar dataKey="box_5" stackId="a" fill="#10b981" name="Mastered (5)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {courses.some((c) => c.misconception_flags.length > 0) ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <AlertTriangle className="size-4 text-amber-500" /> Misconception Alerts
              </CardTitle>
              <CardDescription>Auto-detected knowledge gaps from the adaptive engine</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {courses.flatMap((c) =>
                  c.misconception_flags.map((flag, i) => (
                    <div key={`${c.course_id}-${i}`} className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 space-y-1">
                      <div className="flex items-center justify-between">
                        <Badge variant="outline" className="text-[10px]">{c.course_name}</Badge>
                        <Badge
                          variant="outline"
                          className={`text-[10px] ${
                            flag.severity === "high"
                              ? "border-red-500/30 text-red-600"
                              : flag.severity === "medium"
                                ? "border-amber-500/30 text-amber-600"
                                : "border-zinc-500/30 text-zinc-600"
                          }`}
                        >
                          {flag.severity}
                        </Badge>
                      </div>
                      <p className="text-sm font-medium">{formatTopicName(flag.topic)}</p>
                      <p className="text-xs text-muted-foreground">{flag.description}</p>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Activity Heatmap</CardTitle>
            <CardDescription>Questions answered per day (last 30 days)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-1">
              {daily_activity.map((d) => {
                const intensity = d.questions_count === 0 ? 0 : Math.min(4, Math.ceil(d.questions_count / 8));
                const colors = [
                  "bg-muted",
                  "bg-emerald-200 dark:bg-emerald-900",
                  "bg-emerald-300 dark:bg-emerald-700",
                  "bg-emerald-500 dark:bg-emerald-500",
                  "bg-emerald-700 dark:bg-emerald-300",
                ];
                return (
                  <div
                    key={d.date}
                    className={`size-7 rounded-sm ${colors[intensity]} transition-colors`}
                    title={`${d.date}: ${d.questions_count} questions`}
                  />
                );
              })}
            </div>
            <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
              <span>Less</span>
              <div className="size-3 rounded-sm bg-muted" />
              <div className="size-3 rounded-sm bg-emerald-200 dark:bg-emerald-900" />
              <div className="size-3 rounded-sm bg-emerald-300 dark:bg-emerald-700" />
              <div className="size-3 rounded-sm bg-emerald-500" />
              <div className="size-3 rounded-sm bg-emerald-700 dark:bg-emerald-300" />
              <span>More</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Activity</CardTitle>
            <CardDescription>Last {recent_attempts.length} question attempts</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Question</TableHead>
                    <TableHead>Course</TableHead>
                    <TableHead className="text-center">Result</TableHead>
                    <TableHead className="text-right">Time</TableHead>
                    <TableHead className="text-right">When</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recent_attempts.map((a, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-mono text-xs">{a.question_key}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-[10px]">{a.course_name}</Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        {a.is_correct ? (
                          <CheckCircle2 className="mx-auto size-4 text-emerald-500" />
                        ) : (
                          <XCircle className="mx-auto size-4 text-red-500" />
                        )}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {formatSeconds(a.time_taken_seconds)}
                      </TableCell>
                      <TableCell className="text-right text-xs text-muted-foreground">
                        {timeAgo(a.created_at)}
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
