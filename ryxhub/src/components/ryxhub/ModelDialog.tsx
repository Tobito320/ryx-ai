import { useState } from "react";
import { Loader2, AlertCircle, CheckCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { ryxService } from "@/services/ryxService";

interface Model {
  id: string;
  name: string;
  status: "online" | "offline" | "loading";
  provider: string;
}

interface ModelDialogProps {
  model: Model | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onModelUpdate?: () => void;
}

export function ModelDialog({ model, open, onOpenChange, onModelUpdate }: ModelDialogProps) {
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>("");

  if (!model) return null;

  const handleConnect = async () => {
    setLoading(true);
    setStatusMessage("");

    try {
      if (model.status === "online") {
        toast.info(`Model ${model.name} is already connected`);
        return;
      }

      const result = await ryxService.loadModel(model.id);

      if (result.success) {
        if (result.status === "connected") {
          toast.success(`Connected to ${model.name}`);
          setStatusMessage("Model is connected and ready!");
        } else if (result.status === "requires_restart") {
          toast.warning(`${model.name} requires Ollama restart`, {
            description: result.message,
          });
          setStatusMessage(result.message || "Requires restart");
        }
      } else {
        toast.error(`Failed to load ${model.name}`, {
          description: result.message,
        });
        setStatusMessage(result.message || "Failed to load model");
      }

      if (onModelUpdate) {
        onModelUpdate();
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      toast.error("Connection failed", { description: errorMessage });
      setStatusMessage(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleCheckStatus = async () => {
    setLoading(true);
    try {
      const models = await ryxService.listModels();
      const modelInfo = models.find(m => m.id === model.id);
      if (modelInfo) {
        const msg = modelInfo.status === 'loaded' ? 'Model is loaded and ready' : 'Model available but not loaded';
        setStatusMessage(msg);
        toast.info(msg);
      } else {
        setStatusMessage('Model not found');
        toast.error('Model not found');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to check status";
      setStatusMessage(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {model.status === "online" && (
              <CheckCircle className="w-5 h-5 text-[hsl(var(--success))]" />
            )}
            {model.status === "offline" && (
              <AlertCircle className="w-5 h-5 text-muted-foreground" />
            )}
            {model.status === "loading" && (
              <Loader2 className="w-5 h-5 animate-spin text-[hsl(var(--warning))]" />
            )}
            {model.name}
          </DialogTitle>
          <DialogDescription>
            Manage model connection and check status
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Model Info */}
          <div className="space-y-2 p-4 rounded-lg bg-muted/30 border border-border">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Provider</span>
              <span className="font-mono text-foreground">{model.provider}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Status</span>
              <span
                className={`font-mono ${
                  model.status === "online"
                    ? "text-[hsl(var(--success))]"
                    : model.status === "loading"
                    ? "text-[hsl(var(--warning))]"
                    : "text-muted-foreground"
                }`}
              >
                {model.status.toUpperCase()}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Model ID</span>
              <span className="font-mono text-foreground text-xs truncate max-w-[250px]">
                {model.id}
              </span>
            </div>
          </div>

          {/* Status Message */}
          {statusMessage && (
            <div className="p-3 rounded-lg bg-card border border-border">
              <p className="text-sm text-muted-foreground">{statusMessage}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2">
            <Button
              onClick={handleConnect}
              disabled={loading || model.status === "loading"}
              className="flex-1"
            >
              {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              {model.status === "online" ? "Already Connected" : "Connect"}
            </Button>
            <Button
              onClick={handleCheckStatus}
              disabled={loading}
              variant="outline"
            >
              {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Check Status
            </Button>
          </div>

          {/* Info */}
          <div className="text-xs text-muted-foreground bg-muted/20 p-3 rounded-lg border border-border">
            <p className="font-semibold mb-1">ℹ️ Ollama Model Management:</p>
            <p>
              Load models from Settings. Multiple models can be loaded simultaneously.
              Ollama manages memory automatically.
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
