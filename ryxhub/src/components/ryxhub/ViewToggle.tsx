import { MessageSquare, GitBranch, LayoutDashboard, Settings, Users } from "lucide-react";
import { cn } from "@/lib/utils";
import { useRyxHub } from "@/context/RyxHubContext";
import type { ViewMode } from "@/types/ryxhub";

const views: { id: ViewMode; label: string; icon: typeof LayoutDashboard }[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "workflow", label: "Workflow", icon: GitBranch },
  { id: "council", label: "Council", icon: Users },
  { id: "settings", label: "Settings", icon: Settings },
];

export function ViewToggle() {
  const { activeView, setActiveView } = useRyxHub();

  return (
    <div className="flex items-center bg-card border border-border rounded-xl p-1">
      {views.map((view) => {
        const Icon = view.icon;
        const isActive = activeView === view.id;
        return (
          <button
            key={view.id}
            onClick={() => setActiveView(view.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
              isActive
                ? "bg-primary text-primary-foreground shadow-lg"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            )}
          >
            <Icon className="w-4 h-4" />
            <span className="hidden sm:inline">{view.label}</span>
          </button>
        );
      })}
    </div>
  );
}
