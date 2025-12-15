import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Paperclip, Bot, User, Sparkles, Copy, Check, Loader2, Settings2, Zap, Clock, MessageSquare, Upload, X, FileText, Image as ImageIcon, Trash2, Edit2, Search, Database, Globe, Wrench, Settings, Brain, AlertTriangle, MoreHorizontal, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { useRyxHub } from "@/context/RyxHubContext";
import { useSendMessage, useModels } from "@/hooks/useRyxApi";
import { toast } from "sonner";
import { getModelDisplayName } from "@/types/ryxhub";
import { MessageActionsMenu } from "./MessageActionsMenu";
import { VariantSelector } from "./VariantSelector";
import { gmailApi } from "@/lib/api/client";
import { GmailSettingsPanel } from "./GmailSettingsPanel";

// Icon map for tools
const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  Search, Database, Globe, FileText, Wrench, Brain,
};

// Tool display names
const toolDisplayNames: Record<string, string> = {
  "web_search": "searched",
  "memory_retrieve": "memory",
  "memory_store": "learned",
  "rag_search": "docs",
};

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
  tools_used?: string[];
  confidence?: number;
  language?: string;
}

// Default model - can be overridden via environment variable or settings
const DEFAULT_MODEL = import.meta.env.VITE_DEFAULT_MODEL || "/models/medium/general/qwen2.5-7b-gptq";

// Available tools for restriction settings
const defaultTools = [
  { id: "websearch", name: "Web Search", description: "Auto-searches when needed", icon: "Search" },
  { id: "rag", name: "RAG", description: "Query knowledge base", icon: "Database" },
  { id: "memory", name: "Memory", description: "Remember context", icon: "Brain" },
  { id: "scrape", name: "Scraper", description: "Extract from websites", icon: "Globe" },
];

export function ChatView() {
  const { sessions, selectedSessionId, addMessageToSession, clearSessionMessages, updateSessionTools, editMessageInSession, models: contextModels, addVariantToMessage, setActiveVariant } = useRyxHub();
  const [input, setInput] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>(DEFAULT_MODEL);
  const [lastStats, setLastStats] = useState<MessageStats | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [sessionSettingsOpen, setSessionSettingsOpen] = useState(false);
  const [sessionSystemPrompt, setSessionSystemPrompt] = useState("");
  const [sessionStyle, setSessionStyle] = useState("normal");
  const [sessionToolRestrictions, setSessionToolRestrictions] = useState<Record<string, boolean>>({});
  const [contextMenu, setContextMenu] = useState<{ messageId: string; position: { x: number; y: number } } | null>(null);
  const [sendingEmail, setSendingEmail] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  const sendMessageMutation = useSendMessage();
  const { data: apiModels } = useModels();
  
  const allModels = apiModels || contextModels;
  const availableModels = allModels.filter(m => m.status === 'loaded');
  const currentSession = sessions.find((s) => s.id === selectedSessionId);
  const messages = currentSession?.messages ?? [];
  
  // Load session settings when session changes
  useEffect(() => {
    if (!currentSession?.id) return;
    
    // Load style and system prompt
    const savedStyle = localStorage.getItem(`session-style-${currentSession.id}`);
    setSessionStyle(savedStyle || 'normal');
    
    const savedPrompt = localStorage.getItem(`session-systemprompt-${currentSession.id}`);
    setSessionSystemPrompt(savedPrompt || '');
    
    // Load tool restrictions (disabled tools)
    const savedRestrictions = localStorage.getItem(`session-tool-restrictions-${currentSession.id}`);
    if (savedRestrictions) {
      try {
        setSessionToolRestrictions(JSON.parse(savedRestrictions));
      } catch {}
    } else {
      setSessionToolRestrictions({});
    }
  }, [currentSession?.id]);

  // Set initial model - auto-switch if selected model not loaded
  useEffect(() => {
    if (availableModels.length === 0) return;
    
    const sessionModel = currentSession?.model;
    const isSessionModelLoaded = sessionModel && availableModels.some(m => m.id === sessionModel);
    
    if (isSessionModelLoaded) {
      setSelectedModel(sessionModel);
    } else if (availableModels.length > 0) {
      // Session model not loaded, use first available loaded model
      setSelectedModel(availableModels[0].id);
    }
  }, [currentSession?.id, availableModels]);

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
    const imageFiles = uploadedFiles.filter(f => f.type.startsWith('image/') && f.preview);
    const textFiles = uploadedFiles.filter(f => !f.type.startsWith('image/'));
    
    // Add text files as context
    if (textFiles.length > 0) {
      const fileContexts = textFiles.map(f => {
        if (f.content) return `\n\n[File: ${f.name}]\n\`\`\`\n${f.content.slice(0, 2000)}${f.content.length > 2000 ? '\n...(truncated)' : ''}\n\`\`\``;
        return `\n\n[Attached: ${f.name}]`;
      }).join('');
      userMessage = input + fileContexts;
    }
    
    // Extract base64 images
    const images = imageFiles.map(f => f.preview!.split(',')[1]);

    setInput("");
    setUploadedFiles([]);

    addMessageToSession(selectedSessionId, {
      role: "user",
      content: userMessage + (images.length > 0 ? ` [${images.length} image(s)]` : ''),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    });

    setIsTyping(true);
    setLastStats(null);

    try {
      // Verify model is loaded before sending
      const isModelLoaded = availableModels.some(m => m.id === selectedModel);
      if (!isModelLoaded) {
        throw new Error(`Model ${selectedModel} is not loaded. Please load it in Settings or select a different model.`);
      }
      
      // Get session style and system prompt from localStorage
      const sessionStyle = localStorage.getItem(`session-style-${selectedSessionId}`) || 'normal';
      const sessionSystemPrompt = localStorage.getItem(`session-systemprompt-${selectedSessionId}`) || undefined;
      
      // Get user memories
      const storedMemories = localStorage.getItem('ryxhub_user_memories');
      const userMemories = storedMemories ? JSON.parse(storedMemories) : [];
      
      const history = buildConversationHistory();
      
      const response = await sendMessageMutation.mutateAsync({
        sessionId: selectedSessionId,
        message: userMessage,
        model: selectedModel,
        history,
        toolRestrictions: sessionToolRestrictions, // Pass restrictions, AI decides what to use
        images: images.length > 0 ? images : undefined,
        style: sessionStyle,
        systemPrompt: sessionSystemPrompt,
        memories: userMemories,
      });

      setLastStats({
        latency_ms: response.latency_ms,
        tokens_per_second: response.tokens_per_second,
        prompt_tokens: response.prompt_tokens,
        completion_tokens: response.completion_tokens,
        tools_used: response.tools_used || [],
        confidence: response.confidence,
        language: response.language,
      });

      addMessageToSession(selectedSessionId, {
        role: "assistant",
        content: response.content,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        model: response.model || selectedModel,
        toolsUsed: response.tools_used || [],
        confidence: response.confidence,
        memoriesUsed: response.memories_used || [],
        toolDecisions: response.tool_decisions || [],
        emailDraft: (response as any).email_draft,
      });

      // Show warnings as toast (auto-dismiss)
      if (response.warnings && response.warnings.length > 0) {
        response.warnings.forEach((warning: string) => {
          toast.warning(warning, { duration: 5000 });
        });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to get response";
      
      // Better error handling
      let displayError = "Connection failed";
      if (errorMessage.includes("does not exist") || errorMessage.includes("NotFoundError")) {
        displayError = "Model not loaded. Please load the model first.";
      } else if (errorMessage.includes("Cannot connect")) {
        displayError = "Ollama not running. Start Ollama first.";
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

  // Right-click context menu handler
  const handleContextMenu = (e: React.MouseEvent, messageId: string) => {
    e.preventDefault();
    setContextMenu({ 
      messageId, 
      position: { x: e.clientX, y: e.clientY } 
    });
  };

  // Regenerate a response with optional modifier - stores as variant
  const handleRegenerateMessage = async (messageId: string, modifier?: 'shorter' | 'longer' | 'explain') => {
    if (!selectedSessionId) return;
    
    // Find the message and the user message before it
    const msgIndex = messages.findIndex(m => m.id === messageId);
    if (msgIndex === -1) return;
    
    // Find the last user message before this assistant message
    let userMsgIndex = msgIndex - 1;
    while (userMsgIndex >= 0 && messages[userMsgIndex].role !== 'user') {
      userMsgIndex--;
    }
    
    if (userMsgIndex < 0) {
      toast.error('Cannot regenerate - no user message found');
      return;
    }
    
    const userMessage = messages[userMsgIndex].content;
    let modifiedPrompt = userMessage;
    
    // Apply modifier
    if (modifier === 'shorter') {
      modifiedPrompt = `${userMessage}\n\n[Instruction: Make your response much shorter and more concise. Maximum 2-3 sentences.]`;
    } else if (modifier === 'longer') {
      modifiedPrompt = `${userMessage}\n\n[Instruction: Provide a more detailed and comprehensive response with examples.]`;
    } else if (modifier === 'explain') {
      modifiedPrompt = `${userMessage}\n\n[Instruction: Explain this in more detail with step-by-step reasoning and examples.]`;
    }
    
    setIsTyping(true);
    try {
      const history = messages.slice(0, userMsgIndex).map(m => ({ 
        role: m.role as "user" | "assistant", 
        content: m.content 
      }));
      
      const response = await sendMessageMutation.mutateAsync({
        sessionId: selectedSessionId,
        message: modifiedPrompt,
        model: selectedModel,
        history,
        toolRestrictions: sessionToolRestrictions,
      });
      
      // Add as variant to the existing message
      addVariantToMessage(selectedSessionId, messageId, {
        content: response.content,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        model: response.model || selectedModel,
        modifier: modifier,
      });
      
      toast.success(modifier ? `Regenerated (${modifier})` : 'Regenerated');
    } catch (error) {
      toast.error("Failed to regenerate");
    } finally {
      setIsTyping(false);
    }
  };

  const handleModelChange = (modelId: string) => {
    const isLoaded = availableModels.some(m => m.id === modelId);
    if (!isLoaded) {
      toast.error(`Model ${modelId} not loaded. Load it in Settings first.`);
      return;
    }
    setSelectedModel(modelId);
    // Save as last used model for next startup
    fetch('http://localhost:8420/api/models/save-last', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: modelId })
    }).catch(() => {});
    toast.success(`Model: ${getModelDisplayName(modelId)}`);
  };


  const handleClearChat = () => {
    if (selectedSessionId) {
      clearSessionMessages(selectedSessionId);
      setLastStats(null);
      toast.success("Chat cleared");
    }
  };

  const handleSaveSessionSettings = () => {
    if (selectedSessionId) {
      localStorage.setItem(`session-style-${selectedSessionId}`, sessionStyle);
      if (sessionSystemPrompt.trim()) {
        localStorage.setItem(`session-systemprompt-${selectedSessionId}`, sessionSystemPrompt);
      } else {
        localStorage.removeItem(`session-systemprompt-${selectedSessionId}`);
      }
      localStorage.setItem(`session-tool-restrictions-${selectedSessionId}`, JSON.stringify(sessionToolRestrictions));
      toast.success("Session settings saved");
      setSessionSettingsOpen(false);
    }
  };

  const STYLE_OPTIONS = [
    { id: "normal", name: "Normal", description: "Balanced responses" },
    { id: "concise", name: "Concise", description: "Short and direct" },
    { id: "explanatory", name: "Explanatory", description: "Detailed with examples" },
    { id: "learning", name: "Learning", description: "Step-by-step teaching" },
    { id: "formal", name: "Formal", description: "Professional language" },
  ];

  const handleSendEmail = async (messageId: string, draft: any) => {
    if (!draft) return;
    
    setSendingEmail(messageId);
    
    try {
      const result = await gmailApi.sendEmail({
        to: draft.to,
        subject: draft.subject,
        body: draft.body,
        from: draft.from
      });
      
      if (result.success) {
        toast.success(`Email sent to ${draft.to}`, {
          description: `Message ID: ${result.message_id?.slice(0, 8)}...`
        });
      } else {
        toast.error("Failed to send email");
      }
    } catch (error: any) {
      if (error.message?.includes("not connected")) {
        toast.error("Gmail not connected", {
          description: "Go to Settings → Connect Gmail to authorize"
        });
      } else {
        toast.error("Failed to send email", {
          description: error.message || "Unknown error"
        });
      }
    } finally {
      setSendingEmail(null);
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
    <div className="flex flex-col h-full bg-background w-full">
      {/* Compact Header */}
      <div className="px-4 py-2 border-b border-border bg-card/50 flex items-center justify-between shrink-0">
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
            
            <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-muted-foreground" onClick={() => setSessionSettingsOpen(true)}>
              <Settings className="w-3 h-3" />
            </Button>
          </div>
        </div>

      {/* Messages - Compact */}
      <ScrollArea className="flex-1 px-4">
          <div className="py-3 space-y-3">
            {messages.map((message) => {
              // Get active variant content
              const activeVariantIndex = message.activeVariant ?? 0;
              const displayContent = activeVariantIndex === 0 
                ? message.content 
                : message.variants?.[activeVariantIndex - 1]?.content ?? message.content;
              const displayModel = activeVariantIndex === 0
                ? message.model
                : message.variants?.[activeVariantIndex - 1]?.model ?? message.model;
              const displayTimestamp = activeVariantIndex === 0
                ? message.timestamp
                : message.variants?.[activeVariantIndex - 1]?.timestamp ?? message.timestamp;
              
              return (
              <div 
                key={message.id} 
                className={cn("flex gap-2", message.role === "user" ? "justify-end" : "justify-start")}
                onContextMenu={(e) => handleContextMenu(e, message.id)}
              >
                {message.role === "assistant" && <Sparkles className="w-4 h-4 text-primary mt-1 flex-shrink-0" />}
                <div className={cn(
                  "max-w-[80%] rounded-lg px-3 py-2 text-sm relative group",
                  message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                )}>
                  {/* Quick action button - visible on hover */}
                  <button
                    onClick={(e) => handleContextMenu(e, message.id)}
                    className="absolute -right-8 top-1 opacity-0 group-hover:opacity-60 hover:!opacity-100 p-1 rounded transition-opacity"
                  >
                    <MoreHorizontal className="w-4 h-4" />
                  </button>
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
                      {/* Memory context indicator - show what memories were used */}
                      {message.role === "assistant" && message.memoriesUsed && message.memoriesUsed.length > 0 && (
                        <div className="mb-2 pb-2 border-b border-border/50 text-[10px] text-muted-foreground">
                          <span className="flex items-center gap-1 font-medium text-primary/80">
                            <Brain className="w-3 h-3" /> Using memories:
                          </span>
                          <div className="mt-1 space-y-0.5">
                            {message.memoriesUsed.slice(0, 3).map((mem: any, idx: number) => (
                              <div key={idx} className="flex items-center gap-1 text-[9px]">
                                <span className="text-muted-foreground/60">[{mem.category}]</span>
                                <span>{mem.fact.length > 60 ? mem.fact.slice(0, 60) + '...' : mem.fact}</span>
                              </div>
                            ))}
                            {message.memoriesUsed.length > 3 && (
                              <span className="text-muted-foreground/50">+{message.memoriesUsed.length - 3} more</span>
                            )}
                          </div>
                        </div>
                      )}
                      
                      <div className="whitespace-pre-wrap">{displayContent}</div>

                      {/* Email draft preview if generated */}
                      {message.role === "assistant" && message.emailDraft && (
                        <div className="mt-2 p-3 rounded-lg bg-card border border-border/50 text-xs space-y-2">
                          <div className="flex items-center gap-2 text-sm font-medium">
                            <Mail className="w-4 h-4" />
                            Email draft prepared
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <div><span className="text-muted-foreground">To:</span> {message.emailDraft.to}</div>
                            <div><span className="text-muted-foreground">From:</span> {message.emailDraft.from}</div>
                            <div className="col-span-2"><span className="text-muted-foreground">Subject:</span> {message.emailDraft.subject}</div>
                          </div>
                          <div className="p-2 rounded bg-muted/60 text-[11px] whitespace-pre-wrap max-h-40 overflow-y-auto">
                            {message.emailDraft.body}
                          </div>
                          <div className="flex gap-2">
                            <Button 
                              size="sm" 
                              variant="outline" 
                              className="h-7 px-2 text-xs"
                              disabled
                            >
                              Open editor (coming soon)
                            </Button>
                            <Button 
                              size="sm" 
                              className="h-7 px-2 text-xs" 
                              variant="default"
                              onClick={() => handleSendEmail(message.id, message.emailDraft)}
                              disabled={sendingEmail === message.id}
                            >
                              {sendingEmail === message.id ? (
                                <>
                                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                                  Sending...
                                </>
                              ) : (
                                <>
                                  <Mail className="w-3 h-3 mr-1" />
                                  Send Email
                                </>
                              )}
                            </Button>
                          </div>
                        </div>
                      )}
                      
                      {/* Variant selector - only for assistant messages with variants */}
                      {message.role === "assistant" && message.variants && message.variants.length > 0 && selectedSessionId && (
                        <div className="mt-2 pt-2 border-t border-border/30">
                          <VariantSelector
                            originalTimestamp={message.timestamp}
                            variants={message.variants}
                            activeVariant={message.activeVariant ?? 0}
                            onSelectVariant={(idx) => setActiveVariant(selectedSessionId, message.id, idx)}
                          />
                        </div>
                      )}
                      
                      {/* Footer with tools, confidence, timestamp */}
                      <div className={cn("flex items-center gap-1.5 mt-2 pt-1 border-t border-border/30 text-[10px] flex-wrap", message.role === "user" ? "text-primary-foreground/70 justify-end" : "text-muted-foreground")}>
                        {displayModel && message.role === "assistant" && (
                          <span className="opacity-60">{getModelDisplayName(displayModel)}</span>
                        )}
                        
                        {/* Tool breakdown - clearer display */}
                        {message.role === "assistant" && message.toolsUsed && message.toolsUsed.length > 0 && (
                          <span className="flex items-center gap-1">
                            {message.toolsUsed.includes("memory_retrieve") && (
                              <span className="text-blue-500 flex items-center gap-0.5" title="Used memory">
                                <Brain className="w-3 h-3" /> memory
                              </span>
                            )}
                            {message.toolsUsed.includes("web_search") && (
                              <span className="text-green-500 flex items-center gap-0.5" title="Searched web">
                                <Search className="w-3 h-3" /> searched
                              </span>
                            )}
                            {message.toolsUsed.includes("memory_store") && (
                              <span className="text-purple-500 flex items-center gap-0.5" title="Learned new fact">
                                <Database className="w-3 h-3" /> learned
                              </span>
                            )}
                          </span>
                        )}
                        
                        {/* Confidence bar */}
                        {message.role === "assistant" && message.confidence !== undefined && (
                          <span 
                            className={cn(
                              "flex items-center gap-0.5 px-1 py-0.5 rounded text-[9px] font-medium",
                              message.confidence >= 0.85 ? "bg-green-500/20 text-green-600" :
                              message.confidence >= 0.7 ? "bg-yellow-500/20 text-yellow-600" :
                              "bg-red-500/20 text-red-600"
                            )} 
                            title={`Confidence: ${(message.confidence * 100).toFixed(0)}%`}
                          >
                            {message.confidence >= 0.85 ? "✓" : message.confidence >= 0.7 ? "~" : "⚠️"}
                            {(message.confidence * 100).toFixed(0)}%
                          </span>
                        )}
                        
                        <span className="opacity-60">{displayTimestamp}</span>
                        <button onClick={() => handleCopy(displayContent, message.id)} className="hover:opacity-100 opacity-60">
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
            );
            })}

            {isTyping && (
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

      {/* ChatGPT-style Input Area */}
      <div className="border-t border-border bg-background shrink-0">
        <div className="max-w-3xl mx-auto p-4">
          {/* File Uploads */}
          <div ref={dropZoneRef} className={cn("relative", isDragging && "bg-primary/10 rounded-lg")}
            onDragEnter={handleDragEnter} onDragLeave={handleDragLeave} onDragOver={handleDragOver} onDrop={handleDrop}>

            {isDragging && (
              <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10 pointer-events-none rounded-lg">
                <div className="flex flex-col items-center gap-2">
                  <Upload className="w-8 h-8 text-primary" />
                  <span className="text-sm text-primary font-medium">Drop files here</span>
                </div>
              </div>
            )}

            {uploadedFiles.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {uploadedFiles.map((file) => (
                  <div key={file.id} className="flex items-center gap-2 px-3 py-2 bg-muted rounded-lg text-xs border border-border">
                    {file.type.startsWith('image/') ? <ImageIcon className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                    <span className="max-w-[150px] truncate">{file.name}</span>
                    <button onClick={() => removeFile(file.id)} className="hover:text-destructive">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Message Input */}
            <div className="relative flex items-end gap-2">
              <div className="flex-1 relative">
                <Textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Message Ryx..."
                  className="min-h-[52px] max-h-[200px] pr-12 text-sm resize-none rounded-2xl border-border focus:border-primary"
                />
                <div className="absolute right-2 bottom-2">
                  <input ref={fileInputRef} type="file" multiple className="hidden"
                    onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
                    accept="image/*,.txt,.md,.json,.py,.ts,.js,.tsx,.jsx,.css,.html" />
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => fileInputRef.current?.click()}>
                    <Paperclip className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              <Button
                size="icon"
                className="h-[52px] w-[52px] rounded-xl shrink-0"
                onClick={handleSend}
                disabled={(!input.trim() && uploadedFiles.length === 0) || isTyping}
              >
                {isTyping ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Session Settings Dialog */}
      <Dialog open={sessionSettingsOpen} onOpenChange={setSessionSettingsOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Session Settings</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Response Style</Label>
              <Select value={sessionStyle} onValueChange={setSessionStyle}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STYLE_OPTIONS.map(style => (
                    <SelectItem key={style.id} value={style.id}>
                      <div className="flex flex-col">
                        <span>{style.name}</span>
                        <span className="text-xs text-muted-foreground">{style.description}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Custom System Prompt (optional)</Label>
              <Textarea
                value={sessionSystemPrompt}
                onChange={(e) => setSessionSystemPrompt(e.target.value)}
                placeholder="Enter a custom system prompt for this session..."
                className="min-h-[100px]"
              />
              <p className="text-xs text-muted-foreground">
                This overrides the style prompt. Leave empty to use style-based prompt.
              </p>
            </div>
            <div className="space-y-2">
              <Label>Tool Restrictions</Label>
              <p className="text-xs text-muted-foreground mb-2">
                Disable specific tools for this session. The AI will automatically decide which tools to use, but will not use disabled ones.
              </p>
              <div className="space-y-2">
                {defaultTools.map((tool) => {
                  const Icon = typeof tool.icon === 'string' ? iconMap[tool.icon] || Wrench : tool.icon;
                  const isDisabled = sessionToolRestrictions[tool.id] === false;
                  return (
                    <div key={tool.id} className="flex items-center justify-between p-2 rounded-lg border border-border">
                      <div className="flex items-center gap-2">
                        <Icon className="w-4 h-4" />
                        <div>
                          <div className="text-sm font-medium">{tool.name}</div>
                          <div className="text-xs text-muted-foreground">{tool.description}</div>
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          const newRestrictions = { ...sessionToolRestrictions };
                          if (isDisabled) {
                            delete newRestrictions[tool.id];
                          } else {
                            newRestrictions[tool.id] = false;
                          }
                          setSessionToolRestrictions(newRestrictions);
                        }}
                        className={cn(
                          "px-3 py-1 rounded text-xs font-medium transition-colors",
                          isDisabled
                            ? "bg-destructive/10 text-destructive hover:bg-destructive/20"
                            : "bg-muted hover:bg-muted/80"
                        )}
                      >
                        {isDisabled ? "Disabled" : "Enabled"}
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
          
          {/* Gmail Integration */}
          <div className="space-y-2 pt-4 border-t">
            <Label className="flex items-center gap-2">
              <Mail className="w-4 h-4" />
              Gmail Integration
            </Label>
            <GmailSettingsPanel />
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setSessionSettingsOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveSessionSettings}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Message Actions Context Menu */}
      {contextMenu && (
        <MessageActionsMenu
          messageId={contextMenu.messageId}
          messageContent={messages.find(m => m.id === contextMenu.messageId)?.content || ''}
          isUser={messages.find(m => m.id === contextMenu.messageId)?.role === 'user'}
          position={contextMenu.position}
          onClose={() => setContextMenu(null)}
          onRegenerate={() => handleRegenerateMessage(contextMenu.messageId)}
          onMakeShorter={() => handleRegenerateMessage(contextMenu.messageId, 'shorter')}
          onMakeLonger={() => handleRegenerateMessage(contextMenu.messageId, 'longer')}
          onExplainMore={() => handleRegenerateMessage(contextMenu.messageId, 'explain')}
          onEdit={() => {
            const msg = messages.find(m => m.id === contextMenu.messageId);
            if (msg) handleEditMessage(contextMenu.messageId, msg.content);
          }}
        />
      )}
    </div>
  );
}
