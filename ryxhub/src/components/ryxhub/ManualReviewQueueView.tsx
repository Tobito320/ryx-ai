import { useEffect, useMemo, useState } from "react";
import { useExam } from "@/context/ExamContext";
import { getManualReviewQueueV2, overrideManualReviewV2, type ManualReviewQueueItemV2 } from "@/services/examService";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ArrowLeft, RefreshCw, AlertCircle } from "lucide-react";

function formatAnswer(answer: unknown): string {
  if (answer == null) return "";
  if (typeof answer === "string") return answer;
  try {
    return JSON.stringify(answer, null, 2);
  } catch {
    return String(answer);
  }
}

export function ManualReviewQueueView() {
  const { setExamView } = useExam();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<ManualReviewQueueItemV2[]>([]);
  const [selectedAttemptId, setSelectedAttemptId] = useState<string | null>(null);

  const [editPoints, setEditPoints] = useState<Record<string, string>>({});
  const [editRationale, setEditRationale] = useState<Record<string, string>>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getManualReviewQueueV2();
      setItems(data);
      if (!selectedAttemptId && data.length > 0) {
        setSelectedAttemptId(data[0].attempt_id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Konnte Review-Queue nicht laden");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selected = useMemo(() => items.find((i) => i.attempt_id === selectedAttemptId) || null, [items, selectedAttemptId]);

  const selectedTaskGrades = useMemo(() => {
    const grades = (selected?.grading_result?.task_grades as any[]) || [];
    const tasksNeedingReview = (selected?.grading_result?.tasks_needing_review as string[]) || [];
    return grades.filter((g) => tasksNeedingReview.includes(g.task_id));
  }, [selected]);

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="border-b border-border p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setExamView("themas")}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Zurück
            </Button>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-semibold">Manuelle Prüfung</h2>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={refresh} disabled={loading}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Aktualisieren
          </Button>
        </div>
        {error && <p className="text-sm text-destructive mt-2">{error}</p>}
      </div>

      <div className="flex-1 overflow-hidden grid grid-cols-3 gap-4 p-4">
        <Card className="col-span-1 overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Queue</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[calc(100vh-240px)]">
              <div className="p-3 space-y-2">
                {items.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    Keine Aufgaben zur manuellen Prüfung.
                  </p>
                )}
                {items.map((item) => {
                  const tasksNeedingReview = (item.grading_result?.tasks_needing_review as string[]) || [];
                  const isSelected = item.attempt_id === selectedAttemptId;
                  return (
                    <button
                      key={item.attempt_id}
                      className={`w-full text-left border rounded-md p-3 transition-colors ${isSelected ? "border-primary bg-primary/5" : "hover:bg-muted"}`}
                      onClick={() => setSelectedAttemptId(item.attempt_id)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="font-medium truncate">{item.attempt_id}</div>
                        <Badge variant={tasksNeedingReview.length > 0 ? "destructive" : "secondary"}>
                          {tasksNeedingReview.length}
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        Note: {item.grading_result?.grade_text ?? "-"} ({item.grading_result?.percentage ?? "-"}%)
                      </div>
                    </button>
                  );
                })}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="col-span-2 overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Details</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[calc(100vh-240px)]">
              <div className="p-4 space-y-4">
                {!selected && (
                  <p className="text-sm text-muted-foreground">Wähle links einen Versuch aus.</p>
                )}

                {selected && selectedTaskGrades.length === 0 && (
                  <p className="text-sm text-muted-foreground">Dieser Versuch hat keine offenen Review-Aufgaben.</p>
                )}

                {selected && selectedTaskGrades.map((tg) => {
                  const task = (selected.mock_exam?.tasks as any[])?.find((t) => t.id === tg.task_id);
                  const response = (selected.task_responses || []).find((r) => r.task_id === tg.task_id);
                  const key = `${selected.attempt_id}:${tg.task_id}`;
                  const currentPoints = editPoints[key] ?? String(tg.earned_points ?? "0");
                  const currentRationale = editRationale[key] ?? String(tg.rationale ?? "");

                  return (
                    <Card key={tg.task_id}>
                      <CardHeader className="pb-2">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <CardTitle className="text-sm">Aufgabe {task?.task_number ?? ""}</CardTitle>
                            <p className="text-sm text-muted-foreground line-clamp-2 mt-1">{task?.question_text ?? ""}</p>
                          </div>
                          <Badge variant="outline">{tg.task_type}</Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="space-y-1">
                          <p className="text-xs font-semibold">Schüler-Antwort</p>
                          <pre className="text-xs bg-muted rounded-md p-3 overflow-auto whitespace-pre-wrap">{formatAnswer(response?.user_answer)}</pre>
                        </div>

                        <div className="space-y-1">
                          <p className="text-xs font-semibold">AI Begründung</p>
                          <p className="text-sm text-muted-foreground whitespace-pre-wrap">{tg.rationale}</p>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div className="space-y-1">
                            <p className="text-xs font-semibold">Punkte (neu)</p>
                            <Input
                              value={currentPoints}
                              onChange={(e) => setEditPoints((prev) => ({ ...prev, [key]: e.target.value }))}
                              inputMode="decimal"
                            />
                            <p className="text-xs text-muted-foreground">Max: {tg.max_points}</p>
                          </div>
                          <div className="space-y-1">
                            <p className="text-xs font-semibold">Begründung (optional)</p>
                            <Textarea
                              value={currentRationale}
                              onChange={(e) => setEditRationale((prev) => ({ ...prev, [key]: e.target.value }))}
                              className="min-h-[72px]"
                            />
                          </div>
                        </div>

                        <div className="flex justify-end">
                          <Button
                            onClick={async () => {
                              setSavingKey(key);
                              try {
                                const earned = Number(currentPoints);
                                await overrideManualReviewV2({
                                  attempt_id: selected.attempt_id,
                                  task_id: tg.task_id,
                                  earned_points: Number.isFinite(earned) ? earned : 0,
                                  rationale: currentRationale.trim() || undefined,
                                  confidence: 100,
                                });
                                await refresh();
                              } catch (e) {
                                setError(e instanceof Error ? e.message : "Override fehlgeschlagen");
                              } finally {
                                setSavingKey(null);
                              }
                            }}
                            disabled={savingKey === key}
                          >
                            {savingKey === key ? "Speichere..." : "Override speichern"}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
