# Task 3.3: Tool Results Panel Component

**Time:** 30 min | **Priority:** HIGH | **Agent:** Copilot

## Objective

Complete the `ToolResults` component with display formats for different tool types, loading states, error handling, and expandable result sections.

## Output File(s)

`ryx/interfaces/web/src/components/ToolResults.tsx`

## Dependencies

- Task 1.2: React component scaffolds

## Requirements

### Display Formats by Tool Type

| Tool Type | Display Format |
|-----------|----------------|
| read_file | Code block with syntax highlighting |
| search_local | File list with paths |
| search_web | Search results with titles and URLs |
| edit_file | Diff view (before/after) |
| create_file | Success message with path |
| launch_app | Terminal output |

### Features

1. Collapsible/expandable results
2. Loading spinner for pending results
3. Error display with red styling
4. Copy button for text output
5. Retry button for failed operations
6. Result count badge

### States

| Status | Display |
|--------|---------|
| pending | Loading spinner |
| running | Loading spinner with "Running..." |
| success | Green checkmark + formatted output |
| failed | Red X + error message |

## Code Template

```typescript
'use client';

import React, { useState, useCallback } from 'react';

// =============================================================================
// Types
// =============================================================================

type ToolStatus = 'pending' | 'running' | 'success' | 'failed';

interface ToolResult {
  id: string;
  toolName: string;
  status: ToolStatus;
  output?: string | string[] | Record<string, any>;
  error?: string;
  latency?: number;
}

interface ToolResultsProps {
  results: ToolResult[];
  isLoading?: boolean;
  onRetry?: (toolId: string) => void;
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
// Helper Components
// =============================================================================

const LoadingSpinner: React.FC<{ text?: string }> = ({ text = 'Loading...' }) => (
  <div className="flex items-center gap-2" style={{ color: DraculaColors.cyan }}>
    <svg
      className="animate-spin h-4 w-4"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
    <span className="text-sm">{text}</span>
  </div>
);

interface CodeBlockProps {
  code: string;
  language?: string;
  onCopy?: () => void;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ code, language, onCopy }) => {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    onCopy?.();
    setTimeout(() => setCopied(false), 2000);
  }, [code, onCopy]);
  
  return (
    <div className="relative rounded overflow-hidden">
      <div
        className="absolute top-2 right-2 flex items-center gap-2"
      >
        {language && (
          <span
            className="text-xs px-2 py-0.5 rounded"
            style={{ 
              backgroundColor: DraculaColors.currentLine,
              color: DraculaColors.comment,
            }}
          >
            {language}
          </span>
        )}
        <button
          onClick={handleCopy}
          className="text-xs px-2 py-0.5 rounded hover:opacity-80 transition-opacity"
          style={{ 
            backgroundColor: copied ? DraculaColors.green : DraculaColors.purple,
            color: DraculaColors.foreground,
          }}
        >
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <pre
        className="p-4 pt-10 overflow-x-auto text-sm"
        style={{
          backgroundColor: DraculaColors.background,
          color: DraculaColors.foreground,
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        }}
      >
        <code>{code}</code>
      </pre>
    </div>
  );
};

interface FileListProps {
  files: string[];
}

const FileList: React.FC<FileListProps> = ({ files }) => (
  <ul className="space-y-1">
    {files.map((file, index) => (
      <li
        key={index}
        className="flex items-center gap-2 px-2 py-1 rounded hover:bg-[#44475a]"
      >
        <span style={{ color: DraculaColors.yellow }}>📄</span>
        <span 
          className="text-sm font-mono"
          style={{ color: DraculaColors.foreground }}
        >
          {file}
        </span>
      </li>
    ))}
  </ul>
);

interface SearchResultDisplayProps {
  results: Array<{ title: string; url: string; snippet?: string }>;
}

const SearchResultDisplay: React.FC<SearchResultDisplayProps> = ({ results }) => (
  <ul className="space-y-3">
    {results.map((result, index) => (
      <li key={index} className="border-b border-[#44475a] pb-3 last:border-0">
        <a
          href={result.url}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:underline"
          style={{ color: DraculaColors.purple }}
        >
          {result.title}
        </a>
        <div 
          className="text-xs truncate"
          style={{ color: DraculaColors.cyan }}
        >
          {result.url}
        </div>
        {result.snippet && (
          <p 
            className="text-sm mt-1"
            style={{ color: DraculaColors.comment }}
          >
            {result.snippet}
          </p>
        )}
      </li>
    ))}
  </ul>
);

// =============================================================================
// Result Card Component
// =============================================================================

interface ResultCardProps {
  result: ToolResult;
  onRetry?: () => void;
}

const ResultCard: React.FC<ResultCardProps> = ({ result, onRetry }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  
  const statusIcons: Record<ToolStatus, { icon: string; color: string }> = {
    pending: { icon: '⏳', color: DraculaColors.yellow },
    running: { icon: '⏳', color: DraculaColors.cyan },
    success: { icon: '✓', color: DraculaColors.green },
    failed: { icon: '✗', color: DraculaColors.red },
  };
  
  const { icon, color } = statusIcons[result.status];
  
  const renderOutput = () => {
    if (result.status === 'pending' || result.status === 'running') {
      return <LoadingSpinner text={result.status === 'running' ? 'Running...' : 'Pending...'} />;
    }
    
    if (result.status === 'failed') {
      return (
        <div className="space-y-2">
          <div 
            className="text-sm p-3 rounded"
            style={{ 
              backgroundColor: `${DraculaColors.red}20`,
              color: DraculaColors.red,
            }}
          >
            {result.error || 'Unknown error'}
          </div>
          {onRetry && (
            <button
              onClick={onRetry}
              className="text-xs px-3 py-1 rounded hover:opacity-80 transition-opacity"
              style={{ 
                backgroundColor: DraculaColors.orange,
                color: DraculaColors.foreground,
              }}
            >
              ↻ Retry
            </button>
          )}
        </div>
      );
    }
    
    // Success - format based on tool type
    if (!result.output) return null;
    
    switch (result.toolName) {
      case 'read_file':
        return <CodeBlock code={String(result.output)} />;
      
      case 'search_local':
        return <FileList files={result.output as string[]} />;
      
      case 'search_web':
        return <SearchResultDisplay results={result.output as any[]} />;
      
      case 'edit_file':
      case 'create_file':
        return (
          <div 
            className="text-sm p-3 rounded"
            style={{ 
              backgroundColor: `${DraculaColors.green}20`,
              color: DraculaColors.green,
            }}
          >
            {String(result.output)}
          </div>
        );
      
      case 'launch_app':
        return <CodeBlock code={String(result.output)} language="terminal" />;
      
      default:
        // Generic display
        if (typeof result.output === 'string') {
          return <CodeBlock code={result.output} />;
        }
        return <CodeBlock code={JSON.stringify(result.output, null, 2)} language="json" />;
    }
  };
  
  return (
    <div
      className="rounded-lg border overflow-hidden"
      style={{ 
        backgroundColor: DraculaColors.background,
        borderColor: DraculaColors.comment,
      }}
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-[#44475a] transition-colors"
        style={{ backgroundColor: DraculaColors.currentLine }}
      >
        <div className="flex items-center gap-3">
          <span style={{ color }}>{icon}</span>
          <span 
            className="font-medium text-sm"
            style={{ color: DraculaColors.foreground }}
          >
            {result.toolName}
          </span>
          {result.latency !== undefined && (
            <span 
              className="text-xs"
              style={{ color: DraculaColors.comment }}
            >
              {result.latency.toFixed(1)}ms
            </span>
          )}
        </div>
        <span style={{ color: DraculaColors.comment }}>
          {isExpanded ? '▼' : '▶'}
        </span>
      </button>
      
      {/* Content */}
      {isExpanded && (
        <div className="p-4">
          {renderOutput()}
        </div>
      )}
    </div>
  );
};

// =============================================================================
// Main Component
// =============================================================================

export const ToolResults: React.FC<ToolResultsProps> = ({
  results,
  isLoading = false,
  onRetry,
}) => {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 
          className="font-medium"
          style={{ color: DraculaColors.foreground }}
        >
          Tool Results
        </h3>
        <span
          className="text-xs px-2 py-0.5 rounded"
          style={{ 
            backgroundColor: DraculaColors.currentLine,
            color: DraculaColors.comment,
          }}
        >
          {results.length} {results.length === 1 ? 'result' : 'results'}
        </span>
      </div>
      
      {/* Loading state */}
      {isLoading && results.length === 0 && (
        <div 
          className="flex items-center justify-center py-8"
          style={{ color: DraculaColors.comment }}
        >
          <LoadingSpinner text="Executing tools..." />
        </div>
      )}
      
      {/* Empty state */}
      {!isLoading && results.length === 0 && (
        <div 
          className="text-center py-8"
          style={{ color: DraculaColors.comment }}
        >
          No tool results yet
        </div>
      )}
      
      {/* Results */}
      <div className="space-y-3">
        {results.map((result) => (
          <ResultCard
            key={result.id}
            result={result}
            onRetry={onRetry ? () => onRetry(result.id) : undefined}
          />
        ))}
      </div>
    </div>
  );
};

export default ToolResults;
```

## Acceptance Criteria

- [ ] Display formats for each tool type:
  - [ ] read_file: Code block
  - [ ] search_local: File list
  - [ ] search_web: Search results with titles/URLs
  - [ ] edit_file: Success message
  - [ ] create_file: Success message
  - [ ] launch_app: Terminal output
- [ ] Loading spinner for pending/running states
- [ ] Error display with red styling
- [ ] Retry button for failed operations
- [ ] Collapsible/expandable result cards
- [ ] Copy button for code blocks
- [ ] Result count badge in header
- [ ] Dracula theme colors applied
- [ ] TypeScript types for all props
- [ ] Component exports as named export

## Notes

- Use monospace font for code blocks
- Search results should open links in new tab
- Copy button should show "Copied" feedback
- Expand/collapse state per result card
- Consider truncating very long outputs
