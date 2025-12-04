import { useState } from "react";
import { Bot, Wrench, Database, Zap } from "lucide-react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

interface AddNodeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onNodeAdd?: (nodeData: { type: string; name: string }) => void;
}

const nodeTypes = [
  { value: "trigger", label: "Trigger", icon: Zap, description: "Start workflow on event" },
  { value: "agent", label: "Agent", icon: Bot, description: "AI agent processing" },
  { value: "tool", label: "Tool", icon: Wrench, description: "Execute tool action" },
  { value: "output", label: "Output", icon: Database, description: "Store or display result" },
];

export function AddNodeDialog({ open, onOpenChange, onNodeAdd }: AddNodeDialogProps) {
  const [nodeName, setNodeName] = useState("");
  const [nodeType, setNodeType] = useState<string>("");

  const handleAdd = () => {
    if (!nodeName.trim()) {
      toast.error("Please enter a node name");
      return;
    }

    if (!nodeType) {
      toast.error("Please select a node type");
      return;
    }

    if (onNodeAdd) {
      onNodeAdd({ type: nodeType, name: nodeName });
    }

    toast.success(`Node "${nodeName}" added to workflow`);
    
    // Reset form
    setNodeName("");
    setNodeType("");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Add Workflow Node</DialogTitle>
          <DialogDescription>
            Add a new node to your workflow
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Node Type Selection */}
          <div className="space-y-2">
            <Label htmlFor="node-type">Node Type</Label>
            <Select value={nodeType} onValueChange={setNodeType}>
              <SelectTrigger id="node-type">
                <SelectValue placeholder="Select node type" />
              </SelectTrigger>
              <SelectContent>
                {nodeTypes.map((type) => {
                  const Icon = type.icon;
                  return (
                    <SelectItem key={type.value} value={type.value}>
                      <div className="flex items-center gap-2">
                        <Icon className="w-4 h-4" />
                        <div className="flex flex-col">
                          <span className="font-medium">{type.label}</span>
                          <span className="text-xs text-muted-foreground">
                            {type.description}
                          </span>
                        </div>
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          </div>

          {/* Node Name */}
          <div className="space-y-2">
            <Label htmlFor="node-name">Node Name</Label>
            <Input
              id="node-name"
              placeholder="e.g., Code Analyzer, Web Scraper"
              value={nodeName}
              onChange={(e) => setNodeName(e.target.value)}
            />
          </div>

          {/* Preview */}
          {nodeType && nodeName && (
            <div className="p-4 rounded-lg bg-muted/30 border border-border">
              <p className="text-xs text-muted-foreground mb-2">Preview:</p>
              <div className="flex items-center gap-2">
                {(() => {
                  const selectedType = nodeTypes.find(t => t.value === nodeType);
                  const Icon = selectedType?.icon || Bot;
                  return <Icon className="w-4 h-4 text-primary" />;
                })()}
                <span className="text-sm font-medium">{nodeName}</span>
                <span className="text-xs text-muted-foreground">
                  ({nodeTypes.find(t => t.value === nodeType)?.label})
                </span>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleAdd} disabled={!nodeName.trim() || !nodeType}>
            Add Node
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
