import React, { useState, useRef, useEffect, useCallback } from 'react';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastContainer, useToast } from './components/Toast';
import EnhancedChatHeader from './components/chat/EnhancedChatHeader';
import EnhancedSidebar from './components/sidebar/EnhancedSidebar';
import EnhancedMessageBubble from './components/chat/EnhancedMessageBubble';
import EnhancedChatInput from './components/chat/EnhancedChatInput';
import N8NLayout from './components/N8NLayout';
import { useChat } from './hooks/useChat';
import { useSessions } from './hooks/useSessions';
import { useConnectionToast } from './hooks/useConnectionToast';
import { useRAGFiles } from './hooks/useRAGFiles';
import { useModels } from './hooks/useModels';
import { matchesShortcut, SHORTCUTS } from './utils/keyboard';
import './styles/dracula.css';

type ViewMode = 'chat' | 'workflow';

function App() {
  const { toasts, showToast, dismissToast } = useToast();
  
  // View mode - switch between chat and workflow views
  const [viewMode, setViewMode] = useState<ViewMode>('workflow');
  
  // CRITICAL: Store BOTH display name AND actual .gguf filename
  const [selectedModelDisplay, setSelectedModelDisplay] = useState('');
  const [selectedModelFile, setSelectedModelFile] = useState('');
  const [ragEnabled, setRagEnabled] = useState(false);
  const [ragDirectoryPath, setRagDirectoryPath] = useState('');
  
  // Model loading state
  const [loadingModel, setLoadingModel] = useState<string | null>(null);
  const [activeModel, setActiveModel] = useState<string | null>(null);

  // Session management
  const {
    sessions,
    selectedSession,
    selectedSessionId,
    createSession,
    deleteSession,
    selectSession,
    updateSessionName,
  } = useSessions();

  // RAG files management
  const { files: ragFiles, addFile: addRAGFile, removeFile: removeRAGFile } = useRAGFiles();

  // Models management
  const { models } = useModels();

  // Model loading function
  const handleLoadModel = useCallback(async (modelPath: string) => {
    setLoadingModel(modelPath);
    console.log('🔄 Loading model:', modelPath);
    
    try {
      const response = await fetch('/api/models/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name: modelPath }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        console.error('Failed to load model:', error);
        showToast(`Failed to load model: ${error.detail || 'Unknown error'}`, 'error');
        setLoadingModel(null);
        return;
      }

      const data = await response.json();
      console.log('✅ Model loaded:', data);
      
      // Store BOTH the .gguf filename (for backend) AND display name (for UI)
      setActiveModel(modelPath);
      setSelectedModelFile(modelPath); // This is what we send to backend
      setLoadingModel(null);
      
      // Extract display name
      const modelDisplayName = modelPath.replace('.gguf', '').replace(/-/g, ' ');
      setSelectedModelDisplay(modelDisplayName);
      
      showToast(`Model loaded: ${modelDisplayName}`, 'success');
    } catch (error) {
      console.error('Error loading model:', error);
      showToast('Failed to load model', 'error');
      setLoadingModel(null);
    }
  }, [showToast]);

  // Auto-load first available model on startup
  useEffect(() => {
    if (models.length > 0 && !activeModel && !loadingModel) {
      const firstModel = models.find(m => m.status === 'available');
      if (firstModel && firstModel.path) {
        console.log('🚀 Auto-loading first model:', firstModel.path);
        handleLoadModel(firstModel.path);
      }
    }
  }, [models, activeModel, loadingModel, handleLoadModel]);

  // Chat functionality - USE THE .gguf FILENAME, NOT DISPLAY NAME
  const {
    messages,
    sendMessage,
    connectionStatus,
    queue,
    retryFailedMessage,
  } = useChat(selectedSessionId, showToast, selectedModelFile, ragEnabled);

  // Manage persistent connection status toast (non-intrusive)
  useConnectionToast(connectionStatus);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [isSending, setIsSending] = useState(false);

  const handleSend = async (content: string) => {
    // Check if model is loaded
    if (!activeModel) {
      showToast('Please wait for a model to load or click on a model to load it', 'warning');
      return;
    }

    setIsSending(true);
    try {
      // Send the .gguf filename, not the display name
      await sendMessage(content, selectedSessionId || undefined, selectedModelFile, ragEnabled);
    } finally {
      setIsSending(false);
    }
  };

  const handleNewSession = useCallback(() => {
    if (!activeModel) {
      showToast('Please load a model first before creating a session', 'warning');
      return;
    }

    const newSession = createSession();
    // Use display name for UI
    if (newSession.id) {
      updateSessionName(
        newSession.id,
        `Chat: ${selectedModelDisplay}`
      );
    }
    showToast(`Created new session with ${selectedModelDisplay}`, 'success', 3000);
  }, [createSession, showToast, activeModel, selectedModelDisplay, updateSessionName]);

  const handleModelNewChat = useCallback((modelId: string) => {
    const model = models.find((m) => m.id === modelId);
    if (model && model.path) {
      // Load the model first
      handleLoadModel(model.path);
      // Then create session with that model
      const newSession = createSession();
      const modelDisplayName = model.path.replace('.gguf', '').replace(/-/g, ' ');
      if (newSession.id) {
        updateSessionName(
          newSession.id,
          `Chat: ${modelDisplayName}`
        );
      }
      showToast(`Started new chat with ${modelDisplayName}`, 'success', 3000);
    }
  }, [models, createSession, updateSessionName, showToast, handleLoadModel]);

  const handleRAGFileAdd = useCallback(() => {
    if (ragDirectoryPath.trim()) {
      const success = addRAGFile(ragDirectoryPath);
      if (success) {
        setRagDirectoryPath('');
        showToast('RAG file added', 'success', 2000);
      } else {
        showToast('File already added', 'warning', 2000);
      }
    }
  }, [ragDirectoryPath, addRAGFile, showToast]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ctrl/Cmd + K: New session
      if (matchesShortcut(event, SHORTCUTS.NEW_SESSION)) {
        event.preventDefault();
        handleNewSession();
      }
      // Ctrl/Cmd + L: Focus input
      if (matchesShortcut(event, SHORTCUTS.FOCUS_INPUT)) {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleNewSession]);

  const handleDeleteSession = (sessionId: string) => {
    if (sessions.length <= 1) {
      showToast('Cannot delete the last session', 'warning', 3000);
      return;
    }
    deleteSession(sessionId);
    showToast('Session deleted', 'info', 3000);
  };

  // Render N8N workflow view
  if (viewMode === 'workflow') {
    return (
      <ErrorBoundary>
        <div className="relative">
          {/* View Mode Toggle */}
          <button
            onClick={() => setViewMode('chat')}
            className="fixed top-4 right-4 z-50 px-4 py-2 bg-[#44475a] text-[#f8f8f2] rounded-lg hover:bg-[#6272a4] transition-colors flex items-center gap-2"
          >
            <span>💬</span>
            <span>Chat View</span>
          </button>
          <N8NLayout />
        </div>
      </ErrorBoundary>
    );
  }

  // Render traditional chat view
  return (
    <ErrorBoundary>
      <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-900 to-gray-800 text-gray-100 overflow-hidden">
        {/* View Mode Toggle */}
        <button
          onClick={() => setViewMode('workflow')}
          className="fixed top-4 right-4 z-50 px-4 py-2 bg-[#bd93f9] text-[#282a36] rounded-lg hover:bg-[#bd93f9]/80 transition-colors flex items-center gap-2"
        >
          <span>📊</span>
          <span>Workflow View</span>
        </button>

        {/* Enhanced Sidebar */}
        <EnhancedSidebar
          connectionStatus={connectionStatus}
          sessions={sessions}
          selectedSession={selectedSession}
          onSessionSelect={selectSession}
          onSessionCreate={handleNewSession}
          onSessionDelete={handleDeleteSession}
          selectedModel={selectedModelDisplay}
          onModelChange={(displayName) => {
            setSelectedModelDisplay(displayName);
            // Find corresponding .gguf file
            const model = models.find(m => m.name === displayName);
            if (model && model.path) {
              setSelectedModelFile(model.path);
            }
          }}
          ragEnabled={ragEnabled}
          onRagToggle={setRagEnabled}
          ragDirectoryPath={ragDirectoryPath}
          onRagDirectoryPathChange={setRagDirectoryPath}
          ragFiles={ragFiles}
          onRagFileAdd={handleRAGFileAdd}
          onRagFileRemove={removeRAGFile}
          models={models}
          onModelNewChat={handleModelNewChat}
          onLoadModel={handleLoadModel}
          loadingModel={loadingModel}
          activeModel={activeModel}
        />

        {/* Main Chat Area */}
        <main className="flex-1 flex flex-col overflow-hidden bg-gray-900/50 backdrop-blur-sm">
          {/* Enhanced Chat Header */}
          <EnhancedChatHeader
            sessionName={selectedSession?.name}
            modelName={selectedModelDisplay}
            connectionStatus={connectionStatus}
            messages={messages}
          />
          
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto py-6 scrollbar-thin scrollbar-thumb-gray-700/50 scrollbar-track-transparent">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center animate-fade-in">
                  <h2 className="text-3xl font-bold mb-3 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                    Welcome to AI Chat
                  </h2>
                  <p className="text-gray-400 mb-1">Start a conversation by typing a message below</p>
                  {selectedSession && (
                    <p className="text-sm mt-3 opacity-70 text-gray-500">
                      Session: {selectedSession.name}
                    </p>
                  )}
                  {!activeModel && loadingModel && (
                    <p className="text-sm mt-3 text-yellow-400">
                      ⏳ Loading model: {loadingModel}...
                    </p>
                  )}
                  {activeModel && (
                    <p className="text-sm mt-3 text-green-400">
                      ✅ Model ready: {selectedModelDisplay}
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <>
                {messages.map((message) => (
                  <EnhancedMessageBubble
                    key={message.id}
                    message={message}
                    onRetry={retryFailedMessage}
                    modelName={selectedModelDisplay}
                  />
                ))}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Enhanced Chat Input */}
          <div className="p-6 border-t border-gray-700/50 bg-gray-900/30 backdrop-blur-sm">
            {queue.length > 0 && (
              <div className="mb-3 text-sm text-yellow-400 flex items-center gap-2 animate-pulse">
                <span className="w-2 h-2 bg-yellow-400 rounded-full"></span>
                <span>
                  {queue.length} message{queue.length > 1 ? 's' : ''} queued
                </span>
              </div>
            )}
            <EnhancedChatInput
              ref={inputRef}
              onSend={handleSend}
              disabled={isSending || !activeModel}
              placeholder={
                !activeModel
                  ? 'Waiting for model to load...'
                  : connectionStatus === 'disconnected'
                  ? 'Backend unavailable. Message will be queued...'
                  : 'Type your message...'
              }
            />
          </div>
        </main>

        {/* Toast Notifications */}
        <ToastContainer toasts={toasts} onDismiss={dismissToast} position="bottom-right" />
      </div>
    </ErrorBoundary>
  );
}

export default App;
