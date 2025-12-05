import React from 'react';
import { PlusIcon, ChatBubbleLeftRightIcon } from '@heroicons/react/20/solid';
import ConnectionStatus from '../ConnectionStatus';
import { ConnectionStatus as ConnectionStatusType, Session, Model, RAGFile } from '../../types';
import SessionItem from './SessionItem';
import ModelsSection from './ModelsSection';
import EnhancedRAGSection from './EnhancedRAGSection';
import SearchToggle from '../SearchToggle';
import SearchProviderSelector from '../SearchProviderSelector';
import { useSearch } from '../../contexts/SearchContext';

interface EnhancedSidebarProps {
  connectionStatus: ConnectionStatusType;
  sessions: Session[];
  selectedSession: Session | null;
  onSessionSelect: (sessionId: string) => void;
  onSessionCreate: () => void;
  onSessionDelete: (sessionId: string) => void;
  selectedModel?: string;
  onModelChange?: (model: string) => void;
  ragEnabled?: boolean;
  onRagToggle?: (enabled: boolean) => void;
  ragDirectoryPath?: string;
  onRagDirectoryPathChange?: (path: string) => void;
  ragFiles?: RAGFile[];
  onRagFileAdd?: () => void;
  onRagFileRemove?: (fileId: string) => void;
  models?: Model[];
  onModelNewChat?: (modelId: string) => void;
  onLoadModel?: (modelPath: string) => void;
  loadingModel?: string | null;
  activeModel?: string | null;
}

/**
 * Enhanced sidebar with modern UI, icons, and better organization
 */
const EnhancedSidebar: React.FC<EnhancedSidebarProps> = ({
  connectionStatus,
  sessions,
  selectedSession,
  onSessionSelect,
  onSessionCreate,
  onSessionDelete,
  selectedModel = 'gpt-4',
  onModelChange,
  ragEnabled = false,
  onRagToggle,
  ragDirectoryPath = '',
  onRagDirectoryPathChange,
  ragFiles = [],
  onRagFileAdd,
  onRagFileRemove,
  models = [],
  onModelNewChat,
  onLoadModel,
  loadingModel,
  activeModel,
}) => {
  const {
    searchEnabled,
    toggleSearch,
    selectedProvider,
    setSelectedProvider,
    providers,
    searchApiUrl,
    setSearchApiUrl,
  } = useSearch();

  // Use actual models from backend only
  const displayModels: Model[] = models;

  return (
    <aside className="w-64 bg-gradient-to-b from-gray-900 to-gray-800/95 backdrop-blur-sm p-4 flex flex-col h-full border-r border-gray-700/50 shadow-strong">
      {/* Connection Status */}
      <div className="mb-4 pb-3 border-b border-gray-700/50">
        <ConnectionStatus status={connectionStatus} />
      </div>

      {/* Sessions Section */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5">
            <ChatBubbleLeftRightIcon className="w-3.5 h-3.5 text-gray-400" />
            <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
              Sessions
            </h2>
          </div>
          <button
            onClick={onSessionCreate}
            className="px-2 py-1 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded text-xs text-white font-medium transition-all duration-200 flex items-center gap-1"
            title="Create new session"
          >
            <PlusIcon className="w-3 h-3" />
            New
          </button>
        </div>
        <div className="space-y-1.5 max-h-[200px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800/50 pr-1">
          {sessions.map((session) => (
            <SessionItem
              key={session.id}
              session={session}
              isSelected={selectedSession?.id === session.id}
              onSelect={() => onSessionSelect(session.id)}
              onDelete={() => onSessionDelete(session.id)}
            />
          ))}
        </div>
      </div>

      {/* Models Section - With Click-to-Load */}
      {displayModels.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center gap-1.5 mb-2">
            <svg className="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
            </svg>
            <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
              Models
            </h2>
            <span className="text-[10px] text-gray-500 font-normal">
              ({displayModels.filter(m => m.status === 'online' || m.status === 'loaded' || activeModel === m.path).length} active)
            </span>
          </div>
          <div className="space-y-1.5 max-h-[150px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800/50 pr-1">
            {displayModels.map((model) => (
              <div
                key={model.id}
                className="p-2 bg-gray-800/50 rounded hover:bg-gray-700/50 transition-colors cursor-pointer border border-gray-700/30 hover:border-gray-600/50"
                onClick={() => {
                  if (model.path && onLoadModel && loadingModel !== model.path) {
                    console.log('🔄 Loading model:', model.path);
                    onLoadModel(model.path);
                  }
                }}
                title={`Click to load ${model.name}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-medium truncate text-gray-200 flex-1">{model.name}</span>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {loadingModel === model.path ? (
                      <div className="flex items-center gap-1">
                        <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-pulse"></div>
                        <span className="text-[10px] text-yellow-400 font-medium">...</span>
                      </div>
                    ) : activeModel === model.path ? (
                      <div className="flex items-center gap-1">
                        <div className="w-1.5 h-1.5 bg-green-400 rounded-full"></div>
                      </div>
                    ) : (
                      <div className="w-1.5 h-1.5 bg-gray-500 rounded-full"></div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No models available message */}
      {displayModels.length === 0 && (
        <div className="mb-4 pb-3 border-b border-gray-700/50">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Models
          </h3>
          <div className="text-xs text-gray-500 text-center py-2">
            No models available
          </div>
        </div>
      )}

      {/* RAG Section */}
      <EnhancedRAGSection
        enabled={ragEnabled}
        onToggle={onRagToggle || (() => {})}
        directoryPath={ragDirectoryPath}
        onDirectoryPathChange={onRagDirectoryPathChange || (() => {})}
        files={ragFiles}
        onAddFile={onRagFileAdd || (() => {})}
        onRemoveFile={onRagFileRemove || (() => {})}
        disabled={connectionStatus === 'disconnected'}
      />

      {/* Search Options */}
      <div className="mb-4">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Search
        </h3>
        <div className="space-y-2">
          <SearchToggle
            enabled={searchEnabled}
            onToggle={toggleSearch}
            disabled={connectionStatus === 'disconnected'}
          />
          {searchEnabled && (
            <SearchProviderSelector
              providers={providers}
              selectedProvider={selectedProvider}
              onProviderChange={setSelectedProvider}
              disabled={connectionStatus === 'disconnected'}
              showCustomUrl={true}
              customUrl={searchApiUrl}
              onCustomUrlChange={setSearchApiUrl}
            />
          )}
        </div>
      </div>

      {/* Spacer */}
      <div className="flex-1" />
    </aside>
  );
};

export default EnhancedSidebar;
