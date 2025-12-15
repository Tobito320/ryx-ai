/**
 * Exam Taking View
 * 
 * Full-screen exam interface with all task types:
 * - Multiple Choice (single & multiple)
 * - Short Answer
 * - Fill in the Blank
 * - Matching
 * - Case Study
 * - Diagram Analysis
 * - Calculation
 */

import { useState, useEffect, useCallback } from "react";
import { useExam } from "@/context/ExamContext";
import {
  ChevronLeft,
  ChevronRight,
  Clock,
  Flag,
  Save,
  Send,
  AlertCircle,
  Check,
  X,
  HelpCircle,
  BookOpen,
  Calculator,
  Image,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import type { Task, TaskType, MockExam, TaskResponse } from "@/types/exam";

export function ExamTakingView() {
  const {
    currentAttempt,
    selectedMockExam,
    submitAnswer,
    finishAttempt,
    setExamView,
  } = useExam();

  const [currentTaskIndex, setCurrentTaskIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [flaggedTasks, setFlaggedTasks] = useState<Set<string>>(new Set());
  const [timeSpent, setTimeSpent] = useState(0);
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [showExitDialog, setShowExitDialog] = useState(false);

  const tasks = selectedMockExam?.tasks || [];
  const currentTask = tasks[currentTaskIndex];
  const totalTasks = tasks.length;

  // Timer
  useEffect(() => {
    const interval = setInterval(() => {
      setTimeSpent((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Auto-save every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      // Save state to localStorage
      localStorage.setItem(
        `exam-progress-${currentAttempt?.id}`,
        JSON.stringify({ answers, flaggedTasks: Array.from(flaggedTasks), timeSpent, currentTaskIndex })
      );
    }, 30000);
    return () => clearInterval(interval);
  }, [answers, flaggedTasks, timeSpent, currentTaskIndex, currentAttempt?.id]);

  // Load saved progress
  useEffect(() => {
    if (currentAttempt?.id) {
      const saved = localStorage.getItem(`exam-progress-${currentAttempt.id}`);
      if (saved) {
        try {
          const { answers: savedAnswers, flaggedTasks: savedFlagged, timeSpent: savedTime, currentTaskIndex: savedIndex } = JSON.parse(saved);
          setAnswers(savedAnswers || {});
          setFlaggedTasks(new Set(savedFlagged || []));
          setTimeSpent(savedTime || 0);
          setCurrentTaskIndex(savedIndex || 0);
        } catch (e) {
          // Ignore parse errors
        }
      }
    }
  }, [currentAttempt?.id]);

  const handleAnswerChange = useCallback((taskId: string, answer: string | string[]) => {
    setAnswers((prev) => ({ ...prev, [taskId]: answer }));
  }, []);

  const handleToggleFlag = useCallback((taskId: string) => {
    setFlaggedTasks((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  }, []);

  const handleSubmit = async () => {
    // Submit all answers
    for (const [taskId, answer] of Object.entries(answers)) {
      await submitAnswer(taskId, answer);
    }
    
    // Finish attempt
    const result = await finishAttempt();
    if (result) {
      // Clear saved progress
      localStorage.removeItem(`exam-progress-${currentAttempt?.id}`);
      setExamView("history");
    }
  };

  const handleExit = () => {
    // Save progress
    localStorage.setItem(
      `exam-progress-${currentAttempt?.id}`,
      JSON.stringify({ answers, flaggedTasks: Array.from(flaggedTasks), timeSpent, currentTaskIndex })
    );
    setExamView("themas");
  };

  const formatTime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
    }
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const answeredCount = Object.keys(answers).filter(
    (taskId) => answers[taskId] && (Array.isArray(answers[taskId]) ? answers[taskId].length > 0 : answers[taskId])
  ).length;

  const progressPercent = (answeredCount / totalTasks) * 100;

  if (!currentTask || !selectedMockExam) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-muted-foreground">Keine Klausur ausgewählt</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="border-b border-border p-4 bg-card">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => setShowExitDialog(true)}>
              <X className="h-4 w-4 mr-2" />
              Beenden
            </Button>
            <div className="h-6 w-px bg-border" />
            <h1 className="font-semibold">{selectedMockExam.title}</h1>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Timer */}
            <div className="flex items-center gap-2 text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span className="font-mono">{formatTime(timeSpent)}</span>
              {selectedMockExam.estimatedDurationMinutes && (
                <span className="text-xs">
                  / {selectedMockExam.estimatedDurationMinutes} Min.
                </span>
              )}
            </div>
            
            {/* Progress */}
            <div className="flex items-center gap-2">
              <Progress value={progressPercent} className="w-24 h-2" />
              <span className="text-sm text-muted-foreground">
                {answeredCount}/{totalTasks}
              </span>
            </div>
            
            {/* Submit */}
            <Button onClick={() => setShowSubmitDialog(true)}>
              <Send className="h-4 w-4 mr-2" />
              Abgeben
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Task Navigator (Left) */}
        <div className="w-20 border-r border-border bg-muted/30 p-2">
          <ScrollArea className="h-full">
            <div className="grid grid-cols-2 gap-1">
              {tasks.map((task, index) => {
                const isAnswered = answers[task.id] && (
                  Array.isArray(answers[task.id]) ? answers[task.id].length > 0 : answers[task.id]
                );
                const isFlagged = flaggedTasks.has(task.id);
                const isCurrent = index === currentTaskIndex;

                return (
                  <button
                    key={task.id}
                    onClick={() => setCurrentTaskIndex(index)}
                    className={cn(
                      "w-8 h-8 rounded text-xs font-medium flex items-center justify-center relative",
                      isCurrent && "ring-2 ring-primary",
                      isAnswered && !isCurrent && "bg-green-500/20 text-green-700 dark:text-green-400",
                      !isAnswered && !isCurrent && "bg-muted hover:bg-muted/80",
                      isFlagged && "ring-2 ring-amber-500"
                    )}
                  >
                    {index + 1}
                    {isFlagged && (
                      <Flag className="h-2 w-2 absolute -top-1 -right-1 text-amber-500" />
                    )}
                  </button>
                );
              })}
            </div>
          </ScrollArea>
        </div>

        {/* Task Content (Center) */}
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-3xl mx-auto">
            {/* Task Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <Badge variant="outline">
                  Aufgabe {currentTaskIndex + 1} von {totalTasks}
                </Badge>
                <Badge variant="secondary">
                  {getTaskTypeLabel(currentTask.type)}
                </Badge>
                <Badge variant="outline">
                  {currentTask.points} {currentTask.points === 1 ? "Punkt" : "Punkte"}
                </Badge>
              </div>
              <Button
                variant={flaggedTasks.has(currentTask.id) ? "default" : "ghost"}
                size="sm"
                onClick={() => handleToggleFlag(currentTask.id)}
              >
                <Flag className={cn("h-4 w-4", flaggedTasks.has(currentTask.id) && "fill-current")} />
              </Button>
            </div>

            {/* Question */}
            <Card className="mb-6">
              <CardContent className="p-6">
                <p className="text-lg leading-relaxed whitespace-pre-wrap">
                  {currentTask.questionText}
                </p>
                
                {/* Question Image */}
                {currentTask.questionImage && (
                  <div className="mt-4 rounded-lg overflow-hidden border">
                    <img
                      src={currentTask.questionImage}
                      alt={currentTask.questionImageAlt || "Aufgabenbild"}
                      className="max-w-full h-auto"
                    />
                  </div>
                )}
                
                {/* Diagram Data */}
                {currentTask.diagramData && (
                  <div className="mt-4 p-4 bg-muted rounded-lg">
                    <div className="flex items-center gap-2 mb-2 text-muted-foreground">
                      <Image className="h-4 w-4" />
                      <span className="text-sm">{currentTask.diagramData.type} Diagramm</span>
                    </div>
                    <p className="text-sm">{currentTask.diagramData.description}</p>
                  </div>
                )}
                
                {/* Calculation Data */}
                {currentTask.calculationData && (
                  <div className="mt-4 p-4 bg-muted rounded-lg">
                    <div className="flex items-center gap-2 mb-2 text-muted-foreground">
                      <Calculator className="h-4 w-4" />
                      <span className="text-sm">Gegebene Werte</span>
                    </div>
                    <div className="space-y-1">
                      {currentTask.calculationData.givenValues.map((value, i) => (
                        <p key={i} className="text-sm">
                          {value.name}: <strong>{value.value} {value.unit || ""}</strong>
                        </p>
                      ))}
                    </div>
                    {currentTask.calculationData.formula && (
                      <p className="text-sm mt-2 text-muted-foreground">
                        Formel: {currentTask.calculationData.formula}
                      </p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Answer Input */}
            <div className="space-y-4">
              <TaskInput
                task={currentTask}
                value={answers[currentTask.id]}
                onChange={(value) => handleAnswerChange(currentTask.id, value)}
              />
            </div>

            {/* Hints */}
            {currentTask.hints && currentTask.hints.length > 0 && (
              <div className="mt-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                <div className="flex items-center gap-2 mb-2 text-blue-600 dark:text-blue-400">
                  <HelpCircle className="h-4 w-4" />
                  <span className="font-medium">Hinweise</span>
                </div>
                <ul className="list-disc list-inside text-sm space-y-1">
                  {currentTask.hints.map((hint, i) => (
                    <li key={i}>{hint}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Navigation (Right) */}
        <div className="w-64 border-l border-border p-4 flex flex-col">
          <h3 className="font-medium mb-4">Übersicht</h3>
          
          {/* Legend */}
          <div className="space-y-2 text-sm mb-6">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-green-500/20 rounded" />
              <span>Beantwortet</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-muted rounded" />
              <span>Nicht beantwortet</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-amber-500/20 rounded ring-2 ring-amber-500" />
              <span>Markiert</span>
            </div>
          </div>

          {/* Stats */}
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Beantwortet</span>
              <span className="font-medium">{answeredCount}/{totalTasks}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Markiert</span>
              <span className="font-medium">{flaggedTasks.size}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Punkte gesamt</span>
              <span className="font-medium">{selectedMockExam.totalPoints}</span>
            </div>
          </div>

          <div className="flex-1" />

          {/* Navigation Buttons */}
          <div className="space-y-2">
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setCurrentTaskIndex(Math.max(0, currentTaskIndex - 1))}
                disabled={currentTaskIndex === 0}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Zurück
              </Button>
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setCurrentTaskIndex(Math.min(totalTasks - 1, currentTaskIndex + 1))}
                disabled={currentTaskIndex === totalTasks - 1}
              >
                Weiter
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Submit Dialog */}
      <AlertDialog open={showSubmitDialog} onOpenChange={setShowSubmitDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Klausur abgeben?</AlertDialogTitle>
            <AlertDialogDescription>
              {answeredCount < totalTasks ? (
                <>
                  Du hast erst {answeredCount} von {totalTasks} Aufgaben beantwortet.
                  Bist du sicher, dass du die Klausur abgeben möchtest?
                </>
              ) : (
                <>
                  Du hast alle {totalTasks} Aufgaben beantwortet.
                  Möchtest du die Klausur jetzt abgeben?
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Weiter bearbeiten</AlertDialogCancel>
            <AlertDialogAction onClick={handleSubmit}>
              Ja, abgeben
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Exit Dialog */}
      <AlertDialog open={showExitDialog} onOpenChange={setShowExitDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Klausur verlassen?</AlertDialogTitle>
            <AlertDialogDescription>
              Dein Fortschritt wird gespeichert und du kannst später fortfahren.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Weiter bearbeiten</AlertDialogCancel>
            <AlertDialogAction onClick={handleExit}>
              Verlassen
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// ============================================================================
// Task Input Component
// ============================================================================

interface TaskInputProps {
  task: Task;
  value: string | string[] | undefined;
  onChange: (value: string | string[]) => void;
}

function TaskInput({ task, value, onChange }: TaskInputProps) {
  switch (task.type) {
    case "MC_SingleChoice":
      return (
        <RadioGroup
          value={value as string || ""}
          onValueChange={onChange}
          className="space-y-3"
        >
          {task.options?.map((option) => (
            <div
              key={option.id}
              className={cn(
                "flex items-center space-x-3 p-4 border rounded-lg transition-colors",
                value === option.id && "border-primary bg-primary/5"
              )}
            >
              <RadioGroupItem value={option.id} id={option.id} />
              <Label htmlFor={option.id} className="flex-1 cursor-pointer">
                <span className="font-medium mr-2">{option.id})</span>
                {option.text}
              </Label>
            </div>
          ))}
        </RadioGroup>
      );

    case "MC_MultipleChoice":
      const selectedOptions = Array.isArray(value) ? value : [];
      return (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Mehrere Antworten möglich
          </p>
          {task.options?.map((option) => (
            <div
              key={option.id}
              className={cn(
                "flex items-center space-x-3 p-4 border rounded-lg transition-colors",
                selectedOptions.includes(option.id) && "border-primary bg-primary/5"
              )}
            >
              <Checkbox
                id={option.id}
                checked={selectedOptions.includes(option.id)}
                onCheckedChange={(checked) => {
                  if (checked) {
                    onChange([...selectedOptions, option.id]);
                  } else {
                    onChange(selectedOptions.filter((id) => id !== option.id));
                  }
                }}
              />
              <Label htmlFor={option.id} className="flex-1 cursor-pointer">
                <span className="font-medium mr-2">{option.id})</span>
                {option.text}
              </Label>
            </div>
          ))}
        </div>
      );

    case "ShortAnswer":
    case "Explanation":
    case "Justification":
      return (
        <div className="space-y-2">
          <Label>Deine Antwort</Label>
          <Textarea
            value={value as string || ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Schreibe deine Antwort hier..."
            className="min-h-[150px]"
          />
          <p className="text-sm text-muted-foreground">
            Erwartete Länge: 2-4 Sätze
          </p>
        </div>
      );

    case "CaseStudy":
      return (
        <div className="space-y-2">
          <Label>Deine Analyse</Label>
          <Textarea
            value={value as string || ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Analysiere den Fall und formuliere deine Empfehlungen..."
            className="min-h-[300px]"
          />
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>Empfohlene Struktur:</span>
            <Badge variant="outline">1. Analyse</Badge>
            <Badge variant="outline">2. Bewertung</Badge>
            <Badge variant="outline">3. Empfehlung</Badge>
          </div>
        </div>
      );

    case "FillInBlank":
      return (
        <div className="space-y-4">
          <Label>Fülle die Lücken aus</Label>
          {task.fillInBlanks?.map((blank, index) => (
            <div key={blank.id} className="flex items-center gap-3">
              <span className="font-medium">Lücke {index + 1}:</span>
              <Input
                value={(value as string[])?.[index] || ""}
                onChange={(e) => {
                  const newValues = [...((value as string[]) || [])];
                  newValues[index] = e.target.value;
                  onChange(newValues);
                }}
                placeholder="..."
                className="max-w-xs"
              />
            </div>
          ))}
        </div>
      );

    case "Calculation":
      return (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Rechenweg (optional)</Label>
            <Textarea
              value={typeof value === "object" && !Array.isArray(value) ? (value as any).steps || "" : ""}
              onChange={(e) => {
                const current = typeof value === "object" ? value : { answer: value || "" };
                onChange({ ...current, steps: e.target.value } as any);
              }}
              placeholder="Zeige deinen Rechenweg..."
              className="min-h-[100px] font-mono"
            />
          </div>
          <div className="space-y-2">
            <Label>Ergebnis</Label>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                value={typeof value === "object" && !Array.isArray(value) ? (value as any).answer || "" : value || ""}
                onChange={(e) => {
                  const current = typeof value === "object" ? value : { steps: "" };
                  onChange({ ...current, answer: e.target.value } as any);
                }}
                placeholder="0"
                className="max-w-xs"
              />
              {task.calculationData?.expectedUnit && (
                <span className="text-muted-foreground">{task.calculationData.expectedUnit}</span>
              )}
            </div>
          </div>
        </div>
      );

    case "DiagramAnalysis":
      return (
        <div className="space-y-2">
          <Label>Deine Analyse</Label>
          <Textarea
            value={value as string || ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Beschreibe, was du im Diagramm siehst und ziehe Schlussfolgerungen..."
            className="min-h-[200px]"
          />
        </div>
      );

    case "Matching":
      return (
        <div className="space-y-4">
          <Label>Ordne die Begriffe zu</Label>
          {task.matchingPairs?.map((pair, index) => (
            <div key={pair.id} className="flex items-center gap-4">
              <div className="flex-1 p-3 bg-muted rounded-lg">
                {pair.left}
              </div>
              <span>→</span>
              <Input
                value={(value as string[])?.[index] || ""}
                onChange={(e) => {
                  const newValues = [...((value as string[]) || [])];
                  newValues[index] = e.target.value;
                  onChange(newValues);
                }}
                placeholder="Zuordnung..."
                className="flex-1"
              />
            </div>
          ))}
        </div>
      );

    default:
      return (
        <div className="space-y-2">
          <Label>Deine Antwort</Label>
          <Textarea
            value={value as string || ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Schreibe deine Antwort hier..."
            className="min-h-[150px]"
          />
        </div>
      );
  }
}

// ============================================================================
// Helpers
// ============================================================================

function getTaskTypeLabel(type: TaskType): string {
  const labels: Record<TaskType, string> = {
    MC_SingleChoice: "Multiple Choice",
    MC_MultipleChoice: "Mehrfachauswahl",
    ShortAnswer: "Kurzantwort",
    FillInBlank: "Lückentext",
    Matching: "Zuordnung",
    CaseStudy: "Fallstudie",
    DiagramAnalysis: "Diagrammanalyse",
    Calculation: "Berechnung",
    Explanation: "Erläuterung",
    Justification: "Begründung",
  };
  return labels[type] || type;
}

export default ExamTakingView;
