import { useState, useMemo } from "react";
import {
  MessageSquare,
  Plus,
  Search,
  MoreHorizontal,
  Trash2,
  Edit,
  Settings,
  Zap,
  Home,
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

// Group sessions by date
function groupSessionsByDate(sessions: any[]) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const weekAgo = new Date(today);
  weekAgo.setDate(weekAgo.getDate() - 7);

  const groups: { label: string; sessions: any[] }[] = [
    { label: "Today", sessions: [] },
    { label: "Yesterday", sessions: [] },
    { label: "This Week", sessions: [] },
    { label: "Older", sessions: [] },
  ];

  sessions.forEach((session) => {
    const lastUsed = parseInt(localStorage.getItem(`session-lastused-${session.id}`) || '0');
    const sessionDate = lastUsed ? new Date(lastUsed) : new Date();

    if (sessionDate >= today) {
      groups[0].sessions.push(session);
    } else if (sessionDate >= yesterday) {
      groups[1].sessions.push(session);
    } else if (sessionDate >= weekAgo) {
      groups[2].sessions.push(session);
    } else {
      groups[3].sessions.push(session);
    }
  });

  return groups.filter((g) => g.sessions.length > 0);
}

export function LeftSidebar() {
  const { sessions, selectedSessionId, selectSession, setActiveView, deleteSession, renameSession } = useRyxHub();
  const [searchQuery, setSearchQuery] = useState("");
  const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const filteredSessions = useMemo(() => {
    return sessions.filter((s) =>
      s.name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [sessions, searchQuery]);

  const groupedSessions = useMemo(() => {
    return groupSessionsByDate(filteredSessions);
  }, [filteredSessions]);

  const handleSessionClick = (sessionId: string) => {
    selectSession(sessionId);
    localStorage.setItem(`session-lastused-${sessionId}`, Date.now().toString());
    setActiveView("chat");
  };

  const handleDeleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteSession(sessionId);
    toast.success("Session deleted");
  };

  const handleRenameStart = (sessionId: string, currentName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setRenamingSessionId(sessionId);
    setRenameValue(currentName);
  };

  const handleRenameSubmit = (sessionId: string) => {
    if (!renameValue.trim()) {
      setRenamingSessionId(null);
      return;
    }
    renameSession(sessionId, renameValue);
    toast.success("Session renamed");
    setRenamingSessionId(null);
  };

  const handleNewSession = () => {
    window.dispatchEvent(new CustomEvent('new-session-click'));
  };

  return (
    <aside className="w-64 bg-sidebar border-r border-sidebar-border flex flex-col h-full">
      {/* Header: Logo + Actions */}
      <div className="p-3 border-b border-sidebar-border">
        <div className="flex items-center justify-between">
          <button 
            onClick={() => setActiveView("dashboard")}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity"
          >
            <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
              <Zap className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="text-sm font-semibold text-sidebar-foreground">RyxHub</span>
          </button>
          
          {/* New Chat Icon Button */}
          <Button
            onClick={handleNewSession}
            size="sm"
            variant="ghost"
            className="h-8 w-8 p-0"
            title="New chat"
          >
            <Plus className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Search - Minimal */}
      <div className="px-3 py-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input
            placeholder="Search chats..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 h-8 bg-sidebar-accent/50 border-0 text-sm placeholder:text-muted-foreground/60"
          />
        </div>
      </div>

      {/* Sessions List - Grouped by Date */}
      <ScrollArea className="flex-1 px-2">
        <div className="py-1 space-y-4">
          {groupedSessions.map((group) => (
            <div key={group.label}>
              <div className="px-2 py-1.5 text-[11px] font-medium text-muted-foreground/70 uppercase tracking-wide">
                {group.label}
              </div>
              <div className="space-y-0.5">
                {group.sessions.map((session) => (
                  <div
                    key={session.id}
                    className={cn(
                      "group relative flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer transition-colors",
                      session.id === selectedSessionId
                        ? "bg-sidebar-accent text-sidebar-foreground"
                        : "hover:bg-sidebar-accent/50 text-muted-foreground hover:text-sidebar-foreground"
                    )}
                    onClick={() => handleSessionClick(session.id)}
                  >
                    <MessageSquare className="w-4 h-4 flex-shrink-0 opacity-70" />
                    
                    {renamingSessionId === session.id ? (
                      <Input
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onBlur={() => handleRenameSubmit(session.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleRenameSubmit(session.id);
                          if (e.key === 'Escape') setRenamingSessionId(null);
                        }}
                        className="h-6 text-sm flex-1 bg-transparent border-primary"
                        autoFocus
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : (
                      <span className="text-sm truncate flex-1">
                        {session.name.length > 28 ? session.name.slice(0, 28) + '...' : session.name}
                      </span>
                    )}
                    
                    {/* Actions - Show on Hover */}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button
                          className={cn(
                            "h-6 w-6 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-muted/50 transition-opacity",
                            session.id === selectedSessionId && "opacity-60"
                          )}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-36">
                        <DropdownMenuItem onClick={(e) => handleRenameStart(session.id, session.name, e as any)}>
                          <Edit className="mr-2 h-3.5 w-3.5" />
                          Rename
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={(e) => handleDeleteSession(session.id, e as any)}
                          className="text-destructive focus:text-destructive"
                        >
                          <Trash2 className="mr-2 h-3.5 w-3.5" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                ))}
              </div>
            </div>
          ))}
          
          {filteredSessions.length === 0 && (
            <div className="px-3 py-8 text-center">
              <MessageSquare className="w-8 h-8 mx-auto text-muted-foreground/40 mb-2" />
              <p className="text-sm text-muted-foreground/60">No chats yet</p>
              <p className="text-xs text-muted-foreground/40 mt-1">Start a new conversation</p>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Footer: Home + Settings */}
      <div className="p-2 border-t border-sidebar-border space-y-1">
        <button
          onClick={() => setActiveView("dashboard")}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent/50 transition-colors"
        >
          <Home className="w-4 h-4" />
          Home
        </button>
        <button
          onClick={() => setActiveView("settings")}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent/50 transition-colors"
        >
          <Settings className="w-4 h-4" />
          Settings
        </button>
      </div>
    </aside>
  );
}
