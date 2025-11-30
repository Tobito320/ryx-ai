/**
 * @file ryx/interfaces/web/src/hooks/useWorkflowWebsocket.ts
 * @description WebSocket hook for workflow execution streaming.
 * 
 * Encapsulates WebSocket connection to ws://localhost:8000/api/workflow/stream
 * with automatic reconnection, event parsing, and React state management.
 * 
 * Features:
 * - Connect, reconnect with exponential backoff
 * - Send execute_workflow payloads
 * - Parse and emit WorkflowEvent objects
 * - Expose connection status
 */

import { useState, useEffect, useRef, useCallback } from 'react';

/** Event types emitted during workflow execution */
export type WorkflowEventType =
  | 'workflow_start'
  | 'workflow_complete'
  | 'workflow_failed'
  | 'node_start'
  | 'node_progress'
  | 'node_complete'
  | 'node_failed'
  | 'node_skipped'
  | 'edge_traversed';

/** Workflow event data structure matching backend schema */
export interface WorkflowEvent {
  /** Event type identifier */
  event: WorkflowEventType;
  /** Current step number (1-8 for typical workflow) */
  step: number;
  /** Node identifier */
  node: string;
  /** Human-readable event message */
  message: string;
  /** Latency in milliseconds */
  latency?: number;
  /** Additional event data */
  data?: Record<string, unknown>;
  /** Timestamp of the event */
  timestamp: string;
}

/** WebSocket connection status */
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'error';

/** Event callback function type */
export type WorkflowEventCallback = (event: WorkflowEvent) => void;

/** Hook configuration options */
export interface UseWorkflowWebsocketOptions {
  /** WebSocket URL (default: ws://localhost:8000/api/workflow/stream) */
  url?: string;
  /** Auto-connect on mount (default: true) */
  autoConnect?: boolean;
  /** Maximum reconnection attempts (default: 5) */
  maxReconnectAttempts?: number;
  /** Base delay for reconnection in ms (default: 1000) */
  reconnectBaseDelay?: number;
  /** Enable debug logging (default: false) */
  debug?: boolean;
}

/** Return type for the useWorkflowWebsocket hook */
export interface UseWorkflowWebsocketReturn {
  /** Current connection status */
  status: ConnectionStatus;
  /** Whether currently connected */
  isConnected: boolean;
  /** Last error message if any */
  error: string | null;
  /** Number of reconnection attempts */
  reconnectAttempts: number;
  /** Send execute workflow command */
  sendExecute: (input: string, model?: string) => void;
  /** Subscribe to workflow events */
  subscribe: (callback: WorkflowEventCallback) => () => void;
  /** Manually connect to WebSocket */
  connect: () => void;
  /** Manually disconnect from WebSocket */
  disconnect: () => void;
  /** Recent events (last 50) */
  events: WorkflowEvent[];
}

/**
 * React hook for managing WebSocket connection to workflow stream
 * 
 * @example
 * ```tsx
 * const { status, sendExecute, subscribe, events } = useWorkflowWebsocket();
 * 
 * useEffect(() => {
 *   return subscribe((event) => {
 *     console.log('Workflow event:', event);
 *   });
 * }, [subscribe]);
 * 
 * const handleExecute = () => {
 *   sendExecute('Process this text', 'gpt-4');
 * };
 * ```
 */
export function useWorkflowWebsocket(
  options: UseWorkflowWebsocketOptions = {}
): UseWorkflowWebsocketReturn {
  const {
    url = 'ws://localhost:8000/api/workflow/stream',
    autoConnect = true,
    maxReconnectAttempts = 5,
    reconnectBaseDelay = 1000,
    debug = false,
  } = options;

  // State
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<string | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const callbacksRef = useRef<Set<WorkflowEventCallback>>(new Set());
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isManualDisconnectRef = useRef(false);

  // Debug logger
  const log = useCallback(
    (...args: unknown[]) => {
      if (debug) {
        console.log('[WorkflowWebsocket]', ...args);
      }
    },
    [debug]
  );

  // Emit event to all subscribers
  const emitEvent = useCallback((event: WorkflowEvent) => {
    callbacksRef.current.forEach((callback) => {
      try {
        callback(event);
      } catch (err) {
        console.error('Error in workflow event callback:', err);
      }
    });

    // Store event in state (limit to 50)
    setEvents((prev) => {
      const newEvents = [...prev, event];
      return newEvents.slice(-50);
    });
  }, []);

  // Parse incoming WebSocket message
  const parseMessage = useCallback(
    (data: string): WorkflowEvent | null => {
      try {
        const parsed = JSON.parse(data);

        // Map backend format to WorkflowEvent
        const event: WorkflowEvent = {
          event: parsed.event_type || parsed.event || 'node_progress',
          step: parsed.step || 0,
          node: parsed.node_id || parsed.node || '',
          message: parsed.data?.message || parsed.message || '',
          latency: parsed.data?.execution_time_ms || parsed.latency,
          data: parsed.data,
          timestamp: parsed.timestamp || new Date().toISOString(),
        };

        return event;
      } catch (err) {
        log('Failed to parse message:', err, data);
        return null;
      }
    },
    [log]
  );

  // Connect to WebSocket
  const connect = useCallback(() => {
    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Clear any pending reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    isManualDisconnectRef.current = false;
    setStatus('connecting');
    setError(null);
    log('Connecting to', url);

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        log('Connected');
        setStatus('connected');
        setReconnectAttempts(0);
        setError(null);
      };

      ws.onmessage = (event) => {
        const workflowEvent = parseMessage(event.data);
        if (workflowEvent) {
          log('Event received:', workflowEvent);
          emitEvent(workflowEvent);
        }
      };

      ws.onerror = (event) => {
        log('WebSocket error:', event);
        setError('WebSocket connection error');
        setStatus('error');
      };

      ws.onclose = (event) => {
        log('Connection closed:', event.code, event.reason);
        wsRef.current = null;

        if (!isManualDisconnectRef.current && reconnectAttempts < maxReconnectAttempts) {
          // Schedule reconnection with exponential backoff
          const delay = reconnectBaseDelay * Math.pow(2, reconnectAttempts);
          log(`Scheduling reconnect in ${delay}ms (attempt ${reconnectAttempts + 1}/${maxReconnectAttempts})`);
          
          setStatus('reconnecting');
          setReconnectAttempts((prev) => prev + 1);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (reconnectAttempts >= maxReconnectAttempts) {
          setStatus('error');
          setError(`Failed to connect after ${maxReconnectAttempts} attempts`);
        } else {
          setStatus('disconnected');
        }
      };
    } catch (err) {
      log('Connection error:', err);
      setError(err instanceof Error ? err.message : 'Failed to create WebSocket');
      setStatus('error');
    }
  }, [url, maxReconnectAttempts, reconnectBaseDelay, reconnectAttempts, parseMessage, emitEvent, log]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    isManualDisconnectRef.current = true;
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }

    setStatus('disconnected');
    setReconnectAttempts(0);
    log('Disconnected');
  }, [log]);

  // Send execute workflow command
  const sendExecute = useCallback(
    (input: string, model?: string) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        console.warn('WebSocket not connected. Cannot send execute command.');
        return;
      }

      const payload = {
        type: 'execute_workflow',
        input,
        model: model || undefined,
        timestamp: new Date().toISOString(),
      };

      log('Sending execute:', payload);
      wsRef.current.send(JSON.stringify(payload));
    },
    [log]
  );

  // Subscribe to workflow events
  const subscribe = useCallback((callback: WorkflowEventCallback) => {
    callbacksRef.current.add(callback);

    // Return unsubscribe function
    return () => {
      callbacksRef.current.delete(callback);
    };
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoConnect]);

  return {
    status,
    isConnected: status === 'connected',
    error,
    reconnectAttempts,
    sendExecute,
    subscribe,
    connect,
    disconnect,
    events,
  };
}

export default useWorkflowWebsocket;
