"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import {
  Search,
  Upload,
  FileQuestion,
  Filter,
  Loader2,
  ChevronDown,
  ChevronRight,
  Target,
  BookOpen,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { AdminShell } from "@/components/admin-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { QuestionEditorDialog } from "@/components/questions/question-editor-dialog";
import { listQuestions, type QuestionRecord } from "@/lib/api";
import { adminQueryKeys } from "@/lib/query-keys";
import { useAdminPrincipal } from "@/lib/use-admin-principal";

type CourseGroup = {
  courseId: string;
  courseName: string;
  questions: QuestionRecord[];
};

function humanizeCourseId(courseId: string, slug?: string | null): string {
  if (slug) {
    return slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
  return courseId.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function groupByCourse(questions: QuestionRecord[]): CourseGroup[] {
  const map = new Map<string, QuestionRecord[]>();
  for (const q of questions) {
    const key = q.course_id;
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(q);
  }
  return Array.from(map.entries())
    .map(([courseId, qs]) => ({
      courseId,
      courseName: qs[0]?.course_name || humanizeCourseId(courseId, qs[0]?.course_slug),
      questions: qs,
    }))
    .sort((a, b) => a.courseName.localeCompare(b.courseName));
}

export default function QuestionsPage() {
  const [search, setSearch] = useState("");
  const [courseFilter, setCourseFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionRecord | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [expandedCourses, setExpandedCourses] = useState<Set<string>>(new Set());
  const principalQuery = useAdminPrincipal();
  const principal = principalQuery.data ?? null;
  const activeBotId = principal?.active_bot_id ?? null;
  const hasBotSelected = Boolean(activeBotId);

  const questionsQuery = useQuery({
    queryKey: adminQueryKeys.questions(activeBotId),
    queryFn: listQuestions,
    enabled: hasBotSelected,
    staleTime: 120_000,
  });

  const questions = questionsQuery.data ?? [];
  const uniqueCourses = [...new Set(questions.map((q) => q.course_id))];

  const filtered = questions.filter((q) => {
    const matchesSearch =
      q.question_text.toLowerCase().includes(search.toLowerCase()) ||
      q.question_key.toLowerCase().includes(search.toLowerCase());
    const matchesCourse = courseFilter === "all" || q.course_id === courseFilter;
    const matchesStatus = statusFilter === "all" || q.status === statusFilter;
    return matchesSearch && matchesCourse && matchesStatus;
  });

  const courseGroups = useMemo(() => groupByCourse(filtered), [filtered]);

  function toggleCourse(courseId: string) {
    setExpandedCourses((prev) => {
      const next = new Set(prev);
      if (next.has(courseId)) next.delete(courseId);
      else next.add(courseId);
      return next;
    });
  }

  function expandAll() {
    setExpandedCourses(new Set(courseGroups.map((g) => g.courseId)));
  }

  function collapseAll() {
    setExpandedCourses(new Set());
  }

  function handleEdit(question: QuestionRecord) {
    setSelectedQuestion(question);
    setEditorOpen(true);
  }

  // Loading state
  if (principalQuery.isLoading || (questionsQuery.isLoading && questions.length === 0)) {
    return (
      <AdminShell>
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Questions</h2>
            <p className="text-sm text-muted-foreground">
              Manage the question bank for the active bot workspace.
            </p>
          </div>
          <Card>
            <CardContent className="flex min-h-40 flex-col items-center justify-center gap-3 py-12 text-center">
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Loading questions...</p>
            </CardContent>
          </Card>
        </div>
      </AdminShell>
    );
  }

  // No bot selected
  if (!hasBotSelected) {
    return (
      <AdminShell>
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Questions</h2>
            <p className="text-sm text-muted-foreground">
              Manage the question bank for the active bot workspace.
            </p>
          </div>
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center gap-3 py-10 text-center">
              <div className="flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Target className="size-5" />
              </div>
              <div>
                <p className="text-sm font-medium">No workspace selected</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Select a bot workspace from the header to view and manage questions.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </AdminShell>
    );
  }

  return (
    <AdminShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Questions</h2>
            <p className="text-sm text-muted-foreground">
              Manage the question bank for the active bot workspace.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" render={<Link href="/questions/import" />} nativeButton={false}>
              <Upload className="mr-2 size-4" />
              Bulk Import
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search questions..."
              className="pl-9"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Select value={courseFilter} onValueChange={(v) => setCourseFilter(v ?? "all")}>
            <SelectTrigger className="w-48">
              <Filter className="mr-2 size-4" />
              <SelectValue placeholder="All courses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All courses</SelectItem>
              {uniqueCourses.map((code) => (
                <SelectItem key={code} value={code}>
                  {humanizeCourseId(code)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v ?? "all")}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="ready">Ready</SelectItem>
              <SelectItem value="processing">Processing</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="error">Error</SelectItem>
              <SelectItem value="invalid">Invalid</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Stats */}
        <div className="grid gap-4 sm:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{questions.length}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Courses</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{uniqueCourses.length}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Ready</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {questions.filter((q) => q.status === "ready").length}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">With LaTeX</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {questions.filter((q) => q.has_latex).length}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Expand/Collapse controls */}
        {courseGroups.length > 1 && (
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={expandAll}>
              Expand all
            </Button>
            <Button variant="ghost" size="sm" onClick={collapseAll}>
              Collapse all
            </Button>
            <span className="text-xs text-muted-foreground ml-2">
              {filtered.length} question{filtered.length !== 1 ? "s" : ""} across {courseGroups.length} course{courseGroups.length !== 1 ? "s" : ""}
            </span>
          </div>
        )}

        {/* Grouped by Course */}
        {questionsQuery.isError ? (
          <Card>
            <CardContent className="flex min-h-40 flex-col items-center justify-center gap-3 py-12 text-center">
              <p className="text-sm text-destructive">Unable to load questions.</p>
            </CardContent>
          </Card>
        ) : courseGroups.length === 0 ? (
          <Card>
            <CardContent className="flex min-h-40 flex-col items-center justify-center gap-3 py-12 text-center">
              <FileQuestion className="size-8 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">No questions match your filters.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {courseGroups.map((group) => {
              const isExpanded = expandedCourses.has(group.courseId);
              const readyCount = group.questions.filter((q) => q.status === "ready").length;
              return (
                <div key={group.courseId} className="rounded-lg border bg-card overflow-hidden">
                  <button
                    type="button"
                    className="flex w-full items-center gap-3 px-4 py-3 hover:bg-accent/50 transition-colors text-left"
                    onClick={() => toggleCourse(group.courseId)}
                  >
                    {isExpanded ? (
                      <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
                    )}
                    <BookOpen className="size-4 shrink-0 text-muted-foreground" />
                    <span className="font-medium text-sm">{group.courseName}</span>
                    <Badge variant="secondary" className="text-[10px] ml-auto">
                      {group.questions.length} question{group.questions.length !== 1 ? "s" : ""}
                    </Badge>
                    <Badge
                      variant="outline"
                      className="text-[10px] text-emerald-600 border-emerald-500/30"
                    >
                      {readyCount} ready
                    </Badge>
                  </button>
                  {isExpanded && (
                    <div className="border-t">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-20">Key</TableHead>
                            <TableHead>Question</TableHead>
                            <TableHead>Band</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead className="w-20">LaTeX</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {group.questions.map((q) => (
                            <TableRow
                              key={q.question_key}
                              className="cursor-pointer"
                              onClick={() => handleEdit(q)}
                            >
                              <TableCell className="font-mono text-xs text-muted-foreground">
                                {q.question_key}
                              </TableCell>
                              <TableCell className="max-w-xs truncate">{q.question_text}</TableCell>
                              <TableCell className="text-muted-foreground">{q.band}</TableCell>
                              <TableCell>
                                <Badge
                                  variant={q.status === "ready" ? "default" : "secondary"}
                                  className="text-xs"
                                >
                                  {q.status}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                {q.has_latex && (
                                  <Badge variant="outline" className="text-xs font-mono">
                                    TeX
                                  </Badge>
                                )}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Editor */}
      <QuestionEditorDialog
        open={editorOpen}
        onOpenChange={setEditorOpen}
        question={selectedQuestion}
      />
    </AdminShell>
  );
}
