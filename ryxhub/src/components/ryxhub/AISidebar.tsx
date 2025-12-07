/**
 * AI Sidebar - Resizable assistant panel
 * Clean, functional, concise responses
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { cn } from "@/lib/utils";
import { log } from "@/lib/logger";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Sparkles,
  FileText,
  Send,
  Copy,
  Check,
  Loader2,
  Clock,
  AlertTriangle,
  Trash2,
  Calendar,
  Bot,
  User,
  GripVertical,
  Search,
  Brain,
  Globe,
  Mail,
} from "lucide-react";
import { toast } from "sonner";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8420";

interface Document {
  name: string;
  path: string;
  type: string;
  category: string;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface AISidebarProps {
  document: Document | null;
  onClose?: () => void;
  summary?: any;
}

export function AISidebar({ document: selectedDoc, onClose, summary }: AISidebarProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [userMessage, setUserMessage] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [copied, setCopied] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  
  // Sidebar width state for resizing
  const [sidebarWidth, setSidebarWidth] = useState(340);
  const isResizing = useRef(false);
  const sidebarRef = useRef<HTMLDivElement>(null);
  
  // Tool toggles - persist in localStorage
  const [useMemory, setUseMemory] = useState(() => {
    const saved = localStorage.getItem('ryx-tool-memory');
    return saved !== null ? saved === 'true' : true;
  });
  const [useSearch, setUseSearch] = useState(() => {
    const saved = localStorage.getItem('ryx-tool-search');
    return saved === 'true';
  });
  const [useScrape, setUseScrape] = useState(() => {
    const saved = localStorage.getItem('ryx-tool-scrape');
    return saved === 'true';
  });

  // Save tool toggles
  useEffect(() => {
    localStorage.setItem('ryx-tool-memory', String(useMemory));
  }, [useMemory]);
  useEffect(() => {
    localStorage.setItem('ryx-tool-search', String(useSearch));
  }, [useSearch]);
  useEffect(() => {
    localStorage.setItem('ryx-tool-scrape', String(useScrape));
  }, [useScrape]);

  // Resize handlers
  const startResize = useCallback((e: React.MouseEvent) => {
    isResizing.current = true;
    window.document.body.style.cursor = 'ew-resize';
    window.document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing.current) return;
      const newWidth = window.innerWidth - e.clientX;
      setSidebarWidth(Math.max(280, Math.min(600, newWidth)));
    };

    const handleMouseUp = () => {
      isResizing.current = false;
      window.document.body.style.cursor = '';
      window.document.body.style.userSelect = '';
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  // Scroll to bottom on new message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // Abort current request
  const abortRequest = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsSending(false);
    }
  };

  const sendMessage = async () => {
    if (!userMessage.trim() || isSending) return;

    const message = userMessage.trim();
    setUserMessage("");
    setIsSending(true);

    // Create abort controller
    abortControllerRef.current = new AbortController();

    // Add user message
    setChatMessages(prev => [...prev, {
      role: "user",
      content: message,
      timestamp: new Date(),
    }]);

    // Add placeholder for streaming response
    setChatMessages(prev => [...prev, {
      role: "assistant",
      content: "",
      timestamp: new Date(),
    }]);

    try {
      // Use streaming endpoint
      const params = new URLSearchParams({
        message,
        include_memory: String(useMemory),
        use_search: String(useSearch),
        document: selectedDoc?.name || "",
      });

      const res = await fetch(`${API_BASE}/api/chat/smart/stream?${params}`, {
        signal: abortControllerRef.current.signal,
      });

      if (!res.ok) throw new Error("Chat failed");

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let fullContent = "";

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') break;

            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                fullContent += parsed.content;
                // Update the last message with streaming content
                setChatMessages(prev => {
                  const updated = [...prev];
                  if (updated.length > 0 && updated[updated.length - 1].role === "assistant") {
                    updated[updated.length - 1] = {
                      ...updated[updated.length - 1],
                      content: fullContent,
                    };
                  }
                  return updated;
                });
              }
            } catch (e) {
              // Skip invalid JSON
            }
          }
        }
      }

      if (!fullContent) {
        // Fallback: update with error message
        setChatMessages(prev => {
          const updated = [...prev];
          if (updated.length > 0 && updated[updated.length - 1].role === "assistant") {
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: "Keine Antwort erhalten",
            };
          }
          return updated;
        });
      }

      log.info("Smart chat response", { chars: fullContent.length });
    } catch (error: any) {
      if (error.name === 'AbortError') {
        log.info("Chat aborted by user");
        // Update the placeholder message
        setChatMessages(prev => {
          const updated = [...prev];
          if (updated.length > 0 && updated[updated.length - 1].role === "assistant" && !updated[updated.length - 1].content) {
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: "(Abgebrochen)",
            };
          }
          return updated;
        });
      } else {
        log.error("Chat failed", { error });
        setChatMessages(prev => {
          const updated = [...prev];
          if (updated.length > 0 && updated[updated.length - 1].role === "assistant") {
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: "Fehler bei der Verbindung zum AI. Ist vLLM aktiv?",
            };
          }
          return updated;
        });
      }
    } finally {
      setIsSending(false);
      abortControllerRef.current = null;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const copyLastResponse = () => {
    const lastAssistant = chatMessages.filter(m => m.role === "assistant").pop();
    if (lastAssistant) {
      navigator.clipboard.writeText(lastAssistant.content);
      setCopied(true);
      toast.success("Kopiert!");
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div 
      ref={sidebarRef}
      style={{ width: sidebarWidth }}
      className="border-l bg-card/50 flex flex-col h-full relative shrink-0"
    >
      {/* Resize Handle */}
      <div
        onMouseDown={startResize}
        className="absolute left-0 top-0 bottom-0 w-1 cursor-ew-resize hover:bg-primary/30 transition-colors z-10 flex items-center"
      >
        <GripVertical className="w-3 h-3 text-muted-foreground/50 -ml-1" />
      </div>
      
      {/* Header */}
      <div className="h-10 border-b flex items-center justify-between px-3 shrink-0">
        <div className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-primary" />
          <span className="font-medium text-xs">AI Assistent</span>
        </div>
        {chatMessages.length > 0 && (
          <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={copyLastResponse}>
            {copied ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
          </Button>
        )}
      </div>

      {/* Tool Toggles - Compact with Tooltips */}
      <div className="px-3 py-1.5 border-b flex items-center gap-4 text-[10px]">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1">
                <Brain className="w-3 h-3 text-muted-foreground" />
                <Switch checked={useMemory} onCheckedChange={setUseMemory} className="scale-[0.6]" />
              </div>
            </TooltipTrigger>
            <TooltipContent><p>Memory - Persönliche Infos</p></TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1">
                <Search className="w-3 h-3 text-muted-foreground" />
                <Switch checked={useSearch} onCheckedChange={setUseSearch} className="scale-[0.6]" />
              </div>
            </TooltipTrigger>
            <TooltipContent><p>Web-Suche</p></TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1">
                <Globe className="w-3 h-3 text-muted-foreground" />
                <Switch checked={useScrape} onCheckedChange={setUseScrape} className="scale-[0.6]" />
              </div>
            </TooltipTrigger>
            <TooltipContent><p>Website scrapen</p></TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-3 space-y-3">
          {/* Welcome / Quick Info when no chat */}
          {chatMessages.length === 0 && (
            <div className="space-y-3">
              {/* Document context */}
              {selectedDoc && (
                <div className="p-2 rounded-md bg-primary/10 border border-primary/20">
                  <div className="flex items-start gap-2">
                    <FileText className="w-3.5 h-3.5 mt-0.5 text-primary" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{selectedDoc?.name}</p>
                      <p className="text-xs text-muted-foreground capitalize">{selectedDoc?.category}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Quick Info from summary */}
              {summary && (
                <>
                  {/* Tomorrow's Trash */}
                  {summary.trash?.tomorrow?.length > 0 && (
                    <div className="p-3 rounded-lg bg-orange-500/10 border border-orange-500/20">
                      <div className="flex items-center gap-2 mb-1">
                        <Trash2 className="w-4 h-4 text-orange-500" />
                        <span className="text-sm font-medium text-orange-600">Morgen: Müllabfuhr</span>
                      </div>
                      <p className="text-sm text-orange-600/80">
                        {summary.trash.tomorrow.map((t: any) => t.type).join(", ")}
                      </p>
                    </div>
                  )}

                  {/* Reminders */}
                  {summary.reminders?.overdue > 0 && (
                    <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-destructive" />
                        <span className="text-sm text-destructive">
                          {summary.reminders.overdue} überfällige Erinnerungen
                        </span>
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* Greeting */}
              <div className="text-center py-4">
                <Bot className="w-10 h-10 mx-auto mb-3 text-primary/50" />
                <p className="text-sm text-muted-foreground">
                  Hallo{summary?.profile?.name ? ` ${summary.profile.name}` : ""}! 
                  <br />Wie kann ich helfen?
                </p>
              </div>

              {/* Quick prompts */}
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">Schnelle Aktionen:</p>
                <div className="flex flex-wrap gap-2">
                  {[
                    "Wann ist Müllabfuhr?",
                    "Schreib eine Email",
                    "Was steht heute an?",
                  ].map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => {
                        setUserMessage(prompt);
                        setTimeout(sendMessage, 100);
                      }}
                      className="text-xs px-3 py-1.5 rounded-full bg-muted hover:bg-muted/80 transition-colors"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Chat Messages */}
          {chatMessages.map((msg, i) => (
            <div
              key={i}
              className={cn(
                "flex gap-1.5",
                msg.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              {msg.role === "assistant" && (
                <div className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                  <Bot className="w-3 h-3 text-primary" />
                </div>
              )}
              <div
                className={cn(
                  "max-w-[85%] px-2.5 py-1.5 rounded text-xs overflow-hidden",
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                )}
              >
                <p className="whitespace-pre-wrap leading-relaxed break-words overflow-wrap-anywhere">{msg.content}</p>
              </div>
              {msg.role === "user" && (
                <div className="w-5 h-5 rounded-full bg-muted flex items-center justify-center shrink-0 mt-0.5">
                  <User className="w-3 h-3" />
                </div>
              )}
            </div>
          ))}

          {/* Loading indicator - click to abort */}
          {isSending && (
            <div 
              className="flex gap-2 cursor-pointer group"
              onClick={abortRequest}
              title="Klicken zum Abbrechen"
            >
              <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="w-3.5 h-3.5 text-primary" />
              </div>
              <div className="bg-muted p-3 rounded-lg flex items-center gap-2 group-hover:bg-destructive/10 transition-colors">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-[10px] text-muted-foreground group-hover:text-destructive">Klick zum Abbrechen</span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>
      </ScrollArea>

      {/* Chat Input */}
      <div className="p-2 border-t shrink-0">
        <div className="relative">
          <Textarea
            placeholder="Frag mich etwas..."
            value={userMessage}
            onChange={(e) => setUserMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            className="min-h-[40px] max-h-[80px] pr-10 resize-none text-xs"
            rows={1}
          />
          <Button
            size="icon"
            className="absolute right-1.5 bottom-1.5 h-6 w-6"
            disabled={!userMessage.trim() || isSending}
            onClick={sendMessage}
          >
            {isSending ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Send className="w-3 h-3" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
