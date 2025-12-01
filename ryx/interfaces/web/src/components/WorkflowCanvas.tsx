/**
 * @file ryx/interfaces/web/src/components/WorkflowCanvas.tsx
 * @description React Flow workflow visualization canvas component.
 * 
 * Features:
 * - Renders 8 workflow step nodes with React Flow
 * - Subscribes to WebSocket events to update node status
 * - Shows latency badges on edges
 * - Highlights running step with animation
 * - Supports zoom, pan, and node selection
 * 
 * Uses Dracula theme colors via Tailwind CSS.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  MarkerType,
  ConnectionMode,
  NodeChange,
  EdgeChange,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { WorkflowFlowNode, WorkflowNodeData, NodeExecutionStatus } from './WorkflowNode';
import { WorkflowEvent, WorkflowEventType } from '../hooks/useWorkflowWebsocket';

/** Props for WorkflowCanvas component */
export interface WorkflowCanvasProps {
  /** Initial nodes for the workflow (optional) */
  initialNodes?: Node<WorkflowNodeData>[];
  /** Initial edges connecting nodes (optional) */
  initialEdges?: Edge[];
  /** Callback when a workflow event is received */
  onEvent?: (event: WorkflowEvent) => void;
  /** Subscribe function from useWorkflowWebsocket */
  subscribe?: (callback: (event: WorkflowEvent) => void) => () => void;
  /** Callback when a node is selected */
  onNodeSelect?: (nodeId: string | null) => void;
  /** Callback when node action is triggered */
  onNodeAction?: (nodeId: string) => void;
  /** Whether to show controls */
  showControls?: boolean;
  /** Whether to show minimap */
  showMinimap?: boolean;
  /** Custom class name */
  className?: string;
}

// Custom node types registration
const nodeTypes = {
  workflow: WorkflowFlowNode,
};

// Default 8-step workflow nodes
const createDefaultNodes = (): Node<WorkflowNodeData>[] => [
  {
    id: 'input',
    type: 'workflow',
    position: { x: 50, y: 200 },
    data: { label: 'Input', type: 'input', status: 'pending', step: 1 },
  },
  {
    id: 'router',
    type: 'workflow',
    position: { x: 280, y: 200 },
    data: { label: 'Router', type: 'router', status: 'pending', step: 2 },
  },
  {
    id: 'model',
    type: 'workflow',
    position: { x: 510, y: 100 },
    data: { label: 'Model', type: 'model', status: 'pending', step: 3 },
  },
  {
    id: 'tool-search',
    type: 'workflow',
    position: { x: 510, y: 300 },
    data: { label: 'Search Tool', type: 'tool', status: 'pending', step: 4 },
  },
  {
    id: 'process',
    type: 'workflow',
    position: { x: 740, y: 200 },
    data: { label: 'Process', type: 'process', status: 'pending', step: 5 },
  },
  {
    id: 'tool-edit',
    type: 'workflow',
    position: { x: 970, y: 100 },
    data: { label: 'Edit File', type: 'tool', status: 'pending', step: 6 },
  },
  {
    id: 'tool-launch',
    type: 'workflow',
    position: { x: 970, y: 300 },
    data: { label: 'Launch App', type: 'tool', status: 'pending', step: 7 },
  },
  {
    id: 'output',
    type: 'workflow',
    position: { x: 1200, y: 200 },
    data: { label: 'Output', type: 'output', status: 'pending', step: 8 },
  },
];

// Default edges connecting the workflow
const createDefaultEdges = (): Edge[] => [
  {
    id: 'input-router',
    source: 'input',
    target: 'router',
    animated: false,
    style: { stroke: '#6272a4', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6272a4' },
  },
  {
    id: 'router-model',
    source: 'router',
    target: 'model',
    animated: false,
    style: { stroke: '#6272a4', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6272a4' },
  },
  {
    id: 'router-search',
    source: 'router',
    target: 'tool-search',
    animated: false,
    style: { stroke: '#6272a4', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6272a4' },
  },
  {
    id: 'model-process',
    source: 'model',
    target: 'process',
    animated: false,
    style: { stroke: '#6272a4', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6272a4' },
  },
  {
    id: 'search-process',
    source: 'tool-search',
    target: 'process',
    animated: false,
    style: { stroke: '#6272a4', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6272a4' },
  },
  {
    id: 'process-edit',
    source: 'process',
    target: 'tool-edit',
    animated: false,
    style: { stroke: '#6272a4', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6272a4' },
  },
  {
    id: 'process-launch',
    source: 'process',
    target: 'tool-launch',
    animated: false,
    style: { stroke: '#6272a4', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6272a4' },
  },
  {
    id: 'edit-output',
    source: 'tool-edit',
    target: 'output',
    animated: false,
    style: { stroke: '#6272a4', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6272a4' },
  },
  {
    id: 'launch-output',
    source: 'tool-launch',
    target: 'output',
    animated: false,
    style: { stroke: '#6272a4', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6272a4' },
  },
];

// Map event types to node status
const eventToStatus = (eventType: WorkflowEventType): NodeExecutionStatus => {
  switch (eventType) {
    case 'node_start':
      return 'running';
    case 'node_complete':
      return 'success';
    case 'node_failed':
      return 'failed';
    case 'node_skipped':
      return 'pending';
    default:
      return 'pending';
  }
};

/**
 * WorkflowCanvas - Main workflow visualization component using React Flow
 */
export const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({
  initialNodes,
  initialEdges,
  subscribe,
  onEvent,
  onNodeSelect,
  onNodeAction,
  showControls = true,
  className = '',
}) => {
  const defaultNodes = useMemo(() => initialNodes || createDefaultNodes(), [initialNodes]);
  const defaultEdges = useMemo(() => initialEdges || createDefaultEdges(), [initialEdges]);

  const [nodes, setNodes, onNodesChange] = useNodesState(defaultNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(defaultEdges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Handle workflow events
  const handleWorkflowEvent = useCallback(
    (event: WorkflowEvent) => {
      onEvent?.(event);

      // Update node status based on event
      if (event.node) {
        const eventNodeLower = event.node.toLowerCase();
        
        setNodes((nds) =>
          nds.map((node) => {
            // Direct ID match or label contains node name
            const isMatch = node.id === event.node || 
                           node.data.label.toLowerCase().includes(eventNodeLower);
            
            if (isMatch) {
              const newStatus = eventToStatus(event.event);
              return {
                ...node,
                data: {
                  ...node.data,
                  status: newStatus,
                  latency: event.latency ?? node.data.latency,
                },
              };
            }
            return node;
          })
        );

        // Animate edges when node completes
        if (event.event === 'node_complete') {
          setEdges((eds) =>
            eds.map((edge) => {
              if (edge.source === event.node) {
                return {
                  ...edge,
                  animated: true,
                  style: { ...edge.style, stroke: '#8be9fd' },
                  label: event.latency ? `${event.latency}ms` : undefined,
                  labelStyle: { fill: '#8be9fd', fontSize: 12 },
                  labelBgStyle: { fill: '#282a36', fillOpacity: 0.8 },
                };
              }
              return edge;
            })
          );
        }
      }

      // Handle workflow-level events
      if (event.event === 'workflow_start') {
        // Reset all nodes to pending
        setNodes((nds) =>
          nds.map((node) => ({
            ...node,
            data: { ...node.data, status: 'pending' as NodeExecutionStatus, latency: undefined },
          }))
        );
        // Reset edges
        setEdges((eds) =>
          eds.map((edge) => ({
            ...edge,
            animated: false,
            style: { ...edge.style, stroke: '#6272a4' },
            label: undefined,
          }))
        );
      }

      if (event.event === 'workflow_complete') {
        // Mark output node as success
        setNodes((nds) =>
          nds.map((node) =>
            node.id === 'output'
              ? { ...node, data: { ...node.data, status: 'success' as NodeExecutionStatus } }
              : node
          )
        );
      }

      if (event.event === 'workflow_failed') {
        // Mark remaining running nodes as failed
        setNodes((nds) =>
          nds.map((node) =>
            node.data.status === 'running'
              ? { ...node, data: { ...node.data, status: 'failed' as NodeExecutionStatus } }
              : node
          )
        );
      }
    },
    [onEvent, setNodes, setEdges]
  );

  // Subscribe to workflow events
  useEffect(() => {
    if (subscribe) {
      const unsubscribe = subscribe(handleWorkflowEvent);
      return unsubscribe;
    }
  }, [subscribe, handleWorkflowEvent]);

  // Handle node selection
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      onNodesChange(changes);

      // Find selection changes
      const selectionChange = changes.find(
        (change) => change.type === 'select' && 'selected' in change
      );
      if (selectionChange && 'id' in selectionChange && 'selected' in selectionChange) {
        const nodeId = (selectionChange as { selected: boolean; id: string }).selected 
          ? (selectionChange as { id: string }).id 
          : null;
        setSelectedNodeId(nodeId);
        onNodeSelect?.(nodeId);
      }
    },
    [onNodesChange, onNodeSelect]
  );

  // Inject onAction callback into node data
  const nodesWithAction = useMemo(() => {
    if (!onNodeAction) return nodes;
    return nodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        onAction: onNodeAction,
      },
    }));
  }, [nodes, onNodeAction]);

  return (
    <div
      className={`w-full h-full bg-[#282a36] rounded-lg border border-[#6272a4] ${className}`}
      data-testid="workflow-canvas"
    >
      <ReactFlow
        nodes={nodesWithAction}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={2}
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
      >
        {showControls && (
          <Controls
            className="!bg-[#44475a] !border-[#6272a4] !rounded-lg"
            showZoom={true}
            showFitView={true}
            showInteractive={false}
          />
        )}
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#6272a4"
        />
      </ReactFlow>

      {/* Empty State */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <p className="text-[#6272a4]">No workflow nodes to display</p>
        </div>
      )}
    </div>
  );
};

export default WorkflowCanvas;

// Re-export types for convenience
export type { WorkflowNodeData } from './WorkflowNode';
