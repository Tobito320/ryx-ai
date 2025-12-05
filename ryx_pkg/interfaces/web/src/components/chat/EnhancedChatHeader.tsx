import React, { useState } from 'react';
import { ClipboardDocumentIcon, SparklesIcon, TrashIcon } from '@heroicons/react/20/solid';
import ConnectionStatus from '../ConnectionStatus';
import { ConnectionStatus as ConnectionStatusType, ResponseStyle } from '../../types';
import { useToast } from '../Toast';

interface EnhancedChatHeaderProps {
  sessionName?: string;
  modelName: string;
  connectionStatus: ConnectionStatusType;
  messages?: Array<{ content: string; role: string }>;
  onSummarize?: () => void;
  onClearChat?: () => void;
  style?: ResponseStyle;
  onStyleChange?: (style: ResponseStyle) => void;
}

/**
 * Enhanced chat header with session title, actions, and connection status
 */
const EnhancedChatHeader: React.FC<EnhancedChatHeaderProps> = ({
  sessionName,
  modelName,
  connectionStatus,
  messages = [],
  onSummarize,
  onClearChat,
  style = 'concise',
  onStyleChange,
}) => {
  const { showToast } = useToast();
  const [isCopying, setIsCopying] = useState(false);

  const handleCopyAll = async () => {
    if (messages.length === 0) {
      showToast('No messages to copy', 'info', 2000);
      return;
    }

    setIsCopying(true);
    try {
      const text = messages
        .map((msg) => `${msg.role === 'user' ? 'You' : modelName}: ${msg.content}`)
        .join('\n\n');
      await navigator.clipboard.writeText(text);
      showToast('All messages copied to clipboard', 'success', 2000);
    } catch (error) {
      showToast('Failed to copy messages', 'error', 2000);
    } finally {
      setIsCopying(false);
    }
  };

  const handleSummarize = () => {
    if (onSummarize) {
      onSummarize();
    } else {
      showToast('Summarize feature coming soon', 'info', 2000);
    }
  };

  const handleClearChat = () => {
    if (messages.length === 0) {
      showToast('No messages to clear', 'info', 2000);
      return;
    }

    if (window.confirm('Are you sure you want to clear all messages in this session?')) {
      if (onClearChat) {
        onClearChat();
        showToast('Chat cleared successfully', 'success', 2000);
      }
    }
  };

  const displayTitle = sessionName || `Chat: ${modelName}`;

  const styleOptions: Array<{value: ResponseStyle; label: string; description: string}> = [
    { value: 'concise', label: 'Concise', description: 'Brief, to-the-point responses' },
    { value: 'balanced', label: 'Balanced', description: 'Moderate detail and explanation' },
    { value: 'explanatory', label: 'Explanatory', description: 'Detailed with examples' },
    { value: 'technical', label: 'Technical', description: 'In-depth technical details' },
  ];

  return (
    <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700/50 bg-gradient-to-r from-gray-800/95 to-gray-800/80 backdrop-blur-sm shadow-soft">
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <div className="flex-1 min-w-0">
          <h1 className="text-base font-semibold text-gray-100 truncate">
            Session: {displayTitle}
          </h1>
          <div className="flex items-center gap-3 mt-0.5">
            {modelName && (
              <p className="text-xs text-gray-400">{modelName}</p>
            )}
            {onStyleChange && (
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-gray-500">•</span>
                <select
                  value={style}
                  onChange={(e) => onStyleChange(e.target.value as ResponseStyle)}
                  className="text-xs bg-gray-700/50 text-gray-300 border border-gray-600/50 rounded px-2 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 hover:bg-gray-700"
                  title={styleOptions.find(s => s.value === style)?.description}
                >
                  {styleOptions.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>
        <ConnectionStatus status={connectionStatus} />
      </div>

      <div className="flex items-center gap-2 ml-4">
        <button
          onClick={handleClearChat}
          disabled={messages.length === 0}
          className="px-3 py-1.5 text-sm font-medium text-gray-300 hover:text-white bg-gray-700/50 hover:bg-gray-700 rounded-lg transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-red-600/50"
          title="Clear all messages"
        >
          <TrashIcon className="w-4 h-4" />
          Clear
        </button>
        <button
          onClick={handleCopyAll}
          disabled={isCopying || messages.length === 0}
          className="px-3 py-1.5 text-sm font-medium text-gray-300 hover:text-white bg-gray-700/50 hover:bg-gray-700 rounded-lg transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Copy all messages"
        >
          <ClipboardDocumentIcon className="w-4 h-4" />
          Copy All
        </button>
      </div>
    </div>
  );
};

export default EnhancedChatHeader;

