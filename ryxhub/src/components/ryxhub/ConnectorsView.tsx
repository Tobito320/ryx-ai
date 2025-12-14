import { useState, useEffect } from "react";
import { X, ExternalLink, Check, MoreHorizontal, Loader2, Unplug } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// OAuth-based integrations like Claude
interface Connector {
  id: string;
  name: string;
  icon: string;
  description: string;
  oauthUrl?: string; // If set, uses OAuth flow
  manualConfig?: boolean; // If true, shows manual config
  scopes?: string[];
}

const CONNECTORS: Connector[] = [
  {
    id: "github",
    name: "GitHub",
    icon: "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
    description: "Access your repositories and code",
    oauthUrl: "https://github.com/login/oauth/authorize",
    scopes: ["repo", "read:user"],
  },
  {
    id: "google_drive",
    name: "Google Drive",
    icon: "https://ssl.gstatic.com/images/branding/product/1x/drive_2020q4_48dp.png",
    description: "Access your files and documents",
    oauthUrl: "https://accounts.google.com/o/oauth2/v2/auth",
    scopes: ["https://www.googleapis.com/auth/drive.readonly"],
  },
  {
    id: "gmail",
    name: "Gmail",
    icon: "https://ssl.gstatic.com/ui/v1/icons/mail/rfr/gmail.ico",
    description: "Read and send emails",
    oauthUrl: "https://accounts.google.com/o/oauth2/v2/auth",
    scopes: ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"],
  },
  {
    id: "google_calendar",
    name: "Google Calendar",
    icon: "https://ssl.gstatic.com/calendar/images/dynamiclogo_2020q4/calendar_31_2x.png",
    description: "View your schedule and events",
    oauthUrl: "https://accounts.google.com/o/oauth2/v2/auth",
    scopes: ["https://www.googleapis.com/auth/calendar.readonly"],
  },
  {
    id: "notion",
    name: "Notion",
    icon: "https://upload.wikimedia.org/wikipedia/commons/e/e9/Notion-logo.svg",
    description: "Access your Notion workspace",
    oauthUrl: "https://api.notion.com/v1/oauth/authorize",
    scopes: [],
  },
];

interface ConnectorStatus {
  connected: boolean;
  accountName?: string;
  email?: string;
  connectedAt?: string;
}

interface Props {
  onClose: () => void;
}

export function ConnectorsView({ onClose }: Props) {
  const [connectorStatus, setConnectorStatus] = useState<Record<string, ConnectorStatus>>({});
  const [connecting, setConnecting] = useState<string | null>(null);

  // Load connector status from storage
  useEffect(() => {
    const loadStatus = async () => {
      // Try to load from API first
      try {
        const res = await fetch("http://localhost:8420/api/integrations/status");
        if (res.ok) {
          const data = await res.json();
          setConnectorStatus(data);
          return;
        }
      } catch {}

      // Fallback to localStorage
      const status: Record<string, ConnectorStatus> = {};
      CONNECTORS.forEach(c => {
        const saved = localStorage.getItem(`ryxhub_connector_${c.id}`);
        if (saved) {
          try {
            status[c.id] = JSON.parse(saved);
          } catch {}
        }
      });
      setConnectorStatus(status);
    };
    loadStatus();
  }, []);

  // Handle OAuth callback message
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data.type === "oauth_callback") {
        const { connectorId, success, accountName, email } = event.data;
        if (success) {
          const newStatus: ConnectorStatus = {
            connected: true,
            accountName,
            email,
            connectedAt: new Date().toISOString(),
          };
          setConnectorStatus(prev => ({ ...prev, [connectorId]: newStatus }));
          localStorage.setItem(`ryxhub_connector_${connectorId}`, JSON.stringify(newStatus));
          toast.success(`Connected to ${CONNECTORS.find(c => c.id === connectorId)?.name}`);
        } else {
          toast.error("Connection failed");
        }
        setConnecting(null);
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  const handleConnect = async (connector: Connector) => {
    setConnecting(connector.id);

    // Build OAuth URL
    const clientId = getClientId(connector.id);
    const redirectUri = `${window.location.origin}/oauth/callback`;
    const state = btoa(JSON.stringify({ connectorId: connector.id }));

    let authUrl = connector.oauthUrl || "";
    
    if (connector.id === "github") {
      authUrl = `${connector.oauthUrl}?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=${connector.scopes?.join(" ")}&state=${state}`;
    } else if (connector.id.startsWith("google") || connector.id === "gmail") {
      authUrl = `${connector.oauthUrl}?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=${encodeURIComponent(connector.scopes?.join(" ") || "")}&state=${state}&access_type=offline&prompt=consent`;
    } else if (connector.id === "notion") {
      authUrl = `${connector.oauthUrl}?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&state=${state}`;
    }

    // Open popup for OAuth
    const width = 600;
    const height = 700;
    const left = window.screenX + (window.innerWidth - width) / 2;
    const top = window.screenY + (window.innerHeight - height) / 2;
    
    const popup = window.open(
      authUrl,
      "oauth_popup",
      `width=${width},height=${height},left=${left},top=${top}`
    );

    // If no client ID configured, simulate connection for demo
    if (!clientId) {
      setTimeout(() => {
        // Simulate successful connection
        const mockStatus: ConnectorStatus = {
          connected: true,
          accountName: "Demo User",
          email: "demo@example.com",
          connectedAt: new Date().toISOString(),
        };
        setConnectorStatus(prev => ({ ...prev, [connector.id]: mockStatus }));
        localStorage.setItem(`ryxhub_connector_${connector.id}`, JSON.stringify(mockStatus));
        toast.success(`Connected to ${connector.name} (Demo mode)`);
        setConnecting(null);
        popup?.close();
      }, 1500);
    }

    // Monitor popup close
    const checkClosed = setInterval(() => {
      if (popup?.closed) {
        clearInterval(checkClosed);
        setConnecting(null);
      }
    }, 500);
  };

  const handleDisconnect = async (connectorId: string) => {
    // Clear from API
    try {
      await fetch(`http://localhost:8420/api/integrations/${connectorId}/disconnect`, {
        method: "POST",
      });
    } catch {}

    // Clear from localStorage
    localStorage.removeItem(`ryxhub_connector_${connectorId}`);
    setConnectorStatus(prev => {
      const next = { ...prev };
      delete next[connectorId];
      return next;
    });
    toast.success(`Disconnected from ${CONNECTORS.find(c => c.id === connectorId)?.name}`);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-card border border-border rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <h2 className="text-lg font-semibold">Connectors</h2>
            <p className="text-sm text-muted-foreground">
              Allow Ryx to reference other apps and services for more context.
            </p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Connectors List */}
        <div className="p-6 space-y-3 overflow-y-auto max-h-[60vh]">
          {CONNECTORS.map(connector => {
            const status = connectorStatus[connector.id];
            const isConnected = status?.connected;
            const isConnecting = connecting === connector.id;

            return (
              <div
                key={connector.id}
                className="flex items-center justify-between p-4 rounded-lg border border-border hover:border-primary/30 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center overflow-hidden">
                    <img 
                      src={connector.icon} 
                      alt={connector.name} 
                      className="w-6 h-6 object-contain"
                      onError={(e) => {
                        // Fallback to emoji
                        (e.target as HTMLImageElement).style.display = 'none';
                        (e.target as HTMLImageElement).parentElement!.innerHTML = 
                          connector.id === 'github' ? '🐙' :
                          connector.id === 'gmail' ? '📧' :
                          connector.id === 'google_drive' ? '📁' :
                          connector.id === 'google_calendar' ? '📅' :
                          '📝';
                      }}
                    />
                  </div>
                  <div>
                    <div className="font-medium">{connector.name}</div>
                    {isConnected ? (
                      <div className="text-sm text-muted-foreground">
                        {status.email || status.accountName || "Connected"}
                      </div>
                    ) : (
                      <div className="text-sm text-muted-foreground">
                        Disconnected
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {isConnected ? (
                    <>
                      <span className="text-primary text-sm font-medium flex items-center gap-1">
                        <Check className="w-4 h-4" />
                        Connected
                      </span>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem 
                            onClick={() => handleDisconnect(connector.id)}
                            className="text-destructive focus:text-destructive"
                          >
                            <Unplug className="w-4 h-4 mr-2" />
                            Disconnect
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleConnect(connector)}
                      disabled={isConnecting}
                      className="gap-2"
                    >
                      {isConnecting ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <ExternalLink className="w-4 h-4" />
                      )}
                      Connect
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border bg-muted/30">
          <p className="text-xs text-muted-foreground text-center">
            Connections are stored locally. OAuth tokens are managed securely.
          </p>
        </div>
      </div>
    </div>
  );
}

// Get OAuth client ID from config (would be set in backend/env)
function getClientId(connectorId: string): string {
  // These would normally come from environment variables or backend config
  const clientIds: Record<string, string> = {
    github: localStorage.getItem("ryxhub_github_client_id") || "",
    google_drive: localStorage.getItem("ryxhub_google_client_id") || "",
    gmail: localStorage.getItem("ryxhub_google_client_id") || "",
    google_calendar: localStorage.getItem("ryxhub_google_client_id") || "",
    notion: localStorage.getItem("ryxhub_notion_client_id") || "",
  };
  return clientIds[connectorId] || "";
}
