/**
 * Application configuration
 * Centralizes API URLs and other configuration values
 */

// vLLM API base URL - typically runs on port 8001
export const VLLM_API_URL = import.meta.env.VITE_VLLM_API_URL || 'http://localhost:8001';

// Ryx backend API base URL - for sessions, RAG, workflows
export const API_BASE_URL = import.meta.env.VITE_RYX_API_URL || 'http://localhost:8420';

// API endpoints
export const API_ENDPOINTS = {
  // Health & Status
  health: `${API_BASE_URL}/api/health`,
  status: `${API_BASE_URL}/api/status`,
  
  // Stats
  dashboardStats: `${API_BASE_URL}/api/stats/dashboard`,
  recentActivity: `${API_BASE_URL}/api/activity/recent`,
  topWorkflows: `${API_BASE_URL}/api/workflows/top`,
  
  // Models (via backend for enriched status info)
  models: `${API_BASE_URL}/api/models`,
  completions: `${VLLM_API_URL}/v1/chat/completions`,
  
  // Sessions
  sessions: `${API_BASE_URL}/api/sessions`,
  sessionById: (id: string) => `${API_BASE_URL}/api/sessions/${id}`,
  sessionMessages: (id: string) => `${API_BASE_URL}/api/sessions/${id}/messages`,
  sessionTools: (id: string) => `${API_BASE_URL}/api/sessions/${id}/tools`,
  sessionExport: (id: string, format = 'markdown') =>
    `${API_BASE_URL}/api/sessions/${id}/export?format=${format}`,

  // Tools
  tools: `${API_BASE_URL}/api/tools`,
  searxngStatus: `${API_BASE_URL}/api/searxng/status`,
  searxngSearch: `${API_BASE_URL}/api/searxng/search`,
  
  // Workflows (legacy, kept for compatibility)
  workflows: `${API_BASE_URL}/api/workflows`,
  workflowById: (id: string) => `${API_BASE_URL}/api/workflows/${id}`,
  
  // RAG
  ragStatus: `${API_BASE_URL}/api/rag/status`,
  ragUpload: `${API_BASE_URL}/api/rag/upload`,
  ragSearch: `${API_BASE_URL}/api/rag/search`,
  ragSync: `${API_BASE_URL}/api/rag/sync`,

  // Board Mode - Documents, Memory, Gmail
  documentsScan: `${API_BASE_URL}/api/documents/scan`,
  
  memory: `${API_BASE_URL}/api/memory`,
  memoryById: (id: string) => `${API_BASE_URL}/api/memory/${id}`,
  
  gmailAccounts: `${API_BASE_URL}/api/gmail/accounts`,
  gmailAccountById: (id: string) => `${API_BASE_URL}/api/gmail/accounts/${id}`,
  gmailAccountDefault: (id: string) => `${API_BASE_URL}/api/gmail/accounts/${id}/default`,
  
  boards: `${API_BASE_URL}/api/boards`,
  boardById: (id: string) => `${API_BASE_URL}/api/boards/${id}`,
};

// Polling intervals (milliseconds)
export const POLLING_INTERVALS = {
  models: 10000,      // 10 seconds
  dashboard: 10000,   // 10 seconds
  workflows: 30000,   // 30 seconds
};

export default {
  VLLM_API_URL,
  API_BASE_URL,
  API_ENDPOINTS,
  POLLING_INTERVALS,
};
