/**
 * @file ryx/interfaces/web/src/components/WorkflowSidebar.tsx
 * @description N8N-style workflow sidebar with collapsible workflow templates.
 * 
 * Features:
 * - Collapsible workflow categories
 * - Click to execute workflows
 * - Categories: Search, Code, Files, Browse, Chat
 * - Dracula theme styling
 */

import React, { useState } from 'react';

/**
 * Workflow template interface
 */
export interface WorkflowTemplate {
  name: string;
  icon: string;
  description: string;
  category: string;
}

/**
 * Props for the WorkflowSidebar component
 */
export interface WorkflowSidebarProps {
  /** Array of workflow templates */
  workflows: WorkflowTemplate[];
  /** Currently selected workflow */
  selectedWorkflow?: string;
  /** Callback when a workflow is clicked */
  onWorkflowClick: (workflow: WorkflowTemplate) => void;
  /** Callback to create a new workflow */
  onNewWorkflow?: () => void;
  /** Whether the sidebar is collapsed */
  collapsed?: boolean;
  /** Callback to toggle collapsed state */
  onToggleCollapse?: () => void;
  /** Custom class name */
  className?: string;
}

// Default workflow templates
const DEFAULT_WORKFLOWS: WorkflowTemplate[] = [
  { name: 'Search', icon: '🔍', description: 'Web search with SearxNG', category: 'Research' },
  { name: 'Code Help', icon: '💻', description: 'Get coding assistance', category: 'Development' },
  { name: 'File Mgmt', icon: '📁', description: 'Find and open files', category: 'System' },
  { name: 'Browse', icon: '🌐', description: 'Browse and scrape pages', category: 'Research' },
  { name: 'Chat', icon: '💬', description: 'General conversation', category: 'Chat' },
];

// Category icons
const CATEGORY_ICONS: Record<string, string> = {
  Research: '🔬',
  Development: '⚙️',
  System: '🖥️',
  Chat: '💬',
};

/**
 * WorkflowSidebar - A collapsible sidebar with workflow templates
 */
export const WorkflowSidebar: React.FC<WorkflowSidebarProps> = ({
  workflows = DEFAULT_WORKFLOWS,
  selectedWorkflow,
  onWorkflowClick,
  onNewWorkflow,
  collapsed = false,
  onToggleCollapse,
  className = '',
}) => {
  // Track which categories are expanded
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(['Research', 'Development', 'System', 'Chat'])
  );

  // Group workflows by category
  const workflowsByCategory = workflows.reduce((acc, workflow) => {
    const cat = workflow.category || 'Other';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(workflow);
    return acc;
  }, {} as Record<string, WorkflowTemplate[]>);

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  if (collapsed) {
    return (
      <div
        className={`w-16 bg-[#21222c] border-r border-[#6272a4] flex flex-col items-center py-4 ${className}`}
      >
        {/* Expand button */}
        <button
          onClick={onToggleCollapse}
          className="w-10 h-10 flex items-center justify-center rounded-lg bg-[#44475a] hover:bg-[#6272a4] transition-colors mb-4"
          title="Expand sidebar"
        >
          <span className="text-[#f8f8f2]">→</span>
        </button>

        {/* Quick workflow icons */}
        {workflows.slice(0, 5).map((workflow) => (
          <button
            key={workflow.name}
            onClick={() => onWorkflowClick(workflow)}
            className={`w-10 h-10 flex items-center justify-center rounded-lg mb-2 transition-colors ${
              selectedWorkflow === workflow.name
                ? 'bg-[#bd93f9] text-[#282a36]'
                : 'bg-[#44475a] hover:bg-[#6272a4] text-[#f8f8f2]'
            }`}
            title={workflow.name}
          >
            <span>{workflow.icon}</span>
          </button>
        ))}
      </div>
    );
  }

  return (
    <div
      className={`w-64 bg-[#21222c] border-r border-[#6272a4] flex flex-col h-full ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-[#6272a4]">
        <h2 className="text-[#bd93f9] font-bold text-lg flex items-center gap-2">
          <span>🟣</span>
          <span>Workflows</span>
        </h2>
        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="w-8 h-8 flex items-center justify-center rounded hover:bg-[#44475a] transition-colors"
            title="Collapse sidebar"
          >
            <span className="text-[#6272a4]">←</span>
          </button>
        )}
      </div>

      {/* Workflow List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 dracula-scrollbar">
        {Object.entries(workflowsByCategory).map(([category, categoryWorkflows]) => (
          <div key={category} className="mb-3">
            {/* Category Header */}
            <button
              onClick={() => toggleCategory(category)}
              className="w-full flex items-center gap-2 px-2 py-2 text-sm font-medium text-[#6272a4] hover:text-[#f8f8f2] transition-colors rounded hover:bg-[#44475a]/30"
            >
              <span
                className={`transform transition-transform ${
                  expandedCategories.has(category) ? 'rotate-90' : ''
                }`}
              >
                ▶
              </span>
              <span>{CATEGORY_ICONS[category] || '📂'}</span>
              <span>{category}</span>
              <span className="ml-auto text-xs text-[#6272a4]">
                {categoryWorkflows.length}
              </span>
            </button>

            {/* Workflow Items */}
            {expandedCategories.has(category) && (
              <div className="ml-4 mt-1 space-y-1">
                {categoryWorkflows.map((workflow) => (
                  <button
                    key={workflow.name}
                    onClick={() => onWorkflowClick(workflow)}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-all ${
                      selectedWorkflow === workflow.name
                        ? 'bg-[#bd93f9]/20 border border-[#bd93f9] text-[#f8f8f2]'
                        : 'hover:bg-[#44475a] text-[#f8f8f2]'
                    }`}
                  >
                    <span className="text-lg">{workflow.icon}</span>
                    <div className="text-left">
                      <div className="text-sm font-medium">{workflow.name}</div>
                      <div className="text-xs text-[#6272a4] truncate">
                        {workflow.description}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* New Workflow Button */}
      {onNewWorkflow && (
        <div className="p-3 border-t border-[#6272a4]">
          <button
            onClick={onNewWorkflow}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-[#50fa7b]/20 text-[#50fa7b] rounded-lg hover:bg-[#50fa7b]/30 transition-colors font-medium"
          >
            <span>+</span>
            <span>New Workflow</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default WorkflowSidebar;
