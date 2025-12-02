/**
 * @file ryx/interfaces/web/src/components/ChatPanel.tsx
 * @description Hidden chat panel that can be toggled with Ctrl+K.
 * 
 * Features:
 * - Minimal chat UI
 * - Toggle with Ctrl+K or "💬 Chat" button
 * - Compact 200-280px width when open
 * - Slide-in animation
 * - Input field at bottom
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';

/**
 * Chat message interface
 */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

/**
 * Props for the ChatPanel component
 */
export interface ChatPanelProps {
  /** Whether the panel is visible */
  isOpen: boolean;
  /** Callback to toggle panel visibility */
  onToggle: () => void;
  /** Array of chat messages */
  messages?: ChatMessage[];
  /** Callback when a message is sent */
  onSendMessage?: (message: string) => void;
  /** Whether the chat is processing */
  isLoading?: boolean;
  /** Custom class name */
  className?: string;
}

/**
 * ChatPanel - A collapsible chat sidebar
 */
export const ChatPanel: React.FC<ChatPanelProps> = ({
  isOpen,
  onToggle,
  messages = [],
  onSendMessage,
  isLoading = false,
  className = '',
}) => {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when panel opens - only once, without re-triggering
  const hasFocusedRef = useRef(false);
  useEffect(() => {
    if (isOpen && !hasFocusedRef.current) {
      hasFocusedRef.current = true;
      const timer = setTimeout(() => inputRef.current?.focus(), 200);
      return () => clearTimeout(timer);
    }
    if (!isOpen) {
      hasFocusedRef.current = false;
    }
  }, [isOpen]);

  // Handle message send
  const handleSend = useCallback(() => {
    if (!inputValue.trim() || isLoading) return;
    
    onSendMessage?.(inputValue.trim());
    setInputValue('');
  }, [inputValue, isLoading, onSendMessage]);

  // Handle key press
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    if (e.key === 'Escape') {
      onToggle();
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className={`
        w-64 sm:w-72 flex flex-col
        bg-ryx-bg-elevated border-l border-ryx-border
        animate-fade-in
        ${className}
      `}
      role="complementary"
      aria-label="Chat panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-ryx-border">
        <h3 className="text-sm font-semibold text-ryx-foreground font-mono flex items-center gap-2">
          <span className="text-ryx-accent">💬</span>
          Chat
        </h3>
        <button
          onClick={onToggle}
          className="text-ryx-text-muted hover:text-ryx-foreground transition-colors p-1"
          title="Close chat (Esc)"
          aria-label="Close chat panel"
        >
          ✕
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 ryx-scrollbar">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-ryx-text-muted text-sm text-center font-mono">
              No messages yet.<br />
              <span className="text-xs opacity-70">Press Ctrl+K to toggle</span>
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`
                p-2 rounded-ryx text-sm font-mono
                ${msg.role === 'user'
                  ? 'bg-ryx-accent/20 text-ryx-foreground ml-4'
                  : 'bg-ryx-current-line text-ryx-text mr-4'
                }
              `}
            >
              <p className="break-words">{msg.content}</p>
              <span className="text-[10px] text-ryx-text-muted mt-1 block">
                {msg.timestamp.toLocaleTimeString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-ryx-border">
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message..."
            disabled={isLoading}
            className="
              w-full px-3 py-2 pr-10
              bg-ryx-bg border border-ryx-border rounded-ryx
              text-sm font-mono text-ryx-foreground
              placeholder-ryx-text-muted
              focus:outline-none focus:border-ryx-accent focus:ring-1 focus:ring-ryx-accent
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors duration-150
            "
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
            className="
              absolute right-2 top-1/2 -translate-y-1/2
              text-ryx-accent hover:text-ryx-purple
              disabled:text-ryx-text-muted disabled:cursor-not-allowed
              transition-colors
            "
            title="Send message"
            aria-label="Send message"
          >
            {isLoading ? (
              <span className="animate-spin">⏳</span>
            ) : (
              <span>➤</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;
