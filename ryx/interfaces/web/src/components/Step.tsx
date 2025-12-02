/**
 * @file ryx/interfaces/web/src/components/Step.tsx
 * @description N8N-style workflow step card for the execution timeline.
 */

import React from 'react';

export type StepStatus = 'pending' | 'running' | 'success' | 'error' | 'skipped';

export interface StepData {
  step: number;
  action: string;
  status: StepStatus;
  latency?: number;
  details?: string;
  timestamp?: Date;
}

export interface StepProps {
  data: StepData;
  isActive?: boolean;
  onClick?: () => void;
  className?: string;
}

/**
 * Step - N8N-style execution step card
 */
export const Step: React.FC<StepProps> = ({
  data,
  isActive = false,
  onClick,
  className = '',
}) => {
  const { step, action, status, latency, details } = data;

  return (
    <div
      className={`step-card ${status} ${isActive ? 'ring-1 ring-[var(--accent)]' : ''} ${className}`}
      onClick={onClick}
      role="listitem"
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Header: Title + Latency */}
      <div className="step-header">
        <span className="step-title">
          <span style={{ color: 'var(--text-muted)', marginRight: '6px' }}>{step}.</span>
          {action}
        </span>
        {latency !== undefined && status === 'success' && (
          <span className="step-latency">{latency}ms</span>
        )}
        {status === 'running' && (
          <span className="step-latency" style={{ color: 'var(--status-running)' }}>
            Running...
          </span>
        )}
      </div>
      
      {/* Content: Details if present */}
      {details && (
        <div className="step-content">{details}</div>
      )}
    </div>
  );
};

export default Step;
