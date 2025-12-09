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

// Response styles matching ryx CLI
const RESPONSE_STYLES = [
  { id: "normal", name: "Normal", description: "Balanced, helpful responses" },
  { id: "concise", name: "Concise", description: "Short, to the point" },
  { id: "explanatory", name: "Explanatory", description: "Detailed with examples" },
  { id: "learning", name: "Learning", description: "Step-by-step teaching" },
  { id: "formal", name: "Formal", description: "Professional language" },
];

interface NewSessionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSessionCreated?: (sessionId: string) => void;
}

export function NewSessionDialog({ open, onOpenChange, onSessionCreated }: NewSessionDialogProps) {
  const [sessionName, setSessionName] = useState("");
  const [selectedModel, setSelectedModel] = useState("");
  const [selectedStyle, setSelectedStyle] = useState("normal");
  const [models, setModels] = useState<Array<{ id: string; name: string; status: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [loadingModels, setLoadingModels] = useState(false);

  useEffect(() => {
    if (open) {
      loadModels();
      setSessionName(`Session ${new Date().toLocaleTimeString()}`);
      setSelectedStyle("normal");
    }
  }, [open]);

  const loadModels = async () => {
    setLoadingModels(true);
    try {
      const modelList = await ryxService.listModels();
      // Sort: loaded first, then by name
      const sorted = [...modelList].sort((a, b) => {
        if (a.status === "loaded" && b.status !== "loaded") return -1;
        if (a.status !== "loaded" && b.status === "loaded") return 1;
        return a.name.localeCompare(b.name);
      });
      setModels(sorted);
      
      // Select first loaded model
      const loadedModel = sorted.find(m => m.status === "loaded");
      if (loadedModel) {
        setSelectedModel(loadedModel.id);
      } else if (sorted.length > 0) {
        setSelectedModel(sorted[0].id);
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
      // Check if model is loaded, if not load it
      const model = models.find(m => m.id === selectedModel);
      if (model && model.status !== "loaded") {
        toast.info(`Loading model ${model.name}...`);
        try {
          await ryxService.loadModel(selectedModel);
        } catch {
          toast.error(`Failed to load model ${model.name}`);
        }
      }

      // Use ryxService which creates locally
      const session = await ryxService.createSession({
        name: sessionName,
        model: selectedModel,
      });

      // Store style in session
      localStorage.setItem(`session-style-${session.id}`, selectedStyle);

      toast.success(`Session "${session.name}" created!`);
      
      if (onSessionCreated) {
        onSessionCreated(session.id);
      }

      // Force page reload to pick up new session from localStorage
      window.location.reload();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to create session";
      toast.error("Failed to create session", { description: errorMessage });
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[450px]">
        <DialogHeader>
          <DialogTitle>Create New Session</DialogTitle>
          <DialogDescription>
            Start a new conversation with Ryx AI
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Session Name */}
          <div className="space-y-2">
            <Label htmlFor="session-name">Session Name</Label>
            <Input
              id="session-name"
              placeholder="e.g., Code Review"
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
                            model.status === "loaded"
                              ? "bg-green-500"
                              : "bg-gray-400"
                          }`}
                        />
                        <span>{model.name}</span>
                        {model.status !== "loaded" && (
                          <span className="text-xs text-muted-foreground">
                            (will load)
                          </span>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Response Style */}
          <div className="space-y-2">
            <Label htmlFor="style-select">Response Style</Label>
            <Select value={selectedStyle} onValueChange={setSelectedStyle} disabled={loading}>
              <SelectTrigger id="style-select">
                <SelectValue placeholder="Select style" />
              </SelectTrigger>
              <SelectContent>
                {RESPONSE_STYLES.map((style) => (
                  <SelectItem key={style.id} value={style.id}>
                    <div className="flex flex-col">
                      <span>{style.name}</span>
                      <span className="text-xs text-muted-foreground">{style.description}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
