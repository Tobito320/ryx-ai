import React from 'react';

/**
 * Represents a tool execution result
 */
export interface ToolResult {
  /** Unique result identifier */
  id: string;
  /** Name of the tool */
  toolName: string;
  /** Execution status */
  status: 'pending' | 'running' | 'success' | 'failed';
  /** Tool output on success */
  output?: string;
  /** Error message on failure */
  error?: string;
  /** Execution latency in milliseconds */
  latency?: number;
}

/**
 * Props for the ToolResults component
 */
interface ToolResultsProps {
  /** Array of tool execution results */
  results: ToolResult[];
  /** Whether results are loading */
  isLoading?: boolean;
  /** Callback to retry a failed tool execution */
  onRetry?: (toolId: string) => void;
}

/**
 * ToolResults - A component for displaying tool execution results
 * Uses Dracula theme colors for status indicators
 */
export const ToolResults: React.FC<ToolResultsProps> = ({
  results,
  isLoading = false,
  onRetry,
}) => {
  // Status color mapping using Dracula theme colors
  const statusColors = {
    pending: 'bg-[#f1fa8c]/20 border-[#f1fa8c]',   // Yellow
    running: 'bg-[#8be9fd]/20 border-[#8be9fd]',   // Cyan
    success: 'bg-[#50fa7b]/20 border-[#50fa7b]',   // Green
    failed: 'bg-[#ff5555]/20 border-[#ff5555]',    // Red
  };

  // Status text colors
  const statusTextColors = {
    pending: 'text-[#f1fa8c]',
    running: 'text-[#8be9fd]',
    success: 'text-[#50fa7b]',
    failed: 'text-[#ff5555]',
  };

  // Status labels
  const statusLabels = {
    pending: 'Pending',
    running: 'Running...',
    success: 'Success',
    failed: 'Failed',
  };

  return (
    <div className="flex flex-col h-full bg-[#282a36] rounded-lg border border-[#6272a4]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#6272a4]">
        <h3 className="text-[#f8f8f2] font-semibold">Tool Results</h3>
        {isLoading && (
          <span className="text-xs text-[#8be9fd] animate-pulse">Loading...</span>
        )}
      </div>

      {/* Results List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {results.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-[#6272a4]">No tool results to display</p>
          </div>
        ) : (
          results.map((result) => (
            <div
              key={result.id}
              className={`p-4 rounded-lg border ${statusColors[result.status]} transition-colors`}
            >
              {/* Tool Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-[#ff79c6] font-mono text-sm">
                    🔧 {result.toolName}
                  </span>
                  <span className={`text-xs px-2 py-1 rounded ${statusTextColors[result.status]}`}>
                    {statusLabels[result.status]}
                    {result.status === 'running' && (
                      <span className="inline-block ml-1 animate-pulse">●</span>
                    )}
                  </span>
                </div>
                {result.latency !== undefined && (
                  <span className="text-xs text-[#ffb86c]">{result.latency}ms</span>
                )}
              </div>

              {/* Output Content */}
              {result.output && (
                <div className="mt-2">
                  <pre className="text-sm text-[#f8f8f2] bg-[#44475a] p-3 rounded overflow-x-auto whitespace-pre-wrap font-mono">
                    {result.output}
                  </pre>
                </div>
              )}

              {/* Error Content */}
              {result.error && (
                <div className="mt-2">
                  <pre className="text-sm text-[#ff5555] bg-[#44475a] p-3 rounded overflow-x-auto whitespace-pre-wrap font-mono">
                    {result.error}
                  </pre>
                </div>
              )}

              {/* Retry Button for Failed Results */}
              {result.status === 'failed' && onRetry && (
                <button
                  onClick={() => onRetry(result.id)}
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
