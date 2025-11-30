/**
 * API Service with robust error handling
 * Handles network errors, timeouts, and connection issues gracefully
 */

import { ChatMessage, ChatRequest, ChatResponse, SearchResponse, SearchProvider } from '../types';

// Re-export types for backward compatibility
export type { ChatMessage, ChatRequest, ChatResponse };

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public isNetworkError: boolean = false,
    public isTimeout: boolean = false
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Check if backend is reachable
 */
export const checkBackendHealth = async (baseUrl: string = ''): Promise<boolean> => {
  try {
    const response = await fetch(`${baseUrl}/api/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(3000), // 3 second timeout
    });
    return response.ok;
  } catch (error) {
    return false;
  }
};

/**
 * Main API service class
 */
export class ApiService {
  private baseUrl: string;
  private defaultTimeout: number;

  constructor(baseUrl: string = '', defaultTimeout: number = 30000) {
    this.baseUrl = baseUrl;
    this.defaultTimeout = defaultTimeout;
  }

  /**
   * Check if response is HTML (error page) instead of JSON
   */
  private async checkIfHtmlResponse(response: Response): Promise<boolean> {
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('text/html')) {
      return true;
    }
    
    // Also check the first few bytes
    const text = await response.clone().text();
    return text.trim().startsWith('<!DOCTYPE') || text.trim().startsWith('<html');
  }

    /**
   * Send chat message to backend
   * Returns response or throws ApiError
   */
  async sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.defaultTimeout);

    try {
      // Format request for llama.cpp backend (uses "message" field)
      const requestBody = {
        message: request.message,
        model: request.model,
        session_id: request.sessionId,
        max_tokens: 512,
        temperature: 0.7
      };

      // Use proxy if baseUrl is empty (development mode)
      const apiUrl = this.baseUrl || '/api';
      
      const response = await fetch(`${apiUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Check if we got HTML instead of JSON (backend error page)
      if (await this.checkIfHtmlResponse(response)) {
        throw new ApiError(
          'Backend returned HTML error page. Is the API server running?',
          response.status || 500,
          true
        );
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.detail || errorData.message || `Server error: ${response.status}`,
          response.status,
          false
        );
      }

      const data = await response.json();
      
      // Handle backend response format
      const chatResponse: ChatResponse = {
        message: data.response || data.message || '',
        response: data.response || data.message,
        sessionId: data.session_id || data.sessionId || request.sessionId,
        error: data.error,
      };

      return chatResponse;
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof ApiError) {
        throw error;
      }

      // Handle network errors
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new ApiError('Request timeout', undefined, false, true);
      }

      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new ApiError(
          'Network error: Unable to reach backend',
          undefined,
          true
        );
      }

      // Unknown error
      throw new ApiError(
        error instanceof Error ? error.message : 'Unknown error occurred',
        undefined,
        true
      );
    }
  }


  /**
   * Perform search query using selected search provider
   * Returns search results or throws ApiError
   */
  async performSearch(
    query: string,
    provider: SearchProvider,
    customApiUrl?: string | null
  ): Promise<SearchResponse> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout for search

    try {
      // Determine search API URL
      const searchUrl = customApiUrl || this.getSearchProviderUrl(provider);

      // Try SearXNG format first (most common)
      let response: Response;

      if (provider === 'searxng' || !customApiUrl) {
        // SearXNG format: GET request with query parameter
        const searchParams = new URLSearchParams({ q: query });
        response = await fetch(`${searchUrl}/search?${searchParams}`, {
          method: 'GET',
          signal: controller.signal,
        });
      } else {
        // Generic search API format: POST with JSON
        response = await fetch(`${searchUrl}/search`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query,
            provider,
          }),
          signal: controller.signal,
        });
      }

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.message || `Search API error: ${response.status}`,
          response.status,
          false
        );
      }

      const data = await response.json();
      
      // Handle different response formats
      let searchResponse: SearchResponse;
      
      if (data.results && Array.isArray(data.results)) {
        // Standard format
        searchResponse = {
          results: data.results.map((r: any) => ({
            title: r.title || r.name || '',
            url: r.url || r.link || '',
            snippet: r.snippet || r.content || r.description || '',
            source: r.source || provider,
          })),
          query: data.query || query,
          provider: data.provider || provider,
          error: data.error,
        };
      } else if (Array.isArray(data)) {
        // Array format
        searchResponse = {
          results: data.map((r: any) => ({
            title: r.title || r.name || '',
            url: r.url || r.link || '',
            snippet: r.snippet || r.content || r.description || '',
            source: r.source || provider,
          })),
          query,
          provider,
        };
      } else {
        // Fallback: create empty response
        searchResponse = {
          results: [],
          query,
          provider,
          error: 'Unexpected response format',
        };
      }

      return searchResponse;
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof ApiError) {
        throw error;
      }

      // Handle network errors
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new ApiError('Search request timeout', undefined, false, true);
      }

      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new ApiError(
          'Network error: Unable to reach search API',
          undefined,
          true
        );
      }

      // Unknown error
      throw new ApiError(
        error instanceof Error ? error.message : 'Unknown search error occurred',
        undefined,
        true
      );
    }
  }

  /**
   * Get default API URL for a search provider
   */
  private getSearchProviderUrl(provider: SearchProvider): string {
    const providerUrls: Record<SearchProvider, string> = {
      searxng: process.env.REACT_APP_SEARXNG_URL || 'http://localhost:8080',
      duckduckgo: process.env.REACT_APP_DUCKDUCKGO_URL || 'https://api.duckduckgo.com',
      google: process.env.REACT_APP_GOOGLE_SEARCH_URL || 'https://www.googleapis.com/customsearch/v1',
      bing: process.env.REACT_APP_BING_SEARCH_URL || 'https://api.bing.microsoft.com/v7.0/search',
      brave: process.env.REACT_APP_BRAVE_SEARCH_URL || 'https://api.search.brave.com/res/v1/web/search',
    };

    return providerUrls[provider] || providerUrls.searxng; // Fallback to SearXNG
  }

  /**
   * Health check endpoint
   * Never throws - always returns false on error to prevent crashes
   */
  async healthCheck(): Promise<boolean> {
    try {
      // Use proxy if baseUrl is empty (development mode)
      const apiUrl = this.baseUrl || '/api';
      
      // Use a shorter timeout for health checks
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000); // 2 second timeout
      
      try {
        const response = await fetch(`${apiUrl}/health`, {
          method: 'GET',
          signal: controller.signal,
          // Don't throw on network errors
          cache: 'no-cache',
        });
        
        clearTimeout(timeoutId);
        
        // Check if we got HTML instead of JSON (backend error page)
        if (await this.checkIfHtmlResponse(response)) {
          return false;
        }
        
        return response.ok;
      } catch (fetchError) {
        clearTimeout(timeoutId);
        // Silently return false - backend is down
        return false;
      }
    } catch (error) {
      // Catch any unexpected errors and return false
      // Never throw from health check
      return false;
    }
  }
}

// Export singleton instance
// In development, if REACT_APP_API_URL is not set, use empty string to leverage proxy
// In production, use the full URL
export const apiService = new ApiService(
  process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'production' ? '' : '')
);

