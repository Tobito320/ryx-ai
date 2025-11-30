import React from 'react';
import { ChatMessage } from '../types';

interface MessageBubbleProps {
  message: ChatMessage;
  onRetry?: (messageId: string) => void;
}

/**
 * Message bubble component for displaying chat messages
 * Shows user and AI messages with distinct styling
 */
const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onRetry }) => {
  const isUser = message.role === 'user';
  const isFailed = message.status === 'failed';
  const isQueued = message.status === 'queued';
  const isSending = message.status === 'sending';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 px-4`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 shadow-sm ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-sm'
            : 'bg-gray-700/80 text-gray-100 rounded-bl-sm border border-gray-600/50'
        }`}
      >
        <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
          {message.content}
        </p>
        <div className="flex items-center justify-between gap-2 mt-2 pt-2 border-t border-current/10">
          <span className={`text-xs ${isUser ? 'text-blue-100' : 'text-gray-400'}`}>
            {new Date(message.timestamp).toLocaleTimeString([], { 
              hour: '2-digit', 
              minute: '2-digit' 
            })}
          </span>
          <div className="flex items-center gap-2">
            {isSending && (
              <span className={`text-xs ${isUser ? 'text-blue-100' : 'text-gray-400'}`}>
                Sending...
              </span>
            )}
            {isQueued && (
              <span className={`text-xs ${isUser ? 'text-blue-100' : 'text-yellow-400'}`}>
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
      </div>
    </div>
  );
};

export default MessageBubble;

