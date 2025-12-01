/**
 * @file ryx/interfaces/web/src/components/ResultsPanel.tsx
 * @description Clean results panel for displaying workflow output.
 * 
 * Features:
 * - Clean, minimal output (no chat bubbles)
 * - Structured data display
 * - Dracula theme styling
 * - Support for different result types
 */

import React from 'react';

/**
 * Result item interface
 */
export interface ResultItem {
  id: string;
  type: 'text' | 'list' | 'code' | 'link' | 'error';
  title?: string;
  content: string;
  metadata?: Record<string, string | number>;
  timestamp?: Date;
}

/**
 * Props for the ResultsPanel component
 */
export interface ResultsPanelProps {
  /** Array of result items */
  results: ResultItem[];
  /** Whether results are loading */
  loading?: boolean;
  /** Title for the results panel */
  title?: string;
  /** Callback when a result is clicked */
  onResultClick?: (result: ResultItem) => void;
  /** Callback to clear results */
  onClear?: () => void;
  /** Custom class name */
  className?: string;
}

/**
 * ResultsPanel - A clean panel for displaying workflow results
 */
export const ResultsPanel: React.FC<ResultsPanelProps> = ({
  results,
  loading = false,
  title = 'Results',
  onResultClick,
  onClear,
  className = '',
}) => {
  const renderResult = (result: ResultItem) => {
    switch (result.type) {
      case 'text':
        return (
          <div className="text-[#f8f8f2] text-sm leading-relaxed whitespace-pre-wrap">
            {result.content}
          </div>
        );

      case 'list':
        return (
          <ul className="space-y-1">
            {result.content.split('\n').map((item, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-[#f8f8f2]">
                <span className="text-[#bd93f9]">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        );

      case 'code':
        return (
          <pre className="bg-[#21222c] rounded-lg p-4 overflow-x-auto text-sm font-mono">
            <code className="text-[#f8f8f2]">{result.content}</code>
          </pre>
        );

      case 'link':
        return (
          <a
            href={result.content}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#8be9fd] hover:text-[#bd93f9] underline text-sm"
          >
            {result.title || result.content}
          </a>
        );

      case 'error':
        return (
          <div className="flex items-start gap-2 text-[#ff5555] text-sm">
            <span>❌</span>
            <span>{result.content}</span>
          </div>
        );

      default:
        return (
          <div className="text-[#f8f8f2] text-sm">{result.content}</div>
        );
    }
  };

  return (
    <div
      className={`flex flex-col h-full bg-[#282a36] rounded-lg border border-[#6272a4] ${className}`}
      data-testid="results-panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#6272a4]">
        <h3 className="text-[#f8f8f2] font-semibold flex items-center gap-2">
          <span className="text-[#50fa7b]">📋</span>
          {title}
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-xs text-[#6272a4]">
            {results.length} result{results.length !== 1 ? 's' : ''}
          </span>
          {onClear && results.length > 0 && (
            <button
              onClick={onClear}
              className="text-xs text-[#ff5555] hover:text-[#ff5555]/80 transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Results List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 dracula-scrollbar">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex items-center gap-3 text-[#8be9fd]">
              <span className="animate-spin">⏳</span>
              <span>Processing...</span>
            </div>
          </div>
        ) : results.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-[#6272a4]">No results to display</p>
          </div>
        ) : (
          results.map((result) => (
            <div
              key={result.id}
              className={`p-4 rounded-lg bg-[#44475a] transition-colors ${
                onResultClick ? 'cursor-pointer hover:bg-[#6272a4]/30' : ''
              }`}
              onClick={() => onResultClick?.(result)}
              data-testid={`result-${result.id}`}
            >
              {/* Result Header */}
              {result.title && (
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-[#bd93f9] font-medium text-sm">
                    {result.title}
                  </h4>
                  {result.metadata?.latency_ms && (
                    <span className="text-xs bg-[#282a36] text-[#8be9fd] px-2 py-0.5 rounded-full font-mono">
                      {result.metadata.latency_ms}ms
                    </span>
                  )}
                </div>
              )}

              {/* Result Content */}
              {renderResult(result)}

              {/* Result Footer */}
              {result.timestamp && (
                <div className="mt-2 text-xs text-[#6272a4]">
                  {result.timestamp.toLocaleTimeString()}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ResultsPanel;
