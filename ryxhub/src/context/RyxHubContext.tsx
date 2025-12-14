import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from "react";
import type { Session, Model, RAGStatus, ViewMode, Message, MessageVariant, Board, UserMemory, GmailAccount } from "@/types/ryxhub";
import {
  mockModels,
} from "@/data/mockData";
import { API_ENDPOINTS } from "@/config";
import type { ToolConfig } from "@/components/ryxhub/ToolsPanel";
import { defaultTools } from "@/components/ryxhub/ToolsPanel";

interface RyxHubContextType {
  // View state
  activeView: ViewMode;
  setActiveView: (view: ViewMode) => void;

  // Sessions
  sessions: Session[];
  selectedSessionId: string | null;
  selectSession: (id: string) => void;
  createSession: (name: string, model?: string) => Promise<Session | null>;
  addMessageToSession: (sessionId: string, message: Omit<Message, "id">) => void;
  clearSessionMessages: (sessionId: string) => void;
  editMessageInSession: (sessionId: string, messageId: string, newContent: string) => void;
  updateSessionTools: (sessionId: string, toolId: string, enabled: boolean) => void;
  deleteSession: (sessionId: string) => Promise<void>;
  renameSession: (sessionId: string, newName: string) => Promise<void>;
  refreshSessions: () => Promise<void>;
  addVariantToMessage: (sessionId: string, messageId: string, variant: Omit<MessageVariant, "id">) => void;
  setActiveVariant: (sessionId: string, messageId: string, variantIndex: number) => void;

  // Models
  models: Model[];

  // RAG
  ragStatus: RAGStatus;
  refreshRAGStatus: () => Promise<void>;

  // Tools
  tools: ToolConfig[];
  toggleTool: (toolId: string, enabled: boolean) => void;

  // Boards
  boards: Board[];
  selectedBoardId: string | null;
  selectBoard: (id: string) => void;
  createBoard: (name: string, category?: string) => Promise<Board | null>;
  refreshBoards: () => Promise<void>;

  // Memory
  memories: UserMemory[];
  refreshMemories: () => Promise<void>;

  // Gmail Accounts
  gmailAccounts: GmailAccount[];
  defaultGmailAccount: GmailAccount | null;
  refreshGmailAccounts: () => Promise<void>;
}

const RyxHubContext = createContext<RyxHubContextType | null>(null);

export function RyxHubProvider({ children }: { children: ReactNode }) {
  // View state
  const [activeView, setActiveView] = useState<ViewMode>("dashboard");

  // Sessions state - initialize from localStorage or empty
  const [sessions, setSessions] = useState<Session[]>(() => {
    const stored = localStorage.getItem('ryxhub_sessions');
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        return [];
      }
    }
    return [];
  });
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(() => {
    const stored = localStorage.getItem('ryxhub_selected_session');
    return stored || null;
  });

  // Models state - fetch from API
  const [models, setModels] = useState<Model[]>(mockModels);

  // Tools state
  const [tools, setTools] = useState<ToolConfig[]>(defaultTools);

  // RAG state
  const [ragStatus, setRAGStatus] = useState<RAGStatus>({
    indexed: 0,
    pending: 0,
    lastSync: "never",
    status: "idle",
  });

  // Board state
  const [boards, setBoards] = useState<Board[]>(() => {
    const stored = localStorage.getItem('ryxhub_boards');
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        return [];
      }
    }
    // Default board
    return [{
      id: 'default-board',
      name: 'Mein Board',
      description: 'Hauptboard für Dokumente und Notizen',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      isDefault: true,
      category: 'personal',
    }];
  });
  const [selectedBoardId, setSelectedBoardId] = useState<string | null>(() => {
    const stored = localStorage.getItem('ryxhub_selected_board');
    return stored || 'default-board';
  });

  // Memory state
  const [memories, setMemories] = useState<UserMemory[]>(() => {
    const stored = localStorage.getItem('ryxhub_memories');
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        return [];
      }
    }
    return [];
  });

  // Gmail accounts state
  const [gmailAccounts, setGmailAccounts] = useState<GmailAccount[]>(() => {
    const stored = localStorage.getItem('ryxhub_gmail_accounts');
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        return [];
      }
    }
    return [];
  });

  const defaultGmailAccount = gmailAccounts.find(a => a.isDefault) || null;

  // Save selected session to localStorage
  useEffect(() => {
    if (selectedSessionId) {
      localStorage.setItem('ryxhub_selected_session', selectedSessionId);
    }
  }, [selectedSessionId]);

  // Fetch sessions from API on mount
  const refreshSessions = useCallback(async () => {
    try {
      const response = await fetch(API_ENDPOINTS.sessions);
      if (response.ok) {
        const data = await response.json();
        if (data.sessions && data.sessions.length > 0) {
          setSessions(data.sessions);
          localStorage.setItem('ryxhub_sessions', JSON.stringify(data.sessions));
          // Auto-select first session if none selected
          if (!selectedSessionId) {
            setSelectedSessionId(data.sessions[0].id);
          }
        }
      }
    } catch (error) {
      console.warn('Failed to fetch sessions:', error);
    }
  }, [selectedSessionId]);

  // Fetch RAG status
  const refreshRAGStatus = useCallback(async () => {
    try {
      const response = await fetch(API_ENDPOINTS.ragStatus);
      if (response.ok) {
        const data = await response.json();
        setRAGStatus(data);
      }
    } catch (error) {
      console.warn('Failed to fetch RAG status:', error);
    }
  }, []);

  // Fetch models from API on mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await fetch(API_ENDPOINTS.models);
        if (response.ok) {
          const data = await response.json();
          if (data.models) {
            setModels(data.models);
          }
        }
      } catch (error) {
        console.warn('Failed to fetch models, using mock data');
      }
    };
    fetchModels();
    refreshSessions();
    refreshRAGStatus();
    // Refresh every 10 seconds
    const interval = setInterval(fetchModels, 10000);
    return () => clearInterval(interval);
  }, [refreshSessions, refreshRAGStatus]);

  // Board functions
  const selectBoard = useCallback((id: string) => {
    setSelectedBoardId(id);
    localStorage.setItem('ryxhub_selected_board', id);
  }, []);

  const refreshBoards = useCallback(async () => {
    try {
      const response = await fetch('/api/boards');
      if (response.ok) {
        const data = await response.json();
        if (data.boards) {
          setBoards(data.boards);
          localStorage.setItem('ryxhub_boards', JSON.stringify(data.boards));
        }
      }
    } catch (error) {
      console.warn('Failed to fetch boards:', error);
    }
  }, []);

  const createBoard = useCallback(async (name: string, category?: string): Promise<Board | null> => {
    const newBoard: Board = {
      id: `board-${Date.now()}`,
      name,
      category: category as Board['category'] || 'other',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    setBoards((prev) => {
      const updated = [...prev, newBoard];
      localStorage.setItem('ryxhub_boards', JSON.stringify(updated));
      return updated;
    });

    return newBoard;
  }, []);

  // Memory functions
  const refreshMemories = useCallback(async () => {
    try {
      const response = await fetch('/api/memory');
      if (response.ok) {
        const data = await response.json();
        if (data.memories) {
          setMemories(data.memories);
          localStorage.setItem('ryxhub_memories', JSON.stringify(data.memories));
        }
      }
    } catch (error) {
      console.warn('Failed to fetch memories:', error);
    }
  }, []);

  // Gmail functions
  const refreshGmailAccounts = useCallback(async () => {
    try {
      const response = await fetch('/api/gmail/accounts');
      if (response.ok) {
        const data = await response.json();
        if (data.accounts) {
          setGmailAccounts(data.accounts);
          localStorage.setItem('ryxhub_gmail_accounts', JSON.stringify(data.accounts));
        }
      }
    } catch (error) {
      console.warn('Failed to fetch Gmail accounts:', error);
    }
  }, []);

  const selectSession = useCallback((id: string) => {
    setSelectedSessionId(id);
    setSessions((prev) =>
      prev.map((s) => ({
        ...s,
        isActive: s.id === id,
      }))
    );
  }, []);

  const addMessageToSession = useCallback((sessionId: string, message: Omit<Message, "id">) => {
    setSessions((prev) => {
      const updated = prev.map((s) => {
        if (s.id === sessionId) {
          const newMessage: Message = {
            ...message,
            id: `msg-${Date.now()}`,
          };
          return {
            ...s,
            messages: [...s.messages, newMessage],
            lastMessage: message.content.slice(0, 30) + "...",
            timestamp: "just now",
          };
        }
        return s;
      });
      // Persist to localStorage
      localStorage.setItem('ryxhub_sessions', JSON.stringify(updated));
      return updated;
    });
  }, []);

  const clearSessionMessages = useCallback((sessionId: string) => {
    // Clear messages locally (no backend needed)
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === sessionId) {
          return {
            ...s,
            messages: [],
            lastMessage: "Chat cleared",
            timestamp: "just now",
          };
        }
        return s;
      })
    );
    // Persist to localStorage
    const stored = localStorage.getItem('ryxhub_sessions');
    if (stored) {
      try {
        const sessions = JSON.parse(stored);
        const updated = sessions.map((s: Session) =>
          s.id === sessionId ? { ...s, messages: [], lastMessage: "Chat cleared" } : s
        );
        localStorage.setItem('ryxhub_sessions', JSON.stringify(updated));
      } catch {}
    }
  }, []);

  const editMessageInSession = useCallback((sessionId: string, messageId: string, newContent: string) => {
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === sessionId) {
          const msgIndex = s.messages.findIndex(m => m.id === messageId);
          if (msgIndex === -1) return s;
          
          // Edit the message and remove any subsequent assistant messages
          const newMessages = s.messages.slice(0, msgIndex);
          newMessages.push({ ...s.messages[msgIndex], content: newContent });
          
          return { ...s, messages: newMessages };
        }
        return s;
      })
    );
  }, []);

  const addVariantToMessage = useCallback((sessionId: string, messageId: string, variant: Omit<MessageVariant, "id">) => {
    setSessions((prev) => {
      const updated = prev.map((s) => {
        if (s.id === sessionId) {
          return {
            ...s,
            messages: s.messages.map((m) => {
              if (m.id === messageId) {
                const newVariant: MessageVariant = {
                  ...variant,
                  id: `var-${Date.now()}`,
                };
                const variants = m.variants ? [...m.variants, newVariant] : [newVariant];
                return {
                  ...m,
                  variants,
                  activeVariant: variants.length, // Switch to the new variant
                };
              }
              return m;
            }),
          };
        }
        return s;
      });
      localStorage.setItem('ryxhub_sessions', JSON.stringify(updated));
      return updated;
    });
  }, []);

  const setActiveVariant = useCallback((sessionId: string, messageId: string, variantIndex: number) => {
    setSessions((prev) => {
      const updated = prev.map((s) => {
        if (s.id === sessionId) {
          return {
            ...s,
            messages: s.messages.map((m) => {
              if (m.id === messageId) {
                return { ...m, activeVariant: variantIndex };
              }
              return m;
            }),
          };
        }
        return s;
      });
      localStorage.setItem('ryxhub_sessions', JSON.stringify(updated));
      return updated;
    });
  }, []);

  const updateSessionTools = useCallback(async (sessionId: string, toolId: string, enabled: boolean) => {
    // Update local state first for immediate UI feedback
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === sessionId) {
          return {
            ...s,
            tools: { ...(s.tools || {}), [toolId]: enabled },
          };
        }
        return s;
      })
    );

    // Persist to API
    try {
      await fetch(API_ENDPOINTS.sessionTools(sessionId), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ toolId, enabled }),
      });
    } catch (error) {
      console.warn('Failed to persist tool state to API:', error);
    }

    // Persist to localStorage as backup
    const stored = localStorage.getItem('ryxhub_sessions');
    if (stored) {
      const sessions = JSON.parse(stored);
      const updated = sessions.map((s: Session) =>
        s.id === sessionId ? { ...s, tools: { ...(s.tools || {}), [toolId]: enabled } } : s
      );
      localStorage.setItem('ryxhub_sessions', JSON.stringify(updated));
    }
  }, []);

  const createSession = useCallback((name: string, model?: string): Promise<Session | null> => {
    const newSession: Session = {
      id: `session-${Date.now()}`,
      name: name || `Session ${new Date().toLocaleTimeString()}`,
      model: model || 'qwen2.5:1.5b',
      lastMessage: '',
      timestamp: 'just now',
      isActive: true,
      messages: [],
      agentId: `agent-${Date.now()}`,
    };
    
    setSessions((prev) => {
      const updated = [newSession, ...prev.map(s => ({ ...s, isActive: false }))];
      localStorage.setItem('ryxhub_sessions', JSON.stringify(updated));
      return updated;
    });
    setSelectedSessionId(newSession.id);
    localStorage.setItem('ryxhub_selected_session', newSession.id);
    return Promise.resolve(newSession);
  }, []);

  const toggleTool = useCallback((toolId: string, enabled: boolean) => {
    setTools((prev) =>
      prev.map((tool) =>
        tool.id === toolId ? { ...tool, enabled } : tool
      )
    );

    // Persist tool state to backend if session is selected
    if (selectedSessionId) {
      fetch(API_ENDPOINTS.sessionTools(selectedSessionId), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ toolId, enabled }),
      }).catch((err) => console.warn('Failed to persist tool state:', err));
    }
  }, [selectedSessionId]);

  const deleteSession = useCallback((sessionId: string): Promise<void> => {
    setSessions((prev) => {
      const updated = prev.filter((s) => s.id !== sessionId);
      localStorage.setItem('ryxhub_sessions', JSON.stringify(updated));
      return updated;
    });

    // Clear selection if deleted session was selected
    if (selectedSessionId === sessionId) {
      setSelectedSessionId(null);
      localStorage.removeItem('ryxhub_selected_session');
    }
    
    // Remove all session-related data from localStorage
    localStorage.removeItem(`session-style-${sessionId}`);
    localStorage.removeItem(`session-tools-${sessionId}`);
    localStorage.removeItem(`session-lastused-${sessionId}`);
    
    return Promise.resolve();
  }, [selectedSessionId]);

  const renameSession = useCallback((sessionId: string, newName: string): Promise<void> => {
    setSessions((prev) => {
      const updated = prev.map((s) => (s.id === sessionId ? { ...s, name: newName } : s));
      localStorage.setItem('ryxhub_sessions', JSON.stringify(updated));
      return updated;
    });
    return Promise.resolve();
  }, []);

  return (
    <RyxHubContext.Provider
      value={{
        activeView,
        setActiveView,
        sessions,
        selectedSessionId,
        selectSession,
        createSession,
        addMessageToSession,
        clearSessionMessages,
        editMessageInSession,
        updateSessionTools,
        deleteSession,
        renameSession,
        refreshSessions,
        addVariantToMessage,
        setActiveVariant,
        models,
        ragStatus,
        refreshRAGStatus,
        tools,
        toggleTool,
        boards,
        selectedBoardId,
        selectBoard,
        createBoard,
        refreshBoards,
        memories,
        refreshMemories,
        gmailAccounts,
        defaultGmailAccount,
        refreshGmailAccounts,
      }}
    >
      {children}
    </RyxHubContext.Provider>
  );
}

export function useRyxHub() {
  const context = useContext(RyxHubContext);
  if (!context) {
    throw new Error("useRyxHub must be used within a RyxHubProvider");
  }
  return context;
}
