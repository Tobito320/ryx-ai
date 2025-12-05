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

// Simulated AI responses based on tools and context
const generateAIResponse = (message: string, enabledTools: string[] = ['websearch', 'rag', 'filesystem']): string => {
  const lowerMessage = message.toLowerCase();
  
  // Check for file attachments
  if (message.includes('[File:') || message.includes('[Image:')) {
    return `I've received and analyzed the attached files. Here's what I found:

**File Analysis:**
- Successfully parsed the content
- Identified key patterns and structures
- Cross-referenced with RAG knowledge base

${enabledTools.includes('rag') ? `\n**RAG Context:** Found 3 related documents in the knowledge base that may be relevant.` : ''}

Would you like me to:
1. Provide a detailed breakdown of the content
2. Compare with existing codebase patterns
3. Generate suggestions for improvements`;
  }
  
  // Code-related queries
  if (lowerMessage.includes('code') || lowerMessage.includes('function') || lowerMessage.includes('bug')) {
    return `I've analyzed your request. Here's my assessment:

**Code Analysis:**
\`\`\`python
# Example relevant code pattern
def example_function():
    # Implementation based on your query
    pass
\`\`\`

${enabledTools.includes('rag') ? '**RAG Search:** Found 5 relevant code examples in the indexed codebase.' : ''}
${enabledTools.includes('websearch') ? '**Web Search:** Found 3 recent Stack Overflow discussions on this topic.' : ''}

Would you like me to elaborate on any specific aspect?`;
  }
  
  // Search-related queries
  if (lowerMessage.includes('search') || lowerMessage.includes('find') || lowerMessage.includes('look')) {
    return `I've searched for relevant information:

${enabledTools.includes('websearch') ? `**Web Search Results:**
1. [Relevant Article] - Key insights about your query
2. [Documentation] - Official documentation reference
3. [Discussion] - Community discussion with solutions` : '**Note:** Web search is disabled.'}

${enabledTools.includes('rag') ? `**Knowledge Base:**
- Found 7 indexed documents matching your query
- Most relevant: "architecture.md" (0.94 similarity)` : ''}

Would you like me to dive deeper into any of these results?`;
  }
  
  // Default intelligent response
  return `I understand you're asking about "${message.slice(0, 50)}${message.length > 50 ? '...' : ''}"

Here's my analysis:

**Key Points:**
1. I've processed your query through the multi-agent pipeline
2. ${enabledTools.includes('rag') ? 'Checked the RAG knowledge base for relevant context' : 'RAG is disabled for this session'}
3. ${enabledTools.includes('websearch') ? 'Ready to search the web if needed' : 'Web search is disabled'}

**Recommendations:**
- Consider breaking down complex tasks into smaller steps
- I can help with code generation, analysis, or research
- Let me know if you'd like me to use specific tools

What would you like to explore further?`;
};

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

  async sendMessage(
    sessionId: string, 
    message: string, 
    model?: string,
    history?: Array<{ role: "user" | "assistant"; content: string }>,
    tools?: string[]
  ): Promise<Message> {
    await delay(400 + Math.random() * 600);

    const session = sessions.find((s) => s.id === sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }

    const usedModel = model || session.model;
    const latencyMs = 400 + Math.random() * 600;
    const completionTokens = 80 + Math.floor(Math.random() * 200);
    
    const aiMessage: Message = {
      id: `msg-${++messageIdCounter}`,
      role: 'assistant',
      content: generateAIResponse(message, tools || ['websearch', 'rag']),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      model: usedModel,
      latency_ms: latencyMs,
      tokens_per_second: (completionTokens / latencyMs) * 1000,
      prompt_tokens: 50 + Math.floor(Math.random() * 100),
      completion_tokens: completionTokens,
    };

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
