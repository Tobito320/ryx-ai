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
    <div className="h-full overflow-y-auto px-8 py-10">
      <div className="max-w-5xl mx-auto space-y-10">
        <div className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-8 py-10 text-center shadow-[0_20px_60px_-40px_rgba(0,0,0,0.6)]">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-[hsl(var(--primary))/0.12] border border-[hsl(var(--primary))/0.3]">
            <span className="text-4xl">⚡</span>
          </div>
          <h1 className="text-3xl font-semibold mb-2">Willkommen bei RyxHub</h1>
          <p className="text-[hsl(var(--muted-foreground))] mb-6 text-base">
            Dein intelligenter Lernassistent. Starte sofort einen neuen Space oder öffne dein Dashboard.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Button
              onClick={() => setActiveView("studyspace")}
              className="px-6 h-11 border-[hsl(var(--border))] bg-[hsl(var(--card))] hover:bg-[hsl(var(--primary))/0.12] hover:border-[hsl(var(--primary))]"
              variant="outline"
            >
              Neuen Study Space erstellen
            </Button>
            <Button
              onClick={() => setActiveView("dashboard")}
              className="px-6 h-11 border-[hsl(var(--border))] bg-[hsl(var(--card))] hover:bg-[hsl(var(--primary))/0.12] hover:border-[hsl(var(--primary))]"
              variant="outline"
            >
              Zum Dashboard
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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

        {personaFacts.length > 0 && (
          <section className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
                <User className="w-4 h-4" />
                Persona
              </div>
              <button
                onClick={() => setActiveView("settings")}
                className="text-xs text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
              >
                Edit
              </button>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {personaFacts.map((fact) => {
                const formatted = formatPersonaFact(fact.fact);
                const Icon = formatted.icon;
                return (
                  <div
                    key={fact.id}
                    className="flex items-center gap-3 px-4 py-3 rounded-lg bg-[hsl(var(--secondary))] border border-[hsl(var(--border))]"
                  >
                    <Icon className="w-4 h-4 text-[hsl(var(--primary))] flex-shrink-0" />
                    <span className="text-sm">
                      {fact.fact.replace(/^(User'?s?|user'?s?)\s*/i, '').replace(/^(User\s+)/i, '')}
                    </span>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        <section className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-[hsl(var(--muted-foreground))] flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Recent Chats
            </h2>
            <Button onClick={handleNewChat} size="sm" variant="outline" className="h-9 px-3">
              <Plus className="w-4 h-4 mr-2" />
              Neuer Chat
            </Button>
          </div>
          {recentSessions.length > 0 ? (
            <div className="space-y-1">
              {recentSessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => handleOpenChat(session.id)}
                  className="w-full flex items-center justify-between px-3 py-3 rounded-lg hover:bg-[hsl(var(--secondary))] transition-colors text-left"
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
          ) : (
            <div className="text-center py-8 text-[hsl(var(--muted-foreground))]">
              <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-60" />
              <p className="text-sm">Keine Chats</p>
            </div>
          )}
        </section>
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
