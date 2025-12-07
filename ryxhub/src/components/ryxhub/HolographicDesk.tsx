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
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
    try {
      const res = await fetch(`${API_BASE}/api/gmail/accounts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: newGmailEmail.trim(),
          name: newGmailName.trim() || newGmailEmail.split("@")[0],
          isDefault: gmailAccounts.length === 0,
        }),
      });
      if (res.ok) {
        toast.success("Gmail Account hinzugefügt");
        setNewGmailEmail("");
        setNewGmailName("");
        loadGmailAccounts();
      } else {
        const err = await res.json();
        toast.error(err.detail || "Fehler");
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
      toast.info(`${files.length} Datei(en) - Upload noch nicht implementiert`);
      // TODO: Implement file upload
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
            toast.info(`${files.length} Datei(en) ausgewählt`);
          }
        }}
      />

      {/* Main Desk Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar - Compact */}
        <div className="h-11 border-b flex items-center justify-between px-4 bg-card/50">
          <div className="flex items-center gap-3">
            <h1 className="text-sm font-semibold">Dokumente</h1>
            <span className="text-xs text-muted-foreground">
              {documents.length}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {/* Search */}
            <div className="relative w-48">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <Input
                placeholder="Suchen..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 h-8 text-sm bg-background"
              />
            </div>

            {/* Add Document */}
            <Button
              variant="outline"
              size="sm"
              className="h-8 gap-1.5"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="w-3.5 h-3.5" />
              <span className="hidden sm:inline text-xs">Hinzufügen</span>
            </Button>

            {/* Gmail Selector */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-8 gap-1.5">
                  <Mail className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline text-xs">
                    {gmailAccounts.find(a => a.isDefault)?.email?.split("@")[0] || "Gmail"}
                  </span>
                  <ChevronDown className="w-3 h-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                {gmailAccounts.map((acc) => (
                  <DropdownMenuItem
                    key={acc.id}
                    onClick={() => setDefaultGmail(acc.id)}
                    className="flex justify-between"
                  >
                    <span className="text-sm">{acc.email}</span>
                    {acc.isDefault && <span className="text-xs text-primary">Default</span>}
                  </DropdownMenuItem>
                ))}
                {gmailAccounts.length > 0 && <DropdownMenuSeparator />}
                <DropdownMenuItem onClick={() => setGmailModalOpen(true)}>
                  <Plus className="w-3.5 h-3.5 mr-2" />
                  Gmail hinzufügen
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Refresh */}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={loadData}
              disabled={isLoading}
            >
              <RefreshCw className={cn("w-3.5 h-3.5", isLoading && "animate-spin")} />
            </Button>
          </div>
        </div>

        {/* Alerts Bar - Compact */}
        {summary && (summary.reminders.overdue > 0 || summary.trash.tomorrow.length > 0) && (
          <div className="px-4 py-1.5 bg-destructive/10 border-b flex items-center gap-3 text-xs">
            {summary.reminders.overdue > 0 && (
              <div className="flex items-center gap-1.5 text-destructive">
                <AlertTriangle className="w-3 h-3" />
                <span>{summary.reminders.overdue} überfällig</span>
              </div>
            )}
            {summary.trash.tomorrow.length > 0 && (
              <div className="flex items-center gap-1.5 text-orange-500">
                <Trash2 className="w-3 h-3" />
                <span>Morgen: {summary.trash.tomorrow.map((t) => t.type).join(", ")}</span>
              </div>
            )}
          </div>
        )}

        {/* Category Tabs - Compact */}
        <div className="px-4 py-2 border-b bg-card/30">
          <div className="flex gap-1.5 overflow-x-auto">
            {CATEGORIES.map((cat) => {
              const count = cat.id === "all"
                ? documents.length
                : documents.filter((d) => d.category === cat.id).length;

              return (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={cn(
                    "flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-all",
                    "border border-transparent whitespace-nowrap",
                    selectedCategory === cat.id
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground"
                  )}
                  style={{
                    borderColor: selectedCategory === cat.id && cat.color ? cat.color : undefined,
                  }}
                >
                  {cat.label}
                  {count > 0 && (
                    <span className="text-[10px] opacity-70">
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Document Grid - Compact */}
        <ScrollArea className="flex-1 p-4">
          {filteredDocuments.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
              <FolderOpen className="w-12 h-12 mb-3 opacity-30" />
              <p className="text-sm">Keine Dokumente</p>
              <p className="text-xs opacity-70">
                Drag & Drop oder /home/tobi/documents/
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-8 gap-2.5">
              {filteredDocuments.map((doc) => (
                <DocumentCard
                  key={doc.path + doc.name}
                  document={doc}
                  selected={selectedDoc?.name === doc.name}
                  onClick={() => setSelectedDoc(doc)}
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
              <Button onClick={addGmailAccount} className="w-full">
                <Plus className="w-4 h-4 mr-2" />
                Account hinzufügen
              </Button>
              <p className="text-xs text-muted-foreground text-center">
                Hinweis: Vollständige Gmail API Integration kommt später.
                <br />Aktuell nur für Speichern der Account-Info.
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
