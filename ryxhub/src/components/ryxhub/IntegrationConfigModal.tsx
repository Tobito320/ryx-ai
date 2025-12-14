import { useState } from "react";
import { X, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface IntegrationConfig {
  name: string;
  emoji: string;
  fields: { key: string; label: string; type: 'text' | 'password'; placeholder: string }[];
  testEndpoint?: string;
}

const INTEGRATIONS: Record<string, IntegrationConfig> = {
  webuntis: {
    name: "WebUntis",
    emoji: "📅",
    fields: [
      { key: "school", label: "School Code", type: "text", placeholder: "e.g., school123" },
      { key: "server", label: "Server", type: "text", placeholder: "e.g., neilo.webuntis.com" },
      { key: "username", label: "Username", type: "text", placeholder: "Your username" },
      { key: "password", label: "Password", type: "password", placeholder: "Your password" },
    ],
    testEndpoint: "/api/integrations/webuntis/test"
  },
  gmail: {
    name: "Gmail",
    emoji: "📧",
    fields: [
      { key: "email", label: "Email Address", type: "text", placeholder: "you@gmail.com" },
      { key: "app_password", label: "App Password", type: "password", placeholder: "16-char app password" },
    ],
    testEndpoint: "/api/integrations/gmail/test"
  },
  github: {
    name: "GitHub",
    emoji: "🐙",
    fields: [
      { key: "token", label: "Personal Access Token", type: "password", placeholder: "ghp_..." },
    ],
    testEndpoint: "/api/integrations/github/test"
  },
  notion: {
    name: "Notion",
    emoji: "📝",
    fields: [
      { key: "token", label: "Integration Token", type: "password", placeholder: "secret_..." },
    ],
    testEndpoint: "/api/integrations/notion/test"
  }
};

interface Props {
  integrationId: string;
  onClose: () => void;
}

export function IntegrationConfigModal({ integrationId, onClose }: Props) {
  const config = INTEGRATIONS[integrationId];
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null);
  const [saving, setSaving] = useState(false);

  if (!config) {
    return null;
  }

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    
    try {
      // Simulate test - replace with actual API call
      const res = await fetch(`http://localhost:8420${config.testEndpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      if (res.ok) {
        setTestResult('success');
        toast.success(`${config.name} connection successful!`);
      } else {
        setTestResult('error');
        toast.error(`${config.name} connection failed`);
      }
    } catch (error) {
      // Fallback for demo - simulate success after delay
      await new Promise(r => setTimeout(r, 1000));
      setTestResult('error');
      toast.error(`${config.name} not configured on server yet`);
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    
    try {
      const res = await fetch(`http://localhost:8420/api/integrations/${integrationId}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      if (res.ok) {
        toast.success(`${config.name} configuration saved`);
        onClose();
      } else {
        // Save to localStorage as fallback
        localStorage.setItem(`ryxhub_integration_${integrationId}`, JSON.stringify(formData));
        toast.success(`${config.name} configuration saved locally`);
        onClose();
      }
    } catch (error) {
      // Save to localStorage as fallback
      localStorage.setItem(`ryxhub_integration_${integrationId}`, JSON.stringify(formData));
      toast.success(`${config.name} configuration saved locally`);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const handleDisconnect = () => {
    localStorage.removeItem(`ryxhub_integration_${integrationId}`);
    setFormData({});
    setTestResult(null);
    toast.success(`${config.name} disconnected`);
  };

  // Load saved config on mount
  useState(() => {
    const saved = localStorage.getItem(`ryxhub_integration_${integrationId}`);
    if (saved) {
      try {
        setFormData(JSON.parse(saved));
      } catch {}
    }
  });

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-card border border-border rounded-xl shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{config.emoji}</span>
            <h2 className="text-lg font-semibold">Configure {config.name}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-muted transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <div className="px-6 py-4 space-y-4">
          {config.fields.map((field) => (
            <div key={field.key}>
              <label className="block text-sm font-medium mb-1.5">
                {field.label}
              </label>
              <Input
                type={field.type}
                placeholder={field.placeholder}
                value={formData[field.key] || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, [field.key]: e.target.value }))}
              />
            </div>
          ))}

          {/* Test Result */}
          {testResult && (
            <div className={cn(
              "flex items-center gap-2 px-3 py-2 rounded-lg text-sm",
              testResult === 'success' ? "bg-[hsl(var(--success))]/10 text-[hsl(var(--success))]" : "bg-destructive/10 text-destructive"
            )}>
              {testResult === 'success' ? (
                <>
                  <CheckCircle className="w-4 h-4" />
                  Connection successful
                </>
              ) : (
                <>
                  <AlertCircle className="w-4 h-4" />
                  Connection failed
                </>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-muted/30">
          <button
            onClick={handleDisconnect}
            className="text-sm text-muted-foreground hover:text-destructive transition-colors"
          >
            Disconnect
          </button>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleTest}
              disabled={testing || Object.keys(formData).length === 0}
            >
              {testing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                  Testing...
                </>
              ) : (
                'Test Connection'
              )}
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={saving || Object.keys(formData).length === 0}
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save'
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
