# Task 3.4: WebSocket Integration

**Time:** 60 min | **Priority:** HIGH | **Agent:** Copilot

## Objective

Implement WebSocket connection to the backend for real-time workflow event streaming, including message protocol handling, auto-reconnect on disconnect, and integration with all UI components.

## Output File(s)

- `ryx/interfaces/web/src/hooks/useWorkflowWebSocket.ts`
- `ryx/interfaces/web/src/components/WorkflowDashboard.tsx` (update)

## Dependencies

- Task 1.3: FastAPI WebSocket endpoint
- Task 3.1: WorkflowCanvas component
- Task 3.2: ExecutionMonitor component
- Task 3.3: ToolResults component

## Requirements

### WebSocket Connection

- URL: `ws://localhost:8000/api/workflow/stream`
- Auto-connect on component mount
- Auto-reconnect on disconnect (exponential backoff)
- Connection status indicator

### Message Protocol

**Client → Server:**
```json
{
  "action": "execute_workflow",
  "input": "user query",
  "model": "qwen2.5-coder:14b"  // optional
}
```

**Server → Client:**
```json
{
  "event": "step_start" | "step_complete" | "tool_call" | "tool_result" | "workflow_complete" | "error",
  "step": "input_reception",
  "node": "input",
  "message": "Processing input...",
  "latency": 123.45,
  "data": {}
}
```

### Features

1. WebSocket hook with state management
2. Connection status (connecting, connected, disconnected, error)
3. Auto-reconnect with exponential backoff
4. Message queue for offline messages
5. Real-time UI updates

### Reconnection Strategy

- Initial delay: 1 second
- Max delay: 30 seconds
- Backoff multiplier: 2x
- Max retries: 10

## Code Template

### useWorkflowWebSocket.ts

```typescript
import { useState, useEffect, useCallback, useRef } from 'react';

// =============================================================================
// Types
// =============================================================================

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface WorkflowEvent {
  event: string;
  step: string;
  node?: string;
  message: string;
  latency?: number;
  data?: Record<string, any>;
}

interface WorkflowMessage {
  action: 'execute_workflow' | 'cancel_workflow';
  input?: string;
  model?: string;
}

interface UseWorkflowWebSocketOptions {
  url?: string;
  autoConnect?: boolean;
  onEvent?: (event: WorkflowEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

interface UseWorkflowWebSocketReturn {
  status: ConnectionStatus;
  events: WorkflowEvent[];
  connect: () => void;
  disconnect: () => void;
  sendMessage: (message: WorkflowMessage) => void;
  executeWorkflow: (input: string, model?: string) => void;
  cancelWorkflow: () => void;
  clearEvents: () => void;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_URL = 'ws://localhost:8000/api/workflow/stream';
const INITIAL_RETRY_DELAY = 1000;
const MAX_RETRY_DELAY = 30000;
const MAX_RETRIES = 10;
const BACKOFF_MULTIPLIER = 2;

// =============================================================================
// Hook
// =============================================================================

export const useWorkflowWebSocket = (
  options: UseWorkflowWebSocketOptions = {}
): UseWorkflowWebSocketReturn => {
  const {
    url = DEFAULT_URL,
    autoConnect = true,
    onEvent,
    onConnect,
    onDisconnect,
    onError,
  } = options;
  
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const retryDelayRef = useRef(INITIAL_RETRY_DELAY);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const messageQueueRef = useRef<WorkflowMessage[]>([]);
  
  // Clear retry timeout
  const clearRetryTimeout = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
  }, []);
  
  // Reset retry state
  const resetRetryState = useCallback(() => {
    retryCountRef.current = 0;
    retryDelayRef.current = INITIAL_RETRY_DELAY;
    clearRetryTimeout();
  }, [clearRetryTimeout]);
  
  // Schedule reconnect
  const scheduleReconnect = useCallback(() => {
    if (retryCountRef.current >= MAX_RETRIES) {
      console.error('Max reconnection attempts reached');
      setStatus('error');
      return;
    }
    
    clearRetryTimeout();
    
    console.log(`Reconnecting in ${retryDelayRef.current}ms (attempt ${retryCountRef.current + 1}/${MAX_RETRIES})`);
    
    retryTimeoutRef.current = setTimeout(() => {
      retryCountRef.current += 1;
      retryDelayRef.current = Math.min(
        retryDelayRef.current * BACKOFF_MULTIPLIER,
        MAX_RETRY_DELAY
      );
      connect();
    }, retryDelayRef.current);
  }, [clearRetryTimeout]);
  
  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }
    
    setStatus('connecting');
    
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setStatus('connected');
        resetRetryState();
        onConnect?.();
        
        // Send queued messages
        while (messageQueueRef.current.length > 0) {
          const message = messageQueueRef.current.shift();
          if (message) {
            ws.send(JSON.stringify(message));
          }
        }
      };
      
      ws.onmessage = (event) => {
        try {
          const data: WorkflowEvent = JSON.parse(event.data);
          setEvents((prev) => [...prev, data]);
          onEvent?.(data);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setStatus('disconnected');
        wsRef.current = null;
        onDisconnect?.();
        scheduleReconnect();
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        onError?.(error);
      };
      
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setStatus('error');
      scheduleReconnect();
    }
  }, [url, onConnect, onDisconnect, onEvent, onError, resetRetryState, scheduleReconnect]);
  
  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    clearRetryTimeout();
    resetRetryState();
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setStatus('disconnected');
  }, [clearRetryTimeout, resetRetryState]);
  
  // Send message
  const sendMessage = useCallback((message: WorkflowMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      // Queue message for when connection is established
      messageQueueRef.current.push(message);
      
      // Try to connect if not already connecting
      if (status === 'disconnected' || status === 'error') {
        connect();
      }
    }
  }, [status, connect]);
  
  // Execute workflow helper
  const executeWorkflow = useCallback((input: string, model?: string) => {
    sendMessage({
      action: 'execute_workflow',
      input,
      model,
    });
  }, [sendMessage]);
  
  // Cancel workflow helper
  const cancelWorkflow = useCallback(() => {
    sendMessage({
      action: 'cancel_workflow',
    });
  }, [sendMessage]);
  
  // Clear events
  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);
  
  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    
    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);
  
  return {
    status,
    events,
    connect,
    disconnect,
    sendMessage,
    executeWorkflow,
    cancelWorkflow,
    clearEvents,
  };
};

export default useWorkflowWebSocket;
```

### Updated WorkflowDashboard.tsx

```typescript
'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { WorkflowCanvas } from './WorkflowCanvas';
import { ExecutionMonitor } from './ExecutionMonitor';
import { ToolResults } from './ToolResults';
import { useWorkflowWebSocket } from '../hooks/useWorkflowWebSocket';

// =============================================================================
// Types
// =============================================================================

interface WorkflowDashboardProps {
  className?: string;
}

// =============================================================================
// Dracula Theme
// =============================================================================

const DraculaColors = {
  background: '#282a36',
  currentLine: '#44475a',
  foreground: '#f8f8f2',
  comment: '#6272a4',
  cyan: '#8be9fd',
  green: '#50fa7b',
  orange: '#ffb86c',
  pink: '#ff79c6',
  purple: '#bd93f9',
  red: '#ff5555',
  yellow: '#f1fa8c',
};

// =============================================================================
// Status Badge Component
// =============================================================================

interface StatusBadgeProps {
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const statusConfig = {
    connecting: { color: DraculaColors.yellow, text: '● Connecting...' },
    connected: { color: DraculaColors.green, text: '● Connected' },
    disconnected: { color: DraculaColors.comment, text: '○ Disconnected' },
    error: { color: DraculaColors.red, text: '✗ Error' },
  };
  
  const config = statusConfig[status];
  
  return (
    <span className="text-xs px-2 py-1 rounded" style={{ color: config.color }}>
      {config.text}
    </span>
  );
};

// =============================================================================
// Main Component
// =============================================================================

export const WorkflowDashboard: React.FC<WorkflowDashboardProps> = ({
  className = '',
}) => {
  const [inputValue, setInputValue] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  
  const {
    status,
    events,
    executeWorkflow,
    cancelWorkflow,
    clearEvents,
  } = useWorkflowWebSocket({
    autoConnect: true,
  });
  
  // Convert events to workflow nodes
  const workflowNodes = useMemo(() => {
    const steps = [
      'input_reception',
      'intent_detection',
      'model_selection',
      'tool_selection',
      'tool_execution',
      'rag_context',
      'llm_response',
      'post_processing',
    ];
    
    return steps.map((step, index) => {
      const stepEvents = events.filter((e) => e.step === step);
      const lastEvent = stepEvents[stepEvents.length - 1];
      
      let nodeStatus: 'pending' | 'running' | 'success' | 'failed' = 'pending';
      if (lastEvent) {
        if (lastEvent.event.includes('complete')) nodeStatus = 'success';
        else if (lastEvent.event.includes('error')) nodeStatus = 'failed';
        else if (lastEvent.event.includes('start')) nodeStatus = 'running';
      }
      
      return {
        id: step,
        label: step.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
        type: 'process' as const,
        status: nodeStatus,
        latency: lastEvent?.latency,
        position: { x: 0, y: index * 100 },
      };
    });
  }, [events]);
  
  // Create edges between nodes
  const workflowEdges = useMemo(() => {
    const steps = workflowNodes.map((n) => n.id);
    return steps.slice(0, -1).map((source, index) => ({
      id: `${source}-${steps[index + 1]}`,
      source,
      target: steps[index + 1],
    }));
  }, [workflowNodes]);
  
  // Convert events to monitor format
  const monitorEvents = useMemo(() => {
    return events.map((e, index) => ({
      id: `${index}`,
      timestamp: new Date(),
      step: e.step,
      node: e.node,
      message: e.message,
      status: e.event.includes('error') ? 'error' as const :
              e.event.includes('complete') ? 'success' as const :
              e.event.includes('start') ? 'running' as const : 'info' as const,
      latency: e.latency,
    }));
  }, [events]);
  
  // Extract tool results
  const toolResults = useMemo(() => {
    return events
      .filter((e) => e.event === 'tool_result')
      .map((e) => ({
        id: e.node || 'unknown',
        toolName: e.node || 'unknown',
        status: e.data?.success ? 'success' as const : 'failed' as const,
        output: e.data?.output,
        error: e.data?.error,
        latency: e.latency,
      }));
  }, [events]);
  
  // Handle form submission
  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      executeWorkflow(inputValue, selectedModel || undefined);
      setInputValue('');
    }
  }, [inputValue, selectedModel, executeWorkflow]);
  
  const isRunning = events.some(
    (e) => e.event === 'workflow_start' && 
    !events.some((e2) => e2.event === 'workflow_complete' || e2.event === 'workflow_error')
  );
  
  return (
    <div 
      className={`flex flex-col h-screen ${className}`}
      style={{ backgroundColor: DraculaColors.background }}
    >
      {/* Header */}
      <header 
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ 
          backgroundColor: DraculaColors.currentLine,
          borderColor: DraculaColors.comment,
        }}
      >
        <h1 
          className="text-xl font-bold"
          style={{ color: DraculaColors.purple }}
        >
          🟣 Ryx AI
        </h1>
        <StatusBadge status={status} />
      </header>
      
      {/* Input Form */}
      <form 
        onSubmit={handleSubmit}
        className="px-4 py-3 border-b flex gap-2"
        style={{ borderColor: DraculaColors.comment }}
      >
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Enter your query..."
          className="flex-1 px-4 py-2 rounded border focus:outline-none focus:ring-2"
          style={{
            backgroundColor: DraculaColors.background,
            borderColor: DraculaColors.comment,
            color: DraculaColors.foreground,
          }}
          disabled={status !== 'connected'}
        />
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          className="px-3 py-2 rounded border"
          style={{
            backgroundColor: DraculaColors.background,
            borderColor: DraculaColors.comment,
            color: DraculaColors.foreground,
          }}
        >
          <option value="">Auto</option>
          <option value="qwen2.5:3b">qwen2.5:3b (fast)</option>
          <option value="qwen2.5-coder:14b">qwen2.5-coder:14b (code)</option>
          <option value="mistral:7b">mistral:7b (shell)</option>
        </select>
        <button
          type="submit"
          disabled={status !== 'connected' || !inputValue.trim()}
          className="px-4 py-2 rounded font-medium hover:opacity-80 transition-opacity disabled:opacity-50"
          style={{
            backgroundColor: DraculaColors.green,
            color: DraculaColors.background,
          }}
        >
          Execute
        </button>
        {isRunning && (
          <button
            type="button"
            onClick={cancelWorkflow}
            className="px-4 py-2 rounded font-medium hover:opacity-80 transition-opacity"
            style={{
              backgroundColor: DraculaColors.red,
              color: DraculaColors.foreground,
            }}
          >
            Cancel
          </button>
        )}
      </form>
      
      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Workflow Canvas */}
        <div className="w-1/2 border-r" style={{ borderColor: DraculaColors.comment }}>
          <WorkflowCanvas
            nodes={workflowNodes}
            edges={workflowEdges}
          />
        </div>
        
        {/* Right Panel */}
        <div className="w-1/2 flex flex-col">
          {/* Execution Monitor */}
          <div className="flex-1 overflow-hidden">
            <ExecutionMonitor
              events={monitorEvents}
              onClear={clearEvents}
            />
          </div>
          
          {/* Tool Results */}
          <div 
            className="h-1/3 border-t p-4 overflow-auto"
            style={{ borderColor: DraculaColors.comment }}
          >
            <ToolResults results={toolResults} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default WorkflowDashboard;
```

## Acceptance Criteria

- [ ] WebSocket hook created with connection management
- [ ] Connection status tracking (connecting, connected, disconnected, error)
- [ ] Auto-connect on component mount
- [ ] Auto-reconnect with exponential backoff
- [ ] Message queue for offline messages
- [ ] `executeWorkflow()` helper function
- [ ] `cancelWorkflow()` helper function
- [ ] `clearEvents()` helper function
- [ ] WorkflowDashboard integrates all components
- [ ] Real-time workflow node status updates
- [ ] Real-time execution monitor events
- [ ] Real-time tool results display
- [ ] Input form for queries
- [ ] Model selection dropdown
- [ ] Connection status badge
- [ ] TypeScript types for all props and messages

## Notes

- WebSocket URL should be configurable via environment variable
- Message queue prevents lost messages during reconnection
- Exponential backoff prevents server overload during outages
- Events should be deduplicated by ID if server sends duplicates
