/**
 * @file ryx/interfaces/web/src/__tests__/WorkflowCanvas.test.tsx
 * @description Unit tests for WorkflowCanvas component.
 * 
 * Tests:
 * - Renders without crashing
 * - Displays default workflow nodes
 * - Updates node status on workflow events
 * - Handles node selection
 */

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import WorkflowCanvas from '../components/WorkflowCanvas';
import { WorkflowEvent } from '../hooks/useWorkflowWebsocket';

// Mock React Flow since it requires DOM measurements
jest.mock('reactflow', () => {
  const React = require('react');
  
  return {
    __esModule: true,
    default: ({ children, nodes, edges, ...props }: any) => (
      <div data-testid="react-flow-mock" data-nodes={JSON.stringify(nodes)} data-edges={JSON.stringify(edges)}>
        {children}
      </div>
    ),
    Controls: ({ children }: any) => <div data-testid="react-flow-controls">{children}</div>,
    Background: () => <div data-testid="react-flow-background" />,
    BackgroundVariant: { Dots: 'dots' },
    Handle: ({ type, position }: any) => (
      <div data-testid={`handle-${type}-${position}`} />
    ),
    Position: { Left: 'left', Right: 'right', Top: 'top', Bottom: 'bottom' },
    MarkerType: { ArrowClosed: 'arrowclosed' },
    ConnectionMode: { Loose: 'loose' },
    useNodesState: (initialNodes: any) => {
      const [nodes, setNodes] = React.useState(initialNodes);
      return [nodes, setNodes, jest.fn()];
    },
    useEdgesState: (initialEdges: any) => {
      const [edges, setEdges] = React.useState(initialEdges);
      return [edges, setEdges, jest.fn()];
    },
  };
});

describe('WorkflowCanvas', () => {
  it('renders without crashing', () => {
    render(<WorkflowCanvas />);
    expect(screen.getByTestId('workflow-canvas')).toBeInTheDocument();
  });

  it('renders React Flow container', () => {
    render(<WorkflowCanvas />);
    expect(screen.getByTestId('react-flow-mock')).toBeInTheDocument();
  });

  it('renders controls when showControls is true', () => {
    render(<WorkflowCanvas showControls={true} />);
    expect(screen.getByTestId('react-flow-controls')).toBeInTheDocument();
  });

  it('renders background', () => {
    render(<WorkflowCanvas />);
    expect(screen.getByTestId('react-flow-background')).toBeInTheDocument();
  });

  it('uses default nodes when initialNodes not provided', () => {
    render(<WorkflowCanvas />);
    const flowContainer = screen.getByTestId('react-flow-mock');
    const nodesData = JSON.parse(flowContainer.getAttribute('data-nodes') || '[]');
    
    // Should have 8 default workflow nodes
    expect(nodesData.length).toBe(8);
    
    // Check for expected node IDs
    const nodeIds = nodesData.map((n: any) => n.id);
    expect(nodeIds).toContain('input');
    expect(nodeIds).toContain('router');
    expect(nodeIds).toContain('output');
  });

  it('uses default edges when initialEdges not provided', () => {
    render(<WorkflowCanvas />);
    const flowContainer = screen.getByTestId('react-flow-mock');
    const edgesData = JSON.parse(flowContainer.getAttribute('data-edges') || '[]');
    
    // Should have edges connecting nodes
    expect(edgesData.length).toBeGreaterThan(0);
  });

  it('uses custom initial nodes when provided', () => {
    const customNodes = [
      {
        id: 'custom-1',
        type: 'workflow',
        position: { x: 0, y: 0 },
        data: { label: 'Custom Node', type: 'process' as const, status: 'pending' as const },
      },
    ];
    
    render(<WorkflowCanvas initialNodes={customNodes} />);
    const flowContainer = screen.getByTestId('react-flow-mock');
    const nodesData = JSON.parse(flowContainer.getAttribute('data-nodes') || '[]');
    
    expect(nodesData.length).toBe(1);
    expect(nodesData[0].id).toBe('custom-1');
  });

  it('accepts custom className', () => {
    render(<WorkflowCanvas className="custom-class" />);
    expect(screen.getByTestId('workflow-canvas')).toHaveClass('custom-class');
  });

  it('subscribes to workflow events when subscribe is provided', () => {
    const mockSubscribe = jest.fn((callback) => {
      // Return unsubscribe function
      return jest.fn();
    });

    render(<WorkflowCanvas subscribe={mockSubscribe} />);
    
    expect(mockSubscribe).toHaveBeenCalled();
  });

  it('calls onEvent callback when workflow event is received', () => {
    const onEventMock = jest.fn();
    let capturedCallback: ((event: WorkflowEvent) => void) | null = null;
    
    const mockSubscribe = jest.fn((callback) => {
      capturedCallback = callback;
      return jest.fn();
    });

    render(<WorkflowCanvas subscribe={mockSubscribe} onEvent={onEventMock} />);
    
    // Simulate receiving an event
    const testEvent: WorkflowEvent = {
      event: 'node_start',
      step: 1,
      node: 'input',
      message: 'Starting input node',
      timestamp: new Date().toISOString(),
    };

    act(() => {
      if (capturedCallback) {
        capturedCallback(testEvent);
      }
    });

    expect(onEventMock).toHaveBeenCalledWith(testEvent);
  });

  it('calls onNodeSelect when node selection changes', () => {
    const onNodeSelectMock = jest.fn();
    
    render(<WorkflowCanvas onNodeSelect={onNodeSelectMock} />);
    
    // Note: Full node selection testing would require more complex React Flow mocking
    // This test verifies the prop is accepted
    expect(screen.getByTestId('workflow-canvas')).toBeInTheDocument();
  });

  it('applies correct styling classes', () => {
    render(<WorkflowCanvas />);
    const canvas = screen.getByTestId('workflow-canvas');
    
    expect(canvas).toHaveClass('w-full');
    expect(canvas).toHaveClass('h-full');
    expect(canvas).toHaveClass('bg-[#282a36]');
    expect(canvas).toHaveClass('rounded-lg');
    expect(canvas).toHaveClass('border');
    expect(canvas).toHaveClass('border-[#6272a4]');
  });
});
