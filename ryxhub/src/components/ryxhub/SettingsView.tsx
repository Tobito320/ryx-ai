import { useState, useEffect } from "react";
import { 
  Settings, Server, Activity, RefreshCw, Power, PowerOff, 
  Brain, Trash2, Plus, ChevronLeft, Check, X
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useModels, useLoadModel, useHealth } from "@/hooks/useRyxApi";
import { toast } from "sonner";
import { useRyxHub } from "@/context/RyxHubContext";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function SettingsView() {
  const { setActiveView } = useRyxHub();
  const { data: models, isLoading: modelsLoading, refetch: refetchModels } = useModels();
  const { data: health } = useHealth();
  const loadModelMutation = useLoadModel();
  
  // User preferences
  const [responseStyle, setResponseStyle] = useState(() => 
    localStorage.getItem('ryxhub_response_style') || 'normal'
  );
  const [language, setLanguage] = useState(() => 
    localStorage.getItem('ryxhub_language') || 'auto'
  );
  const [autoSearch, setAutoSearch] = useState(() => 
    localStorage.getItem('ryxhub_auto_search') !== 'false'
  );
  const [autoLearn, setAutoLearn] = useState(() => 
    localStorage.getItem('ryxhub_auto_learn') !== 'false'
  );

  // Memories
  const [memories, setMemories] = useState<string[]>([]);
  const [dbMemories, setDbMemories] = useState<any[]>([]);
  const [newMemory, setNewMemory] = useState("");

  useEffect(() => {
    // Load local memories
    const stored = localStorage.getItem('ryxhub_user_memories');
    if (stored) {
      try { setMemories(JSON.parse(stored)); } catch {}
    }
    // Load DB memories
    fetch('http://localhost:8420/api/memory?limit=20')
      .then(r => r.json())
      .then(d => setDbMemories(d.memories || []))
      .catch(() => {});
  }, []);

  // Save preferences
  const savePreference = (key: string, value: string | boolean) => {
    localStorage.setItem(`ryxhub_${key}`, String(value));
  };

  const handleStyleChange = (value: string) => {
    setResponseStyle(value);
    savePreference('response_style', value);
    toast.success(`Response style: ${value}`);
  };

  const handleLanguageChange = (value: string) => {
    setLanguage(value);
    savePreference('language', value);
    toast.success(`Language: ${value}`);
  };

  const handleLoadModel = async (modelId: string) => {
    try {
      await loadModelMutation.mutateAsync(modelId);
      refetchModels();
    } catch (error) {
      // Error handled by mutation
    }
  };

  const handleUnloadModel = async (modelId: string) => {
    const loadedModels = models?.filter(m => m.status === "loaded") || [];
    if (loadedModels.length <= 1) {
      toast.error("Keep at least one model loaded");
      return;
    }
    try {
      await fetch(`http://localhost:8420/api/models/${modelId}/unload`, { method: 'POST' });
      toast.success(`Unloaded model`);
      refetchModels();
    } catch {
      toast.error('Failed to unload');
    }
  };

  const addMemory = () => {
    if (newMemory.trim()) {
      const updated = [...memories, newMemory.trim()];
      setMemories(updated);
      localStorage.setItem('ryxhub_user_memories', JSON.stringify(updated));
      // Also save to backend
      fetch('http://localhost:8420/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fact: newMemory.trim(), category: 'user_added', relevance_score: 0.9 })
      }).catch(() => {});
      setNewMemory("");
      toast.success("Memory added");
    }
  };

  const removeMemory = (index: number) => {
    const updated = memories.filter((_, i) => i !== index);
    setMemories(updated);
    localStorage.setItem('ryxhub_user_memories', JSON.stringify(updated));
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

  const clearAllMemories = async () => {
    if (!confirm("Clear all memories? This cannot be undone.")) return;
    setMemories([]);
    localStorage.setItem('ryxhub_user_memories', JSON.stringify([]));
    // Clear DB memories
    for (const mem of dbMemories) {
      await fetch(`http://localhost:8420/api/memory/${mem.id}`, { method: 'DELETE' }).catch(() => {});
    }
    setDbMemories([]);
    toast.success("All memories cleared");
  };

  const loadedModels = models?.filter(m => m.status === "loaded") || [];
  const availableModels = models?.filter(m => m.status !== "loaded") || [];

  return (
    <div className="h-full overflow-auto bg-background">
      {/* Header */}
      <div className="sticky top-0 bg-background/95 backdrop-blur-sm border-b border-border z-10">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setActiveView("chat")}
              className="p-1.5 rounded-lg hover:bg-muted transition-colors"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <h1 className="text-lg font-semibold flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Settings
            </h1>
          </div>
          <Button variant="ghost" size="sm" onClick={() => refetchModels()}>
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Content - Single Screen, No Scroll Needed */}
      <div className="max-w-3xl mx-auto px-6 py-6 space-y-8">
        
        {/* Status Row */}
        <div className="grid grid-cols-3 gap-3">
          <StatusCard
            icon={<Server className="w-4 h-4" />}
            label="Ollama"
            status={health?.ollama_status === "online"}
          />
          <StatusCard
            icon={<Activity className="w-4 h-4" />}
            label="SearXNG"
            status={health?.searxng_status === "online"}
          />
          <StatusCard
            icon={<Brain className="w-4 h-4" />}
            label="Memory"
            status={true}
            detail={`${memories.length + dbMemories.length} facts`}
          />
        </div>

        {/* Response Settings */}
        <section>
          <h2 className="text-sm font-medium text-muted-foreground mb-3">Response</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-muted-foreground mb-1.5 block">Style</label>
              <Select value={responseStyle} onValueChange={handleStyleChange}>
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="concise">Concise</SelectItem>
                  <SelectItem value="normal">Balanced</SelectItem>
                  <SelectItem value="explanatory">Detailed</SelectItem>
                  <SelectItem value="learning">Teaching</SelectItem>
                  <SelectItem value="formal">Formal</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1.5 block">Language</label>
              <Select value={language} onValueChange={handleLanguageChange}>
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto-detect</SelectItem>
                  <SelectItem value="de">German</SelectItem>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="ar">Arabic</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </section>

        {/* Feature Toggles */}
        <section>
          <h2 className="text-sm font-medium text-muted-foreground mb-3">Features</h2>
          <div className="space-y-2">
            <ToggleRow
              label="Auto web search"
              description="Search when needed (weather, news, facts)"
              checked={autoSearch}
              onChange={(v) => { setAutoSearch(v); savePreference('auto_search', v); }}
            />
            <ToggleRow
              label="Auto-learn facts"
              description="Remember what you tell Ryx"
              checked={autoLearn}
              onChange={(v) => { setAutoLearn(v); savePreference('auto_learn', v); }}
            />
          </div>
        </section>

        {/* Models */}
        <section>
          <h2 className="text-sm font-medium text-muted-foreground mb-3">Ollama Models</h2>
          
          {/* Loaded */}
          <div className="mb-3">
            <span className="text-xs text-muted-foreground">Loaded ({loadedModels.length})</span>
            <div className="flex flex-wrap gap-2 mt-1.5">
              {loadedModels.map((model) => (
                <span key={model.id} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-primary/10 border border-primary/20 rounded-lg text-sm">
                  <span className="w-1.5 h-1.5 rounded-full bg-[hsl(var(--success))]" />
                  {model.name}
                  <button
                    onClick={() => handleUnloadModel(model.id)}
                    className="ml-1 text-muted-foreground hover:text-destructive"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>
          
          {/* Available */}
          <div>
            <span className="text-xs text-muted-foreground">Available ({availableModels.length})</span>
            <div className="flex flex-wrap gap-2 mt-1.5">
              {availableModels.slice(0, 8).map((model) => (
                <button
                  key={model.id}
                  onClick={() => handleLoadModel(model.id)}
                  disabled={loadModelMutation.isPending}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 border border-border rounded-lg text-sm hover:bg-muted/50 transition-colors"
                >
                  <Power className="w-3 h-3 text-muted-foreground" />
                  {model.name}
                </button>
              ))}
              {availableModels.length > 8 && (
                <span className="text-xs text-muted-foreground self-center">+{availableModels.length - 8} more</span>
              )}
            </div>
          </div>
        </section>

        {/* Memory */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-muted-foreground">Memory</h2>
            <button
              onClick={clearAllMemories}
              className="text-xs text-muted-foreground hover:text-destructive transition-colors"
            >
              Clear all
            </button>
          </div>
          
          {/* Add memory */}
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={newMemory}
              onChange={(e) => setNewMemory(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addMemory()}
              placeholder="Add something Ryx should remember..."
              className="flex-1 px-3 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <Button onClick={addMemory} size="sm" variant="outline">
              <Plus className="w-4 h-4" />
            </Button>
          </div>
          
          {/* Memory tags */}
          <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto scrollbar-thin">
            {memories.map((memory, index) => (
              <MemoryTag key={`local-${index}`} text={memory} onDelete={() => removeMemory(index)} />
            ))}
            {dbMemories.map((mem) => (
              <MemoryTag 
                key={`db-${mem.id}`} 
                text={mem.fact} 
                category={mem.category}
                onDelete={() => deleteDbMemory(mem.id)} 
              />
            ))}
            {memories.length === 0 && dbMemories.length === 0 && (
              <span className="text-sm text-muted-foreground/60">No memories yet</span>
            )}
          </div>
        </section>

        {/* Integrations Grid */}
        <section>
          <h2 className="text-sm font-medium text-muted-foreground mb-3">Integrations</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <IntegrationCard name="WebUntis" emoji="📅" status="available" />
            <IntegrationCard name="Gmail" emoji="📧" status="coming" />
            <IntegrationCard name="GitHub" emoji="🐙" status="coming" />
            <IntegrationCard name="Notion" emoji="📝" status="coming" />
          </div>
        </section>
      </div>
    </div>
  );
}

// Helper Components

function StatusCard({ icon, label, status, detail }: { icon: React.ReactNode; label: string; status: boolean; detail?: string }) {
  return (
    <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-card">
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-sm">{label}</span>
      </div>
      <div className="flex items-center gap-1.5">
        {detail && <span className="text-xs text-muted-foreground">{detail}</span>}
        <span className={cn(
          "w-2 h-2 rounded-full",
          status ? "bg-[hsl(var(--success))]" : "bg-destructive"
        )} />
      </div>
    </div>
  );
}

function ToggleRow({ label, description, checked, onChange }: { label: string; description: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <div className="text-sm">{label}</div>
        <div className="text-xs text-muted-foreground">{description}</div>
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={cn(
          "w-10 h-6 rounded-full transition-colors relative",
          checked ? "bg-primary" : "bg-muted"
        )}
      >
        <span className={cn(
          "absolute top-1 w-4 h-4 rounded-full bg-white transition-transform",
          checked ? "translate-x-5" : "translate-x-1"
        )} />
      </button>
    </div>
  );
}

function MemoryTag({ text, category, onDelete }: { text: string; category?: string; onDelete: () => void }) {
  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs",
      category ? "bg-primary/10 border border-primary/20" : "bg-muted"
    )} title={category ? `Category: ${category}` : undefined}>
      {text.length > 40 ? text.slice(0, 40) + '...' : text}
      <button onClick={onDelete} className="text-muted-foreground hover:text-destructive ml-0.5">
        <Trash2 className="w-3 h-3" />
      </button>
    </span>
  );
}

function IntegrationCard({ name, emoji, status }: { name: string; emoji: string; status: 'connected' | 'available' | 'coming' }) {
  return (
    <button 
      className={cn(
        "flex items-center gap-2 p-3 rounded-lg border border-border transition-colors text-left",
        status === 'coming' ? "opacity-50 cursor-not-allowed" : "hover:bg-muted/50"
      )}
      disabled={status === 'coming'}
    >
      <span className="text-lg">{emoji}</span>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">{name}</div>
        <div className="text-[10px] text-muted-foreground">
          {status === 'connected' && <span className="text-[hsl(var(--success))]">✓ Connected</span>}
          {status === 'available' && <span>Available</span>}
          {status === 'coming' && <span>Coming soon</span>}
        </div>
      </div>
    </button>
  );
}
