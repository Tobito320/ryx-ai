/**
 * Mock Exam Generator
 * 
 * AI-powered exam generation with teacher pattern support
 * FIX 3: Added free_prompt and context_texts support
 */

import { useState } from "react";
import { useExam } from "@/context/ExamContext";
import {
  Wand2,
  Settings,
  Clock,
  Target,
  BookOpen,
  Loader2,
  Check,
  AlertTriangle,
  FileText,
  MessageSquare,
  X,
  Upload,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface MockExamGeneratorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subjectId?: string;
  themaId?: string;
}

export function MockExamGenerator({
  open,
  onOpenChange,
  subjectId,
  themaId,
}: MockExamGeneratorProps) {
  const { generateMockExam, teachers, loading, selectedSubject, schools } = useExam();

  const [selectedThemas, setSelectedThemas] = useState<string[]>(themaId ? [themaId] : []);
  const [selectedTeacher, setSelectedTeacher] = useState<string>("");
  const [difficultyLevel, setDifficultyLevel] = useState(3);
  const [taskCount, setTaskCount] = useState(15);
  const [durationMinutes, setDurationMinutes] = useState(90);
  const [useTeacherPattern, setUseTeacherPattern] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);
  
  // NEW: Free prompt and context
  const [freePrompt, setFreePrompt] = useState("");
  const [contextTexts, setContextTexts] = useState<string[]>([]);
  const [currentContext, setCurrentContext] = useState("");
  const [includeDiagrams, setIncludeDiagrams] = useState(true);

  // Get available themas for the subject
  const availableThemas = [
    { id: "marktforschung", name: "Marktforschung" },
    { id: "marketingmix", name: "Marketingmix (4Ps)" },
    { id: "kundenakquisition", name: "Kundenakquisition" },
    { id: "preismanagement", name: "Preismanagement" },
    { id: "werbung", name: "Werbung & Kommunikation" },
    { id: "it-service", name: "IT Service Management" },
    { id: "incident-management", name: "Incident Management" },
    { id: "sla", name: "Service Level Agreements" },
    { id: "netzwerke", name: "Netzwerktechnik" },
  ];

  // Get teachers for the subject
  const subjectTeachers = teachers.filter((t) =>
    t.subjectIds.includes(subjectId || "")
  );

  const handleGenerate = async () => {
    setGenerating(true);
    
    try {
      await generateMockExam(subjectId || "wbl", selectedThemas.length > 0 ? selectedThemas : ["marktforschung"], {
        teacherId: useTeacherPattern ? selectedTeacher : undefined,
        difficultyLevel,
        taskCount,
        durationMinutes,
        freePrompt: freePrompt.trim() || undefined,
        contextTexts: contextTexts.length > 0 ? contextTexts : undefined,
        includeDiagrams,
      });
      setGenerated(true);
    } catch (error) {
      console.error("Failed to generate exam:", error);
    } finally {
      setGenerating(false);
    }
  };

  const handleClose = () => {
    setGenerated(false);
    setFreePrompt("");
    setContextTexts([]);
    setCurrentContext("");
    onOpenChange(false);
  };

  const addContextText = () => {
    if (currentContext.trim()) {
      setContextTexts((prev) => [...prev, currentContext.trim()]);
      setCurrentContext("");
    }
  };

  const removeContextText = (index: number) => {
    setContextTexts((prev) => prev.filter((_, i) => i !== index));
  };

  const toggleThema = (themaId: string) => {
    setSelectedThemas((prev) =>
      prev.includes(themaId)
        ? prev.filter((id) => id !== themaId)
        : [...prev, themaId]
    );
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Wand2 className="h-5 w-5 text-primary" />
            Übungsklausur erstellen
          </DialogTitle>
          <DialogDescription>
            Erstelle eine KI-generierte Übungsklausur basierend auf IHK-Standards
          </DialogDescription>
        </DialogHeader>

        {!generated ? (
          <Tabs defaultValue="basic" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="basic">Grundeinstellungen</TabsTrigger>
              <TabsTrigger value="prompt">Eigene Anweisungen</TabsTrigger>
              <TabsTrigger value="context">Kontext-Material</TabsTrigger>
            </TabsList>
            
            <TabsContent value="basic" className="space-y-6 py-4">
              {/* Thema Selection */}
              <div className="space-y-3">
                <Label>Themen auswählen</Label>
                <div className="flex flex-wrap gap-2">
                  {availableThemas.map((thema) => (
                    <Badge
                      key={thema.id}
                      variant={selectedThemas.includes(thema.id) ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => toggleThema(thema.id)}
                    >
                      {thema.name}
                      {selectedThemas.includes(thema.id) && (
                        <Check className="h-3 w-3 ml-1" />
                      )}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Teacher Pattern */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Lehrer-Muster verwenden</Label>
                  <Switch
                    checked={useTeacherPattern}
                    onCheckedChange={setUseTeacherPattern}
                  />
                </div>
                {useTeacherPattern && (
                  <Select value={selectedTeacher} onValueChange={setSelectedTeacher}>
                    <SelectTrigger>
                      <SelectValue placeholder="Lehrer auswählen (optional)" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="generic">Standard IHK-Stil</SelectItem>
                      {subjectTeachers.map((teacher) => (
                        <SelectItem key={teacher.id} value={teacher.id}>
                          {teacher.name}
                          {teacher.testsCount >= 3 && (
                            <span className="text-muted-foreground ml-2">
                              ({teacher.testsCount} Tests)
                            </span>
                          )}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
                {useTeacherPattern && subjectTeachers.length === 0 && (
                  <p className="text-sm text-muted-foreground flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    Lade mindestens 3 Tests hoch, um das Muster deines Lehrers zu lernen.
                  </p>
                )}
              </div>

              {/* Settings Grid */}
              <div className="grid grid-cols-2 gap-4">
                {/* Difficulty */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>Schwierigkeit</Label>
                    <span className="text-sm text-muted-foreground">
                      {difficultyLevel}/5
                    </span>
                  </div>
                  <Slider
                    value={[difficultyLevel]}
                    onValueChange={([value]) => setDifficultyLevel(value)}
                    min={1}
                    max={5}
                    step={1}
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>Leicht</span>
                    <span>Schwer</span>
                  </div>
                </div>

                {/* Task Count */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>Aufgaben</Label>
                    <span className="text-sm text-muted-foreground">{taskCount}</span>
                  </div>
                  <Slider
                    value={[taskCount]}
                    onValueChange={([value]) => setTaskCount(value)}
                    min={5}
                    max={30}
                    step={5}
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>5</span>
                    <span>30</span>
                  </div>
                </div>

                {/* Duration */}
                <div className="space-y-3 col-span-2">
                  <div className="flex items-center justify-between">
                    <Label>Bearbeitungszeit</Label>
                    <span className="text-sm text-muted-foreground">
                      {durationMinutes} Minuten
                    </span>
                  </div>
                  <Slider
                    value={[durationMinutes]}
                    onValueChange={([value]) => setDurationMinutes(value)}
                    min={30}
                    max={180}
                    step={15}
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>30 Min.</span>
                    <span>3 Std.</span>
                  </div>
                </div>
              </div>

              {/* Include Diagrams */}
              <div className="flex items-center justify-between">
                <Label>Diagramm-Aufgaben einschließen</Label>
                <Switch
                  checked={includeDiagrams}
                  onCheckedChange={setIncludeDiagrams}
                />
              </div>
            </TabsContent>

            <TabsContent value="prompt" className="space-y-4 py-4">
              <div className="space-y-3">
                <Label className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Eigene Anweisungen für die KI
                </Label>
                <Textarea
                  placeholder="Beispiel: Fokussiere dich auf Primärforschung mit mindestens 3 Fallstudien. Füge eine Berechnungsaufgabe zur Marktanteilsberechnung hinzu."
                  value={freePrompt}
                  onChange={(e) => setFreePrompt(e.target.value)}
                  className="min-h-[150px]"
                />
                <p className="text-sm text-muted-foreground">
                  Gib der KI spezielle Anweisungen für die Klausur-Erstellung. 
                  Du kannst bestimmte Aufgabentypen, Schwerpunkte oder Formate wünschen.
                </p>
              </div>

              {/* Prompt Examples */}
              <div className="space-y-2">
                <Label className="text-sm text-muted-foreground">Beispiel-Prompts:</Label>
                <div className="flex flex-wrap gap-2">
                  {[
                    "Mehr Fallstudien zu echten Unternehmen",
                    "Fokus auf ITIL-Prozesse",
                    "Berechnungen mit Deckungsbeitrag",
                    "Mindestens 2 Diagramm-Aufgaben",
                    "Praxisbezogene Multiple-Choice",
                  ].map((example) => (
                    <Badge
                      key={example}
                      variant="outline"
                      className="cursor-pointer hover:bg-accent"
                      onClick={() => setFreePrompt((prev) => prev ? `${prev}\n${example}` : example)}
                    >
                      {example}
                    </Badge>
                  ))}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="context" className="space-y-4 py-4">
              <div className="space-y-3">
                <Label className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Kontext-Material hinzufügen
                </Label>
                <p className="text-sm text-muted-foreground">
                  Füge Texte aus Unterrichtsmaterial, Büchern oder Skripten hinzu.
                  Die KI nutzt diese als Grundlage für die Aufgaben.
                </p>
                
                <Textarea
                  placeholder="Füge hier Text aus deinem Unterrichtsmaterial ein..."
                  value={currentContext}
                  onChange={(e) => setCurrentContext(e.target.value)}
                  className="min-h-[120px]"
                />
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={addContextText}
                  disabled={!currentContext.trim()}
                >
                  <Upload className="h-4 w-4 mr-2" />
                  Text hinzufügen
                </Button>
              </div>

              {/* Added Context Texts */}
              {contextTexts.length > 0 && (
                <div className="space-y-2">
                  <Label>Hinzugefügtes Material ({contextTexts.length})</Label>
                  <div className="space-y-2 max-h-[200px] overflow-y-auto">
                    {contextTexts.map((text, index) => (
                      <div 
                        key={index}
                        className="flex items-start gap-2 p-2 bg-muted rounded-md"
                      >
                        <FileText className="h-4 w-4 mt-0.5 flex-shrink-0" />
                        <p className="text-sm flex-1 line-clamp-2">{text}</p>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6 flex-shrink-0"
                          onClick={() => removeContextText(index)}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        ) : (
          <div className="text-center py-8 space-y-4">
            <div className="w-16 h-16 mx-auto bg-green-500/10 rounded-full flex items-center justify-center">
              <Check className="h-8 w-8 text-green-500" />
            </div>
            <div>
              <p className="font-medium text-lg">Übungsklausur erstellt!</p>
              <p className="text-sm text-muted-foreground">
                Du kannst jetzt mit dem Üben beginnen.
              </p>
            </div>
          </div>
        )}

        <DialogFooter>
          {!generated ? (
            <>
              <Button variant="outline" onClick={handleClose}>
                Abbrechen
              </Button>
              <Button
                onClick={handleGenerate}
                disabled={generating || selectedThemas.length === 0}
              >
                {generating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Generiere...
                  </>
                ) : (
                  <>
                    <Wand2 className="h-4 w-4 mr-2" />
                    Klausur erstellen
                  </>
                )}
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => setGenerated(false)}>
                Weitere erstellen
              </Button>
              <Button onClick={handleClose}>
                Zur Klausur
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default MockExamGenerator;
