import { useState } from "react";
import { Search, Database, Globe, FileText, Wrench } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface ToolConfig {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  enabled: boolean;
}

interface ToolsPanelProps {
  tools: ToolConfig[];
  onToolToggle: (toolId: string, enabled: boolean) => void;
}

export function ToolsPanel({ tools, onToolToggle }: ToolsPanelProps) {
  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Wrench className="w-4 h-4 text-primary" />
          Active Tools
        </CardTitle>
        <CardDescription className="text-xs">
          Toggle tools for this chat session
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {tools.map((tool) => {
          const Icon = tool.icon;
          return (
            <div
              key={tool.id}
              className={cn(
                "flex items-center justify-between p-3 rounded-lg transition-all",
                "border border-border/50",
                tool.enabled ? "bg-primary/5 border-primary/30" : "bg-muted/20"
              )}
            >
              <div className="flex items-center gap-3 flex-1">
                <div
                  className={cn(
                    "p-2 rounded-md",
                    tool.enabled ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                  )}
                >
                  <Icon className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Label
                      htmlFor={`tool-${tool.id}`}
                      className="text-sm font-medium cursor-pointer"
                    >
                      {tool.name}
                    </Label>
                    {tool.enabled && (
                      <Badge
                        variant="outline"
                        className="h-5 px-1.5 text-xs bg-primary/10 text-primary border-primary/30"
                      >
                        Active
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {tool.description}
                  </p>
                </div>
              </div>
              <Switch
                id={`tool-${tool.id}`}
                checked={tool.enabled}
                onCheckedChange={(checked) => onToolToggle(tool.id, checked)}
                className="ml-3"
              />
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

export const defaultTools: ToolConfig[] = [
  {
    id: "websearch",
    name: "Web Search",
    description: "Search the web using SearXNG",
    icon: Search,
    enabled: true,
  },
  {
    id: "rag",
    name: "RAG Database",
    description: "Query indexed documents",
    icon: Database,
    enabled: true,
  },
  {
    id: "scrape",
    name: "Web Scraper",
    description: "Extract content from websites",
    icon: Globe,
    enabled: false,
  },
  {
    id: "filesystem",
    name: "File System",
    description: "Read and write local files",
    icon: FileText,
    enabled: true,
  },
];
