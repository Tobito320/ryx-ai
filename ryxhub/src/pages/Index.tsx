import { useState, useEffect } from "react";
import { LeftSidebar } from "@/components/ryxhub/LeftSidebar";
import { ChatView } from "@/components/ryxhub/ChatView";
import { SettingsView } from "@/components/ryxhub/SettingsView";
import { DashboardView } from "@/components/ryxhub/DashboardView";
import { DocumentsView } from "@/components/ryxhub/DocumentsView";
import { NewSessionDialog } from "@/components/ryxhub/NewSessionDialog";
import { RyxHubProvider, useRyxHub } from "@/context/RyxHubContext";
import { PanelLeft, Sun, Moon } from "lucide-react";

function RyxHubApp() {
  const { activeView, sessions, selectedSessionId, selectSession, setActiveView } = useRyxHub();
  const [newSessionDialogOpen, setNewSessionDialogOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [theme, setTheme] = useState<'dark' | 'light'>(() => 
    (localStorage.getItem('ryxhub_theme') as 'dark' | 'light') || 'dark'
  );

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
        setSidebarOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <>
      <div className="flex h-screen w-screen bg-background overflow-hidden">
        {/* Left Sidebar - Toggleable */}
        {sidebarOpen && (
          <div className="shrink-0">
            <LeftSidebar />
          </div>
        )}

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
          {/* Sidebar Toggle - Floating */}
          {!sidebarOpen && (
            <button
              onClick={() => setSidebarOpen(true)}
              className="absolute top-3 left-3 z-20 p-2 rounded-lg bg-card border border-border hover:bg-muted transition-colors"
              title="Show sidebar (Ctrl+B)"
            >
              <PanelLeft className="w-4 h-4" />
            </button>
          )}

          {/* Theme Toggle - Floating Top Right */}
          <button
            onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
            className="absolute top-3 right-3 z-20 p-2 rounded-lg bg-card border border-border hover:bg-muted transition-colors"
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          {/* Content - Full Height */}
          <main className="flex-1 overflow-hidden">
            {activeView === "dashboard" && <DashboardView />}
            {activeView === "chat" && <ChatView />}
            {activeView === "documents" && <DocumentsView />}
            {activeView === "settings" && <SettingsView />}
          </main>
        </div>
      </div>

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
      <RyxHubApp />
    </RyxHubProvider>
  );
};

export default Index;
