import React from 'react';
import { ChatMessage } from '../../types';
import Avatar from '../ui/Avatar';
import MessageMetrics from './MessageMetrics';

interface EnhancedMessageBubbleProps {
  message: ChatMessage;
  onRetry?: (messageId: string) => void;
  modelName?: string;
}

/**
 * Enhanced message bubble with avatars, better styling, and performance metrics
 */
const EnhancedMessageBubble: React.FC<EnhancedMessageBubbleProps> = ({
  message,
  onRetry,
  modelName = 'AI',
}) => {
  const isUser = message.role === 'user';
  const isFailed = message.status === 'failed';
  const isQueued = message.status === 'queued';
  const isSending = message.status === 'sending';

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-6 px-6 animate-fade-in`}>
      <div className={`flex gap-3 max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Avatar */}
        <div className="flex-shrink-0">
          <Avatar
            name={isUser ? 'You' : modelName}
            size="md"
            className={isUser ? '' : 'ring-2 ring-blue-500/30'}
          />
        </div>

        {/* Message Content */}
        <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
          {/* Label */}
          <div className={`text-xs font-medium mb-1.5 px-1 ${isUser ? 'text-gray-400' : 'text-gray-400'}`}>
            {isUser ? 'You' : modelName}
          </div>

          {/* Bubble */}
          <div
            className={`rounded-2xl px-4 py-3 shadow-medium ${
              isUser
                ? 'bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-br-sm'
                : 'bg-gray-800/90 text-gray-100 rounded-bl-sm border border-gray-700/50 backdrop-blur-sm'
            } ${isFailed ? 'ring-2 ring-red-500/50' : ''}`}
          >
            <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
              {message.content}
            </p>

            {/* Status & Time */}
            <div className="flex items-center justify-between gap-3 mt-2 pt-2 border-t border-current/10">
              <span className={`text-xs ${isUser ? 'text-blue-100/80' : 'text-gray-400'}`}>
                {formatTime(message.timestamp)}
              </span>
              <div className="flex items-center gap-2">
                {isSending && (
                  <span className={`text-xs ${isUser ? 'text-blue-100/80' : 'text-gray-400'}`}>
                    Sending...
                  </span>
                )}
                {isQueued && (
                  <span className={`text-xs ${isUser ? 'text-blue-100/80' : 'text-yellow-400'}`}>
                    Queued
                  </span>
                )}
                {isFailed && onRetry && (
                  <button
                    onClick={() => onRetry(message.id)}
                    className={`text-xs underline hover:no-underline transition-opacity ${
                      isUser ? 'text-blue-100 hover:text-white' : 'text-red-400 hover:text-red-300'
                    }`}
                  >
                    Retry
                  </button>
                )}
              </div>
            </div>

            {/* Performance Metrics (only for assistant messages) */}
            {!isUser && message.performanceMetrics && (
              <MessageMetrics metrics={message.performanceMetrics} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default EnhancedMessageBubble;

