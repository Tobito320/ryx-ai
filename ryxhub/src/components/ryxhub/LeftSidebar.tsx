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
    <aside className="w-72 bg-sidebar border-r border-sidebar-border flex flex-col h-full">
      {/* Logo */}
      <div className="p-4 border-b border-sidebar-border">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
            <Zap className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="text-lg font-semibold text-sidebar-foreground tracking-tight">
            RyxHub
          </span>
        </div>
      </div>

      {/* Search */}
      <div className="p-3 border-b border-sidebar-border">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search sessions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 bg-input border-border text-sm"
          />
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-3 space-y-4">
          {/* Sessions */}
          <div>
            <button
              onClick={() => toggleSection("sessions")}
              className="flex items-center justify-between w-full text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 hover:text-foreground transition-colors"
            >
              <span className="flex items-center gap-2">
                <MessageSquare className="w-3.5 h-3.5" />
                Sessions ({filteredSessions.length})
              </span>
              <ChevronDown
                className={cn(
                  "w-3.5 h-3.5 transition-transform",
                  !expandedSections.sessions && "-rotate-90"
                )}
              />
            </button>
            {expandedSections.sessions && (
              <div className="space-y-1">
                {filteredSessions.map((session) => (
                  <div
                    key={session.id}
                    className={cn(
                      "relative group w-full p-2.5 rounded-lg transition-all",
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
                            className="h-6 text-sm"
                            autoFocus
                            onClick={(e) => e.stopPropagation()}
                          />
                        ) : (
                          <span className="text-sm font-medium text-foreground truncate">
                            {session.name}
                          </span>
                        )}
                        <div className="flex items-center gap-1">
                          <span className="text-[10px] text-muted-foreground">
                            {session.timestamp}
                          </span>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <MoreVertical className="h-3 w-3" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={(e) => handleRenameStart(session.id, session.name, e)}>
                                <Edit className="mr-2 h-4 w-4" />
                                Rename
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={(e) => handleExportSession(session.id, e)}>
                                <Download className="mr-2 h-4 w-4" />
                                Export
                              </DropdownMenuItem>
                              <DropdownMenuItem 
                                onClick={(e) => handleDeleteSession(session.id, e)}
                                className="text-destructive"
                              >
                                <Trash2 className="mr-2 h-4 w-4" />
                                Delete
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground truncate mt-0.5">
                        {session.lastMessage}
                      </p>
                      <div className="flex items-center gap-1 mt-1">
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                          {session.model}
                        </span>
                      </div>
                    </button>
                  </div>
                ))}
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="w-full justify-start text-muted-foreground hover:text-foreground"
                  onClick={() => window.dispatchEvent(new CustomEvent('new-session-click'))}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  New Session
                </Button>
              </div>
            )}
          </div>

          {/* Active Models */}
          <div>
            <button
              onClick={() => toggleSection("models")}
              className="flex items-center justify-between w-full text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 hover:text-foreground transition-colors"
            >
              <span className="flex items-center gap-2">
                <Bot className="w-3.5 h-3.5" />
                Active Models ({models.filter((m) => m.status === "online").length})
              </span>
              <ChevronDown
                className={cn(
                  "w-3.5 h-3.5 transition-transform",
                  !expandedSections.models && "-rotate-90"
                )}
              />
            </button>
            {expandedSections.models && (
              <div className="space-y-1">
                {models.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => window.dispatchEvent(new CustomEvent('model-click', { detail: model }))}
                    className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-colors w-full cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      <Circle className={cn("w-2 h-2 fill-current", getStatusColor(model.status))} />
                      <span className="text-sm text-foreground truncate">{model.name}</span>
                    </div>
                    <span className="text-[10px] text-muted-foreground">{model.provider}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* RAG Status */}
          <div>
            <button
              onClick={() => toggleSection("rag")}
              className="flex items-center justify-between w-full text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 hover:text-foreground transition-colors"
            >
              <span className="flex items-center gap-2">
                <Database className="w-3.5 h-3.5" />
                RAG Index
              </span>
              <ChevronDown
                className={cn(
                  "w-3.5 h-3.5 transition-transform",
                  !expandedSections.rag && "-rotate-90"
                )}
              />
            </button>
            {expandedSections.rag && (
              <div className="p-3 rounded-lg bg-muted/30 border border-border space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Indexed</span>
                  <span className="text-[hsl(var(--success))] font-mono">{ragStatus.indexed.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Pending</span>
                  <span className="text-[hsl(var(--warning))] font-mono">{ragStatus.pending}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Last Sync</span>
                  <span className="text-foreground font-mono">{ragStatus.lastSync}</span>
                </div>
                <div className="flex items-center gap-1.5 pt-1">
                  <Circle
                    className={cn(
                      "w-2 h-2 fill-current",
                      ragStatus.status === "syncing" && "text-[hsl(var(--warning))] animate-pulse",
                      ragStatus.status === "idle" && "text-[hsl(var(--success))]",
                      ragStatus.status === "error" && "text-destructive"
                    )}
                  />
                  <span className="text-xs text-muted-foreground capitalize">{ragStatus.status}</span>
                </div>
              </div>
            )}
          </div>

          {/* Shortcuts */}
          <div>
            <button
              onClick={() => toggleSection("shortcuts")}
              className="flex items-center justify-between w-full text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 hover:text-foreground transition-colors"
            >
              <span className="flex items-center gap-2">
                <Wrench className="w-3.5 h-3.5" />
                Quick Actions
              </span>
              <ChevronDown
                className={cn(
                  "w-3.5 h-3.5 transition-transform",
                  !expandedSections.shortcuts && "-rotate-90"
                )}
              />
            </button>
            {expandedSections.shortcuts && (
              <div className="grid grid-cols-2 gap-2">
                <Button variant="secondary" size="sm" className="justify-start text-xs">
                  <Bot className="w-3.5 h-3.5 mr-1.5" />
                  Agents
                </Button>
                <Button variant="secondary" size="sm" className="justify-start text-xs">
                  <Wrench className="w-3.5 h-3.5 mr-1.5" />
                  Tools
                </Button>
                <Button variant="secondary" size="sm" className="justify-start text-xs">
                  <Database className="w-3.5 h-3.5 mr-1.5" />
                  Sources
                </Button>
                <Button variant="secondary" size="sm" className="justify-start text-xs">
                  <Zap className="w-3.5 h-3.5 mr-1.5" />
                  Triggers
                </Button>
              </div>
            )}
          </div>
        </div>
      </ScrollArea>
    </aside>
  );
}
