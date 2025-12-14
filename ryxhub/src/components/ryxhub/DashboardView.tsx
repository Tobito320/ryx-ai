import { useState, useEffect } from "react";
import { 
  MessageSquare, Brain, Search, Zap, Plus, Clock,
  MapPin, Settings as SettingsIcon, User, Cpu, ChevronRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRyxHub } from "@/context/RyxHubContext";

interface Stats {
  total_memories: number;
  persona_count: number;
  general_count: number;
}

interface LogStats {
  total_interactions: number;
  average_latency_ms: number;
  average_confidence: number;
  tool_usage: Record<string, number>;
}

interface PersonaMemory {
  id: number;
  category: string;
  fact: string;
  relevance_score: number;
}

export function DashboardView() {
  const { sessions, selectSession, setActiveView } = useRyxHub();
  const [memoryStats, setMemoryStats] = useState<Stats | null>(null);
  const [logStats, setLogStats] = useState<LogStats | null>(null);
  const [personaFacts, setPersonaFacts] = useState<PersonaMemory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      // Fetch memory stats
      const memRes = await fetch('http://localhost:8420/api/memory/stats');
      if (memRes.ok) {
        setMemoryStats(await memRes.json());
      }
      
      // Fetch log stats
      const logRes = await fetch('http://localhost:8420/api/logs/stats');
      if (logRes.ok) {
        setLogStats(await logRes.json());
      }
      
      // Fetch persona facts
      const personaRes = await fetch('http://localhost:8420/api/memory/persona?limit=5');
      if (personaRes.ok) {
        const data = await personaRes.json();
        setPersonaFacts(data.memories || []);
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    window.dispatchEvent(new CustomEvent('new-session-click'));
  };

  const handleOpenChat = (sessionId: string) => {
    selectSession(sessionId);
    setActiveView("chat");
  };

  // Get recent sessions (last 5)
  const recentSessions = [...sessions]
    .sort((a, b) => {
      const aTime = parseInt(localStorage.getItem(`session-lastused-${a.id}`) || '0');
      const bTime = parseInt(localStorage.getItem(`session-lastused-${b.id}`) || '0');
      return bTime - aTime;
    })
    .slice(0, 5);

  // Format persona fact for display
  const formatPersonaFact = (fact: string) => {
    // Extract key info
    if (fact.toLowerCase().includes('live')) return { icon: MapPin, text: fact };
    if (fact.toLowerCase().includes('name')) return { icon: User, text: fact };
    if (fact.toLowerCase().includes('use') || fact.toLowerCase().includes('tech')) return { icon: Cpu, text: fact };
    return { icon: Brain, text: fact };
  };

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

  return (
    <div className="h-full overflow-auto bg-background">
      <div className="max-w-3xl mx-auto px-6 py-12">
        {/* Welcome Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 mb-4">
            <Zap className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-2xl font-semibold mb-2">Welcome back, Tobi!</h1>
          <p className="text-muted-foreground">
            Your local AI assistant is ready.
          </p>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-4 mb-10">
          <StatCard
            icon={<Brain className="w-4 h-4" />}
            label="Facts Learned"
            value={memoryStats?.total_memories || 0}
            subtext={`${memoryStats?.persona_count || 0} about you`}
          />
          <StatCard
            icon={<Search className="w-4 h-4" />}
            label="Searches"
            value={logStats?.tool_usage?.['web_search'] || 0}
          />
          <StatCard
            icon={<MessageSquare className="w-4 h-4" />}
            label="Messages"
            value={logStats?.total_interactions || 0}
            subtext={`${Math.round(logStats?.average_latency_ms || 0)}ms avg`}
          />
        </div>

        {/* Your Persona */}
        {personaFacts.length > 0 && (
          <section className="mb-10">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <User className="w-4 h-4" />
                Your Persona
              </h2>
              <button
                onClick={() => setActiveView("settings")}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                Edit
              </button>
            </div>
            <div className="space-y-2">
              {personaFacts.map((fact) => {
                const formatted = formatPersonaFact(fact.fact);
                const Icon = formatted.icon;
                return (
                  <div
                    key={fact.id}
                    className="flex items-center gap-3 px-4 py-2.5 rounded-lg bg-card border border-border"
                  >
                    <Icon className="w-4 h-4 text-primary flex-shrink-0" />
                    <span className="text-sm">
                      {fact.fact.replace(/^(User'?s?|user'?s?)\s*/i, '').replace(/^(User\s+)/i, '')}
                    </span>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Recent Chats */}
        <section className="mb-10">
          <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2 mb-3">
            <Clock className="w-4 h-4" />
            Recent Chats
          </h2>
          
          {recentSessions.length > 0 ? (
            <div className="space-y-1">
              {recentSessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => handleOpenChat(session.id)}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-lg hover:bg-muted/50 transition-colors text-left group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <MessageSquare className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                    <span className="text-sm truncate">{session.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      {formatTimeAgo(session.id)}
                    </span>
                    <ChevronRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No chats yet</p>
            </div>
          )}
        </section>

        {/* New Chat CTA */}
        <div className="text-center">
          <Button
            onClick={handleNewChat}
            size="lg"
            className="gap-2 px-8"
          >
            <Plus className="w-4 h-4" />
            New Chat
          </Button>
        </div>
      </div>
    </div>
  );
}

// Helper Components

function StatCard({ 
  icon, 
  label, 
  value, 
  subtext 
}: { 
  icon: React.ReactNode; 
  label: string; 
  value: number; 
  subtext?: string;
}) {
  return (
    <div className="p-4 rounded-xl border border-border bg-card">
      <div className="flex items-center gap-2 text-muted-foreground mb-2">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <div className="text-2xl font-semibold">{value}</div>
      {subtext && (
        <div className="text-xs text-muted-foreground mt-0.5">{subtext}</div>
      )}
    </div>
  );
}
