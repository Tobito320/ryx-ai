/**
 * Overview Dashboard - Personal desktop with draggable widgets
 */

import { useEffect, useState, useCallback } from "react";
import { 
  Trash2, Calendar, FileText, Mail, Clock, 
  AlertTriangle, Sparkles, ExternalLink, FolderOpen,
  GraduationCap, Briefcase, Sun, Moon, GripVertical
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useRyxHub } from "@/context/RyxHubContext";
import { cn } from "@/lib/utils";
import GridLayout, { Layout } from "react-grid-layout";
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8420";

// Default layout for widgets
const DEFAULT_LAYOUT: Layout[] = [
  { i: "header", x: 0, y: 0, w: 12, h: 1, static: true },
  { i: "alerts", x: 0, y: 1, w: 12, h: 1, static: true },
  { i: "quickactions", x: 0, y: 2, w: 12, h: 2 },
  { i: "trash", x: 0, y: 4, w: 4, h: 4 },
  { i: "reminders", x: 4, y: 4, w: 4, h: 4 },
  { i: "documents", x: 8, y: 4, w: 4, h: 4 },
  { i: "school", x: 0, y: 8, w: 4, h: 4 },
  { i: "holidays", x: 4, y: 8, w: 4, h: 4 },
  { i: "work", x: 8, y: 8, w: 4, h: 4 },
];

interface TrashItem { type: string; formatted_date: string; weekday: string; }
interface Reminder { id: string; title: string; due: string; completed: boolean; }
interface Document { name: string; path: string; category: string; }
interface Holiday { name: string; formatted: string; days_until?: number; }
interface SchoolLesson { subject: string; start: string; room: string; cancelled: boolean; }

export function OverviewDashboard() {
  const { setActiveView } = useRyxHub();
  const [layout, setLayout] = useState<Layout[]>(() => {
    const saved = localStorage.getItem("dashboard-layout");
    return saved ? JSON.parse(saved) : DEFAULT_LAYOUT;
  });
  
  const [trashSchedule, setTrashSchedule] = useState<{ upcoming: TrashItem[]; tomorrow: TrashItem[] }>({ upcoming: [], tomorrow: [] });
  const [reminders, setReminders] = useState<{ items: Reminder[]; overdue: number }>({ items: [], overdue: 0 });
  const [recentDocs, setRecentDocs] = useState<Document[]>([]);
  const [profile, setProfile] = useState<{ name: string }>({ name: "" });
  const [currentTime, setCurrentTime] = useState(new Date());
  const [holidays, setHolidays] = useState<{ upcoming: Holiday[]; next: Holiday | null }>({ upcoming: [], next: null });
  const [schoolToday, setSchoolToday] = useState<{ lessons: SchoolLesson[]; configured: boolean }>({ lessons: [], configured: false });

  // Update time
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  // Load data
  useEffect(() => {
    const loadData = async () => {
      try {
        const [summaryRes, trashRes, docsRes, holidaysRes, schoolRes] = await Promise.all([
          fetch(`${API_BASE}/api/dashboard/summary`),
          fetch(`${API_BASE}/api/trash/schedule`),
          fetch(`${API_BASE}/api/documents/scan`),
          fetch(`${API_BASE}/api/holidays/nrw`),
          fetch(`${API_BASE}/api/webuntis/today`),
        ]);

        if (summaryRes.ok) {
          const data = await summaryRes.json();
          setProfile(data.profile || {});
          setReminders(data.reminders || { items: [], overdue: 0 });
        }
        if (trashRes.ok) {
          const data = await trashRes.json();
          setTrashSchedule({ upcoming: data.upcoming || [], tomorrow: data.tomorrow || [] });
        }
        if (docsRes.ok) {
          const data = await docsRes.json();
          setRecentDocs((data.documents || []).slice(0, 6));
        }
        if (holidaysRes.ok) {
          const data = await holidaysRes.json();
          setHolidays({ upcoming: data.upcoming || [], next: data.next });
        }
        if (schoolRes.ok) {
          const data = await schoolRes.json();
          setSchoolToday({ lessons: data.lessons || [], configured: !data.error?.includes("not configured") });
        }
      } catch (error) {
        console.error("Dashboard load failed", error);
      }
    };
    loadData();
    const interval = setInterval(loadData, 60000);
    return () => clearInterval(interval);
  }, []);

  const onLayoutChange = useCallback((newLayout: Layout[]) => {
    setLayout(newLayout);
    localStorage.setItem("dashboard-layout", JSON.stringify(newLayout));
  }, []);

  const resetLayout = () => {
    setLayout(DEFAULT_LAYOUT);
    localStorage.removeItem("dashboard-layout");
  };

  const greeting = currentTime.getHours() < 12 ? "Guten Morgen" : currentTime.getHours() < 18 ? "Guten Tag" : "Guten Abend";
  const trashColors: Record<string, string> = { 'Restmüll': 'bg-gray-500', 'Gelber Sack': 'bg-yellow-500', 'Papier': 'bg-blue-500', 'Bio': 'bg-green-500' };

  return (
    <div className="h-full overflow-auto bg-background p-2">
      <GridLayout
        className="layout"
        layout={layout}
        cols={12}
        rowHeight={40}
        width={1200}
        onLayoutChange={onLayoutChange}
        draggableHandle=".drag-handle"
        compactType="vertical"
        preventCollision={false}
      >
        {/* Header */}
        <div key="header" className="flex items-center justify-between px-4">
          <div>
            <h1 className="text-lg font-semibold">
              {greeting}, {profile.name || "Tobi"}!
              {currentTime.getHours() < 12 ? <Sun className="inline w-4 h-4 ml-2 text-yellow-500" /> : 
               currentTime.getHours() > 18 ? <Moon className="inline w-4 h-4 ml-2 text-blue-400" /> : null}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xl font-mono">{currentTime.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })}</span>
            <Button variant="ghost" size="sm" onClick={resetLayout} className="text-xs">Reset Layout</Button>
          </div>
        </div>

        {/* Alerts */}
        <div key="alerts" className="flex gap-2 px-4">
          {trashSchedule.tomorrow.length > 0 && (
            <div className="flex items-center gap-2 px-3 py-1 rounded bg-orange-500/10 border border-orange-500/20 text-orange-600 text-sm">
              <Trash2 className="w-3 h-3" />
              Morgen: {trashSchedule.tomorrow.map(t => t.type).join(", ")}
            </div>
          )}
          {reminders.overdue > 0 && (
            <div className="flex items-center gap-2 px-3 py-1 rounded bg-destructive/10 border border-destructive/20 text-destructive text-sm">
              <AlertTriangle className="w-3 h-3" />
              {reminders.overdue} überfällig
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div key="quickactions" className="px-4">
          <Card className="h-full">
            <CardContent className="p-2 flex gap-2 h-full items-center">
              <Button variant="outline" className="flex-1 h-12 flex-col gap-1" onClick={() => setActiveView("documents")}>
                <FolderOpen className="w-4 h-4" /><span className="text-xs">Dokumente</span>
              </Button>
              <Button variant="outline" className="flex-1 h-12 flex-col gap-1" onClick={() => setActiveView("chat")}>
                <Sparkles className="w-4 h-4" /><span className="text-xs">AI Chat</span>
              </Button>
              <Button variant="outline" className="flex-1 h-12 flex-col gap-1" onClick={() => window.open('https://webuntis.com', '_blank')}>
                <GraduationCap className="w-4 h-4" /><span className="text-xs">WebUntis</span>
              </Button>
              <Button variant="outline" className="flex-1 h-12 flex-col gap-1" onClick={() => window.open('https://mail.google.com', '_blank')}>
                <Mail className="w-4 h-4" /><span className="text-xs">Gmail</span>
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Trash Widget */}
        <div key="trash">
          <Card className="h-full overflow-hidden">
            <CardHeader className="p-2 pb-1 flex flex-row items-center">
              <GripVertical className="w-3 h-3 mr-1 cursor-move drag-handle text-muted-foreground" />
              <Trash2 className="w-3 h-3 mr-1 text-muted-foreground" />
              <CardTitle className="text-xs font-medium">Müllabfuhr</CardTitle>
            </CardHeader>
            <CardContent className="p-2 pt-0 overflow-auto" style={{ maxHeight: 'calc(100% - 32px)' }}>
              {trashSchedule.upcoming.slice(0, 4).map((item, i) => (
                <div key={i} className={cn("flex justify-between p-1 rounded text-xs mb-1", i === 0 && trashSchedule.tomorrow.length > 0 ? "bg-orange-500/10" : "bg-muted/30")}>
                  <div className="flex items-center gap-1">
                    <div className={cn("w-2 h-2 rounded-full", trashColors[item.type] || "bg-gray-400")} />
                    <span>{item.type}</span>
                  </div>
                  <span className="text-muted-foreground">{item.weekday}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Reminders Widget */}
        <div key="reminders">
          <Card className="h-full overflow-hidden">
            <CardHeader className="p-2 pb-1 flex flex-row items-center">
              <GripVertical className="w-3 h-3 mr-1 cursor-move drag-handle text-muted-foreground" />
              <Clock className="w-3 h-3 mr-1 text-muted-foreground" />
              <CardTitle className="text-xs font-medium">Erinnerungen</CardTitle>
            </CardHeader>
            <CardContent className="p-2 pt-0 overflow-auto" style={{ maxHeight: 'calc(100% - 32px)' }}>
              {reminders.items.slice(0, 4).map((item) => (
                <div key={item.id} className={cn("p-1 rounded text-xs mb-1", item.completed ? "opacity-50 line-through" : "bg-muted/30")}>
                  {item.title}
                </div>
              ))}
              {reminders.items.length === 0 && <p className="text-xs text-muted-foreground text-center py-2">Keine</p>}
            </CardContent>
          </Card>
        </div>

        {/* Documents Widget */}
        <div key="documents">
          <Card className="h-full overflow-hidden">
            <CardHeader className="p-2 pb-1 flex flex-row items-center justify-between">
              <div className="flex items-center">
                <GripVertical className="w-3 h-3 mr-1 cursor-move drag-handle text-muted-foreground" />
                <FileText className="w-3 h-3 mr-1 text-muted-foreground" />
                <CardTitle className="text-xs font-medium">Dokumente</CardTitle>
              </div>
              <Button variant="ghost" size="sm" className="h-5 px-1" onClick={() => setActiveView("documents")}>
                <ExternalLink className="w-3 h-3" />
              </Button>
            </CardHeader>
            <CardContent className="p-2 pt-0 grid grid-cols-2 gap-1 overflow-auto" style={{ maxHeight: 'calc(100% - 32px)' }}>
              {recentDocs.map((doc) => (
                <div key={doc.path} className="p-1 rounded bg-muted/30 text-xs truncate cursor-pointer hover:bg-muted/50" onClick={() => setActiveView("documents")}>
                  {doc.name}
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* School Widget */}
        <div key="school">
          <Card className="h-full overflow-hidden">
            <CardHeader className="p-2 pb-1 flex flex-row items-center">
              <GripVertical className="w-3 h-3 mr-1 cursor-move drag-handle text-muted-foreground" />
              <GraduationCap className="w-3 h-3 mr-1 text-blue-500" />
              <CardTitle className="text-xs font-medium">Berufsschule</CardTitle>
            </CardHeader>
            <CardContent className="p-2 pt-0 overflow-auto" style={{ maxHeight: 'calc(100% - 32px)' }}>
              {schoolToday.configured ? (
                schoolToday.lessons.length > 0 ? (
                  schoolToday.lessons.slice(0, 4).map((l, i) => (
                    <div key={i} className={cn("flex justify-between p-1 rounded text-xs mb-1", l.cancelled ? "bg-destructive/10 line-through" : "bg-muted/30")}>
                      <span>{l.start} {l.subject}</span>
                      <span className="text-muted-foreground">{l.room}</span>
                    </div>
                  ))
                ) : <p className="text-xs text-center py-2">Heute frei 🎉</p>
              ) : (
                <div className="text-center py-2">
                  <p className="text-xs text-muted-foreground">Nicht verbunden</p>
                  <Button variant="outline" size="sm" className="mt-1 h-6 text-xs" onClick={() => setActiveView("settings")}>Setup</Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Holidays Widget */}
        <div key="holidays">
          <Card className="h-full overflow-hidden">
            <CardHeader className="p-2 pb-1 flex flex-row items-center">
              <GripVertical className="w-3 h-3 mr-1 cursor-move drag-handle text-muted-foreground" />
              <Calendar className="w-3 h-3 mr-1 text-green-500" />
              <CardTitle className="text-xs font-medium">Feiertage NRW</CardTitle>
            </CardHeader>
            <CardContent className="p-2 pt-0 overflow-auto" style={{ maxHeight: 'calc(100% - 32px)' }}>
              {holidays.next && (
                <div className="p-1 rounded bg-green-500/10 border border-green-500/20 mb-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium">{holidays.next.name}</span>
                    <span className="text-green-600">in {holidays.next.days_until}d</span>
                  </div>
                </div>
              )}
              {holidays.upcoming.slice(1, 3).map((h, i) => (
                <div key={i} className="flex justify-between text-xs p-1 bg-muted/30 rounded mb-1">
                  <span>{h.name}</span>
                  <span className="text-muted-foreground">{h.formatted}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Work Widget */}
        <div key="work">
          <Card className="h-full overflow-hidden">
            <CardHeader className="p-2 pb-1 flex flex-row items-center">
              <GripVertical className="w-3 h-3 mr-1 cursor-move drag-handle text-muted-foreground" />
              <Briefcase className="w-3 h-3 mr-1 text-orange-500" />
              <CardTitle className="text-xs font-medium">Arbeit</CardTitle>
            </CardHeader>
            <CardContent className="p-2 pt-0 flex items-center justify-center h-full">
              <div className="text-center">
                <p className="text-xs text-muted-foreground">Kalender hinzufügen</p>
                <Button variant="outline" size="sm" className="mt-1 h-6 text-xs" onClick={() => setActiveView("settings")}>Setup</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </GridLayout>
    </div>
  );
}
