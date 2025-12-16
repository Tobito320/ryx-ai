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
import { Sun, Moon, X } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";

function RyxHubApp() {
  const { activeView, sessions, selectedSessionId, selectSession, setActiveView } = useRyxHub();
  const [newSessionDialogOpen, setNewSessionDialogOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
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

  return (
    <>
      <div className="min-h-screen w-screen bg-[hsl(var(--background))] text-[hsl(var(--foreground))] flex overflow-hidden">
        <LeftSidebar
          collapsed={sidebarCollapsed}
          onToggleCollapsed={() => setSidebarCollapsed((prev) => !prev)}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onOpenSettings={() => setSettingsOpen(true)}
        />

        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <header className="sticky top-0 z-10 flex items-center justify-between px-6 py-4 border-b border-[hsl(var(--border))] bg-[hsl(var(--background))]/95 backdrop-blur-sm">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[hsl(var(--accent))]/10 border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--accent))]">
                <span className="text-lg font-semibold">✚</span>
              </div>
              <div>
                <div className="text-sm uppercase tracking-[0.08em] text-[hsl(var(--muted-foreground))]">RyxHub • {activeTab === "study" ? "Study" : activeTab === "exams" ? "Exams" : "Documents"}</div>
                <div className="text-xl font-semibold">Dein intelligenter Lernassistent</div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
                className="h-10 w-10 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] flex items-center justify-center hover:border-[hsl(var(--primary))]"
                title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
              >
                {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              </button>
            </div>
          </header>

          <main className="flex-1 overflow-hidden">
            <div className="h-full overflow-y-auto px-8 py-8 md:py-10 bg-[hsl(var(--background))]">
              <div className="h-full view-transition rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] shadow-[0_20px_60px_-40px_rgba(0,0,0,0.6)]">
                <div className="h-full">
                  {activeView === "dashboard" && <DashboardView />}
                  {activeView === "chat" && <ChatView />}
                  {activeView === "documents" && <DocumentsView />}
                  {activeView === "school" && <SchoolView />}
                  {activeView === "studyspace" && <StudySpaceView />}
                  {activeView === "settings" && <SettingsView />}
                </div>
              </div>
            </div>
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
  const sections = [
    {
      title: "GENERAL",
      items: [
        { label: "Profile", icon: "→" },
        { label: "Preferences", icon: "→" },
        { label: "Appearance", icon: "→" },
      ],
    },
    {
      title: "ACCOUNT",
      items: [
        { label: "Billing", icon: "→" },
        { label: "Security", icon: "→" },
        { label: "Data & Privacy", icon: "→" },
      ],
    },
    {
      title: "ADVANCED",
      items: [
        { label: "API Keys", icon: "→" },
        { label: "Integrations", icon: "→" },
      ],
    },
    {
      title: "ACTIONS",
      divider: true,
      items: [
        { label: "Help & Support", icon: "?" },
        { label: "Log out", icon: "🚪" },
      ],
    },
  ];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-[400px] max-w-full bg-[hsl(var(--secondary))] border-l border-[hsl(var(--primary))] px-0 text-[hsl(var(--foreground))]"
      >
        <SheetHeader className="px-6 py-4 border-b border-[hsl(var(--border))]">
          <SheetTitle className="text-lg font-semibold">Einstellungen</SheetTitle>
          <SheetDescription className="text-[hsl(var(--muted-foreground))]">
            Passe RyxHub an deine Arbeitsweise an.
          </SheetDescription>
        </SheetHeader>

        <div className="h-full overflow-y-auto px-6 py-5 space-y-6">
          {sections.map((section) => (
            <div key={section.title} className="space-y-3">
              {section.divider && <Separator className="bg-[hsl(var(--border))]" />}
              <div className="text-[11px] font-semibold tracking-[0.08em] text-[hsl(var(--muted-foreground))]">
                {section.title}
              </div>
              <div className="space-y-1">
                {section.items.map((item) => (
                  <button
                    key={item.label}
                    className="w-full flex items-center justify-between px-3 py-3 rounded-lg text-sm bg-[hsl(var(--card))] border border-[hsl(var(--border))] hover:border-[hsl(var(--primary))] hover:text-[hsl(var(--foreground))] transition-colors"
                  >
                    <span>{item.label}</span>
                    <span className="text-[hsl(var(--muted-foreground))] text-xs">{item.icon}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
          <button
            onClick={() => onOpenChange(false)}
            className="w-full mt-4 inline-flex items-center justify-center gap-2 rounded-lg border border-[hsl(var(--border))] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:border-[hsl(var(--primary))]"
          >
            <X className="w-4 h-4" />
            Schließen
          </button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
