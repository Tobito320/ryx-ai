import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Paperclip, Bot, User, Sparkles, Copy, Check, Loader2, Settings2, Zap, Clock, MessageSquare, Upload, X, FileText, Image as ImageIcon, Trash2, Edit2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { useRyxHub } from "@/context/RyxHubContext";
import { useSendMessage, useModels } from "@/hooks/useRyxApi";
import { toast } from "sonner";
import { ToolsPanel, type ToolConfig } from "@/components/ryxhub/ToolsPanel";
import { getModelDisplayName } from "@/types/ryxhub";

interface UploadedFile {
  id: string;
  name: string;
  type: string;
  size: number;
  preview?: string;
  content?: string;
}

interface MessageStats {
  latency_ms?: number;
  tokens_per_second?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
}

const DEFAULT_MODEL = "/models/medium/general/qwen2.5-7b-gptq";

// Default tools - websearch and rag enabled
const defaultTools: ToolConfig[] = [
  { id: "websearch", name: "Web Search", description: "Search the web", icon: "Search", enabled: true },
  { id: "rag", name: "RAG", description: "Query knowledge base", icon: "Database", enabled: true },
  { id: "scrape", name: "Scraper", description: "Extract from websites", icon: "Globe", enabled: false },
  { id: "filesystem", name: "Files", description: "Read/write files", icon: "FileText", enabled: false },
];

export function ChatView() {
  const { sessions, selectedSessionId, addMessageToSession, clearSessionMessages, updateSessionTools, editMessageInSession, models: contextModels } = useRyxHub();
  const [input, setInput] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>(DEFAULT_MODEL);
  const [lastStats, setLastStats] = useState<MessageStats | null>(null);
  const [tools, setTools] = useState<ToolConfig[]>(defaultTools);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [toolStatus, setToolStatus] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  const sendMessageMutation = useSendMessage();
  const { data: apiModels } = useModels();
  
  const availableModels = apiModels || contextModels;
  const currentSession = sessions.find((s) => s.id === selectedSessionId);
  const messages = currentSession?.messages ?? [];
  
  // Load session tools when session changes
  useEffect(() => {
    if (currentSession?.tools) {
      setTools(prev => prev.map(t => ({
        ...t,
        enabled: currentSession.tools?.[t.id] ?? t.enabled
      })));
    }
  }, [currentSession?.id]);

  // Set initial model
  useEffect(() => {
    if (currentSession?.model) {
      setSelectedModel(currentSession.model);
    } else if (availableModels.length > 0) {
      const onlineModel = availableModels.find(m => m.status === "online");
      setSelectedModel(onlineModel?.id || availableModels[0].id);
    }
  }, [currentSession, availableModels]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length, isTyping]);

  // File upload handling
  const processFile = useCallback(async (file: File): Promise<UploadedFile> => {
    const id = `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const uploadedFile: UploadedFile = { id, name: file.name, type: file.type, size: file.size };

    if (file.type.startsWith('image/')) {
      return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => { uploadedFile.preview = e.target?.result as string; resolve(uploadedFile); };
        reader.readAsDataURL(file);
      });
    }

    if (file.type.startsWith('text/') || /\.(md|json|py|ts|js|tsx|jsx|css|html)$/.test(file.name)) {
      return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => { uploadedFile.content = e.target?.result as string; resolve(uploadedFile); };
        reader.readAsText(file);
      });
    }

    return uploadedFile;
  }, []);

  const handleFileUpload = useCallback(async (files: FileList | File[]) => {
    const fileArray = Array.from(files);
    const processed = await Promise.all(fileArray.map(processFile));
    setUploadedFiles(prev => [...prev, ...processed]);
    toast.success(`Added ${fileArray.length} file(s)`);
  }, [processFile]);

  const removeFile = useCallback((id: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== id));
  }, []);

  // Drag and drop
  const handleDragEnter = useCallback((e: React.DragEvent) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); }, []);
  const handleDragLeave = useCallback((e: React.DragEvent) => { e.preventDefault(); e.stopPropagation(); if (e.currentTarget === dropZoneRef.current) setIsDragging(false); }, []);
  const handleDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); e.stopPropagation(); }, []);
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation(); setIsDragging(false);
    if (e.dataTransfer.files.length > 0) handleFileUpload(e.dataTransfer.files);
  }, [handleFileUpload]);

  // Build conversation history for context
  const buildConversationHistory = useCallback(() => {
    return messages.map(m => ({
      role: m.role as "user" | "assistant",
      content: m.content
    }));
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() && uploadedFiles.length === 0) return;
    if (!selectedSessionId || isTyping) return;

    let userMessage = input;
    if (uploadedFiles.length > 0) {
      const fileContexts = uploadedFiles.map(f => {
        if (f.content) return `\n\n[File: ${f.name}]\n\`\`\`\n${f.content.slice(0, 2000)}${f.content.length > 2000 ? '\n...(truncated)' : ''}\n\`\`\``;
        if (f.preview) return `\n\n[Image: ${f.name}]`;
        return `\n\n[Attached: ${f.name}]`;
      }).join('');
      userMessage = input + fileContexts;
    }

    setInput("");
    setUploadedFiles([]);

    addMessageToSession(selectedSessionId, {
      role: "user",
      content: userMessage,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    });

    setIsTyping(true);
    setLastStats(null);
    setToolStatus(null);

    try {
      const enabledTools = tools.filter(t => t.enabled).map(t => t.id);
      
      // Show tool usage feedback
      if (enabledTools.includes('websearch')) {
        setToolStatus('🔍 Searching the web...');
      } else if (enabledTools.includes('rag')) {
        setToolStatus('📚 Searching knowledge base...');
      }
      
      const history = buildConversationHistory();
      
      const response = await sendMessageMutation.mutateAsync({
        sessionId: selectedSessionId,
        message: userMessage,
        model: selectedModel,
        history,
        tools: enabledTools,
      });
      
      setToolStatus(null);

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
        model: response.model || selectedModel,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to get response";
      
      // Better error handling
      let displayError = "Connection failed";
      if (errorMessage.includes("does not exist") || errorMessage.includes("NotFoundError")) {
        displayError = "Model not loaded. Please load the model first.";
      } else if (errorMessage.includes("Cannot connect")) {
        displayError = "vLLM not running. Start vLLM first.";
      } else {
        displayError = errorMessage;
      }
      
      toast.error(displayError);

      addMessageToSession(selectedSessionId, {
        role: "assistant",
        content: `⚠️ ${displayError}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        model: "System",
      });
    } finally {
      setIsTyping(false);
    }
  };

  const handleEditMessage = (messageId: string, content: string) => {
    setEditingMessageId(messageId);
    setEditContent(content);
  };

  const handleSaveEdit = async () => {
    if (!editingMessageId || !selectedSessionId || !editContent.trim()) return;
    
    // Find the message index
    const msgIndex = messages.findIndex(m => m.id === editingMessageId);
    if (msgIndex === -1) return;
    
    // Edit the message and remove subsequent assistant response if exists
    editMessageInSession(selectedSessionId, editingMessageId, editContent);
    
    setEditingMessageId(null);
    setEditContent("");
    
    // Resend the edited message
    setIsTyping(true);
    try {
      const history = messages.slice(0, msgIndex).map(m => ({ role: m.role as "user" | "assistant", content: m.content }));
      const response = await sendMessageMutation.mutateAsync({
        sessionId: selectedSessionId,
        message: editContent,
        model: selectedModel,
        history,
        tools: tools.filter(t => t.enabled).map(t => t.id),
      });
      
      addMessageToSession(selectedSessionId, {
        role: "assistant",
        content: response.content,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        model: response.model || selectedModel,
      });
    } catch (error) {
      toast.error("Failed to regenerate response");
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
    toast.success("Copied");
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleModelChange = (modelId: string) => {
    setSelectedModel(modelId);
    toast.success(`Model: ${getModelDisplayName(modelId)}`);
  };

  const handleToolToggle = (toolId: string, enabled: boolean) => {
    setTools(prev => prev.map(t => t.id === toolId ? { ...t, enabled } : t));
    if (selectedSessionId) {
      updateSessionTools(selectedSessionId, toolId, enabled);
    }
  };

  const handleClearChat = () => {
    if (selectedSessionId) {
      clearSessionMessages(selectedSessionId);
      setLastStats(null);
      toast.success("Chat cleared");
    }
  };

  if (!currentSession) {
    return (
      <div className="flex flex-col h-full bg-background items-center justify-center">
        <Bot className="w-12 h-12 text-muted-foreground mb-3" />
        <h2 className="text-sm font-medium text-foreground">No Session</h2>
        <p className="text-xs text-muted-foreground mt-1">Select or create a session</p>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-background">
      <div className="flex-1 flex flex-col min-w-0">
        {/* Compact Header */}
        <div className="px-4 py-2 border-b border-border bg-card/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-primary" />
            <span className="text-sm font-medium">{currentSession.name}</span>
            <span className="text-xs text-muted-foreground">({messages.length})</span>
          </div>
          
          <div className="flex items-center gap-2">
            <Select value={selectedModel} onValueChange={handleModelChange}>
              <SelectTrigger className="w-[140px] h-7 text-xs">
                <SelectValue>{getModelDisplayName(selectedModel)}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {availableModels.map((model) => (
                  <SelectItem key={model.id} value={model.id} className="text-xs">
                    <div className="flex items-center gap-2">
                      <span className={cn("w-1.5 h-1.5 rounded-full", model.status === "online" ? "bg-green-500" : "bg-gray-400")} />
                      {getModelDisplayName(model.name)}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            {lastStats && (
              <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                {lastStats.tokens_per_second && <span className="flex items-center gap-0.5"><Zap className="w-3 h-3" />{lastStats.tokens_per_second.toFixed(0)}t/s</span>}
                {lastStats.latency_ms && <span>{(lastStats.latency_ms / 1000).toFixed(1)}s</span>}
              </div>
            )}
            
            {messages.length > 0 && (
              <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-muted-foreground hover:text-destructive" onClick={handleClearChat}>
                <Trash2 className="w-3 h-3" />
              </Button>
            )}
          </div>
        </div>

        {/* Messages - Compact */}
        <ScrollArea className="flex-1 px-4">
          <div className="py-3 space-y-3">
            {messages.map((message) => (
              <div key={message.id} className={cn("flex gap-2", message.role === "user" ? "justify-end" : "justify-start")}>
                {message.role === "assistant" && <Sparkles className="w-4 h-4 text-primary mt-1 flex-shrink-0" />}
                <div className={cn(
                  "max-w-[80%] rounded-lg px-3 py-2 text-sm",
                  message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                )}>
                  {editingMessageId === message.id ? (
                    <div className="space-y-2">
                      <Textarea value={editContent} onChange={(e) => setEditContent(e.target.value)} className="min-h-[60px] text-sm" />
                      <div className="flex gap-1">
                        <Button size="sm" className="h-6 text-xs" onClick={handleSaveEdit}>Save & Resend</Button>
                        <Button size="sm" variant="ghost" className="h-6 text-xs" onClick={() => setEditingMessageId(null)}>Cancel</Button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="whitespace-pre-wrap">{message.content}</div>
                      <div className={cn("flex items-center gap-1 mt-1 text-[10px]", message.role === "user" ? "text-primary-foreground/70 justify-end" : "text-muted-foreground")}>
                        {message.model && message.role === "assistant" && <span className="opacity-60">{getModelDisplayName(message.model)}</span>}
                        <span>{message.timestamp}</span>
                        <button onClick={() => handleCopy(message.content, message.id)} className="hover:opacity-100 opacity-60">
                          {copiedId === message.id ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                        </button>
                        {message.role === "user" && (
                          <button onClick={() => handleEditMessage(message.id, message.content)} className="hover:opacity-100 opacity-60">
                            <Edit2 className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </>
                  )}
                </div>
                {message.role === "user" && <User className="w-4 h-4 text-muted-foreground mt-1 flex-shrink-0" />}
              </div>
            ))}

            {toolStatus && (
              <div className="flex gap-2 justify-start">
                <Sparkles className="w-4 h-4 text-primary animate-pulse mt-1" />
                <div className="bg-muted/50 rounded-lg px-3 py-2 text-xs text-muted-foreground">
                  {toolStatus}
                </div>
              </div>
            )}

            {isTyping && !toolStatus && (
              <div className="flex gap-2 justify-start">
                <Sparkles className="w-4 h-4 text-primary animate-pulse mt-1" />
                <div className="bg-muted rounded-lg px-3 py-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                </div>
              </div>
            )}
            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Compact Input */}
        <div ref={dropZoneRef} className={cn("p-3 border-t border-border", isDragging && "bg-primary/10")}
          onDragEnter={handleDragEnter} onDragLeave={handleDragLeave} onDragOver={handleDragOver} onDrop={handleDrop}>
          
          {isDragging && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10 pointer-events-none">
              <Upload className="w-8 h-8 text-primary" />
            </div>
          )}

          {uploadedFiles.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {uploadedFiles.map((file) => (
                <div key={file.id} className="flex items-center gap-1 px-2 py-1 bg-muted rounded text-xs">
                  {file.type.startsWith('image/') ? <ImageIcon className="w-3 h-3" /> : <FileText className="w-3 h-3" />}
                  <span className="max-w-[100px] truncate">{file.name}</span>
                  <button onClick={() => removeFile(file.id)}><X className="w-3 h-3" /></button>
                </div>
              ))}
            </div>
          )}

          <div className="relative">
            <Textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown}
              placeholder="Message..." className="min-h-[50px] max-h-[150px] pr-20 text-sm resize-none" />
            <div className="absolute right-2 bottom-2 flex items-center gap-1">
              <input ref={fileInputRef} type="file" multiple className="hidden"
                onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
                accept="image/*,.txt,.md,.json,.py,.ts,.js,.tsx,.jsx,.css,.html" />
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => fileInputRef.current?.click()}>
                <Paperclip className="w-4 h-4" />
              </Button>
              <Button size="icon" className="h-7 w-7" onClick={handleSend} disabled={(!input.trim() && uploadedFiles.length === 0) || isTyping}>
                {isTyping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Compact Tools Panel */}
      <div className="w-64 border-l border-border p-3 overflow-y-auto">
        <ToolsPanel tools={tools} onToolToggle={handleToolToggle} compact />
      </div>
    </div>
  );
}
