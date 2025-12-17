import { useState, useEffect } from "react";
import { 
  Settings, Server, Activity, RefreshCw, Power, PowerOff, 
  Brain, Trash2, Plus, ChevronLeft, Check, X, User, BookOpen, ExternalLink
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
import { ConnectorsView } from "./ConnectorsView";

export function SettingsView() {
  const { setActiveView } = useRyxHub();
  const { data: models, isLoading: modelsLoading, refetch: refetchModels } = useModels();
  const { data: health } = useHealth();
  const loadModelMutation = useLoadModel();
  
  // VRAM usage
  const [vramUsage, setVramUsage] = useState<{ total_vram_gb: number; max_vram_gb: number; usage_percent: number } | null>(null);
  const [loadingModel, setLoadingModel] = useState<string | null>(null);
  
  // Fetch VRAM usage
  useEffect(() => {
    const fetchVram = async () => {
      try {
        const res = await fetch('http://localhost:8420/api/models/vram');
        if (res.ok) {
          setVramUsage(await res.json());
        }
      } catch {}
    };
    fetchVram();
    const interval = setInterval(fetchVram, 5000);
    return () => clearInterval(interval);
  }, []);
  
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
  const [personaMemories, setPersonaMemories] = useState<any[]>([]);
  const [generalMemories, setGeneralMemories] = useState<any[]>([]);
  const [activeMemoryTab, setActiveMemoryTab] = useState<'persona' | 'general'>('persona');
  const [newMemory, setNewMemory] = useState("");
  const [connectorsOpen, setConnectorsOpen] = useState(false);

  useEffect(() => {
    // Load local memories
    const stored = localStorage.getItem('ryxhub_user_memories');
    if (stored) {
      try { setMemories(JSON.parse(stored)); } catch {}
    }
    // Load DB memories by type
    fetch('http://localhost:8420/api/memory/persona?limit=20')
      .then(r => r.json())
      .then(d => setPersonaMemories(d.memories || []))
      .catch(() => {});
    fetch('http://localhost:8420/api/memory/general?limit=20')
      .then(r => r.json())
      .then(d => setGeneralMemories(d.memories || []))
      .catch(() => {});
    // Also load all for backwards compatibility
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
      setLoadingModel(modelId);
      await loadModelMutation.mutateAsync(modelId);
      refetchModels();
      // Refresh VRAM
      const res = await fetch('http://localhost:8420/api/models/vram');
      if (res.ok) setVramUsage(await res.json());
    } catch (error) {
      // Error handled by mutation
    } finally {
      setLoadingModel(null);
    }
  };

  const handleUnloadModel = async (modelId: string) => {
    const loadedModels = models?.filter(m => m.status === "online") || [];
    if (loadedModels.length <= 1) {
      toast.error("Keep at least one model loaded");
      return;
    }
    try {
      setLoadingModel(modelId);
      await fetch(`http://localhost:8420/api/models/${modelId}/unload`, { method: 'POST' });
      toast.success(`Unloaded model`);
      refetchModels();
      // Refresh VRAM
      const res = await fetch('http://localhost:8420/api/models/vram');
      if (res.ok) setVramUsage(await res.json());
    } catch {
      toast.error('Failed to unload');
    } finally {
      setLoadingModel(null);
    }
  };

  const addMemory = () => {
    if (newMemory.trim()) {
      const updated = [...memories, newMemory.trim()];
      setMemories(updated);
      localStorage.setItem('ryxhub_user_memories', JSON.stringify(updated));
      // Save to backend as persona (user-added = always persona)
      fetch('http://localhost:8420/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fact: newMemory.trim(), category: 'persona', relevance_score: 0.9 })
      }).then(() => {
        // Refresh persona memories
        fetch('http://localhost:8420/api/memory/persona?limit=20')
          .then(r => r.json())
          .then(d => setPersonaMemories(d.memories || []))
          .catch(() => {});
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
      setPersonaMemories(prev => prev.filter(m => m.id !== id));
      setGeneralMemories(prev => prev.filter(m => m.id !== id));
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
    for (const mem of [...dbMemories, ...personaMemories, ...generalMemories]) {
      await fetch(`http://localhost:8420/api/memory/${mem.id}`, { method: 'DELETE' }).catch(() => {});
    }
    setDbMemories([]);
    setPersonaMemories([]);
    setGeneralMemories([]);
    toast.success("All memories cleared");
  };

  const loadedModels = models?.filter(m => m.status === "online") || [];
  const availableModels = models?.filter(m => m.status !== "online") || [];

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
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-muted-foreground">Ollama Models</h2>
            {vramUsage && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{vramUsage.total_vram_gb}GB / {vramUsage.max_vram_gb}GB VRAM</span>
                <div className="w-20 h-1.5 bg-muted rounded-full overflow-hidden">
                  <div 
                    className={cn(
                      "h-full rounded-full transition-all",
                      vramUsage.usage_percent > 85 ? "bg-destructive" :
                      vramUsage.usage_percent > 60 ? "bg-[hsl(var(--warning))]" :
                      "bg-[hsl(var(--success))]"
                    )}
                    style={{ width: `${vramUsage.usage_percent}%` }}
                  />
                </div>
              </div>
            )}
          </div>
          
          {/* Loaded */}
          <div className="mb-3">
            <span className="text-xs text-muted-foreground">Loaded ({loadedModels.length})</span>
            <div className="flex flex-wrap gap-2 mt-1.5">
              {loadedModels.map((model) => (
                <span key={model.id} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-primary/10 border border-primary/20 rounded-lg text-sm">
                  <span className="w-1.5 h-1.5 rounded-full bg-[hsl(var(--success))]" />
                  {model.name}
                  {loadingModel === model.id ? (
                    <RefreshCw className="w-3 h-3 animate-spin text-muted-foreground ml-1" />
                  ) : (
                    <button
                      onClick={() => handleUnloadModel(model.id)}
                      className="ml-1 text-muted-foreground hover:text-destructive"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
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
                  disabled={loadModelMutation.isPending || loadingModel === model.id}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 border border-border rounded-lg text-sm hover:bg-muted/50 transition-colors disabled:opacity-50"
                >
                  {loadingModel === model.id ? (
                    <RefreshCw className="w-3 h-3 animate-spin" />
                  ) : (
                    <Power className="w-3 h-3 text-muted-foreground" />
                  )}
                  {model.name}
                </button>
              ))}
              {availableModels.length > 8 && (
                <span className="text-xs text-muted-foreground self-center">+{availableModels.length - 8} more</span>
              )}
            </div>
          </div>
        </section>

        {/* Memory - Two Tabs */}
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
          
          {/* Memory Tabs */}
          <div className="flex gap-1 mb-3 p-1 bg-muted/50 rounded-lg">
            <button
              onClick={() => setActiveMemoryTab('persona')}
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                activeMemoryTab === 'persona' 
                  ? "bg-background shadow-sm text-foreground" 
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <User className="w-3 h-3" />
              Your Persona ({personaMemories.length})
            </button>
            <button
              onClick={() => setActiveMemoryTab('general')}
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                activeMemoryTab === 'general' 
                  ? "bg-background shadow-sm text-foreground" 
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <BookOpen className="w-3 h-3" />
              General ({generalMemories.length})
            </button>
          </div>
          
          {/* Add memory (only for persona tab) */}
          {activeMemoryTab === 'persona' && (
            <div className="flex gap-2 mb-3">
              <input
                type="text"
                value={newMemory}
                onChange={(e) => setNewMemory(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addMemory()}
                placeholder="Add something Ryx should remember about you..."
                className="flex-1 px-3 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <Button onClick={addMemory} size="sm" variant="outline">
                <Plus className="w-4 h-4" />
              </Button>
            </div>
          )}
          
          {/* Memory tags based on active tab */}
          <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto scrollbar-thin">
            {activeMemoryTab === 'persona' ? (
              <>
                {memories.map((memory, index) => (
                  <MemoryTag key={`local-${index}`} text={memory} isPersona onDelete={() => removeMemory(index)} />
                ))}
                {personaMemories.map((mem) => (
                  <MemoryTag 
                    key={`persona-${mem.id}`} 
                    text={mem.fact} 
                    isPersona
                    onDelete={() => deleteDbMemory(mem.id)} 
                  />
                ))}
                {memories.length === 0 && personaMemories.length === 0 && (
                  <span className="text-sm text-muted-foreground/60">No persona facts yet. Tell Ryx about yourself!</span>
                )}
              </>
            ) : (
              <>
                {generalMemories.map((mem) => (
                  <MemoryTag 
                    key={`general-${mem.id}`} 
                    text={mem.fact} 
                    onDelete={() => deleteDbMemory(mem.id)} 
                  />
                ))}
                {generalMemories.length === 0 && (
                  <span className="text-sm text-muted-foreground/60">No general facts learned yet</span>
                )}
              </>
            )}
          </div>
        </section>

        {/* Connectors Section - Claude Style */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-muted-foreground">Connectors</h2>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => setConnectorsOpen(true)}
              className="h-7 text-xs gap-1.5"
            >
              <ExternalLink className="w-3 h-3" />
              Browse connectors
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mb-3">
            Allow Ryx to reference other apps and services for more context.
          </p>
          <ConnectorStatusList />
        </section>
      </div>

      {/* Connectors Modal */}
      {connectorsOpen && (
        <ConnectorsView onClose={() => setConnectorsOpen(false)} />
      )}
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

function MemoryTag({ text, isPersona, onDelete }: { text: string; isPersona?: boolean; onDelete: () => void }) {
  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs",
      isPersona ? "bg-primary/10 border border-primary/20" : "bg-muted"
    )}>
      {text.length > 40 ? text.slice(0, 40) + '...' : text}
      <button onClick={onDelete} className="text-muted-foreground hover:text-destructive ml-0.5">
        <Trash2 className="w-3 h-3" />
      </button>
    </span>
  );
}

// Connector status list showing connected services
function ConnectorStatusList() {
  const [status, setStatus] = useState<Record<string, any>>({});

  useEffect(() => {
    // Load connector status from localStorage
    const connectors = ['github', 'gmail', 'google_drive', 'google_calendar', 'notion'];
    const newStatus: Record<string, any> = {};
    connectors.forEach(id => {
      const saved = localStorage.getItem(`ryxhub_connector_${id}`);
      if (saved) {
        try {
          newStatus[id] = JSON.parse(saved);
        } catch {}
      }
    });
    setStatus(newStatus);
  }, []);

  const connectedCount = Object.keys(status).length;

  if (connectedCount === 0) {
    return (
      <div className="p-4 rounded-lg border border-dashed border-border text-center">
        <p className="text-sm text-muted-foreground">No connectors configured</p>
        <p className="text-xs text-muted-foreground mt-1">Click "Browse connectors" to get started</p>
      </div>
    );
  }

  const connectorNames: Record<string, string> = {
    github: "GitHub",
    gmail: "Gmail",
    google_drive: "Google Drive",
    google_calendar: "Google Calendar",
    notion: "Notion",
  };

  const connectorIcons: Record<string, string> = {
    github: "🐙",
    gmail: "📧",
    google_drive: "📁",
    google_calendar: "📅",
    notion: "📝",
  };

  return (
    <div className="space-y-2">
      {Object.entries(status).map(([id, data]) => (
        <div 
          key={id}
          className="flex items-center justify-between p-3 rounded-lg border border-border bg-card"
        >
          <div className="flex items-center gap-3">
            <span className="text-lg">{connectorIcons[id]}</span>
            <div>
              <div className="text-sm font-medium">{connectorNames[id]}</div>
              <div className="text-[10px] text-muted-foreground">
                {data.email || data.accountName || "Connected"}
              </div>
            </div>
          </div>
          <span className="text-[10px] text-[hsl(var(--success))] font-medium flex items-center gap-1">
            <Check className="w-3 h-3" />
            Connected
          </span>
        </div>
      ))}
    </div>
  );
}
