// Core types for RyxHub

export interface Session {
  id: string;
  name: string;
  lastMessage: string;
  timestamp: string;
  isActive?: boolean;
  messages: Message[];
  agentId: string;
  model: string;
  tools?: { [toolId: string]: boolean };
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  model?: string;
  latency_ms?: number;
  tokens_per_second?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
}

export interface Model {
  id: string;
  name: string;
  status: "online" | "offline" | "loading";
  provider: string;
}

export interface RAGStatus {
  indexed: number;
  pending: number;
  lastSync: string;
  status: "syncing" | "idle" | "error";
}

export interface WorkflowNode {
  id: string;
  type: "trigger" | "agent" | "tool" | "output";
  name: string;
  x: number;
  y: number;
  status: "idle" | "running" | "success" | "error";
  config: Record<string, unknown>;
  logs: LogEntry[];
  runs: RunHistory[];
}

export interface Connection {
  id: string;
  from: string;
  to: string;
}

export interface LogEntry {
  time: string;
  level: "info" | "success" | "warning" | "error";
  message: string;
}

export interface RunHistory {
  id: string;
  status: "success" | "error" | "running";
  duration: string;
  timestamp: string;
}

export interface DashboardStats {
  activeAgents: { value: number; change: string };
  workflowsRunning: { value: number; queued: number };
  ragDocuments: { value: number; pending: number };
  apiCalls: { value: string; period: string };
}

export interface Workflow {
  id: string;
  name: string;
  nodes: WorkflowNode[];
  connections: Connection[];
  lastRun: string;
  status: "idle" | "running" | "paused";
}

export type ViewMode = "dashboard" | "chat" | "workflow" | "council" | "settings";

// Helper to extract model name from path
export function getModelDisplayName(modelPath: string): string {
  if (!modelPath) return "Unknown";
  const parts = modelPath.split('/');
  return parts[parts.length - 1] || modelPath;
}
