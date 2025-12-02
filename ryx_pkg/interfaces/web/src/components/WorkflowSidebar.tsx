/**
 * @file ryx/interfaces/web/src/components/WorkflowSidebar.tsx
 * @description N8N-style workflow sidebar with collapsible workflow templates.
 * 
 * Features:
 * - Collapsible workflow categories
 * - Click to execute workflows
 * - Keyboard shortcuts (1-5 for workflow selection)
 * - Categories: Search, Code, Files, Browse, Chat
 * - Dracula/Hyprland theme styling
 */

import React, { useState, useEffect, useCallback } from 'react';

/**
 * Workflow template interface
 */
export interface WorkflowTemplate {
  name: string;
  icon: string;
  description: string;
  category: string;
  shortcut?: number; // 1-5 keyboard shortcut
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

// Default workflow templates with keyboard shortcuts
const DEFAULT_WORKFLOWS: WorkflowTemplate[] = [
  { name: 'Search', icon: '🔍', description: 'Web search + summarize', category: 'Research', shortcut: 1 },
  { name: 'Code Help', icon: '💻', description: 'Code analysis/suggestions', category: 'Development', shortcut: 2 },
  { name: 'File Mgmt', icon: '📁', description: 'Find/manage files', category: 'System', shortcut: 3 },
  { name: 'Browse', icon: '🌐', description: 'Open RyxSurf browser', category: 'Research', shortcut: 4 },
  { name: 'Chat', icon: '💬', description: 'Toggle chat panel', category: 'Chat', shortcut: 5 },
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

  // Keyboard shortcuts for workflow selection (1-5)
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    // Only handle 1-5 keys when not focused on an input or editable element
    const target = e.target as HTMLElement;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return;

    const key = parseInt(e.key, 10);
    if (key >= 1 && key <= 5) {
      const workflow = workflows.find(w => w.shortcut === key);
      if (workflow) {
        e.preventDefault();
        onWorkflowClick(workflow);
      }
    }
  }, [workflows, onWorkflowClick]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  if (collapsed) {
    return (
      <div
        className={`w-16 bg-ryx-bg-elevated border-r border-ryx-border flex flex-col items-center py-4 ${className}`}
      >
        {/* Expand button */}
        <button
          onClick={onToggleCollapse}
          className="w-10 h-10 flex items-center justify-center rounded-ryx bg-ryx-current-line hover:bg-ryx-bg-hover transition-colors mb-4"
          title="Expand sidebar"
          aria-label="Expand sidebar"
        >
          <span className="text-ryx-foreground">→</span>
        </button>

        {/* Quick workflow icons */}
        {workflows.slice(0, 5).map((workflow, index) => (
          <button
            key={workflow.name}
            onClick={() => onWorkflowClick(workflow)}
            className={`w-10 h-10 flex items-center justify-center rounded-ryx mb-2 transition-all duration-150 relative group ${
              selectedWorkflow === workflow.name
                ? 'bg-ryx-accent text-ryx-bg'
                : 'bg-ryx-current-line hover:bg-ryx-bg-hover text-ryx-foreground'
            }`}
            title={`${workflow.name} (${index + 1})`}
            aria-label={workflow.name}
          >
            <span>{workflow.icon}</span>
            {/* Shortcut badge */}
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-ryx-accent text-ryx-bg text-[10px] font-bold rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
              {index + 1}
            </span>
          </button>
        ))}
      </div>
    );
  }

  return (
    <div
      className={`w-64 bg-ryx-bg-elevated border-r border-ryx-border flex flex-col h-full ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-ryx-border">
        <h2 className="text-ryx-accent font-bold text-lg font-mono flex items-center gap-2">
          <span>🟣</span>
          <span>Workflows</span>
        </h2>
        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="w-8 h-8 flex items-center justify-center rounded hover:bg-ryx-current-line transition-colors"
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
          >
            <span className="text-ryx-text-muted">←</span>
          </button>
        )}
      </div>

      {/* Search hint */}
      <div className="px-4 py-2 border-b border-ryx-border/50">
        <p className="text-xs text-ryx-text-muted font-mono">
          Press <kbd className="px-1 bg-ryx-current-line rounded">1-5</kbd> to select
        </p>
      </div>

      {/* Workflow List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 ryx-scrollbar">
        {Object.entries(workflowsByCategory).map(([category, categoryWorkflows]) => (
          <div key={category} className="mb-3">
            {/* Category Header */}
            <button
              onClick={() => toggleCategory(category)}
              className="w-full flex items-center gap-2 px-2 py-2 text-sm font-medium text-ryx-text-muted hover:text-ryx-foreground transition-colors rounded hover:bg-ryx-current-line/30 font-mono"
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
              <span className="ml-auto text-xs text-ryx-text-muted">
                {categoryWorkflows.length}
              </span>
            </button>

            {/* Workflow Items - N8N Node Style */}
            {expandedCategories.has(category) && (
              <div className="ml-2 mt-1 space-y-1">
                {categoryWorkflows.map((workflow) => (
                  <button
                    key={workflow.name}
                    onClick={() => onWorkflowClick(workflow)}
                    className={`workflow-node w-full ${
                      selectedWorkflow === workflow.name ? 'active' : ''
                    }`}
                    tabIndex={0}
                  >
                    <div className="node-icon">{workflow.icon}</div>
                    <span className="node-label">{workflow.name}</span>
                    {workflow.shortcut && (
                      <span className="node-shortcut">{workflow.shortcut}</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* New Workflow Button */}
      {onNewWorkflow && (
        <div className="p-3 border-t border-ryx-border">
          <button
            onClick={onNewWorkflow}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[var(--accent-dim)] text-[var(--accent)] rounded-lg hover:bg-[var(--accent)]/20 transition-colors font-medium text-sm"
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
