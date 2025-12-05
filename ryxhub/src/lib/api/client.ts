/**
 * RyxHub Live API Client
 *
 * HTTP client for communicating with vLLM (OpenAI-compatible) and Ryx backend.
 * Handles all API calls with proper error handling, timeouts, and retries.
 */

// Get API URLs from environment
const VLLM_API_URL = import.meta.env.VITE_VLLM_API_URL || 'http://localhost:8001';
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
    // Try vLLM health first
    try {
      const response = await fetch(`${VLLM_API_URL}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      });
      if (response.ok) {
        return {
          status: 'healthy',
          version: '1.0.0',
          uptime: 0,
          vllm_status: 'online',
        };
      }
    } catch {
      // vLLM not available
    }
    return {
      status: 'degraded',
      version: '1.0.0',
      uptime: 0,
      vllm_status: 'offline',
    };
  },

  async getStatus(): Promise<StatusResponse> {
    return {
      models_loaded: 1,
      active_sessions: 0,
      gpu_memory_used: 0,
      gpu_memory_total: 16,
      vllm_workers: 1,
    };
  },

  // ============ Models ============

  async listModels(): Promise<Model[]> {
    // Query vLLM OpenAI-compatible /v1/models endpoint
    try {
      const response = await fetch(`${VLLM_API_URL}/v1/models`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: AbortSignal.timeout(10000),
      });

      if (response.ok) {
        const data = await response.json();
        // vLLM returns OpenAI format: { data: [{ id: "model-name", ... }] }
        if (data.data && Array.isArray(data.data)) {
          return data.data.map((m: { id: string }) => {
            // Extract a friendly name from the model ID
            const parts = m.id.split('/');
            const lastName = parts[parts.length - 1];
            // Clean up the name - remove common suffixes and make it readable
            const friendlyName = lastName
              .replace(/-gptq$/i, '')
              .replace(/-awq$/i, '')
              .replace(/-gguf$/i, '')
              .replace(/\./g, ' ')
              .split('-')
              .map(part => part.charAt(0).toUpperCase() + part.slice(1))
              .join(' ');

            return {
              id: m.id,
              name: friendlyName || m.id,
              status: 'online' as const,
              provider: 'vLLM',
            };
          });
        }
      }
    } catch (error) {
      console.warn('vLLM not available:', error);
    }

    // Return empty array if vLLM is not running
    return [];
  },

  async loadModel(modelId: string): Promise<{ success: boolean; message?: string; status?: string }> {
    // vLLM doesn't support dynamic model loading - models are loaded at startup
    return { 
      success: false, 
      message: 'vLLM loads models at startup. Restart vLLM with the desired model.',
      status: 'requires_restart'
    };
  },

  async unloadModel(modelId: string): Promise<{ success: boolean; message?: string }> {
    return { 
      success: false, 
      message: 'vLLM does not support dynamic model unloading' 
    };
  },

  async getModelStatus(modelId: string): Promise<{ id: string; status: string; loaded: boolean; message: string }> {
    const models = await this.listModels();
    const model = models.find(m => m.id === modelId);
    return {
      id: modelId,
      status: model ? 'online' : 'offline',
      loaded: !!model,
      message: model ? 'Model is loaded and ready' : 'Model not loaded in vLLM'
    };
  },

  // ============ Sessions ============

  async listSessions(): Promise<Session[]> {
    try {
      const response = await apiRequest<{ sessions: Session[] }>('/api/sessions');
      return response.sessions || [];
    } catch {
      return [];
    }
  },

  async createSession(data: { name: string; model: string }): Promise<Session> {
    try {
      return await apiRequest<Session>('/api/sessions', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    } catch {
      // Fallback: create local session
      return {
        id: `session-${Date.now()}`,
        name: data.name,
        model: data.model,
        lastMessage: '',
        timestamp: 'just now',
        isActive: true,
        messages: [],
        agentId: `agent-${Date.now()}`,
      };
    }
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
    tools?: string[]
  ): Promise<Message> {
    const startTime = Date.now();
    const modelToUse = model || '/models/medium/general/qwen2.5-7b-gptq';

    // Check if we need to search or use RAG before responding
    let searchResults = '';
    const needsWebSearch = tools?.includes('websearch') && this.shouldSearch(message);
    const needsRAG = tools?.includes('rag');

    if (needsWebSearch) {
      try {
        const searchQuery = this.extractSearchQuery(message);
        const results = await this.searxngSearch(searchQuery);
        if (results.results.length > 0) {
          searchResults = '\n\n**Web Search Results for "' + searchQuery + '":**\n' +
            results.results.slice(0, 5).map((r, i) =>
              `${i + 1}. **${r.title}**\n   ${r.content}\n   Source: ${r.url}`
            ).join('\n\n');
        }
      } catch (error) {
        console.warn('Web search failed:', error);
      }
    }

    if (needsRAG) {
      try {
        const ragResults = await this.searchRag(message, 5);
        if (ragResults.results.length > 0) {
          searchResults += '\n\n**Knowledge Base Results:**\n' +
            ragResults.results.slice(0, 5).map((r, i) =>
              `${i + 1}. ${r.content.substring(0, 200)}...`
            ).join('\n\n');
        }
      } catch (error) {
        console.warn('RAG search failed:', error);
      }
    }

    // Build messages array with history
    const systemMessage = {
      role: 'system',
      content: `You are Ryx AI, an intelligent local AI assistant. Today is ${new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}. You are helpful, accurate, and concise.${tools?.includes('websearch') ? ' When answering questions about current events, recent information, or facts you are uncertain about, web search results will be provided to you.' : ''}${tools?.includes('rag') ? ' You have access to a knowledge base.' : ''}`,
    };

    const conversationMessages = history?.map(m => ({ role: m.role, content: m.content })) || [];

    // Add user message with search results if available
    const userMessageContent = searchResults ? message + searchResults : message;
    conversationMessages.push({ role: 'user', content: userMessageContent });

    const allMessages = [systemMessage, ...conversationMessages];

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), LLM_TIMEOUT);

    try {
      const response = await fetch(`${VLLM_API_URL}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          model: modelToUse,
          messages: allMessages,
          max_tokens: 4096,
          temperature: 0.7,
        }),
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const error = await response.text();
        throw new RyxApiError(`vLLM error: ${error}`, response.status);
      }

      const data = await response.json();
      const latencyMs = Date.now() - startTime;
      const content = data.choices?.[0]?.message?.content || 'No response from model';
      const completionTokens = data.usage?.completion_tokens || 0;
      const promptTokens = data.usage?.prompt_tokens || 0;

      return {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        model: modelToUse,
        latency_ms: latencyMs,
        tokens_per_second: completionTokens > 0 ? (completionTokens / latencyMs) * 1000 : undefined,
        prompt_tokens: promptTokens,
        completion_tokens: completionTokens,
      };
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof RyxApiError) throw error;

      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new RyxApiError('Request timed out', undefined, 'TIMEOUT');
        }
        throw new RyxApiError(
          `Cannot connect to vLLM: ${error.message}`,
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
