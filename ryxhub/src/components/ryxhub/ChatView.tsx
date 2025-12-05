import { useState, useRef, useEffect } from "react";
import { Send, Paperclip, Bot, User, Sparkles, Copy, RotateCcw, Check, Loader2, Settings2, Zap, Clock, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { useRyxHub } from "@/context/RyxHubContext";
import { useSendMessage, useModels } from "@/hooks/useRyxApi";
import { toast } from "sonner";
import { ToolsPanel, defaultTools, type ToolConfig } from "@/components/ryxhub/ToolsPanel";

interface MessageStats {
  latency_ms?: number;
  tokens_per_second?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
}

export function ChatView() {
  const { sessions, selectedSessionId, addMessageToSession, models: contextModels } = useRyxHub();
  const [input, setInput] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [lastStats, setLastStats] = useState<MessageStats | null>(null);
  const [tools, setTools] = useState<ToolConfig[]>(defaultTools);
  const scrollRef = useRef<HTMLDivElement>(null);

  const sendMessageMutation = useSendMessage();
  const { data: apiModels } = useModels();
  
  // Use API models if available, otherwise fall back to context models
  const availableModels = apiModels || contextModels;

  const currentSession = sessions.find((s) => s.id === selectedSessionId);
  const messages = currentSession?.messages ?? [];
  
  // Set initial model from session
  useEffect(() => {
    if (currentSession && !selectedModel) {
      setSelectedModel(currentSession.model);
    }
  }, [currentSession, selectedModel]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length, isTyping]);

  const handleSend = async () => {
    if (!input.trim() || !selectedSessionId || isTyping) return;

    const userMessage = input;
    setInput("");

    addMessageToSession(selectedSessionId, {
      role: "user",
      content: userMessage,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    });

    setIsTyping(true);
    setLastStats(null);

    try {
      const response = await sendMessageMutation.mutateAsync({
        sessionId: selectedSessionId,
        message: userMessage,
        model: selectedModel || undefined,
      });

      // Store stats
      setLastStats({
        latency_ms: response.latency_ms,
        tokens_per_second: response.tokens_per_second,
        prompt_tokens: response.prompt_tokens,
        completion_tokens: response.completion_tokens,
      });

      addMessageToSession(selectedSessionId, {
        role: "assistant",
        content: response.content,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        model: response.model || selectedModel || currentSession?.model,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to get response";
      toast.error(`API Error: ${errorMessage}`);

      addMessageToSession(selectedSessionId, {
        role: "assistant",
        content: `⚠️ **Connection Error**\n\nCouldn't reach the Ryx backend. Please check:\n- Is vLLM running on localhost:8420?\n- Is the model loaded?\n\n_Error: ${errorMessage}_`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        model: "System",
      });
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey && !isTyping) {
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

  const handleModelChange = (modelId: string) => {
    setSelectedModel(modelId);
    toast.success(`Switched to ${modelId.split('/').pop()}`);
  };

  const handleToolToggle = async (toolId: string, enabled: boolean) => {
    setTools((prev) =>
      prev.map((tool) =>
        tool.id === toolId ? { ...tool, enabled } : tool
      )
    );

    // TODO: Send to backend API to persist tool state
    // await fetch(`http://localhost:8420/api/sessions/${selectedSessionId}/tools`, {
    //   method: 'PUT',
    //   body: JSON.stringify({ toolId, enabled })
    // });

    toast.success(`${enabled ? 'Enabled' : 'Disabled'} ${tools.find(t => t.id === toolId)?.name}`);
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
    <div className="flex h-full bg-background">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Chat Header with Model Selector */}
        <div className="px-6 py-4 border-b border-border bg-card/50 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg">
              <Bot className="w-5 h-5 text-primary-foreground" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-foreground">{currentSession.name}</h2>
              <p className="text-xs text-muted-foreground">
                {messages.length} messages
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Model Selector */}
            <Select value={selectedModel || currentSession.model} onValueChange={handleModelChange}>
              <SelectTrigger className="w-[200px] h-8 text-xs">
                <Settings2 className="w-3 h-3 mr-1" />
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent>
                {availableModels.map((model) => (
                  <SelectItem key={model.id} value={model.id} className="text-xs">
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        "w-2 h-2 rounded-full",
                        model.status === "online" ? "bg-green-500" : "bg-gray-400"
                      )} />
                      {model.name}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            {/* Stats Display */}
            {lastStats && (
              <div className="flex items-center gap-3 text-[10px] text-muted-foreground bg-muted/30 px-3 py-1.5 rounded-full">
                {lastStats.tokens_per_second && (
                  <span className="flex items-center gap-1">
                    <Zap className="w-3 h-3 text-yellow-500" />
                    {lastStats.tokens_per_second.toFixed(1)} t/s
                  </span>
                )}
                {lastStats.latency_ms && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {(lastStats.latency_ms / 1000).toFixed(1)}s
                  </span>
                )}
                {lastStats.completion_tokens && (
                  <span className="flex items-center gap-1">
                    <MessageSquare className="w-3 h-3" />
                    {lastStats.completion_tokens} tokens
                  </span>
                )}
              </div>
            )}
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

          {/* Typing Indicator */}
          {isTyping && (
            <div className="flex gap-4 justify-start">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20 border border-primary/30 flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-4 h-4 text-primary animate-pulse" />
              </div>
              <div className="bg-card border border-border rounded-2xl px-4 py-3">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Thinking...</span>
                </div>
              </div>
            </div>
          )}

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
              disabled={!input.trim() || isTyping}
            >
              {isTyping ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>
        <p className="text-[10px] text-muted-foreground mt-2 text-center">
          Press Enter to send • Shift+Enter for new line
        </p>
        </div>
      </div>

      {/* Right Sidebar - Tools Panel */}
      <div className="w-80 border-l border-border bg-card/30 backdrop-blur-sm p-4 overflow-y-auto">
        <ToolsPanel tools={tools} onToolToggle={handleToolToggle} />
      </div>
    </div>
  );
}
