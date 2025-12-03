import { LeftSidebar } from "@/components/ryxhub/LeftSidebar";
import { ChatView } from "@/components/ryxhub/ChatView";
import { WorkflowCanvas } from "@/components/ryxhub/WorkflowCanvas";
import { RightInspector } from "@/components/ryxhub/RightInspector";
import { DashboardView } from "@/components/ryxhub/DashboardView";
import { ViewToggle } from "@/components/ryxhub/ViewToggle";
import { RyxHubProvider, useRyxHub } from "@/context/RyxHubContext";

function RyxHubApp() {
  const { activeView } = useRyxHub();

  return (
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
            {activeView === "workflow" && <WorkflowCanvas />}
          </div>

          {/* Right Inspector - Only show in workflow view */}
          {activeView === "workflow" && <RightInspector />}
        </main>
      </div>
    </div>
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
