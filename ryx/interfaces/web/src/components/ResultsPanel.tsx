/**
 * @file ryx/interfaces/web/src/components/ResultsPanel.tsx
 * @description N8N-style results panel with card-based output display.
 */

import React, { useState, useCallback } from 'react';

export interface ResultItem {
  id: string;
  type: 'text' | 'list' | 'code' | 'link' | 'file' | 'error';
  title?: string;
  content: string;
  url?: string;
  metadata?: Record<string, string | number>;
  timestamp?: Date;
}

export interface ResultsPanelProps {
  results: ResultItem[];
  loading?: boolean;
  title?: string;
  onResultClick?: (result: ResultItem) => void;
  onClear?: () => void;
  className?: string;
}

const TYPE_LABELS: Record<ResultItem['type'], string> = {
  text: 'TEXT',
  list: 'LIST',
  code: 'CODE',
  link: 'LINK',
  file: 'FILE',
  error: 'ERROR',
};

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
      className="text-[10px] px-2 py-1 rounded"
      style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}
      title={copied ? 'Copied!' : 'Copy'}
    >
      {copied ? '✓' : 'Copy'}
    </button>
  );
};

export const ResultsPanel: React.FC<ResultsPanelProps> = ({
  results,
  loading = false,
  title = 'Results',
  onResultClick,
  onClear,
  className = '',
}) => {
  const renderContent = (result: ResultItem) => {
    switch (result.type) {
      case 'code':
        return <code>{result.content}</code>;
      case 'list':
        return (
          <ul style={{ margin: 0, paddingLeft: '16px' }}>
            {result.content.split('\n').filter(Boolean).map((item, idx) => (
              <li key={idx} style={{ marginBottom: '4px' }}>{item}</li>
            ))}
          </ul>
        );
      case 'link':
        return (
          <a
            href={result.url || result.content}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--status-running)', textDecoration: 'underline' }}
            onClick={(e) => e.stopPropagation()}
          >
            {result.title || result.content}
          </a>
        );
      case 'error':
        return <span style={{ color: 'var(--status-error)' }}>{result.content}</span>;
      default:
        return <span>{result.content}</span>;
    }
  };

  return (
    <div
      className={`flex flex-col h-full ${className}`}
      style={{ background: 'var(--bg-elevated)' }}
      data-testid="results-panel"
    >
      {/* Header */}
      <div className="panel-header">
        <h2>{title}</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            {results.length} items
          </span>
          {onClear && results.length > 0 && (
            <button
              onClick={onClear}
              style={{ fontSize: '11px', color: 'var(--status-error)' }}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <span style={{ color: 'var(--status-running)' }}>Processing...</span>
          </div>
        ) : results.length === 0 ? (
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            justifyContent: 'center', 
            height: '100%',
            color: 'var(--text-muted)'
          }}>
            <span style={{ fontSize: '24px', marginBottom: '8px', opacity: 0.5 }}>📋</span>
            <span style={{ fontSize: '12px' }}>No results yet</span>
          </div>
        ) : (
          results.map((result) => (
            <div
              key={result.id}
              className="result-card"
              onClick={() => onResultClick?.(result)}
              style={{ cursor: onResultClick ? 'pointer' : 'default' }}
            >
              {/* Type Label */}
              <div className="result-type" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span>{TYPE_LABELS[result.type]}</span>
                <CopyButton content={result.content} />
              </div>
              
              {/* Title if present */}
              {result.title && (
                <div style={{ fontWeight: 500, marginBottom: '6px', color: 'var(--text-primary)' }}>
                  {result.title}
                </div>
              )}
              
              {/* Content */}
              <div className="result-content">
                {renderContent(result)}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ResultsPanel;
