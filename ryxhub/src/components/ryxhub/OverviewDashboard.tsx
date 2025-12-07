/**
 * Overview Dashboard - Clean, simple personal dashboard
 */

import { useEffect, useState } from "react";
import { 
  Trash2, Calendar, FileText, Mail, Clock, 
  AlertTriangle, Sparkles, FolderOpen,
  GraduationCap, Sun, Moon, RefreshCw
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useRyxHub } from "@/context/RyxHubContext";
import { cn } from "@/lib/utils";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8420";

interface TrashItem { type: string; formatted_date: string; weekday: string; }
interface Document { name: string; path: string; category: string; }
interface Holiday { name: string; formatted: string; days_until?: number; }

export function OverviewDashboard() {
  const { setActiveView } = useRyxHub();
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [trash, setTrash] = useState<{ upcoming: TrashItem[]; tomorrow: TrashItem[] }>({ upcoming: [], tomorrow: [] });
  const [docs, setDocs] = useState<Document[]>([]);
  const [holidays, setHolidays] = useState<{ upcoming: Holiday[]; next: Holiday | null }>({ upcoming: [], next: null });
  const [profile, setProfile] = useState({ name: "Tobi" });

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [summaryRes, trashRes, docsRes, holidaysRes] = await Promise.all([
        fetch(`${API_BASE}/api/dashboard/summary`).catch(() => null),
        fetch(`${API_BASE}/api/trash/schedule`).catch(() => null),
        fetch(`${API_BASE}/api/documents/scan`).catch(() => null),
        fetch(`${API_BASE}/api/holidays/nrw`).catch(() => null),
      ]);

      if (summaryRes?.ok) {
        const data = await summaryRes.json();
        setProfile(data.profile || { name: "Tobi" });
      }
      if (trashRes?.ok) {
        const data = await trashRes.json();
        setTrash({ upcoming: data.upcoming || [], tomorrow: data.tomorrow || [] });
      }
      if (docsRes?.ok) {
        const data = await docsRes.json();
        setDocs((data.documents || []).slice(0, 6));
      }
      if (holidaysRes?.ok) {
        const data = await holidaysRes.json();
        setHolidays({ upcoming: data.upcoming || [], next: data.next });
      }
    } catch (error) {
      console.error("Dashboard load failed", error);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  const hour = currentTime.getHours();
  const greeting = hour < 12 ? "Guten Morgen" : hour < 18 ? "Guten Tag" : "Guten Abend";
  const trashColors: Record<string, string> = {
    'Restmüll': 'bg-gray-500', 'Restmüll wöchentlich': 'bg-gray-500',
    'Gelber Sack': 'bg-yellow-500', 'Papier': 'bg-blue-500', 
    'Altpapier': 'bg-blue-500', 'Bio': 'bg-green-500'
  };

  return (
    <div className="h-full overflow-auto bg-background p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            {greeting}, {profile.name || "Tobi"}!
            {hour < 12 ? <Sun className="w-5 h-5 text-yellow-500" /> : 
             hour > 18 ? <Moon className="w-5 h-5 text-blue-400" /> : null}
          </h1>
          <p className="text-muted-foreground text-sm">
            {currentTime.toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-3xl font-mono font-light">
            {currentTime.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })}
          </span>
          <Button variant="ghost" size="icon" onClick={loadData} disabled={loading}>
            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          </Button>
        </div>
      </div>

      {/* Alerts */}
      {trash.tomorrow.length > 0 && (
        <div className="mb-4 p-3 rounded-lg bg-orange-500/10 border border-orange-500/30 flex items-center gap-2">
          <Trash2 className="w-5 h-5 text-orange-500" />
          <span className="font-medium text-orange-600">Morgen abholen: {trash.tomorrow.map(t => t.type).join(", ")}</span>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <Button variant="outline" className="h-16 flex flex-col gap-1" onClick={() => setActiveView("documents")}>
          <FolderOpen className="w-5 h-5" />
          <span className="text-xs">Dokumente</span>
        </Button>
        <Button variant="outline" className="h-16 flex flex-col gap-1" onClick={() => setActiveView("chat")}>
          <Sparkles className="w-5 h-5" />
          <span className="text-xs">AI Chat</span>
        </Button>
        <Button variant="outline" className="h-16 flex flex-col gap-1" onClick={() => window.open('https://webuntis.com', '_blank')}>
          <GraduationCap className="w-5 h-5" />
          <span className="text-xs">WebUntis</span>
        </Button>
        <Button variant="outline" className="h-16 flex flex-col gap-1" onClick={() => window.open('https://mail.google.com', '_blank')}>
          <Mail className="w-5 h-5" />
          <span className="text-xs">Gmail</span>
        </Button>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Trash Schedule */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Trash2 className="w-4 h-4 text-muted-foreground" />
              Müllabfuhr
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {trash.upcoming.length === 0 ? (
              <p className="text-sm text-muted-foreground">Keine Termine geladen</p>
            ) : (
              trash.upcoming.slice(0, 5).map((item, i) => (
                <div key={i} className={cn(
                  "flex justify-between items-center p-2 rounded text-sm",
                  trash.tomorrow.some(t => t.type === item.type) ? "bg-orange-500/10" : "bg-muted/50"
                )}>
                  <div className="flex items-center gap-2">
                    <div className={cn("w-3 h-3 rounded-full", trashColors[item.type] || "bg-gray-400")} />
                    <span>{item.type}</span>
                  </div>
                  <span className="text-muted-foreground text-xs">{item.weekday}, {item.formatted_date}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Holidays */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Calendar className="w-4 h-4 text-green-500" />
              Feiertage NRW
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {holidays.next && (
              <div className="p-2 rounded bg-green-500/10 border border-green-500/20">
                <div className="flex justify-between items-center">
                  <span className="font-medium text-sm">{holidays.next.name}</span>
                  <span className="text-green-600 text-xs font-medium">
                    in {holidays.next.days_until} Tagen
                  </span>
                </div>
                <span className="text-xs text-muted-foreground">{holidays.next.formatted}</span>
              </div>
            )}
            {holidays.upcoming.slice(1, 4).map((h, i) => (
              <div key={i} className="flex justify-between items-center p-2 rounded bg-muted/50 text-sm">
                <span>{h.name}</span>
                <span className="text-muted-foreground text-xs">{h.formatted}</span>
              </div>
            ))}
            {!holidays.next && holidays.upcoming.length === 0 && (
              <p className="text-sm text-muted-foreground">Keine Feiertage geladen</p>
            )}
          </CardContent>
        </Card>

        {/* Recent Documents */}
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <FileText className="w-4 h-4 text-muted-foreground" />
              Letzte Dokumente
            </CardTitle>
            <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => setActiveView("documents")}>
              Alle →
            </Button>
          </CardHeader>
          <CardContent className="space-y-1">
            {docs.length === 0 ? (
              <p className="text-sm text-muted-foreground">Keine Dokumente</p>
            ) : (
              docs.map((doc) => (
                <div 
                  key={doc.path} 
                  className="p-2 rounded bg-muted/50 text-sm truncate cursor-pointer hover:bg-muted transition-colors"
                  onClick={() => setActiveView("documents")}
                >
                  {doc.name}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
