# Task 3.2: Execution Monitor Component

**Time:** 45 min | **Priority:** HIGH | **Agent:** Copilot

## Objective

Complete the `ExecutionMonitor` component with live event stream display, formatted output showing step and status, auto-scroll behavior, and Dracula theme styling.

## Output File(s)

`ryx/interfaces/web/src/components/ExecutionMonitor.tsx`

## Dependencies

- Task 1.2: React component scaffolds

## Requirements

### Event Display Format

```
[step_name] node_name ✓ (latency_ms)
[step_name] node_name ✗ (error message)
[step_name] node_name ⋯ (in progress)
```

### Features

1. Live event stream display
2. Auto-scroll to latest event (toggleable)
3. Maximum 50 events displayed
4. Monospace font for log-like appearance
5. Status icons with color coding
6. Timestamp display (optional)
7. Clear button
8. Pause/resume toggle

### Status Indicators

| Status | Icon | Color (Dracula) |
|--------|------|-----------------|
| info | ℹ | Comment (#6272a4) |
| success | ✓ | Green (#50fa7b) |
| warning | ⚠ | Orange (#ffb86c) |
| error | ✗ | Red (#ff5555) |
| running | ⋯ | Cyan (#8be9fd) |

### Dracula Theme

- Background: #282a36
- Text: #f8f8f2
- Monospace font: JetBrains Mono, Fira Code, or system monospace

## Code Template

```typescript
'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';

// =============================================================================
// Types
// =============================================================================

type EventStatus = 'info' | 'success' | 'warning' | 'error' | 'running';

interface WorkflowEvent {
  id: string;
  timestamp: Date;
  step: string;
  node?: string;
  message: string;
  status: EventStatus;
  latency?: number;
}

interface ExecutionMonitorProps {
  events: WorkflowEvent[];
  maxEvents?: number;
  autoScroll?: boolean;
  showTimestamp?: boolean;
  onClear?: () => void;
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

const statusConfig: Record<EventStatus, { icon: string; color: string }> = {
  info: { icon: 'ℹ', color: DraculaColors.comment },
  success: { icon: '✓', color: DraculaColors.green },
  warning: { icon: '⚠', color: DraculaColors.orange },
  error: { icon: '✗', color: DraculaColors.red },
  running: { icon: '⋯', color: DraculaColors.cyan },
};

// =============================================================================
// Helper Components
// =============================================================================

interface EventLineProps {
  event: WorkflowEvent;
  showTimestamp: boolean;
}

const EventLine: React.FC<EventLineProps> = ({ event, showTimestamp }) => {
  const config = statusConfig[event.status];
  const timestamp = event.timestamp.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
  
  return (
    <div 
      className="py-1 px-2 hover:bg-[#44475a] transition-colors"
      style={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace" }}
    >
      {showTimestamp && (
        <span style={{ color: DraculaColors.comment }} className="mr-2">
          {timestamp}
        </span>
      )}
      <span style={{ color: DraculaColors.purple }}>
        [{event.step}]
      </span>
      {event.node && (
        <span style={{ color: DraculaColors.foreground }} className="ml-2">
          {event.node}
        </span>
      )}
      <span style={{ color: config.color }} className="ml-2">
        {config.icon}
      </span>
      {event.message && (
        <span style={{ color: DraculaColors.foreground }} className="ml-2">
          {event.message}
        </span>
      )}
      {event.latency !== undefined && (
        <span style={{ color: DraculaColors.cyan }} className="ml-2">
          ({event.latency.toFixed(1)}ms)
        </span>
      )}
    </div>
  );
};

// =============================================================================
// Main Component
// =============================================================================

export const ExecutionMonitor: React.FC<ExecutionMonitorProps> = ({
  events,
  maxEvents = 50,
  autoScroll: initialAutoScroll = true,
  showTimestamp = false,
  onClear,
}) => {
  const [autoScroll, setAutoScroll] = useState(initialAutoScroll);
  const [isPaused, setIsPaused] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  
  // Limit displayed events
  const displayedEvents = events.slice(-maxEvents);
  
  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (autoScroll && !isPaused && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [events, autoScroll, isPaused]);
  
  // Handle scroll to detect manual scrolling
  const handleScroll = useCallback(() => {
    if (!scrollContainerRef.current) return;
    
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    
    // If user scrolls up, disable auto-scroll
    if (!isAtBottom && autoScroll) {
      setAutoScroll(false);
    }
  }, [autoScroll]);
  
  // Resume auto-scroll
  const handleResumeAutoScroll = useCallback(() => {
    setAutoScroll(true);
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, []);
  
  // Toggle pause
  const togglePause = useCallback(() => {
    setIsPaused(!isPaused);
  }, [isPaused]);
  
  return (
    <div 
      className="flex flex-col h-full rounded-lg overflow-hidden border"
      style={{ 
        backgroundColor: DraculaColors.background,
        borderColor: DraculaColors.comment,
      }}
    >
      {/* Header */}
      <div 
        className="flex items-center justify-between px-3 py-2 border-b"
        style={{ 
          backgroundColor: DraculaColors.currentLine,
          borderColor: DraculaColors.comment,
        }}
      >
        <div className="flex items-center gap-2">
          <span 
            className="text-sm font-medium"
            style={{ color: DraculaColors.foreground }}
          >
            Execution Monitor
          </span>
          <span 
            className="text-xs px-2 py-0.5 rounded"
            style={{ 
              backgroundColor: DraculaColors.background,
              color: DraculaColors.comment,
            }}
          >
            {displayedEvents.length} events
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Pause/Resume button */}
          <button
            onClick={togglePause}
            className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity"
            style={{ 
              backgroundColor: isPaused ? DraculaColors.orange : DraculaColors.currentLine,
              color: DraculaColors.foreground,
            }}
          >
            {isPaused ? '▶ Resume' : '⏸ Pause'}
          </button>
          
          {/* Auto-scroll indicator */}
          {!autoScroll && (
            <button
              onClick={handleResumeAutoScroll}
              className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity"
              style={{ 
                backgroundColor: DraculaColors.purple,
                color: DraculaColors.foreground,
              }}
            >
              ↓ Auto-scroll
            </button>
          )}
          
          {/* Clear button */}
          {onClear && (
            <button
              onClick={onClear}
              className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity"
              style={{ 
                backgroundColor: DraculaColors.red,
                color: DraculaColors.foreground,
              }}
            >
              Clear
            </button>
          )}
        </div>
      </div>
      
      {/* Event list */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto text-sm"
        style={{ color: DraculaColors.foreground }}
      >
        {displayedEvents.length === 0 ? (
          <div 
            className="flex items-center justify-center h-full"
            style={{ color: DraculaColors.comment }}
          >
            No events yet. Start a workflow to see execution logs.
          </div>
        ) : (
          <div className="py-2">
            {displayedEvents.map((event) => (
              <EventLine
                key={event.id}
                event={event}
                showTimestamp={showTimestamp}
              />
            ))}
          </div>
        )}
      </div>
      
      {/* Footer with status */}
      <div 
        className="px-3 py-1 border-t text-xs"
        style={{ 
          backgroundColor: DraculaColors.currentLine,
          borderColor: DraculaColors.comment,
          color: DraculaColors.comment,
        }}
      >
        {isPaused ? (
          <span style={{ color: DraculaColors.orange }}>⏸ Paused</span>
        ) : autoScroll ? (
          <span style={{ color: DraculaColors.green }}>● Live</span>
        ) : (
          <span>Scrolled up - click "Auto-scroll" to resume</span>
        )}
      </div>
    </div>
  );
};

export default ExecutionMonitor;
```

## Acceptance Criteria

- [ ] Live event stream display working
- [ ] Event format: `[step] node ✓/✗/⋯ message (latency)`
- [ ] Auto-scroll to latest event
- [ ] Auto-scroll disabled when user scrolls up
- [ ] "Auto-scroll" button to resume
- [ ] Maximum 50 events displayed (configurable)
- [ ] Pause/Resume toggle button
- [ ] Clear button (optional callback)
- [ ] Monospace font (JetBrains Mono, Fira Code)
- [ ] Dracula theme colors applied
- [ ] Status icons colored correctly:
  - [ ] Info: Comment gray
  - [ ] Success: Green
  - [ ] Warning: Orange
  - [ ] Error: Red
  - [ ] Running: Cyan
- [ ] Optional timestamp display
- [ ] Hover effect on event lines
- [ ] TypeScript types for all props
- [ ] Component exports as named export

## Notes

- Use `useRef` for scroll container
- Use `useEffect` for auto-scroll behavior
- Detect manual scrolling to disable auto-scroll
- Event ID should be unique for React keys
- Consider using virtualization (react-window) for large event lists
