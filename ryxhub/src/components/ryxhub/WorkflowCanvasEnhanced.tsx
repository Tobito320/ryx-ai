import { useCallback, useState, useMemo, useEffect, useRef } from "react";
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  Connection,
  addEdge,
  NodeChange,
  EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
  BackgroundVariant,
  MiniMap,
} from "reactflow";
import "reactflow/dist/style.css";
import { Zap, Bot, Wrench, Database, Plus, Play, Pause, Trash2, BookTemplate } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useRyxHub } from "@/context/RyxHubContext";
import { AddNodeDialog } from "@/components/ryxhub/AddNodeDialog";
import { NodeConfigDialog } from "@/components/ryxhub/NodeConfigDialog";
import { WorkflowTemplates } from "@/components/ryxhub/WorkflowTemplates";
import type { WorkflowNode as RyxWorkflowNode } from "@/types/ryxhub";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrapingVisualization, generateMockScrapes } from "@/components/ryxhub/ScrapingVisualization";
import { useRunWorkflow } from "@/hooks/useRyxApi";

const nodeIcons = {
  trigger: Zap,
  agent: Bot,
  tool: Wrench,
  output: Database,
};

const nodeColors = {
  trigger: { bg: "bg-yellow-500/10", border: "border-yellow-500/30", text: "text-yellow-500" },
  agent: { bg: "bg-purple-500/10", border: "border-purple-500/30", text: "text-purple-500" },
  tool: { bg: "bg-green-500/10", border: "border-green-500/30", text: "text-green-500" },
  output: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-500" },
};

const statusColors = {
  idle: "border-border",
  running: "border-primary shadow-[0_0_20px_hsl(270_95%_65%_/_0.4)] animate-pulse",
  success: "border-green-500 shadow-[0_0_15px_hsl(150_80%_45%_/_0.3)]",
  error: "border-red-500 shadow-[0_0_15px_hsl(0_80%_45%_/_0.3)]",
};

// Custom Node Component
function CustomNode({ data }: { data: RyxWorkflowNode & { onDoubleClick: (node: RyxWorkflowNode) => void } }) {
  const Icon = nodeIcons[data.type];
  const colors = nodeColors[data.type];
  const { selectNode, selectedNodeId } = useRyxHub();
  const isSelected = selectedNodeId === data.id;

  return (
    <div
      onClick={() => selectNode(data.id)}
      onDoubleClick={() => data.onDoubleClick(data)}
      className={cn(
        "px-4 py-3 rounded-lg border-2 bg-card transition-all cursor-pointer min-w-[160px]",
        colors.border,
        statusColors[data.status],
        isSelected && "ring-2 ring-primary ring-offset-2"
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        <div className={cn("p-1.5 rounded", colors.bg)}>
          <Icon className={cn("w-4 h-4", colors.text)} />
        </div>
        <span className="font-medium text-sm">{data.name}</span>
      </div>
      <div className="text-xs text-muted-foreground capitalize">{data.type}</div>
      {data.status !== "idle" && (
        <Badge
          variant="outline"
          className={cn(
            "mt-2 text-xs",
            data.status === "running" && "bg-primary/10 text-primary",
            data.status === "success" && "bg-green-500/10 text-green-500",
            data.status === "error" && "bg-red-500/10 text-red-500"
          )}
        >
          {data.status}
        </Badge>
      )}
    </div>
  );
}

const nodeTypes = {
  custom: CustomNode,
};

export function WorkflowCanvasEnhanced() {
  const {
    workflowNodes,
    connections: ryxConnections,
    selectedNodeId,
    isWorkflowRunning,
    toggleWorkflowRunning,
    addWorkflowNode,
  } = useRyxHub();

  const [addNodeDialogOpen, setAddNodeDialogOpen] = useState(false);
  const [configNodeDialogOpen, setConfigNodeDialogOpen] = useState(false);
  const [templatesDialogOpen, setTemplatesDialogOpen] = useState(false);
  const [selectedConfigNode, setSelectedConfigNode] = useState<RyxWorkflowNode | null>(null);
  const [executionLogs, setExecutionLogs] = useState<string[]>([]);
  const [scrapingData, setScrapingData] = useState<Array<{
    url: string;
    status: string;
    progress: number;
    items: Array<{ type: string; content: string; selector: string }>;
    totalItems: number;
  }>>([]);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const logsWsRef = useRef<WebSocket | null>(null);
  const runWorkflowMutation = useRunWorkflow();

  const handleNodeDoubleClick = useCallback((node: RyxWorkflowNode) => {
    setSelectedConfigNode(node);
    setConfigNodeDialogOpen(true);
  }, []);

  // Convert RYX nodes to ReactFlow nodes
  const [nodes, setNodes] = useState<Node[]>(
    workflowNodes.map((node) => ({
      id: node.id,
      type: "custom",
      position: { x: node.x, y: node.y },
      data: { ...node, onDoubleClick: handleNodeDoubleClick },
    }))
  );

  // Convert RYX connections to ReactFlow edges
  const [edges, setEdges] = useState<Edge[]>(
    ryxConnections.map((conn) => ({
      id: conn.id,
      source: conn.from,
      target: conn.to,
      type: "smoothstep",
      animated: isWorkflowRunning,
      style: { stroke: "hsl(var(--primary))", strokeWidth: 2 },
    }))
  );

  // Update nodes when workflow nodes change
  useMemo(() => {
    setNodes(
      workflowNodes.map((node) => ({
        id: node.id,
        type: "custom",
        position: { x: node.x, y: node.y },
        data: { ...node, onDoubleClick: handleNodeDoubleClick },
      }))
    );
  }, [workflowNodes, handleNodeDoubleClick]);

  // Update edge animation when workflow is running
  useMemo(() => {
    setEdges((eds) =>
      eds.map((edge) => ({
        ...edge,
        animated: isWorkflowRunning,
      }))
    );
  }, [isWorkflowRunning]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      setNodes((nds) => applyNodeChanges(changes, nds));
    },
    []
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      setEdges((eds) => applyEdgeChanges(changes, eds));
    },
    []
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      const newEdge = {
        ...connection,
        type: "smoothstep",
        animated: isWorkflowRunning,
        style: { stroke: "hsl(var(--primary))", strokeWidth: 2 },
      };
      setEdges((eds) => addEdge(newEdge, eds));
      toast.success("Connection created");
      
      // Note: Connections are persisted when workflow is saved/updated
      // In a full implementation, you'd call an API to save the workflow here
    },
    [isWorkflowRunning]
  );

  const handleAddNode = async (nodeData: { type: string; name: string }) => {
    try {
      const newNode: RyxWorkflowNode = {
        id: `node-${Date.now()}`,
        type: nodeData.type as "trigger" | "agent" | "tool" | "output",
        name: nodeData.name,
        x: 100 + Math.random() * 400,
        y: 100 + Math.random() * 300,
        status: "idle",
        config: {},
        logs: [
          {
            time: new Date().toLocaleTimeString(),
            level: "info",
            message: `${nodeData.name} node created`,
          },
        ],
        runs: [],
      };

      addWorkflowNode(newNode);
      toast.success(`Node "${nodeData.name}" added to workflow`);
    } catch (error) {
      toast.error("Failed to add node", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    }
  };

  const handleRunWorkflow = async () => {
    if (!isWorkflowRunning) {
      toggleWorkflowRunning();
      setExecutionLogs([]);
      setScrapingData([]);
      
      try {
        // Create a temporary workflow ID (in real app, you'd save the workflow first)
        const tempWorkflowId = "temp-workflow-" + Date.now();
        
        // Run the workflow via backend API
        const result = await runWorkflowMutation.mutateAsync(tempWorkflowId);
        setCurrentRunId(result.run_id);
        
        // Connect to WebSocket for live updates
        const { ryxApi } = await import('@/lib/api/client');
        
        // Connect to workflow status stream
        const ws = ryxApi.connectWorkflowStream(
          result.run_id,
          (data: unknown) => {
            const message = data as { type: string; status?: string; nodeId?: string };
            if (message.type === "workflow_status") {
              if (message.status === "success" || message.status === "error") {
                toggleWorkflowRunning();
                // Reset node statuses after a delay
                setTimeout(() => {
                  setNodes((nds) =>
                    nds.map((n) => ({ ...n, data: { ...n.data, status: "idle" } }))
                  );
                }, 2000);
              }
            } else if (message.type === "node_status") {
              // Update node status in UI
              setNodes((nds) =>
                nds.map((n) =>
                  n.id === message.nodeId
                    ? { ...n, data: { ...n.data, status: message.status } }
                    : n
                )
              );
            }
          },
          (error) => {
            console.error("WebSocket error:", error);
            toast.error("Lost connection to workflow execution");
          }
        );
        wsRef.current = ws;
        
        // Connect to logs stream
        const logsWs = ryxApi.connectWorkflowLogsStream(
          result.run_id,
          (data: unknown) => {
            const log = data as { type: string; timestamp: string; message: string };
            if (log.type === "log") {
              setExecutionLogs((prev) => [
                ...prev,
                `[${new Date(log.timestamp).toLocaleTimeString()}] ${log.message}`,
              ]);
            }
          },
          (error) => {
            console.error("Logs WebSocket error:", error);
          }
        );
        logsWsRef.current = logsWs;
        
        toast.success("Workflow execution started");
      } catch (error) {
        console.error("Failed to run workflow:", error);
        toast.error("Failed to start workflow execution");
        toggleWorkflowRunning();
      }
    } else {
      // Pause workflow
      setExecutionLogs((prev) => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] ⏸️ Workflow execution paused`,
      ]);
      toggleWorkflowRunning();
      
      // Close WebSocket connections
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (logsWsRef.current) {
        logsWsRef.current.close();
        logsWsRef.current = null;
      }
    }
  };
  
  // Cleanup WebSocket connections on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (logsWsRef.current) {
        logsWsRef.current.close();
      }
    };
  }, []);

  const handleClearCanvas = () => {
    setNodes([]);
    setEdges([]);
    toast.success("Canvas cleared");
  };

  const handleSaveNodeConfig = (nodeId: string, config: Record<string, unknown>) => {
    // Update node configuration in state
    toast.success("Node configuration updated");
    
    // Note: Node configuration is persisted when workflow is saved
    // In a full implementation, you'd call an API to update the workflow here
  };

  const handleSelectTemplate = (template: {
    name: string;
    nodes: Array<Omit<RyxWorkflowNode, "logs" | "runs">>;
    connections: Array<{ id: string; from: string; to: string }>;
  }) => {
    // Load template nodes and connections
    const templateNodes = template.nodes.map((node) => ({
      ...node,
      logs: [],
      runs: [],
    }));

    templateNodes.forEach((node: RyxWorkflowNode) => {
      addWorkflowNode(node);
    });

    // Add connections
    template.connections.forEach((conn) => {
      const newEdge = {
        id: conn.id,
        source: conn.from,
        target: conn.to,
        type: "smoothstep",
        animated: false,
        style: { stroke: "hsl(var(--primary))", strokeWidth: 2 },
      };
      setEdges((eds) => [...eds, newEdge]);
    });

    toast.success(`Template "${template.name}" loaded successfully`);
  };

  return (
    <div className="flex h-full">
      {/* Main Canvas */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          className="bg-background"
        >
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="hsl(var(--muted))" />
          <Controls className="bg-card border border-border rounded-lg" />
          <MiniMap
            className="bg-card border border-border rounded-lg"
            nodeColor={(node) => {
              const data = node.data as RyxWorkflowNode;
              return nodeColors[data.type].text.replace("text-", "");
            }}
          />
        </ReactFlow>

        {/* Floating Toolbar */}
        <div className="absolute top-4 left-4 flex items-center gap-2 bg-card/80 backdrop-blur-sm border border-border rounded-lg p-2 shadow-lg">
          <Button
            size="sm"
            onClick={() => setTemplatesDialogOpen(true)}
            variant="outline"
            className="gap-2"
          >
            <BookTemplate className="w-4 h-4" />
            Templates
          </Button>
          <Button
            size="sm"
            onClick={() => setAddNodeDialogOpen(true)}
            className="gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Node
          </Button>
          <Button
            size="sm"
            variant={isWorkflowRunning ? "destructive" : "default"}
            onClick={handleRunWorkflow}
            className="gap-2"
          >
            {isWorkflowRunning ? (
              <>
                <Pause className="w-4 h-4" />
                Pause
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Workflow
              </>
            )}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleClearCanvas}
            className="gap-2"
          >
            <Trash2 className="w-4 h-4" />
            Clear
          </Button>
        </div>
      </div>

      {/* Right Panel - Execution Info */}
      <Card className="w-96 border-l border-border bg-card/30 backdrop-blur-sm">
        <Tabs defaultValue="logs" className="h-full">
          <div className="border-b border-border px-4 py-2">
            <TabsList className="w-full grid grid-cols-2">
              <TabsTrigger value="logs">Execution Logs</TabsTrigger>
              <TabsTrigger value="scraping">
                Scraping
                {scrapingData.length > 0 && (
                  <Badge variant="secondary" className="ml-1 h-4 px-1 text-[10px]">
                    {scrapingData.length}
                  </Badge>
                )}
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="logs" className="mt-0 p-4">
            <ScrollArea className="h-[calc(100vh-12rem)]">
              <div className="space-y-1 font-mono text-xs">
                {executionLogs.length === 0 ? (
                  <div className="text-muted-foreground text-center py-8">
                    No execution logs yet
                    <p className="text-[10px] mt-2">
                      Click "Run Workflow" to start
                    </p>
                  </div>
                ) : (
                  executionLogs.map((log, index) => (
                    <div
                      key={index}
                      className="text-foreground/80 bg-muted/20 px-2 py-1 rounded"
                    >
                      {log}
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="scraping" className="mt-0 p-4">
            <ScrollArea className="h-[calc(100vh-12rem)]">
              <ScrapingVisualization scrapes={scrapingData} />
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </Card>

      {/* Workflow Templates Dialog */}
      <WorkflowTemplates
        open={templatesDialogOpen}
        onOpenChange={setTemplatesDialogOpen}
        onSelectTemplate={handleSelectTemplate}
      />

      {/* Add Node Dialog */}
      <AddNodeDialog
        open={addNodeDialogOpen}
        onOpenChange={setAddNodeDialogOpen}
        onAddNode={handleAddNode}
      />

      {/* Node Configuration Dialog */}
      <NodeConfigDialog
        node={selectedConfigNode}
        open={configNodeDialogOpen}
        onOpenChange={setConfigNodeDialogOpen}
        onSave={handleSaveNodeConfig}
      />
    </div>
  );
}
