import React from 'react';
import ConnectionStatus from './ConnectionStatus';
import { ConnectionStatus as ConnectionStatusType } from '../types';
import { Session } from '../types';
import SearchToggle from './SearchToggle';
import SearchProviderSelector from './SearchProviderSelector';
import RAGSection from './RAGSection';
import { useSearch } from '../contexts/SearchContext';

interface SidebarProps {
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
}

/**
 * Sidebar component with sessions, model selector, and RAG options
 * Now integrated with session management
 */
const Sidebar: React.FC<SidebarProps> = ({
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
}) => {
  const models = ['gpt-4', 'gpt-3.5-turbo', 'claude-3', 'llama-2'];
  const {
    searchEnabled,
    toggleSearch,
    selectedProvider,
    setSelectedProvider,
    providers,
    searchApiUrl,
    setSearchApiUrl,
  } = useSearch();

  return (
    <aside className="w-72 bg-gray-800/95 backdrop-blur-sm p-4 flex flex-col h-full border-r border-gray-700/50 shadow-lg">
      {/* Connection Status */}
      <div className="mb-6 pb-4 border-b border-gray-700/50">
        <ConnectionStatus status={connectionStatus} />
      </div>

      {/* Sessions Section */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-100">Sessions</h2>
          <button
            onClick={onSessionCreate}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-md text-sm text-white font-medium transition-all duration-150 shadow-sm hover:shadow"
            title="Create new session"
          >
            + New
          </button>
        </div>
        <div className="space-y-1.5 max-h-[300px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
          {sessions.map((session) => (
            <div
              key={session.id}
              className={`p-2.5 rounded-lg cursor-pointer flex items-center justify-between transition-all duration-150 ${
                selectedSession?.id === session.id
                  ? 'bg-blue-600/20 border border-blue-500/50 text-white shadow-sm'
                  : 'bg-gray-700/50 text-gray-300 hover:bg-gray-700 border border-transparent'
              }`}
              onClick={() => onSessionSelect(session.id)}
            >
              <div className="flex-1 min-w-0">
                <div className="truncate font-medium text-sm">{session.name}</div>
                <div className="text-xs opacity-60 truncate mt-0.5">
                  {new Date(session.lastActive).toLocaleDateString()}
                </div>
              </div>
              {sessions.length > 1 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onSessionDelete(session.id);
                  }}
                  className="ml-2 p-1 text-red-400 hover:text-red-300 hover:bg-red-500/20 rounded text-sm flex-shrink-0 transition-colors"
                  title="Delete session"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Model Selector */}
      <div className="mb-6 pb-4 border-b border-gray-700/50">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Model
        </h3>
        <select
          value={selectedModel}
          onChange={(e) => onModelChange?.(e.target.value)}
          disabled={connectionStatus === 'disconnected'}
          className="w-full px-3 py-2 text-sm rounded-lg bg-gray-700/80 border border-gray-600/50 text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {models.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
      </div>

      {/* RAG Options */}
      <div className="mb-6 pb-4 border-b border-gray-700/50">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
          RAG Options
        </h3>
        <RAGSection
          enabled={ragEnabled}
          onToggle={onRagToggle || (() => {})}
          directoryPath={ragDirectoryPath}
          onDirectoryPathChange={onRagDirectoryPathChange}
          disabled={connectionStatus === 'disconnected'}
        />
      </div>

      {/* Search Options */}
      <div className="mb-6">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Search
        </h3>
        <div className="space-y-3">
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

      {/* Spacer to push content to top */}
      <div className="flex-1" />
    </aside>
  );
};

export default Sidebar;
