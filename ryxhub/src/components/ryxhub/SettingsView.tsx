import { useState, useEffect } from "react";
import { 
  Settings, Server, Cpu, HardDrive, Activity, Zap, 
  RefreshCw, Power, PowerOff, Database, Clock,
  TrendingUp, BarChart3, Loader2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useModels, useLoadModel, useHealth } from "@/hooks/useRyxApi";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { RAGManagement } from "@/components/ryxhub/RAGManagement";

interface VLLMMetrics {
  available: boolean;
  memory?: {
    resident_gb?: number;
    virtual_gb?: number;
  };
  requests?: {
    running?: number;
    waiting?: number;
    successful?: number;
  };
  tokens?: {
    prompt_total?: number;
    generation_total?: number;
    total?: number;
  };
  cache?: {
    kv_usage_percent?: number;
    prefix_hits?: number;
    prefix_queries?: number;
    hit_rate_percent?: number;
  };
  model?: {
    name?: string;
    short_name?: string;
  };
  error?: string;
}

export function SettingsView() {
  const { data: models, isLoading: modelsLoading, refetch: refetchModels } = useModels();
  const { data: health } = useHealth();
  const loadModelMutation = useLoadModel();
  
  const [metrics, setMetrics] = useState<VLLMMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Fetch metrics
  const fetchMetrics = async () => {
    try {
      setMetricsLoading(true);
      const response = await fetch("http://localhost:8420/api/metrics/vllm");
      const data = await response.json();
      setMetrics(data);
    } catch (error) {
      setMetrics({ available: false, error: "Failed to fetch metrics" });
    } finally {
      setMetricsLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    
    if (autoRefresh) {
      const interval = setInterval(fetchMetrics, 2000); // 2 second refresh
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const handleLoadModel = async (modelId: string) => {
    try {
      await loadModelMutation.mutateAsync(modelId);
      refetchModels();
    } catch (error) {
      // Error handled by mutation
    }
  };

  const formatNumber = (n: number | undefined) => {
    if (n === undefined) return "0";
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
    return n.toString();
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
              Monitor vLLM performance and manage models
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={cn(autoRefresh && "bg-primary/10")}
            >
              <RefreshCw className={cn("w-4 h-4 mr-1", autoRefresh && "animate-spin")} />
              {autoRefresh ? "Auto" : "Manual"}
            </Button>
            <Button variant="outline" size="sm" onClick={fetchMetrics} disabled={metricsLoading}>
              {metricsLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            </Button>
          </div>
        </div>

        {/* System Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* vLLM Status */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Server className="w-4 h-4 text-primary" />
                vLLM Server
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <span className={cn(
                  "w-3 h-3 rounded-full",
                  health?.vllm_status === "online" ? "bg-green-500" : "bg-red-500"
                )} />
                <span className="text-lg font-semibold capitalize">
                  {health?.vllm_status || "Unknown"}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Port 8001
              </p>
            </CardContent>
          </Card>

          {/* Memory Usage */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-blue-500" />
                Memory Usage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg font-semibold">
                {metrics?.memory?.resident_gb?.toFixed(1) || "0"} GB
              </div>
              <p className="text-xs text-muted-foreground">
                Virtual: {metrics?.memory?.virtual_gb?.toFixed(1) || "0"} GB
              </p>
            </CardContent>
          </Card>

          {/* Active Requests */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Activity className="w-4 h-4 text-green-500" />
                Requests
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-2">
                <span className="text-lg font-semibold">
                  {metrics?.requests?.running || 0}
                </span>
                <span className="text-sm text-muted-foreground">running</span>
              </div>
              <p className="text-xs text-muted-foreground">
                {metrics?.requests?.waiting || 0} waiting · {metrics?.requests?.successful || 0} completed
              </p>
            </CardContent>
          </Card>

          {/* Tokens Processed */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Zap className="w-4 h-4 text-yellow-500" />
                Tokens Processed
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg font-semibold">
                {formatNumber(metrics?.tokens?.total)}
              </div>
              <p className="text-xs text-muted-foreground">
                {formatNumber(metrics?.tokens?.prompt_total)} prompt · {formatNumber(metrics?.tokens?.generation_total)} generated
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Cache & Performance */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* KV Cache */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Database className="w-4 h-4 text-purple-500" />
                KV Cache Usage
              </CardTitle>
              <CardDescription>GPU key-value cache utilization</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Usage</span>
                  <span className="font-medium">{metrics?.cache?.kv_usage_percent?.toFixed(2) || 0}%</span>
                </div>
                <Progress value={metrics?.cache?.kv_usage_percent || 0} className="h-2" />
              </div>
            </CardContent>
          </Card>

          {/* Prefix Cache */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-cyan-500" />
                Prefix Cache
              </CardTitle>
              <CardDescription>Cache hit rate for repeated prompts</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Hit Rate</span>
                  <span className="font-medium">{metrics?.cache?.hit_rate_percent?.toFixed(1) || 0}%</span>
                </div>
                <Progress value={metrics?.cache?.hit_rate_percent || 0} className="h-2" />
                <p className="text-xs text-muted-foreground">
                  {metrics?.cache?.prefix_hits || 0} hits / {metrics?.cache?.prefix_queries || 0} queries
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Models Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="w-5 h-5" />
              Available Models ({models?.length || 0} total, {models?.filter(m => m.status === "online").length || 0} loaded)
            </CardTitle>
            <CardDescription>
              vLLM currently loads one model at startup. To switch models, restart the vLLM container with: <code className="text-xs bg-muted px-1 py-0.5 rounded">docker-compose restart vllm</code> and update the MODEL environment variable.
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
                      model.status === "online" 
                        ? "bg-primary/5 border-primary/20" 
                        : "bg-muted/30 border-border"
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "w-3 h-3 rounded-full",
                        model.status === "online" ? "bg-green-500" : "bg-gray-400"
                      )} />
                      <div>
                        <div className="font-medium">{model.name}</div>
                        <div className="text-xs text-muted-foreground font-mono">{model.id}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={model.status === "online" ? "default" : "secondary"}>
                        {model.status}
                      </Badge>
                      {model.status === "online" ? (
                        <Button variant="ghost" size="sm" disabled>
                          <Power className="w-4 h-4 mr-1" />
                          Active
                        </Button>
                      ) : (
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleLoadModel(model.id)}
                          disabled={loadModelMutation.isPending}
                        >
                          <PowerOff className="w-4 h-4 mr-1" />
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

        {/* Current Model Info */}
        {metrics?.model?.name && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <BarChart3 className="w-4 h-4" />
                Currently Loaded Model
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <div>
                  <div className="font-semibold">{metrics.model.short_name}</div>
                  <div className="text-xs text-muted-foreground font-mono">{metrics.model.name}</div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* RAG Management Section */}
        <div className="mt-8">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Database className="w-5 h-5" />
            Knowledge Base Management
          </h2>
          <RAGManagement />
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
