/**
 * Attempt History View
 * 
 * Shows past attempts with scores, grades, and detailed feedback
 */

import { useEffect, useState } from "react";
import { useExam } from "@/context/ExamContext";
import {
  History,
  ChevronLeft,
  Clock,
  Target,
  Award,
  TrendingUp,
  AlertCircle,
  Loader2,
  Calendar,
  FileText,
  Lightbulb,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Attempt, MockExam, GradeText, Task, TaskGrade, TaskResponse } from "@/types/exam";
import {
  getAttemptResultsV2,
  type AttemptResultsV2Response,
  type GradingResultV2,
  type TaskGradeV2,
} from "@/services/examService";

interface AttemptHistoryViewProps {
  onBack: () => void;
}

const LOW_CONFIDENCE_THRESHOLD = 75;

interface NormalizedTaskResponse {
  taskId: string;
  userAnswer: string | string[] | Record<string, any>;
}

interface NormalizedGradingResult {
  totalScore: number;
  totalPoints: number;
  percentage: number;
  grade: number;
  gradeText: GradeText | string;
  overallFeedback: string;
  manualReviewFlagged: boolean;
  graderConfidence: number;
  tasksNeedingReview: string[];
  taskGrades: TaskGrade[];
}

interface AttemptResultData {
  mockExam: MockExam;
  gradingResult: NormalizedGradingResult;
  taskResponses: Record<string, NormalizedTaskResponse>;
}

export function AttemptHistoryView({ onBack }: AttemptHistoryViewProps) {
  const { attempts, mockExams, selectedThema } = useExam();
  const [selectedAttemptId, setSelectedAttemptId] = useState<string | null>(null);
  const [attemptResults, setAttemptResults] = useState<Record<string, AttemptResultData>>({});
  const [loadingResults, setLoadingResults] = useState<Record<string, boolean>>({});
  const [resultErrors, setResultErrors] = useState<Record<string, string>>({});

  // Filter attempts for selected thema
  const filteredAttempts = selectedThema
    ? attempts.filter((a) => {
        const exam = mockExams.find((m) => m.id === a.mockExamId);
        return exam?.themaIds.includes(selectedThema.id);
      })
    : attempts;

  // Sort by date descending
  const sortedAttempts = [...filteredAttempts].sort(
    (a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime()
  );

  const selectedAttempt = selectedAttemptId
    ? attempts.find((a) => a.id === selectedAttemptId)
    : null;

  const selectedMockExam = selectedAttempt
    ? mockExams.find((m) => m.id === selectedAttempt.mockExamId)
    : null;
  const selectedAttemptResult = selectedAttempt
    ? attemptResults[selectedAttempt.id]
    : undefined;
  const attemptResultError = selectedAttempt
    ? resultErrors[selectedAttempt.id]
    : null;
  const attemptResultLoading = selectedAttempt
    ? !!loadingResults[selectedAttempt.id]
    : false;

  useEffect(() => {
    if (!selectedAttempt || selectedAttempt.status !== "graded") {
      return;
    }

    const attemptId = selectedAttempt.id;
    if (attemptResults[attemptId] || loadingResults[attemptId]) {
      return;
    }

    let cancelled = false;
    setLoadingResults((prev) => ({ ...prev, [attemptId]: true }));

    getAttemptResultsV2(attemptId)
      .then((payload) => {
        if (cancelled) return;
        const normalized = normalizeAttemptResultResponse(payload);
        setAttemptResults((prev) => ({ ...prev, [attemptId]: normalized }));
        setResultErrors((prev) => {
          const next = { ...prev };
          delete next[attemptId];
          return next;
        });
      })
      .catch((err) => {
        if (cancelled) return;
        const message =
          err instanceof Error
            ? err.message
            : "Ergebnis konnte nicht geladen werden";
        setResultErrors((prev) => ({ ...prev, [attemptId]: message }));
      })
      .finally(() => {
        if (cancelled) return;
        setLoadingResults((prev) => {
          const next = { ...prev };
          delete next[attemptId];
          return next;
        });
      });

    return () => {
      cancelled = true;
    };
  }, [selectedAttempt, attemptResults, loadingResults]);

  // Calculate stats
  const completedAttempts = sortedAttempts.filter((a) => a.status === "graded");
  const avgGrade =
    completedAttempts.length > 0
      ? completedAttempts.reduce((sum, a) => sum + a.grade, 0) / completedAttempts.length
      : 0;
  const avgPercentage =
    completedAttempts.length > 0
      ? completedAttempts.reduce((sum, a) => sum + a.percentage, 0) / completedAttempts.length
      : 0;
  const bestGrade = completedAttempts.length > 0
    ? Math.min(...completedAttempts.map((a) => a.grade))
    : 0;

  // Progress trend
  const hasImproved =
    completedAttempts.length >= 2 &&
    completedAttempts[0].grade < completedAttempts[completedAttempts.length - 1].grade;

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="border-b border-border p-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={onBack}>
            <ChevronLeft className="h-4 w-4 mr-2" />
            Zurück
          </Button>
          <div className="h-6 w-px bg-border" />
          <div className="flex items-center gap-2">
            <History className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-semibold">
              Verlauf {selectedThema && `- ${selectedThema.name}`}
            </h1>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full flex">
          {/* Attempts List */}
          <div className="w-96 border-r border-border flex flex-col">
            {/* Stats Header */}
            <div className="p-4 border-b bg-muted/30">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-2xl font-bold">{completedAttempts.length}</div>
                  <div className="text-xs text-muted-foreground">Versuche</div>
                </div>
                <div>
                  <div className="text-2xl font-bold">{avgGrade.toFixed(1)}</div>
                  <div className="text-xs text-muted-foreground">Ø Note</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-600">{bestGrade.toFixed(1)}</div>
                  <div className="text-xs text-muted-foreground">Beste</div>
                </div>
              </div>
              {hasImproved && (
                <div className="mt-3 flex items-center justify-center gap-2 text-green-600 text-sm">
                  <TrendingUp className="h-4 w-4" />
                  <span>Du verbesserst dich!</span>
                </div>
              )}
            </div>

            {/* List */}
            <ScrollArea className="flex-1">
              <div className="p-2 space-y-2">
                {sortedAttempts.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <History className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Noch keine Versuche</p>
                  </div>
                ) : (
                  sortedAttempts.map((attempt) => {
                    const exam = mockExams.find((m) => m.id === attempt.mockExamId);
                    const isSelected = selectedAttemptId === attempt.id;

                    return (
                      <Card
                        key={attempt.id}
                        className={cn(
                          "cursor-pointer transition-colors",
                          isSelected && "border-primary"
                        )}
                        onClick={() => setSelectedAttemptId(attempt.id)}
                      >
                        <CardContent className="p-3">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <GradeIndicator grade={attempt.grade} />
                              <span className="font-medium">{attempt.grade.toFixed(1)}</span>
                            </div>
                            <Badge variant={getStatusVariant(attempt.status)}>
                              {getStatusLabel(attempt.status)}
                            </Badge>
                          </div>
                          <div className="text-sm text-muted-foreground mb-2 truncate">
                            {exam?.title || "Unbekannte Klausur"}
                          </div>
                          <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <div className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {formatDate(attempt.startedAt)}
                            </div>
                            <div className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {formatDuration(attempt.durationSeconds)}
                            </div>
                          </div>
                          <Progress
                            value={attempt.percentage}
                            className="h-1 mt-2"
                          />
                        </CardContent>
                      </Card>
                    );
                  })
                )}
              </div>
            </ScrollArea>
          </div>

          {/* Detail View */}
          <div className="flex-1 overflow-auto">
            {selectedAttempt && selectedMockExam ? (
              <AttemptDetail
                attempt={selectedAttempt}
                mockExam={selectedMockExam}
                resultData={selectedAttemptResult}
                loadingResult={attemptResultLoading}
                resultError={attemptResultError}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Wähle einen Versuch aus der Liste</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Detail Component
// ============================================================================

function AttemptDetail({
  attempt,
  mockExam,
  resultData,
  loadingResult = false,
  resultError,
}: {
  attempt: Attempt;
  mockExam: MockExam;
  resultData?: AttemptResultData;
  loadingResult?: boolean;
  resultError?: string | null;
}) {
  const gradingSummary = resultData?.gradingResult;
  const activeMockExam = resultData?.mockExam ?? mockExam;
  const tasks = activeMockExam.tasks ?? [];
  const apiResponseMap = resultData?.taskResponses ?? {};
  const attemptResponseMap = mapAttemptResponses(attempt.taskResponses);
  const gradeMap = buildGradeMap(gradingSummary?.taskGrades, attempt.taskResponses);
  const totalScore = gradingSummary?.totalScore ?? attempt.totalScore;
  const totalPoints = gradingSummary?.totalPoints ?? attempt.totalPoints;
  const percentage = gradingSummary?.percentage ?? attempt.percentage;
  const gradeValue = gradingSummary?.grade ?? attempt.grade;
  const gradeText = (gradingSummary?.gradeText as GradeText | undefined) ?? attempt.gradeText;
  const overallFeedback = gradingSummary?.overallFeedback ?? attempt.overallFeedback;
  const tasksNeedingReview = gradingSummary?.tasksNeedingReview ?? attempt.flagsForReview;
  const manualReviewFlagged =
    gradingSummary?.manualReviewFlagged ?? attempt.flagsForReview.length > 0;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold">{activeMockExam.title}</h2>
          <p className="text-muted-foreground">
            {formatDate(attempt.startedAt)} • {formatDuration(attempt.durationSeconds)}
          </p>
        </div>
        <div className="text-right">
          <div className="text-4xl font-bold">{gradeValue.toFixed(1)}</div>
          <div className={cn("text-lg font-medium", getGradeColor(gradeValue))}>
            {gradeText}
          </div>
        </div>
      </div>

      {/* Score Overview */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <Target className="h-8 w-8 mx-auto mb-2 text-primary" />
            <div className="text-2xl font-bold">
              {totalScore}/{totalPoints}
            </div>
            <div className="text-sm text-muted-foreground">Punkte</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Award className="h-8 w-8 mx-auto mb-2 text-amber-500" />
            <div className="text-2xl font-bold">{Math.round(percentage)}%</div>
            <div className="text-sm text-muted-foreground">Prozent</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Clock className="h-8 w-8 mx-auto mb-2 text-blue-500" />
            <div className="text-2xl font-bold">
              {formatDuration(attempt.durationSeconds)}
            </div>
            <div className="text-sm text-muted-foreground">Dauer</div>
          </CardContent>
        </Card>
      </div>

      {(loadingResult || resultError) && (
        <div className="space-y-2">
          {loadingResult && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>AI Feedback wird geladen...</span>
            </div>
          )}
          {resultError && (
            <div className="flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4" />
              <span>{resultError}</span>
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="feedback">
        <TabsList>
          <TabsTrigger value="feedback">Feedback</TabsTrigger>
          <TabsTrigger value="breakdown">Aufschlüsselung</TabsTrigger>
          <TabsTrigger value="answers">Antworten</TabsTrigger>
        </TabsList>

        <TabsContent value="feedback" className="mt-4 space-y-4">
          {/* AI Feedback */}
          {overallFeedback && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Gesamtfeedback</CardTitle>
              </CardHeader>
              <CardContent>
                <p>{overallFeedback}</p>
              </CardContent>
            </Card>
          )}

          {/* Section Breakdown */}
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Wissensteil</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl font-bold">
                    {Math.round(attempt.sectionBreakdown.knowledgeSection.percentage)}%
                  </span>
                  <span className="text-muted-foreground">
                    {attempt.sectionBreakdown.knowledgeSection.earned}/
                    {attempt.sectionBreakdown.knowledgeSection.max} Pkt.
                  </span>
                </div>
                <Progress
                  value={attempt.sectionBreakdown.knowledgeSection.percentage}
                  className="h-2"
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Anwendungsteil</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl font-bold">
                    {Math.round(attempt.sectionBreakdown.applicationSection.percentage)}%
                  </span>
                  <span className="text-muted-foreground">
                    {attempt.sectionBreakdown.applicationSection.earned}/
                    {attempt.sectionBreakdown.applicationSection.max} Pkt.
                  </span>
                </div>
                <Progress
                  value={attempt.sectionBreakdown.applicationSection.percentage}
                  className="h-2"
                />
              </CardContent>
            </Card>
          </div>

          {/* Flagged for Review */}
          {manualReviewFlagged && tasksNeedingReview.length > 0 && (
            <Card className="border-amber-500/50 bg-amber-500/5">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-amber-500" />
                  Zur Überprüfung markiert
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {tasksNeedingReview.length} Aufgabe(n) wurden aufgrund niedriger AI-Sicherheit markiert.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="breakdown" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Leistung nach Aufgabentyp</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { label: "Multiple Choice", percentage: 85 },
                  { label: "Kurzantworten", percentage: 72 },
                  { label: "Fallstudien", percentage: 68 },
                  { label: "Berechnungen", percentage: 75 },
                ].map((item) => (
                  <div key={item.label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span>{item.label}</span>
                      <span className="font-medium">{item.percentage}%</span>
                    </div>
                    <Progress value={item.percentage} className="h-2" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="answers" className="mt-4 space-y-4">
          {tasks.map((task, index) => {
            const grade = gradeMap[task.id];
            const apiResponse = apiResponseMap[task.id];
            const fallbackResponse = attemptResponseMap[task.id];
            const userAnswer = apiResponse?.userAnswer ?? fallbackResponse?.userAnswer;
            const earned = grade?.earnedPoints ?? fallbackResponse?.earnedPoints ?? 0;
            const maxPoints = grade?.maxPoints ?? fallbackResponse?.maxPoints ?? task.points;
            const confidence = grade?.confidence ?? fallbackResponse?.confidence ?? 0;
            const rationale = grade?.feedback ?? fallbackResponse?.feedback;
            const improvementSuggestion =
              grade?.improvementSuggestion ?? fallbackResponse?.improvementSuggestion;
            const flagged =
              confidence < LOW_CONFIDENCE_THRESHOLD ||
              tasksNeedingReview.includes(task.id) ||
              fallbackResponse?.flaggedForReview;

            return (
              <Card key={task.id}>
                <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-base flex items-center gap-2">
                      <span className="text-muted-foreground">Aufgabe {index + 1}</span>
                      <span className="font-semibold">{getTaskTypeLabel(task.type)}</span>
                    </CardTitle>
                    <CardDescription className="line-clamp-2">
                      {task.questionText}
                    </CardDescription>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={earned === maxPoints ? "default" : "secondary"}>
                      {earned}/{maxPoints} Punkte
                    </Badge>
                    <Badge
                      variant={confidence >= 90 ? "default" : confidence >= 75 ? "secondary" : "destructive"}
                    >
                      {confidence}% AI
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {task.questionImage && (
                    <div className="rounded-md border bg-muted/40 p-3">
                      <img src={task.questionImage} alt="Aufgabenbild" className="max-h-64 rounded object-contain" />
                    </div>
                  )}

                  <div className="rounded-md bg-muted/30 p-3">
                    <p className="text-xs text-muted-foreground">Deine Antwort</p>
                    <p className="font-medium">{formatAnswer(userAnswer)}</p>
                  </div>

                  {rationale && (
                    <div className="rounded-md border-l-4 border-primary/60 bg-primary/5 p-3">
                      <p className="text-xs font-semibold text-primary">AI Feedback</p>
                      <p className="italic leading-relaxed text-muted-foreground mt-1">{rationale}</p>
                    </div>
                  )}

                  {improvementSuggestion && (
                    <div className="flex items-start gap-2 rounded-md bg-amber-50 p-3 text-amber-800">
                      <Lightbulb className="h-4 w-4 mt-0.5" />
                      <div>
                        <p className="text-xs font-semibold">Verbesserung</p>
                        <p>{improvementSuggestion}</p>
                      </div>
                    </div>
                  )}

                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">AI-Sicherheit</p>
                    <div className="h-2 w-full rounded-full bg-muted">
                      <div
                        className={cn(
                          "h-2 rounded-full transition-all",
                          getConfidenceColor(confidence)
                        )}
                        style={{ width: `${confidence}%` }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">{confidence}%</p>
                  </div>

                  {flagged && (
                    <div className="flex items-center gap-2 text-sm text-amber-600">
                      <AlertCircle className="h-4 w-4" />
                      <span>⚠️ Diese Aufgabe wurde zur manuellen Überprüfung markiert</span>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ============================================================================
// Helpers
// ============================================================================

function GradeIndicator({ grade }: { grade: number }) {
  const color = getGradeColor(grade);
  return (
    <div
      className={cn(
        "w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold",
        grade <= 2 && "bg-green-500/20 text-green-600",
        grade > 2 && grade <= 3.5 && "bg-amber-500/20 text-amber-600",
        grade > 3.5 && "bg-red-500/20 text-red-600"
      )}
    >
      {grade.toFixed(1)}
    </div>
  );
}

function getGradeColor(grade: number): string {
  if (grade <= 2) return "text-green-600";
  if (grade <= 3.5) return "text-amber-600";
  return "text-red-600";
}

function getStatusVariant(status: Attempt["status"]): "default" | "secondary" | "outline" {
  switch (status) {
    case "graded":
      return "default";
    case "in_progress":
      return "secondary";
    case "submitted":
      return "outline";
    default:
      return "outline";
  }
}

function getStatusLabel(status: Attempt["status"]): string {
  switch (status) {
    case "graded":
      return "Bewertet";
    case "in_progress":
      return "In Bearbeitung";
    case "submitted":
      return "Abgegeben";
    case "reviewed":
      return "Überprüft";
    default:
      return status;
  }
}

function getTaskTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    MC_SingleChoice: "MC",
    MC_MultipleChoice: "MC (Mehrfach)",
    ShortAnswer: "Kurzantwort",
    CaseStudy: "Fallstudie",
    DiagramAnalysis: "Diagramm",
    Calculation: "Berechnung",
    FillInBlank: "Lückentext",
    Matching: "Zuordnung",
    Explanation: "Erläuterung",
    Justification: "Begründung",
  };
  return labels[type] || type;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins < 60) {
    return `${mins}:${secs.toString().padStart(2, "0")} Min.`;
  }
  const hrs = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  return `${hrs}:${remainingMins.toString().padStart(2, "0")} Std.`;
}

function formatAnswer(answer: unknown): string {
  if (answer === undefined || answer === null) return "Keine Antwort";
  if (Array.isArray(answer)) return answer.join(", ");
  if (typeof answer === "object") return JSON.stringify(answer);
  return String(answer);
}

function normalizeAttemptResultResponse(payload: AttemptResultsV2Response): AttemptResultData {
  return {
    mockExam: normalizeMockExamFromApi(payload.mock_exam || {}),
    gradingResult: normalizeGradingResultPayload(payload.grading_result),
    taskResponses: normalizeTaskResponsesPayload(payload.task_responses),
  };
}

function normalizeMockExamFromApi(apiMock: Record<string, any>): MockExam {
  const mockExamId =
    apiMock.id ?? apiMock.mock_exam_id ?? `mock-${globalThis.crypto?.randomUUID?.() ?? Date.now()}`;
  const rawTasks = Array.isArray(apiMock.tasks) ? apiMock.tasks : [];
  const tasks: Task[] = rawTasks.map((task: Record<string, any>, index: number) =>
    normalizeTaskFromApi(task, mockExamId, index)
  );
  const totalPoints =
    apiMock.total_points ??
    apiMock.totalPoints ??
    tasks.reduce((sum, task) => sum + (task.points || 0), 0);

  return {
    id: mockExamId,
    subjectId: apiMock.subject_id ?? apiMock.subjectId ?? "wbl",
    themaIds: apiMock.thema_ids ?? apiMock.themaIds ?? [],
    generatedAt: apiMock.generated_at ?? apiMock.generatedAt ?? new Date().toISOString(),
    studyContentUsed: apiMock.study_content_used ?? apiMock.studyContentUsed,
    teacherPatternUsed: apiMock.teacher_pattern_used ?? apiMock.teacherPatternUsed,
    tasks,
    totalPoints,
    estimatedDurationMinutes: apiMock.estimated_duration_minutes ?? apiMock.estimatedDurationMinutes ?? 90,
    difficultyLevel: apiMock.difficulty_level ?? apiMock.difficultyLevel ?? 3,
    title: apiMock.title ?? "Übungsklausur",
    description: apiMock.description,
    status: apiMock.status ?? "ready",
  };
}

function normalizeTaskFromApi(task: Record<string, any>, mockExamId: string, index: number): Task {
  const points = task.points ?? task.pointsValue ?? 5;
  return {
    id: task.id ?? `task-${index + 1}`,
    mockExamId,
    type: task.type ?? "ShortAnswer",
    taskNumber: task.task_number ?? task.taskNumber ?? index + 1,
    questionText: task.question_text ?? task.questionText ?? "",
    questionImage: task.question_image ?? task.questionImage,
    questionImageAlt: task.question_image_alt ?? task.questionImageAlt,
    options: task.options,
    matchingPairs: task.matching_pairs ?? task.matchingPairs,
    fillInBlanks: task.fill_in_blanks ?? task.fillInBlanks,
    diagramData: task.diagram_data ?? task.diagramData,
    calculationData: task.calculation_data ?? task.calculationData,
    difficulty: task.difficulty ?? 3,
    points,
    timeEstimateMinutes: task.time_estimate_minutes ?? task.timeEstimateMinutes ?? 5,
    correctAnswer: task.correct_answer ?? task.correctAnswer ?? "",
    modelAnswer: task.model_answer ?? task.modelAnswer,
    gradingRubric: normalizeRubricFromApi(task.grading_rubric ?? task.gradingRubric, points),
    rationale: task.rationale,
    source: task.source ?? "ai_generated",
    hints: task.hints ?? [],
    relatedThemas: task.related_themas ?? task.relatedThemas,
  };
}

function normalizeRubricFromApi(
  rubric: Record<string, any> | undefined,
  fallbackPoints: number
): Task["gradingRubric"] {
  if (!rubric || typeof rubric !== "object") {
    return {
      maxPoints: fallbackPoints ?? 0,
      criteria: [],
      autoGradable: false,
      partialCreditAllowed: true,
    };
  }

  const criteria = Array.isArray(rubric.criteria)
    ? rubric.criteria.map((criterion: Record<string, any>, index: number) => ({
        name: criterion.name ?? criterion.criterion ?? `Kriterium ${index + 1}`,
        description: criterion.description ?? "",
        maxPoints: criterion.max_points ?? criterion.maxPoints ?? 0,
        keywords: criterion.keywords,
      }))
    : [];

  return {
    maxPoints: rubric.max_points ?? rubric.maxPoints ?? fallbackPoints ?? 0,
    criteria,
    autoGradable: rubric.auto_gradable ?? rubric.autoGradable ?? false,
    partialCreditAllowed: rubric.partial_credit_allowed ?? rubric.partialCreditAllowed ?? true,
  };
}

function normalizeGradingResultPayload(grading: GradingResultV2): NormalizedGradingResult {
  const taskGrades = Array.isArray(grading.task_grades)
    ? grading.task_grades.map(normalizeTaskGradePayload)
    : [];
  return {
    totalScore: grading.total_score,
    totalPoints: grading.total_points,
    percentage: grading.percentage,
    grade: grading.grade,
    gradeText: grading.grade_text,
    overallFeedback: grading.overall_feedback,
    manualReviewFlagged: grading.manual_review_flagged,
    graderConfidence: grading.grader_confidence,
    tasksNeedingReview: grading.tasks_needing_review ?? [],
    taskGrades,
  };
}

function normalizeTaskGradePayload(grade: TaskGradeV2): TaskGrade {
  const isMultipleChoice = grade.task_type?.startsWith("MC");
  return {
    taskId: grade.task_id,
    earnedPoints: grade.earned_points,
    maxPoints: grade.max_points,
    autoGraded: !!isMultipleChoice,
    confidence: grade.confidence,
    feedback: grade.rationale,
    isCorrect: isMultipleChoice ? grade.earned_points === grade.max_points : undefined,
    criteriaBreakdown: undefined,
    suggestedReview: grade.confidence < LOW_CONFIDENCE_THRESHOLD,
    reviewReason: undefined,
    improvementSuggestion: grade.improvement_suggestion,
    rubricBreakdown: grade.rubric_breakdown,
  };
}

function normalizeTaskResponsesPayload(
  responses: AttemptResultsV2Response["task_responses"]
): Record<string, NormalizedTaskResponse> {
  const map: Record<string, NormalizedTaskResponse> = {};
  if (!Array.isArray(responses)) {
    return map;
  }

  responses.forEach((response) => {
    if (!response?.task_id) return;
    map[response.task_id] = {
      taskId: response.task_id,
      userAnswer: response.user_answer,
    };
  });

  return map;
}

function mapAttemptResponses(responses: TaskResponse[]): Record<string, TaskResponse> {
  return responses.reduce<Record<string, TaskResponse>>((acc, response) => {
    acc[response.taskId] = response;
    return acc;
  }, {});
}

function buildGradeMap(taskGrades?: TaskGrade[], responses?: TaskResponse[]): Record<string, TaskGrade> {
  if (taskGrades && taskGrades.length > 0) {
    return taskGrades.reduce<Record<string, TaskGrade>>((acc, grade) => {
      acc[grade.taskId] = grade;
      return acc;
    }, {});
  }

  if (!responses) {
    return {};
  }

  return responses.reduce<Record<string, TaskGrade>>((acc, response) => {
    acc[response.taskId] = {
      taskId: response.taskId,
      earnedPoints: response.earnedPoints,
      maxPoints: response.maxPoints,
      autoGraded: response.autoGraded,
      confidence: response.confidence,
      feedback: response.feedback ?? "",
      isCorrect: response.isCorrect,
      criteriaBreakdown: response.criteriaScores?.map((criterion) => ({
        name: criterion.criterionName,
        score: criterion.score,
        max: criterion.maxScore,
        feedback: criterion.feedback ?? "",
      })),
      suggestedReview: response.flaggedForReview,
      improvementSuggestion: response.improvementSuggestion,
      rubricBreakdown: response.rubricBreakdown,
    };
    return acc;
  }, {});
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 90) return "bg-green-500";
  if (confidence >= LOW_CONFIDENCE_THRESHOLD) return "bg-amber-500";
  return "bg-red-500";
}

export default AttemptHistoryView;
