import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from "react";
import type { Session, Model, RAGStatus, WorkflowNode, Connection, ViewMode, Message } from "@/types/ryxhub";
import {
  mockSessions,
  mockModels,
  mockRAGStatus,
  mockWorkflowNodes,
  mockConnections,
} from "@/data/mockData";

interface RyxHubContextType {
  // View state
  activeView: ViewMode;
  setActiveView: (view: ViewMode) => void;

  // Sessions
  sessions: Session[];
  selectedSessionId: string | null;
  selectSession: (id: string) => void;
  addMessageToSession: (sessionId: string, message: Omit<Message, "id">) => void;
  deleteSession: (sessionId: string) => Promise<void>;
  renameSession: (sessionId: string, newName: string) => Promise<void>;

  // Models
  models: Model[];

  // RAG
  ragStatus: RAGStatus;

  // Workflow
  workflowNodes: WorkflowNode[];
  connections: Connection[];
  selectedNodeId: string | null;
  selectNode: (id: string | null) => void;
  isWorkflowRunning: boolean;
  toggleWorkflowRunning: () => void;
}

const RyxHubContext = createContext<RyxHubContextType | null>(null);

export function RyxHubProvider({ children }: { children: ReactNode }) {
  // View state
  const [activeView, setActiveView] = useState<ViewMode>("dashboard");

  // Sessions state
  const [sessions, setSessions] = useState<Session[]>(mockSessions);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>("session-1");

  // Models state - fetch from API
  const [models, setModels] = useState<Model[]>(mockModels);
  
  // Fetch models from API on mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await fetch('http://localhost:8420/api/models');
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
    // Refresh every 10 seconds
    const interval = setInterval(fetchModels, 10000);
    return () => clearInterval(interval);
  }, []);

  // RAG state
  const [ragStatus] = useState<RAGStatus>(mockRAGStatus);

  // Workflow state
  const [workflowNodes, setWorkflowNodes] = useState<WorkflowNode[]>(mockWorkflowNodes);
  const [connections, setConnections] = useState<Connection[]>(mockConnections);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isWorkflowRunning, setIsWorkflowRunning] = useState(false);

  // Fetch workflows from API
  useEffect(() => {
    const fetchWorkflows = async () => {
      try {
        const response = await fetch('http://localhost:8420/api/workflows');
        if (response.ok) {
          const data = await response.json();
          // For now, keep using mock workflow nodes until we implement
          // full workflow canvas with backend persistence
          console.log('Workflows loaded:', data.workflows);
        }
      } catch (error) {
        console.warn('Failed to fetch workflows, using mock data');
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
    setSessions((prev) =>
      prev.map((s) => {
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
      })
    );
  }, []);

  const selectNode = useCallback((id: string | null) => {
    setSelectedNodeId(id);
  }, []);

  const toggleWorkflowRunning = useCallback(() => {
    setIsWorkflowRunning((prev) => !prev);
  }, []);

  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      const response = await fetch(`http://localhost:8420/api/sessions/${sessionId}`, {
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
      const response = await fetch(`http://localhost:8420/api/sessions/${sessionId}`, {
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
        addMessageToSession,
        deleteSession,
        renameSession,
        models,
        ragStatus,
        workflowNodes,
        connections,
        selectedNodeId,
        selectNode,
        isWorkflowRunning,
        toggleWorkflowRunning,
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
