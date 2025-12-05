/**
 * RyxHub Service Layer
 * 
 * Unified service that switches between mock and real API based on configuration.
 * When USE_MOCK_API is false, attempts to connect to vLLM first.
 * 
 * Usage:
 *   import { ryxService } from '@/services/ryxService';
 *   const models = await ryxService.listModels();
 * 
 * Configuration:
 *   Set VITE_USE_MOCK_API=true for mock mode (default in development)
 *   Set VITE_VLLM_API_URL=http://localhost:8000 for vLLM
 *   Set VITE_RYX_API_URL=http://localhost:8420 for Ryx backend
 */

import { ryxApi } from '@/lib/api/client';
import { mockApi } from '@/lib/api/mock';

// Determine whether to use mock API
const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API !== 'false';

// Log which mode we're in
if (import.meta.env.DEV) {
  console.log(`🔌 RyxHub API: ${USE_MOCK_API ? 'Mock Mode' : 'vLLM Mode'}`);
}

// Service interface - same methods as API client
export interface RyxService {
  // Health & Status
  getHealth: typeof ryxApi.getHealth;
  getStatus: typeof ryxApi.getStatus;
  
  // Models
  listModels: typeof ryxApi.listModels;
  loadModel: typeof ryxApi.loadModel;
  unloadModel: typeof ryxApi.unloadModel;
  getModelStatus: typeof ryxApi.getModelStatus;
  
  // Sessions
  listSessions: typeof ryxApi.listSessions;
  createSession: typeof ryxApi.createSession;
  getSession: typeof ryxApi.getSession;
  deleteSession: typeof ryxApi.deleteSession;
  updateSessionTools: typeof ryxApi.updateSessionTools;
  
  // Chat
  sendMessage: typeof ryxApi.sendMessage;
  getStreamUrl: typeof ryxApi.getStreamUrl;
  
  // RAG
  getRagStatus: typeof ryxApi.getRagStatus;
  triggerRagSync: typeof ryxApi.triggerRagSync;
  searchRag: typeof ryxApi.searchRag;
  
  // Workflows
  listWorkflows: typeof ryxApi.listWorkflows;
  getWorkflow: typeof ryxApi.getWorkflow;
  runWorkflow: typeof ryxApi.runWorkflow;
  pauseWorkflow: typeof ryxApi.pauseWorkflow;
  connectWorkflowStream: typeof ryxApi.connectWorkflowStream;
  connectWorkflowLogsStream: typeof ryxApi.connectWorkflowLogsStream;
  connectScrapingStream: typeof ryxApi.connectScrapingStream;
  
  // Agents
  listAgents: typeof ryxApi.listAgents;
  getAgentLogs: typeof ryxApi.getAgentLogs;
  
  // Tools
  listTools: typeof ryxApi.listTools;
  executeToolDry: typeof ryxApi.executeToolDry;
  
  // SearXNG
  getSearxngStatus: typeof ryxApi.getSearxngStatus;
  searxngSearch: typeof ryxApi.searxngSearch;
}

// Create the service with fallback logic
function createRyxService(): RyxService {
  if (USE_MOCK_API) {
    return {
      getHealth: () => mockApi.getHealth(),
      getStatus: () => mockApi.getStatus(),
      listModels: () => mockApi.listModels(),
      loadModel: (id: string) => mockApi.loadModel(id),
      unloadModel: (id: string) => mockApi.unloadModel(id),
      getModelStatus: (id: string) => mockApi.getModelStatus(id),
      listSessions: () => mockApi.listSessions(),
      createSession: (data: { name: string; model: string }) => mockApi.createSession(data),
      getSession: (id: string) => mockApi.getSession(id),
      deleteSession: (id: string) => mockApi.deleteSession(id),
      updateSessionTools: async (sessionId: string, toolId: string, enabled: boolean) => {
        // Mock implementation
        return { success: true, sessionId, tools: { [toolId]: enabled } };
      },
      sendMessage: (sessionId: string, message: string, model?: string, history?: Array<{ role: "user" | "assistant"; content: string }>, tools?: string[]) => 
        mockApi.sendMessage(sessionId, message, model, history, tools),
      getStreamUrl: (sessionId: string) => `mock://stream/${sessionId}`,
      getRagStatus: () => mockApi.getRagStatus(),
      triggerRagSync: () => mockApi.triggerRagSync(),
      searchRag: (query: string, topK?: number) => mockApi.searchRag(query, topK),
      listWorkflows: () => mockApi.listWorkflows(),
      getWorkflow: (id: string) => mockApi.getWorkflow(id),
      runWorkflow: (id: string) => mockApi.runWorkflow(id),
      pauseWorkflow: (id: string) => mockApi.pauseWorkflow(id),
      connectWorkflowStream: () => {
        // Mock WebSocket - returns a complete mock object
        const mockWs = {
          close: () => {},
          send: () => {},
          addEventListener: () => {},
          removeEventListener: () => {},
          dispatchEvent: () => false,
          onopen: null,
          onclose: null,
          onerror: null,
          onmessage: null,
          readyState: 1, // OPEN
          url: 'mock://workflow/stream',
          protocol: '',
          extensions: '',
          bufferedAmount: 0,
          binaryType: 'blob' as BinaryType,
          CONNECTING: 0,
          OPEN: 1,
          CLOSING: 2,
          CLOSED: 3,
        } as unknown as WebSocket;
        return mockWs;
      },
      connectWorkflowLogsStream: () => {
        const mockWs = {
          close: () => {},
          send: () => {},
          addEventListener: () => {},
          removeEventListener: () => {},
          dispatchEvent: () => false,
          onopen: null,
          onclose: null,
          onerror: null,
          onmessage: null,
          readyState: 1,
          url: 'mock://workflow/logs',
          protocol: '',
          extensions: '',
          bufferedAmount: 0,
          binaryType: 'blob' as BinaryType,
          CONNECTING: 0,
          OPEN: 1,
          CLOSING: 2,
          CLOSED: 3,
        } as unknown as WebSocket;
        return mockWs;
      },
      connectScrapingStream: () => {
        const mockWs = {
          close: () => {},
          send: () => {},
          addEventListener: () => {},
          removeEventListener: () => {},
          dispatchEvent: () => false,
          onopen: null,
          onclose: null,
          onerror: null,
          onmessage: null,
          readyState: 1,
          url: 'mock://scraping/stream',
          protocol: '',
          extensions: '',
          bufferedAmount: 0,
          binaryType: 'blob' as BinaryType,
          CONNECTING: 0,
          OPEN: 1,
          CLOSING: 2,
          CLOSED: 3,
        } as unknown as WebSocket;
        return mockWs;
      },
      listAgents: () => mockApi.listAgents(),
      getAgentLogs: (id: string, lines?: number) => mockApi.getAgentLogs(id, lines),
      listTools: () => mockApi.listTools(),
      executeToolDry: (name: string, params: Record<string, unknown>) => mockApi.executeToolDry(name, params),
      getSearxngStatus: () => mockApi.getSearxngStatus(),
      searxngSearch: (query: string) => mockApi.searxngSearch(query),
    };
  }
  
  // Use real API
  return ryxApi;
}

// Export singleton service
export const ryxService = createRyxService();

// Helper hooks for React Query integration
export const queryKeys = {
  health: ['health'] as const,
  status: ['status'] as const,
  models: ['models'] as const,
  sessions: ['sessions'] as const,
  session: (id: string) => ['session', id] as const,
  ragStatus: ['rag', 'status'] as const,
  workflows: ['workflows'] as const,
  workflow: (id: string) => ['workflow', id] as const,
  agents: ['agents'] as const,
  agentLogs: (id: string) => ['agent', id, 'logs'] as const,
  tools: ['tools'] as const,
};

export default ryxService;
