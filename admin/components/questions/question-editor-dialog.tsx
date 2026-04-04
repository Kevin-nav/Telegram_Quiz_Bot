"use client";

import { useState, useEffect, useMemo } from "react";
import { Loader2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
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
import { saveQuestion, type QuestionRecord } from "@/lib/api";
import { InlineMath } from "react-katex";
import "katex/dist/katex.min.css";
import { toast } from "sonner";

// Helper component to parse and render text mixed with LaTeX inline blocks ($...$)
function LatexText({ text }: { text: string }) {
  if (!text) return null;
  // Split the text on $math$ segments. Captures the segment including the $ delimiters.
  const parts = text.split(/(\$[^$\\]*(?:\\.[^$\\]*)*\$)/);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("$") && part.endsWith("$") && part.length > 1) {
          const math = part.slice(1, -1);
          return (
            <InlineMath
              key={i}
              math={math}
              renderError={(error: Error) => (
                <span className="text-red-500 font-mono text-xs" title={error.message}>
                  {part}
                </span>
              )}
            />
          );
        }
        return <span key={i} className="whitespace-pre-wrap">{part}</span>;
      })}
    </>
  );
}

interface QuestionEditorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  question: QuestionRecord | null;
}

export function QuestionEditorDialog({
  open,
  onOpenChange,
  question,
}: QuestionEditorDialogProps) {
  const queryClient = useQueryClient();
  const isEditing = question !== null;

  const [questionText, setQuestionText] = useState("");
  const [options, setOptions] = useState<string[]>(["", "", "", ""]);
  const [correctOption, setCorrectOption] = useState(0);
  const [explanation, setExplanation] = useState("");
  const [explanationCleared, setExplanationCleared] = useState(false);
  const [band, setBand] = useState("1");
  const [cognitiveLevel, setCognitiveLevel] = useState("knowledge");
  const [topicId, setTopicId] = useState("");
  const [baseScore, setBaseScore] = useState("1.0");
  const [noteReference, setNoteReference] = useState("1.0");
  const [distractorComplexity, setDistractorComplexity] = useState("1.0");
  const [processingComplexity, setProcessingComplexity] = useState("1.0");
  const [negativeStem, setNegativeStem] = useState("1.0");
  const [rawScore, setRawScore] = useState("1.0");
  const [scaledScore, setScaledScore] = useState("1.0");
  const [editorMode, setEditorMode] = useState<"visual" | "raw">("visual");
  const [rawJson, setRawJson] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (question) {
      setQuestionText(question.question_text);
      setOptions(question.options?.length ? question.options : ["", "", "", ""]);
      const answerIndex = (question.options ?? []).findIndex(
        (option) => option === question.correct_option_text,
      );
      setCorrectOption(answerIndex >= 0 ? answerIndex : 0);
      setExplanation(question.short_explanation ?? "");
      setBand(String(question.band));
      setCognitiveLevel(question.cognitive_level ?? "knowledge");
      setTopicId(question.topic_id || "");
      setBaseScore(question.base_score ? String(question.base_score) : "1.0");
      setNoteReference(question.note_reference ? String(question.note_reference) : "1.0");
      setDistractorComplexity(question.distractor_complexity ? String(question.distractor_complexity) : "1.0");
      setProcessingComplexity(question.processing_complexity ? String(question.processing_complexity) : "1.0");
      setNegativeStem(question.negative_stem ? String(question.negative_stem) : "1.0");
      setRawScore(question.raw_score ? String(question.raw_score) : "1.0");
      setScaledScore(question.scaled_score ? String(question.scaled_score) : "1.0");
      setExplanationCleared(false);
    } else {
      setQuestionText("");
      setOptions(["", "", "", ""]);
      setCorrectOption(0);
      setExplanation("");
      setBand("1");
      setCognitiveLevel("knowledge");
      setTopicId("");
      setBaseScore("1.0");
      setNoteReference("1.0");
      setDistractorComplexity("1.0");
      setProcessingComplexity("1.0");
      setNegativeStem("1.0");
      setRawScore("1.0");
      setScaledScore("1.0");
      setExplanationCleared(false);
    }
    setEditorMode("visual");
  }, [question, open]);

  // Sync raw JSON when switching to raw mode
  function syncToRawJson() {
    const payload = {
      topic_id: topicId,
      question_text: questionText,
      options,
      option_count: options.length,
      correct_option: correctOption,
      short_explanation: explanation,
      band: parseInt(band),
      cognitive_level: cognitiveLevel,
      base_score: parseFloat(baseScore),
      note_reference: parseFloat(noteReference),
      distractor_complexity: parseFloat(distractorComplexity),
      processing_complexity: parseFloat(processingComplexity),
      negative_stem: parseFloat(negativeStem),
      raw_score: parseFloat(rawScore),
      scaled_score: parseFloat(scaledScore),
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
        setTopicId(parsed.topic_id ?? "");
        setBaseScore(String(parsed.base_score ?? 1.0));
        setNoteReference(String(parsed.note_reference ?? 1.0));
        setDistractorComplexity(String(parsed.distractor_complexity ?? 1.0));
        setProcessingComplexity(String(parsed.processing_complexity ?? 1.0));
        setNegativeStem(String(parsed.negative_stem ?? 1.0));
        setRawScore(String(parsed.raw_score ?? 1.0));
        setScaledScore(String(parsed.scaled_score ?? 1.0));
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
    if (!question) {
      toast.error("Select an existing question before saving.");
      return;
    }

    setIsSaving(true);
    try {
      await saveQuestion(question.question_key, {
        question_text: questionText,
        options_text: options.join("\n"),
        correct_option_text: options[correctOption] ?? "",
        short_explanation: explanation,
        question_type: question.question_type || "MCQ",
        status: question.status || "draft",
        band: Number.parseInt(band, 10) || 1,
        topic_id: topicId,
        cognitive_level: cognitiveLevel,
      });
      await queryClient.invalidateQueries({ queryKey: ["questions"] });
      toast.success("Question updated.");
      onOpenChange(false);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Unable to save question.",
      );
    } finally {
      setIsSaving(false);
    }
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
              ? `${question.course_id} | Band ${question.band}`
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
                <div className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="grid gap-2">
                      <Label>Topic ID</Label>
                      <Input
                        value={topicId}
                        onChange={(e) => setTopicId(e.target.value)}
                        placeholder="e.g. order_of_diff_eq"
                        className="text-sm"
                      />
                    </div>
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

                  {/* Difficulty Metrics */}
                  <div className="space-y-3 rounded-lg border p-4 bg-muted/20">
                    <div className="font-medium text-sm text-muted-foreground mb-1">Scoring & Complexity Metrics</div>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                      <div className="grid gap-2">
                        <Label className="text-xs">Base Score</Label>
                        <Input type="number" step="0.1" value={baseScore} onChange={(e) => setBaseScore(e.target.value)} className="h-8 text-xs" />
                      </div>
                      <div className="grid gap-2">
                        <Label className="text-xs">Note Ref.</Label>
                        <Input type="number" step="0.1" value={noteReference} onChange={(e) => setNoteReference(e.target.value)} className="h-8 text-xs" />
                      </div>
                      <div className="grid gap-2">
                        <Label className="text-xs">Distractor Cmplx.</Label>
                        <Input type="number" step="0.1" value={distractorComplexity} onChange={(e) => setDistractorComplexity(e.target.value)} className="h-8 text-xs" />
                      </div>
                      <div className="grid gap-2">
                        <Label className="text-xs">Proc. Cmplx.</Label>
                        <Input type="number" step="0.1" value={processingComplexity} onChange={(e) => setProcessingComplexity(e.target.value)} className="h-8 text-xs" />
                      </div>
                      <div className="grid gap-2">
                        <Label className="text-xs">Neg. Stem</Label>
                        <Input type="number" step="0.1" value={negativeStem} onChange={(e) => setNegativeStem(e.target.value)} className="h-8 text-xs" />
                      </div>
                    </div>
                    <Separator className="my-2" />
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="grid gap-2">
                        <Label className="text-xs font-semibold text-emerald-600 dark:text-emerald-500">Raw Score</Label>
                        <Input type="number" step="0.01" value={rawScore} onChange={(e) => setRawScore(e.target.value)} className="h-8 text-xs font-semibold" />
                      </div>
                      <div className="grid gap-2">
                        <Label className="text-xs font-semibold text-emerald-600 dark:text-emerald-500">Scaled Score</Label>
                        <Input type="number" step="0.1" value={scaledScore} onChange={(e) => setScaledScore(e.target.value)} className="h-8 text-xs font-semibold" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right: Preview */}
              <div className="rounded-lg border bg-muted/30 p-4 flex flex-col gap-4 overflow-y-auto">
                <div className="flex flex-col gap-3">
                  <div className="mb-1 flex items-center justify-between shrink-0 px-1">
                    <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Live Preview
                    </span>
                    <Badge variant="outline" className="text-[10px]">
                      As seen in Telegram
                    </Badge>
                  </div>
                  <Separator />
                </div>

                {/* Simulated Question Card Image */}
                <div className="relative overflow-hidden rounded-md border bg-white p-6 shadow-sm font-serif text-slate-800 shrink-0">
                  {/* Watermark */}
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-[0.03]">
                    <span className="text-[#1A6B3A] text-8xl font-bold -rotate-45 transform scale-150">
                      TANJAH
                    </span>
                  </div>

                  <div className="relative z-10 space-y-5">
                    {/* Header */}
                    <div className="font-bold text-[#1A6B3A] text-xs uppercase tracking-wider">
                      TANJAH PHILP
                    </div>

                    {/* Question Box */}
                    <div
                      className="relative mt-4 rounded-md shadow-sm"
                      style={{
                        backgroundColor: 'white',
                        border: '1px solid rgba(26, 107, 58, 0.3)',
                        borderLeft: '4px solid #1A6B3A',
                      }}
                    >
                      <div
                        className="absolute -top-3 left-4 rounded px-2 py-0.5 text-sm font-bold shadow-sm"
                        style={{ backgroundColor: '#EDF2EE', color: '#1A6B3A' }}
                      >
                        Question
                      </div>
                      <div className="p-4 pt-5 whitespace-pre-wrap leading-relaxed font-serif text-[15px]">
                        {previewText ? (
                          <LatexText text={previewText} />
                        ) : (
                          <span className="text-muted-foreground italic font-sans text-sm">
                            Question text will appear here...
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Options Grid */}
                    <div className="grid grid-cols-2 gap-3 mt-4">
                      {options.map((opt, i) =>
                        opt ? (
                          <div
                            key={i}
                            className="relative rounded-md p-3 pl-4 flex items-center gap-3 shadow-sm bg-white"
                            style={{
                              border: '1px solid #F5B800',
                              borderLeft: '4px solid #F5B800',
                            }}
                          >
                            <span
                              className="font-bold shrink-0 text-[15px]"
                              style={{ color: '#C49300' }}
                            >
                              {String.fromCharCode(65 + i)}
                            </span>
                            <span className="leading-relaxed font-serif text-[15px]">
                              <LatexText text={opt} />
                            </span>
                          </div>
                        ) : null
                      )}
                    </div>

                    {/* Footer */}
                    <div className="flex items-center justify-between mt-6">
                      <span className="font-bold text-[#1A6B3A] text-[10px] opacity-80">
                        #YOUR_FINANCIAL_ENGINEER
                      </span>
                      <span className="font-mono font-bold text-[#1A6B3A] text-[10px] opacity-80">
                        @study_with_tanjah_bot
                      </span>
                    </div>
                  </div>
                </div>

                {/* Simulated Explanation Card Image */}
                {explanation && (
                  <div className="relative overflow-hidden rounded-md border bg-white p-6 shadow-sm font-serif text-slate-800 shrink-0">
                    {/* Watermark */}
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-[0.03]">
                      <span className="text-[#1A6B3A] text-8xl font-bold -rotate-45 transform scale-150">
                        TANJAH
                      </span>
                    </div>

                    <div className="relative z-10 space-y-5">
                      {/* Header */}
                      <div className="font-bold text-[#1A6B3A] text-xs uppercase tracking-wider">
                        TANJAH PHILP
                      </div>

                      {/* Correct Answer Box */}
                      {options[correctOption] && (
                        <div
                          className="relative mt-4 rounded-md shadow-sm"
                          style={{
                            backgroundColor: 'white',
                            border: '1px solid rgba(245, 184, 0, 0.4)',
                            borderLeft: '4px solid #F5B800',
                          }}
                        >
                          <div
                            className="absolute -top-3 left-4 rounded px-2 py-0.5 text-sm font-bold shadow-sm"
                            style={{ backgroundColor: '#FCF3D8', color: '#C49300' }}
                          >
                            Correct Answer
                          </div>
                          <div className="p-4 pt-5 whitespace-pre-wrap leading-relaxed font-serif text-[15px]">
                            <LatexText text={options[correctOption]} />
                          </div>
                        </div>
                      )}

                      {/* Explanation Box */}
                      <div
                        className="relative mt-4 rounded-md shadow-sm"
                        style={{
                          backgroundColor: 'white',
                          border: '1px solid rgba(26, 107, 58, 0.3)',
                          borderLeft: '4px solid #1A6B3A',
                        }}
                      >
                        <div
                          className="absolute -top-3 left-4 rounded px-2 py-0.5 text-sm font-bold shadow-sm"
                          style={{ backgroundColor: '#EDF2EE', color: '#1A6B3A' }}
                        >
                          Explanation
                        </div>
                        <div className="p-4 pt-5 whitespace-pre-wrap leading-relaxed font-serif text-[15px]">
                          <LatexText text={explanation} />
                        </div>
                      </div>

                      {/* Footer */}
                      <div className="flex items-center justify-between mt-6">
                        <span className="font-bold text-[#1A6B3A] text-[10px] opacity-80">
                          #YOUR_FINANCIAL_ENGINEER
                        </span>
                        <span className="font-mono font-bold text-[#1A6B3A] text-[10px] opacity-80">
                          @study_with_tanjah_bot
                        </span>
                      </div>
                    </div>
                  </div>
                )}
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
