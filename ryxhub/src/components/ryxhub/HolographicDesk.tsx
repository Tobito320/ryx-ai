/**
 * Holographic Desk - Tony Stark style document workspace
 * Ultra-clean n8n-inspired design
 */

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { log } from "@/lib/logger";
import { DocumentCard } from "./DocumentCard";
import { AISidebar } from "./AISidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Search,
  RefreshCw,
  FolderOpen,
  Clock,
  AlertTriangle,
  Trash2,
  Mail,
  ChevronDown,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

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
  const [gmailAccounts, setGmailAccounts] = useState<any[]>([]);
  const [selectedGmail, setSelectedGmail] = useState<string | null>(null);

  // Load everything on mount
  useEffect(() => {
    loadData();
    log.info("HolographicDesk mounted");
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      // Load documents and summary in parallel
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
    <div className="h-full flex bg-background">
      {/* Main Desk Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <div className="h-14 border-b flex items-center justify-between px-6 bg-card/50">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold">Dokumente</h1>
            <span className="text-sm text-muted-foreground">
              {documents.length} Dateien
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Search */}
            <div className="relative w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Suchen..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 h-9 bg-background"
              />
            </div>

            {/* Gmail Selector */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="gap-2">
                  <Mail className="w-4 h-4" />
                  <span className="hidden sm:inline">Gmail</span>
                  <ChevronDown className="w-3 h-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem>+ Gmail verbinden</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Refresh */}
            <Button
              variant="ghost"
              size="icon"
              onClick={loadData}
              disabled={isLoading}
            >
              <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
            </Button>
          </div>
        </div>

        {/* Alerts Bar */}
        {summary && (summary.reminders.overdue > 0 || summary.trash.tomorrow.length > 0) && (
          <div className="px-6 py-2 bg-destructive/10 border-b flex items-center gap-4 text-sm">
            {summary.reminders.overdue > 0 && (
              <div className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="w-4 h-4" />
                <span>{summary.reminders.overdue} überfällige Erinnerungen</span>
              </div>
            )}
            {summary.trash.tomorrow.length > 0 && (
              <div className="flex items-center gap-2 text-orange-500">
                <Trash2 className="w-4 h-4" />
                <span>
                  Morgen: {summary.trash.tomorrow.map((t) => t.type).join(", ")}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Category Tabs */}
        <div className="px-6 py-3 border-b bg-card/30">
          <div className="flex gap-2 overflow-x-auto">
            {CATEGORIES.map((cat) => {
              const count = cat.id === "all"
                ? documents.length
                : documents.filter((d) => d.category === cat.id).length;

              return (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
                    "border border-transparent",
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
                    <Badge variant="secondary" className="ml-1 text-xs">
                      {count}
                    </Badge>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Document Grid */}
        <ScrollArea className="flex-1 p-6">
          {filteredDocuments.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <FolderOpen className="w-16 h-16 mb-4 opacity-30" />
              <p className="text-lg">Keine Dokumente gefunden</p>
              <p className="text-sm">
                Lege PDFs in /home/tobi/documents/ ab
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
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
    </div>
  );
}
