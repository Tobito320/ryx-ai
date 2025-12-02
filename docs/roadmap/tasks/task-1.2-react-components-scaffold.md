# Task 1.2: React Components Scaffold

**Time:** 45 min | **Priority:** HIGH | **Agent:** Copilot

## Objective

Create React component scaffolds for the workflow visualization UI using TypeScript and Tailwind CSS with Dracula theme colors.

## Output File(s)

```
ryx/interfaces/web/src/components/
├── WorkflowNode.tsx
├── WorkflowCanvas.tsx
├── ExecutionMonitor.tsx
├── ToolResults.tsx
└── WorkflowDashboard.tsx
```

## Requirements

1. **All files must be TypeScript** (`.tsx` extension)

2. **Use Tailwind CSS** with Dracula theme colors:
   ```css
   bg: #282a36 (bg-[#282a36])
   text: #f8f8f2 (text-[#f8f8f2])
   cyan: #8be9fd (text-[#8be9fd])
   pink: #ff79c6 (text-[#ff79c6])
   green: #50fa7b (text-[#50fa7b])
   purple: #bd93f9 (text-[#bd93f9])
   orange: #ffb86c (text-[#ffb86c])
   red: #ff5555 (text-[#ff5555])
   yellow: #f1fa8c (text-[#f1fa8c])
   ```

3. **Component Props interfaces** must be defined for each component

4. **Structure only** - no complex logic, just render basic UI structure

### Component Specifications

#### WorkflowNode.tsx
Props interface:
- `id: string` - Unique node identifier
- `label: string` - Display label
- `type: 'input' | 'process' | 'output' | 'tool'` - Node type
- `status: 'pending' | 'running' | 'success' | 'failed'` - Current status
- `latency?: number` - Execution time in ms
- `isSelected?: boolean` - Selection state
- `onSelect?: (id: string) => void` - Selection handler

#### WorkflowCanvas.tsx
Props interface:
- `nodes: WorkflowNodeData[]` - Array of node data
- `edges: WorkflowEdge[]` - Array of edge connections
- `onNodeSelect?: (id: string) => void` - Node selection handler
- `onZoom?: (level: number) => void` - Zoom handler

Supporting types:
```typescript
interface WorkflowNodeData {
  id: string;
  label: string;
  type: 'input' | 'process' | 'output' | 'tool';
  status: 'pending' | 'running' | 'success' | 'failed';
  position: { x: number; y: number };
}

interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  latency?: number;
}
```

#### ExecutionMonitor.tsx
Props interface:
- `events: WorkflowEvent[]` - Array of workflow events
- `maxEvents?: number` - Maximum events to display (default: 50)
- `autoScroll?: boolean` - Auto-scroll to latest event

Supporting type:
```typescript
interface WorkflowEvent {
  id: string;
  timestamp: Date;
  step: string;
  node?: string;
  message: string;
  status: 'info' | 'success' | 'warning' | 'error';
  latency?: number;
}
```

#### ToolResults.tsx
Props interface:
- `results: ToolResult[]` - Array of tool execution results
- `isLoading?: boolean` - Loading state
- `onRetry?: (toolId: string) => void` - Retry handler

Supporting type:
```typescript
interface ToolResult {
  id: string;
  toolName: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  output?: string;
  error?: string;
  latency?: number;
}
```

#### WorkflowDashboard.tsx
Props interface:
- `workflowId?: string` - Current workflow ID
- `status: 'idle' | 'running' | 'completed' | 'failed'` - Overall status
- `onStart?: () => void` - Start handler
- `onStop?: () => void` - Stop handler
- `onReset?: () => void` - Reset handler

## Code Template

```typescript
// WorkflowNode.tsx
import React from 'react';

interface WorkflowNodeProps {
  id: string;
  label: string;
  type: 'input' | 'process' | 'output' | 'tool';
  status: 'pending' | 'running' | 'success' | 'failed';
  latency?: number;
  isSelected?: boolean;
  onSelect?: (id: string) => void;
}

export const WorkflowNode: React.FC<WorkflowNodeProps> = ({
  id,
  label,
  type,
  status,
  latency,
  isSelected = false,
  onSelect,
}) => {
  // Status color mapping (Dracula theme)
  const statusColors = {
    pending: 'border-[#f1fa8c]',
    running: 'border-[#8be9fd] animate-pulse',
    success: 'border-[#50fa7b]',
    failed: 'border-[#ff5555]',
  };

  return (
    <div
      className={`
        p-4 rounded-lg border-2 cursor-pointer
        bg-[#282a36] text-[#f8f8f2]
        ${statusColors[status]}
        ${isSelected ? 'ring-2 ring-[#bd93f9]' : ''}
      `}
      onClick={() => onSelect?.(id)}
    >
      <div className="font-medium">{label}</div>
      {latency !== undefined && (
        <div className="text-sm text-[#6272a4]">{latency}ms</div>
      )}
    </div>
  );
};
```

## Acceptance Criteria

- [ ] All 5 component files created in correct directory
- [ ] All files use `.tsx` extension
- [ ] Each component has a Props interface defined
- [ ] Tailwind CSS used for all styling
- [ ] Dracula theme colors applied correctly
- [ ] All props have TypeScript types
- [ ] Components export as named exports
- [ ] No complex business logic (scaffold only)
- [ ] Files can be imported without TypeScript errors

## Notes

- Create the directory structure if it doesn't exist: `ryx/interfaces/web/src/components/`
- Use functional components only (no class components)
- Include JSDoc comments on complex interfaces
- Status indicators should use appropriate Dracula colors:
  - Pending: Yellow (#f1fa8c)
  - Running: Cyan (#8be9fd) with animation
  - Success: Green (#50fa7b)
  - Failed: Red (#ff5555)
