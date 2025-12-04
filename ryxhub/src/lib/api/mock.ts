/**
 * RyxHub Mock API
 *
 * Mock implementation that returns realistic data for development.
 * Uses the same interface as the live API client.
 */

import {
  mockSessions,
  mockModels,
  mockRAGStatus,
  mockWorkflowNodes,
  mockConnections,
} from '@/data/mockData';

import type {
  HealthResponse,
  StatusResponse,
  Model,
  Session,
  Message,
  RAGStatus,
  SyncResponse,
  SearchResults,
  Workflow,
  RunResponse,
  Agent,
  LogEntry,
  Tool,
} from './client';

// Simulate network delay
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Random delay between 100-500ms to simulate real network
const randomDelay = () => delay(100 + Math.random() * 400);

// In-memory state for mock data mutations
let sessions = [...mockSessions];
let messageIdCounter = 100;

/**
 * Mock API implementation
 */
export const mockApi = {
  // ============ Health & Status ============

  async getHealth(): Promise<HealthResponse> {
    await randomDelay();
    return {
      status: 'healthy',
      version: '1.0.0-dev',
      uptime: 3600 + Math.floor(Math.random() * 7200),
      vllm_status: 'online',
    };
  },

  async getStatus(): Promise<StatusResponse> {
    await randomDelay();
    return {
      models_loaded: mockModels.filter((m) => m.status === 'online').length,
      active_sessions: sessions.filter((s) => s.isActive).length,
      gpu_memory_used: 8.2 + Math.random() * 2,
      gpu_memory_total: 16.0,
      vllm_workers: 2,
    };
  },

  // ============ Models ============

  async listModels(): Promise<Model[]> {
    await randomDelay();
    return [...mockModels];
  },

  async loadModel(modelId: string): Promise<{ success: boolean; message?: string; status?: string }> {
    await delay(1500); // Simulate loading time
    const model = mockModels.find((m) => m.id === modelId);
    if (model) {
      if (model.status === 'online') {
        return { success: true, message: 'Model already loaded', status: 'connected' };
      }
      model.status = 'online';
      return { success: true, message: 'Model loaded successfully', status: 'connected' };
    }
    return { success: false, message: 'Model not found', status: 'not_found' };
  },

  async unloadModel(modelId: string): Promise<{ success: boolean; message?: string }> {
    await delay(500);
    const model = mockModels.find((m) => m.id === modelId);
    if (model) {
      model.status = 'offline';
      return { success: true, message: 'Model unloaded successfully' };
    }
    return { success: false, message: 'Model not found' };
  },

  async getModelStatus(modelId: string): Promise<{ id: string; status: string; loaded: boolean; message: string }> {
    await randomDelay();
    const model = mockModels.find((m) => m.id === modelId);
    if (model) {
      return {
        id: modelId,
        status: model.status,
        loaded: model.status === 'online',
        message: model.status === 'online' ? 'Model is loaded and ready' : 'Model is available but not loaded'
      };
    }
    return {
      id: modelId,
      status: 'not_found',
      loaded: false,
      message: 'Model not found'
    };
  },

  // ============ Sessions ============

  async listSessions(): Promise<Session[]> {
    await randomDelay();
    return sessions.map((s) => ({
      ...s,
      messages: [], // Don't return full messages in list
    }));
  },

  async createSession(data: { name: string; model: string }): Promise<Session> {
    await randomDelay();
    const newSession: Session = {
      id: `session-${Date.now()}`,
      name: data.name,
      model: data.model,
      lastMessage: '',
      timestamp: 'just now',
      isActive: true,
      messages: [],
      agentId: `agent-${Date.now()}`,
    };
    sessions.unshift(newSession);
    return newSession;
  },

  async getSession(sessionId: string): Promise<Session> {
    await randomDelay();
    const session = sessions.find((s) => s.id === sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }
    return { ...session };
  },

  async deleteSession(sessionId: string): Promise<void> {
    await randomDelay();
    sessions = sessions.filter((s) => s.id !== sessionId);
  },

  // ============ Chat ============

  async sendMessage(sessionId: string, message: string): Promise<Message> {
    await delay(800 + Math.random() * 1200); // Simulate LLM response time

    const session = sessions.find((s) => s.id === sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }

    // Add user message
    const userMessage: Message = {
      id: `msg-${++messageIdCounter}`,
      role: 'user',
      content: message,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    session.messages.push(userMessage);

    // Generate mock AI response
    const responses = [
      `I've analyzed your request. Here's what I found:\n\n**Key Points:**\n1. Your query relates to ${message.slice(0, 20)}...\n2. Based on the RAG index, I found 3 relevant documents\n3. Recommended next steps are outlined below\n\nWould you like me to elaborate on any of these points?`,
      `Great question! Let me help you with that.\n\nI've processed your input through the multi-agent pipeline and here are the results:\n\n- **Analysis Agent**: Identified key entities and relationships\n- **Research Agent**: Found supporting context from 5 documents\n- **Synthesis Agent**: Combined findings into actionable insights\n\nWhat aspect would you like to explore further?`,
      `I understand you're asking about "${message.slice(0, 30)}..."\n\nHere's my analysis:\n\n\`\`\`\nProcessing pipeline: completed\nConfidence: 0.94\nSources: 4 documents\n\`\`\`\n\nThe most relevant finding is that this relates to your existing workflow configuration. Should I make any adjustments?`,
    ];

    const aiMessage: Message = {
      id: `msg-${++messageIdCounter}`,
      role: 'assistant',
      content: responses[Math.floor(Math.random() * responses.length)],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      model: session.model,
    };
    session.messages.push(aiMessage);
    session.lastMessage = aiMessage.content.slice(0, 30) + '...';
    session.timestamp = 'just now';

    return aiMessage;
  },

  getStreamUrl(sessionId: string): string {
    return `mock://stream/${sessionId}`;
  },

  // ============ RAG ============

  async getRagStatus(): Promise<RAGStatus> {
    await randomDelay();
    return {
      ...mockRAGStatus,
      pending: Math.floor(Math.random() * 30),
    };
  },

  async triggerRagSync(): Promise<SyncResponse> {
    await delay(500);
    return {
      success: true,
      queued_files: 15 + Math.floor(Math.random() * 20),
    };
  },

  async searchRag(query: string, topK: number = 5): Promise<SearchResults> {
    await delay(300 + Math.random() * 500);
    return {
      results: Array.from({ length: Math.min(topK, 5) }, (_, i) => ({
        id: `doc-${i + 1}`,
        content: `Relevant content for "${query.slice(0, 20)}..." - Document ${i + 1} contains information about the topic you're searching for. This includes implementation details and best practices.`,
        score: 0.95 - i * 0.1,
        metadata: {
          source: `docs/topic-${i + 1}.md`,
          timestamp: new Date().toISOString(),
        },
      })),
      total: 47,
    };
  },

  // ============ Workflows ============

  async listWorkflows(): Promise<Workflow[]> {
    await randomDelay();
    return [
      {
        id: 'workflow-1',
        name: 'PR Review Workflow',
        status: 'running',
        lastRun: '2m ago',
      },
      {
        id: 'workflow-2',
        name: 'Code Analysis',
        status: 'idle',
        lastRun: '1h ago',
      },
      {
        id: 'workflow-3',
        name: 'Security Scan',
        status: 'idle',
        lastRun: '3h ago',
      },
    ];
  },

  async getWorkflow(workflowId: string): Promise<Workflow & { nodes: typeof mockWorkflowNodes; connections: typeof mockConnections }> {
    await randomDelay();
    return {
      id: workflowId,
      name: 'PR Review Workflow',
      status: 'running',
      lastRun: '2m ago',
      nodes: mockWorkflowNodes,
      connections: mockConnections,
    };
  },

  async runWorkflow(workflowId: string): Promise<RunResponse> {
    await delay(500);
    return {
      success: true,
      run_id: `run-${Date.now()}`,
    };
  },

  async pauseWorkflow(_workflowId: string): Promise<void> {
    await delay(300);
  },

  // ============ Agents ============

  async listAgents(): Promise<Agent[]> {
    await randomDelay();
    return [
      { id: 'agent-1', name: 'Code Analyzer', status: 'active', model: 'Qwen2.5-7B' },
      { id: 'agent-2', name: 'Research Agent', status: 'active', model: 'Llama-3.2-3B' },
      { id: 'agent-3', name: 'Security Scanner', status: 'idle', model: 'Qwen2.5-7B' },
      { id: 'agent-4', name: 'Doc Generator', status: 'idle', model: 'Llama-3.2-3B' },
    ];
  },

  async getAgentLogs(agentId: string, lines: number = 50): Promise<LogEntry[]> {
    await randomDelay();
    const baseLogs: LogEntry[] = [
      { time: '10:24:30', level: 'info', message: `Agent ${agentId} initialized` },
      { time: '10:24:31', level: 'info', message: 'Loading model from vLLM pool...' },
      { time: '10:24:32', level: 'success', message: 'Model loaded successfully' },
      { time: '10:24:33', level: 'info', message: 'Processing request...' },
      { time: '10:24:35', level: 'info', message: 'RAG context retrieved (5 documents)' },
      { time: '10:24:38', level: 'success', message: 'Response generated' },
    ];
    return baseLogs.slice(0, lines);
  },

  // ============ Tools ============

  async listTools(): Promise<Tool[]> {
    await randomDelay();
    return [
      {
        id: 'tool-rag-search',
        name: 'RAG Search',
        description: 'Search the knowledge base',
        parameters: { query: 'string', top_k: 'number' },
      },
      {
        id: 'tool-web-search',
        name: 'Web Search',
        description: 'Search the web for information',
        parameters: { query: 'string' },
      },
      {
        id: 'tool-code-exec',
        name: 'Code Executor',
        description: 'Execute code in a sandbox',
        parameters: { language: 'string', code: 'string' },
      },
      {
        id: 'tool-file-ops',
        name: 'File Operations',
        description: 'Read and write files',
        parameters: { operation: 'string', path: 'string' },
      },
    ];
  },

  async executeToolDry(
    toolName: string,
    params: Record<string, unknown>
  ): Promise<{ result: unknown }> {
    await delay(500);
    return {
      result: {
        tool: toolName,
        params,
        dry_run: true,
        would_execute: true,
        estimated_duration: '0.5s',
      },
    };
  },

  // ============ SearXNG ============

  async getSearxngStatus(): Promise<{ healthy: boolean; status: string; message: string }> {
    await randomDelay();
    return {
      healthy: true,
      status: 'online',
      message: 'SearXNG is online'
    };
  },

  async searxngSearch(query: string): Promise<{ results: Array<{ title: string; url: string; content: string }>; total: number }> {
    await delay(800); // Simulate search time
    return {
      results: [
        {
          title: `Search result for "${query}" - Wikipedia`,
          url: 'https://en.wikipedia.org/wiki/' + query.replace(/\s/g, '_'),
          content: `This is a comprehensive article about ${query}. It covers the history, key concepts, and applications...`
        },
        {
          title: `${query} - Documentation`,
          url: 'https://docs.example.com/' + query.toLowerCase(),
          content: `Official documentation for ${query}. Learn about the API, configuration, and best practices...`
        },
        {
          title: `Stack Overflow - Questions about ${query}`,
          url: 'https://stackoverflow.com/questions/tagged/' + query.toLowerCase(),
          content: `Find answers to common questions about ${query} from the developer community...`
        }
      ],
      total: 3
    };
  },
};

export default mockApi;
