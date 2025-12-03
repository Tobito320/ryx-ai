import { useState, useRef, useEffect } from "react";
import { Send, Paperclip, Bot, User, Sparkles, Copy, RotateCcw, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { useRyxHub } from "@/context/RyxHubContext";
import { toast } from "sonner";

export function ChatView() {
  const { sessions, selectedSessionId, addMessageToSession } = useRyxHub();
  const [input, setInput] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const currentSession = sessions.find((s) => s.id === selectedSessionId);
  const messages = currentSession?.messages ?? [];

  useEffect(() => {
    // Scroll to bottom when messages change
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length]);

  const handleSend = () => {
    if (!input.trim() || !selectedSessionId) return;

    // Add user message
    addMessageToSession(selectedSessionId, {
      role: "user",
      content: input,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    });

    // Simulate AI response
    setTimeout(() => {
      addMessageToSession(selectedSessionId, {
        role: "assistant",
        content: `I've received your message: "${input.slice(0, 50)}..."\n\nThis is a simulated response. In a real implementation, this would be connected to your AI backend via the Ryx API.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        model: currentSession?.model,
      });
    }, 1000);

    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCopy = async (content: string, id: string) => {
    await navigator.clipboard.writeText(content);
    setCopiedId(id);
    toast.success("Copied to clipboard");
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleClear = () => {
    toast.info("Chat cleared (mock action)");
  };

  if (!currentSession) {
    return (
      <div className="flex flex-col h-full bg-background items-center justify-center">
        <div className="text-center">
          <Bot className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-foreground">No Session Selected</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Select a session from the sidebar to start chatting
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Chat Header */}
      <div className="px-6 py-4 border-b border-border bg-card/50 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg">
              <Bot className="w-5 h-5 text-primary-foreground" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-foreground">{currentSession.name}</h2>
              <p className="text-xs text-muted-foreground">
                Using {currentSession.model} • RAG enabled • {messages.length} messages
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={handleClear}>
              <RotateCcw className="w-4 h-4 mr-1.5" />
              Clear
            </Button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 px-6">
        <div className="py-6 space-y-6">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex gap-4",
                message.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              {message.role === "assistant" && (
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20 border border-primary/30 flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-4 h-4 text-primary" />
                </div>
              )}
              <div
                className={cn(
                  "max-w-[75%] rounded-2xl px-4 py-3",
                  message.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-card border border-border"
                )}
              >
                <div className={cn(
                  "text-sm whitespace-pre-wrap",
                  message.role === "assistant" && "text-foreground"
                )}>
                  {message.content}
                </div>
                <div className={cn(
                  "flex items-center gap-2 mt-2 text-[10px]",
                  message.role === "user" ? "text-primary-foreground/70 justify-end" : "text-muted-foreground"
                )}>
                  {message.model && (
                    <span className="px-1.5 py-0.5 rounded bg-muted/50">{message.model}</span>
                  )}
                  <span>{message.timestamp}</span>
                  {message.role === "assistant" && (
                    <button
                      onClick={() => handleCopy(message.content, message.id)}
                      className="hover:text-foreground transition-colors"
                    >
                      {copiedId === message.id ? (
                        <Check className="w-3 h-3 text-[hsl(var(--success))]" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )}
                    </button>
                  )}
                </div>
              </div>
              {message.role === "user" && (
                <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-secondary-foreground" />
                </div>
              )}
            </div>
          ))}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="p-4 border-t border-border bg-card/30 backdrop-blur-sm">
        <div className="relative">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Message ${currentSession.name}...`}
            className="min-h-[60px] max-h-[200px] pr-24 bg-input border-border resize-none text-sm"
          />
          <div className="absolute right-2 bottom-2 flex items-center gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
              <Paperclip className="w-4 h-4" />
            </Button>
            <Button
              size="icon"
              className="h-8 w-8 bg-primary hover:bg-primary/90"
              onClick={handleSend}
              disabled={!input.trim()}
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
        <p className="text-[10px] text-muted-foreground mt-2 text-center">
          Press Enter to send • Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
