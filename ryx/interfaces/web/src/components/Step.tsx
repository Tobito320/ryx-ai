/**
 * @file ryx/interfaces/web/src/components/Step.tsx
 * @description Single workflow step component for the execution monitor.
 * 
 * Features:
 * - Status indicator (✓ done, → in progress, ⚠️ error)
 * - Latency badge
 * - Smooth fade-in animation
 * - Current step highlighted
 */

import React from 'react';

/**
 * Step status types
 */
export type StepStatus = 'pending' | 'running' | 'success' | 'error' | 'skipped';

/**
 * Step data interface
 */
export interface StepData {
  /** Step number (1-based) */
  step: number;
  /** Step action/description */
  action: string;
  /** Step status */
  status: StepStatus;
  /** Latency in milliseconds */
  latency?: number;
  /** Additional details */
  details?: string;
  /** Timestamp */
  timestamp?: Date;
}

/**
 * Props for the Step component
 */
export interface StepProps {
  /** Step data */
  data: StepData;
  /** Whether this is the current/active step */
  isActive?: boolean;
  /** Callback when step is clicked */
  onClick?: () => void;
  /** Custom class name */
  className?: string;
}

// Status to icon mapping
const STATUS_ICONS: Record<StepStatus, string> = {
  pending: '○',
  running: '→',
  success: '✓',
  error: '⚠️',
  skipped: '⊘',
};

// Status to color classes mapping
const STATUS_COLORS: Record<StepStatus, { text: string; bg: string; border: string }> = {
  pending: {
    text: 'text-ryx-text-muted',
    bg: 'bg-ryx-current-line/50',
    border: 'border-ryx-border',
  },
  running: {
    text: 'text-ryx-cyan',
    bg: 'bg-ryx-cyan/10',
    border: 'border-ryx-cyan',
  },
  success: {
    text: 'text-ryx-success',
    bg: 'bg-ryx-success/10',
    border: 'border-ryx-success/50',
  },
  error: {
    text: 'text-ryx-error',
    bg: 'bg-ryx-error/10',
    border: 'border-ryx-error',
  },
  skipped: {
    text: 'text-ryx-text-muted',
    bg: 'bg-ryx-current-line/30',
    border: 'border-ryx-border/50',
  },
};

/**
 * Step - A single workflow execution step
 */
export const Step: React.FC<StepProps> = ({
  data,
  isActive = false,
  onClick,
  className = '',
}) => {
  const { step, action, status, latency, details, timestamp } = data;
  const colors = STATUS_COLORS[status];
  const icon = STATUS_ICONS[status];

  return (
    <div
      className={`
        flex items-start gap-3 p-3 rounded-ryx
        ${colors.bg} ${colors.border}
        border transition-all duration-200
        ${isActive ? 'ring-2 ring-ryx-accent/50' : ''}
        ${status === 'running' ? 'animate-pulse-glow' : 'animate-step-in'}
        ${onClick ? 'cursor-pointer hover:bg-opacity-80' : ''}
        ${className}
      `}
      onClick={onClick}
      role="listitem"
      aria-current={isActive ? 'step' : undefined}
    >
      {/* Step Number & Status Icon */}
      <div className={`flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-full ${colors.bg} ${colors.text} font-mono text-sm font-bold border ${colors.border}`}>
        {status === 'running' ? (
          <span className="animate-spin">{icon}</span>
        ) : (
          <span>{icon}</span>
        )}
      </div>

      {/* Step Content */}
      <div className="flex-1 min-w-0">
        {/* Step Number & Action */}
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-mono text-ryx-orange bg-ryx-bg px-1.5 py-0.5 rounded">
            {step}.
          </span>
          <span className={`text-sm font-medium font-mono ${colors.text}`}>
            {action}
          </span>
        </div>

        {/* Details */}
        {details && (
          <p className="text-xs text-ryx-text-muted font-mono mt-1 break-words">
            {details}
          </p>
        )}

        {/* Footer: Timestamp & Latency */}
        <div className="flex items-center gap-3 mt-2">
          {timestamp && (
            <span className="text-[10px] text-ryx-text-muted font-mono">
              {timestamp.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false,
              })}
            </span>
          )}
          {latency !== undefined && status === 'success' && (
            <span className="text-xs bg-ryx-current-line text-ryx-cyan px-2 py-0.5 rounded-full font-mono">
              {latency}ms
            </span>
          )}
          {status === 'running' && (
            <span className="text-xs text-ryx-cyan font-mono animate-pulse">
              Running...
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default Step;
