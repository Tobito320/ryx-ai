import { useState, useEffect } from "react";
import { 
  Settings, Server, Cpu, Activity, 
  RefreshCw, Power, PowerOff, Database, Loader2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useModels, useLoadModel, useHealth } from "@/hooks/useRyxApi";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { RAGManagement } from "@/components/ryxhub/RAGManagement";



export function SettingsView() {
  const { data: models, isLoading: modelsLoading, refetch: refetchModels } = useModels();
  const { data: health } = useHealth();
  const loadModelMutation = useLoadModel();
  
  // Removed vLLM metrics - Ollama manages internally

  const handleLoadModel = async (modelId: string) => {
    try {
      await loadModelMutation.mutateAsync(modelId);
      refetchModels();
    } catch (error) {
      // Error handled by mutation
    }
  };



  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
              <Settings className="w-6 h-6" />
              Settings & Metrics
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Monitor Ollama performance and manage models
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetchModels()}>
            <RefreshCw className="w-4 h-4 mr-1" />
            Refresh
          </Button>
        </div>

        {/* System Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Ollama Status */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Server className="w-4 h-4 text-primary" />
                Ollama Server
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <span className={cn(
                  "w-3 h-3 rounded-full",
                  health?.ollama_status === "online" ? "bg-green-500" : "bg-red-500"
                )} />
                <span className="text-lg font-semibold capitalize">
                  {health?.ollama_status || "Unknown"}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Port 11434
              </p>
            </CardContent>
          </Card>

          {/* SearXNG Status */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Activity className="w-4 h-4 text-green-500" />
                SearXNG Search
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <span className={cn(
                  "w-3 h-3 rounded-full",
                  health?.searxng_status === "online" ? "bg-green-500" : "bg-red-500"
                )} />
                <span className="text-lg font-semibold capitalize">
                  {health?.searxng_status || "Unknown"}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Port 8888
              </p>
            </CardContent>
          </Card>

          {/* Models Available */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Cpu className="w-4 h-4 text-blue-500" />
                Models Available
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg font-semibold">
                {health?.models_available || 0}
              </div>
              <p className="text-xs text-muted-foreground">
                Ollama models ready
              </p>
            </CardContent>
          </Card>
        </div>



        {/* Models Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="w-5 h-5" />
              Available Models ({models?.length || 0} total)
            </CardTitle>
            <CardDescription>
              Load and unload models dynamically. Ollama manages memory automatically.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {modelsLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <div className="space-y-3">
                {models?.map((model) => (
                <div
                  key={model.id}
                  className={cn(
                    "flex items-center justify-between p-4 rounded-lg border",
                    model.status === "loaded" 
                      ? "bg-primary/5 border-primary/20" 
                      : "bg-muted/30 border-border"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "w-3 h-3 rounded-full",
                      model.status === "loaded" ? "bg-green-500 animate-pulse" : "bg-gray-400"
                    )} />
                    <div>
                      <div className="font-medium">{model.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {(model.size / (1024 * 1024 * 1024)).toFixed(1)} GB
                        {model.status === "loaded" && " • Loaded"}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {model.status === "loaded" ? (
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={async () => {
                          const loadedCount = models?.filter(m => m.status === "loaded").length || 0;
                          if (loadedCount <= 1) {
                            toast.error("At least one model must stay loaded");
                            return;
                          }
                          try {
                            await fetch(`http://localhost:8420/api/models/${model.id}/unload`, { method: 'POST' });
                            toast.success(`Model ${model.name} unloaded`);
                            refetchModels();
                          } catch {
                            toast.error('Failed to unload model');
                          }
                        }}
                      >
                        <PowerOff className="w-4 h-4 mr-1" />
                        Unload
                      </Button>
                    ) : (
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleLoadModel(model.id)}
                        disabled={loadModelMutation.isPending}
                      >
                        {loadModelMutation.isPending ? (
                          <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                        ) : (
                          <Power className="w-4 h-4 mr-1" />
                        )}
                        Load
                      </Button>
                    )}
                  </div>
                </div>
              ))}
              </div>
            )}
          </CardContent>
        </Card>



        {/* RAG Management Section */}
        <div className="mt-8">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Database className="w-5 h-5" />
            Knowledge Base Management
          </h2>
          <RAGManagement />
        </div>

        {/* User Memory Section */}
        <div className="mt-8">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Database className="w-5 h-5" />
            User Memory
          </h2>
          <UserMemorySettings />
        </div>

        {/* Integrations Section */}
        <div className="mt-8">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Integrationen
          </h2>
          <WebUntisSettings />
        </div>
      </div>
    </ScrollArea>
  );
}

// User Memory Settings Component
function UserMemorySettings() {
  const [memories, setMemories] = useState<string[]>([]);
  const [newMemory, setNewMemory] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem('ryxhub_user_memories');
    if (stored) {
      try {
        setMemories(JSON.parse(stored));
      } catch {}
    }
  }, []);

  const saveMemories = (updated: string[]) => {
    setMemories(updated);
    localStorage.setItem('ryxhub_user_memories', JSON.stringify(updated));
  };

  const addMemory = () => {
    if (newMemory.trim()) {
      saveMemories([...memories, newMemory.trim()]);
      setNewMemory("");
      toast.success("Memory added");
    }
  };

  const removeMemory = (index: number) => {
    const updated = memories.filter((_, i) => i !== index);
    saveMemories(updated);
    toast.success("Memory removed");
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Things Ryx Remembers About You</CardTitle>
        <CardDescription>
          Add personal information that Ryx should remember across all sessions
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={newMemory}
            onChange={(e) => setNewMemory(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addMemory()}
            placeholder="e.g., My name is Tobi, I prefer concise answers..."
            className="flex-1 px-3 py-2 text-sm border rounded-md bg-background"
          />
          <Button onClick={addMemory} size="sm">Add</Button>
        </div>
        {memories.length === 0 ? (
          <p className="text-sm text-muted-foreground">No memories yet. Add something for Ryx to remember!</p>
        ) : (
          <div className="space-y-2">
            {memories.map((memory, index) => (
              <div key={index} className="flex items-center justify-between p-2 bg-muted rounded-md">
                <span className="text-sm">{memory}</span>
                <Button variant="ghost" size="sm" onClick={() => removeMemory(index)} className="h-6 px-2 text-destructive hover:text-destructive">
                  ×
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// WebUntis Settings Component
function WebUntisSettings() {
  const [config, setConfig] = useState({ server: "", school: "", username: "", password: "" });
  const [isConfigured, setIsConfigured] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await fetch("http://localhost:8420/api/webuntis/config");
        if (res.ok) {
          const data = await res.json();
          setIsConfigured(data.configured);
          if (data.configured) {
            setConfig(prev => ({
              ...prev,
              server: data.server,
              school: data.school,
              username: data.username,
            }));
          }
        }
      } catch (error) {
        console.error("Failed to load WebUntis config", error);
      }
    };
    loadConfig();
  }, []);

  const handleSave = async () => {
    if (!config.server || !config.school || !config.username || !config.password) {
      toast.error("Alle Felder erforderlich");
      return;
    }
    
    setIsSaving(true);
    try {
      const res = await fetch("http://localhost:8420/api/webuntis/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      
      if (res.ok) {
        toast.success("WebUntis konfiguriert!");
        setIsConfigured(true);
      } else {
        const err = await res.json();
        toast.error(err.detail || "Fehler beim Speichern");
      }
    } catch (error) {
      toast.error("Verbindungsfehler");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">WebUntis (Berufsschule)</CardTitle>
        <CardDescription>
          Verbinde dein WebUntis-Konto für den Stundenplan
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {isConfigured && (
          <Badge variant="outline" className="mb-2 text-green-600 border-green-600">
            ✓ Verbunden als {config.username}
          </Badge>
        )}
        <div className="grid grid-cols-2 gap-3">
          <input
            type="text"
            placeholder="Server (z.B. neilo.webuntis.com)"
            value={config.server}
            onChange={(e) => setConfig(prev => ({ ...prev, server: e.target.value }))}
            className="px-3 py-2 text-sm rounded-md border bg-background"
          />
          <input
            type="text"
            placeholder="Schule"
            value={config.school}
            onChange={(e) => setConfig(prev => ({ ...prev, school: e.target.value }))}
            className="px-3 py-2 text-sm rounded-md border bg-background"
          />
          <input
            type="text"
            placeholder="Benutzername"
            value={config.username}
            onChange={(e) => setConfig(prev => ({ ...prev, username: e.target.value }))}
            className="px-3 py-2 text-sm rounded-md border bg-background"
          />
          <input
            type="password"
            placeholder="Passwort"
            value={config.password}
            onChange={(e) => setConfig(prev => ({ ...prev, password: e.target.value }))}
            className="px-3 py-2 text-sm rounded-md border bg-background"
          />
        </div>
        <Button onClick={handleSave} disabled={isSaving} className="w-full">
          {isSaving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
          {isConfigured ? "Aktualisieren" : "Verbinden"}
        </Button>
      </CardContent>
    </Card>
  );
}
