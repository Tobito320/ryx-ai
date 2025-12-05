import { useState, useEffect } from "react";
import { LeftSidebar } from "@/components/ryxhub/LeftSidebar";
import { ChatView } from "@/components/ryxhub/ChatView";
import { WorkflowCanvasEnhanced } from "@/components/ryxhub/WorkflowCanvasEnhanced";
import { RightInspector } from "@/components/ryxhub/RightInspector";
import { DashboardView } from "@/components/ryxhub/DashboardView";
import { SettingsView } from "@/components/ryxhub/SettingsView";
import { ViewToggle } from "@/components/ryxhub/ViewToggle";
import { ModelDialog } from "@/components/ryxhub/ModelDialog";
import { NewSessionDialog } from "@/components/ryxhub/NewSessionDialog";
import { RyxHubProvider, useRyxHub } from "@/context/RyxHubContext";

interface Model {
  id: string;
  name: string;
  status: "online" | "offline" | "loading";
  provider: string;
}

function RyxHubApp() {
  const { activeView, selectSession, setActiveView } = useRyxHub();
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [modelDialogOpen, setModelDialogOpen] = useState(false);
  const [newSessionDialogOpen, setNewSessionDialogOpen] = useState(false);

  useEffect(() => {
    // Listen for model click events
    const handleModelClick = (e: Event) => {
      const customEvent = e as CustomEvent<Model>;
      setSelectedModel(customEvent.detail);
      setModelDialogOpen(true);
    };

    // Listen for new session click events
    const handleNewSessionClick = () => {
      setNewSessionDialogOpen(true);
    };

    window.addEventListener('model-click', handleModelClick as EventListener);
    window.addEventListener('new-session-click', handleNewSessionClick);

    return () => {
      window.removeEventListener('model-click', handleModelClick as EventListener);
      window.removeEventListener('new-session-click', handleNewSessionClick);
    };
  }, []);

  const handleSessionCreated = (sessionId: string) => {
    selectSession(sessionId);
    setActiveView("chat");
  };

  return (
    <>
      <div className="flex h-screen w-full bg-background overflow-hidden">
        {/* Left Sidebar */}
        <LeftSidebar />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Top Bar with View Toggle */}
          <header className="h-16 px-6 border-b border-border bg-card/30 backdrop-blur-sm flex items-center justify-between shrink-0">
            <ViewToggle />
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[hsl(var(--success))]/10 border border-[hsl(var(--success))]/20">
                <span className="w-2 h-2 rounded-full bg-[hsl(var(--success))] animate-pulse" />
                <span className="text-xs font-medium text-[hsl(var(--success))]">All Systems Online</span>
              </div>
            </div>
          </header>

          {/* Content */}
          <main className="flex-1 flex min-h-0">
            <div className="flex-1 min-w-0">
              {activeView === "dashboard" && <DashboardView />}
              {activeView === "chat" && <ChatView />}
              {activeView === "workflow" && <WorkflowCanvasEnhanced />}
              {activeView === "settings" && <SettingsView />}
            </div>
          </main>
        </div>
      </div>

      {/* Dialogs */}
      <ModelDialog
        model={selectedModel}
        open={modelDialogOpen}
        onOpenChange={setModelDialogOpen}
        onModelUpdate={() => {
          // Models are automatically refreshed in context via polling
          console.log('Model updated, will refresh automatically');
        }}
      />

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
      <RyxHubApp />
    </RyxHubProvider>
  );
};

export default Index;
