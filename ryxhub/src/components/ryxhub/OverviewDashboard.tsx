/**
 * Overview Dashboard - Personal desktop overview
 * Shows trash schedule, calendars, quick actions, recent documents
 */

import { useEffect, useState } from "react";
import { 
  Trash2, Calendar, FileText, Mail, Clock, 
  AlertTriangle, Sparkles, ExternalLink, FolderOpen,
  GraduationCap, Briefcase, Sun, Moon
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useRyxHub } from "@/context/RyxHubContext";
import { cn } from "@/lib/utils";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8420";

interface TrashItem {
  type: string;
  date: string;
  formatted_date: string;
  weekday: string;
}

interface Reminder {
  id: string;
  title: string;
  due: string;
  completed: boolean;
}

interface Document {
  name: string;
  path: string;
  type: string;
  category: string;
  modifiedAt: string;
}

export function OverviewDashboard() {
  const { setActiveView } = useRyxHub();
  const [trashSchedule, setTrashSchedule] = useState<{ upcoming: TrashItem[]; tomorrow: TrashItem[] }>({ upcoming: [], tomorrow: [] });
  const [reminders, setReminders] = useState<{ items: Reminder[]; overdue: number; today: number }>({ items: [], overdue: 0, today: 0 });
  const [recentDocs, setRecentDocs] = useState<Document[]>([]);
  const [profile, setProfile] = useState<{ name: string; address: string }>({ name: "", address: "" });
  const [currentTime, setCurrentTime] = useState(new Date());

  // Update time every minute
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  // Load data
  useEffect(() => {
    const loadData = async () => {
      try {
        // Get dashboard summary
        const summaryRes = await fetch(`${API_BASE}/api/dashboard/summary`);
        if (summaryRes.ok) {
          const data = await summaryRes.json();
          setProfile(data.profile || {});
          setReminders(data.reminders || { items: [], overdue: 0, today: 0 });
        }

        // Get trash schedule
        const trashRes = await fetch(`${API_BASE}/api/trash/schedule`);
        if (trashRes.ok) {
          const data = await trashRes.json();
          setTrashSchedule({ upcoming: data.upcoming || [], tomorrow: data.tomorrow || [] });
        }

        // Get recent documents
        const docsRes = await fetch(`${API_BASE}/api/documents/scan`);
        if (docsRes.ok) {
          const data = await docsRes.json();
          setRecentDocs((data.documents || []).slice(0, 6));
        }
      } catch (error) {
        console.error("Failed to load dashboard data", error);
      }
    };

    loadData();
    const interval = setInterval(loadData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const greeting = () => {
    const hour = currentTime.getHours();
    if (hour < 12) return "Guten Morgen";
    if (hour < 18) return "Guten Tag";
    return "Guten Abend";
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('de-DE', { 
      weekday: 'long', 
      day: 'numeric', 
      month: 'long' 
    });
  };

  const trashColors: Record<string, string> = {
    'Restmüll': 'bg-gray-500',
    'Gelber Sack': 'bg-yellow-500',
    'Papier': 'bg-blue-500',
    'Bio': 'bg-green-500',
    'Glas': 'bg-emerald-500',
  };

  return (
    <div className="h-full flex flex-col bg-background overflow-auto">
      {/* Header with greeting */}
      <div className="px-6 py-4 border-b bg-card/30 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">
              {greeting()}, {profile.name || "Tobi"}! 
              {currentTime.getHours() < 12 ? <Sun className="inline w-5 h-5 ml-2 text-yellow-500" /> : 
               currentTime.getHours() > 18 ? <Moon className="inline w-5 h-5 ml-2 text-blue-400" /> : null}
            </h1>
            <p className="text-sm text-muted-foreground">{formatDate(currentTime)}</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-mono">{currentTime.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })}</p>
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {/* Alerts Row */}
          {(trashSchedule.tomorrow.length > 0 || reminders.overdue > 0) && (
            <div className="flex gap-3 flex-wrap">
              {trashSchedule.tomorrow.length > 0 && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-orange-500/10 border border-orange-500/20 text-orange-600">
                  <Trash2 className="w-4 h-4" />
                  <span className="text-sm font-medium">
                    Morgen: {trashSchedule.tomorrow.map(t => t.type).join(", ")}
                  </span>
                </div>
              )}
              {reminders.overdue > 0 && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="text-sm font-medium">{reminders.overdue} überfällige Erinnerungen</span>
                </div>
              )}
            </div>
          )}

          {/* Quick Actions */}
          <div className="grid grid-cols-4 gap-2">
            <Button 
              variant="outline" 
              className="h-16 flex-col gap-1"
              onClick={() => setActiveView("documents")}
            >
              <FolderOpen className="w-5 h-5" />
              <span className="text-xs">Dokumente</span>
            </Button>
            <Button 
              variant="outline" 
              className="h-16 flex-col gap-1"
              onClick={() => setActiveView("chat")}
            >
              <Sparkles className="w-5 h-5" />
              <span className="text-xs">AI Chat</span>
            </Button>
            <Button 
              variant="outline" 
              className="h-16 flex-col gap-1"
              onClick={() => window.open('https://webuntis.com', '_blank')}
            >
              <GraduationCap className="w-5 h-5" />
              <span className="text-xs">WebUntis</span>
            </Button>
            <Button 
              variant="outline" 
              className="h-16 flex-col gap-1"
              onClick={() => window.open('https://mail.google.com', '_blank')}
            >
              <Mail className="w-5 h-5" />
              <span className="text-xs">Gmail</span>
            </Button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Trash Schedule */}
            <Card className="border-border bg-card/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Trash2 className="w-4 h-4 text-muted-foreground" />
                  Müllabfuhr
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {trashSchedule.upcoming.slice(0, 5).map((item, i) => (
                  <div 
                    key={i}
                    className={cn(
                      "flex items-center justify-between p-2 rounded-md",
                      i === 0 && trashSchedule.tomorrow.length > 0 ? "bg-orange-500/10" : "bg-muted/30"
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        trashColors[item.type] || "bg-gray-400"
                      )} />
                      <span className="text-sm">{item.type}</span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {item.weekday}, {item.formatted_date}
                    </div>
                  </div>
                ))}
                {trashSchedule.upcoming.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-4">Keine Termine geladen</p>
                )}
              </CardContent>
            </Card>

            {/* Reminders */}
            <Card className="border-border bg-card/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Clock className="w-4 h-4 text-muted-foreground" />
                  Erinnerungen
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {reminders.items.slice(0, 5).map((item) => (
                  <div 
                    key={item.id}
                    className={cn(
                      "flex items-center justify-between p-2 rounded-md",
                      item.completed ? "opacity-50" : "bg-muted/30"
                    )}
                  >
                    <span className={cn("text-sm", item.completed && "line-through")}>
                      {item.title}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {item.due ? new Date(item.due).toLocaleDateString('de-DE') : ''}
                    </span>
                  </div>
                ))}
                {reminders.items.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-4">Keine Erinnerungen</p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Recent Documents */}
          <Card className="border-border bg-card/50">
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <FileText className="w-4 h-4 text-muted-foreground" />
                Letzte Dokumente
              </CardTitle>
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => setActiveView("documents")}
              >
                Alle anzeigen
                <ExternalLink className="w-3 h-3 ml-1" />
              </Button>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
                {recentDocs.map((doc) => (
                  <div
                    key={doc.path}
                    className="p-2 rounded-md bg-muted/30 hover:bg-muted/50 cursor-pointer transition-colors"
                    onClick={() => setActiveView("documents")}
                  >
                    <FileText className="w-6 h-6 mb-1 text-muted-foreground" />
                    <p className="text-xs font-medium truncate">{doc.name}</p>
                    <p className="text-[10px] text-muted-foreground capitalize">{doc.category}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* School/Work Calendar placeholder */}
          <Card className="border-border bg-card/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Calendar className="w-4 h-4 text-muted-foreground" />
                Kalender
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-2">
                <div className="p-3 rounded-md bg-muted/30 text-center">
                  <GraduationCap className="w-5 h-5 mx-auto mb-1 text-blue-500" />
                  <p className="text-xs font-medium">Berufsschule</p>
                  <p className="text-[10px] text-muted-foreground">WebUntis verbinden</p>
                </div>
                <div className="p-3 rounded-md bg-muted/30 text-center">
                  <Briefcase className="w-5 h-5 mx-auto mb-1 text-orange-500" />
                  <p className="text-xs font-medium">Arbeit</p>
                  <p className="text-[10px] text-muted-foreground">Kalender hinzufügen</p>
                </div>
                <div className="p-3 rounded-md bg-muted/30 text-center">
                  <Calendar className="w-5 h-5 mx-auto mb-1 text-green-500" />
                  <p className="text-xs font-medium">Feiertage NRW</p>
                  <p className="text-[10px] text-muted-foreground">Automatisch</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </ScrollArea>
    </div>
  );
}
