"use client";

import { useState, useCallback } from "react";
import {
  Upload,
  FileJson,
  CheckCircle2,
  XCircle,
  ArrowLeft,
  Loader2,
} from "lucide-react";
import Link from "next/link";
import { AdminShell } from "@/components/admin-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type ValidationResult = {
  valid: ImportQuestion[];
  errors: { index: number; message: string }[];
};

type ImportQuestion = {
  question_text: string;
  options: string[];
  correct_option_text: string;
  short_explanation: string;
  cognitive_level?: string;
  has_latex?: boolean;
  band?: number;
};

const REQUIRED_KEYS = ["question_text", "options", "correct_option_text", "short_explanation"];

function validateQuestions(data: unknown): ValidationResult {
  if (!Array.isArray(data)) {
    return { valid: [], errors: [{ index: -1, message: "Root must be a JSON array." }] };
  }

  const valid: ImportQuestion[] = [];
  const errors: { index: number; message: string }[] = [];

  data.forEach((item, index) => {
    if (!item || typeof item !== "object") {
      errors.push({ index, message: "Item is not an object." });
      return;
    }

    const missing = REQUIRED_KEYS.filter((key) => !(key in item));
    if (missing.length > 0) {
      errors.push({ index, message: `Missing keys: ${missing.join(", ")}` });
      return;
    }

    const q = item as Record<string, unknown>;
    if (!Array.isArray(q.options) || q.options.length < 2) {
      errors.push({ index, message: "Options must be an array with at least 2 items." });
      return;
    }

    valid.push(item as ImportQuestion);
  });

  return { valid, errors };
}

export default function ImportPage() {
  const [isDragging, setIsDragging] = useState(false);
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const processFile = useCallback((file: File) => {
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        setResult(validateQuestions(data));
      } catch {
        setResult({
          valid: [],
          errors: [{ index: -1, message: "Invalid JSON file." }],
        });
      }
    };
    reader.readAsText(file);
  }, []);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  }

  async function handleCommit() {
    setIsUploading(true);
    // TODO: Wire to API
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setIsUploading(false);
  }

  return (
    <AdminShell>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" render={<Link href="/questions" />} nativeButton={false}>
              <ArrowLeft className="size-4" />
          </Button>
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Bulk Import</h2>
            <p className="text-sm text-muted-foreground">
              Drop a JSON file to validate and import questions.
            </p>
          </div>
        </div>

        {/* Dropzone */}
        {!result ? (
          <div
            className={`relative flex min-h-[300px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed transition-colors ${
              isDragging
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50"
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => document.getElementById("file-input")?.click()}
          >
            <input
              id="file-input"
              type="file"
              accept=".json"
              className="hidden"
              onChange={handleFileInput}
            />
            <FileJson className="mb-4 size-12 text-muted-foreground/40" />
            <p className="text-sm font-medium">
              Drop your JSON file here, or click to browse
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Expects a JSON array of question objects
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <FileJson className="size-4" />
                  {fileName}
                </CardTitle>
                <CardDescription>Validation complete</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex gap-6">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="size-4 text-emerald-500" />
                    <span className="text-sm font-medium">{result.valid.length} Valid</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <XCircle className="size-4 text-red-500" />
                    <span className="text-sm font-medium">{result.errors.length} Errors</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Errors */}
            {result.errors.length > 0 && (
              <Card className="border-destructive/20">
                <CardHeader>
                  <CardTitle className="text-base text-destructive">Validation Errors</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="rounded-lg border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-20">Index</TableHead>
                          <TableHead>Error</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {result.errors.map((err, i) => (
                          <TableRow key={i}>
                            <TableCell className="font-mono text-xs">
                              {err.index === -1 ? "—" : `#${err.index}`}
                            </TableCell>
                            <TableCell className="text-sm text-destructive">
                              {err.message}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Valid preview */}
            {result.valid.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Preview ({result.valid.length} questions)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="rounded-lg border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-8">#</TableHead>
                          <TableHead>Question</TableHead>
                          <TableHead className="w-20">Options</TableHead>
                          <TableHead className="w-20">Level</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {result.valid.slice(0, 10).map((q, i) => (
                          <TableRow key={i}>
                            <TableCell className="text-muted-foreground">{i + 1}</TableCell>
                            <TableCell className="max-w-xs truncate text-sm">
                              {q.question_text}
                            </TableCell>
                            <TableCell>{q.options.length}</TableCell>
                            <TableCell>
                              <Badge variant="outline" className="text-xs">
                                {q.cognitive_level ?? "—"}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                  {result.valid.length > 10 && (
                    <p className="mt-2 text-xs text-muted-foreground">
                      Showing first 10 of {result.valid.length} questions
                    </p>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Actions */}
            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setResult(null);
                  setFileName(null);
                }}
              >
                Upload Different File
              </Button>
              {result.valid.length > 0 && (
                <Button onClick={handleCommit} disabled={isUploading}>
                  {isUploading ? (
                    <>
                      <Loader2 className="mr-2 size-4 animate-spin" />
                      Importing...
                    </>
                  ) : (
                    <>
                      <Upload className="mr-2 size-4" />
                      Import {result.valid.length} Questions
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </AdminShell>
  );
}
