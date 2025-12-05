import { useCallback, useState } from "react";
import { Zap, Bot, Wrench, Database, Plus, Play, Pause } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useRyxHub } from "@/context/RyxHubContext";
import { AddNodeDialog } from "@/components/ryxhub/AddNodeDialog";
import type { WorkflowNode } from "@/types/ryxhub";
import { toast } from "sonner";

const nodeIcons = {
  trigger: Zap,
  agent: Bot,
  tool: Wrench,
  output: Database,
};

const nodeColors = {
  trigger: "from-[hsl(var(--warning))] to-[hsl(45_100%_45%)]",
  agent: "from-primary to-[hsl(320_90%_60%)]",
  tool: "from-accent to-[hsl(150_80%_50%)]",
  output: "from-secondary to-muted",
};

const statusColors = {
  idle: "border-border",
  running: "border-primary shadow-[0_0_20px_hsl(270_95%_65%_/_0.4)]",
  success: "border-[hsl(var(--success))] shadow-[0_0_15px_hsl(150_80%_45%_/_0.3)]",
  error: "border-destructive",
};

export function WorkflowCanvas() {
  const {
    workflowNodes,
    connections,
    selectedNodeId,
    selectNode,
    isWorkflowRunning,
    toggleWorkflowRunning,
  } = useRyxHub();

  const [addNodeDialogOpen, setAddNodeDialogOpen] = useState(false);

  const getNodePosition = useCallback(
    (nodeId: string) => {
      const node = workflowNodes.find((n) => n.id === nodeId);
      return node ? { x: node.x + 80, y: node.y + 30 } : { x: 0, y: 0 };
    },
    [workflowNodes]
  );

  const handleNodeClick = (node: WorkflowNode) => {
    selectNode(node.id === selectedNodeId ? null : node.id);
  };

  const handleAddNode = async (nodeData: { type: string; name: string }) => {
    try {
      // In a full implementation, this would add the node to the workflow
      // For now, we'll show success and indicate nodes can be added
      const newNode = {
        id: `node-${Date.now()}`,
        type: nodeData.type as "trigger" | "agent" | "tool" | "output",
        name: nodeData.name,
        x: 100 + Math.random() * 200,
        y: 100 + Math.random() * 200,
        status: "idle" as const,
        config: {},
        logs: [],
        runs: []
      };

      // Note: In a real implementation, this would update the workflow state
      // and persist to the backend via PUT /api/workflows/:id
      toast.success(`Node "${nodeData.name}" added to workflow`, {
        description: "Node created successfully"
      });
      
      // TODO: Actually add to workflowNodes state and persist to backend
      console.log("New node:", newNode);
    } catch (error) {
      toast.error("Failed to add node", {
        description: error instanceof Error ? error.message : "Unknown error"
      });
    }
  };

  const runningCount = workflowNodes.filter((n) => n.status === "running").length;
  const successCount = workflowNodes.filter((n) => n.status === "success").length;

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Canvas Header */}
      <div className="px-6 py-4 border-b border-border bg-card/50 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-foreground">PR Review Workflow</h2>
            <p className="text-xs text-muted-foreground">
              {workflowNodes.length} nodes • {connections.length} connections •{" "}
              {successCount} completed • {runningCount} running
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="secondary" 
              size="sm"
              onClick={() => setAddNodeDialogOpen(true)}
            >
              <Plus className="w-4 h-4 mr-1.5" />
              Add Node
            </Button>
            <Button
              size="sm"
              variant={isWorkflowRunning ? "destructive" : "default"}
              onClick={toggleWorkflowRunning}
            >
              {isWorkflowRunning ? (
                <>
                  <Pause className="w-4 h-4 mr-1.5" />
                  Pause
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-1.5" />
                  Run
                </>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Canvas Area */}
      <div className="flex-1 relative overflow-hidden">
        {/* Grid Background */}
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage: `
              linear-gradient(hsl(var(--border)) 1px, transparent 1px),
              linear-gradient(90deg, hsl(var(--border)) 1px, transparent 1px)
            `,
            backgroundSize: "40px 40px",
          }}
        />

        {/* SVG Connections */}
        <svg className="absolute inset-0 pointer-events-none" width="100%" height="100%">
          <defs>
            <linearGradient id="connectionGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.6" />
              <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity="0.6" />
            </linearGradient>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon
                points="0 0, 10 3.5, 0 7"
                fill="hsl(var(--primary))"
                opacity="0.6"
              />
            </marker>
          </defs>
          {connections.map((conn) => {
            const from = getNodePosition(conn.from);
            const to = getNodePosition(conn.to);
            const midX = (from.x + to.x) / 2;
            return (
              <path
                key={conn.id}
                d={`M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x - 10} ${to.y}`}
                stroke="url(#connectionGradient)"
                strokeWidth="2"
                fill="none"
                markerEnd="url(#arrowhead)"
                className="transition-all duration-300"
              />
            );
          })}
        </svg>

        {/* Nodes */}
        {workflowNodes.map((node) => {
          const Icon = nodeIcons[node.type];
          const isSelected = node.id === selectedNodeId;
          return (
            <button
              key={node.id}
              onClick={() => handleNodeClick(node)}
              className={cn(
                "absolute w-40 p-3 rounded-xl border-2 bg-card backdrop-blur-sm transition-all duration-200 hover:scale-105 cursor-pointer text-left",
                statusColors[node.status],
                isSelected && "ring-2 ring-primary ring-offset-2 ring-offset-background scale-105"
              )}
              style={{ left: node.x, top: node.y }}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <div
                  className={cn(
                    "w-7 h-7 rounded-lg bg-gradient-to-br flex items-center justify-center",
                    nodeColors[node.type]
                  )}
                >
                  <Icon className="w-4 h-4 text-primary-foreground" />
                </div>
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                  {node.type}
                </span>
              </div>
              <p className="text-sm font-medium text-foreground truncate">{node.name}</p>
              {node.status === "running" && (
                <div className="mt-2 h-1 rounded-full bg-muted overflow-hidden">
                  <div className="h-full w-1/2 bg-primary rounded-full animate-pulse" />
                </div>
              )}
              {node.status === "success" && (
                <div className="mt-2 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[hsl(var(--success))]" />
                  <span className="text-[10px] text-[hsl(var(--success))]">Complete</span>
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Canvas Footer */}
      <div className="px-6 py-3 border-t border-border bg-card/30 flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[hsl(var(--success))]" />
            Success ({successCount})
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            Running ({runningCount})
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-muted" />
            Idle ({workflowNodes.filter((n) => n.status === "idle").length})
          </span>
        </div>
        <span className="text-xs text-muted-foreground">
          Click a node to inspect • {selectedNodeId ? "Node selected" : "No selection"}
        </span>
      </div>

      {/* Dialogs */}
      <AddNodeDialog
        open={addNodeDialogOpen}
        onOpenChange={setAddNodeDialogOpen}
        onNodeAdd={handleAddNode}
      />
    </div>
  );
}
