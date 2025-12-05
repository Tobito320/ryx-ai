import type {
  Session,
  Model,
  RAGStatus,
  WorkflowNode,
  Connection,
  DashboardStats,
  Message,
} from "@/types/ryxhub";

// No hardcoded sessions - all sessions should come from the API
export const mockSessions: Session[] = [];

// No hardcoded models - all models should come from the API
export const mockModels: Model[] = [];

// RAG Status
export const mockRAGStatus: RAGStatus = {
  indexed: 1247,
  pending: 23,
  lastSync: "5m ago",
  status: "idle",
};

// Dashboard Stats
export const mockDashboardStats: DashboardStats = {
  activeAgents: { value: 12, change: "+3 today" },
  workflowsRunning: { value: 4, queued: 2 },
  ragDocuments: { value: 1247, pending: 23 },
  apiCalls: { value: "8.2K", period: "Last 24h" },
};

// Workflow Nodes with detailed config and logs
export const mockWorkflowNodes: WorkflowNode[] = [
  {
    id: "trigger-1",
    type: "trigger",
    name: "GitHub PR Event",
    x: 100,
    y: 200,
    status: "success",
    config: {
      repository: "org/main-repo",
      events: ["pull_request.opened", "pull_request.synchronize"],
      branch: "main",
    },
    logs: [
      { time: "10:24:30", level: "info", message: "Webhook received from GitHub" },
      { time: "10:24:30", level: "info", message: "PR #234 opened by @developer" },
      { time: "10:24:31", level: "success", message: "Trigger activated successfully" },
    ],
    runs: [
      { id: "run-t1-1", status: "success", duration: "0.1s", timestamp: "2m ago" },
      { id: "run-t1-2", status: "success", duration: "0.1s", timestamp: "1h ago" },
    ],
  },
  {
    id: "agent-1",
    type: "agent",
    name: "Code Analyzer",
    x: 350,
    y: 120,
    status: "running",
    config: {
      model: "Qwen2.5-7B-Instruct",
      temperature: 0.7,
      maxTokens: 4096,
      ragEnabled: true,
      ragTopK: 5,
      timeout: "30s",
    },
    logs: [
      { time: "10:24:32", level: "info", message: "Initializing Code Analyzer agent..." },
      { time: "10:24:33", level: "info", message: "Loading context from RAG index (1,247 documents)" },
      { time: "10:24:35", level: "success", message: "Context loaded successfully" },
      { time: "10:24:36", level: "info", message: "Analyzing PR #234 changes..." },
      { time: "10:24:38", level: "warning", message: "Potential security issue detected in user_service.py" },
      { time: "10:24:40", level: "info", message: "Generating recommendations..." },
    ],
    runs: [
      { id: "run-a1-1", status: "running", duration: "2.3s", timestamp: "now" },
      { id: "run-a1-2", status: "success", duration: "1.8s", timestamp: "15m ago" },
      { id: "run-a1-3", status: "error", duration: "0.5s", timestamp: "1h ago" },
    ],
  },
  {
    id: "agent-2",
    type: "agent",
    name: "Security Scanner",
    x: 350,
    y: 280,
    status: "idle",
    config: {
      model: "Llama-3.2-3B-Instruct",
      temperature: 0.3,
      maxTokens: 2048,
      scanTypes: ["SQL Injection", "XSS", "CSRF", "Secrets"],
    },
    logs: [
      { time: "10:20:00", level: "info", message: "Security Scanner ready" },
      { time: "10:20:01", level: "info", message: "Waiting for upstream agent..." },
    ],
    runs: [
      { id: "run-a2-1", status: "success", duration: "3.2s", timestamp: "30m ago" },
      { id: "run-a2-2", status: "success", duration: "2.9s", timestamp: "2h ago" },
    ],
  },
  {
    id: "tool-1",
    type: "tool",
    name: "RAG Search",
    x: 600,
    y: 120,
    status: "idle",
    config: {
      indexName: "codebase-index",
      topK: 10,
      minScore: 0.75,
      namespace: "production",
    },
    logs: [
      { time: "10:15:00", level: "info", message: "RAG Search tool initialized" },
    ],
    runs: [
      { id: "run-t1-1", status: "success", duration: "0.4s", timestamp: "5m ago" },
    ],
  },
  {
    id: "tool-2",
    type: "tool",
    name: "Slack Notify",
    x: 600,
    y: 280,
    status: "idle",
    config: {
      channel: "#code-reviews",
      mentionUsers: ["@security-team"],
      template: "security-alert",
    },
    logs: [
      { time: "10:10:00", level: "info", message: "Slack integration ready" },
    ],
    runs: [
      { id: "run-t2-1", status: "success", duration: "0.2s", timestamp: "1h ago" },
    ],
  },
  {
    id: "output-1",
    type: "output",
    name: "PR Comment",
    x: 850,
    y: 200,
    status: "idle",
    config: {
      repository: "org/main-repo",
      commentTemplate: "review-summary",
      autoApprove: false,
    },
    logs: [
      { time: "10:05:00", level: "info", message: "Output node ready" },
    ],
    runs: [
      { id: "run-o1-1", status: "success", duration: "0.3s", timestamp: "2h ago" },
    ],
  },
];

export const mockConnections: Connection[] = [
  { id: "c1", from: "trigger-1", to: "agent-1" },
  { id: "c2", from: "trigger-1", to: "agent-2" },
  { id: "c3", from: "agent-1", to: "tool-1" },
  { id: "c4", from: "agent-2", to: "tool-2" },
  { id: "c5", from: "tool-1", to: "output-1" },
  { id: "c6", from: "tool-2", to: "output-1" },
];

// Recent Activity for Dashboard
export const mockRecentActivity = [
  { id: 1, type: "success" as const, message: "PR Review Workflow completed", time: "2m ago" },
  { id: 2, type: "info" as const, message: "Code Analyzer agent started", time: "5m ago" },
  { id: 3, type: "warning" as const, message: "RAG index sync delayed", time: "12m ago" },
  { id: 4, type: "success" as const, message: "Security Scanner found 0 issues", time: "15m ago" },
  { id: 5, type: "info" as const, message: "New documents indexed (23)", time: "20m ago" },
];

// Top Workflows for Dashboard
export const mockTopWorkflows = [
  { name: "PR Review", runs: 156, successRate: 98 },
  { name: "Code Analysis", runs: 89, successRate: 95 },
  { name: "Security Scan", runs: 67, successRate: 100 },
  { name: "Doc Generation", runs: 45, successRate: 91 },
];
