/**
 * @file ryx/interfaces/web/src/components/LiveExecution.tsx
 * @description N8N-style execution timeline panel.
 */

import React, { useEffect, useRef } from 'react';
import { Step, StepData, StepStatus } from './Step';

export interface LiveExecutionProps {
  steps: StepData[];
  title?: string;
  isExecuting?: boolean;
  totalLatency?: number;
  onStepClick?: (step: StepData) => void;
  className?: string;
}

export const LiveExecution: React.FC<LiveExecutionProps> = ({
  steps,
  title = 'Execution',
  isExecuting = false,
  totalLatency,
  onStepClick,
  className = '',
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const activeStepIndex = steps.findIndex(s => s.status === 'running');

  // Auto-scroll to active step
  useEffect(() => {
    if (activeStepIndex >= 0 && scrollContainerRef.current) {
      const container = scrollContainerRef.current;
      const stepElements = container.querySelectorAll('.step-card');
      if (stepElements[activeStepIndex]) {
        stepElements[activeStepIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [activeStepIndex, steps.length]);

  const completedSteps = steps.filter(s => s.status === 'success').length;
  const totalSteps = steps.length;

  return (
    <div
      className={`flex flex-col h-full ${className}`}
      style={{ background: 'var(--bg-elevated)' }}
      data-testid="live-execution"
    >
      {/* Header */}
      <div className="panel-header">
        <h2>{title}</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {totalSteps > 0 && (
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              {completedSteps}/{totalSteps} steps
            </span>
          )}
          {totalLatency && !isExecuting && (
            <span 
              style={{ 
                fontSize: '11px', 
                padding: '2px 8px', 
                background: 'var(--bg-card)', 
                borderRadius: '10px',
                color: 'var(--status-success)' 
              }}
            >
              {totalLatency}ms total
            </span>
          )}
          {isExecuting && (
            <span style={{ fontSize: '11px', color: 'var(--status-running)' }}>
              Running...
            </span>
          )}
        </div>
      </div>

      {/* Steps Timeline */}
      <div 
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-4 scrollbar-thin"
        style={{ paddingLeft: '28px' }}
      >
        {steps.length === 0 ? (
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            justifyContent: 'center', 
            height: '100%',
            color: 'var(--text-muted)'
          }}>
            <span style={{ fontSize: '24px', marginBottom: '8px', opacity: 0.5 }}>▶️</span>
            <span style={{ fontSize: '12px' }}>Select a workflow to execute</span>
          </div>
        ) : (
          <div style={{ position: 'relative' }}>
            {/* Timeline line */}
            <div style={{
              position: 'absolute',
              left: '-14px',
              top: '20px',
              bottom: '20px',
              width: '2px',
              background: 'var(--border-subtle)',
            }} />
            
            {/* Steps */}
            {steps.map((step, index) => (
              <Step
                key={step.step}
                data={step}
                isActive={index === activeStepIndex}
                onClick={onStepClick ? () => onStepClick(step) : undefined}
                className="animate-fade-in"
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Helper function to convert backend events to StepData
export function eventToStep(event: {
  step: number;
  action?: string;
  message?: string;
  status: string;
  latency?: number;
  timestamp?: string;
}): StepData {
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

export default LiveExecution;
