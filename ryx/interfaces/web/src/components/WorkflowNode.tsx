/**
 * @file ryx/interfaces/web/src/components/WorkflowNode.tsx
 * @description Custom React Flow node component for workflow visualization.
 * 
 * Presents node UI with:
 * - Title and icon based on node type
 * - Status indicator dot with color coding
 * - Latency badge showing execution time
 * - Small action button for node-specific actions
 * 
 * Uses Tailwind CSS classes and Dracula theme color variables.
 */

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

/** Possible node types in the workflow */
export type WorkflowNodeType = 'input' | 'process' | 'output' | 'tool' | 'model' | 'router' | 'condition';

/** Possible execution statuses for a node */
export type NodeExecutionStatus = 'pending' | 'running' | 'success' | 'failed';

/** Data structure for workflow node */
export interface WorkflowNodeData {
  /** Display label for the node */
  label: string;
  /** Node type determining visual appearance */
  type: WorkflowNodeType;
  /** Current execution status */
  status: NodeExecutionStatus;
  /** Execution time in milliseconds */
  latency?: number;
  /** Step number in the workflow (1-8) */
  step?: number;
  /** Additional description */
  description?: string;
  /** Callback when action button is clicked */
  onAction?: (nodeId: string) => void;
}

/** Props for standalone WorkflowNode usage */
export interface WorkflowNodeProps {
  /** Unique node identifier */
  id: string;
  /** Display label */
  label: string;
  /** Node type determining visual appearance */
  type: WorkflowNodeType;
  /** Current execution status */
  status: NodeExecutionStatus;
  /** Execution time in milliseconds */
  latency?: number;
  /** Step number in the workflow */
  step?: number;
  /** Whether the node is currently selected */
  isSelected?: boolean;
  /** Callback when node is selected */
  onSelect?: (id: string) => void;
  /** Callback when action button is clicked */
  onAction?: (id: string) => void;
}

// Status color mapping using Dracula theme colors
const statusColors: Record<NodeExecutionStatus, string> = {
  pending: 'border-[#f1fa8c]',
  running: 'border-[#8be9fd]',
  success: 'border-[#50fa7b]',
  failed: 'border-[#ff5555]',
};

// Status dot colors
const statusDotColors: Record<NodeExecutionStatus, string> = {
  pending: 'bg-[#f1fa8c]',
  running: 'bg-[#8be9fd]',
  success: 'bg-[#50fa7b]',
  failed: 'bg-[#ff5555]',
};

// Type icon mapping for visual distinction
const typeIcons: Record<WorkflowNodeType, string> = {
  input: '📥',
  process: '⚙️',
  output: '📤',
  tool: '🔧',
  model: '🤖',
  router: '🔀',
  condition: '❓',
};

/**
 * React Flow custom node component for workflow visualization
 * Used with React Flow's node types configuration
 */
export const WorkflowFlowNode: React.FC<NodeProps<WorkflowNodeData>> = memo(
  ({ id, data, selected }) => {
    const { label, type, status, latency, step, onAction } = data;

    return (
      <div
        className={`
          relative min-w-[180px] p-4 rounded-lg border-2
          bg-[#282a36] text-[#f8f8f2]
          transition-all duration-200 hover:shadow-lg
          ${statusColors[status]}
          ${status === 'running' ? 'animate-pulse shadow-[0_0_12px_rgba(139,233,253,0.4)]' : ''}
          ${selected ? 'ring-2 ring-[#bd93f9] ring-offset-2 ring-offset-[#282a36]' : ''}
        `}
        data-testid={`workflow-node-${id}`}
      >
        {/* Input Handle */}
        <Handle
          type="target"
          position={Position.Left}
          className="!bg-[#bd93f9] !border-2 !border-[#282a36] !w-3 !h-3"
        />

        {/* Status Dot */}
        <div className="absolute -top-2 -right-2">
          <span
            className={`
              inline-block w-4 h-4 rounded-full
              ${statusDotColors[status]}
              ${status === 'running' ? 'animate-ping' : ''}
            `}
            aria-label={`Status: ${status}`}
          />
        </div>

        {/* Header with Icon and Label */}
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xl" role="img" aria-label={type}>
            {typeIcons[type]}
          </span>
          <div className="flex-1 min-w-0">
            <span className="font-semibold text-[#f8f8f2] truncate block">{label}</span>
            {step !== undefined && (
              <span className="text-xs text-[#6272a4]">Step {step}</span>
            )}
          </div>
        </div>

        {/* Footer with Type and Latency */}
        <div className="flex items-center justify-between text-xs mt-2">
          <span className="text-[#6272a4] capitalize">{type}</span>
          {latency !== undefined && (
            <span className="bg-[#44475a] text-[#8be9fd] px-2 py-0.5 rounded-full font-mono">
              {latency}ms
            </span>
          )}
        </div>

        {/* Action Button */}
        {onAction && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onAction(id);
            }}
            className="
              absolute -bottom-2 left-1/2 -translate-x-1/2
              bg-[#ff79c6] text-[#282a36] text-xs
              px-2 py-0.5 rounded-full
              hover:bg-[#ff79c6]/80 transition-colors
              font-medium
            "
            aria-label={`Action for ${label}`}
          >
            ▶
          </button>
        )}

        {/* Output Handle */}
        <Handle
          type="source"
          position={Position.Right}
          className="!bg-[#bd93f9] !border-2 !border-[#282a36] !w-3 !h-3"
        />
      </div>
    );
  }
);

WorkflowFlowNode.displayName = 'WorkflowFlowNode';

/**
 * Standalone WorkflowNode component (non-React Flow)
 * For use outside of React Flow canvas
 */
export const WorkflowNode: React.FC<WorkflowNodeProps> = ({
  id,
  label,
  type,
  status,
  latency,
  step,
  isSelected = false,
  onSelect,
  onAction,
}) => {
  return (
    <div
      className={`
        p-4 rounded-lg border-2 cursor-pointer
        bg-[#282a36] text-[#f8f8f2]
        transition-all duration-200 hover:shadow-lg
        ${statusColors[status]}
        ${status === 'running' ? 'animate-pulse shadow-[0_0_12px_rgba(139,233,253,0.4)]' : ''}
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
      data-testid={`workflow-node-${id}`}
    >
      {/* Status Dot */}
      <div className="flex items-center gap-2 mb-1">
        <span
          className={`inline-block w-3 h-3 rounded-full ${statusDotColors[status]}`}
          aria-hidden="true"
        />
        <span className="text-lg">{typeIcons[type]}</span>
        <span className="font-medium text-[#f8f8f2]">{label}</span>
      </div>

      <div className="flex items-center justify-between text-xs">
        <span className="text-[#6272a4]">
          {type}
          {step !== undefined && ` • Step ${step}`}
        </span>
        <div className="flex items-center gap-2">
          {latency !== undefined && (
            <span className="bg-[#44475a] text-[#8be9fd] px-2 py-0.5 rounded-full">
              {latency}ms
            </span>
          )}
          {onAction && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAction(id);
              }}
              className="bg-[#ff79c6] text-[#282a36] px-2 py-0.5 rounded hover:bg-[#ff79c6]/80"
              aria-label={`Action for ${label}`}
            >
              ▶
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default WorkflowNode;
