import React, { useState, KeyboardEvent, forwardRef } from 'react';
import { PaperAirplaneIcon } from '@heroicons/react/20/solid';

interface EnhancedChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

/**
 * Enhanced chat input with better styling and micro-interactions
 */
const EnhancedChatInput = forwardRef<HTMLTextAreaElement, EnhancedChatInputProps>(({
  onSend,
  disabled = false,
  placeholder = 'Type your message...',
}, ref) => {
  const [input, setInput] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input);
      setInput('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="relative">
      <div
        className={`flex gap-3 items-end p-4 rounded-xl bg-gray-800/50 border transition-all duration-200 ${
          isFocused
            ? 'border-blue-500/50 shadow-glow-blue'
            : 'border-gray-700/50 hover:border-gray-600/50'
        }`}
      >
        <textarea
          ref={ref}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          disabled={disabled}
          placeholder={placeholder}
          rows={1}
          className="flex-1 bg-transparent text-gray-100 placeholder-gray-500 resize-none focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed text-sm leading-relaxed"
          style={{
            minHeight: '44px',
            maxHeight: '200px',
          }}
          onInput={(e) => {
            const target = e.target as HTMLTextAreaElement;
            target.style.height = 'auto';
            target.style.height = `${Math.min(target.scrollHeight, 200)}px`;
          }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          className={`px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-white font-medium transition-all duration-200 flex items-center gap-2 min-w-[90px] justify-center shadow-md hover:shadow-lg hover:scale-105 active:scale-100 ${
            input.trim() && !disabled ? 'animate-scale-in' : ''
          }`}
        >
          {disabled ? (
            <>
              <svg
                className="animate-spin h-4 w-4 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <span className="text-sm">Sending...</span>
            </>
          ) : (
            <>
              <PaperAirplaneIcon className="w-4 h-4" />
              <span className="text-sm">Send</span>
            </>
          )}
        </button>
      </div>
      <div className="mt-2 text-xs text-gray-500 px-1">
        Press <kbd className="px-1.5 py-0.5 bg-gray-700/50 rounded text-gray-400">Enter</kbd> to send,{' '}
        <kbd className="px-1.5 py-0.5 bg-gray-700/50 rounded text-gray-400">Shift + Enter</kbd> for new line
      </div>
    </div>
  );
});

EnhancedChatInput.displayName = 'EnhancedChatInput';

export default EnhancedChatInput;

