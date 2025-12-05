/**
 * @file ryx/interfaces/web/src/components/N8NLayout.tsx
 * @description N8N-style workflow layout for RyxHub.
 * 
 * Layout Structure (3-Panel Grid):
 * ┌──────────────────────────────────────────────────────────┐
 * │ 🟣 RYXHUB                          [⚙️ Settings] [👤]     │
 * ├──────────────────┬────────────────────┬─────────────────┤
 * │  WORKFLOWS       │ EXECUTION LIVE     │ RESULTS         │
 * │  (Sidebar)       │ (Center)           │ (Right)         │
 * └──────────────────┴────────────────────┴─────────────────┘
 * 
 * Features:
 * - Workflow sidebar on the left (collapsible)
 * - Execution monitor in the center
 * - Results panel on the right
 * - Chat panel (hidden, toggleable with Ctrl+K)
 * - Settings modal
 * - Dracula/Hyprland theme styling
 * - Keyboard shortcuts (1-5 for workflows, Ctrl+K for chat)
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Header } from './Header';
import { WorkflowSidebar, WorkflowTemplate } from './WorkflowSidebar';
import { LiveExecution } from './LiveExecution';
import { StepData } from './Step';
import { ResultsPanel, ResultItem } from './ResultsPanel';
import { ChatPanel, ChatMessage } from './ChatPanel';
import { SettingsModal, SettingsConfig } from './SettingsModal';
import { ToastContainer, useToast } from './Toast';
import { useModels } from '../hooks/useModels';

/**
 * Props for the N8NLayout component
 */
export interface N8NLayoutProps {
  /** Custom class name */
  className?: string;
}

// Default workflow templates
const DEFAULT_WORKFLOWS: WorkflowTemplate[] = [
  { name: 'Search', icon: '🔍', description: 'Web search + summarize', category: 'Research', shortcut: 1 },
  { name: 'Code Help', icon: '💻', description: 'Code analysis/suggestions', category: 'Development', shortcut: 2 },
  { name: 'File Mgmt', icon: '📁', description: 'Find/manage files', category: 'System', shortcut: 3 },
  { name: 'Browse', icon: '🌐', description: 'Open RyxSurf browser', category: 'Research', shortcut: 4 },
  { name: 'Chat', icon: '💬', description: 'Toggle chat panel', category: 'Chat', shortcut: 5 },
];

// Default settings
const DEFAULT_SETTINGS: SettingsConfig = {
  theme: 'dracula',
  modelTier: 'balanced',
  safetyLevel: 'normal',
  cacheEnabled: true,
};

/**
 * N8NLayout - The main N8N-style layout component
 */
export const N8NLayout: React.FC<N8NLayoutProps> = ({ className = '' }) => {
  const { toasts, showToast, dismissToast } = useToast();
  
  // State
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | undefined>();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [steps, setSteps] = useState<StepData[]>([]);
  const [results, setResults] = useState<ResultItem[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [totalLatency, setTotalLatency] = useState<number | undefined>();
  
  // Chat panel state
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  
  // Settings state
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState<SettingsConfig>(DEFAULT_SETTINGS);

  // Models state
  const { models } = useModels();
  const [loadingModel, setLoadingModel] = useState<string | null>(null);
  const [activeModel, setActiveModel] = useState<string | null>(null);

  // Handle workflow selection - use callback ref pattern to avoid infinite loops
  const showToastRef = React.useRef(showToast);
  showToastRef.current = showToast;
  
  const handleWorkflowClick = useCallback((workflow: WorkflowTemplate) => {
    // Special case: Chat workflow toggles chat panel
    if (workflow.name === 'Chat') {
      setChatOpen(prev => !prev);
      return;
    }
    
    setSelectedWorkflow(workflow.name);
    showToastRef.current(`Selected: ${workflow.name}`, 'info', 2000);
  }, []);

  // Handle command execution
  const handleExecute = useCallback(async () => {
    if (!inputValue.trim()) return;

    setIsExecuting(true);
    setTotalLatency(undefined);
    const startTime = Date.now();

    // Clear previous steps for new execution
    setSteps([]);

    // Add step helper
    const addStep = (step: number, action: string, status: StepData['status'], latency?: number) => {
      setSteps((prev) => {
        // Update existing step or add new one
        const existingIndex = prev.findIndex(s => s.step === step && s.action === action);
        if (existingIndex >= 0) {
          const updated = [...prev];
          updated[existingIndex] = {
            ...updated[existingIndex],
            status,
            latency: latency || updated[existingIndex].latency,
            timestamp: new Date(),
          };
          return updated;
        }
        return [...prev, {
          step,
          action,
          status,
          latency,
          timestamp: new Date(),
        }];
      });
    };

    try {
      // Step 1: Parse command
      addStep(1, 'Parsing command...', 'running');
      await new Promise((r) => setTimeout(r, 100));
      addStep(1, 'Command parsed', 'success', 50);

      // Step 2: Planning approach
      addStep(2, 'Planning approach...', 'running');
      await new Promise((r) => setTimeout(r, 150));
      addStep(2, 'Plan ready', 'success', 120);

      // Step 3: Execute workflow
      addStep(3, 'Executing workflow...', 'running');
      
      // Make actual API call with error handling
      let data: { result?: string } | undefined;
      try {
        const response = await fetch('/api/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: inputValue, workflow: selectedWorkflow }),
        });

        if (!response.ok) {
          const errorText = await response.text().catch(() => 'Unknown error');
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        data = await response.json();
      } catch (fetchError) {
        // Handle network errors gracefully
        addStep(3, `Network error: ${fetchError instanceof Error ? fetchError.message : 'Request failed'}`, 'error');
        showToastRef.current('Failed to connect to backend', 'error');
        setIsExecuting(false);
        return;
      }

      const executeLatency = Date.now() - startTime - 270;
      addStep(3, 'Workflow executed', 'success', executeLatency);

      // Step 4: Format results
      addStep(4, 'Formatting results...', 'running');
      await new Promise((r) => setTimeout(r, 80));
      addStep(4, 'Results formatted', 'success', 45);

      const totalTime = Date.now() - startTime;
      setTotalLatency(totalTime);

      // Add result
      setResults((prev) => [
        {
          id: `result-${Date.now()}`,
          type: 'text',
          title: `${selectedWorkflow || 'Query'}: ${inputValue.slice(0, 30)}${inputValue.length > 30 ? '...' : ''}`,
          content: data?.result || JSON.stringify(data, null, 2),
          metadata: { latency_ms: totalTime },
          timestamp: new Date(),
        },
        ...prev,
      ]);

      showToastRef.current('Execution complete', 'success', 2000);
      setInputValue('');
    } catch (error) {
      // Use a fixed step number for error since we're at the end of the sequence
      addStep(5, `Error: ${error}`, 'error');
      showToastRef.current('Execution failed', 'error');
    } finally {
      setIsExecuting(false);
    }
  }, [inputValue, selectedWorkflow]);

  // Handle key press for input
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleExecute();
    }
  };

  // Global keyboard shortcuts
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      // Ctrl+K: Toggle chat
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setChatOpen(prev => !prev);
      }
      // Ctrl+?: Show settings
      if ((e.ctrlKey || e.metaKey) && e.key === '?') {
        e.preventDefault();
        setSettingsOpen(true);
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  // Clear results
  const handleClearResults = useCallback(() => {
    setResults([]);
    setSteps([]);
    setTotalLatency(undefined);
  }, []);

  // Handle model loading
  const handleLoadModel = useCallback(async (modelPath: string) => {
    setLoadingModel(modelPath);

    try {
      const response = await fetch('/api/models/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name: modelPath }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        showToast(`Failed to load model: ${error.detail || 'Unknown error'}`, 'error');
        setLoadingModel(null);
        return;
      }

      const data = await response.json();
      setActiveModel(modelPath);
      setLoadingModel(null);

      const modelDisplayName = modelPath.replace('.gguf', '').replace(/-/g, ' ');
      showToast(`Model loaded: ${modelDisplayName}`, 'success');
    } catch (error) {
      showToast('Failed to load model', 'error');
      setLoadingModel(null);
    }
  }, [showToast]);

  // Handle chat message send
  const handleChatSend = useCallback(async (message: string) => {
    setChatLoading(true);
    
    // Add user message
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date(),
    };
    setChatMessages(prev => [...prev, userMessage]);

    // Simulate response (in real implementation, this would call the API)
    setTimeout(() => {
      const assistantMessage: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: `I received your message: "${message}". This is a placeholder response.`,
        timestamp: new Date(),
      };
      setChatMessages(prev => [...prev, assistantMessage]);
      setChatLoading(false);
    }, 1000);
  }, []);

  return (
    <div className={`flex flex-col h-screen bg-ryx-bg text-ryx-foreground overflow-hidden font-mono ${className}`}>
      {/* Header */}
      <Header
        workflowName={selectedWorkflow}
        onSettingsClick={() => setSettingsOpen(true)}
        onProfileClick={() => showToastRef.current('Profile coming soon!', 'info', 2000)}
      />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Workflows */}
        <WorkflowSidebar
          workflows={DEFAULT_WORKFLOWS}
          selectedWorkflow={selectedWorkflow}
          onWorkflowClick={handleWorkflowClick}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
          onNewWorkflow={() => showToastRef.current('New workflow coming soon!', 'info', 2000)}
        />

        {/* Center - Command Input & Execution */}
        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          {/* Command Input */}
          <div className="px-4 py-3 border-b border-ryx-border bg-ryx-bg-elevated">
            <div className="flex items-center gap-3">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type a command... (e.g., 'search docker', 'open hyprland config')"
                  className="w-full px-4 py-3 bg-ryx-current-line border border-ryx-border rounded-ryx text-ryx-foreground placeholder-ryx-text-muted focus:outline-none focus:border-ryx-accent focus:ring-1 focus:ring-ryx-accent font-mono text-sm transition-colors duration-150"
                  disabled={isExecuting}
                />
                {isExecuting && (
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-ryx-cyan animate-pulse">
                    ⏳
                  </span>
                )}
              </div>
              <button
                onClick={handleExecute}
                disabled={isExecuting || !inputValue.trim()}
                className={`px-6 py-3 rounded-ryx font-medium font-mono transition-colors duration-150 ${
                  isExecuting || !inputValue.trim()
                    ? 'bg-ryx-current-line text-ryx-text-muted cursor-not-allowed'
                    : 'bg-ryx-accent text-ryx-bg hover:bg-ryx-purple'
                }`}
              >
                {isExecuting ? '⏳ Running...' : '▶ Execute'}
              </button>
            </div>
          </div>

          {/* Main Content Grid - Execution & Results */}
          <div className="flex-1 flex overflow-hidden p-4 gap-4">
            {/* Execution Monitor */}
            <div className="flex-1 min-w-0">
              <LiveExecution
                steps={steps}
                isExecuting={isExecuting}
                totalLatency={totalLatency}
                title="Execution Live"
                className="h-full"
              />
            </div>

            {/* Results Panel */}
            <div className="w-80 lg:w-96 flex-shrink-0">
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

        {/* Right - Chat Panel (Hidden by default) */}
        <ChatPanel
          isOpen={chatOpen}
          onToggle={() => setChatOpen(false)}
          messages={chatMessages}
          onSendMessage={handleChatSend}
          isLoading={chatLoading}
        />
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        onSettingsChange={setSettings}
        models={models}
        activeModel={activeModel}
        loadingModel={loadingModel}
        onLoadModel={handleLoadModel}
      />

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} position="bottom-right" />
    </div>
  );
};

export default N8NLayout;
