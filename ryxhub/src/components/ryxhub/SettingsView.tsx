import { useState, useEffect } from "react";
import { 
  Settings, Server, Cpu, Activity, 
  RefreshCw, Power, PowerOff, Database, Loader2,
  Brain, ChevronRight, Trash2, Plus, BarChart3
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
  const [logStats, setLogStats] = useState<any>(null);
  
  // Fetch log stats
  useEffect(() => {
    fetch('http://localhost:8420/api/logs/stats')
      .then(r => r.json())
      .then(setLogStats)
      .catch(() => {});
  }, []);

  const handleLoadModel = async (modelId: string) => {
    try {
      await loadModelMutation.mutateAsync(modelId);
      refetchModels();
    } catch (error) {
      // Error handled by mutation
    }
  };

  const loadedModels = models?.filter(m => m.status === "loaded") || [];
  const availableModels = models?.filter(m => m.status !== "loaded") || [];

  return (
    <div className="h-full overflow-auto p-6">
      {/* Compact Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Settings
          </h1>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetchModels()}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      {/* Grid Layout - Apple Style */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        
        {/* Status Cards Row */}
        <Card className="col-span-1">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium">Ollama</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn(
                  "w-2 h-2 rounded-full",
                  health?.ollama_status === "online" ? "bg-green-500" : "bg-red-500"
                )} />
                <span className="text-sm capitalize">{health?.ollama_status || "..."}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="col-span-1">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-green-500" />
                <span className="text-sm font-medium">SearXNG</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn(
                  "w-2 h-2 rounded-full",
                  health?.searxng_status === "online" ? "bg-green-500" : "bg-red-500"
                )} />
                <span className="text-sm capitalize">{health?.searxng_status || "..."}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="col-span-1">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-blue-500" />
                <span className="text-sm font-medium">Models</span>
              </div>
              <span className="text-sm font-bold">{loadedModels.length} loaded / {models?.length || 0} total</span>
            </div>
          </CardContent>
        </Card>

        {/* Session Stats Card */}
        {logStats && (
          <Card className="col-span-1 md:col-span-2 lg:col-span-3">
            <CardContent className="pt-4">
              <div className="flex items-center gap-2 mb-3">
                <BarChart3 className="w-4 h-4 text-purple-500" />
                <span className="text-sm font-medium">Session Stats</span>
              </div>
              <div className="grid grid-cols-4 gap-4 text-center">
                <div>
                  <div className="text-2xl font-bold">{logStats.total_interactions}</div>
                  <div className="text-xs text-muted-foreground">Interactions</div>
                </div>
                <div>
                  <div className="text-2xl font-bold">{(logStats.average_latency_ms / 1000).toFixed(1)}s</div>
                  <div className="text-xs text-muted-foreground">Avg Latency</div>
                </div>
                <div>
                  <div className="text-2xl font-bold">{(logStats.average_confidence * 100).toFixed(0)}%</div>
                  <div className="text-xs text-muted-foreground">Avg Confidence</div>
                </div>
                <div>
                  <div className="text-2xl font-bold">{logStats.tool_usage?.web_search || 0}</div>
                  <div className="text-xs text-muted-foreground">Web Searches</div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loaded Models - Compact */}
        <Card className="col-span-1 md:col-span-2 lg:col-span-3">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              Loaded Models ({loadedModels.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loadedModels.length === 0 ? (
              <p className="text-sm text-muted-foreground">No models loaded. Load one below.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {loadedModels.map((model) => (
                  <div key={model.id} className="flex items-center gap-2 px-3 py-1.5 bg-primary/10 rounded-lg border border-primary/20">
                    <span className="text-sm font-medium">{model.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {(model.size / (1024 * 1024 * 1024)).toFixed(1)}GB
                    </span>
                    <button
                      onClick={async () => {
                        if (loadedModels.length <= 1) {
                          toast.error("Keep at least one model loaded");
                          return;
                        }
                        try {
                          await fetch(`http://localhost:8420/api/models/${model.id}/unload`, { method: 'POST' });
                          toast.success(`Unloaded ${model.name}`);
                          refetchModels();
                        } catch {
                          toast.error('Failed to unload');
                        }
                      }}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <PowerOff className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Available Models - Dropdown Style */}
        <Card className="col-span-1 md:col-span-2 lg:col-span-3">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Available Models ({availableModels.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {modelsLoading ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {availableModels.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => handleLoadModel(model.id)}
                    disabled={loadModelMutation.isPending}
                    className="flex items-center justify-between p-2 rounded-lg border hover:bg-muted/50 transition-colors text-left"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{model.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {(model.size / (1024 * 1024 * 1024)).toFixed(1)}GB
                      </div>
                    </div>
                    <Power className="w-4 h-4 text-muted-foreground flex-shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Memory Management */}
        <Card className="col-span-1 md:col-span-2 lg:col-span-3">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Brain className="w-4 h-4" />
              User Memory
            </CardTitle>
            <CardDescription className="text-xs">Things Ryx remembers about you</CardDescription>
          </CardHeader>
          <CardContent>
            <UserMemoryCompact />
          </CardContent>
        </Card>

        {/* Integrations Grid */}
        <Card className="col-span-1 md:col-span-2 lg:col-span-3">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Integrations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <IntegrationCard name="WebUntis" icon="📅" status="available" />
              <IntegrationCard name="Gmail" icon="📧" status="coming" />
              <IntegrationCard name="GitHub" icon="🐙" status="coming" />
              <IntegrationCard name="Notion" icon="📝" status="coming" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Compact Integration Card
function IntegrationCard({ name, icon, status }: { name: string; icon: string; status: 'connected' | 'available' | 'coming' }) {
  return (
    <button 
      className={cn(
        "flex items-center gap-2 p-3 rounded-lg border transition-colors",
        status === 'coming' ? "opacity-50 cursor-not-allowed" : "hover:bg-muted/50"
      )}
      disabled={status === 'coming'}
    >
      <span className="text-xl">{icon}</span>
      <div className="flex-1 text-left">
        <div className="text-sm font-medium">{name}</div>
        <div className="text-xs text-muted-foreground capitalize">
          {status === 'coming' ? 'Coming soon' : status}
        </div>
      </div>
      {status !== 'coming' && <ChevronRight className="w-4 h-4 text-muted-foreground" />}
    </button>
  );
}

// Compact User Memory Component
function UserMemoryCompact() {
  const [memories, setMemories] = useState<string[]>([]);
  const [newMemory, setNewMemory] = useState("");
  const [dbMemories, setDbMemories] = useState<any[]>([]);

  useEffect(() => {
    // Local memories
    const stored = localStorage.getItem('ryxhub_user_memories');
    if (stored) {
      try { setMemories(JSON.parse(stored)); } catch {}
    }
    // DB memories
    fetch('http://localhost:8420/api/memory?limit=10')
      .then(r => r.json())
      .then(d => setDbMemories(d.memories || []))
      .catch(() => {});
  }, []);

  const saveMemories = (updated: string[]) => {
    setMemories(updated);
    localStorage.setItem('ryxhub_user_memories', JSON.stringify(updated));
  };

  const addMemory = () => {
    if (newMemory.trim()) {
      saveMemories([...memories, newMemory.trim()]);
      // Also save to backend
      fetch('http://localhost:8420/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fact: newMemory.trim(), category: 'user_added' })
      }).catch(() => {});
      setNewMemory("");
      toast.success("Memory added");
    }
  };

  const removeMemory = (index: number) => {
    saveMemories(memories.filter((_, i) => i !== index));
    toast.success("Memory removed");
  };

  const deleteDbMemory = async (id: number) => {
    try {
      await fetch(`http://localhost:8420/api/memory/${id}`, { method: 'DELETE' });
      setDbMemories(prev => prev.filter(m => m.id !== id));
      toast.success("Memory deleted");
    } catch {
      toast.error("Failed to delete");
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={newMemory}
          onChange={(e) => setNewMemory(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && addMemory()}
          placeholder="Add a memory..."
          className="flex-1 px-3 py-1.5 text-sm border rounded-lg bg-background"
        />
        <Button onClick={addMemory} size="sm" variant="outline">
          <Plus className="w-4 h-4" />
        </Button>
      </div>
      
      {/* Combined memories */}
      <div className="flex flex-wrap gap-2">
        {memories.map((memory, index) => (
          <span key={`local-${index}`} className="inline-flex items-center gap-1 px-2 py-1 bg-muted rounded-lg text-xs">
            {memory}
            <button onClick={() => removeMemory(index)} className="text-muted-foreground hover:text-destructive">
              <Trash2 className="w-3 h-3" />
            </button>
          </span>
        ))}
        {dbMemories.map((mem) => (
          <span key={`db-${mem.id}`} className="inline-flex items-center gap-1 px-2 py-1 bg-primary/10 rounded-lg text-xs" title={`Category: ${mem.category}`}>
            {mem.fact}
            <button onClick={() => deleteDbMemory(mem.id)} className="text-muted-foreground hover:text-destructive">
              <Trash2 className="w-3 h-3" />
            </button>
          </span>
        ))}
        {memories.length === 0 && dbMemories.length === 0 && (
          <span className="text-sm text-muted-foreground">No memories yet</span>
        )}
      </div>
    </div>
  );
}
