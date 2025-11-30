import { useState, useEffect, useCallback } from 'react';
import { ChatMessage } from '../types';
import { getStorageItem, setStorageItem } from '../utils/storage';

const MESSAGES_STORAGE_PREFIX = 'chat_messages_';

/**
 * Hook to manage message history per session with localStorage persistence
 */
export const useMessageHistory = (sessionId: string | null) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  // Load messages for current session
  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      return;
    }

    try {
      const storageKey = `${MESSAGES_STORAGE_PREFIX}${sessionId}`;
      const stored = getStorageItem<ChatMessage[]>(storageKey, []);
      setMessages(stored || []);
    } catch (error) {
      console.error('Failed to load message history from localStorage:', error);
      setMessages([]);
    }
  }, [sessionId]);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (!sessionId) return;

    try {
      const storageKey = `${MESSAGES_STORAGE_PREFIX}${sessionId}`;
      setStorageItem(storageKey, messages);
    } catch (error) {
      if (error instanceof Error && 'code' in error && error.code === 'QUOTA_EXCEEDED') {
        console.error('Storage quota exceeded. Some messages may not be saved.');
      } else {
        console.error('Failed to save message history to localStorage:', error);
      }
    }
  }, [messages, sessionId]);

  const addMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const updateMessage = useCallback((messageId: string, updates: Partial<ChatMessage>) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === messageId ? { ...msg, ...updates } : msg))
    );
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    if (sessionId) {
      try {
        const storageKey = `${MESSAGES_STORAGE_PREFIX}${sessionId}`;
        localStorage.removeItem(storageKey);
      } catch (error) {
        console.error('Failed to clear message history from localStorage:', error);
      }
    }
  }, [sessionId]);

  return {
    messages,
    setMessages,
    addMessage,
    updateMessage,
    clearMessages,
  };
};

