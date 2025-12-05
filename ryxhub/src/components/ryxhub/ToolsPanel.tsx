import { Search, Database, Globe, FileText, Wrench } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

export interface ToolConfig {
  id: string;
  name: string;
  description: string;
  icon: string | React.ComponentType<{ className?: string }>;
  enabled: boolean;
}

interface ToolsPanelProps {
  tools: ToolConfig[];
  onToolToggle: (toolId: string, enabled: boolean) => void;
  compact?: boolean;
}

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  Search, Database, Globe, FileText, Wrench,
};

export function ToolsPanel({ tools, onToolToggle, compact }: ToolsPanelProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-2">
        <Wrench className="w-3 h-3" />
        Tools
      </div>
      {tools.map((tool) => {
        const Icon = typeof tool.icon === 'string' ? iconMap[tool.icon] || Wrench : tool.icon;
        return (
          <div
            key={tool.id}
            className={cn(
              "flex items-center justify-between rounded-md transition-all",
              compact ? "p-1.5" : "p-2",
              tool.enabled ? "bg-primary/5" : "bg-transparent"
            )}
          >
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <Icon className={cn("flex-shrink-0", compact ? "w-3 h-3" : "w-4 h-4", tool.enabled ? "text-primary" : "text-muted-foreground")} />
              <div className="flex-1 min-w-0">
                <span className={cn("font-medium", compact ? "text-xs" : "text-sm")}>{tool.name}</span>
                {!compact && <p className="text-xs text-muted-foreground truncate">{tool.description}</p>}
              </div>
            </div>
            <Switch
              checked={tool.enabled}
              onCheckedChange={(checked) => onToolToggle(tool.id, checked)}
              className={compact ? "scale-75" : ""}
            />
          </div>
        );
      })}
    </div>
  );
}

export const defaultTools: ToolConfig[] = [
  { id: "websearch", name: "Web Search", description: "Search the web", icon: "Search", enabled: true },
  { id: "rag", name: "RAG", description: "Query knowledge base", icon: "Database", enabled: true },
  { id: "scrape", name: "Scraper", description: "Extract from websites", icon: "Globe", enabled: false },
  { id: "filesystem", name: "Files", description: "Read/write files", icon: "FileText", enabled: false },
];
