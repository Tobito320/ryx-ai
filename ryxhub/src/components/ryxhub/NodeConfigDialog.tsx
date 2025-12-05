import { useState, useEffect } from "react";
import { Settings2, Zap, Bot, Wrench, Database } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { WorkflowNode } from "@/types/ryxhub";
import { toast } from "sonner";

interface NodeConfigDialogProps {
  node: WorkflowNode | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (nodeId: string, config: Record<string, unknown>) => void;
}

const nodeIcons = {
  trigger: Zap,
  agent: Bot,
  tool: Wrench,
  output: Database,
};

export function NodeConfigDialog({ node, open, onOpenChange, onSave }: NodeConfigDialogProps) {
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [nodeName, setNodeName] = useState("");

  useEffect(() => {
    if (node) {
      setConfig(node.config || {});
      setNodeName(node.name);
    }
  }, [node]);

  if (!node) return null;

  const Icon = nodeIcons[node.type];

  const handleSave = () => {
    onSave(node.id, { ...config, name: nodeName });
    toast.success("Node configuration saved");
    onOpenChange(false);
  };

  const updateConfig = (key: string, value: unknown) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Icon className="w-5 h-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Configure {node.type.charAt(0).toUpperCase() + node.type.slice(1)} Node</DialogTitle>
              <DialogDescription>
                Customize the behavior and settings for this node
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <Tabs defaultValue="general" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="config">Configuration</TabsTrigger>
            <TabsTrigger value="advanced">Advanced</TabsTrigger>
          </TabsList>

          {/* General Tab */}
          <TabsContent value="general" className="space-y-4 pt-4">
            <div className="space-y-2">
              <Label htmlFor="node-name">Node Name</Label>
              <Input
                id="node-name"
                value={nodeName}
                onChange={(e) => setNodeName(e.target.value)}
                placeholder="Enter node name"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="node-description">Description</Label>
              <Textarea
                id="node-description"
                value={(config.description as string) || ""}
                onChange={(e) => updateConfig("description", e.target.value)}
                placeholder="Describe what this node does"
                rows={3}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Enabled</Label>
                <p className="text-xs text-muted-foreground">
                  Whether this node is active in the workflow
                </p>
              </div>
              <Switch
                checked={(config.enabled as boolean) ?? true}
                onCheckedChange={(checked) => updateConfig("enabled", checked)}
              />
            </div>
          </TabsContent>

          {/* Configuration Tab */}
          <TabsContent value="config" className="space-y-4 pt-4">
            {node.type === "trigger" && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="trigger-type">Trigger Type</Label>
                  <Select
                    value={(config.triggerType as string) || "manual"}
                    onValueChange={(value) => updateConfig("triggerType", value)}
                  >
                    <SelectTrigger id="trigger-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="manual">Manual</SelectItem>
                      <SelectItem value="schedule">Scheduled</SelectItem>
                      <SelectItem value="webhook">Webhook</SelectItem>
                      <SelectItem value="file">File Watch</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {config.triggerType === "schedule" && (
                  <div className="space-y-2">
                    <Label htmlFor="cron">Cron Expression</Label>
                    <Input
                      id="cron"
                      value={(config.cron as string) || ""}
                      onChange={(e) => updateConfig("cron", e.target.value)}
                      placeholder="0 0 * * *"
                    />
                    <p className="text-xs text-muted-foreground">
                      Define when this workflow should run
                    </p>
                  </div>
                )}
              </>
            )}

            {node.type === "agent" && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="model">AI Model</Label>
                  <Select
                    value={(config.model as string) || "qwen2.5-coder:14b"}
                    onValueChange={(value) => updateConfig("model", value)}
                  >
                    <SelectTrigger id="model">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="qwen2.5-coder:14b">Qwen 2.5 Coder 14B</SelectItem>
                      <SelectItem value="mistral:7b">Mistral 7B</SelectItem>
                      <SelectItem value="deepseek-coder-v2:16b">DeepSeek Coder V2 16B</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="prompt">System Prompt</Label>
                  <Textarea
                    id="prompt"
                    value={(config.prompt as string) || ""}
                    onChange={(e) => updateConfig("prompt", e.target.value)}
                    placeholder="Enter the system prompt for this agent"
                    rows={5}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="temperature">Temperature: {(config.temperature as number) || 0.7}</Label>
                  <input
                    type="range"
                    id="temperature"
                    min="0"
                    max="2"
                    step="0.1"
                    value={(config.temperature as number) || 0.7}
                    onChange={(e) => updateConfig("temperature", parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>
              </>
            )}

            {node.type === "tool" && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="tool-type">Tool Type</Label>
                  <Select
                    value={(config.toolType as string) || "websearch"}
                    onValueChange={(value) => updateConfig("toolType", value)}
                  >
                    <SelectTrigger id="tool-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="websearch">Web Search (SearXNG)</SelectItem>
                      <SelectItem value="scrape">Web Scraper</SelectItem>
                      <SelectItem value="rag">RAG Query</SelectItem>
                      <SelectItem value="filesystem">File System</SelectItem>
                      <SelectItem value="shell">Shell Command</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="tool-params">Tool Parameters (JSON)</Label>
                  <Textarea
                    id="tool-params"
                    value={(config.params as string) || "{}"}
                    onChange={(e) => updateConfig("params", e.target.value)}
                    placeholder='{"query": "example"}'
                    rows={4}
                    className="font-mono text-xs"
                  />
                </div>
              </>
            )}

            {node.type === "output" && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="output-format">Output Format</Label>
                  <Select
                    value={(config.format as string) || "json"}
                    onValueChange={(value) => updateConfig("format", value)}
                  >
                    <SelectTrigger id="output-format">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="json">JSON</SelectItem>
                      <SelectItem value="text">Plain Text</SelectItem>
                      <SelectItem value="markdown">Markdown</SelectItem>
                      <SelectItem value="html">HTML</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="output-destination">Destination</Label>
                  <Input
                    id="output-destination"
                    value={(config.destination as string) || ""}
                    onChange={(e) => updateConfig("destination", e.target.value)}
                    placeholder="/path/to/output.json"
                  />
                </div>
              </>
            )}
          </TabsContent>

          {/* Advanced Tab */}
          <TabsContent value="advanced" className="space-y-4 pt-4">
            <div className="space-y-2">
              <Label htmlFor="timeout">Timeout (seconds)</Label>
              <Input
                id="timeout"
                type="number"
                value={(config.timeout as number) || 30}
                onChange={(e) => updateConfig("timeout", parseInt(e.target.value))}
                min={1}
                max={300}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="retries">Retry Attempts</Label>
              <Input
                id="retries"
                type="number"
                value={(config.retries as number) || 3}
                onChange={(e) => updateConfig("retries", parseInt(e.target.value))}
                min={0}
                max={10}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Continue on Error</Label>
                <p className="text-xs text-muted-foreground">
                  Continue workflow execution even if this node fails
                </p>
              </div>
              <Switch
                checked={(config.continueOnError as boolean) ?? false}
                onCheckedChange={(checked) => updateConfig("continueOnError", checked)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="error-handler">Error Handler</Label>
              <Textarea
                id="error-handler"
                value={(config.errorHandler as string) || ""}
                onChange={(e) => updateConfig("errorHandler", e.target.value)}
                placeholder="Custom error handling logic"
                rows={3}
              />
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            <Settings2 className="w-4 h-4 mr-2" />
            Save Configuration
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
