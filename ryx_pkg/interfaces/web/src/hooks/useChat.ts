import { useCallback, useState } from 'react';
import { ChatMessage, ChatRequest, SearchResponse } from '../types';
import { apiService, ApiError } from '../services/api';
import { useMessageQueue } from './useMessageQueue';
import { useConnectionStatus } from './useConnectionStatus';
import { useMessageHistory } from './useMessageHistory';
import { useSearch } from '../contexts/SearchContext';

/**
 * Main chat hook that manages messages, sending, and error handling
 * Now integrated with message history and session management
 */
export const useChat = (
  sessionId: string | null,
  showToast: (message: string, type: 'success' | 'error' | 'warning' | 'info', duration?: number) => string,
  model?: string,
  ragEnabled?: boolean
) => {
  const { status: connectionStatus } = useConnectionStatus();
  const { messages, setMessages, addMessage, updateMessage } = useMessageHistory(sessionId);
  const { searchEnabled, selectedProvider, searchApiUrl } = useSearch();
  const [lastSearchResults, setLastSearchResults] = useState<SearchResponse | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const { queue, addToQueue, retryMessage } = useMessageQueue(
    connectionStatus,
    (message, aiResponse) => {
      // Message successfully sent from queue
      updateMessage(message.id, { status: 'sent' });
      // Add AI response if available
      if (aiResponse) {
        addMessage(aiResponse);
      }
      showToast('Message sent successfully', 'success', 3000);
    },
    (message, error) => {
      // Message failed to send
      updateMessage(message.id, { status: 'failed' });
      showToast(
        `Failed to send message: ${error.message}`,
        'error',
        5000
      );
    },
    () => ({
      sessionId: sessionId || undefined,
      model,
      ragEnabled,
    })
  );

  const sendMessage = useCallback(
    async (content: string, sessionId?: string, model?: string, ragEnabled?: boolean) => {
      if (!content.trim()) return;

      const userMessage: ChatMessage = {
        id: `msg-${Date.now()}-${Math.random()}`,
        role: 'user',
        content: content.trim(),
        timestamp: Date.now(),
        status: 'sending',
      };

      // Add user message to chat immediately
      addMessage(userMessage);

      // If disconnected, queue the message
      if (connectionStatus === 'disconnected') {
        userMessage.status = 'queued';
        addToQueue(userMessage);
        updateMessage(userMessage.id, { status: 'queued' });
        showToast('Backend unavailable. Message queued for sending.', 'warning', 4000);
        return;
      }

      let searchResults: SearchResponse | null = null;
      let searchContext = '';

      // Perform search if enabled
      if (searchEnabled) {
        setIsSearching(true);
        try {
          searchResults = await apiService.performSearch(
            content.trim(),
            selectedProvider,
            searchApiUrl
          );

          if (searchResults.results && searchResults.results.length > 0) {
            // Format search results as context
            searchContext = searchResults.results
              .slice(0, 5) // Use top 5 results
              .map((result, idx) => `[${idx + 1}] ${result.title}\n${result.snippet}\nSource: ${result.url}`)
              .join('\n\n');

            setLastSearchResults(searchResults);
            showToast(
              `Found ${searchResults.results.length} search results`,
              'success',
              3000
            );
          } else {
            showToast('No search results found', 'warning', 3000);
          }
        } catch (error) {
          // Search failed, but continue with chat anyway
          const searchError = error instanceof ApiError ? error : new ApiError('Search failed');
          
          if (searchError.isNetworkError || searchError.isTimeout) {
            showToast(
              'Search unavailable. Continuing without search results.',
              'warning',
              4000
            );
          } else {
            showToast(
              `Search error: ${searchError.message}. Continuing without search.`,
              'warning',
              4000
            );
          }
          // Continue with chat even if search fails
        } finally {
          setIsSearching(false);
        }
      }

      // Send chat message (with search context if available)
      try {
        // Format prompt with search context if available
        let prompt = content.trim();
        if (searchContext) {
          prompt = `Context from search:\n${searchContext}\n\nUser question: ${content.trim()}`;
        }

        const request: ChatRequest = {
          message: content.trim(), // Keep original message
          prompt: prompt, // Use prompt field for vLLM with search context
          sessionId,
          model,
          ragEnabled,
        };

        const response = await apiService.sendChatMessage(request);

        // Update user message status
        updateMessage(userMessage.id, { status: 'sent' });

        // Format AI response with search results if available
        let aiContent = response.message || response.response || '';
        if (searchResults && searchResults.results.length > 0) {
          const searchSection = `\n\n---\n**Search Results:**\n${searchResults.results
            .slice(0, 3)
            .map((r, i) => `${i + 1}. [${r.title}](${r.url})\n   ${r.snippet}`)
            .join('\n\n')}`;
          aiContent += searchSection;
        }

        // Add AI response
        const aiMessage: ChatMessage = {
          id: `msg-${Date.now()}-${Math.random()}`,
          role: 'assistant',
          content: aiContent,
          timestamp: Date.now(),
          status: 'sent',
        };

        addMessage(aiMessage);
      } catch (error) {
        // Handle error gracefully
        const apiError = error instanceof ApiError ? error : new ApiError('Unknown error');

        if (apiError.isNetworkError || apiError.isTimeout) {
          // Queue message for retry
          userMessage.status = 'queued';
          addToQueue(userMessage);
          updateMessage(userMessage.id, { status: 'queued' });
          showToast(
            'Connection lost. Message queued for retry.',
            'warning',
            4000
          );
        } else {
          // Server error - mark as failed
          updateMessage(userMessage.id, { status: 'failed' });
          showToast(
            `Failed to send message: ${apiError.message}`,
            'error',
            5000
          );
        }
      }
    },
    [connectionStatus, addToQueue, showToast, addMessage, updateMessage, searchEnabled, selectedProvider, searchApiUrl]
  );

  const retryFailedMessage = useCallback(
    async (messageId: string) => {
      await retryMessage(messageId);
    },
    [retryMessage]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, [setMessages]);

  return {
    messages,
    sendMessage,
    connectionStatus,
    queue,
    retryFailedMessage,
    clearMessages,
    lastSearchResults,
    isSearching,
  };
};
