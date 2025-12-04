import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
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
import { ryxService } from "@/services/ryxService";

interface NewSessionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSessionCreated?: (sessionId: string) => void;
}

export function NewSessionDialog({ open, onOpenChange, onSessionCreated }: NewSessionDialogProps) {
  const [sessionName, setSessionName] = useState("");
  const [selectedModel, setSelectedModel] = useState("");
  const [models, setModels] = useState<Array<{ id: string; name: string; status: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [loadingModels, setLoadingModels] = useState(false);

  useEffect(() => {
    if (open) {
      loadModels();
      setSessionName(`Session ${new Date().toLocaleTimeString()}`);
    }
  }, [open]);

  const loadModels = async () => {
    setLoadingModels(true);
    try {
      const modelList = await ryxService.listModels();
      setModels(modelList);
      
      // Select first online model by default
      const onlineModel = modelList.find(m => m.status === "online");
      if (onlineModel) {
        setSelectedModel(onlineModel.id);
      } else if (modelList.length > 0) {
        setSelectedModel(modelList[0].id);
      }
    } catch (error) {
      toast.error("Failed to load models");
      console.error(error);
    } finally {
      setLoadingModels(false);
    }
  };

  const handleCreate = async () => {
    if (!sessionName.trim()) {
      toast.error("Please enter a session name");
      return;
    }

    if (!selectedModel) {
      toast.error("Please select a model");
      return;
    }

    setLoading(true);
    try {
      const session = await ryxService.createSession({
        name: sessionName,
        model: selectedModel,
      });

      toast.success(`Session "${session.name}" created successfully!`);
      
      if (onSessionCreated) {
        onSessionCreated(session.id);
      }

      onOpenChange(false);
      
      // Reset form
      setSessionName("");
      setSelectedModel("");
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to create session";
      toast.error("Failed to create session", { description: errorMessage });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[450px]">
        <DialogHeader>
          <DialogTitle>Create New Session</DialogTitle>
          <DialogDescription>
            Start a new conversation session with an AI model
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Session Name */}
          <div className="space-y-2">
            <Label htmlFor="session-name">Session Name</Label>
            <Input
              id="session-name"
              placeholder="e.g., Code Review Session"
              value={sessionName}
              onChange={(e) => setSessionName(e.target.value)}
              disabled={loading}
            />
          </div>

          {/* Model Selection */}
          <div className="space-y-2">
            <Label htmlFor="model-select">AI Model</Label>
            {loadingModels ? (
              <div className="flex items-center justify-center p-4 text-muted-foreground">
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Loading models...
              </div>
            ) : (
              <Select value={selectedModel} onValueChange={setSelectedModel} disabled={loading}>
                <SelectTrigger id="model-select">
                  <SelectValue placeholder="Select a model" />
                </SelectTrigger>
                <SelectContent>
                  {models.map((model) => (
                    <SelectItem key={model.id} value={model.id}>
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-2 h-2 rounded-full ${
                            model.status === "online"
                              ? "bg-[hsl(var(--success))]"
                              : model.status === "loading"
                              ? "bg-[hsl(var(--warning))]"
                              : "bg-muted-foreground"
                          }`}
                        />
                        <span>{model.name}</span>
                        {model.status !== "online" && (
                          <span className="text-xs text-muted-foreground">
                            ({model.status})
                          </span>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {models.length === 0 && !loadingModels && (
              <p className="text-xs text-muted-foreground">
                No models available. Please ensure vLLM is running.
              </p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            disabled={loading || !sessionName.trim() || !selectedModel || loadingModels}
          >
            {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Create Session
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
