import { useState, useEffect } from "react";
import { LeftSidebar, type SidebarTab } from "@/components/ryxhub/LeftSidebar";
import { ChatView } from "@/components/ryxhub/ChatView";
import { SettingsView } from "@/components/ryxhub/SettingsView";
import { DashboardView } from "@/components/ryxhub/DashboardView";
import { DocumentsView } from "@/components/ryxhub/DocumentsView";
import { SchoolView } from "@/components/ryxhub/SchoolView";
import { StudySpaceView } from "@/components/ryxhub/StudySpaceView";
import { NewSessionDialog } from "@/components/ryxhub/NewSessionDialog";
import { RyxHubProvider, useRyxHub } from "@/context/RyxHubContext";
import { ExamProvider } from "@/context/ExamContext";
import { Sun, Moon, X, Zap, Settings, User, Shield, Database } from "lucide-react";
import { cn } from "@/lib/utils";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useModels } from "@/hooks/useRyxApi";
import { getModelDisplayName } from "@/types/ryxhub";

function RyxHubApp() {
  const { activeView, sessions, selectedSessionId, selectSession, setActiveView, models: contextModels } = useRyxHub();
  const [newSessionDialogOpen, setNewSessionDialogOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState<SidebarTab>("study");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [theme, setTheme] = useState<'dark' | 'light'>(() => 
    (localStorage.getItem('ryxhub_theme') as 'dark' | 'light') || 'dark'
  );
  const { data: apiModels } = useModels();
  const allModels = apiModels || contextModels;
  const availableModels = allModels.filter(m => m.status === 'online');

  // Apply theme
  useEffect(() => {
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(theme);
    localStorage.setItem('ryxhub_theme', theme);
  }, [theme]);

  // Show dashboard when no session selected
  useEffect(() => {
    if (activeView === "chat" && !selectedSessionId && sessions.length === 0) {
      setActiveView("dashboard");
    }
  }, [activeView, selectedSessionId, sessions.length, setActiveView]);

  // Auto-select session when switching to chat view
  useEffect(() => {
    if (activeView === "chat" && !selectedSessionId && sessions.length > 0) {
      // Find most recently used session
      let mostRecent = sessions[0];
      let mostRecentTime = 0;
      
      for (const session of sessions) {
        const lastUsed = parseInt(localStorage.getItem(`session-lastused-${session.id}`) || '0');
        if (lastUsed > mostRecentTime) {
          mostRecentTime = lastUsed;
          mostRecent = session;
        }
      }
      
      selectSession(mostRecent.id);
    }
  }, [activeView, selectedSessionId, sessions, selectSession]);

  useEffect(() => {
    // Listen for new session click events
    const handleNewSessionClick = () => {
      setNewSessionDialogOpen(true);
    };

    window.addEventListener('new-session-click', handleNewSessionClick);
    return () => {
      window.removeEventListener('new-session-click', handleNewSessionClick);
    };
  }, []);

  const handleSessionCreated = (sessionId: string) => {
    selectSession(sessionId);
    setActiveView("chat");
  };

  // Keyboard shortcut for sidebar toggle
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'b' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setSidebarCollapsed(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (activeView === "chat") setActiveTab("study");
    if (activeView === "school") setActiveTab("exams");
    if (activeView === "documents") setActiveTab("documents");
  }, [activeView]);

  // Set initial model
  useEffect(() => {
    if (availableModels.length > 0 && !selectedModel) {
      const lastModel = localStorage.getItem('ryxhub_last_model');
      const modelExists = lastModel && availableModels.some(m => m.id === lastModel);
      setSelectedModel(modelExists ? lastModel : availableModels[0].id);
    }
  }, [availableModels, selectedModel]);

  const handleModelChange = (modelId: string) => {
    setSelectedModel(modelId);
    localStorage.setItem('ryxhub_last_model', modelId);
  };

  return (
    <>
      <div className="min-h-screen w-screen bg-[hsl(var(--background))] text-[hsl(var(--foreground))] flex overflow-hidden">
        <LeftSidebar
          collapsed={sidebarCollapsed}
          onToggleCollapsed={() => setSidebarCollapsed((prev) => !prev)}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onOpenSettings={() => setSettingsOpen(true)}
          setActiveView={setActiveView}
        />

        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <header className="sticky top-0 z-10 flex items-center justify-between px-4 py-3 border-b border-[hsl(var(--border))] bg-[hsl(var(--background))]/95 backdrop-blur-sm">
            {sidebarCollapsed ? (
              <button
                onClick={() => setSidebarCollapsed(false)}
                className="h-8 w-8 rounded-lg flex items-center justify-center hover:bg-[hsl(var(--muted))] transition-colors"
                aria-label="Open sidebar"
              >
                <Zap className="w-5 h-5 text-[hsl(var(--primary))]" />
              </button>
            ) : (
              <div className="flex items-center gap-2">
                {availableModels.length > 0 ? (
                  <Select value={selectedModel || availableModels[0]?.id} onValueChange={handleModelChange}>
                    <SelectTrigger className="h-8 border-0 bg-transparent hover:bg-[hsl(var(--muted))] px-2 text-sm font-medium">
                      <SelectValue placeholder="Ryx" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableModels.map((model) => (
                        <SelectItem key={model.id} value={model.id}>
                          <div className="flex items-center gap-2">
                            <span className={cn("w-1.5 h-1.5 rounded-full", model.status === "online" ? "bg-green-500" : "bg-gray-400")} />
                            {getModelDisplayName(model.id)}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <span className="text-sm font-medium">Ryx</span>
                )}
              </div>
            )}
          </header>

          <main className="flex-1 overflow-hidden bg-[hsl(var(--background))]">
            {activeView === "dashboard" && <DashboardView />}
            {activeView === "chat" && <ChatView />}
            {activeView === "documents" && <DocumentsView />}
            {activeView === "school" && <SchoolView />}
            {activeView === "studyspace" && <StudySpaceView />}
            {activeView === "settings" && <SettingsView />}
          </main>
        </div>
      </div>

      <SettingsModal open={settingsOpen} onOpenChange={setSettingsOpen} />

      {/* New Session Dialog */}
      <NewSessionDialog
        open={newSessionDialogOpen}
        onOpenChange={setNewSessionDialogOpen}
        onSessionCreated={handleSessionCreated}
      />
    </>
  );
}

const Index = () => {
  return (
    <RyxHubProvider>
      <ExamProvider>
        <RyxHubApp />
      </ExamProvider>
    </RyxHubProvider>
  );
};

export default Index;

function SettingsModal({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [activeTab, setActiveTab] = useState<string>("general");
  const { setActiveView } = useRyxHub();

  // Listen for settings tab change event
  useEffect(() => {
    const handleTabChange = (e: CustomEvent) => {
      if (e.detail) {
        setActiveTab(e.detail);
      }
    };
    window.addEventListener('settings-tab', handleTabChange as EventListener);
    return () => window.removeEventListener('settings-tab', handleTabChange as EventListener);
  }, []);

  const tabs = [
    { id: "general", label: "General", icon: Settings },
    { id: "notifications", label: "Notifications", icon: Sun },
    { id: "personalizations", label: "Personalization", icon: User },
    { id: "connectors", label: "Apps & Connectors", icon: Zap },
    { id: "data", label: "Data controls", icon: Database },
    { id: "security", label: "Security", icon: Shield },
    { id: "parental", label: "Parental controls", icon: User },
    { id: "account", label: "Account", icon: User },
  ];


  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl w-full h-[85vh] p-0 flex flex-col bg-[hsl(var(--background))] [&>button]:hidden left-[50%] top-[50%] translate-x-[-50%] translate-y-[-50%]">
        <div className="flex h-full">
          {/* Left Sidebar - Tabs */}
          <div className="w-64 border-r border-[hsl(var(--border))] flex flex-col">
            <div className="p-4 border-b border-[hsl(var(--border))] flex items-center justify-between">
              <h2 className="text-lg font-semibold">Settings</h2>
              <button
                onClick={() => onOpenChange(false)}
                className="h-8 w-8 rounded-lg flex items-center justify-center hover:bg-[hsl(var(--muted))] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto py-2">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      "w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors",
                      activeTab === tab.id
                        ? "bg-[hsl(var(--muted))] text-[hsl(var(--foreground))]"
                        : "text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))] hover:text-[hsl(var(--foreground))]"
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Content Area */}
          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === "general" && <GeneralSettings />}
            {activeTab === "notifications" && <NotificationsSettings />}
            {activeTab === "personalizations" && <PersonalizationSettings />}
            {activeTab === "connectors" && <ConnectorsSettings />}
            {activeTab === "data" && <DataControlsSettings />}
            {activeTab === "security" && <SecuritySettings />}
            {activeTab === "parental" && <ParentalControlsSettings />}
            {activeTab === "account" && <AccountSettings />}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Placeholder components for each settings tab
function GeneralSettings() {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold">General</h3>
      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-2 block">Appearance</label>
          <Select defaultValue="light">
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="light">Light</SelectItem>
              <SelectItem value="dark">Dark</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-sm font-medium mb-2 block">Accent color</label>
          <Select defaultValue="default">
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="default">Default</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-sm font-medium mb-2 block">Language</label>
          <Select defaultValue="auto">
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">Auto-detect</SelectItem>
              <SelectItem value="de">German</SelectItem>
              <SelectItem value="en">English</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );
}

function NotificationsSettings() {
  return <div><h3 className="text-lg font-semibold">Notifications</h3></div>;
}

function PersonalizationSettings() {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold">Personalization</h3>
      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-2 block">Base style and tone</label>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mb-2">
            Set the style and tone of how Ryx responds to you. This doesn't impact Ryx's capabilities.
          </p>
          <Select defaultValue="efficient">
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="efficient">Efficient</SelectItem>
              <SelectItem value="balanced">Balanced</SelectItem>
              <SelectItem value="detailed">Detailed</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-sm font-medium mb-2 block">Custom instructions</label>
          <textarea
            className="w-full min-h-[100px] p-3 border border-[hsl(var(--border))] rounded-lg bg-[hsl(var(--background))] text-sm"
            placeholder="Enter custom instructions..."
          />
        </div>
        <div>
          <label className="text-sm font-medium mb-2 block">About you</label>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-[hsl(var(--muted-foreground))] mb-1 block">Nickname</label>
              <input
                type="text"
                className="w-full p-2 border border-[hsl(var(--border))] rounded-lg bg-[hsl(var(--background))] text-sm"
                placeholder="Your nickname"
              />
            </div>
            <div>
              <label className="text-xs text-[hsl(var(--muted-foreground))] mb-1 block">Occupation</label>
              <input
                type="text"
                className="w-full p-2 border border-[hsl(var(--border))] rounded-lg bg-[hsl(var(--background))] text-sm"
                placeholder="Your occupation"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ConnectorsSettings() {
  return <div><h3 className="text-lg font-semibold">Apps & Connectors</h3></div>;
}

function DataControlsSettings() {
  return <div><h3 className="text-lg font-semibold">Data controls</h3></div>;
}

function SecuritySettings() {
  return <div><h3 className="text-lg font-semibold">Security</h3></div>;
}

function ParentalControlsSettings() {
  return <div><h3 className="text-lg font-semibold">Parental controls</h3></div>;
}

function AccountSettings() {
  return <div><h3 className="text-lg font-semibold">Account</h3></div>;
}
