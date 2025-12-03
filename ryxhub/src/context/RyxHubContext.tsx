import { createContext, useContext, useState, useCallback, ReactNode } from "react";
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

  // Models state
  const [models] = useState<Model[]>(mockModels);

  // RAG state
  const [ragStatus] = useState<RAGStatus>(mockRAGStatus);

  // Workflow state
  const [workflowNodes] = useState<WorkflowNode[]>(mockWorkflowNodes);
  const [connections] = useState<Connection[]>(mockConnections);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isWorkflowRunning, setIsWorkflowRunning] = useState(true);

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

  return (
    <RyxHubContext.Provider
      value={{
        activeView,
        setActiveView,
        sessions,
        selectedSessionId,
        selectSession,
        addMessageToSession,
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
