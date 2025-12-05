import { useState } from "react";
import {
  MessageSquare,
  Bot,
  Database,
  Wrench,
  Plus,
  ChevronDown,
  Circle,
  Zap,
  Search,
  MoreVertical,
  Trash2,
  Edit,
  Download,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useRyxHub } from "@/context/RyxHubContext";
import { toast } from "sonner";
import { API_ENDPOINTS } from "@/config";

export function LeftSidebar() {
  const { sessions, selectedSessionId, selectSession, models, ragStatus, setActiveView, deleteSession, renameSession } = useRyxHub();
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedSections, setExpandedSections] = useState({
    sessions: true,
    models: true,
    rag: true,
    shortcuts: true,
  });
  const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const getStatusColor = (status: "online" | "offline" | "loading") => {
    switch (status) {
      case "online":
        return "bg-[hsl(var(--success))]";
      case "loading":
        return "bg-[hsl(var(--warning))] animate-pulse";
      default:
        return "bg-muted-foreground";
    }
  };

  const filteredSessions = sessions.filter((s) =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleSessionClick = (sessionId: string) => {
    selectSession(sessionId);
    setActiveView("chat");
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const session = sessions.find(s => s.id === sessionId);
    if (!session) return;

    try {
      await deleteSession(sessionId);
      toast.success(`Session "${session.name}" deleted`);
    } catch (error) {
      toast.error("Failed to delete session");
    }
  };

  const handleRenameStart = (sessionId: string, currentName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setRenamingSessionId(sessionId);
    setRenameValue(currentName);
  };

  const handleRenameSubmit = async (sessionId: string) => {
    if (!renameValue.trim()) {
      setRenamingSessionId(null);
      return;
    }

    try {
      await renameSession(sessionId, renameValue);
      toast.success("Session renamed");
      setRenamingSessionId(null);
    } catch (error) {
      toast.error("Failed to rename session");
    }
  };

  const handleExportSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const response = await fetch(API_ENDPOINTS.sessionExport(sessionId, 'markdown'));
      if (response.ok) {
        const data = await response.json();
        // Create download link
        const blob = new Blob([data.content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = data.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast.success("Session exported");
      }
    } catch (error) {
      toast.error("Failed to export session");
    }
  };

  return (
    <aside className="w-56 bg-sidebar border-r border-sidebar-border flex flex-col h-full">
      {/* Logo - Compact */}
      <div className="p-2.5 border-b border-sidebar-border">
        <div className="flex items-center gap-1.5">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-primary to-accent flex items-center justify-center">
            <Zap className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="text-sm font-semibold text-sidebar-foreground tracking-tight">
            RyxHub
          </span>
        </div>
      </div>

      {/* Search - Compact */}
      <div className="p-2 border-b border-sidebar-border">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-7 h-7 bg-input border-border text-xs"
          />
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-2 space-y-3">
          {/* Sessions - Compact */}
          <div>
            <button
              onClick={() => toggleSection("sessions")}
              className="flex items-center justify-between w-full text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5 hover:text-foreground transition-colors"
            >
              <span className="flex items-center gap-1.5">
                <MessageSquare className="w-3 h-3" />
                Sessions ({filteredSessions.length})
              </span>
              <ChevronDown
                className={cn(
                  "w-3 h-3 transition-transform",
                  !expandedSections.sessions && "-rotate-90"
                )}
              />
            </button>
            {expandedSections.sessions && (
              <div className="space-y-0.5">
                {filteredSessions.map((session) => (
                  <div
                    key={session.id}
                    className={cn(
                      "relative group w-full p-1.5 rounded-md transition-all",
                      session.id === selectedSessionId
                        ? "bg-primary/10 border border-primary/30"
                        : "hover:bg-muted/50 border border-transparent"
                    )}
                  >
                    <button
                      onClick={() => handleSessionClick(session.id)}
                      className="w-full text-left"
                    >
                      <div className="flex items-center justify-between">
                        {renamingSessionId === session.id ? (
                          <Input
                            value={renameValue}
                            onChange={(e) => setRenameValue(e.target.value)}
                            onBlur={() => handleRenameSubmit(session.id)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleRenameSubmit(session.id);
                              if (e.key === 'Escape') setRenamingSessionId(null);
                            }}
                            className="h-5 text-xs"
                            autoFocus
                            onClick={(e) => e.stopPropagation()}
                          />
                        ) : (
                          <span className="text-xs font-medium text-foreground truncate">
                            {session.name}
                          </span>
                        )}
                        <div className="flex items-center gap-0.5">
                          <span className="text-[9px] text-muted-foreground">
                            {session.timestamp}
                          </span>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-4 w-4 p-0 opacity-0 group-hover:opacity-100"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <MoreVertical className="h-2.5 w-2.5" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={(e) => handleRenameStart(session.id, session.name, e)}>
                                <Edit className="mr-2 h-3.5 w-3.5" />
                                <span className="text-xs">Rename</span>
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={(e) => handleExportSession(session.id, e)}>
                                <Download className="mr-2 h-3.5 w-3.5" />
                                <span className="text-xs">Export</span>
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={(e) => handleDeleteSession(session.id, e)}
                                className="text-destructive"
                              >
                                <Trash2 className="mr-2 h-3.5 w-3.5" />
                                <span className="text-xs">Delete</span>
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </div>
                      <p className="text-[10px] text-muted-foreground truncate mt-0.5">
                        {session.lastMessage}
                      </p>
                    </button>
                  </div>
                ))}
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full h-7 justify-start text-xs text-muted-foreground hover:text-foreground"
                  onClick={() => window.dispatchEvent(new CustomEvent('new-session-click'))}
                >
                  <Plus className="w-3.5 h-3.5 mr-1.5" />
                  New Session
                </Button>
              </div>
            )}
          </div>

          {/* Active Models - Compact */}
          <div>
            <button
              onClick={() => toggleSection("models")}
              className="flex items-center justify-between w-full text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5 hover:text-foreground transition-colors"
            >
              <span className="flex items-center gap-1.5">
                <Bot className="w-3 h-3" />
                Models ({models.filter((m) => m.status === "online").length})
              </span>
              <ChevronDown
                className={cn(
                  "w-3 h-3 transition-transform",
                  !expandedSections.models && "-rotate-90"
                )}
              />
            </button>
            {expandedSections.models && (
              <div className="space-y-0.5">
                {models.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => window.dispatchEvent(new CustomEvent('model-click', { detail: model }))}
                    className="flex items-center justify-between p-1.5 rounded-md hover:bg-muted/50 transition-colors w-full cursor-pointer"
                  >
                    <div className="flex items-center gap-1.5 min-w-0">
                      <Circle className={cn("w-1.5 h-1.5 flex-shrink-0 fill-current", getStatusColor(model.status))} />
                      <span className="text-xs text-foreground truncate">{model.name}</span>
                    </div>
                    <span className="text-[9px] text-muted-foreground flex-shrink-0 ml-1">{model.provider}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* RAG Status - Compact */}
          <div>
            <button
              onClick={() => toggleSection("rag")}
              className="flex items-center justify-between w-full text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5 hover:text-foreground transition-colors"
            >
              <span className="flex items-center gap-1.5">
                <Database className="w-3 h-3" />
                RAG
              </span>
              <ChevronDown
                className={cn(
                  "w-3 h-3 transition-transform",
                  !expandedSections.rag && "-rotate-90"
                )}
              />
            </button>
            {expandedSections.rag && (
              <div className="p-2 rounded-md bg-muted/30 border border-border space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Indexed</span>
                  <span className="text-[hsl(var(--success))] font-mono">{ragStatus.indexed.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Pending</span>
                  <span className="text-[hsl(var(--warning))] font-mono">{ragStatus.pending}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Sync</span>
                  <span className="text-foreground font-mono text-[10px]">{ragStatus.lastSync}</span>
                </div>
                <div className="flex items-center gap-1 pt-0.5">
                  <Circle
                    className={cn(
                      "w-1.5 h-1.5 fill-current",
                      ragStatus.status === "syncing" && "text-[hsl(var(--warning))] animate-pulse",
                      ragStatus.status === "idle" && "text-[hsl(var(--success))]",
                      ragStatus.status === "error" && "text-destructive"
                    )}
                  />
                  <span className="text-[10px] text-muted-foreground capitalize">{ragStatus.status}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </ScrollArea>
    </aside>
  );
}
