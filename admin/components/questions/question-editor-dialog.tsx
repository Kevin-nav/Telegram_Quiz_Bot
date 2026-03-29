"use client";

import { useState, useEffect, useMemo } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { Question } from "@/lib/mock-data";

interface QuestionEditorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  question: Question | null;
}

export function QuestionEditorDialog({
  open,
  onOpenChange,
  question,
}: QuestionEditorDialogProps) {
  const isEditing = question !== null;

  const [questionText, setQuestionText] = useState("");
  const [options, setOptions] = useState<string[]>(["", "", "", ""]);
  const [correctOption, setCorrectOption] = useState(0);
  const [explanation, setExplanation] = useState("");
  const [explanationCleared, setExplanationCleared] = useState(false);
  const [band, setBand] = useState("1");
  const [cognitiveLevel, setCognitiveLevel] = useState("knowledge");
  const [editorMode, setEditorMode] = useState<"visual" | "raw">("visual");
  const [rawJson, setRawJson] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (question) {
      setQuestionText(question.question_text);
      setOptions(question.options);
      setCorrectOption(question.correct_option);
      setExplanation(question.short_explanation);
      setBand(String(question.band));
      setCognitiveLevel(question.cognitive_level);
      setExplanationCleared(false);
    } else {
      setQuestionText("");
      setOptions(["", "", "", ""]);
      setCorrectOption(0);
      setExplanation("");
      setBand("1");
      setCognitiveLevel("knowledge");
      setExplanationCleared(false);
    }
    setEditorMode("visual");
  }, [question, open]);

  // Sync raw JSON when switching to raw mode
  function syncToRawJson() {
    const payload = {
      question_text: questionText,
      options,
      correct_option: correctOption,
      short_explanation: explanation,
      band: parseInt(band),
      cognitive_level: cognitiveLevel,
    };
    setRawJson(JSON.stringify(payload, null, 2));
  }

  // Parse raw JSON when switching back to visual
  function handleModeSwitch(mode: string) {
    if (mode === "raw") {
      syncToRawJson();
    } else if (mode === "visual" && editorMode === "raw") {
      try {
        const parsed = JSON.parse(rawJson);
        setQuestionText(parsed.question_text ?? "");
        setOptions(parsed.options ?? ["", "", "", ""]);
        setCorrectOption(parsed.correct_option ?? 0);
        setExplanation(parsed.short_explanation ?? "");
        setBand(String(parsed.band ?? 1));
        setCognitiveLevel(parsed.cognitive_level ?? "knowledge");
      } catch {
        // Keep current state if JSON is invalid
      }
    }
    setEditorMode(mode as "visual" | "raw");
  }

  // ─── Crucial validation: changing correct_option clears explanation ─────
  function handleCorrectOptionChange(index: number) {
    if (index !== correctOption) {
      setCorrectOption(index);
      setExplanation("");
      setExplanationCleared(true);
    }
  }

  function updateOption(index: number, value: string) {
    setOptions((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  }

  function addOption() {
    setOptions((prev) => [...prev, ""]);
  }

  function removeOption(index: number) {
    if (options.length <= 2) return;
    setOptions((prev) => prev.filter((_, i) => i !== index));
    if (correctOption >= options.length - 1) {
      setCorrectOption(0);
    }
  }

  async function handleSave() {
    setIsSaving(true);
    await new Promise((resolve) => setTimeout(resolve, 800));
    setIsSaving(false);
    onOpenChange(false);
  }

  // Simple LaTeX preview (renders as text with markers for now)
  const previewText = useMemo(() => {
    return questionText;
  }, [questionText]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[95vw] max-w-[95vw] sm:max-w-[95vw] md:max-w-4xl lg:max-w-6xl h-[95vh] max-h-[95vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? `Edit ${question.question_key}` : "New Question"}
          </DialogTitle>
          <DialogDescription>
            {isEditing
              ? `${question.course_name} · Band ${question.band}`
              : "Create a new question for the bank."}
          </DialogDescription>
        </DialogHeader>

        <Tabs value={editorMode} onValueChange={handleModeSwitch} className="flex-1 overflow-hidden flex flex-col">
          <TabsList className="w-fit">
            <TabsTrigger value="visual">Visual Editor</TabsTrigger>
            <TabsTrigger value="raw">Raw JSON</TabsTrigger>
          </TabsList>

          {/* ─── Visual Editor ─── */}
          <TabsContent value="visual" className="flex-1 overflow-y-auto mt-0 pt-4">
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Left: Form */}
              <div className="space-y-4">
                <div className="grid gap-2">
                  <Label htmlFor="q-text">Question Text</Label>
                  <Textarea
                    id="q-text"
                    rows={4}
                    placeholder="Enter the question text (LaTeX supported)..."
                    value={questionText}
                    onChange={(e) => setQuestionText(e.target.value)}
                    className="font-mono text-sm"
                  />
                </div>

                {/* Options */}
                <div className="grid gap-2">
                  <div className="flex items-center justify-between">
                    <Label>Options</Label>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={addOption}
                    >
                      + Add option
                    </Button>
                  </div>
                  {options.map((opt, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleCorrectOptionChange(i)}
                        className={cn(
                          "flex size-6 shrink-0 items-center justify-center rounded-full border text-xs font-medium transition-colors",
                          correctOption === i
                            ? "border-emerald-500 bg-emerald-500 text-white"
                            : "border-border hover:border-foreground/50",
                        )}
                      >
                        {String.fromCharCode(65 + i)}
                      </button>
                      <Input
                        value={opt}
                        onChange={(e) => updateOption(i, e.target.value)}
                        placeholder={`Option ${String.fromCharCode(65 + i)}`}
                        className="text-sm"
                      />
                      {options.length > 2 && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-7 shrink-0 text-muted-foreground hover:text-destructive"
                          onClick={() => removeOption(i)}
                        >
                          ×
                        </Button>
                      )}
                    </div>
                  ))}
                </div>

                {/* Explanation */}
                <div className="grid gap-2">
                  <Label
                    htmlFor="q-explanation"
                    className={cn(explanationCleared && !explanation && "text-destructive")}
                  >
                    Explanation
                    {explanationCleared && !explanation && (
                      <span className="ml-2 text-xs font-normal">
                        ⚠ Required — you changed the correct answer
                      </span>
                    )}
                  </Label>
                  <Textarea
                    id="q-explanation"
                    rows={3}
                    placeholder="Explain why this is the correct answer..."
                    value={explanation}
                    onChange={(e) => {
                      setExplanation(e.target.value);
                      if (e.target.value) setExplanationCleared(false);
                    }}
                    className={cn(
                      "text-sm",
                      explanationCleared && !explanation && "border-destructive ring-destructive/20",
                    )}
                  />
                </div>

                {/* Metadata */}
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="grid gap-2">
                    <Label>Band</Label>
                    <Select value={band} onValueChange={(v) => setBand(v ?? "1")}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">Band 1</SelectItem>
                        <SelectItem value="2">Band 2</SelectItem>
                        <SelectItem value="3">Band 3</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-2">
                    <Label>Cognitive Level</Label>
                    <Select value={cognitiveLevel} onValueChange={(v) => setCognitiveLevel(v ?? "knowledge")}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="knowledge">Knowledge</SelectItem>
                        <SelectItem value="comprehension">Comprehension</SelectItem>
                        <SelectItem value="application">Application</SelectItem>
                        <SelectItem value="analysis">Analysis</SelectItem>
                        <SelectItem value="synthesis">Synthesis</SelectItem>
                        <SelectItem value="evaluation">Evaluation</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              {/* Right: Preview */}
              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Live Preview
                  </span>
                  <Badge variant="outline" className="text-[10px]">
                    As seen in Telegram
                  </Badge>
                </div>
                <Separator className="mb-4" />

                <div className="space-y-3">
                  {/* Question text */}
                  <div className="rounded-lg bg-background p-3 shadow-sm">
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">
                      {previewText || (
                        <span className="text-muted-foreground italic">
                          Question text will appear here...
                        </span>
                      )}
                    </p>
                  </div>

                  {/* Options */}
                  <div className="space-y-1.5">
                    {options.map((opt, i) =>
                      opt ? (
                        <div
                          key={i}
                          className={cn(
                            "rounded-lg border px-3 py-2 text-sm",
                            correctOption === i
                              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                              : "bg-background",
                          )}
                        >
                          <span className="font-medium">
                            {String.fromCharCode(65 + i)}.
                          </span>{" "}
                          {opt}
                        </div>
                      ) : null,
                    )}
                  </div>

                  {/* Explanation */}
                  {explanation && (
                    <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
                      <p className="text-xs font-medium text-blue-600 mb-1">
                        Explanation
                      </p>
                      <p className="text-sm text-blue-800">{explanation}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </TabsContent>

          {/* ─── Raw JSON Editor ─── */}
          <TabsContent value="raw" className="flex-1 overflow-hidden mt-0 pt-4">
            <Textarea
              value={rawJson}
              onChange={(e) => setRawJson(e.target.value)}
              className="h-full min-h-[400px] font-mono text-xs"
              placeholder="Paste question JSON here..."
            />
          </TabsContent>
        </Tabs>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={isSaving || (explanationCleared && !explanation)}
          >
            {isSaving ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Saving...
              </>
            ) : isEditing ? (
              "Save Changes"
            ) : (
              "Create Question"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
