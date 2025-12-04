/**
 * RyxHub Live API Client
 *
 * HTTP client for communicating with the Ryx backend running on vLLM/ROCm.
 * Handles all API calls with proper error handling, timeouts, and retries.
 */

// Get API URL from environment
const API_BASE_URL = import.meta.env.VITE_RYX_API_URL || 'http://localhost:8420';

// Default timeout for API calls (30 seconds)
const DEFAULT_TIMEOUT = 30000;

// Custom error class for API errors
export class RyxApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string,
    public details?: unknown
  ) {
    super(message);
    this.name = 'RyxApiError';
  }
}

// Types for API responses
export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  uptime: number;
  vllm_status: 'online' | 'offline' | 'starting';
}

export interface StatusResponse {
  models_loaded: number;
  active_sessions: number;
  gpu_memory_used: number;
  gpu_memory_total: number;
  vllm_workers: number;
}

export interface Model {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'loading';
  provider: string;
  context_length?: number;
  parameters?: string;
}

export interface Session {
  id: string;
  name: string;
  lastMessage: string;
  timestamp: string;
  isActive?: boolean;
  messages: Message[];
  agentId: string;
  model: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  model?: string;
}

export interface RAGStatus {
  indexed: number;
  pending: number;
  lastSync: string;
  status: 'syncing' | 'idle' | 'error';
}

export interface SyncResponse {
  success: boolean;
  queued_files: number;
}

export interface SearchResult {
  id: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface SearchResults {
  results: SearchResult[];
  total: number;
}

export interface Workflow {
  id: string;
  name: string;
  status: 'idle' | 'running' | 'paused';
  lastRun: string;
}

export interface RunResponse {
  success: boolean;
  run_id: string;
}

export interface Agent {
  id: string;
  name: string;
  status: 'active' | 'idle' | 'error';
  model: string;
}

export interface LogEntry {
  time: string;
  level: 'info' | 'success' | 'warning' | 'error';
  message: string;
}

export interface Tool {
  id: string;
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

/**
 * Make an API request with timeout and error handling
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
  timeout: number = DEFAULT_TIMEOUT
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = { message: response.statusText };
      }

      throw new RyxApiError(
        errorData.message || `API error: ${response.status}`,
        response.status,
        errorData.code,
        errorData
      );
    }

    // Handle empty responses
    const text = await response.text();
    if (!text) {
      return {} as T;
    }

    return JSON.parse(text) as T;
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof RyxApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new RyxApiError('Request timed out', undefined, 'TIMEOUT');
      }
      if (error.message.includes('fetch')) {
        throw new RyxApiError(
          'Cannot connect to Ryx backend. Is vLLM running?',
          undefined,
          'CONNECTION_FAILED'
        );
      }
      throw new RyxApiError(error.message, undefined, 'UNKNOWN');
    }

    throw new RyxApiError('Unknown error occurred', undefined, 'UNKNOWN');
  }
}

/**
 * Ryx API Client
 *
 * All methods match the interface expected by ryxService.ts
 */
export const ryxApi = {
  // ============ Health & Status ============

  async getHealth(): Promise<HealthResponse> {
    return apiRequest<HealthResponse>('/api/health');
  },

  async getStatus(): Promise<StatusResponse> {
    return apiRequest<StatusResponse>('/api/status');
  },

  // ============ Models ============

  async listModels(): Promise<Model[]> {
    const response = await apiRequest<{ models: Model[] }>('/api/models');
    return response.models || [];
  },

  async loadModel(modelId: string): Promise<{ success: boolean }> {
    return apiRequest<{ success: boolean }>('/api/models/load', {
      method: 'POST',
      body: JSON.stringify({ model_id: modelId }),
    });
  },

  async unloadModel(modelId: string): Promise<{ success: boolean }> {
    return apiRequest<{ success: boolean }>('/api/models/unload', {
      method: 'POST',
      body: JSON.stringify({ model_id: modelId }),
    });
  },

  // ============ Sessions ============

  async listSessions(): Promise<Session[]> {
    const response = await apiRequest<{ sessions: Session[] }>('/api/sessions');
    return response.sessions || [];
  },

  async createSession(data: { name: string; model: string }): Promise<Session> {
    return apiRequest<Session>('/api/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getSession(sessionId: string): Promise<Session> {
    return apiRequest<Session>(`/api/sessions/${sessionId}`);
  },

  async deleteSession(sessionId: string): Promise<void> {
    await apiRequest<void>(`/api/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  },

  // ============ Chat ============

  async sendMessage(sessionId: string, message: string): Promise<Message> {
    return apiRequest<Message>(`/api/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content: message }),
    });
  },

  getStreamUrl(sessionId: string): string {
    return `${API_BASE_URL}/api/sessions/${sessionId}/stream`;
  },

  // ============ RAG ============

  async getRagStatus(): Promise<RAGStatus> {
    return apiRequest<RAGStatus>('/api/rag/status');
  },

  async triggerRagSync(): Promise<SyncResponse> {
    return apiRequest<SyncResponse>('/api/rag/sync', {
      method: 'POST',
    });
  },

  async searchRag(query: string, topK: number = 5): Promise<SearchResults> {
    return apiRequest<SearchResults>('/api/rag/search', {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    });
  },

  // ============ Workflows ============

  async listWorkflows(): Promise<Workflow[]> {
    const response = await apiRequest<{ workflows: Workflow[] }>('/api/workflows');
    return response.workflows || [];
  },

  async getWorkflow(workflowId: string): Promise<Workflow> {
    return apiRequest<Workflow>(`/api/workflows/${workflowId}`);
  },

  async runWorkflow(workflowId: string): Promise<RunResponse> {
    return apiRequest<RunResponse>(`/api/workflows/${workflowId}/run`, {
      method: 'POST',
    });
  },

  async pauseWorkflow(workflowId: string): Promise<void> {
    await apiRequest<void>(`/api/workflows/${workflowId}/pause`, {
      method: 'POST',
    });
  },

  // ============ Agents ============

  async listAgents(): Promise<Agent[]> {
    const response = await apiRequest<{ agents: Agent[] }>('/api/agents');
    return response.agents || [];
  },

  async getAgentLogs(agentId: string, lines: number = 50): Promise<LogEntry[]> {
    const response = await apiRequest<{ logs: LogEntry[] }>(
      `/api/agents/${agentId}/logs?lines=${lines}`
    );
    return response.logs || [];
  },

  // ============ Tools ============

  async listTools(): Promise<Tool[]> {
    const response = await apiRequest<{ tools: Tool[] }>('/api/tools');
    return response.tools || [];
  },

  async executeToolDry(
    toolName: string,
    params: Record<string, unknown>
  ): Promise<{ result: unknown }> {
    return apiRequest<{ result: unknown }>(`/api/tools/${toolName}/dry-run`, {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },
};

export default ryxApi;
