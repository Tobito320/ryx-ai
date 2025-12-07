/**
 * Overview Dashboard - Clean, simple personal dashboard
 */

import { useEffect, useState } from "react";
import { 
  Trash2, Calendar, FileText, Mail, 
  Sparkles, FolderOpen, GraduationCap, Sun, Moon, RefreshCw,
  ChevronLeft, ChevronRight, X, Eye, EyeOff
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useRyxHub } from "@/context/RyxHubContext";
import { cn } from "@/lib/utils";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8420";

interface TrashItem { type: string; formatted_date: string; weekday: string; date?: string; }
interface Document { name: string; path: string; category: string; }
interface Holiday { name: string; formatted: string; days_until?: number; date: string; }

export function OverviewDashboard() {
  const { setActiveView } = useRyxHub();
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [trash, setTrash] = useState<{ upcoming: TrashItem[]; tomorrow: TrashItem[] }>({ upcoming: [], tomorrow: [] });
  const [docs, setDocs] = useState<Document[]>([]);
  const [holidays, setHolidays] = useState<{ all: Holiday[]; upcoming: Holiday[]; next: Holiday | null }>({ all: [], upcoming: [], next: null });
  const [profile, setProfile] = useState({ name: "Tobi" });
  
  // Calendar modal state
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [calendarMonth, setCalendarMonth] = useState(new Date());
  const [showHolidays, setShowHolidays] = useState(true);
  const [showTrash, setShowTrash] = useState(true);

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
        setHolidays({ 
          all: data.holidays || [], 
          upcoming: data.upcoming || [], 
          next: data.next 
        });
      }
    } catch (error) {
      console.error("Dashboard load failed", error);
    }
    setLoading(false);
  };

  useEffect(() => { loadData(); }, []);

  const hour = currentTime.getHours();
  const greeting = hour < 12 ? "Guten Morgen" : hour < 18 ? "Guten Tag" : "Guten Abend";
  const trashColors: Record<string, string> = {
    'Restmüll': 'bg-gray-500', 'Restmüll wöchentlich': 'bg-gray-500',
    'Gelber Sack': 'bg-yellow-500', 'Papier': 'bg-blue-500', 
    'Altpapier': 'bg-blue-500', 'Bio': 'bg-green-500'
  };

  // Calendar helpers
  const getDaysInMonth = (date: Date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const days: Date[] = [];
    
    // Add padding for first week
    const startPadding = (firstDay.getDay() + 6) % 7; // Monday = 0
    for (let i = startPadding - 1; i >= 0; i--) {
      days.push(new Date(year, month, -i));
    }
    
    // Add days of month
    for (let i = 1; i <= lastDay.getDate(); i++) {
      days.push(new Date(year, month, i));
    }
    
    // Add padding for last week
    const endPadding = (7 - (days.length % 7)) % 7;
    for (let i = 1; i <= endPadding; i++) {
      days.push(new Date(year, month + 1, i));
    }
    
    return days;
  };

  const getEventsForDate = (date: Date) => {
    const dateStr = date.toISOString().split('T')[0];
    const events: { type: 'holiday' | 'trash'; name: string; color: string }[] = [];
    
    if (showHolidays) {
      holidays.all.forEach(h => {
        if (h.date === dateStr) {
          events.push({ type: 'holiday', name: h.name, color: 'bg-green-500' });
        }
      });
    }
    
    if (showTrash) {
      trash.upcoming.forEach(t => {
        // Convert DD.MM.YYYY to YYYY-MM-DD
        const parts = t.formatted_date.split('.');
        if (parts.length === 3) {
          const trashDate = `${parts[2]}-${parts[1]}-${parts[0]}`;
          if (trashDate === dateStr) {
            events.push({ type: 'trash', name: t.type, color: trashColors[t.type] || 'bg-gray-400' });
          }
        }
      });
    }
    
    return events;
  };

  const isToday = (date: Date) => {
    const today = new Date();
    return date.getDate() === today.getDate() && 
           date.getMonth() === today.getMonth() && 
           date.getFullYear() === today.getFullYear();
  };

  const isCurrentMonth = (date: Date) => {
    return date.getMonth() === calendarMonth.getMonth();
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
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Calendar className="w-4 h-4 text-green-500" />
              Feiertage NRW
            </CardTitle>
            <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => setCalendarOpen(true)}>
              Kalender →
            </Button>
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

      {/* Calendar Modal */}
      <Dialog open={calendarOpen} onOpenChange={setCalendarOpen}>
        <DialogContent className="sm:max-w-4xl max-h-[85vh] overflow-hidden">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Calendar className="w-5 h-5" />
                Kalender
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant={showHolidays ? "default" : "outline"}
                  size="sm"
                  onClick={() => setShowHolidays(!showHolidays)}
                  className="h-7 text-xs"
                >
                  {showHolidays ? <Eye className="w-3 h-3 mr-1" /> : <EyeOff className="w-3 h-3 mr-1" />}
                  Feiertage
                </Button>
                <Button
                  variant={showTrash ? "default" : "outline"}
                  size="sm"
                  onClick={() => setShowTrash(!showTrash)}
                  className="h-7 text-xs"
                >
                  {showTrash ? <Eye className="w-3 h-3 mr-1" /> : <EyeOff className="w-3 h-3 mr-1" />}
                  Müll
                </Button>
              </div>
            </DialogTitle>
          </DialogHeader>
          
          {/* Month Navigation */}
          <div className="flex items-center justify-between py-2">
            <Button variant="ghost" size="icon" onClick={() => setCalendarMonth(new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() - 1))}>
              <ChevronLeft className="w-5 h-5" />
            </Button>
            <h2 className="text-lg font-semibold">
              {calendarMonth.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' })}
            </h2>
            <Button variant="ghost" size="icon" onClick={() => setCalendarMonth(new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1))}>
              <ChevronRight className="w-5 h-5" />
            </Button>
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7 gap-1">
            {/* Weekday headers */}
            {['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'].map(day => (
              <div key={day} className="text-center text-xs font-medium text-muted-foreground py-2">
                {day}
              </div>
            ))}
            
            {/* Days */}
            {getDaysInMonth(calendarMonth).map((date, i) => {
              const events = getEventsForDate(date);
              return (
                <div
                  key={i}
                  className={cn(
                    "min-h-[80px] p-1 border rounded text-sm",
                    !isCurrentMonth(date) && "opacity-30",
                    isToday(date) && "border-primary border-2 bg-primary/5"
                  )}
                >
                  <div className={cn(
                    "text-right text-xs mb-1",
                    isToday(date) && "font-bold text-primary"
                  )}>
                    {date.getDate()}
                  </div>
                  <div className="space-y-0.5">
                    {events.slice(0, 3).map((event, j) => (
                      <div
                        key={j}
                        className={cn(
                          "text-[10px] px-1 py-0.5 rounded truncate text-white",
                          event.color
                        )}
                        title={event.name}
                      >
                        {event.name}
                      </div>
                    ))}
                    {events.length > 3 && (
                      <div className="text-[10px] text-muted-foreground">
                        +{events.length - 3} mehr
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex gap-4 pt-2 border-t mt-2">
            <div className="flex items-center gap-2 text-xs">
              <div className="w-3 h-3 rounded bg-green-500" />
              <span>Feiertage</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <div className="w-3 h-3 rounded bg-yellow-500" />
              <span>Gelber Sack</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <div className="w-3 h-3 rounded bg-gray-500" />
              <span>Restmüll</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <div className="w-3 h-3 rounded bg-blue-500" />
              <span>Papier</span>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
