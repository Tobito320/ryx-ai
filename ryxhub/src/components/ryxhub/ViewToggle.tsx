import { MessageSquare, GitBranch, LayoutDashboard, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { useRyxHub } from "@/context/RyxHubContext";
import type { ViewMode } from "@/types/ryxhub";

const views: { id: ViewMode; label: string; icon: typeof LayoutDashboard }[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "workflow", label: "Workflow", icon: GitBranch },
  { id: "settings", label: "Settings", icon: Settings },
];

export function ViewToggle() {
  const { activeView, setActiveView } = useRyxHub();

  return (
    <div className="flex items-center bg-card border border-border rounded-lg p-0.5">
      {views.map((view) => {
        const Icon = view.icon;
        const isActive = activeView === view.id;
        return (
          <button
            key={view.id}
            onClick={() => setActiveView(view.id)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
              isActive
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            )}
          >
            <Icon className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{view.label}</span>
          </button>
        );
      })}
    </div>
  );
}
