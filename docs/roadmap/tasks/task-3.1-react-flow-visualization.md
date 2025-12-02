# Task 3.1: React Flow Workflow Visualization

**Time:** 60 min | **Priority:** HIGH | **Agent:** Copilot

## Objective

Complete the `WorkflowCanvas` component with full React Flow integration, node status updates, color coding with Dracula theme, latency display on edges, and automatic layout.

## Output File(s)

`ryx/interfaces/web/src/components/WorkflowCanvas.tsx`

## Dependencies

- Task 1.2: React component scaffolds

## Requirements

### React Flow Integration

- Use `reactflow` package for the flow visualization
- Implement custom node component for workflow steps
- Implement custom edge component with latency display

### Node Status Updates

| Status | Visual | Animation |
|--------|--------|-----------|
| pending | Yellow border | None |
| running | Cyan border | Pulse animation |
| success | Green border | None |
| failed | Red border | None |

### Dracula Theme Colors

```typescript
const DraculaColors = {
  background: '#282a36',
  currentLine: '#44475a',
  foreground: '#f8f8f2',
  comment: '#6272a4',
  cyan: '#8be9fd',
  green: '#50fa7b',
  orange: '#ffb86c',
  pink: '#ff79c6',
  purple: '#bd93f9',
  red: '#ff5555',
  yellow: '#f1fa8c',
};
```

### Automatic Layout

- Use dagre for automatic node positioning
- Support horizontal and vertical layouts
- Nodes should not overlap
- Edges should have proper routing

### Features

1. Zoom and pan controls
2. Node selection highlighting
3. Mini-map for navigation
4. Fit-to-view button
5. Real-time status updates

## Code Template

```typescript
'use client';

import React, { useCallback, useMemo, useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  MiniMap,
  Background,
  useNodesState,
  useEdgesState,
  NodeTypes,
  EdgeTypes,
  Position,
  MarkerType,
} from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';

// =============================================================================
// Types
// =============================================================================

type NodeStatus = 'pending' | 'running' | 'success' | 'failed';

interface WorkflowNodeData {
  id: string;
  label: string;
  type: 'input' | 'process' | 'output' | 'tool';
  status: NodeStatus;
  latency?: number;
}

interface WorkflowEdgeData {
  latency?: number;
}

interface WorkflowCanvasProps {
  nodes: WorkflowNodeData[];
  edges: Array<{
    id: string;
    source: string;
    target: string;
    latency?: number;
  }>;
  onNodeSelect?: (id: string) => void;
  direction?: 'TB' | 'LR';  // Top-to-bottom or Left-to-right
}

// =============================================================================
// Dracula Theme
// =============================================================================

const DraculaColors = {
  background: '#282a36',
  currentLine: '#44475a',
  foreground: '#f8f8f2',
  comment: '#6272a4',
  cyan: '#8be9fd',
  green: '#50fa7b',
  orange: '#ffb86c',
  pink: '#ff79c6',
  purple: '#bd93f9',
  red: '#ff5555',
  yellow: '#f1fa8c',
};

const statusColors: Record<NodeStatus, string> = {
  pending: DraculaColors.yellow,
  running: DraculaColors.cyan,
  success: DraculaColors.green,
  failed: DraculaColors.red,
};

// =============================================================================
// Custom Node Component
// =============================================================================

interface CustomNodeProps {
  data: WorkflowNodeData;
  selected: boolean;
}

const CustomNode: React.FC<CustomNodeProps> = ({ data, selected }) => {
  const borderColor = statusColors[data.status];
  const isRunning = data.status === 'running';
  
  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 min-w-[120px]
        transition-all duration-200
        ${isRunning ? 'animate-pulse' : ''}
        ${selected ? 'ring-2 ring-offset-2 ring-offset-[#282a36]' : ''}
      `}
      style={{
        backgroundColor: DraculaColors.currentLine,
        borderColor: borderColor,
        color: DraculaColors.foreground,
        boxShadow: selected ? `0 0 10px ${DraculaColors.purple}` : 'none',
      }}
    >
      <div className="font-medium text-sm">{data.label}</div>
      {data.latency !== undefined && (
        <div 
          className="text-xs mt-1"
          style={{ color: DraculaColors.comment }}
        >
          {data.latency.toFixed(1)}ms
        </div>
      )}
      <div 
        className="text-xs mt-1 capitalize"
        style={{ color: borderColor }}
      >
        {data.status}
      </div>
    </div>
  );
};

// =============================================================================
// Custom Edge Component
// =============================================================================

interface CustomEdgeProps {
  id: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  data?: WorkflowEdgeData;
}

const CustomEdge: React.FC<CustomEdgeProps> = ({
  sourceX,
  sourceY,
  targetX,
  targetY,
  data,
}) => {
  const midX = (sourceX + targetX) / 2;
  const midY = (sourceY + targetY) / 2;
  
  return (
    <>
      <path
        d={`M${sourceX},${sourceY} C${midX},${sourceY} ${midX},${targetY} ${targetX},${targetY}`}
        fill="none"
        stroke={DraculaColors.comment}
        strokeWidth={2}
      />
      {data?.latency !== undefined && (
        <foreignObject
          x={midX - 25}
          y={midY - 10}
          width={50}
          height={20}
        >
          <div
            className="text-xs px-1 rounded text-center"
            style={{
              backgroundColor: DraculaColors.background,
              color: DraculaColors.cyan,
            }}
          >
            {data.latency.toFixed(0)}ms
          </div>
        </foreignObject>
      )}
    </>
  );
};

// =============================================================================
// Layout Helper
// =============================================================================

const getLayoutedElements = (
  nodes: Node[],
  edges: Edge[],
  direction: 'TB' | 'LR' = 'TB'
) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  
  const nodeWidth = 150;
  const nodeHeight = 80;
  
  dagreGraph.setGraph({ 
    rankdir: direction,
    ranksep: 80,
    nodesep: 50,
  });
  
  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });
  
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });
  
  dagre.layout(dagreGraph);
  
  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
      targetPosition: direction === 'TB' ? Position.Top : Position.Left,
      sourcePosition: direction === 'TB' ? Position.Bottom : Position.Right,
    };
  });
  
  return { nodes: layoutedNodes, edges };
};

// =============================================================================
// Main Component
// =============================================================================

const nodeTypes: NodeTypes = {
  custom: CustomNode,
};

const edgeTypes: EdgeTypes = {
  custom: CustomEdge as any,
};

export const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({
  nodes: inputNodes,
  edges: inputEdges,
  onNodeSelect,
  direction = 'TB',
}) => {
  // Convert input data to React Flow format
  const initialNodes: Node[] = useMemo(() => 
    inputNodes.map((node) => ({
      id: node.id,
      type: 'custom',
      position: { x: 0, y: 0 },
      data: node,
    })),
    [inputNodes]
  );
  
  const initialEdges: Edge[] = useMemo(() =>
    inputEdges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'custom',
      data: { latency: edge.latency },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: DraculaColors.comment,
      },
    })),
    [inputEdges]
  );
  
  // Apply layout
  const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(
    () => getLayoutedElements(initialNodes, initialEdges, direction),
    [initialNodes, initialEdges, direction]
  );
  
  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);
  
  // Update nodes when input changes
  useEffect(() => {
    const { nodes: newNodes, edges: newEdges } = getLayoutedElements(
      initialNodes,
      initialEdges,
      direction
    );
    setNodes(newNodes);
    setEdges(newEdges);
  }, [inputNodes, inputEdges, direction, setNodes, setEdges]);
  
  // Handle node click
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeSelect?.(node.id);
    },
    [onNodeSelect]
  );
  
  return (
    <div 
      className="w-full h-full"
      style={{ backgroundColor: DraculaColors.background }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Background 
          color={DraculaColors.comment}
          gap={20}
          size={1}
        />
        <Controls 
          style={{
            backgroundColor: DraculaColors.currentLine,
            borderColor: DraculaColors.comment,
          }}
        />
        <MiniMap
          nodeColor={(node) => statusColors[(node.data as WorkflowNodeData).status]}
          style={{
            backgroundColor: DraculaColors.background,
            border: `1px solid ${DraculaColors.comment}`,
          }}
        />
      </ReactFlow>
    </div>
  );
};

export default WorkflowCanvas;
```

## Acceptance Criteria

- [ ] React Flow integration complete
- [ ] Custom node component with status colors
- [ ] Custom edge component with latency display
- [ ] Dracula theme colors applied
- [ ] Automatic dagre layout working
- [ ] Pending nodes have yellow border
- [ ] Running nodes have cyan border with pulse animation
- [ ] Success nodes have green border
- [ ] Failed nodes have red border
- [ ] Node selection highlighting with purple ring
- [ ] Zoom and pan controls visible
- [ ] MiniMap for navigation
- [ ] Fit-to-view on initial render
- [ ] TypeScript types for all props
- [ ] Component exports as named export

## Notes

- Install required packages: `npm install reactflow dagre @types/dagre`
- Use `useMemo` for performance with layout calculations
- Node positions should update when status changes
- Edge latency should display in milliseconds
- Support both TB (top-to-bottom) and LR (left-to-right) directions
