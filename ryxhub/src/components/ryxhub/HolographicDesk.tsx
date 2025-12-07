/**
 * Holographic Desk - Document workspace
 * Clean n8n-inspired design, compact
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { cn } from "@/lib/utils";
import { log } from "@/lib/logger";
import { DocumentCard } from "./DocumentCard";
import { AISidebar } from "./AISidebar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Search,
  RefreshCw,
  FolderOpen,
  AlertTriangle,
  Trash2,
  Mail,
  ChevronDown,
  Plus,
  Upload,
  X,
  Sparkles,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8420";

interface Document {
  name: string;
  path: string;
  type: string;
  category: string;
  modifiedAt?: string;
  size?: number;
}

interface DashboardSummary {
  documents: {
    total: number;
    by_category: Record<string, number>;
  };
  reminders: {
    today: number;
    overdue: number;
    items: any[];
  };
  trash: {
    tomorrow: { type: string; description: string }[];
  };
  profile: {
    name: string;
    address: string;
  };
}

interface GmailAccount {
  id: string;
  email: string;
  name: string;
  isDefault: boolean;
}

const CATEGORIES = [
  { id: "all", label: "Alle", icon: FolderOpen },
  { id: "familie", label: "Familie", color: "#8b5cf6" },
  { id: "aok", label: "AOK", color: "#22c55e" },
  { id: "sparkasse", label: "Sparkasse", color: "#3b82f6" },
  { id: "auto", label: "Auto", color: "#ef4444" },
  { id: "azubi", label: "Azubi", color: "#f97316" },
  { id: "arbeit", label: "Arbeit", color: "#a855f7" },
];

export function HolographicDesk() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [gmailAccounts, setGmailAccounts] = useState<GmailAccount[]>([]);
  const [selectedGmail, setSelectedGmail] = useState<string | null>(null);
  const [gmailModalOpen, setGmailModalOpen] = useState(false);
  const [newGmailEmail, setNewGmailEmail] = useState("");
  const [newGmailName, setNewGmailName] = useState("");
  const [newGmailAppPassword, setNewGmailAppPassword] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null);
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Open document with system default app
  const openDocument = async (doc: Document) => {
    try {
      const res = await fetch(`${API_BASE}/api/documents/open`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: doc.path }),
      });
      if (res.ok) {
        toast.success(`Öffne ${doc.name}`);
      } else {
        const err = await res.json();
        const errMsg = typeof err.detail === 'string' ? err.detail : "Fehler beim Öffnen";
        toast.error(errMsg);
      }
    } catch (error) {
      toast.error("Verbindungsfehler");
    }
  };

  // Preview document
  const showPreview = async (doc: Document) => {
    setPreviewDoc(doc);
    try {
      const res = await fetch(`${API_BASE}/api/documents/preview/${encodeURIComponent(doc.path)}`);
      if (res.ok) {
        const data = await res.json();
        setPreviewContent(data.content || null);
      }
    } catch (error) {
      log.error("Preview failed", { error });
    }
  };

  // Handle document click - toggle selection
  const handleDocClick = (doc: Document) => {
    // Toggle: if already selected, deselect
    if (selectedDoc?.path === doc.path) {
      setSelectedDoc(null);
    } else {
      setSelectedDoc(doc);
    }
  };

  const handleDocDoubleClick = (doc: Document) => {
    // Show in-app preview instead of opening externally
    showPreview(doc);
  };

  // Load everything on mount
  useEffect(() => {
    loadData();
    loadGmailAccounts();
    log.info("HolographicDesk mounted");
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [docsRes, summaryRes] = await Promise.all([
        fetch(`${API_BASE}/api/documents/scan`),
        fetch(`${API_BASE}/api/dashboard/summary`),
      ]);

      if (docsRes.ok) {
        const docsData = await docsRes.json();
        setDocuments(docsData.documents || []);
      }

      if (summaryRes.ok) {
        const summaryData = await summaryRes.json();
        setSummary(summaryData);
      }

      log.info("Data loaded");
    } catch (error) {
      log.error("Failed to load data", { error });
    } finally {
      setIsLoading(false);
    }
  };

  const loadGmailAccounts = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/gmail/accounts`);
      if (res.ok) {
        const data = await res.json();
        setGmailAccounts(data.accounts || []);
        if (data.default_account) {
          setSelectedGmail(data.default_account);
        }
      }
    } catch (error) {
      log.error("Failed to load Gmail accounts", { error });
    }
  };

  const addGmailAccount = async () => {
    if (!newGmailEmail.trim()) {
      toast.error("Email erforderlich");
      return;
    }
    if (!newGmailAppPassword.trim()) {
      toast.error("App-Passwort erforderlich");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/gmail/accounts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: newGmailEmail.trim(),
          name: newGmailName.trim() || newGmailEmail.split("@")[0],
          app_password: newGmailAppPassword.trim(),
          isDefault: gmailAccounts.length === 0,
        }),
      });
      if (res.ok) {
        toast.success("Gmail Account hinzugefügt");
        setNewGmailEmail("");
        setNewGmailName("");
        setNewGmailAppPassword("");
        loadGmailAccounts();
      } else {
        const err = await res.json();
        const errMsg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail) || "Fehler";
        toast.error(errMsg);
      }
    } catch (error) {
      toast.error("Verbindungsfehler");
    }
  };

  const removeGmailAccount = async (id: string) => {
    try {
      await fetch(`${API_BASE}/api/gmail/accounts/${id}`, { method: "DELETE" });
      loadGmailAccounts();
      toast.success("Account entfernt");
    } catch (error) {
      toast.error("Fehler beim Entfernen");
    }
  };

  const setDefaultGmail = async (id: string) => {
    try {
      await fetch(`${API_BASE}/api/gmail/accounts/${id}/default`, { method: "PUT" });
      loadGmailAccounts();
      toast.success("Default gesetzt");
    } catch (error) {
      toast.error("Fehler");
    }
  };

  // Drag & Drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      uploadFiles(files);
    }
  };

  // Upload files function
  const uploadFiles = async (files: File[]) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('category', selectedCategory === 'all' ? 'unsorted' : selectedCategory);

    try {
      const res = await fetch(`${API_BASE}/api/documents/upload-multiple`, {
        method: 'POST',
        body: formData,
      });
      
      if (res.ok) {
        const data = await res.json();
        toast.success(`${data.total} Datei(en) hochgeladen`);
        loadData(); // Refresh documents
      } else {
        const err = await res.json();
        toast.error(err.detail || "Upload fehlgeschlagen");
      }
    } catch (error) {
      toast.error("Upload fehlgeschlagen");
    }
  };

  // Filter documents
  const filteredDocuments = documents.filter((doc) => {
    const matchesCategory = selectedCategory === "all" || doc.category === selectedCategory;
    const matchesSearch = doc.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  // Group by category for stacks
  const documentsByCategory = CATEGORIES.slice(1).map((cat) => ({
    ...cat,
    documents: documents.filter((d) => d.category === cat.id),
    count: documents.filter((d) => d.category === cat.id).length,
  }));

  return (
    <div 
      className="h-full flex bg-background"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {isDragging && (
        <div className="absolute inset-0 bg-primary/10 border-2 border-dashed border-primary z-50 flex items-center justify-center">
          <div className="text-lg font-medium text-primary">Dateien hier ablegen</div>
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.txt"
        className="hidden"
        onChange={(e) => {
          const files = Array.from(e.target.files || []);
          if (files.length > 0) {
            uploadFiles(files);
          }
          // Reset input
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
        }}
      />

      {/* Main Desk Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar - Compact */}
        <div className="h-10 border-b flex items-center justify-between px-3 bg-card/30">
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-medium">Dokumente</h1>
            <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
              {documents.length}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            {/* Search */}
            <div className="relative w-40">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
              <Input
                placeholder="Suchen..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-7 h-7 text-xs bg-background"
              />
            </div>

            {/* Add Document */}
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => fileInputRef.current?.click()}
              title="Dokument hinzufügen"
            >
              <Upload className="w-3.5 h-3.5" />
            </Button>

            {/* Gmail Selector */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-7 px-2 gap-1">
                  <Mail className="w-3.5 h-3.5" />
                  <ChevronDown className="w-2.5 h-2.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52">
                {gmailAccounts.map((acc) => (
                  <DropdownMenuItem
                    key={acc.id}
                    onClick={() => setDefaultGmail(acc.id)}
                    className="flex justify-between text-xs"
                  >
                    <span>{acc.email}</span>
                    {acc.isDefault && <span className="text-[10px] text-primary">★</span>}
                  </DropdownMenuItem>
                ))}
                {gmailAccounts.length > 0 && <DropdownMenuSeparator />}
                <DropdownMenuItem onClick={() => setGmailModalOpen(true)} className="text-xs">
                  <Plus className="w-3 h-3 mr-1.5" />
                  Gmail hinzufügen
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Refresh */}
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={loadData}
              disabled={isLoading}
            >
              <RefreshCw className={cn("w-3.5 h-3.5", isLoading && "animate-spin")} />
            </Button>
          </div>
        </div>

        {/* Alerts Bar - Compact */}
        {summary && (summary.reminders.overdue > 0 || summary.trash.tomorrow.length > 0) && (
          <div className="px-3 py-1 bg-destructive/5 border-b flex items-center gap-2 text-[10px]">
            {summary.reminders.overdue > 0 && (
              <div className="flex items-center gap-1 text-destructive">
                <AlertTriangle className="w-2.5 h-2.5" />
                <span>{summary.reminders.overdue} überfällig</span>
              </div>
            )}
            {summary.trash.tomorrow.length > 0 && (
              <div className="flex items-center gap-1 text-orange-500">
                <Trash2 className="w-2.5 h-2.5" />
                <span>Morgen: {summary.trash.tomorrow.map((t) => t.type).join(", ")}</span>
              </div>
            )}
          </div>
        )}

        {/* Category Tabs - Compact */}
        <div className="px-3 py-1.5 border-b bg-card/20">
          <div className="flex gap-1 overflow-x-auto">
            {CATEGORIES.map((cat) => {
              const count = cat.id === "all"
                ? documents.length
                : documents.filter((d) => d.category === cat.id).length;

              return (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={cn(
                    "flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium transition-all",
                    "whitespace-nowrap",
                    selectedCategory === cat.id
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  )}
                >
                  {cat.label}
                  {count > 0 && (
                    <span className="opacity-60">{count}</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Document Grid - Compact */}
        <ScrollArea className="flex-1 p-3">
          {filteredDocuments.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-muted-foreground">
              <FolderOpen className="w-10 h-10 mb-2 opacity-20" />
              <p className="text-xs">Keine Dokumente</p>
              <p className="text-[10px] opacity-60">Drag & Drop zum Hinzufügen</p>
            </div>
          ) : (
            <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-6 lg:grid-cols-7 xl:grid-cols-9 gap-2">
              {filteredDocuments.map((doc) => (
                <DocumentCard
                  key={doc.path + doc.name}
                  document={doc}
                  selected={selectedDoc?.name === doc.name}
                  onClick={() => handleDocClick(doc)}
                  onDoubleClick={() => handleDocDoubleClick(doc)}
                  onPreview={() => showPreview(doc)}
                />
              ))}
            </div>
          )}
        </ScrollArea>
      </div>

      {/* AI Sidebar */}
      <AISidebar
        document={selectedDoc}
        onClose={() => setSelectedDoc(null)}
        summary={summary}
      />

      {/* Gmail Modal */}
      <Dialog open={gmailModalOpen} onOpenChange={setGmailModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Gmail Account verwalten</DialogTitle>
            <DialogDescription>
              Füge Gmail Accounts hinzu für E-Mail Integration
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Existing accounts */}
            {gmailAccounts.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium">Verbundene Accounts:</p>
                {gmailAccounts.map((acc) => (
                  <div key={acc.id} className="flex items-center justify-between p-2 rounded border">
                    <div>
                      <p className="text-sm font-medium">{acc.name}</p>
                      <p className="text-xs text-muted-foreground">{acc.email}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {acc.isDefault && (
                        <span className="text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded">Default</span>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => removeGmailAccount(acc.id)}
                      >
                        <X className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Add new account */}
            <div className="space-y-3 pt-2 border-t">
              <p className="text-sm font-medium">Neuen Account hinzufügen:</p>
              <Input
                placeholder="Email Adresse"
                value={newGmailEmail}
                onChange={(e) => setNewGmailEmail(e.target.value)}
                type="email"
              />
              <Input
                placeholder="Name (optional)"
                value={newGmailName}
                onChange={(e) => setNewGmailName(e.target.value)}
              />
              <Input
                placeholder="App-Passwort"
                value={newGmailAppPassword}
                onChange={(e) => setNewGmailAppPassword(e.target.value)}
                type="password"
              />
              <Button onClick={addGmailAccount} className="w-full">
                <Plus className="w-4 h-4 mr-2" />
                Account hinzufügen
              </Button>
              <p className="text-xs text-muted-foreground text-center">
                App-Passwort in Gmail: Einstellungen → Sicherheit → 2FA aktivieren → App-Passwörter
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Document Preview Modal */}
      <Dialog open={!!previewDoc} onOpenChange={(open) => !open && setPreviewDoc(null)}>
        <DialogContent className="sm:max-w-4xl max-h-[90vh] overflow-hidden">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FolderOpen className="w-4 h-4" />
              {previewDoc?.name}
            </DialogTitle>
            <DialogDescription>
              {previewDoc?.category?.toUpperCase()} • {previewDoc?.type?.toUpperCase()}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-3 py-2">
            {/* PDF Preview */}
            {previewDoc?.type === 'pdf' && (
              <div className="bg-muted rounded-md overflow-hidden" style={{ height: '60vh' }}>
                <iframe
                  src={`${API_BASE}/api/documents/serve/${encodeURIComponent(previewDoc.path)}`}
                  className="w-full h-full border-0"
                  title={previewDoc.name}
                />
              </div>
            )}
            
            {/* Image Preview */}
            {['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(previewDoc?.type || '') && (
              <div className="bg-muted rounded-md overflow-hidden flex items-center justify-center" style={{ maxHeight: '60vh' }}>
                <img
                  src={`${API_BASE}/api/documents/serve/${encodeURIComponent(previewDoc?.path || '')}`}
                  alt={previewDoc?.name}
                  className="max-w-full max-h-full object-contain"
                />
              </div>
            )}
            
            {/* Text Preview */}
            {['txt', 'md', 'json', 'py', 'js', 'ts'].includes(previewDoc?.type || '') && previewContent && (
              <div className="bg-muted p-3 rounded-md overflow-auto" style={{ maxHeight: '60vh' }}>
                <pre className="text-xs whitespace-pre-wrap font-mono">{previewContent}</pre>
              </div>
            )}
            
            {/* Unsupported type */}
            {!['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'txt', 'md', 'json', 'py', 'js', 'ts'].includes(previewDoc?.type || '') && (
              <div className="text-sm text-muted-foreground text-center py-8">
                <FolderOpen className="w-12 h-12 mx-auto mb-2 opacity-20" />
                <p>Keine In-App Vorschau für {previewDoc?.type?.toUpperCase()} Dateien.</p>
                <p className="text-xs mt-1">Klicke "Extern Öffnen" um die Datei zu öffnen.</p>
              </div>
            )}
            
            <div className="flex gap-2">
              {previewDoc?.type === 'pdf' && (
                <Button 
                  variant="outline"
                  onClick={async () => {
                    if (!previewDoc) return;
                    toast.info("Formularfelder werden erkannt...");
                    try {
                      const res = await fetch(`${API_BASE}/api/pdf/ai-fill`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ path: previewDoc.path }),
                      });
                      if (res.ok) {
                        const data = await res.json();
                        if (data.fields?.length > 0) {
                          toast.success(`${data.fields.length} Felder gefunden`);
                          // TODO: Show form filling modal
                          console.log("AI suggestions:", data.suggestions);
                        } else {
                          toast.info("Keine Formularfelder gefunden");
                        }
                      }
                    } catch (error) {
                      toast.error("Formularerkennung fehlgeschlagen");
                    }
                  }}
                >
                  <Sparkles className="w-4 h-4 mr-2" />
                  AI Ausfüllen
                </Button>
              )}
              <Button 
                onClick={() => previewDoc && openDocument(previewDoc)}
                variant="outline"
                className="flex-1"
              >
                Extern Öffnen
              </Button>
              <Button 
                variant="default" 
                onClick={() => setPreviewDoc(null)}
              >
                Schließen
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
