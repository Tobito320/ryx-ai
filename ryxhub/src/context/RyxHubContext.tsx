import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from "react";
import type { Session, Model, RAGStatus, WorkflowNode, Connection, ViewMode, Message } from "@/types/ryxhub";
import {
  mockModels,
  mockWorkflowNodes,
  mockConnections,
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

  // Models
  models: Model[];

  // RAG
  ragStatus: RAGStatus;
  refreshRAGStatus: () => Promise<void>;

  // Tools
  tools: ToolConfig[];
  toggleTool: (toolId: string, enabled: boolean) => void;

  // Workflow
  workflowNodes: WorkflowNode[];
  connections: Connection[];
  selectedNodeId: string | null;
  selectNode: (id: string | null) => void;
  isWorkflowRunning: boolean;
  toggleWorkflowRunning: () => void;
  addWorkflowNode: (node: WorkflowNode) => void;
  runWorkflow: (workflowId: string) => Promise<void>;
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

  // Workflow state
  const [workflowNodes, setWorkflowNodes] = useState<WorkflowNode[]>(mockWorkflowNodes);
  const [connections, setConnections] = useState<Connection[]>(mockConnections);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isWorkflowRunning, setIsWorkflowRunning] = useState(false);

  // Fetch workflows from API
  useEffect(() => {
    const fetchWorkflows = async () => {
      try {
        const response = await fetch(API_ENDPOINTS.workflows);
        if (response.ok) {
          const data = await response.json();
          console.log('Workflows loaded:', data.workflows?.length || 0);
        }
      } catch (error) {
        console.warn('Failed to fetch workflows');
      }
    };
    fetchWorkflows();
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
      const sessions = JSON.parse(stored);
      const updated = sessions.map((s: Session) => 
        s.id === sessionId ? { ...s, messages: [], lastMessage: "Chat cleared" } : s
      );
      localStorage.setItem('ryxhub_sessions', JSON.stringify(updated));
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

  const updateSessionTools = useCallback((sessionId: string, toolId: string, enabled: boolean) => {
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
    // Persist
    const stored = localStorage.getItem('ryxhub_sessions');
    if (stored) {
      const sessions = JSON.parse(stored);
      const updated = sessions.map((s: Session) => 
        s.id === sessionId ? { ...s, tools: { ...(s.tools || {}), [toolId]: enabled } } : s
      );
      localStorage.setItem('ryxhub_sessions', JSON.stringify(updated));
    }
  }, []);

  const selectNode = useCallback((id: string | null) => {
    setSelectedNodeId(id);
  }, []);

  const toggleWorkflowRunning = useCallback(() => {
    setIsWorkflowRunning((prev) => !prev);
  }, []);

  const addWorkflowNode = useCallback((node: WorkflowNode) => {
    setWorkflowNodes((prev) => [...prev, node]);
  }, []);

  const createSession = useCallback(async (name: string, model?: string): Promise<Session | null> => {
    try {
      const response = await fetch(API_ENDPOINTS.sessions, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, model }),
      });

      if (response.ok) {
        const newSession = await response.json();
        setSessions((prev) => [newSession, ...prev]);
        setSelectedSessionId(newSession.id);
        return newSession;
      }
    } catch (error) {
      console.error('Failed to create session:', error);
    }
    return null;
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

  const runWorkflow = useCallback(async (workflowId: string) => {
    try {
      const response = await fetch(`${API_ENDPOINTS.workflowById(workflowId)}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });

      if (response.ok) {
        const result = await response.json();
        setIsWorkflowRunning(true);
        console.log('Workflow started:', result);

        // Update node statuses as workflow runs
        if (result.runId) {
          // Could connect to WebSocket here for real-time updates
          console.log('Run ID:', result.runId);
        }
      }
    } catch (error) {
      console.error('Failed to run workflow:', error);
    }
  }, []);

  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      const response = await fetch(API_ENDPOINTS.sessionById(sessionId), {
        method: 'DELETE',
      });
      
      if (response.ok) {
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
        if (selectedSessionId === sessionId) {
          setSelectedSessionId(null);
        }
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
      throw error;
    }
  }, [selectedSessionId]);

  const renameSession = useCallback(async (sessionId: string, newName: string) => {
    try {
      const response = await fetch(API_ENDPOINTS.sessionById(sessionId), {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: newName }),
      });
      
      if (response.ok) {
        const updated = await response.json();
        setSessions((prev) =>
          prev.map((s) => (s.id === sessionId ? { ...s, name: newName } : s))
        );
      }
    } catch (error) {
      console.error('Failed to rename session:', error);
      throw error;
    }
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
        models,
        ragStatus,
        refreshRAGStatus,
        tools,
        toggleTool,
        workflowNodes,
        connections,
        selectedNodeId,
        selectNode,
        isWorkflowRunning,
        toggleWorkflowRunning,
        addWorkflowNode,
        runWorkflow,
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
