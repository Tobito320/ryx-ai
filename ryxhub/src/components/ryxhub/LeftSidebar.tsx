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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useRyxHub } from "@/context/RyxHubContext";

export function LeftSidebar() {
  const { sessions, selectedSessionId, selectSession, models, ragStatus, setActiveView } = useRyxHub();
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedSections, setExpandedSections] = useState({
    sessions: true,
    models: true,
    rag: true,
    shortcuts: true,
  });

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
                  <button
                    key={session.id}
                    onClick={() => handleSessionClick(session.id)}
                    className={cn(
                      "w-full p-2.5 rounded-lg text-left transition-all",
                      session.id === selectedSessionId
                        ? "bg-primary/10 border border-primary/30"
                        : "hover:bg-muted/50 border border-transparent"
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-foreground truncate">
                        {session.name}
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        {session.timestamp}
                      </span>
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
                ))}
                <Button variant="ghost" size="sm" className="w-full justify-start text-muted-foreground hover:text-foreground">
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
                  <div
                    key={model.id}
                    className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <Circle className={cn("w-2 h-2 fill-current", getStatusColor(model.status))} />
                      <span className="text-sm text-foreground">{model.name}</span>
                    </div>
                    <span className="text-[10px] text-muted-foreground">{model.provider}</span>
                  </div>
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
