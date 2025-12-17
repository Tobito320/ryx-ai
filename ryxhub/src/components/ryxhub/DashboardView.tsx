import { useRef } from "react";
import { 
  MessageSquare, Zap, Plus, Clock, ChevronRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRyxHub } from "@/context/RyxHubContext";

export function DashboardView() {
  const { sessions, selectSession, setActiveView } = useRyxHub();
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleNewChat = () => {
    // Focus the prompt field in chat view
    window.dispatchEvent(new CustomEvent('new-session-click'));
    // Switch to chat view and focus input
    setTimeout(() => {
      setActiveView("chat");
      // Dispatch event to focus input in ChatView
      window.dispatchEvent(new CustomEvent('focus-chat-input'));
    }, 100);
  };

  // Get recent sessions (last 5)
  const recentSessions = [...sessions]
    .sort((a, b) => {
      const aTime = parseInt(localStorage.getItem(`session-lastused-${a.id}`) || '0');
      const bTime = parseInt(localStorage.getItem(`session-lastused-${b.id}`) || '0');
      return bTime - aTime;
    })
    .slice(0, 5);

  const formatTimeAgo = (sessionId: string) => {
    const lastUsed = parseInt(localStorage.getItem(`session-lastused-${sessionId}`) || '0');
    if (!lastUsed) return '';
    
    const diff = Date.now() - lastUsed;
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    if (days === 1) return 'Yesterday';
    return `${days} days ago`;
  };

  const handleOpenChat = (sessionId: string) => {
    selectSession(sessionId);
    setActiveView("chat");
  };

  return (
    <div className="h-full flex flex-col items-center justify-center px-4">
      <div className="max-w-3xl w-full flex flex-col items-center">
        {/* ChatGPT-style greeting */}
        <h1 className="text-2xl font-medium mb-8 text-center">
          What's on your mind today?
        </h1>

        {/* Input field similar to ChatGPT */}
        <div className="w-full max-w-3xl">
          <div className="relative flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                placeholder="Ask anything"
                className="w-full min-h-[52px] max-h-[200px] px-4 py-3 pr-12 rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm resize-none focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleNewChat();
                  }
                }}
              />
              <button
                onClick={handleNewChat}
                className="absolute right-3 bottom-3 h-8 w-8 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center justify-center hover:bg-[hsl(var(--primary))/0.9] transition-colors"
              >
                <Zap className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Recent Chats Section */}
        {recentSessions.length > 0 && (
          <div className="w-full max-w-3xl mt-8">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium text-[hsl(var(--muted-foreground))] flex items-center gap-2">
                <Clock className="w-4 h-4" />
                Recent Chats
              </h2>
              <Button onClick={handleNewChat} size="sm" variant="ghost" className="h-8 px-3 text-xs">
                <Plus className="w-3 h-3 mr-1" />
                New Chat
              </Button>
            </div>
            <div className="space-y-1">
              {recentSessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => handleOpenChat(session.id)}
                  className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-[hsl(var(--muted))] transition-colors text-left"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <MessageSquare className="w-4 h-4 text-[hsl(var(--muted-foreground))] flex-shrink-0" />
                    <span className="text-sm truncate">{session.name}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
                    <span>{formatTimeAgo(session.id)}</span>
                    <ChevronRight className="w-4 h-4" />
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
