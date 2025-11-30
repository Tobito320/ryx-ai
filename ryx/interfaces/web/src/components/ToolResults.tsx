/**
 * @file ryx/interfaces/web/src/components/ToolResults.tsx
 * @description Component for displaying tool execution results with streaming updates.
 * 
 * Features:
 * - Renders results for tools: search_local, search_web, edit_file, launch_app
 * - Tool-specific formatting (file list, URL cards, diff snippet, status message)
 * - Accepts streaming updates and appends results live
 * - Color-coded status indicators
 * 
 * Uses Dracula theme colors via Tailwind CSS.
 */

import React, { useEffect, useCallback, useRef } from 'react';
import { WorkflowEvent } from '../hooks/useWorkflowWebsocket';

/** Tool types supported by this component */
export type ToolType = 'search_local' | 'search_web' | 'edit_file' | 'launch_app' | 'unknown';

/** File result item for search_local tool */
export interface FileResult {
  path: string;
  name: string;
  type: 'file' | 'directory';
  size?: number;
  modified?: string;
  snippet?: string;
}

/** URL result item for search_web tool */
export interface UrlResult {
  url: string;
  title: string;
  snippet?: string;
  favicon?: string;
}

/** Diff snippet for edit_file tool */
export interface DiffResult {
  path: string;
  additions: number;
  deletions: number;
  diff: string;
}

/** App launch result */
export interface LaunchResult {
  appName: string;
  pid?: number;
  status: 'started' | 'running' | 'stopped' | 'failed';
  message?: string;
}

/** Generic tool result data structure */
export interface ToolResult {
  /** Unique result identifier */
  id: string;
  /** Name of the tool */
  toolName: ToolType;
  /** Execution status */
  status: 'pending' | 'running' | 'success' | 'failed';
  /** Tool output data (type depends on toolName) */
  output?: FileResult[] | UrlResult[] | DiffResult | LaunchResult | string;
  /** Error message on failure */
  error?: string;
  /** Execution latency in milliseconds */
  latency?: number;
  /** Timestamp of the result */
  timestamp?: Date;
  /** Whether this result is streaming/incomplete */
  streaming?: boolean;
}

/** Props for the ToolResults component */
export interface ToolResultsProps {
  /** Array of tool execution results */
  results?: ToolResult[];
  /** Subscribe function from useWorkflowWebsocket */
  subscribe?: (callback: (event: WorkflowEvent) => void) => () => void;
  /** Whether results are loading */
  isLoading?: boolean;
  /** Callback to retry a failed tool execution */
  onRetry?: (toolId: string) => void;
  /** Callback when result is clicked */
  onResultClick?: (result: ToolResult) => void;
  /** Custom class name */
  className?: string;
  /** Maximum results to display */
  maxResults?: number;
}

// Status color mapping using Dracula theme colors
const statusColors: Record<ToolResult['status'], string> = {
  pending: 'bg-[#f1fa8c]/20 border-[#f1fa8c]',
  running: 'bg-[#8be9fd]/20 border-[#8be9fd]',
  success: 'bg-[#50fa7b]/20 border-[#50fa7b]',
  failed: 'bg-[#ff5555]/20 border-[#ff5555]',
};

// Status text colors
const statusTextColors: Record<ToolResult['status'], string> = {
  pending: 'text-[#f1fa8c]',
  running: 'text-[#8be9fd]',
  success: 'text-[#50fa7b]',
  failed: 'text-[#ff5555]',
};

// Status labels
const statusLabels: Record<ToolResult['status'], string> = {
  pending: 'Pending',
  running: 'Running...',
  success: 'Success',
  failed: 'Failed',
};

// Tool icons
const toolIcons: Record<ToolType, string> = {
  search_local: '📁',
  search_web: '🌐',
  edit_file: '📝',
  launch_app: '🚀',
  unknown: '🔧',
};

// Tool display names
const toolNames: Record<ToolType, string> = {
  search_local: 'Local Search',
  search_web: 'Web Search',
  edit_file: 'File Editor',
  launch_app: 'App Launcher',
  unknown: 'Tool',
};

/** Render file search results */
const FileResultsView: React.FC<{ files: FileResult[] }> = ({ files }) => (
  <div className="space-y-2">
    {files.map((file, index) => (
      <div
        key={`${file.path}-${index}`}
        className="flex items-center gap-3 p-2 bg-[#282a36] rounded hover:bg-[#44475a] transition-colors"
      >
        <span className="text-lg">{file.type === 'directory' ? '📁' : '📄'}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-[#f8f8f2] font-mono truncate">{file.name}</p>
          <p className="text-xs text-[#6272a4] truncate">{file.path}</p>
          {file.snippet && (
            <p className="text-xs text-[#8be9fd] mt-1 truncate">{file.snippet}</p>
          )}
        </div>
        {file.size !== undefined && (
          <span className="text-xs text-[#6272a4]">
            {(file.size / 1024).toFixed(1)}KB
          </span>
        )}
      </div>
    ))}
  </div>
);

/** Render URL search results as cards */
const UrlResultsView: React.FC<{ urls: UrlResult[] }> = ({ urls }) => (
  <div className="space-y-3">
    {urls.map((url, index) => (
      <a
        key={`${url.url}-${index}`}
        href={url.url}
        target="_blank"
        rel="noopener noreferrer"
        className="block p-3 bg-[#282a36] rounded-lg hover:bg-[#44475a] transition-colors group"
      >
        <div className="flex items-start gap-3">
          {url.favicon ? (
            <img src={url.favicon} alt="" className="w-4 h-4 mt-1" />
          ) : (
            <span className="text-sm">🔗</span>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm text-[#8be9fd] font-medium group-hover:text-[#bd93f9] truncate">
              {url.title}
            </p>
            <p className="text-xs text-[#50fa7b] truncate">{url.url}</p>
            {url.snippet && (
              <p className="text-xs text-[#f8f8f2]/70 mt-1 line-clamp-2">
                {url.snippet}
              </p>
            )}
          </div>
        </div>
      </a>
    ))}
  </div>
);

/** Render diff result */
const DiffResultView: React.FC<{ diff: DiffResult }> = ({ diff }) => (
  <div className="space-y-2">
    <div className="flex items-center gap-4 text-sm">
      <span className="text-[#f8f8f2] font-mono">{diff.path}</span>
      <span className="text-[#50fa7b]">+{diff.additions}</span>
      <span className="text-[#ff5555]">-{diff.deletions}</span>
    </div>
    <pre className="text-xs font-mono p-3 bg-[#282a36] rounded overflow-x-auto whitespace-pre">
      {diff.diff.split('\n').map((line, i) => {
        let lineClass = 'text-[#f8f8f2]';
        if (line.startsWith('+')) lineClass = 'text-[#50fa7b] bg-[#50fa7b]/10';
        if (line.startsWith('-')) lineClass = 'text-[#ff5555] bg-[#ff5555]/10';
        if (line.startsWith('@@')) lineClass = 'text-[#8be9fd]';
        return (
          <div key={i} className={`${lineClass} px-1`}>
            {line}
          </div>
        );
      })}
    </pre>
  </div>
);

/** Render app launch result */
const LaunchResultView: React.FC<{ launch: LaunchResult }> = ({ launch }) => {
  const statusColor =
    launch.status === 'running' || launch.status === 'started'
      ? 'text-[#50fa7b]'
      : launch.status === 'failed'
      ? 'text-[#ff5555]'
      : 'text-[#6272a4]';

  return (
    <div className="flex items-center gap-4 p-3 bg-[#282a36] rounded">
      <span className="text-2xl">🚀</span>
      <div className="flex-1">
        <p className="text-[#f8f8f2] font-medium">{launch.appName}</p>
        <p className={`text-sm ${statusColor}`}>
          {launch.status.charAt(0).toUpperCase() + launch.status.slice(1)}
          {launch.pid && ` (PID: ${launch.pid})`}
        </p>
        {launch.message && (
          <p className="text-xs text-[#6272a4] mt-1">{launch.message}</p>
        )}
      </div>
    </div>
  );
};

/** Render generic string output */
const StringOutputView: React.FC<{ output: string }> = ({ output }) => (
  <pre className="text-sm text-[#f8f8f2] bg-[#282a36] p-3 rounded overflow-x-auto whitespace-pre-wrap font-mono">
    {output}
  </pre>
);

/**
 * ToolResults - Component for displaying tool execution results
 */
export const ToolResults: React.FC<ToolResultsProps> = ({
  results: externalResults,
  subscribe,
  isLoading = false,
  onRetry,
  onResultClick,
  className = '',
  maxResults = 20,
}) => {
  const [internalResults, setInternalResults] = React.useState<ToolResult[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Use external results if provided, otherwise use internal state
  const results = externalResults || internalResults;
  const displayedResults = results.slice(-maxResults);

  // Convert workflow event to tool result
  const eventToToolResult = useCallback((event: WorkflowEvent): ToolResult | null => {
    // Only process tool-related events
    if (!event.node?.includes('tool') && event.event !== 'node_complete') {
      return null;
    }

    const toolName = (event.data?.tool_name as ToolType) || 
                     (event.node?.replace('tool-', '') as ToolType) || 
                     'unknown';

    const status: ToolResult['status'] =
      event.event === 'node_complete' ? 'success' :
      event.event === 'node_failed' ? 'failed' :
      event.event === 'node_start' ? 'running' : 'pending';

    return {
      id: `${event.timestamp}-${event.node}-${Math.random().toString(36).substr(2, 9)}`,
      toolName,
      status,
      output: event.data?.output as ToolResult['output'],
      error: event.data?.error as string,
      latency: event.latency,
      timestamp: new Date(event.timestamp),
      streaming: event.event === 'node_progress',
    };
  }, []);

  // Handle workflow events
  const handleWorkflowEvent = useCallback((event: WorkflowEvent) => {
    const result = eventToToolResult(event);
    if (result) {
      setInternalResults((prev) => {
        // Update existing result or add new one
        const existingIndex = prev.findIndex(
          (r) => r.toolName === result.toolName && r.status === 'running'
        );
        if (existingIndex !== -1 && result.status !== 'running') {
          // Update existing running result
          const updated = [...prev];
          updated[existingIndex] = { ...updated[existingIndex], ...result };
          return updated;
        }
        return [...prev.slice(-(maxResults - 1)), result];
      });
    }
  }, [eventToToolResult, maxResults]);

  // Subscribe to workflow events
  useEffect(() => {
    if (subscribe) {
      const unsubscribe = subscribe(handleWorkflowEvent);
      return unsubscribe;
    }
  }, [subscribe, handleWorkflowEvent]);

  // Auto-scroll on new results
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [displayedResults]);

  // Render result output based on tool type
  const renderOutput = (result: ToolResult) => {
    if (result.error) {
      return (
        <pre className="text-sm text-[#ff5555] bg-[#44475a] p-3 rounded overflow-x-auto whitespace-pre-wrap font-mono">
          {result.error}
        </pre>
      );
    }

    if (!result.output) {
      return result.status === 'running' ? (
        <div className="flex items-center gap-2 text-[#8be9fd] animate-pulse">
          <span className="inline-block w-2 h-2 bg-[#8be9fd] rounded-full animate-ping" />
          Processing...
        </div>
      ) : null;
    }

    // Render based on output type
    if (typeof result.output === 'string') {
      return <StringOutputView output={result.output} />;
    }

    if (Array.isArray(result.output)) {
      // Check if it's file results or URL results
      if (result.output.length > 0) {
        if ('path' in result.output[0] && 'type' in result.output[0]) {
          return <FileResultsView files={result.output as FileResult[]} />;
        }
        if ('url' in result.output[0]) {
          return <UrlResultsView urls={result.output as UrlResult[]} />;
        }
      }
    }

    // Check for diff result
    if ('diff' in result.output && 'additions' in result.output) {
      return <DiffResultView diff={result.output as DiffResult} />;
    }

    // Check for launch result
    if ('appName' in result.output && 'status' in result.output) {
      return <LaunchResultView launch={result.output as LaunchResult} />;
    }

    // Fallback to JSON display
    return (
      <pre className="text-sm text-[#f8f8f2] bg-[#282a36] p-3 rounded overflow-x-auto whitespace-pre-wrap font-mono">
        {JSON.stringify(result.output, null, 2)}
      </pre>
    );
  };

  return (
    <div
      className={`flex flex-col h-full bg-[#282a36] rounded-lg border border-[#6272a4] ${className}`}
      data-testid="tool-results"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#6272a4]">
        <h3 className="text-[#f8f8f2] font-semibold flex items-center gap-2">
          <span className="text-[#ff79c6]">🔧</span>
          Tool Results
        </h3>
        <div className="flex items-center gap-2">
          {isLoading && (
            <span className="text-xs text-[#8be9fd] animate-pulse flex items-center gap-1">
              <span className="inline-block w-2 h-2 bg-[#8be9fd] rounded-full animate-ping" />
              Loading...
            </span>
          )}
          <span className="text-xs text-[#6272a4]">
            {displayedResults.length} results
          </span>
        </div>
      </div>

      {/* Results List */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 dracula-scrollbar"
      >
        {displayedResults.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-[#6272a4]">No tool results to display</p>
          </div>
        ) : (
          displayedResults.map((result) => (
            <div
              key={result.id}
              className={`p-4 rounded-lg border ${statusColors[result.status]} transition-colors cursor-pointer hover:opacity-90`}
              onClick={() => onResultClick?.(result)}
              data-testid={`tool-result-${result.id}`}
            >
              {/* Tool Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-xl">{toolIcons[result.toolName]}</span>
                  <span className="text-[#ff79c6] font-mono text-sm">
                    {toolNames[result.toolName]}
                  </span>
                  <span className={`text-xs px-2 py-1 rounded ${statusTextColors[result.status]}`}>
                    {statusLabels[result.status]}
                    {result.status === 'running' && (
                      <span className="inline-block ml-1 animate-pulse">●</span>
                    )}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {result.latency !== undefined && (
                    <span className="text-xs text-[#ffb86c] font-mono">
                      {result.latency}ms
                    </span>
                  )}
                  {result.streaming && (
                    <span className="text-xs text-[#8be9fd]">Streaming</span>
                  )}
                </div>
              </div>

              {/* Output Content */}
              <div className="mt-2">{renderOutput(result)}</div>

              {/* Retry Button for Failed Results */}
              {result.status === 'failed' && onRetry && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onRetry(result.id);
                  }}
                  className="mt-3 px-4 py-2 bg-[#ff79c6] text-[#282a36] rounded hover:bg-[#ff79c6]/80 transition-colors text-sm font-medium"
                >
                  Retry
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ToolResults;
