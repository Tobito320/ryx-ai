/**
 * @file ryx/interfaces/web/src/components/N8NLayout.tsx
 * @description N8N-style workflow layout for Ryx AI.
 * 
 * Features:
 * - Workflow sidebar on the left
 * - Execution monitor in the center
 * - Results panel on the right/bottom
 * - Dracula theme styling
 * - No traditional chat bubbles
 */

import React, { useState, useCallback } from 'react';
import { WorkflowSidebar, WorkflowTemplate } from './WorkflowSidebar';
import { ExecutionMonitor, DisplayEvent } from './ExecutionMonitor';
import { ResultsPanel, ResultItem } from './ResultsPanel';
import { ToastContainer, useToast } from './Toast';

/**
 * Props for the N8NLayout component
 */
export interface N8NLayoutProps {
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

/**
 * N8NLayout - The main N8N-style layout component
 */
export const N8NLayout: React.FC<N8NLayoutProps> = ({ className = '' }) => {
  const { toasts, showToast, dismissToast } = useToast();
  
  // State
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | undefined>();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [events, setEvents] = useState<DisplayEvent[]>([]);
  const [results, setResults] = useState<ResultItem[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);

  // Handle workflow selection
  const handleWorkflowClick = useCallback((workflow: WorkflowTemplate) => {
    setSelectedWorkflow(workflow.name);
    showToast(`Selected: ${workflow.name}`, 'info', 2000);
  }, [showToast]);

  // Handle command execution
  const handleExecute = useCallback(async () => {
    if (!inputValue.trim()) return;

    setIsExecuting(true);
    const startTime = Date.now();

    // Add step events
    const addEvent = (step: number, message: string, status: DisplayEvent['status'], latency?: number) => {
      setEvents((prev) => [
        ...prev,
        {
          id: `evt-${Date.now()}-${step}`,
          timestamp: new Date(),
          step: step.toString(),
          message,
          status,
          latency,
        },
      ]);
    };

    try {
      // Simulate execution steps
      addEvent(1, 'Parsing command...', 'running');
      await new Promise((r) => setTimeout(r, 100));
      addEvent(1, 'Command parsed', 'success', 50);

      addEvent(2, 'Executing workflow...', 'running');
      
      // Make actual API call
      const response = await fetch('/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: inputValue }),
      });

      const data = await response.json();
      const totalLatency = Date.now() - startTime;

      addEvent(2, 'Workflow complete', 'success', totalLatency - 50);

      // Add result
      setResults((prev) => [
        {
          id: `result-${Date.now()}`,
          type: 'text',
          title: `Executed: ${inputValue.slice(0, 30)}${inputValue.length > 30 ? '...' : ''}`,
          content: data.result || JSON.stringify(data, null, 2),
          metadata: { latency_ms: totalLatency },
          timestamp: new Date(),
        },
        ...prev,
      ]);

      showToast('Execution complete', 'success', 2000);
      setInputValue('');
    } catch (error) {
      addEvent(2, `Error: ${error}`, 'error');
      showToast('Execution failed', 'error');
    } finally {
      setIsExecuting(false);
    }
  }, [inputValue, showToast]);

  // Handle key press
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleExecute();
    }
  };

  // Clear results
  const handleClearResults = useCallback(() => {
    setResults([]);
    setEvents([]);
  }, []);

  return (
    <div className={`flex h-screen bg-[#282a36] text-[#f8f8f2] overflow-hidden ${className}`}>
      {/* Workflow Sidebar */}
      <WorkflowSidebar
        workflows={DEFAULT_WORKFLOWS}
        selectedWorkflow={selectedWorkflow}
        onWorkflowClick={handleWorkflowClick}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-[#6272a4] bg-[#21222c]">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold flex items-center gap-2">
              <span className="text-[#bd93f9]">🟣</span>
              <span>RYX</span>
            </h1>
            {selectedWorkflow && (
              <span className="text-sm text-[#6272a4]">
                / {selectedWorkflow}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button className="px-3 py-1.5 text-sm bg-[#44475a] rounded hover:bg-[#6272a4] transition-colors">
              ⚙️ Settings
            </button>
            <button className="px-3 py-1.5 text-sm bg-[#50fa7b]/20 text-[#50fa7b] rounded hover:bg-[#50fa7b]/30 transition-colors">
              + New
            </button>
          </div>
        </header>

        {/* Command Input */}
        <div className="px-6 py-4 border-b border-[#6272a4] bg-[#21222c]/50">
          <div className="flex items-center gap-3">
            <div className="flex-1 relative">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type a command... (e.g., 'search docker', 'open hyprland config')"
                className="w-full px-4 py-3 bg-[#44475a] border border-[#6272a4] rounded-lg text-[#f8f8f2] placeholder-[#6272a4] focus:outline-none focus:border-[#bd93f9] focus:ring-1 focus:ring-[#bd93f9] font-mono"
                disabled={isExecuting}
              />
              {isExecuting && (
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[#8be9fd] animate-pulse">
                  ⏳
                </span>
              )}
            </div>
            <button
              onClick={handleExecute}
              disabled={isExecuting || !inputValue.trim()}
              className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                isExecuting || !inputValue.trim()
                  ? 'bg-[#44475a] text-[#6272a4] cursor-not-allowed'
                  : 'bg-[#bd93f9] text-[#282a36] hover:bg-[#bd93f9]/80'
              }`}
            >
              {isExecuting ? '⏳ Running...' : '▶ Execute'}
            </button>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="flex-1 flex overflow-hidden p-4 gap-4">
          {/* Execution Monitor */}
          <div className="flex-1 min-w-0">
            <ExecutionMonitor
              events={events}
              maxEvents={50}
              title="Execution Live"
              className="h-full"
            />
          </div>

          {/* Results Panel */}
          <div className="w-96 flex-shrink-0">
            <ResultsPanel
              results={results}
              loading={isExecuting}
              title="Results"
              onClear={handleClearResults}
              className="h-full"
            />
          </div>
        </div>
      </div>

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} position="bottom-right" />
    </div>
  );
};

export default N8NLayout;
