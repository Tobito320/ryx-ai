import { useState, useEffect } from "react";
import { Mail, Loader2, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { gmailApi } from "@/lib/api/client";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export function GmailSettingsPanel() {
  const [authStatus, setAuthStatus] = useState<{
    authenticated: boolean;
    email: string | null;
    expired?: boolean;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    setLoading(true);
    try {
      const status = await gmailApi.getAuthStatus();
      setAuthStatus(status);
    } catch (error) {
      console.error("Failed to check Gmail auth status:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async () => {
    setConnecting(true);
    
    try {
      // Try to load client config from backend (optional - backend can load from file)
      let clientConfig: Record<string, any> | undefined;
      try {
        const configData = await gmailApi.loadConfig();
        clientConfig = configData.config;
      } catch (error) {
        // Backend will load from file system if not provided
        clientConfig = undefined;
      }
      
      // Start OAuth flow (backend will load config from file if not provided)
      const authResponse = await gmailApi.startAuth(clientConfig);
      const authUrl = authResponse.auth_url;
      
      // Open OAuth URL in new window
      const width = 600;
      const height = 700;
      const left = (window.screen.width - width) / 2;
      const top = (window.screen.height - height) / 2;
      
      const popup = window.open(
        authUrl,
        'Gmail OAuth',
        `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no,scrollbars=yes`
      );
      
      if (!popup) {
        toast.error("Popup blocked", {
          description: "Please allow popups for this site to complete OAuth"
        });
        setConnecting(false);
        return;
      }
      
      // Poll for popup closure (OAuth callback will close it)
      const checkClosed = setInterval(() => {
        if (popup.closed) {
          clearInterval(checkClosed);
          setConnecting(false);
          // Wait a moment for backend to process callback, then check status
          setTimeout(() => {
            checkAuthStatus();
          }, 1000);
        }
      }, 500);
      
      // Also listen for message from popup (if callback page sends one)
      const messageHandler = (event: MessageEvent) => {
        if (event.origin !== window.location.origin) return;
        if (event.data.type === 'gmail_oauth_success') {
          clearInterval(checkClosed);
          popup.close();
          setConnecting(false);
          checkAuthStatus();
          window.removeEventListener('message', messageHandler);
        }
      };
      window.addEventListener('message', messageHandler);
      
    } catch (error: any) {
      console.error("OAuth error:", error);
      if (error.message?.includes("not configured") || error.message?.includes("gmail_client_config.json")) {
        toast.error("Gmail OAuth not configured", {
          description: "Save gmail_client_config.json to data/ directory. See docs/GMAIL_OAUTH_SETUP.md",
          duration: 10000
        });
      } else {
        toast.error("Failed to start OAuth", {
          description: error.message || "Unknown error"
        });
      }
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await gmailApi.revokeAuth();
      setAuthStatus({ authenticated: false, email: null });
      toast.success("Gmail disconnected");
    } catch (error: any) {
      toast.error("Failed to disconnect", {
        description: error.message
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 p-3 rounded-lg border border-border bg-muted/30">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Checking Gmail status...</span>
      </div>
    );
  }

  if (authStatus?.authenticated) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between p-3 rounded-lg border border-green-500/20 bg-green-500/5">
          <div className="flex items-center gap-2">
            <Check className="w-4 h-4 text-green-500" />
            <div>
              <div className="text-sm font-medium">Gmail Connected</div>
              <div className="text-xs text-muted-foreground">{authStatus.email}</div>
            </div>
          </div>
          <Button 
            size="sm" 
            variant="ghost" 
            onClick={handleDisconnect}
            className="text-destructive hover:text-destructive"
          >
            Disconnect
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          ✅ You can now send emails directly from chat drafts
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-muted/30">
        <div className="flex items-center gap-2">
          <X className="w-4 h-4 text-muted-foreground" />
          <div>
            <div className="text-sm font-medium">Gmail Not Connected</div>
            <div className="text-xs text-muted-foreground">Connect to send emails</div>
          </div>
        </div>
        <Button 
          size="sm" 
          onClick={handleConnect}
          disabled={connecting}
        >
          {connecting ? (
            <>
              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              Connecting...
            </>
          ) : (
            <>
              <Mail className="w-3 h-3 mr-1" />
              Connect Gmail
            </>
          )}
        </Button>
      </div>
      <div className="space-y-1">
        <p className="text-xs text-muted-foreground">
          To enable Gmail integration:
        </p>
        <ol className="text-xs text-muted-foreground list-decimal list-inside space-y-0.5 ml-1">
          <li>Create Google Cloud Console project</li>
          <li>Enable Gmail API</li>
          <li>Create OAuth credentials</li>
          <li>Save to <code className="px-1 py-0.5 rounded bg-muted">data/gmail_client_config.json</code></li>
        </ol>
        <p className="text-xs text-blue-500 hover:text-blue-600 cursor-pointer mt-1">
          → See <span className="underline">docs/GMAIL_OAUTH_SETUP.md</span> for full guide
        </p>
      </div>
    </div>
  );
}
