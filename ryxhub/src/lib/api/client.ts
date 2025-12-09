/**
 * RyxHub Live API Client
 *
 * HTTP client for communicating with Ollama and Ryx backend.
 * Handles all API calls with proper error handling, timeouts, and retries.
 */

// Get API URLs from environment
const API_BASE_URL = import.meta.env.VITE_RYX_API_URL || 'http://localhost:8420';

// Default timeout for API calls (60 seconds for LLM responses)
const DEFAULT_TIMEOUT = 60000;
const LLM_TIMEOUT = 120000; // 2 minutes for LLM calls

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
  ollama_status: 'online' | 'offline';
  searxng_status: 'online' | 'offline';
  models_available: number;
}

export interface StatusResponse {
  models_loaded: number;
  ollama_url: string;
  searxng_url: string;
}

export interface Model {
  id: string;
  name: string;
  status: 'loaded' | 'available';
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
  latency_ms?: number;
  tokens_per_second?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
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

// WebSocket message types
export interface WorkflowStatusEvent {
  type: 'workflow_status' | 'node_status' | 'connected' | 'pong';
  status?: 'running' | 'success' | 'error' | 'idle';
  nodeId?: string;
  runId?: string;
  timestamp?: string;
  error?: string;
}

export interface LogEvent {
  type: 'log' | 'connected';
  level?: 'info' | 'success' | 'warning' | 'error';
  message?: string;
  nodeId?: string;
  timestamp: string;
  runId?: string;
}

export interface ScrapingProgressEvent {
  type: 'scraping_progress' | 'connected';
  url?: string;
  status?: 'pending' | 'scraping' | 'success' | 'error';
  progress?: number;
  items?: Array<{
    type: string;
    content: string;
    selector: string;
    timestamp: string;
  }>;
  totalItems?: number;
  toolId?: string;
  timestamp: string;
  message?: string;
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
          'Cannot connect to Ryx backend. Is Ollama running?',
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
    const data = await apiRequest<{ models: any[] }>('/api/models');
    return data.models.map((m: any) => ({
      id: m.name,
      name: m.name,
      status: m.status as 'loaded' | 'available',
      provider: 'Ollama',
    }));
  },

  async loadModel(modelId: string): Promise<{ success: boolean; message?: string }> {
    const result = await apiRequest<{ message: string }>(`/api/models/${modelId}/load`, {
      method: 'POST',
    });
    // Save as last used model
    await this.saveLastModel(modelId);
    return result;
  },

  async unloadModel(modelId: string): Promise<{ success: boolean; message?: string }> {
    return apiRequest<{ message: string }>(`/api/models/${modelId}/unload`, {
      method: 'POST',
    });
  },

  async saveLastModel(modelId: string): Promise<void> {
    try {
      await apiRequest('/api/models/save-last', {
        method: 'POST',
        body: JSON.stringify({ model: modelId }),
      });
    } catch {
      // Silent fail - not critical
    }
  },

  async getLastModel(): Promise<string> {
    try {
      const data = await apiRequest<{ model: string }>('/api/models/last');
      return data.model;
    } catch {
      return 'qwen2.5:1.5b';
    }
  },

  async createSession(data: { name: string; model: string }): Promise<Session> {
    // Create session locally - no backend needed
    const session: Session = {
      id: `session-${Date.now()}`,
      name: data.name,
      model: data.model,
      lastMessage: '',
      timestamp: 'just now',
      isActive: true,
      messages: [],
      agentId: `agent-${Date.now()}`,
    };
    
    // Store in localStorage
    const stored = localStorage.getItem('ryxhub_sessions');
    const sessions = stored ? JSON.parse(stored) : [];
    sessions.unshift(session);
    localStorage.setItem('ryxhub_sessions', JSON.stringify(sessions));
    localStorage.setItem('ryxhub_selected_session', session.id);
    
    return session;
  },

  async getSession(sessionId: string): Promise<Session> {
    return apiRequest<Session>(`/api/sessions/${sessionId}`);
  },

  async deleteSession(sessionId: string): Promise<void> {
    await apiRequest<void>(`/api/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  },

  async updateSessionTools(
    sessionId: string,
    toolId: string,
    enabled: boolean
  ): Promise<{ success: boolean; sessionId: string; tools: Record<string, boolean> }> {
    try {
      return await apiRequest<{ success: boolean; sessionId: string; tools: Record<string, boolean> }>(
        `/api/sessions/${sessionId}/tools`,
        {
          method: 'PUT',
          body: JSON.stringify({ toolId, enabled }),
        }
      );
    } catch {
      return { success: true, sessionId, tools: { [toolId]: enabled } };
    }
  },

  // ============ Chat ============

  async sendMessage(
    sessionId: string,
    message: string,
    model?: string,
    history?: Array<{ role: "user" | "assistant"; content: string }>,
    tools?: string[],
    images?: string[],
    style?: string,
    systemPrompt?: string,
    memories?: string[]
  ): Promise<Message> {
    const modelToUse = model || 'qwen2.5-coder:7b';
    const needsWebSearch = tools?.includes('websearch');

    const payload: any = {
      message,
      model: modelToUse,
      use_search: needsWebSearch,
      style: style || 'normal',
      history: history || [],
    };

    if (images && images.length > 0) {
      payload.images = images;
    }
    
    if (systemPrompt) {
      payload.system_prompt = systemPrompt;
    }
    
    if (memories && memories.length > 0) {
      payload.memories = memories;
    }

    try {
      const response = await apiRequest<{ response: string; model: string; latency_ms: number }>(
        '/api/chat/smart',
        {
          method: 'POST',
          body: JSON.stringify(payload),
        },
        LLM_TIMEOUT
      );

      // Auto-save extracted memories
      if (response.extracted_memories && response.extracted_memories.length > 0) {
        const existingMemories = JSON.parse(localStorage.getItem('ryxhub_user_memories') || '[]');
        const newMemories = response.extracted_memories.filter(
          (m: string) => !existingMemories.some((e: string) => e.toLowerCase() === m.toLowerCase())
        );
        if (newMemories.length > 0) {
          localStorage.setItem('ryxhub_user_memories', JSON.stringify([...existingMemories, ...newMemories]));
          console.log('Auto-saved memories:', newMemories);
        }
      }

      return {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        model: response.model,
        latency_ms: response.latency_ms,
      };
    } catch (error) {
      if (error instanceof RyxApiError) throw error;
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new RyxApiError('Request timed out', undefined, 'TIMEOUT');
        }
        throw new RyxApiError(
          `Cannot connect to backend: ${error.message}`,
          undefined,
          'CONNECTION_FAILED'
        );
      }
      throw new RyxApiError('Unknown error occurred', undefined, 'UNKNOWN');
    }
  },

  // Helper to determine if a query needs web search
  shouldSearch(message: string): boolean {
    const searchKeywords = [
      'who is', 'what is', 'when did', 'where is', 'why did',
      'current', 'latest', 'recent', 'today', 'news',
      'president', 'weather', 'price', 'stock',
      'how to', 'search for', 'find', 'look up'
    ];
    const lowerMessage = message.toLowerCase();
    return searchKeywords.some(keyword => lowerMessage.includes(keyword));
  },

  // Extract search query from user message
  extractSearchQuery(message: string): string {
    // Remove common question words and clean up
    return message
      .replace(/^(what|who|when|where|why|how|is|are|was|were|does|did|can|could|would|should)\s+/i, '')
      .replace(/\?$/g, '')
      .trim()
      .slice(0, 200); // Limit query length
  },

  getStreamUrl(sessionId: string): string {
    return `${VLLM_API_URL}/v1/chat/completions`;
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

  // WebSocket connections for workflows
  connectWorkflowStream(
    runId: string,
    onMessage: (data: WorkflowStatusEvent) => void,
    onError?: (error: Event) => void
  ): WebSocket {
    const ws = new WebSocket(getWebSocketUrl(`/ws/workflows/${runId}`));

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WorkflowStatusEvent;
        onMessage(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      if (onError) onError(event);
    };

    return ws;
  },

  connectWorkflowLogsStream(
    runId: string,
    onLog: (log: LogEvent) => void,
    onError?: (error: Event) => void
  ): WebSocket {
    const ws = new WebSocket(getWebSocketUrl(`/ws/workflows/${runId}/logs`));

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as LogEvent;
        onLog(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      if (onError) onError(event);
    };

    return ws;
  },

  connectScrapingStream(
    toolId: string,
    onProgress: (progress: ScrapingProgressEvent) => void,
    onError?: (error: Event) => void
  ): WebSocket {
    const ws = new WebSocket(getWebSocketUrl(`/ws/scraping/${toolId}`));

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ScrapingProgressEvent;
        onProgress(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      if (onError) onError(event);
    };

    return ws;
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

  // ============ SearXNG ============

  async getSearxngStatus(): Promise<{ healthy: boolean; status: string; message: string }> {
    return apiRequest<{ healthy: boolean; status: string; message: string }>('/api/searxng/status');
  },

  async searxngSearch(query: string): Promise<{ results: Array<{ title: string; url: string; content: string }>; total: number }> {
    return apiRequest<{ results: Array<{ title: string; url: string; content: string }>; total: number }>('/api/searxng/search', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  },
};

/**
 * Helper function to convert HTTP URL to WebSocket URL
 */
function getWebSocketUrl(path: string): string {
  const wsUrl = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
  return `${wsUrl}${path}`;
}

export default ryxApi;
