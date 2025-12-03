import { X, Play, Clock, CheckCircle, AlertCircle, Settings, Activity, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { useRyxHub } from "@/context/RyxHubContext";
import { toast } from "sonner";

export function RightInspector() {
  const { workflowNodes, selectedNodeId, selectNode } = useRyxHub();

  const node = workflowNodes.find((n) => n.id === selectedNodeId);

  const handleClose = () => {
    selectNode(null);
  };

  const handleRunNode = () => {
    toast.success(`Running ${node?.name}...`);
  };

  const handleEditConfig = () => {
    toast.info("Configuration editor would open here");
  };

  if (!node) {
    return (
      <aside className="w-80 bg-sidebar border-l border-sidebar-border flex flex-col h-full">
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <div className="w-16 h-16 rounded-2xl bg-muted/50 flex items-center justify-center mx-auto mb-4">
              <Settings className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="text-sm font-medium text-foreground mb-1">No Selection</h3>
            <p className="text-xs text-muted-foreground">
              Select a node in the workflow canvas to view its details
            </p>
          </div>
        </div>
      </aside>
    );
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "success":
        return <CheckCircle className="w-4 h-4 text-[hsl(var(--success))]" />;
      case "error":
        return <AlertCircle className="w-4 h-4 text-destructive" />;
      case "running":
        return <Activity className="w-4 h-4 text-primary animate-pulse" />;
      default:
        return <Clock className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getLogLevelColor = (level: string) => {
    switch (level) {
      case "success":
        return "text-[hsl(var(--success))]";
      case "warning":
        return "text-[hsl(var(--warning))]";
      case "error":
        return "text-destructive";
      default:
        return "text-muted-foreground";
    }
  };

  return (
    <aside className="w-80 bg-sidebar border-l border-sidebar-border flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-sidebar-border">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
            {node.type}
          </span>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>
        <h3 className="text-lg font-semibold text-foreground">{node.name}</h3>
        <div className="flex items-center gap-2 mt-2">
          {getStatusIcon(node.status)}
          <span
            className={cn(
              "text-xs capitalize",
              node.status === "success" && "text-[hsl(var(--success))]",
              node.status === "error" && "text-destructive",
              node.status === "running" && "text-primary",
              node.status === "idle" && "text-muted-foreground"
            )}
          >
            {node.status}
          </span>
          {node.runs.length > 0 && (
            <span className="text-xs text-muted-foreground">
              • Last run: {node.runs[0].timestamp}
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="params" className="flex-1 flex flex-col">
        <TabsList className="w-full justify-start rounded-none border-b border-sidebar-border bg-transparent px-4 h-10">
          <TabsTrigger value="params" className="text-xs data-[state=active]:bg-muted">
            <Settings className="w-3.5 h-3.5 mr-1.5" />
            Params
          </TabsTrigger>
          <TabsTrigger value="logs" className="text-xs data-[state=active]:bg-muted">
            <FileText className="w-3.5 h-3.5 mr-1.5" />
            Logs ({node.logs.length})
          </TabsTrigger>
          <TabsTrigger value="runs" className="text-xs data-[state=active]:bg-muted">
            <Activity className="w-3.5 h-3.5 mr-1.5" />
            Runs ({node.runs.length})
          </TabsTrigger>
        </TabsList>

        <ScrollArea className="flex-1">
          <TabsContent value="params" className="m-0 p-4">
            <div className="space-y-3">
              {Object.entries(node.config).map(([key, value]) => (
                <div
                  key={key}
                  className="flex justify-between items-center py-2 border-b border-border last:border-0"
                >
                  <span className="text-xs text-muted-foreground capitalize">
                    {key.replace(/([A-Z])/g, " $1").trim()}
                  </span>
                  <span className="text-xs font-mono text-foreground max-w-[150px] truncate">
                    {typeof value === "boolean"
                      ? value
                        ? "true"
                        : "false"
                      : Array.isArray(value)
                      ? value.join(", ")
                      : String(value)}
                  </span>
                </div>
              ))}
            </div>
            <Button variant="secondary" size="sm" className="w-full mt-4" onClick={handleEditConfig}>
              <Settings className="w-4 h-4 mr-1.5" />
              Edit Configuration
            </Button>
          </TabsContent>

          <TabsContent value="logs" className="m-0 p-4">
            {node.logs.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-8">No logs available</p>
            ) : (
              <div className="space-y-2 font-mono text-[11px]">
                {node.logs.map((log, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-muted-foreground shrink-0">{log.time}</span>
                    <span className={cn("shrink-0", getLogLevelColor(log.level))}>
                      [{log.level.toUpperCase()}]
                    </span>
                    <span className="text-foreground break-all">{log.message}</span>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="runs" className="m-0 p-4">
            {node.runs.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-8">No run history</p>
            ) : (
              <div className="space-y-2">
                {node.runs.map((run) => (
                  <div
                    key={run.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-border"
                  >
                    <div className="flex items-center gap-2">
                      {getStatusIcon(run.status)}
                      <div>
                        <p className="text-xs font-medium text-foreground">{run.id}</p>
                        <p className="text-[10px] text-muted-foreground">{run.timestamp}</p>
                      </div>
                    </div>
                    <span className="text-xs font-mono text-muted-foreground">{run.duration}</span>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>
        </ScrollArea>
      </Tabs>

      {/* Footer Actions */}
      <div className="p-4 border-t border-sidebar-border">
        <Button className="w-full" size="sm" onClick={handleRunNode}>
          <Play className="w-4 h-4 mr-1.5" />
          Run Node
        </Button>
      </div>
    </aside>
  );
}
