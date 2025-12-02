import { useState, useEffect, useCallback } from 'react';
import { ChatMessage, ChatRequest } from '../types';
import { apiService } from '../services/api';
import { getStorageItem, setStorageItem } from '../utils/storage';

const QUEUE_STORAGE_KEY = 'chat_message_queue';

/**
 * Hook to manage message queue for offline messages
 * Persists queued messages to localStorage and auto-retries when connection is restored
 */
export const useMessageQueue = (
  connectionStatus: 'connected' | 'disconnected' | 'connecting' | 'reconnecting',
  onMessageSent?: (message: ChatMessage, aiResponse?: ChatMessage) => void,
  onMessageFailed?: (message: ChatMessage, error: Error) => void,
  getSessionContext?: () => { sessionId?: string; model?: string; ragEnabled?: boolean }
) => {
  const [queue, setQueue] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  // Load queue from localStorage on mount
  useEffect(() => {
    try {
      const stored = getStorageItem<ChatMessage[]>(QUEUE_STORAGE_KEY, []);
      if (stored) {
        setQueue(stored);
      }
    } catch (error) {
      console.error('Failed to load message queue from localStorage:', error);
    }
  }, []);

  // Save queue to localStorage whenever it changes
  useEffect(() => {
    try {
      setStorageItem(QUEUE_STORAGE_KEY, queue);
    } catch (error) {
      if (error instanceof Error && 'code' in error && error.code === 'QUOTA_EXCEEDED') {
        console.error('Storage quota exceeded. Message queue may not be saved.');
      } else {
        console.error('Failed to save message queue to localStorage:', error);
      }
    }
  }, [queue]);

  const addToQueue = useCallback((message: ChatMessage) => {
    setQueue((prev) => [...prev, message]);
  }, []);

  const removeFromQueue = useCallback((messageId: string) => {
    setQueue((prev) => prev.filter((msg) => msg.id !== messageId));
  }, []);

  // Declare processQueue before it's used in useEffect
  const processQueue = useCallback(async () => {
    if (isProcessing || queue.length === 0 || connectionStatus !== 'connected') {
      return;
    }

    setIsProcessing(true);

    // Process messages one at a time
    for (const message of [...queue]) {
      if (message.status === 'queued' || message.status === 'failed') {
        try {
          // Update message status to sending
          setQueue((prev) =>
            prev.map((msg) =>
              msg.id === message.id ? { ...msg, status: 'sending' as const } : msg
            )
          );

          const context = getSessionContext?.() || {};
          const request: ChatRequest = {
            message: message.content,
            sessionId: context.sessionId,
            model: context.model,
            ragEnabled: context.ragEnabled,
          };

          const response = await apiService.sendChatMessage(request);

          // Create AI response message
          const aiMessage: ChatMessage = {
            id: `msg-${Date.now()}-${Math.random()}`,
            role: 'assistant',
            content: response.message,
            timestamp: Date.now(),
            status: 'sent',
          };

          // Message sent successfully
          removeFromQueue(message.id);
          onMessageSent?.(message, aiMessage);

          // Add AI response to chat if needed
          // You might want to handle this in your chat component
        } catch (error) {
          // Mark message as failed
          setQueue((prev) =>
            prev.map((msg) =>
              msg.id === message.id
                ? { ...msg, status: 'failed' as const }
                : msg
            )
          );

          onMessageFailed?.(
            message,
            error instanceof Error ? error : new Error('Unknown error')
          );
        }
      }
    }

    setIsProcessing(false);
  }, [isProcessing, queue, connectionStatus, removeFromQueue, onMessageSent, onMessageFailed, getSessionContext]);

  // Process queue when connection is restored (now processQueue is declared)
  useEffect(() => {
    if (connectionStatus === 'connected' && queue.length > 0 && !isProcessing) {
      processQueue();
    }
  }, [connectionStatus, queue.length, isProcessing, processQueue]);

  const retryMessage = useCallback(
    async (messageId: string) => {
      const message = queue.find((msg) => msg.id === messageId);
      if (!message) return;

      if (connectionStatus === 'connected') {
        // Process immediately if connected
        await processQueue();
      } else {
        // Just mark as queued if not connected
        setQueue((prev) =>
          prev.map((msg) =>
            msg.id === messageId ? { ...msg, status: 'queued' as const } : msg
          )
        );
      }
    },
    [queue, connectionStatus, processQueue]
  );

  const clearQueue = useCallback(() => {
    setQueue([]);
    try {
      localStorage.removeItem(QUEUE_STORAGE_KEY);
    } catch (error) {
      console.error('Failed to clear message queue from localStorage:', error);
    }
  }, []);

  return {
    queue,
    addToQueue,
    removeFromQueue,
    retryMessage,
    clearQueue,
    processQueue,
    isProcessing,
  };
};
