/**
 * School View Component
 * 
 * Main dashboard for the exam preparation system
 * Navigation: Schools → Subjects → Themas → Actions
 */

import { useState } from "react";
import { useExam } from "@/context/ExamContext";
import {
  GraduationCap,
  BookOpen,
  Upload,
  FileQuestion,
  History,
  TrendingUp,
  ChevronRight,
  Plus,
  Search,
  Filter,
  School,
  User,
  Calendar,
  Target,
  Award,
  Clock,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TestUploadDialog } from "./TestUploadDialog";
import { MockExamGenerator } from "./MockExamGenerator";
import { ExamTakingView } from "./ExamTakingView";
import { AttemptHistoryView } from "./AttemptHistoryView";
import type { Subject, Thema, MockExam, Attempt } from "@/types/exam";

export function SchoolView() {
  const {
    schools,
    selectedSchool,
    selectedSubject,
    selectedThema,
    selectSchool,
    selectSubject,
    selectThema,
    teachers,
    classTests,
    mockExams,
    attempts,
    examView,
    setExamView,
    statistics,
    refreshStatistics,
  } = useExam();

  const [searchQuery, setSearchQuery] = useState("");
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [generatorOpen, setGeneratorOpen] = useState(false);

  // Filter mock exams for selected subject/thema
  const filteredMockExams = mockExams.filter(exam => {
    if (selectedThema) return exam.themaIds.includes(selectedThema.id);
    if (selectedSubject) return exam.subjectId === selectedSubject.id;
    return true;
  });

  // Get attempts for selected exam
  const selectedExamAttempts = selectedThema
    ? attempts.filter(a => {
        const exam = mockExams.find(m => m.id === a.mockExamId);
        return exam?.themaIds.includes(selectedThema.id);
      })
    : [];

  // Get statistics for display
  const subjectStats = selectedSubject
    ? {
        testsUploaded: classTests.filter(t => t.subjectId === selectedSubject.id).length,
        mocksCreated: mockExams.filter(m => m.subjectId === selectedSubject.id).length,
        attempts: attempts.filter(a => {
          const exam = mockExams.find(m => m.id === a.mockExamId);
          return exam?.subjectId === selectedSubject.id;
        }).length,
        avgGrade: 2.5, // TODO: Calculate from attempts
      }
    : null;

  // Show exam taking view if in exam mode
  if (examView === "exam_taking") {
    return <ExamTakingView />;
  }

  // Show history view
  if (examView === "history") {
    return <AttemptHistoryView onBack={() => setExamView("themas")} />;
  }

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="border-b border-border p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <GraduationCap className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-semibold">Schule & Prüfungen</h1>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setUploadDialogOpen(true)}>
              <Upload className="h-4 w-4 mr-2" />
              Test hochladen
            </Button>
            <Button size="sm" onClick={() => setGeneratorOpen(true)} disabled={!selectedSubject}>
              <Plus className="h-4 w-4 mr-2" />
              Übungsklausur erstellen
            </Button>
          </div>
        </div>

        {/* Breadcrumb Navigation */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <button
            onClick={() => {
              selectSubject("");
              selectThema("");
            }}
            className={cn(
              "hover:text-foreground transition-colors",
              !selectedSubject && "text-foreground font-medium"
            )}
          >
            {selectedSchool?.name || "Schule wählen"}
          </button>
          {selectedSubject && (
            <>
              <ChevronRight className="h-4 w-4" />
              <button
                onClick={() => selectThema("")}
                className={cn(
                  "hover:text-foreground transition-colors",
                  !selectedThema && "text-foreground font-medium"
                )}
              >
                {selectedSubject.name}
              </button>
            </>
          )}
          {selectedThema && (
            <>
              <ChevronRight className="h-4 w-4" />
              <span className="text-foreground font-medium">{selectedThema.name}</span>
            </>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="p-4 space-y-6">
            {/* Stats Overview */}
            {selectedSubject && subjectStats && (
              <div className="grid grid-cols-4 gap-4">
                <StatsCard
                  title="Tests hochgeladen"
                  value={subjectStats.testsUploaded}
                  icon={<Upload className="h-4 w-4" />}
                  description="Klassenarbeiten"
                />
                <StatsCard
                  title="Übungsklausuren"
                  value={subjectStats.mocksCreated}
                  icon={<FileQuestion className="h-4 w-4" />}
                  description="Erstellt"
                />
                <StatsCard
                  title="Versuche"
                  value={subjectStats.attempts}
                  icon={<Target className="h-4 w-4" />}
                  description="Gesamt"
                />
                <StatsCard
                  title="Durchschnitt"
                  value={subjectStats.avgGrade.toFixed(1)}
                  icon={<Award className="h-4 w-4" />}
                  description="Note"
                  highlight
                />
              </div>
            )}

            {/* Subject/Thema Selection */}
            {!selectedSubject ? (
              <SubjectGrid
                subjects={selectedSchool?.subjects || []}
                onSelect={selectSubject}
                classTests={classTests}
                mockExams={mockExams}
                attempts={attempts}
              />
            ) : !selectedThema ? (
              <ThemaGrid
                subject={selectedSubject}
                onSelect={selectThema}
                mockExams={mockExams}
                attempts={attempts}
              />
            ) : (
              <ThemaDetail
                thema={selectedThema}
                mockExams={filteredMockExams}
                attempts={selectedExamAttempts}
                onGenerateExam={() => setGeneratorOpen(true)}
                onViewHistory={() => setExamView("history")}
                onStartExam={(examId) => {
                  // Start attempt logic
                }}
              />
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Dialogs */}
      <TestUploadDialog
        open={uploadDialogOpen}
        onOpenChange={setUploadDialogOpen}
      />
      <MockExamGenerator
        open={generatorOpen}
        onOpenChange={setGeneratorOpen}
        subjectId={selectedSubject?.id}
        themaId={selectedThema?.id}
      />
    </div>
  );
}

// ============================================================================
// Sub-Components
// ============================================================================

function StatsCard({
  title,
  value,
  icon,
  description,
  highlight = false,
}: {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  description: string;
  highlight?: boolean;
}) {
  return (
    <Card className={cn(highlight && "border-primary/50 bg-primary/5")}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="text-muted-foreground">{icon}</div>
          <Badge variant="secondary">{description}</Badge>
        </div>
        <div className="mt-2">
          <div className="text-2xl font-bold">{value}</div>
          <div className="text-sm text-muted-foreground">{title}</div>
        </div>
      </CardContent>
    </Card>
  );
}

function SubjectGrid({
  subjects,
  onSelect,
  classTests,
  mockExams,
  attempts,
}: {
  subjects: Subject[];
  onSelect: (id: string) => void;
  classTests: any[];
  mockExams: any[];
  attempts: any[];
}) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Fächer</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {subjects.map((subject) => {
          const testsCount = classTests.filter(t => t.subjectId === subject.id).length;
          const examsCount = mockExams.filter(m => m.subjectId === subject.id).length;
          
          return (
            <Card
              key={subject.id}
              className="cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => onSelect(subject.id)}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-primary" />
                  <CardTitle className="text-base">{subject.name}</CardTitle>
                </div>
                {subject.fullName && (
                  <CardDescription className="text-xs">{subject.fullName}</CardDescription>
                )}
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span>{testsCount} Tests</span>
                  <span>{examsCount} Klausuren</span>
                </div>
              </CardContent>
            </Card>
          );
        })}

        {/* Add Subject Card */}
        <Card className="cursor-pointer hover:border-primary/50 transition-colors border-dashed">
          <CardContent className="flex items-center justify-center h-full min-h-[100px]">
            <div className="text-center text-muted-foreground">
              <Plus className="h-8 w-8 mx-auto mb-2" />
              <span className="text-sm">Fach hinzufügen</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function ThemaGrid({
  subject,
  onSelect,
  mockExams,
  attempts,
}: {
  subject: Subject;
  onSelect: (id: string) => void;
  mockExams: any[];
  attempts: any[];
}) {
  // Default themas for WBL
  const defaultThemas: Thema[] = [
    { id: "marktforschung", subjectId: "wbl", name: "Marktforschung", subtopics: [], extractedFromTests: [], frequency: 0, createdAt: "", updatedAt: "" },
    { id: "marketingmix", subjectId: "wbl", name: "Marketingmix (4Ps)", subtopics: [], extractedFromTests: [], frequency: 0, createdAt: "", updatedAt: "" },
    { id: "kundenakquisition", subjectId: "wbl", name: "Kundenakquisition", subtopics: [], extractedFromTests: [], frequency: 0, createdAt: "", updatedAt: "" },
    { id: "preismanagement", subjectId: "wbl", name: "Preismanagement", subtopics: [], extractedFromTests: [], frequency: 0, createdAt: "", updatedAt: "" },
    { id: "werbung", subjectId: "wbl", name: "Werbung & Kommunikation", subtopics: [], extractedFromTests: [], frequency: 0, createdAt: "", updatedAt: "" },
  ];

  const themas = subject.themas.length > 0 ? subject.themas : defaultThemas;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Themen in {subject.name}</h2>
        <Button variant="outline" size="sm">
          <Plus className="h-4 w-4 mr-2" />
          Thema hinzufügen
        </Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {themas.map((thema) => {
          const examsCount = mockExams.filter(m => m.themaIds.includes(thema.id)).length;
          
          return (
            <Card
              key={thema.id}
              className="cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => onSelect(thema.id)}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Target className="h-4 w-4 text-primary" />
                  {thema.name}
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span>{examsCount} Klausuren</span>
                  <span>{thema.frequency} Tests</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function ThemaDetail({
  thema,
  mockExams,
  attempts,
  onGenerateExam,
  onViewHistory,
  onStartExam,
}: {
  thema: Thema;
  mockExams: MockExam[];
  attempts: Attempt[];
  onGenerateExam: () => void;
  onViewHistory: () => void;
  onStartExam: (examId: string) => void;
}) {
  const { startAttempt, setExamView, selectMockExam } = useExam();

  const handleStartExam = async (examId: string) => {
    const attempt = await startAttempt(examId);
    if (attempt) {
      selectMockExam(examId);
      setExamView("exam_taking");
    }
  };

  return (
    <div className="space-y-6">
      {/* Thema Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">{thema.name}</h2>
          <p className="text-muted-foreground">
            {mockExams.length} Übungsklausuren verfügbar
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={onViewHistory}>
            <History className="h-4 w-4 mr-2" />
            Verlauf
          </Button>
          <Button onClick={onGenerateExam}>
            <Plus className="h-4 w-4 mr-2" />
            Neue Klausur
          </Button>
        </div>
      </div>

      {/* Mock Exams List */}
      <Tabs defaultValue="exams" className="w-full">
        <TabsList>
          <TabsTrigger value="exams">Übungsklausuren</TabsTrigger>
          <TabsTrigger value="study">Lernmaterial</TabsTrigger>
          <TabsTrigger value="stats">Statistik</TabsTrigger>
        </TabsList>

        <TabsContent value="exams" className="mt-4 space-y-4">
          {mockExams.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-8">
                <FileQuestion className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-4">
                  Noch keine Übungsklausuren für dieses Thema
                </p>
                <Button onClick={onGenerateExam}>
                  <Plus className="h-4 w-4 mr-2" />
                  Erste Klausur erstellen
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {mockExams.map((exam) => {
                const examAttempts = attempts.filter(a => a.mockExamId === exam.id);
                const bestAttempt = examAttempts.sort((a, b) => b.percentage - a.percentage)[0];

                return (
                  <Card key={exam.id} className="hover:border-primary/50 transition-colors">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <h3 className="font-medium">{exam.title}</h3>
                          <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <FileQuestion className="h-3 w-3" />
                              {exam.tasks.length} Aufgaben
                            </span>
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {exam.estimatedDurationMinutes} Min.
                            </span>
                            <span className="flex items-center gap-1">
                              <Target className="h-3 w-3" />
                              {exam.totalPoints} Punkte
                            </span>
                            <Badge variant="outline">
                              Schwierigkeit {exam.difficultyLevel}/5
                            </Badge>
                          </div>
                        </div>

                        <div className="flex items-center gap-4">
                          {bestAttempt && (
                            <div className="text-right">
                              <div className="text-sm text-muted-foreground">Beste Note</div>
                              <div className="font-bold text-lg">
                                {bestAttempt.grade.toFixed(1)}
                              </div>
                            </div>
                          )}
                          <Button onClick={() => handleStartExam(exam.id)}>
                            {examAttempts.length > 0 ? "Wiederholen" : "Starten"}
                          </Button>
                        </div>
                      </div>

                      {examAttempts.length > 0 && (
                        <div className="mt-3 pt-3 border-t">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">
                              {examAttempts.length} Versuche
                            </span>
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground">Fortschritt:</span>
                              <Progress
                                value={bestAttempt?.percentage || 0}
                                className="w-24 h-2"
                              />
                              <span>{Math.round(bestAttempt?.percentage || 0)}%</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>

        <TabsContent value="study" className="mt-4">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-4 mb-4">
                <BookOpen className="h-8 w-8 text-primary" />
                <div>
                  <h3 className="font-semibold">Lernmaterial für {thema.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    KI-generiertes Studienmaterial basierend auf IHK-Standards
                  </p>
                </div>
              </div>
              <Button variant="outline">
                Lernmaterial laden
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="stats" className="mt-4">
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Leistungsverlauf</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-32 flex items-center justify-center text-muted-foreground">
                  Chart wird hier angezeigt
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Aufgabentypen</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span>Multiple Choice</span>
                    <span className="font-medium">85%</span>
                  </div>
                  <Progress value={85} className="h-2" />
                  <div className="flex items-center justify-between text-sm">
                    <span>Fallstudien</span>
                    <span className="font-medium">68%</span>
                  </div>
                  <Progress value={68} className="h-2" />
                  <div className="flex items-center justify-between text-sm">
                    <span>Berechnungen</span>
                    <span className="font-medium">72%</span>
                  </div>
                  <Progress value={72} className="h-2" />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default SchoolView;
