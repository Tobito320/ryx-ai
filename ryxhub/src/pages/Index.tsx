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
import { Settings } from "lucide-react";

function RyxHubApp() {
  const { activeView, sessions, selectedSessionId, selectSession, setActiveView } = useRyxHub();
  const [newSessionDialogOpen, setNewSessionDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<SidebarTab>("study");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    (localStorage.getItem('ryxhub_theme') as 'dark' | 'light') || 'dark'
  );

  // Apply theme
  useEffect(() => {
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(theme);
    localStorage.setItem('ryxhub_theme', theme);
  }, [theme]);

  // Auto-select session when switching to chat view
  useEffect(() => {
    if (activeView === "chat" && !selectedSessionId && sessions.length > 0) {
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
    const handleNewSessionClick = () => setNewSessionDialogOpen(true);
    window.addEventListener('new-session-click', handleNewSessionClick);
    return () => window.removeEventListener('new-session-click', handleNewSessionClick);
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

  return (
    <>
      <div className="h-screen w-screen bg-background text-foreground flex overflow-hidden">
        <LeftSidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          setActiveView={setActiveView}
        />

        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {activeView === "chat" && <ChatView />}
          {activeView === "documents" && <DocumentsView />}
          {activeView === "school" && <SchoolView />}
          {activeView === "studyspace" && <StudySpaceView />}
          {activeView === "settings" && <SettingsView />}
        </main>
      </div>

      {/* Fixed floating settings button */}
      <button
        onClick={() => setSettingsOpen(true)}
        className="fixed bottom-6 right-6 h-12 w-12 rounded-full bg-muted hover:bg-muted/80 border border-border shadow-lg flex items-center justify-center transition-colors z-40"
        title="Settings"
      >
        <Settings className="w-5 h-5 text-muted-foreground" />
      </button>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        theme={theme}
        onThemeChange={setTheme}
      />

      <NewSessionDialog
        open={newSessionDialogOpen}
        onOpenChange={setNewSessionDialogOpen}
        onSessionCreated={handleSessionCreated}
      />
    </>
  );
}

const Index = () => (
  <RyxHubProvider>
    <ExamProvider>
      <RyxHubApp />
    </ExamProvider>
  </RyxHubProvider>
);

export default Index;
