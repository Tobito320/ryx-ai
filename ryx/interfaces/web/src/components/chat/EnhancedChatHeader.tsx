import React, { useState } from 'react';
import { ClipboardDocumentIcon, SparklesIcon } from '@heroicons/react/20/solid';
import ConnectionStatus from '../ConnectionStatus';
import { ConnectionStatus as ConnectionStatusType } from '../../types';
import { useToast } from '../Toast';

interface EnhancedChatHeaderProps {
  sessionName?: string;
  modelName: string;
  connectionStatus: ConnectionStatusType;
  messages?: Array<{ content: string; role: string }>;
  onSummarize?: () => void;
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

  const displayTitle = sessionName || `Chat: ${modelName}`;

  return (
    <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700/50 bg-gradient-to-r from-gray-800/95 to-gray-800/80 backdrop-blur-sm shadow-soft">
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <div className="flex-1 min-w-0">
          <h1 className="text-base font-semibold text-gray-100 truncate">
            Session: {displayTitle}
          </h1>
          {modelName && (
            <p className="text-xs text-gray-400 mt-0.5">{modelName}</p>
          )}
        </div>
        <ConnectionStatus status={connectionStatus} />
      </div>

      <div className="flex items-center gap-2 ml-4">
        <button
          onClick={handleCopyAll}
          disabled={isCopying || messages.length === 0}
          className="px-3 py-1.5 text-sm font-medium text-gray-300 hover:text-white bg-gray-700/50 hover:bg-gray-700 rounded-lg transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Copy all messages"
        >
          <ClipboardDocumentIcon className="w-4 h-4" />
          Copy All
        </button>
        <button
          onClick={handleSummarize}
          disabled={messages.length === 0}
          className="px-3 py-1.5 text-sm font-medium text-gray-300 hover:text-white bg-gray-700/50 hover:bg-gray-700 rounded-lg transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Summarize conversation"
        >
          <SparklesIcon className="w-4 h-4" />
          Summarize
        </button>
      </div>
    </div>
  );
};

export default EnhancedChatHeader;

