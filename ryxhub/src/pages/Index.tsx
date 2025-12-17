import { useState, useEffect } from "react";
import { LeftSidebar, type SidebarTab } from "@/components/ryxhub/LeftSidebar";
import { ChatView } from "@/components/ryxhub/ChatView";
import { SettingsView } from "@/components/ryxhub/SettingsView";
import { DocumentsView } from "@/components/ryxhub/DocumentsView";
import { SchoolView } from "@/components/ryxhub/SchoolView";
import { StudySpaceView } from "@/components/ryxhub/StudySpaceView";
import { NewSessionDialog } from "@/components/ryxhub/NewSessionDialog";
import { SettingsModal } from "@/components/ryxhub/SettingsModal";
import { RyxHubProvider, useRyxHub } from "@/context/RyxHubContext";
import { ExamProvider } from "@/context/ExamContext";
import { cn } from "@/lib/utils";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useModels } from "@/hooks/useRyxApi";
import { getModelDisplayName } from "@/types/ryxhub";

function RyxHubApp() {
  const { activeView, sessions, selectedSessionId, selectSession, setActiveView, models: contextModels } = useRyxHub();
  const [newSessionDialogOpen, setNewSessionDialogOpen] = useState(false);
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

  // ChatGPT shows chat directly, no dashboard

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
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onOpenSettings={() => setSettingsOpen(true)}
          setActiveView={setActiveView}
        />

        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <header className="sticky top-0 z-10 flex items-center justify-between px-4 py-3 border-b border-[hsl(var(--border))] bg-[hsl(var(--background))]">
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
          </header>

          <main className="flex-1 overflow-hidden bg-[hsl(var(--background))]">
            {activeView === "chat" && <ChatView />}
            {activeView === "documents" && <DocumentsView />}
            {activeView === "school" && <SchoolView />}
            {activeView === "studyspace" && <StudySpaceView />}
            {activeView === "settings" && <SettingsView />}
          </main>
        </div>
      </div>

      {/* Settings Modal - Slide-in from right */}
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onNavigate={(page) => {
          // Handle navigation to different settings pages
          console.log(`Navigate to: ${page}`);
          if (page === "preferences" || page === "integrations") {
            setActiveView("settings");
          }
        }}
      />

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
