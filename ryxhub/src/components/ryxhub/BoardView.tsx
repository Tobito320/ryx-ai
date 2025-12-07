import { useCallback, useEffect, useState } from "react";
import { Tldraw, Editor, createShapeId } from "tldraw";
import "tldraw/tldraw.css";
import { 
  FileText, 
  Mail, 
  StickyNote, 
  FolderOpen, 
  Plus,
  Search,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle,
  DialogTrigger 
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import type { GmailAccount } from "@/types/ryxhub";
import { API_ENDPOINTS } from "@/config";

// Document categories for organization
const DOCUMENT_CATEGORIES = [
  { id: "all", label: "Alle", icon: FolderOpen },
  { id: "azubi", label: "Azubi/Schule", icon: FileText },
  { id: "arbeit", label: "Arbeit", icon: FileText },
  { id: "aok", label: "AOK", icon: FileText },
  { id: "sparkasse", label: "Sparkasse", icon: FileText },
  { id: "auto", label: "Auto", icon: FileText },
  { id: "familie", label: "Familie", icon: FileText },
  { id: "other", label: "Sonstiges", icon: FileText },
];

interface DocumentFile {
  name: string;
  path: string;
  type: string;
  category?: string;
  modifiedAt?: string;
}

export function BoardView() {
  const [editor, setEditor] = useState<Editor | null>(null);
  const [documents, setDocuments] = useState<DocumentFile[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [gmailAccounts, setGmailAccounts] = useState<GmailAccount[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [addDocDialogOpen, setAddDocDialogOpen] = useState(false);
  const [gmailDialogOpen, setGmailDialogOpen] = useState(false);
  const [newGmailEmail, setNewGmailEmail] = useState("");
  const [newGmailName, setNewGmailName] = useState("");

  // Load documents from /home/tobi/documents/
  const loadDocuments = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch(API_ENDPOINTS.documentsScan);
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.documents || []);
      } else {
        // Mock data for development
        setDocuments([
          { name: "AOK_Bescheid_2024.pdf", path: "/home/tobi/documents/aok/", type: "pdf", category: "aok" },
          { name: "Ausbildungsvertrag.pdf", path: "/home/tobi/documents/azubi/", type: "pdf", category: "azubi" },
          { name: "Sparkasse_Kontoauszug.pdf", path: "/home/tobi/documents/sparkasse/", type: "pdf", category: "sparkasse" },
          { name: "TÜV_Termin.pdf", path: "/home/tobi/documents/auto/", type: "pdf", category: "auto" },
          { name: "Arbeitszeugnis.pdf", path: "/home/tobi/documents/arbeit/", type: "pdf", category: "arbeit" },
        ]);
      }
    } catch (error) {
      console.error("Failed to load documents:", error);
      // Use mock data
      setDocuments([
        { name: "AOK_Bescheid_2024.pdf", path: "/home/tobi/documents/aok/", type: "pdf", category: "aok" },
        { name: "Ausbildungsvertrag.pdf", path: "/home/tobi/documents/azubi/", type: "pdf", category: "azubi" },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Load Gmail accounts
  const loadGmailAccounts = useCallback(async () => {
    try {
      const response = await fetch(API_ENDPOINTS.gmailAccounts);
      if (response.ok) {
        const data = await response.json();
        setGmailAccounts(data.accounts || []);
        const defaultAcc = data.accounts?.find((a: GmailAccount) => a.isDefault);
        if (defaultAcc) setSelectedAccount(defaultAcc.id);
      }
    } catch (error) {
      console.error("Failed to load Gmail accounts:", error);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
    loadGmailAccounts();
  }, [loadDocuments, loadGmailAccounts]);

  // Filter documents
  const filteredDocuments = documents.filter((doc) => {
    const matchesCategory = selectedCategory === "all" || doc.category === selectedCategory;
    const matchesSearch = doc.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  // Add document to canvas as a shape
  const addDocumentToCanvas = useCallback((doc: DocumentFile) => {
    if (!editor) return;

    const shapeId = createShapeId();
    const viewportCenter = editor.getViewportScreenCenter();
    const pagePoint = editor.screenToPage(viewportCenter);

    // Add as a note shape with document info
    editor.createShapes([{
      id: shapeId,
      type: "note",
      x: pagePoint.x - 100 + Math.random() * 50,
      y: pagePoint.y - 50 + Math.random() * 50,
      props: {
        text: `📄 ${doc.name}\n\n📁 ${doc.category?.toUpperCase() || "Dokument"}\n📍 ${doc.path}`,
        color: getCategoryColor(doc.category),
        size: "m",
      },
    }]);

    toast.success(`${doc.name} zum Board hinzugefügt`);
    setAddDocDialogOpen(false);
  }, [editor]);

  // Get color based on category
  const getCategoryColor = (category?: string): "yellow" | "blue" | "green" | "red" | "violet" | "orange" | "grey" => {
    switch (category) {
      case "aok": return "green";
      case "sparkasse": return "blue";
      case "arbeit": return "violet";
      case "azubi": return "orange";
      case "auto": return "red";
      case "familie": return "grey";
      default: return "yellow";
    }
  };

  // Add quick note
  const addQuickNote = useCallback(() => {
    if (!editor) return;

    const shapeId = createShapeId();
    const viewportCenter = editor.getViewportScreenCenter();
    const pagePoint = editor.screenToPage(viewportCenter);

    editor.createShapes([{
      id: shapeId,
      type: "note",
      x: pagePoint.x - 100,
      y: pagePoint.y - 50,
      props: {
        text: "Neue Notiz...",
        color: "yellow",
        size: "m",
      },
    }]);

    // Select and start editing
    editor.select(shapeId);
  }, [editor]);

  // Add email draft placeholder
  const addEmailDraft = useCallback(() => {
    if (!editor) return;

    const shapeId = createShapeId();
    const viewportCenter = editor.getViewportScreenCenter();
    const pagePoint = editor.screenToPage(viewportCenter);

    editor.createShapes([{
      id: shapeId,
      type: "note",
      x: pagePoint.x - 100,
      y: pagePoint.y - 50,
      props: {
        text: `✉️ E-Mail Entwurf\n\nAn: \nBetreff: \n\n---\n\nInhalt hier schreiben...`,
        color: "blue",
        size: "l",
      },
    }]);

    editor.select(shapeId);
    toast.info("E-Mail Entwurf erstellt - bearbeite und verbinde mit Dokumenten");
  }, [editor]);

  // AI Auto-organize documents WITH INTELLIGENCE
  const autoOrganizeDocuments = useCallback(async () => {
    if (!editor || documents.length === 0) {
      toast.error("Keine Dokumente gefunden");
      return;
    }

    toast.info("🤖 AI analysiert und organisiert...");
    
    const categories = [...new Set(documents.map(d => d.category))];
    let x = 100;
    let y = 100;
    
    for (const category of categories) {
      const catDocs = documents.filter(d => d.category === category);
      
      for (const [docIndex, doc] of catDocs.entries()) {
        try {
          // Smart analyze each document
          const analysis = await fetch(`${API_ENDPOINTS.documentsScan.replace('/scan', '')}/analyze`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: doc.path + doc.name }),
          }).then(r => r.ok ? r.json() : null);

          const shapeId = createShapeId();
          const text = analysis 
            ? `📄 ${doc.name}\n\n📋 ${analysis.type}\n⏰ ${analysis.priority}\n${analysis.deadlines.length > 0 ? `⚠️ Frist: ${analysis.deadlines[0].date}` : ''}\n\n${analysis.summary.slice(0, 100)}...`
            : `📄 ${doc.name}\n\n📁 ${category?.toUpperCase() || "Dokument"}`;

          editor.createShapes([{
            id: shapeId,
            type: "note",
            x: x + (docIndex % 3) * 250,
            y: y + Math.floor(docIndex / 3) * 200,
            props: {
              text,
              color: analysis?.priority === "HOCH" ? "red" : getCategoryColor(doc.category),
              size: "l",
            },
          }]);
        } catch (error) {
          console.error("Analysis failed for", doc.name, error);
          // Fallback to simple display
          const shapeId = createShapeId();
          editor.createShapes([{
            id: shapeId,
            type: "note",
            x: x + (docIndex % 3) * 250,
            y: y + Math.floor(docIndex / 3) * 150,
            props: {
              text: `📄 ${doc.name}\n\n📁 ${category?.toUpperCase()}`,
              color: getCategoryColor(doc.category),
              size: "m",
            },
          }]);
        }
      }
      
      x += 850;
      if (x > 2000) {
        x = 100;
        y += 700;
      }
    }

    toast.success(`${documents.length} Dokumente intelligent organisiert!`);
  }, [editor, documents]);

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Top Toolbar */}
      <div className="h-12 px-3 border-b border-border bg-card/50 flex items-center justify-between gap-2 shrink-0">
        {/* Left: Quick Actions */}
        <div className="flex items-center gap-1.5">
          <Button 
            variant="default" 
            size="sm" 
            className="h-8 gap-1.5 bg-primary"
            onClick={autoOrganizeDocuments}
          >
            <span className="text-xs">🤖 AI Organisieren</span>
          </Button>
          
          <Button 
            variant="outline" 
            size="sm" 
            className="h-8 gap-1.5"
            onClick={addQuickNote}
          >
            <StickyNote className="w-3.5 h-3.5" />
            <span className="hidden sm:inline text-xs">Notiz</span>
          </Button>
          
          <Dialog open={addDocDialogOpen} onOpenChange={setAddDocDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" className="h-8 gap-1.5">
                <FileText className="w-3.5 h-3.5" />
                <span className="hidden sm:inline text-xs">Dokument</span>
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[80vh]">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <FolderOpen className="w-5 h-5" />
                  Dokument hinzufügen
                </DialogTitle>
              </DialogHeader>
              
              <div className="space-y-4">
                {/* Search & Filter */}
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      placeholder="Dokument suchen..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-9 h-9"
                    />
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="h-9"
                    onClick={loadDocuments}
                  >
                    <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
                  </Button>
                </div>

                {/* Category Tabs */}
                <Tabs value={selectedCategory} onValueChange={setSelectedCategory}>
                  <TabsList className="grid grid-cols-4 lg:grid-cols-7 h-auto gap-1 bg-transparent p-0">
                    {DOCUMENT_CATEGORIES.map((cat) => (
                      <TabsTrigger
                        key={cat.id}
                        value={cat.id}
                        className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                      >
                        {cat.label}
                      </TabsTrigger>
                    ))}
                  </TabsList>
                </Tabs>

                {/* Document List */}
                <ScrollArea className="h-64 border rounded-lg">
                  <div className="p-2 space-y-1">
                    {filteredDocuments.length === 0 ? (
                      <div className="text-center py-8 text-muted-foreground text-sm">
                        Keine Dokumente gefunden
                      </div>
                    ) : (
                      filteredDocuments.map((doc, idx) => (
                        <button
                          key={idx}
                          onClick={() => addDocumentToCanvas(doc)}
                          className="w-full flex items-center gap-3 p-2 rounded-md hover:bg-muted/50 transition-colors text-left"
                        >
                          <FileText className={cn(
                            "w-5 h-5 shrink-0",
                            doc.category === "aok" && "text-green-500",
                            doc.category === "sparkasse" && "text-blue-500",
                            doc.category === "arbeit" && "text-violet-500",
                            doc.category === "azubi" && "text-orange-500",
                            doc.category === "auto" && "text-red-500",
                            doc.category === "familie" && "text-gray-500",
                          )} />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium truncate">{doc.name}</div>
                            <div className="text-xs text-muted-foreground truncate">{doc.path}</div>
                          </div>
                          <Plus className="w-4 h-4 text-muted-foreground" />
                        </button>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </div>
            </DialogContent>
          </Dialog>

          <Button 
            variant="outline" 
            size="sm" 
            className="h-8 gap-1.5"
            onClick={addEmailDraft}
          >
            <Mail className="w-3.5 h-3.5" />
            <span className="hidden sm:inline text-xs">E-Mail</span>
          </Button>
        </div>

        {/* Center: Board Name */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">
            Mein Board
          </span>
        </div>

        {/* Right: Gmail Account Selector */}
        <div className="flex items-center gap-2">
          {gmailAccounts.length > 0 ? (
            <Select value={selectedAccount || undefined} onValueChange={setSelectedAccount}>
              <SelectTrigger className="w-[180px] h-8 text-xs">
                <Mail className="w-3.5 h-3.5 mr-1.5" />
                <SelectValue placeholder="Gmail Account" />
              </SelectTrigger>
              <SelectContent>
                {gmailAccounts.map((acc) => (
                  <SelectItem key={acc.id} value={acc.id} className="text-xs">
                    {acc.email} {acc.isDefault && "⭐"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Dialog open={gmailDialogOpen} onOpenChange={setGmailDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
                  <Mail className="w-3.5 h-3.5" />
                  Gmail verbinden
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Gmail Account verbinden</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium">E-Mail</label>
                    <Input
                      type="email"
                      placeholder="deine@gmail.com"
                      value={newGmailEmail}
                      onChange={(e) => setNewGmailEmail(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Name</label>
                    <Input
                      type="text"
                      placeholder="Mein Gmail"
                      value={newGmailName}
                      onChange={(e) => setNewGmailName(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div className="text-xs text-muted-foreground">
                    ℹ️ OAuth Integration kommt später. Für jetzt nur zum Tracking.
                  </div>
                  <Button
                    onClick={async () => {
                      if (!newGmailEmail) return;
                      try {
                        const response = await fetch(API_ENDPOINTS.gmailAccounts, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({
                            email: newGmailEmail,
                            name: newGmailName || newGmailEmail,
                            isDefault: true,
                          }),
                        });
                        if (response.ok) {
                          const account = await response.json();
                          setGmailAccounts([account]);
                          setSelectedAccount(account.id);
                          setGmailDialogOpen(false);
                          setNewGmailEmail("");
                          setNewGmailName("");
                          toast.success("Gmail Account hinzugefügt!");
                        }
                      } catch (error) {
                        toast.error("Fehler beim Hinzufügen");
                      }
                    }}
                    className="w-full"
                  >
                    Hinzufügen
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </div>

      {/* tldraw Canvas */}
      <div className="flex-1 relative">
        <Tldraw
          onMount={(editor) => {
            setEditor(editor);
            // Configure for touch/mobile and hide watermark
            editor.updateInstanceState({ 
              isDebugMode: false,
            });
          }}
          inferDarkMode
          hideUi={false}
          components={{
            // Hide watermark by providing empty component
            WatermarkComponent: () => null,
          }}
        />
      </div>
    </div>
  );
}
