/**
 * @file ryx/interfaces/web/src/components/LiveExecution.tsx
 * @description Live step-by-step execution panel for the center of RyxHub.
 * 
 * Features:
 * - Step-by-step progress visualization
 * - Real-time updates via WebSocket
 * - Status indicator (✓ done, → in progress, ⚠️ error)
 * - Latency badge (e.g. "120ms")
 * - Smooth fade-in animation per step
 * - Current step highlighted
 * - Scrolls to active step automatically
 */

import React, { useEffect, useRef } from 'react';
import { Step, StepData, StepStatus } from './Step';

/**
 * Props for the LiveExecution component
 */
export interface LiveExecutionProps {
  /** Array of execution steps */
  steps: StepData[];
  /** Title for the panel */
  title?: string;
  /** Whether execution is in progress */
  isExecuting?: boolean;
  /** Total execution latency */
  totalLatency?: number;
  /** Callback when a step is clicked */
  onStepClick?: (step: StepData) => void;
  /** Custom class name */
  className?: string;
}

/**
 * LiveExecution - The center panel showing real-time workflow execution
 */
export const LiveExecution: React.FC<LiveExecutionProps> = ({
  steps,
  title = 'Execution Live',
  isExecuting = false,
  totalLatency,
  onStepClick,
  className = '',
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const activeStepRef = useRef<HTMLDivElement>(null);

  // Find the current active step (running step)
  const activeStepIndex = steps.findIndex(s => s.status === 'running');

  // Auto-scroll to active step
  useEffect(() => {
    if (activeStepRef.current && scrollContainerRef.current) {
      activeStepRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
  }, [activeStepIndex, steps.length]);

  // Count steps by status
  const completedSteps = steps.filter(s => s.status === 'success').length;
  const failedSteps = steps.filter(s => s.status === 'error').length;
  const runningSteps = steps.filter(s => s.status === 'running').length;

  return (
    <div
      className={`flex flex-col h-full bg-ryx-bg rounded-ryx-lg border border-ryx-border ${className}`}
      data-testid="live-execution"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-ryx-border">
        <h3 className="text-ryx-foreground font-semibold font-mono flex items-center gap-2">
          <span className="text-ryx-accent">📊</span>
          {title}
        </h3>
        <div className="flex items-center gap-4">
          {/* Progress indicator */}
          <div className="flex items-center gap-2 text-xs font-mono">
            {completedSteps > 0 && (
              <span className="text-ryx-success flex items-center gap-1">
                <span>✓</span>
                <span>{completedSteps}</span>
              </span>
            )}
            {runningSteps > 0 && (
              <span className="text-ryx-cyan flex items-center gap-1 animate-pulse">
                <span>→</span>
                <span>{runningSteps}</span>
              </span>
            )}
            {failedSteps > 0 && (
              <span className="text-ryx-error flex items-center gap-1">
                <span>⚠️</span>
                <span>{failedSteps}</span>
              </span>
            )}
          </div>

          {/* Total latency */}
          {totalLatency !== undefined && !isExecuting && (
            <span className="text-xs bg-ryx-current-line text-ryx-cyan px-2 py-1 rounded-full font-mono">
              Total: {totalLatency}ms
            </span>
          )}

          {/* Live indicator */}
          {isExecuting && (
            <span className="flex items-center gap-1 text-xs text-ryx-cyan font-mono animate-pulse">
              <span className="w-2 h-2 bg-ryx-cyan rounded-full animate-ping" />
              Live
            </span>
          )}
        </div>
      </div>

      {/* Steps List */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-3 ryx-scrollbar"
        role="list"
        aria-live="polite"
        aria-label="Workflow execution steps"
      >
        {steps.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <span className="text-4xl mb-4">🚀</span>
            <p className="text-ryx-text-muted font-mono text-sm">
              No steps yet.
            </p>
            <p className="text-ryx-text-muted font-mono text-xs mt-1 opacity-70">
              Execute a workflow to see live progress
            </p>
          </div>
        ) : (
          steps.map((step, index) => (
            <div
              key={`${step.step}-${step.action}`}
              ref={step.status === 'running' ? activeStepRef : null}
            >
              <Step
                data={step}
                isActive={step.status === 'running'}
                onClick={onStepClick ? () => onStepClick(step) : undefined}
              />
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default LiveExecution;

// Helper function to convert backend events to StepData
export function eventToStep(event: {
  step: number;
  action?: string;
  message?: string;
  status: string;
  latency?: number;
  timestamp?: string;
}): StepData {
  // Map event status to StepStatus
  const statusMap: Record<string, StepStatus> = {
    'pending': 'pending',
    'in_progress': 'running',
    'running': 'running',
    'complete': 'success',
    'success': 'success',
    'error': 'error',
    'failed': 'error',
    'skipped': 'skipped',
  };

  return {
    step: event.step,
    action: event.action || event.message || `Step ${event.step}`,
    status: statusMap[event.status] || 'pending',
    latency: event.latency,
    timestamp: event.timestamp ? new Date(event.timestamp) : new Date(),
  };
}
