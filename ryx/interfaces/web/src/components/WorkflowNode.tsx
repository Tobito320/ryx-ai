import React from 'react';

/**
 * Props for the WorkflowNode component
 */
interface WorkflowNodeProps {
  /** Unique node identifier */
  id: string;
  /** Display label */
  label: string;
  /** Node type determining visual appearance */
  type: 'input' | 'process' | 'output' | 'tool';
  /** Current execution status */
  status: 'pending' | 'running' | 'success' | 'failed';
  /** Execution time in milliseconds */
  latency?: number;
  /** Whether the node is currently selected */
  isSelected?: boolean;
  /** Callback when node is selected */
  onSelect?: (id: string) => void;
}

/**
 * WorkflowNode - A visual node component for workflow visualization
 * Uses Dracula theme colors for status indicators
 */
export const WorkflowNode: React.FC<WorkflowNodeProps> = ({
  id,
  label,
  type,
  status,
  latency,
  isSelected = false,
  onSelect,
}) => {
  // Status color mapping using Dracula theme colors
  const statusColors = {
    pending: 'border-[#f1fa8c]',      // Yellow
    running: 'border-[#8be9fd] animate-pulse', // Cyan with animation
    success: 'border-[#50fa7b]',      // Green
    failed: 'border-[#ff5555]',       // Red
  };

  // Type icon mapping for visual distinction
  const typeIcons = {
    input: '📥',
    process: '⚙️',
    output: '📤',
    tool: '🔧',
  };

  return (
    <div
      className={`
        p-4 rounded-lg border-2 cursor-pointer
        bg-[#282a36] text-[#f8f8f2]
        transition-all duration-200 hover:shadow-lg
        ${statusColors[status]}
        ${isSelected ? 'ring-2 ring-[#bd93f9]' : ''}
      `}
      onClick={() => onSelect?.(id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          onSelect?.(id);
        }
      }}
      aria-label={`Workflow node: ${label}, Type: ${type}, Status: ${status}`}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{typeIcons[type]}</span>
        <span className="font-medium text-[#f8f8f2]">{label}</span>
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-[#6272a4]">{type}</span>
        {latency !== undefined && (
          <span className="text-[#8be9fd]">{latency}ms</span>
        )}
      </div>
    </div>
  );
};

export default WorkflowNode;
