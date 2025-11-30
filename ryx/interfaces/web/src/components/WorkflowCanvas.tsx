import React from 'react';
import { WorkflowNode } from './WorkflowNode';

/**
 * Represents a node's data in the workflow
 */
export interface WorkflowNodeData {
  /** Unique node identifier */
  id: string;
  /** Display label */
  label: string;
  /** Node type */
  type: 'input' | 'process' | 'output' | 'tool';
  /** Current execution status */
  status: 'pending' | 'running' | 'success' | 'failed';
  /** Node position on canvas */
  position: { x: number; y: number };
}

/**
 * Represents an edge connecting two nodes
 */
export interface WorkflowEdge {
  /** Unique edge identifier */
  id: string;
  /** Source node ID */
  source: string;
  /** Target node ID */
  target: string;
  /** Edge latency in milliseconds */
  latency?: number;
}

/**
 * Props for the WorkflowCanvas component
 */
interface WorkflowCanvasProps {
  /** Array of node data */
  nodes: WorkflowNodeData[];
  /** Array of edge connections */
  edges: WorkflowEdge[];
  /** Callback when a node is selected */
  onNodeSelect?: (id: string) => void;
  /** Callback when zoom level changes */
  onZoom?: (level: number) => void;
}

/**
 * WorkflowCanvas - A canvas component for rendering workflow visualization
 * Displays nodes and their connections using Dracula theme colors
 */
export const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({
  nodes,
  edges,
  onNodeSelect,
  onZoom,
}) => {
  const [zoomLevel, setZoomLevel] = React.useState(1);
  const [selectedNodeId, setSelectedNodeId] = React.useState<string | null>(null);

  const handleZoomIn = () => {
    const newZoom = Math.min(zoomLevel + 0.1, 2);
    setZoomLevel(newZoom);
    onZoom?.(newZoom);
  };

  const handleZoomOut = () => {
    const newZoom = Math.max(zoomLevel - 0.1, 0.5);
    setZoomLevel(newZoom);
    onZoom?.(newZoom);
  };

  const handleNodeSelect = (id: string) => {
    setSelectedNodeId(id);
    onNodeSelect?.(id);
  };

  return (
    <div className="relative w-full h-full bg-[#282a36] overflow-hidden rounded-lg border border-[#6272a4]">
      {/* Zoom Controls */}
      <div className="absolute top-4 right-4 flex flex-col gap-2 z-10">
        <button
          onClick={handleZoomIn}
          className="p-2 bg-[#44475a] text-[#f8f8f2] rounded hover:bg-[#6272a4] transition-colors"
          aria-label="Zoom in"
        >
          +
        </button>
        <span className="text-center text-xs text-[#8be9fd]">
          {Math.round(zoomLevel * 100)}%
        </span>
        <button
          onClick={handleZoomOut}
          className="p-2 bg-[#44475a] text-[#f8f8f2] rounded hover:bg-[#6272a4] transition-colors"
          aria-label="Zoom out"
        >
          -
        </button>
      </div>

      {/* Canvas Content */}
      <div
        className="relative w-full h-full"
        style={{
          transform: `scale(${zoomLevel})`,
          transformOrigin: 'center center',
        }}
      >
        {/* SVG Layer for Edges */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          {edges.map((edge) => {
            const sourceNode = nodes.find((n) => n.id === edge.source);
            const targetNode = nodes.find((n) => n.id === edge.target);

            if (!sourceNode || !targetNode) return null;

            return (
              <g key={edge.id}>
                <line
                  x1={sourceNode.position.x + 75}
                  y1={sourceNode.position.y + 40}
                  x2={targetNode.position.x + 75}
                  y2={targetNode.position.y + 40}
                  stroke="#6272a4"
                  strokeWidth="2"
                  markerEnd="url(#arrowhead)"
                />
                {edge.latency !== undefined && (
                  <text
                    x={(sourceNode.position.x + targetNode.position.x) / 2 + 75}
                    y={(sourceNode.position.y + targetNode.position.y) / 2 + 40}
                    fill="#8be9fd"
                    fontSize="12"
                    textAnchor="middle"
                  >
                    {edge.latency}ms
                  </text>
                )}
              </g>
            );
          })}
          {/* Arrow marker definition */}
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#6272a4" />
            </marker>
          </defs>
        </svg>

        {/* Nodes Layer */}
        {nodes.map((node) => (
          <div
            key={node.id}
            className="absolute"
            style={{
              left: node.position.x,
              top: node.position.y,
              width: '150px',
            }}
          >
            <WorkflowNode
              id={node.id}
              label={node.label}
              type={node.type}
              status={node.status}
              isSelected={selectedNodeId === node.id}
              onSelect={handleNodeSelect}
            />
          </div>
        ))}
      </div>

      {/* Empty State */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="text-[#6272a4]">No workflow nodes to display</p>
        </div>
      )}
    </div>
  );
};

export default WorkflowCanvas;
