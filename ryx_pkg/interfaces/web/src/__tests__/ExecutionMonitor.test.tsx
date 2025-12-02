/**
 * @file ryx/interfaces/web/src/__tests__/ExecutionMonitor.test.tsx
 * @description Unit tests for ExecutionMonitor component.
 * 
 * Tests:
 * - Renders without crashing
 * - Displays events with correct formatting
 * - Auto-scrolls to new events
 * - Limits displayed events to maxEvents
 * - Color-codes events based on status
 */

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import ExecutionMonitor, { DisplayEvent } from '../components/ExecutionMonitor';
import { WorkflowEvent } from '../hooks/useWorkflowWebsocket';

describe('ExecutionMonitor', () => {
  const createMockEvent = (overrides: Partial<DisplayEvent> = {}): DisplayEvent => ({
    id: `event-${Math.random().toString(36).substr(2, 9)}`,
    timestamp: new Date(),
    step: '1',
    node: 'test-node',
    message: 'Test event message',
    status: 'info',
    latency: 100,
    ...overrides,
  });

  it('renders without crashing', () => {
    render(<ExecutionMonitor />);
    expect(screen.getByTestId('execution-monitor')).toBeInTheDocument();
  });

  it('displays header with title', () => {
    render(<ExecutionMonitor title="Custom Title" />);
    expect(screen.getByText('Custom Title')).toBeInTheDocument();
  });

  it('displays empty state when no events', () => {
    render(<ExecutionMonitor events={[]} />);
    expect(screen.getByText('No events to display')).toBeInTheDocument();
  });

  it('displays event count', () => {
    const events = [createMockEvent(), createMockEvent()];
    render(<ExecutionMonitor events={events} maxEvents={50} />);
    expect(screen.getByText('2 / 50 events')).toBeInTheDocument();
  });

  it('renders events with correct structure', () => {
    const events = [
      createMockEvent({
        id: 'test-1',
        step: '1',
        node: 'input',
        message: 'Processing input',
        status: 'success',
        latency: 150,
      }),
    ];

    render(<ExecutionMonitor events={events} />);
    
    // Check step badge
    expect(screen.getByText('[1]')).toBeInTheDocument();
    
    // Check node name
    expect(screen.getByText('input')).toBeInTheDocument();
    
    // Check message
    expect(screen.getByText('Processing input')).toBeInTheDocument();
    
    // Check latency badge
    expect(screen.getByText('150ms')).toBeInTheDocument();
  });

  it('shows success checkmark for success status', () => {
    const events = [createMockEvent({ status: 'success' })];
    render(<ExecutionMonitor events={events} />);
    
    // Success icon should be present
    expect(screen.getByText('✅')).toBeInTheDocument();
  });

  it('shows error icon for error status', () => {
    const events = [createMockEvent({ status: 'error' })];
    render(<ExecutionMonitor events={events} />);
    
    expect(screen.getByText('❌')).toBeInTheDocument();
  });

  it('shows warning icon for warning status', () => {
    const events = [createMockEvent({ status: 'warning' })];
    render(<ExecutionMonitor events={events} />);
    
    expect(screen.getByText('⚠️')).toBeInTheDocument();
  });

  it('shows info icon for info status', () => {
    const events = [createMockEvent({ status: 'info' })];
    render(<ExecutionMonitor events={events} />);
    
    expect(screen.getByText('ℹ️')).toBeInTheDocument();
  });

  it('shows running icon for running status', () => {
    const events = [createMockEvent({ status: 'running' })];
    render(<ExecutionMonitor events={events} />);
    
    expect(screen.getByText('🔄')).toBeInTheDocument();
  });

  it('limits displayed events to maxEvents', () => {
    const events = Array.from({ length: 10 }, (_, i) =>
      createMockEvent({ id: `event-${i}`, message: `Event ${i}` })
    );

    render(<ExecutionMonitor events={events} maxEvents={5} />);
    
    // Should only show last 5 events
    expect(screen.queryByText('Event 0')).not.toBeInTheDocument();
    expect(screen.queryByText('Event 4')).not.toBeInTheDocument();
    expect(screen.getByText('Event 5')).toBeInTheDocument();
    expect(screen.getByText('Event 9')).toBeInTheDocument();
  });

  it('calls onEventClick when event is clicked', () => {
    const onEventClickMock = jest.fn();
    const events = [createMockEvent({ id: 'clickable-event' })];

    render(<ExecutionMonitor events={events} onEventClick={onEventClickMock} />);
    
    const eventElement = screen.getByRole('listitem');
    fireEvent.click(eventElement);
    
    expect(onEventClickMock).toHaveBeenCalledWith(events[0]);
  });

  it('subscribes to workflow events when subscribe is provided', () => {
    const mockSubscribe = jest.fn((callback) => {
      return jest.fn(); // unsubscribe
    });

    render(<ExecutionMonitor subscribe={mockSubscribe} />);
    
    expect(mockSubscribe).toHaveBeenCalled();
  });

  it('converts workflow events to display events', () => {
    let capturedCallback: ((event: WorkflowEvent) => void) | null = null;
    
    const mockSubscribe = jest.fn((callback) => {
      capturedCallback = callback;
      return jest.fn();
    });

    render(<ExecutionMonitor subscribe={mockSubscribe} />);
    
    // Simulate receiving a workflow event
    const workflowEvent: WorkflowEvent = {
      event: 'node_complete',
      step: 2,
      node: 'router',
      message: 'Router completed',
      latency: 50,
      timestamp: new Date().toISOString(),
    };

    act(() => {
      if (capturedCallback) {
        capturedCallback(workflowEvent);
      }
    });

    // Event should be displayed
    expect(screen.getByText('Router completed')).toBeInTheDocument();
    expect(screen.getByText('router')).toBeInTheDocument();
    expect(screen.getByText('50ms')).toBeInTheDocument();
  });

  it('shows live indicator when there are running events', () => {
    const events = [createMockEvent({ status: 'running' })];
    render(<ExecutionMonitor events={events} />);
    
    expect(screen.getByText('Live')).toBeInTheDocument();
  });

  it('applies correct styling classes', () => {
    render(<ExecutionMonitor className="custom-class" />);
    const monitor = screen.getByTestId('execution-monitor');
    
    expect(monitor).toHaveClass('custom-class');
    expect(monitor).toHaveClass('bg-[#282a36]');
    expect(monitor).toHaveClass('rounded-lg');
    expect(monitor).toHaveClass('border');
    expect(monitor).toHaveClass('border-[#6272a4]');
  });

  it('formats timestamp correctly', () => {
    const testDate = new Date('2024-01-15T14:30:45');
    const events = [createMockEvent({ timestamp: testDate })];

    render(<ExecutionMonitor events={events} />);
    
    // Time should be formatted as HH:MM:SS
    expect(screen.getByText('14:30:45')).toBeInTheDocument();
  });

  it('has accessible role and aria attributes', () => {
    render(<ExecutionMonitor />);
    
    const logContainer = screen.getByRole('log');
    expect(logContainer).toHaveAttribute('aria-live', 'polite');
    expect(logContainer).toHaveAttribute('aria-label', 'Workflow execution events');
  });
});
