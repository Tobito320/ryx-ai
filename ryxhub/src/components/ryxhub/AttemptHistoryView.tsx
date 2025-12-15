/**
 * Attempt History View
 * 
 * Shows past attempts with scores, grades, and detailed feedback
 */

import { useState } from "react";
import { useExam } from "@/context/ExamContext";
import {
  History,
  ChevronLeft,
  ChevronRight,
  Clock,
  Target,
  Award,
  TrendingUp,
  TrendingDown,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Calendar,
  BarChart3,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Attempt, MockExam, GradeText } from "@/types/exam";

interface AttemptHistoryViewProps {
  onBack: () => void;
}

export function AttemptHistoryView({ onBack }: AttemptHistoryViewProps) {
  const { attempts, mockExams, selectedThema } = useExam();
  const [selectedAttemptId, setSelectedAttemptId] = useState<string | null>(null);

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
              <AttemptDetail attempt={selectedAttempt} mockExam={selectedMockExam} />
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
}: {
  attempt: Attempt;
  mockExam: MockExam;
}) {
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold">{mockExam.title}</h2>
          <p className="text-muted-foreground">
            {formatDate(attempt.startedAt)} • {formatDuration(attempt.durationSeconds)}
          </p>
        </div>
        <div className="text-right">
          <div className="text-4xl font-bold">{attempt.grade.toFixed(1)}</div>
          <div className={cn("text-lg font-medium", getGradeColor(attempt.grade))}>
            {attempt.gradeText}
          </div>
        </div>
      </div>

      {/* Score Overview */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <Target className="h-8 w-8 mx-auto mb-2 text-primary" />
            <div className="text-2xl font-bold">
              {attempt.totalScore}/{attempt.totalPoints}
            </div>
            <div className="text-sm text-muted-foreground">Punkte</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Award className="h-8 w-8 mx-auto mb-2 text-amber-500" />
            <div className="text-2xl font-bold">{Math.round(attempt.percentage)}%</div>
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

      {/* Tabs */}
      <Tabs defaultValue="feedback">
        <TabsList>
          <TabsTrigger value="feedback">Feedback</TabsTrigger>
          <TabsTrigger value="breakdown">Aufschlüsselung</TabsTrigger>
          <TabsTrigger value="answers">Antworten</TabsTrigger>
        </TabsList>

        <TabsContent value="feedback" className="mt-4 space-y-4">
          {/* AI Feedback */}
          {attempt.overallFeedback && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Gesamtfeedback</CardTitle>
              </CardHeader>
              <CardContent>
                <p>{attempt.overallFeedback}</p>
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
          {attempt.flagsForReview.length > 0 && (
            <Card className="border-amber-500/50 bg-amber-500/5">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-amber-500" />
                  Zur Überprüfung markiert
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {attempt.flagsForReview.length} Aufgabe(n) wurden für manuelle Überprüfung
                  markiert.
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

        <TabsContent value="answers" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Antworten im Detail</CardTitle>
              <CardDescription>
                Überprüfe deine Antworten und vergleiche mit den Musterlösungen
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">#</TableHead>
                    <TableHead>Typ</TableHead>
                    <TableHead className="text-center">Punkte</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockExam.tasks.map((task, index) => {
                    const response = attempt.taskResponses.find(
                      (r) => r.taskId === task.id
                    );
                    const isCorrect = response?.isCorrect ?? response?.earnedPoints === task.points;

                    return (
                      <TableRow key={task.id}>
                        <TableCell className="font-medium">{index + 1}</TableCell>
                        <TableCell>{getTaskTypeLabel(task.type)}</TableCell>
                        <TableCell className="text-center">
                          {response?.earnedPoints ?? 0}/{task.points}
                        </TableCell>
                        <TableCell className="text-center">
                          {isCorrect ? (
                            <CheckCircle2 className="h-5 w-5 text-green-500 mx-auto" />
                          ) : (
                            <XCircle className="h-5 w-5 text-red-500 mx-auto" />
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
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

export default AttemptHistoryView;
