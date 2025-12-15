/**
 * Test Upload Dialog
 * 
 * Handles uploading class tests with OCR and verification
 */

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useExam } from "@/context/ExamContext";
import {
  Upload,
  FileText,
  Image,
  Check,
  AlertCircle,
  Loader2,
  X,
  ChevronRight,
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { UploadResult, VerificationPrompt } from "@/types/exam";

interface TestUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type UploadStep = "upload" | "processing" | "verify" | "complete";

export function TestUploadDialog({ open, onOpenChange }: TestUploadDialogProps) {
  const { uploadTest, verifyTestUpload, uploadingTest, selectedSubject, teachers, schools } = useExam();
  
  const [step, setStep] = useState<UploadStep>("upload");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [corrections, setCorrections] = useState<Record<string, string>>({});
  const [progress, setProgress] = useState(0);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setSelectedFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/*": [".png", ".jpg", ".jpeg", ".webp"],
    },
    maxFiles: 1,
  });

  const handleUpload = async () => {
    if (!selectedFile) return;

    setStep("processing");
    setProgress(0);

    // Simulate progress
    const interval = setInterval(() => {
      setProgress((prev) => Math.min(prev + 10, 90));
    }, 200);

    try {
      const result = await uploadTest(selectedFile);
      clearInterval(interval);
      setProgress(100);
      setUploadResult(result);

      if (result.success && result.requiresVerification) {
        // Pre-fill corrections with detected values
        const initialCorrections: Record<string, string> = {};
        result.verificationPrompts?.forEach((prompt) => {
          initialCorrections[prompt.field] = prompt.detected;
        });
        setCorrections(initialCorrections);
        setStep("verify");
      } else if (result.success) {
        setStep("complete");
      } else {
        // Handle error
        setStep("upload");
      }
    } catch (error) {
      clearInterval(interval);
      setStep("upload");
    }
  };

  const handleVerify = async () => {
    if (!uploadResult?.classTestId) return;
    await verifyTestUpload(uploadResult.classTestId, corrections);
    setStep("complete");
  };

  const handleClose = () => {
    setStep("upload");
    setSelectedFile(null);
    setUploadResult(null);
    setCorrections({});
    setProgress(0);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Klassenarbeit hochladen
          </DialogTitle>
          <DialogDescription>
            Lade eine vergangene Klassenarbeit hoch, um das Muster deines Lehrers zu lernen.
          </DialogDescription>
        </DialogHeader>

        {/* Step Indicator */}
        <div className="flex items-center justify-between mb-4">
          {(["upload", "processing", "verify", "complete"] as UploadStep[]).map((s, i) => (
            <div key={s} className="flex items-center">
              <div
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium",
                  step === s
                    ? "bg-primary text-primary-foreground"
                    : i < ["upload", "processing", "verify", "complete"].indexOf(step)
                    ? "bg-primary/20 text-primary"
                    : "bg-muted text-muted-foreground"
                )}
              >
                {i < ["upload", "processing", "verify", "complete"].indexOf(step) ? (
                  <Check className="h-4 w-4" />
                ) : (
                  i + 1
                )}
              </div>
              {i < 3 && (
                <ChevronRight className="h-4 w-4 mx-2 text-muted-foreground" />
              )}
            </div>
          ))}
        </div>

        {/* Step Content */}
        <div className="py-4">
          {step === "upload" && (
            <div className="space-y-4">
              {/* Dropzone */}
              <div
                {...getRootProps()}
                className={cn(
                  "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
                  isDragActive
                    ? "border-primary bg-primary/5"
                    : "border-muted-foreground/25 hover:border-primary/50"
                )}
              >
                <input {...getInputProps()} />
                {selectedFile ? (
                  <div className="flex items-center justify-center gap-3">
                    {selectedFile.type.includes("pdf") ? (
                      <FileText className="h-8 w-8 text-red-500" />
                    ) : (
                      <Image className="h-8 w-8 text-blue-500" />
                    )}
                    <div className="text-left">
                      <p className="font-medium">{selectedFile.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedFile(null);
                      }}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  <>
                    <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                    <p className="text-muted-foreground">
                      {isDragActive
                        ? "Datei hier ablegen..."
                        : "PDF oder Bild hierher ziehen oder klicken"}
                    </p>
                    <p className="text-sm text-muted-foreground mt-2">
                      Unterstützt: PDF, PNG, JPG
                    </p>
                  </>
                )}
              </div>

              {/* Subject Selection */}
              <div className="space-y-2">
                <Label>Fach (optional)</Label>
                <Select defaultValue={selectedSubject?.id}>
                  <SelectTrigger>
                    <SelectValue placeholder="Automatisch erkennen" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">Automatisch erkennen</SelectItem>
                    {schools[0]?.subjects.map((subject) => (
                      <SelectItem key={subject.id} value={subject.id}>
                        {subject.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {step === "processing" && (
            <div className="text-center py-8 space-y-4">
              <Loader2 className="h-12 w-12 mx-auto animate-spin text-primary" />
              <div>
                <p className="font-medium">Verarbeite Klassenarbeit...</p>
                <p className="text-sm text-muted-foreground">
                  OCR und Textextraktion läuft
                </p>
              </div>
              <Progress value={progress} className="w-full" />
            </div>
          )}

          {step === "verify" && uploadResult && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <AlertCircle className="h-5 w-5 text-amber-500" />
                <p className="text-sm">
                  Bitte überprüfe die erkannten Informationen
                </p>
              </div>

              <div className="space-y-4">
                {uploadResult.verificationPrompts?.map((prompt) => (
                  <div key={prompt.field} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label className="capitalize">{getFieldLabel(prompt.field)}</Label>
                      <Badge variant={prompt.confidence > 80 ? "default" : "secondary"}>
                        {prompt.confidence}% sicher
                      </Badge>
                    </div>
                    {prompt.suggestions ? (
                      <Select
                        value={corrections[prompt.field]}
                        onValueChange={(value) =>
                          setCorrections((prev) => ({ ...prev, [prompt.field]: value }))
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {prompt.suggestions.map((suggestion) => (
                            <SelectItem key={suggestion} value={suggestion}>
                              {suggestion}
                            </SelectItem>
                          ))}
                          <SelectItem value="other">Andere...</SelectItem>
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        value={corrections[prompt.field] || ""}
                        onChange={(e) =>
                          setCorrections((prev) => ({
                            ...prev,
                            [prompt.field]: e.target.value,
                          }))
                        }
                        placeholder={prompt.detected}
                      />
                    )}
                  </div>
                ))}

                {/* Suggested Themas */}
                {uploadResult.suggestedThemas && uploadResult.suggestedThemas.length > 0 && (
                  <div className="space-y-2">
                    <Label>Erkannte Themen</Label>
                    <div className="flex flex-wrap gap-2">
                      {uploadResult.suggestedThemas.map((thema) => (
                        <Badge key={thema} variant="outline">
                          {thema}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {step === "complete" && (
            <div className="text-center py-8 space-y-4">
              <div className="w-16 h-16 mx-auto bg-green-500/10 rounded-full flex items-center justify-center">
                <Check className="h-8 w-8 text-green-500" />
              </div>
              <div>
                <p className="font-medium text-lg">Klassenarbeit hochgeladen!</p>
                <p className="text-sm text-muted-foreground">
                  Die Analyse wird im Hintergrund fortgesetzt.
                </p>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          {step === "upload" && (
            <Button onClick={handleUpload} disabled={!selectedFile}>
              Hochladen & Analysieren
            </Button>
          )}
          {step === "verify" && (
            <>
              <Button variant="outline" onClick={() => setStep("upload")}>
                Zurück
              </Button>
              <Button onClick={handleVerify}>
                Bestätigen
              </Button>
            </>
          )}
          {step === "complete" && (
            <Button onClick={handleClose}>
              Fertig
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function getFieldLabel(field: string): string {
  const labels: Record<string, string> = {
    teacher: "Lehrer",
    subject: "Fach",
    date: "Datum",
    thema: "Thema",
  };
  return labels[field] || field;
}

export default TestUploadDialog;
