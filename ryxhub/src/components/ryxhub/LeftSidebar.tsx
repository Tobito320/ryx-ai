import { useMemo, useState, type ElementType, type MouseEvent } from "react";
import { BookMarked, FileText, ListChecks, MoreHorizontal, Plus, Search, Trash2, Edit } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useRyxHub } from "@/context/RyxHubContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export type SidebarTab = "study" | "exams" | "documents";

type Props = {
  activeTab: SidebarTab;
  onTabChange: (tab: SidebarTab) => void;
  setActiveView: (view: "chat" | "school" | "documents") => void;
};

export function LeftSidebar({ activeTab, onTabChange, setActiveView }: Props) {
  const { sessions, selectedSessionId, selectSession, deleteSession, renameSession } = useRyxHub();
  const [searchQuery, setSearchQuery] = useState("");
  const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions;
    const q = searchQuery.toLowerCase();
    return sessions.filter((s) => s.name.toLowerCase().includes(q));
  }, [sessions, searchQuery]);

  const handleSessionClick = (sessionId: string) => {
    selectSession(sessionId);
    localStorage.setItem(`session-lastused-${sessionId}`, Date.now().toString());
    setActiveView("chat");
  };

  const handleDeleteSession = (sessionId: string, e: MouseEvent) => {
    e.stopPropagation();
    deleteSession(sessionId);
    toast.success("Deleted");
  };

  const handleRenameStart = (sessionId: string, currentName: string, e: MouseEvent) => {
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
    toast.success("Renamed");
    setRenamingSessionId(null);
  };

  const handleNewSession = () => {
    window.dispatchEvent(new CustomEvent("new-session-click"));
  };

  const tabItems: { id: SidebarTab; label: string; icon: ElementType; view: "chat" | "school" | "documents" }[] = [
    { id: "study", label: "Study", icon: BookMarked, view: "chat" },
    { id: "exams", label: "Exams", icon: ListChecks, view: "school" },
    { id: "documents", label: "Documents", icon: FileText, view: "documents" },
  ];

  return (
    <aside className="h-full w-64 bg-sidebar-background border-r border-border flex flex-col">
      {/* New Chat */}
      <div className="p-3">
        <Button
          onClick={handleNewSession}
          variant="ghost"
          className="w-full justify-start gap-2 h-9 rounded-lg"
        >
          <Plus className="w-4 h-4" />
          <span className="text-sm">New Chat</span>
        </Button>
      </div>

      {/* Search */}
      <div className="px-3 pb-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 h-9 bg-transparent border-0 text-sm focus-visible:ring-1 focus-visible:ring-border"
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="px-3 pb-3 space-y-0.5">
        {tabItems.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => {
                onTabChange(tab.id);
                setActiveView(tab.view);
              }}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                active ? "bg-muted font-medium" : "text-muted-foreground hover:bg-muted"
              )}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Sessions List */}
      <ScrollArea className="flex-1">
        <div className="px-3 space-y-0.5">
          {filteredSessions.map((session) => (
            <div
              key={session.id}
              className={cn(
                "group flex items-center gap-2 rounded-lg px-3 py-2 cursor-pointer transition-colors",
                session.id === selectedSessionId ? "bg-muted" : "hover:bg-muted"
              )}
              onClick={() => handleSessionClick(session.id)}
            >
              {renamingSessionId === session.id ? (
                <Input
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onBlur={() => handleRenameSubmit(session.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleRenameSubmit(session.id);
                    if (e.key === "Escape") setRenamingSessionId(null);
                  }}
                  className="h-7 text-sm bg-transparent border-0 p-0 focus-visible:ring-0"
                  autoFocus
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <>
                  <span className="text-sm truncate flex-1">{session.name}</span>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <button
                        className="h-6 w-6 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-border transition-opacity"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <MoreHorizontal className="h-3.5 w-3.5" />
                      </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-32">
                      <DropdownMenuItem onClick={(e) => handleRenameStart(session.id, session.name, e as any)}>
                        <Edit className="mr-2 h-3.5 w-3.5" />
                        Rename
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={(e) => handleDeleteSession(session.id, e as any)}
                        className="text-destructive"
                      >
                        <Trash2 className="mr-2 h-3.5 w-3.5" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </>
              )}
            </div>
          ))}
          {filteredSessions.length === 0 && (
            <p className="px-3 py-8 text-sm text-center text-muted-foreground">No chats</p>
          )}
        </div>
      </ScrollArea>

      {/* Profile */}
      <div className="p-3 border-t border-border">
        <div className="flex items-center gap-3 px-2 py-2">
          <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-medium text-sm">
            T
          </div>
          <span className="text-sm font-medium">Tobi</span>
        </div>
      </div>
    </aside>
  );
}
