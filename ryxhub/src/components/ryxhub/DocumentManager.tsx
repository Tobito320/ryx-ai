/**
 * Document Manager - n8n Style
 * Simple, clean, powerful - no canvas nonsense
 */

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  FileText, 
  Search, 
  Sparkles, 
  MessageSquare, 
  AlertCircle,
  Clock,
  CheckCircle2,
  Loader2,
  Copy,
  Download,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { log } from "@/lib/logger";
import { API_ENDPOINTS } from "@/config";

interface DocumentFile {
  name: string;
  path: string;
  type: string;
  category?: string;
  modifiedAt?: string;
  size?: number;
}

interface DocumentAnalysis {
  type: string;
  sender: string | null;
  date: string | null;
  subject: string | null;
  deadlines: Array<{
    date: string;
    days_left: number;
    urgent: boolean;
  }>;
  requires_response: boolean;
  priority: string;
  summary: string;
  text_preview: string;
}

const CATEGORIES = [
  { id: "all", label: "Alle", color: "default" },
  { id: "familie", label: "Familie", color: "gray" },
  { id: "aok", label: "AOK", color: "green" },
  { id: "sparkasse", label: "Sparkasse", color: "blue" },
  { id: "auto", label: "Auto", color: "red" },
  { id: "azubi", label: "Azubi", color: "orange" },
  { id: "arbeit", label: "Arbeit", color: "purple" },
];

export function DocumentManager() {
  const [documents, setDocuments] = useState<DocumentFile[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<DocumentFile | null>(null);
  const [analysis, setAnalysis] = useState<DocumentAnalysis | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [generatedResponse, setGeneratedResponse] = useState<string>("");
  const [isGenerating, setIsGenerating] = useState(false);

  // Load documents on mount
  useEffect(() => {
    loadDocuments();
    log.info("Document Manager mounted");
  }, []);

  const loadDocuments = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(API_ENDPOINTS.documentsScan);
      const data = await response.json();
      setDocuments(data.documents || []);
      log.info("Documents loaded", { count: data.documents?.length });
    } catch (error) {
      log.error("Failed to load documents", { error });
      toast.error("Fehler beim Laden der Dokumente");
    } finally {
      setIsLoading(false);
    }
  };

  const analyzeDocument = async (doc: DocumentFile) => {
    setSelectedDoc(doc);
    setIsAnalyzing(true);
    setAnalysis(null);
    
    try {
      const response = await fetch(`${API_ENDPOINTS.documentsScan.replace('/scan', '')}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: doc.path + doc.name }),
      });
      
      if (!response.ok) throw new Error("Analysis failed");
      
      const data: DocumentAnalysis = await response.json();
      setAnalysis(data);
      log.info("Document analyzed", { doc: doc.name, type: data.type });
      toast.success("Dokument analysiert!");
    } catch (error) {
      log.error("Document analysis failed", { doc: doc.name, error });
      toast.error("Analyse fehlgeschlagen");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const generateResponse = async () => {
    if (!selectedDoc) return;
    
    setIsGenerating(true);
    try {
      const response = await fetch(`${API_ENDPOINTS.documentsScan.replace('/scan', '')}/generate-response`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          document_path: selectedDoc.path + selectedDoc.name,
          response_type: "standard"
        }),
      });
      
      if (!response.ok) throw new Error("Generation failed");
      
      const data = await response.json();
      setGeneratedResponse(data.template);
      log.info("Response generated", { doc: selectedDoc.name });
      toast.success("Antwort generiert!");
    } catch (error) {
      log.error("Response generation failed", { error });
      toast.error("Fehler beim Generieren");
    } finally {
      setIsGenerating(false);
    }
  };

  const filteredDocuments = documents.filter(doc => {
    const matchesCategory = selectedCategory === "all" || doc.category === selectedCategory;
    const matchesSearch = doc.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const urgentCount = documents.filter(d => d.category === "familie").length; // Simplified

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Dokumente</h1>
            <p className="text-sm text-muted-foreground">
              {documents.length} Dokumente • {urgentCount} dringend
            </p>
          </div>
          <Button onClick={loadDocuments} disabled={isLoading}>
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Aktualisieren"}
          </Button>
        </div>

        {/* Search & Filter */}
        <div className="mt-4 flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Dokument suchen..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        {/* Categories */}
        <div className="mt-3 flex gap-2 flex-wrap">
          {CATEGORIES.map((cat) => (
            <Badge
              key={cat.id}
              variant={selectedCategory === cat.id ? "default" : "outline"}
              className="cursor-pointer"
              onClick={() => setSelectedCategory(cat.id)}
            >
              {cat.label}
            </Badge>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 p-6 overflow-hidden">
        {/* Document List */}
        <Card>
          <CardHeader>
            <CardTitle>Dokumente ({filteredDocuments.length})</CardTitle>
            <CardDescription>Klick auf ein Dokument für Details</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[calc(100vh-300px)]">
              <div className="space-y-2">
                {filteredDocuments.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground">
                    <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>Keine Dokumente gefunden</p>
                  </div>
                ) : (
                  filteredDocuments.map((doc, idx) => (
                    <Card
                      key={idx}
                      className={cn(
                        "cursor-pointer transition-all hover:shadow-md",
                        selectedDoc?.name === doc.name && "ring-2 ring-primary"
                      )}
                      onClick={() => setSelectedDoc(doc)}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                          <FileText className="w-5 h-5 mt-0.5 shrink-0 text-primary" />
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium truncate">{doc.name}</h4>
                            <p className="text-xs text-muted-foreground truncate">{doc.path}</p>
                            <div className="mt-2">
                              <Badge variant="secondary" className="text-xs">
                                {doc.category?.toUpperCase() || "UNBEKANNT"}
                              </Badge>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Document Details & AI */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              AI Assistent
            </CardTitle>
            <CardDescription>
              {selectedDoc ? `Analysiere: ${selectedDoc.name}` : "Wähle ein Dokument"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!selectedDoc ? (
              <div className="text-center py-12 text-muted-foreground">
                <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>Wähle ein Dokument aus der Liste</p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Action Buttons */}
                <div className="flex gap-2">
                  <Button
                    onClick={() => analyzeDocument(selectedDoc)}
                    disabled={isAnalyzing}
                    className="flex-1"
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
                  >
                    {isGenerating ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    ) : (
                      <MessageSquare className="w-4 h-4 mr-2" />
                    )}
                    Antwort schreiben
                  </Button>
                </div>

                {/* Analysis Results */}
                {analysis && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-3 rounded-lg bg-muted/50">
                        <p className="text-xs text-muted-foreground">Typ</p>
                        <p className="font-medium">{analysis.type}</p>
                      </div>
                      <div className="p-3 rounded-lg bg-muted/50">
                        <p className="text-xs text-muted-foreground">Priorität</p>
                        <Badge variant={analysis.priority === "HOCH" ? "destructive" : "secondary"}>
                          {analysis.priority}
                        </Badge>
                      </div>
                    </div>

                    {analysis.deadlines.length > 0 && (
                      <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20">
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

                    <div className="p-3 rounded-lg bg-muted/50">
                      <p className="text-xs text-muted-foreground mb-2">Zusammenfassung</p>
                      <p className="text-sm">{analysis.summary}</p>
                    </div>
                  </div>
                )}

                {/* Generated Response */}
                {generatedResponse && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">Generierte Antwort</p>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          navigator.clipboard.writeText(generatedResponse);
                          toast.success("Kopiert!");
                        }}
                      >
                        <Copy className="w-4 h-4" />
                      </Button>
                    </div>
                    <ScrollArea className="h-64 rounded-lg border p-3 bg-muted/30">
                      <pre className="text-sm whitespace-pre-wrap">{generatedResponse}</pre>
                    </ScrollArea>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
