/**
 * AI Sidebar - Always visible assistant panel
 * Clean, functional, concise responses
 */

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { log } from "@/lib/logger";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Sparkles,
  FileText,
  Send,
  Copy,
  Check,
  Loader2,
  Clock,
  AlertTriangle,
  Trash2,
  Calendar,
  X,
} from "lucide-react";
import { toast } from "sonner";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8420";

interface Document {
  name: string;
  path: string;
  type: string;
  category: string;
}

interface Analysis {
  type: string;
  sender: string | null;
  date: string | null;
  subject: string | null;
  priority: string;
  deadlines: { date: string; days_left: number; urgent: boolean }[];
  requires_response: boolean;
  summary: string;
}

interface AISidebarProps {
  document: Document | null;
  onClose?: () => void;
  summary?: any;
}

export function AISidebar({ document, onClose, summary }: AISidebarProps) {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [generatedResponse, setGeneratedResponse] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [userMessage, setUserMessage] = useState("");
  const [copied, setCopied] = useState(false);

  // Reset when document changes
  useEffect(() => {
    setAnalysis(null);
    setGeneratedResponse("");
  }, [document?.name]);

  const analyzeDocument = async () => {
    if (!document) return;

    setIsAnalyzing(true);
    setAnalysis(null);

    try {
      const res = await fetch(`${API_BASE}/api/documents/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: document.path + document.name }),
      });

      if (!res.ok) throw new Error("Analysis failed");

      const data = await res.json();
      setAnalysis(data);
      log.info("Document analyzed", { doc: document.name });
    } catch (error) {
      log.error("Analysis failed", { error });
      toast.error("Analyse fehlgeschlagen");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const generateResponse = async () => {
    if (!document) return;

    setIsGenerating(true);

    try {
      const res = await fetch(`${API_BASE}/api/documents/generate-response`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          document_path: document.path + document.name,
          response_type: "standard",
        }),
      });

      if (!res.ok) throw new Error("Generation failed");

      const data = await res.json();
      setGeneratedResponse(data.template);
      log.info("Response generated", { doc: document.name });
    } catch (error) {
      log.error("Generation failed", { error });
      toast.error("Generierung fehlgeschlagen");
    } finally {
      setIsGenerating(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(generatedResponse);
    setCopied(true);
    toast.success("Kopiert!");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="w-[380px] border-l bg-card/50 flex flex-col">
      {/* Header */}
      <div className="h-14 border-b flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-primary" />
          <span className="font-medium">AI Assistent</span>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {/* No document selected */}
          {!document && (
            <div className="space-y-6">
              {/* Quick Info */}
              {summary && (
                <>
                  {/* Today's Reminders */}
                  {summary.reminders?.items?.length > 0 && (
                    <div className="space-y-2">
                      <h3 className="text-sm font-medium flex items-center gap-2">
                        <Calendar className="w-4 h-4" />
                        Erinnerungen
                      </h3>
                      {summary.reminders.items.slice(0, 3).map((r: any, i: number) => (
                        <div
                          key={i}
                          className="text-sm p-2 rounded bg-muted/50 flex items-center gap-2"
                        >
                          <AlertTriangle className="w-3 h-3 text-orange-500" />
                          <span className="truncate">{r.title}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Tomorrow's Trash */}
                  {summary.trash?.tomorrow?.length > 0 && (
                    <div className="space-y-2">
                      <h3 className="text-sm font-medium flex items-center gap-2">
                        <Trash2 className="w-4 h-4" />
                        Morgen: Müllabfuhr
                      </h3>
                      <div className="text-sm p-2 rounded bg-orange-500/10 text-orange-600">
                        {summary.trash.tomorrow.map((t: any) => t.type).join(", ")}
                      </div>
                    </div>
                  )}

                  {/* Profile */}
                  {summary.profile?.name && (
                    <div className="text-sm text-muted-foreground">
                      Hallo {summary.profile.name}! Wähle ein Dokument zum Analysieren.
                    </div>
                  )}
                </>
              )}

              {!summary && (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>Wähle ein Dokument</p>
                </div>
              )}
            </div>
          )}

          {/* Document selected */}
          {document && (
            <div className="space-y-4">
              {/* Document Info */}
              <div className="p-3 rounded-lg bg-muted/50">
                <div className="flex items-start gap-2">
                  <FileText className="w-4 h-4 mt-0.5 text-primary" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{document.name}</p>
                    <p className="text-xs text-muted-foreground capitalize">
                      {document.category}
                    </p>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2">
                <Button
                  onClick={analyzeDocument}
                  disabled={isAnalyzing}
                  className="flex-1"
                  size="sm"
                >
                  {isAnalyzing ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <Sparkles className="w-4 h-4 mr-2" />
                  )}
                  Analysieren
                </Button>
                <Button
                  onClick={generateResponse}
                  disabled={isGenerating || !analysis}
                  variant="secondary"
                  className="flex-1"
                  size="sm"
                >
                  {isGenerating ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <Send className="w-4 h-4 mr-2" />
                  )}
                  Antwort
                </Button>
              </div>

              {/* Analysis Results */}
              {analysis && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2 rounded bg-muted/50">
                      <p className="text-xs text-muted-foreground">Typ</p>
                      <p className="text-sm font-medium">{analysis.type}</p>
                    </div>
                    <div className="p-2 rounded bg-muted/50">
                      <p className="text-xs text-muted-foreground">Priorität</p>
                      <Badge
                        variant={
                          analysis.priority === "HOCH" ? "destructive" : "secondary"
                        }
                      >
                        {analysis.priority}
                      </Badge>
                    </div>
                  </div>

                  {analysis.sender && (
                    <div className="p-2 rounded bg-muted/50">
                      <p className="text-xs text-muted-foreground">Absender</p>
                      <p className="text-sm">{analysis.sender}</p>
                    </div>
                  )}

                  {analysis.deadlines.length > 0 && (
                    <div className="p-2 rounded bg-destructive/10 border border-destructive/20">
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-destructive" />
                        <p className="text-sm font-medium">
                          Frist: {analysis.deadlines[0].date}
                        </p>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        Noch {analysis.deadlines[0].days_left} Tage
                      </p>
                    </div>
                  )}

                  <div className="p-2 rounded bg-muted/50">
                    <p className="text-xs text-muted-foreground mb-1">Zusammenfassung</p>
                    <p className="text-sm leading-relaxed">{analysis.summary}</p>
                  </div>
                </div>
              )}

              {/* Generated Response */}
              {generatedResponse && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium">Antwort</p>
                    <Button size="sm" variant="ghost" onClick={copyToClipboard}>
                      {copied ? (
                        <Check className="w-4 h-4 text-green-500" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                  <div className="p-3 rounded-lg bg-muted/50 border max-h-64 overflow-y-auto">
                    <pre className="text-sm whitespace-pre-wrap font-sans">
                      {generatedResponse}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Chat Input - for quick questions */}
      <div className="p-4 border-t">
        <div className="relative">
          <Textarea
            placeholder="Frag mich etwas..."
            value={userMessage}
            onChange={(e) => setUserMessage(e.target.value)}
            className="min-h-[60px] pr-12 resize-none"
            rows={2}
          />
          <Button
            size="icon"
            className="absolute right-2 bottom-2 h-8 w-8"
            disabled={!userMessage.trim()}
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
