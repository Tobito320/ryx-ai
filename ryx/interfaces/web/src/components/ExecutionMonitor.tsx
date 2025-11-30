/**
 * @file ryx/interfaces/web/src/components/ExecutionMonitor.tsx
 * @description Live scrolling list of workflow execution events.
 * 
 * Features:
 * - Displays WorkflowEvent items with step, node name, status, and latency
 * - Color-coded based on event status
 * - Auto-scrolls to bottom on new events
 * - Limits display to 50 most recent events
 * - Integrates with useWorkflowWebsocket hook
 * 
 * Uses Dracula theme colors via Tailwind CSS.
 */

import React, { useEffect, useRef, useCallback } from 'react';
import { WorkflowEvent, WorkflowEventType } from '../hooks/useWorkflowWebsocket';

/**
 * Display-ready event format for the ExecutionMonitor
 */
export interface DisplayEvent {
  /** Unique event identifier */
  id: string;
  /** Event timestamp */
  timestamp: Date;
  /** Workflow step name or number */
  step: string;
  /** Associated node ID or name */
  node?: string;
  /** Event message */
  message: string;
  /** Event status type for coloring */
  status: 'info' | 'success' | 'warning' | 'error' | 'running';
  /** Event latency in milliseconds */
  latency?: number;
  /** Original event type */
  eventType?: WorkflowEventType;
}

/**
 * Props for the ExecutionMonitor component
 */
export interface ExecutionMonitorProps {
  /** Array of display events (alternative to subscription) */
  events?: DisplayEvent[];
  /** Subscribe function from useWorkflowWebsocket */
  subscribe?: (callback: (event: WorkflowEvent) => void) => () => void;
  /** Maximum number of events to display (default: 50) */
  maxEvents?: number;
  /** Whether to auto-scroll to the latest event (default: true) */
  autoScroll?: boolean;
  /** Callback when an event is clicked */
  onEventClick?: (event: DisplayEvent) => void;
  /** Custom class name */
  className?: string;
  /** Title for the monitor panel */
  title?: string;
}

// Map WorkflowEventType to display status
const eventTypeToStatus = (eventType: WorkflowEventType): DisplayEvent['status'] => {
  switch (eventType) {
    case 'workflow_start':
    case 'node_start':
      return 'running';
    case 'workflow_complete':
    case 'node_complete':
      return 'success';
    case 'workflow_failed':
    case 'node_failed':
      return 'error';
    case 'node_skipped':
      return 'warning';
    case 'edge_traversed':
    case 'node_progress':
    default:
      return 'info';
  }
};

// Simple counter for unique ID generation
let eventIdCounter = 0;

// Generate unique ID for events
const generateEventId = (event: WorkflowEvent): string => {
  eventIdCounter += 1;
  return `evt-${event.timestamp}-${event.node || event.step}-${eventIdCounter}`;
};

// Convert WorkflowEvent to DisplayEvent
const workflowEventToDisplay = (event: WorkflowEvent): DisplayEvent => ({
  id: generateEventId(event),
  timestamp: new Date(event.timestamp),
  step: event.step?.toString() || 'N/A',
  node: event.node,
  message: event.message,
  status: eventTypeToStatus(event.event),
  latency: event.latency,
  eventType: event.event,
});

// Status color mapping using Dracula theme colors
const statusColors: Record<DisplayEvent['status'], string> = {
  info: 'text-[#8be9fd]',      // Cyan
  success: 'text-[#50fa7b]',   // Green
  warning: 'text-[#f1fa8c]',   // Yellow
  error: 'text-[#ff5555]',     // Red
  running: 'text-[#bd93f9]',   // Purple
};

// Status background colors for badges
const statusBgColors: Record<DisplayEvent['status'], string> = {
  info: 'bg-[#8be9fd]/20',
  success: 'bg-[#50fa7b]/20',
  warning: 'bg-[#f1fa8c]/20',
  error: 'bg-[#ff5555]/20',
  running: 'bg-[#bd93f9]/20',
};

// Status icons
const statusIcons: Record<DisplayEvent['status'], string> = {
  info: 'ℹ️',
  success: '✅',
  warning: '⚠️',
  error: '❌',
  running: '🔄',
};

/**
 * ExecutionMonitor - A component for displaying live workflow execution events
 */
export const ExecutionMonitor: React.FC<ExecutionMonitorProps> = ({
  events: externalEvents,
  subscribe,
  maxEvents = 50,
  autoScroll = true,
  onEventClick,
  className = '',
  title = 'Execution Monitor',
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [internalEvents, setInternalEvents] = React.useState<DisplayEvent[]>([]);

  // Use external events if provided, otherwise use internal state
  const displayedEvents = (externalEvents || internalEvents).slice(-maxEvents);

  // Handle incoming workflow events
  const handleWorkflowEvent = useCallback((event: WorkflowEvent) => {
    const displayEvent = workflowEventToDisplay(event);
    setInternalEvents((prev) => [...prev.slice(-(maxEvents - 1)), displayEvent]);
  }, [maxEvents]);

  // Subscribe to workflow events
  useEffect(() => {
    if (subscribe) {
      const unsubscribe = subscribe(handleWorkflowEvent);
      return unsubscribe;
    }
  }, [subscribe, handleWorkflowEvent]);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (autoScroll && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [displayedEvents, autoScroll]);

  const formatTimestamp = (date: Date): string => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  const formatEventType = (eventType?: WorkflowEventType): string => {
    if (!eventType) return '';
    return eventType.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  };

  return (
    <div
      className={`flex flex-col h-full bg-[#282a36] rounded-lg border border-[#6272a4] ${className}`}
      data-testid="execution-monitor"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#6272a4]">
        <h3 className="text-[#f8f8f2] font-semibold flex items-center gap-2">
          <span className="text-[#bd93f9]">📊</span>
          {title}
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-xs text-[#6272a4]">
            {displayedEvents.length} / {maxEvents} events
          </span>
          {displayedEvents.some((e) => e.status === 'running') && (
            <span className="text-xs text-[#8be9fd] animate-pulse flex items-center gap-1">
              <span className="w-2 h-2 bg-[#8be9fd] rounded-full animate-ping" />
              Live
            </span>
          )}
        </div>
      </div>

      {/* Events List */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-2 dracula-scrollbar"
        role="log"
        aria-live="polite"
        aria-label="Workflow execution events"
      >
        {displayedEvents.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-[#6272a4]">No events to display</p>
          </div>
        ) : (
          displayedEvents.map((event) => (
            <div
              key={event.id}
              className={`
                flex items-start gap-3 p-3 rounded-lg
                bg-[#44475a] hover:bg-[#6272a4]/30
                transition-colors cursor-pointer
                ${event.status === 'running' ? 'ring-1 ring-[#bd93f9]' : ''}
              `}
              onClick={() => onEventClick?.(event)}
              role="listitem"
              data-testid={`event-${event.id}`}
            >
              {/* Status Icon */}
              <span
                className={`text-lg flex-shrink-0 ${event.status === 'running' ? 'animate-spin' : ''}`}
                role="img"
                aria-label={event.status}
              >
                {statusIcons[event.status]}
              </span>

              {/* Event Content */}
              <div className="flex-1 min-w-0">
                {/* Event Header */}
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  {/* Step Badge */}
                  <span className="text-xs bg-[#282a36] text-[#ffb86c] px-2 py-0.5 rounded font-mono">
                    [{event.step}]
                  </span>

                  {/* Node Name */}
                  {event.node && (
                    <span className={`font-medium ${statusColors[event.status]}`}>
                      {event.node}
                    </span>
                  )}

                  {/* Status Badge */}
                  {event.status === 'success' && (
                    <span className="text-[#50fa7b]">✓</span>
                  )}

                  {/* Latency Badge */}
                  {event.latency !== undefined && (
                    <span className="text-xs bg-[#44475a] text-[#8be9fd] px-2 py-0.5 rounded-full font-mono">
                      {event.latency}ms
                    </span>
                  )}
                </div>

                {/* Message */}
                <p className="text-sm text-[#f8f8f2] break-words">
                  {event.message}
                </p>

                {/* Footer with Timestamp and Event Type */}
                <div className="flex items-center gap-4 mt-2 text-xs text-[#6272a4]">
                  <span>{formatTimestamp(event.timestamp)}</span>
                  {event.eventType && (
                    <span className={`${statusBgColors[event.status]} px-2 py-0.5 rounded`}>
                      {formatEventType(event.eventType)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ExecutionMonitor;

// Re-export for backward compatibility
export type { WorkflowEvent } from '../hooks/useWorkflowWebsocket';
