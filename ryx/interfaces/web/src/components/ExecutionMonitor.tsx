import React, { useEffect, useRef } from 'react';

/**
 * Represents a workflow execution event
 */
export interface WorkflowEvent {
  /** Unique event identifier */
  id: string;
  /** Event timestamp */
  timestamp: Date;
  /** Workflow step name */
  step: string;
  /** Associated node ID */
  node?: string;
  /** Event message */
  message: string;
  /** Event status type */
  status: 'info' | 'success' | 'warning' | 'error';
  /** Event latency in milliseconds */
  latency?: number;
}

/**
 * Props for the ExecutionMonitor component
 */
interface ExecutionMonitorProps {
  /** Array of workflow events */
  events: WorkflowEvent[];
  /** Maximum number of events to display (default: 50) */
  maxEvents?: number;
  /** Whether to auto-scroll to the latest event */
  autoScroll?: boolean;
}

/**
 * ExecutionMonitor - A component for displaying workflow execution events
 * Uses Dracula theme colors for status indicators
 */
export const ExecutionMonitor: React.FC<ExecutionMonitorProps> = ({
  events,
  maxEvents = 50,
  autoScroll = true,
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Status color mapping using Dracula theme colors
  const statusColors = {
    info: 'text-[#8be9fd]',     // Cyan
    success: 'text-[#50fa7b]',  // Green
    warning: 'text-[#f1fa8c]',  // Yellow
    error: 'text-[#ff5555]',    // Red
  };

  // Status icon mapping
  const statusIcons = {
    info: 'ℹ️',
    success: '✅',
    warning: '⚠️',
    error: '❌',
  };

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (autoScroll && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  // Limit displayed events
  const displayedEvents = events.slice(-maxEvents);

  const formatTimestamp = (date: Date): string => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  return (
    <div className="flex flex-col h-full bg-[#282a36] rounded-lg border border-[#6272a4]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#6272a4]">
        <h3 className="text-[#f8f8f2] font-semibold">Execution Monitor</h3>
        <span className="text-xs text-[#6272a4]">
          {displayedEvents.length} / {maxEvents} events
        </span>
      </div>

      {/* Events List */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-2"
      >
        {displayedEvents.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-[#6272a4]">No events to display</p>
          </div>
        ) : (
          displayedEvents.map((event) => (
            <div
              key={event.id}
              className="flex items-start gap-3 p-3 bg-[#44475a] rounded-lg hover:bg-[#6272a4]/30 transition-colors"
            >
              {/* Status Icon */}
              <span className="text-lg flex-shrink-0" role="img" aria-label={event.status}>
                {statusIcons[event.status]}
              </span>

              {/* Event Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`font-medium ${statusColors[event.status]}`}>
                    {event.step}
                  </span>
                  {event.node && (
                    <span className="text-xs text-[#bd93f9] bg-[#282a36] px-2 py-0.5 rounded">
                      {event.node}
                    </span>
                  )}
                </div>
                <p className="text-sm text-[#f8f8f2] break-words">{event.message}</p>
                <div className="flex items-center gap-4 mt-2 text-xs text-[#6272a4]">
                  <span>{formatTimestamp(event.timestamp)}</span>
                  {event.latency !== undefined && (
                    <span className="text-[#ffb86c]">{event.latency}ms</span>
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
