import React from 'react';

/**
 * Props for the WorkflowDashboard component
 */
interface WorkflowDashboardProps {
  /** Current workflow ID */
  workflowId?: string;
  /** Overall workflow status */
  status: 'idle' | 'running' | 'completed' | 'failed';
  /** Callback to start the workflow */
  onStart?: () => void;
  /** Callback to stop the workflow */
  onStop?: () => void;
  /** Callback to reset the workflow */
  onReset?: () => void;
}

/**
 * WorkflowDashboard - A dashboard component for workflow control
 * Uses Dracula theme colors for visual styling
 */
export const WorkflowDashboard: React.FC<WorkflowDashboardProps> = ({
  workflowId,
  status,
  onStart,
  onStop,
  onReset,
}) => {
  // Status color mapping using Dracula theme colors
  const statusColors = {
    idle: 'text-[#6272a4]',       // Gray/Comment
    running: 'text-[#8be9fd]',    // Cyan
    completed: 'text-[#50fa7b]',  // Green
    failed: 'text-[#ff5555]',     // Red
  };

  // Status badge colors
  const statusBadgeColors = {
    idle: 'bg-[#6272a4]/20 border-[#6272a4]',
    running: 'bg-[#8be9fd]/20 border-[#8be9fd]',
    completed: 'bg-[#50fa7b]/20 border-[#50fa7b]',
    failed: 'bg-[#ff5555]/20 border-[#ff5555]',
  };

  // Status labels
  const statusLabels = {
    idle: 'Idle',
    running: 'Running',
    completed: 'Completed',
    failed: 'Failed',
  };

  // Status icons
  const statusIcons = {
    idle: '⏸️',
    running: '▶️',
    completed: '✅',
    failed: '❌',
  };

  return (
    <div className="bg-[#282a36] rounded-lg border border-[#6272a4] p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-[#f8f8f2]">Workflow Dashboard</h2>
          {workflowId && (
            <p className="text-sm text-[#6272a4] mt-1">
              ID: <span className="text-[#bd93f9] font-mono">{workflowId}</span>
            </p>
          )}
        </div>

        {/* Status Badge */}
        <div
          className={`flex items-center gap-2 px-4 py-2 rounded-full border ${statusBadgeColors[status]}`}
        >
          <span role="img" aria-label={status}>
            {statusIcons[status]}
          </span>
          <span className={`font-medium ${statusColors[status]}`}>
            {statusLabels[status]}
            {status === 'running' && (
              <span className="inline-block ml-1 animate-pulse">●</span>
            )}
          </span>
        </div>
      </div>

      {/* Control Buttons */}
      <div className="flex items-center gap-4">
        {/* Start Button - shown when idle or failed */}
        {(status === 'idle' || status === 'failed') && (
          <button
            onClick={onStart}
            className="flex items-center gap-2 px-6 py-3 bg-[#50fa7b] text-[#282a36] rounded-lg hover:bg-[#50fa7b]/80 transition-colors font-semibold"
          >
            <span>▶️</span>
            <span>Start</span>
          </button>
        )}

        {/* Stop Button - shown when running */}
        {status === 'running' && (
          <button
            onClick={onStop}
            className="flex items-center gap-2 px-6 py-3 bg-[#ff5555] text-[#f8f8f2] rounded-lg hover:bg-[#ff5555]/80 transition-colors font-semibold"
          >
            <span>⏹️</span>
            <span>Stop</span>
          </button>
        )}

        {/* Reset Button - shown when completed or failed */}
        {(status === 'completed' || status === 'failed') && (
          <button
            onClick={onReset}
            className="flex items-center gap-2 px-6 py-3 bg-[#44475a] text-[#f8f8f2] rounded-lg hover:bg-[#6272a4] transition-colors font-semibold"
          >
            <span>🔄</span>
            <span>Reset</span>
          </button>
        )}
      </div>

      {/* Additional Info */}
      <div className="mt-6 pt-6 border-t border-[#6272a4]">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-[#6272a4]">Status:</span>
            <span className={statusColors[status]}>{statusLabels[status]}</span>
          </div>
          {workflowId && (
            <div className="flex items-center gap-2">
              <span className="text-[#6272a4]">Workflow:</span>
              <span className="text-[#bd93f9] font-mono">{workflowId}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WorkflowDashboard;
