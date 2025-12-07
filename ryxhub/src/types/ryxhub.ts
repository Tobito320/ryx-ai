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
  boardId?: string; // Link session to a board
}

// ============================================================================
// Board Types - Infinite Canvas for Documents, Notes, and Knowledge
// ============================================================================

export interface Board {
  id: string;
  name: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
  isDefault?: boolean;
  category?: "personal" | "work" | "finance" | "health" | "education" | "auto" | "other";
}

export interface BoardDocument {
  id: string;
  boardId: string;
  name: string;
  type: "pdf" | "image" | "note" | "email" | "letter" | "template" | "link";
  path?: string; // File path on disk
  content?: string; // For notes/templates
  metadata?: DocumentMetadata;
  x: number;
  y: number;
  width?: number;
  height?: number;
  createdAt: string;
  updatedAt: string;
}

export interface DocumentMetadata {
  sender?: string; // Who sent the letter/email
  recipient?: string; // Who it's addressed to
  date?: string; // Date of document
  subject?: string;
  category?: string; // AOK, Sparkasse, Arbeit, etc.
  tags?: string[];
  summary?: string; // AI-generated summary
  requiresResponse?: boolean;
  responseDeadline?: string;
  relatedDocuments?: string[]; // IDs of related documents
}

export interface BoardConnection {
  id: string;
  boardId: string;
  fromId: string;
  toId: string;
  label?: string;
  type?: "related" | "response" | "reference" | "followup";
}

// ============================================================================
// Memory Types - Personal Knowledge and Context
// ============================================================================

export interface UserMemory {
  id: string;
  type: "fact" | "preference" | "contact" | "template" | "routine";
  key: string;
  value: string;
  confidence: number; // 0-1, how sure the AI is about this
  source?: string; // Where this was learned from
  createdAt: string;
  updatedAt: string;
  usageCount: number;
}

export interface Contact {
  id: string;
  name: string;
  organization?: string; // AOK, Sparkasse, Arbeitgeber, etc.
  email?: string;
  phone?: string;
  address?: string;
  notes?: string;
  category?: string;
}

// ============================================================================
// Gmail Integration Types
// ============================================================================

export interface GmailAccount {
  id: string;
  email: string;
  name: string;
  isDefault: boolean;
  lastSync?: string;
  accessToken?: string; // Stored securely
  refreshToken?: string;
}

export interface EmailDraft {
  id: string;
  accountId: string; // Which Gmail account to use
  to: string[];
  cc?: string[];
  bcc?: string[];
  subject: string;
  body: string;
  replyToId?: string; // If this is a reply
  relatedDocumentIds?: string[]; // Documents this email references
  status: "draft" | "sent" | "scheduled";
  scheduledFor?: string;
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

export type ViewMode = "dashboard" | "chat" | "board" | "settings";

// Helper to extract model name from path
export function getModelDisplayName(modelPath: string): string {
  if (!modelPath) return "Unknown";
  const parts = modelPath.split('/');
  return parts[parts.length - 1] || modelPath;
}
