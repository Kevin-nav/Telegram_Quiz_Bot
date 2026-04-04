"use client";

import { useState } from "react";
import Link from "next/link";
import { Search, Upload, FileQuestion, Filter, Loader2 } from "lucide-react";
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

export default function QuestionsPage() {
  const [search, setSearch] = useState("");
  const [courseFilter, setCourseFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionRecord | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);

  const questionsQuery = useQuery({
    queryKey: ["questions"],
    queryFn: listQuestions,
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

  function handleEdit(question: QuestionRecord) {
    setSelectedQuestion(question);
    setEditorOpen(true);
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
                  {code}
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
        <div className="grid gap-4 sm:grid-cols-3">
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

        {/* Table */}
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-20">Key</TableHead>
                <TableHead>Question</TableHead>
                <TableHead>Course</TableHead>
                <TableHead>Band</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-20">LaTeX</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {questionsQuery.isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                    <Loader2 className="mx-auto mb-2 size-5 animate-spin" />
                    Loading questions...
                  </TableCell>
                </TableRow>
              ) : questionsQuery.isError ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center text-destructive">
                    Unable to load questions.
                  </TableCell>
                </TableRow>
              ) : filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                    <FileQuestion className="mx-auto mb-2 size-8 text-muted-foreground/40" />
                    No questions match your filters.
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((q) => (
                  <TableRow
                    key={q.question_key}
                    className="cursor-pointer"
                    onClick={() => handleEdit(q)}
                  >
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {q.question_key}
                    </TableCell>
                    <TableCell className="max-w-xs truncate">{q.question_text}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {q.course_id}
                      </Badge>
                    </TableCell>
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
                ))
              )}
            </TableBody>
          </Table>
        </div>
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
