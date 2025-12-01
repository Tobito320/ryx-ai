/**
 * @file ryx/interfaces/web/src/components/ResultsPanel.tsx
 * @description Clean results panel for displaying workflow output.
 * 
 * Features:
 * - Clean, minimal output (no chat bubbles)
 * - Structured data display
 * - Copy button per result
 * - Icon per result type (link, file, code, etc.)
 * - Rich text support (bold, code, links)
 * - Dracula/Hyprland theme styling
 */

import React, { useState, useCallback } from 'react';

/**
 * Result item interface
 */
export interface ResultItem {
  id: string;
  type: 'text' | 'list' | 'code' | 'link' | 'file' | 'error';
  title?: string;
  content: string;
  url?: string;
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

// Result type icons
const RESULT_ICONS: Record<ResultItem['type'], string> = {
  text: '📝',
  list: '📋',
  code: '💻',
  link: '🔗',
  file: '📄',
  error: '⚠️',
};

/**
 * CopyButton - A button to copy content to clipboard
 */
const CopyButton: React.FC<{ content: string }> = ({ content }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [content]);

  return (
    <button
      onClick={handleCopy}
      className="p-1.5 text-xs bg-ryx-current-line text-ryx-text-muted hover:text-ryx-foreground rounded transition-colors"
      title={copied ? 'Copied!' : 'Copy to clipboard'}
      aria-label={copied ? 'Copied!' : 'Copy to clipboard'}
    >
      {copied ? '✓' : '📋'}
    </button>
  );
};

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
          <div className="text-ryx-foreground text-sm leading-relaxed whitespace-pre-wrap font-mono">
            {result.content}
          </div>
        );

      case 'list':
        return (
          <ul className="space-y-1.5">
            {result.content.split('\n').filter(Boolean).map((item, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-ryx-foreground font-mono">
                <span className="text-ryx-accent flex-shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        );

      case 'code':
        return (
          <pre className="bg-ryx-bg rounded-ryx p-3 overflow-x-auto text-sm font-mono">
            <code className="text-ryx-foreground">{result.content}</code>
          </pre>
        );

      case 'link':
        return (
          <a
            href={result.url || result.content}
            target="_blank"
            rel="noopener noreferrer"
            className="text-ryx-cyan hover:text-ryx-purple underline text-sm font-mono inline-flex items-center gap-2"
            onClick={(e) => e.stopPropagation()}
          >
            <span>🔗</span>
            <span className="truncate">{result.title || result.content}</span>
          </a>
        );

      case 'file':
        return (
          <div className="flex items-center gap-2 text-ryx-foreground text-sm font-mono">
            <span>📄</span>
            <span className="truncate">{result.content}</span>
          </div>
        );

      case 'error':
        return (
          <div className="flex items-start gap-2 text-ryx-error text-sm font-mono">
            <span className="flex-shrink-0">❌</span>
            <span>{result.content}</span>
          </div>
        );

      default:
        return (
          <div className="text-ryx-foreground text-sm font-mono">{result.content}</div>
        );
    }
  };

  return (
    <div
      className={`flex flex-col h-full bg-ryx-bg rounded-ryx-lg border border-ryx-border ${className}`}
      data-testid="results-panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-ryx-border">
        <h3 className="text-ryx-foreground font-semibold font-mono flex items-center gap-2">
          <span className="text-ryx-success">📋</span>
          {title}
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-xs text-ryx-text-muted font-mono">
            {results.length} result{results.length !== 1 ? 's' : ''}
          </span>
          {onClear && results.length > 0 && (
            <button
              onClick={onClear}
              className="text-xs text-ryx-error hover:text-ryx-error/80 transition-colors font-mono"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Results List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 ryx-scrollbar">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex items-center gap-3 text-ryx-cyan font-mono">
              <span className="animate-spin">⏳</span>
              <span>Processing...</span>
            </div>
          </div>
        ) : results.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <span className="text-4xl mb-4">📋</span>
            <p className="text-ryx-text-muted font-mono text-sm">No results to display</p>
            <p className="text-ryx-text-muted font-mono text-xs mt-1 opacity-70">
              Results will appear here after execution
            </p>
          </div>
        ) : (
          results.map((result) => (
            <div
              key={result.id}
              className={`p-3 rounded-ryx bg-ryx-current-line transition-colors ${
                onResultClick ? 'cursor-pointer hover:bg-ryx-bg-hover' : ''
              }`}
              onClick={() => onResultClick?.(result)}
              data-testid={`result-${result.id}`}
            >
              {/* Result Header */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm">{RESULT_ICONS[result.type]}</span>
                  {result.title && (
                    <h4 className="text-ryx-accent font-medium text-sm font-mono">
                      {result.title}
                    </h4>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {result.metadata?.latency_ms && (
                    <span className="text-xs bg-ryx-bg text-ryx-cyan px-2 py-0.5 rounded-full font-mono">
                      {result.metadata.latency_ms}ms
                    </span>
                  )}
                  <CopyButton content={result.content} />
                </div>
              </div>

              {/* Result Content */}
              {renderResult(result)}

              {/* Result Footer */}
              {result.timestamp && (
                <div className="mt-2 text-[10px] text-ryx-text-muted font-mono">
                  {result.timestamp.toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  })}
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
