/**
 * Centralized type definitions
 */

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  status?: 'sending' | 'sent' | 'failed' | 'queued';
  performanceMetrics?: {
    totalTime?: number; // seconds
    ttft?: number; // Time To First Token in seconds
    inputTokens?: number;
    outputTokens?: number;
    tokensPerSecond?: number;
  };
}

export interface ChatRequest {
  message: string;
  sessionId?: string;
  model?: string;
  ragEnabled?: boolean;
  prompt?: string; // For vLLM backend format
}

export interface ChatResponse {
  message: string;
  response?: string; // For vLLM backend format
  sessionId?: string;
  error?: string;
}

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  source?: string;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  provider: string;
  error?: string;
}

export type SearchProvider = 'searxng' | 'duckduckgo' | 'google' | 'bing' | 'brave';

export interface SearchProviderConfig {
  id: SearchProvider;
  name: string;
  apiUrl?: string; // Optional custom API URL
  enabled: boolean;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
}

export interface Session {
  id: string;
  name: string;
  createdAt: number;        // Changed from Date to number (Unix timestamp)
  lastActive: number;       // Changed from Date to number (Unix timestamp)
  messageCount: number;
  modelName?: string;
}

export interface Model {
  id: string;
  name: string;
  portRange: string;
  status: 'available' | 'loaded' | 'loading' | 'error';
  size?: number;        // File size in bytes
  path?: string;        // Actual filename (e.g., "Llama-3.2-3B-Instruct-Q4_K_M.gguf")
}

export interface RAGFile {
  id: string;
  name: string;
  path: string;
  size: number; // bytes
  addedAt: number;
}

export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'reconnecting';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
}

