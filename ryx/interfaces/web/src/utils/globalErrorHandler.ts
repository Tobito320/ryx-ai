/**
 * Global error handler for unhandled errors and promise rejections
 * Ensures the app never crashes, even when backend is completely down
 */

let errorToastCallback: ((message: string, type: 'error' | 'warning' | 'info') => void) | null = null;

/**
 * Register a callback to show error toasts
 * Called from App component to integrate with toast system
 */
export const registerErrorToastCallback = (
  callback: (message: string, type: 'error' | 'warning' | 'info') => void
) => {
  errorToastCallback = callback;
};

/**
 * Show error notification (non-blocking)
 */
const showError = (message: string, type: 'error' | 'warning' | 'info' = 'error') => {
  if (errorToastCallback) {
    errorToastCallback(message, type);
  } else {
    // Fallback to console if toast system not ready
    console.error('[Global Error Handler]:', message);
  }
};

/**
 * Handle unhandled JavaScript errors
 */
export const setupGlobalErrorHandlers = () => {
  // Handle unhandled JavaScript errors
  window.addEventListener('error', (event) => {
    event.preventDefault();
    
    const error = event.error || new Error(event.message || 'Unknown error');
    const errorMessage = error.message || 'An unexpected error occurred';
    
    // Don't show errors for missing resources (images, etc.)
    if (event.target && (event.target as HTMLElement).tagName) {
      return;
    }
    
    showError(
      `Application error: ${errorMessage}. The app will continue to work.`,
      'error'
    );
    
    console.error('Unhandled error:', error);
  });

  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    event.preventDefault();
    
    const error = event.reason;
    let errorMessage = 'An unexpected error occurred';
    
    if (error instanceof Error) {
      errorMessage = error.message;
    } else if (typeof error === 'string') {
      errorMessage = error;
    } else if (error && typeof error === 'object' && 'message' in error) {
      errorMessage = String(error.message);
    }
    
    // Check if it's a network/API error
    if (
      errorMessage.includes('fetch') ||
      errorMessage.includes('network') ||
      errorMessage.includes('Failed to fetch') ||
      errorMessage.includes('NetworkError') ||
      errorMessage.includes('500') ||
      errorMessage.includes('Connection')
    ) {
      showError(
        'Backend unavailable. The app will continue to work offline.',
        'warning'
      );
    } else {
      showError(
        `Error: ${errorMessage}. The app will continue to work.`,
        'error'
      );
    }
    
    console.error('Unhandled promise rejection:', error);
  });

  // Handle fetch errors globally (as a fallback)
  const originalFetch = window.fetch;
  window.fetch = async (...args) => {
    try {
      const response = await originalFetch(...args);
      
      // Check for HTML error pages
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('text/html') && !response.ok) {
        const text = await response.clone().text();
        if (text.includes('<!DOCTYPE') || text.includes('<html')) {
          // This is an HTML error page, not JSON
          // Don't throw here - let the API service handle it
        }
      }
      
      return response;
    } catch (error) {
      // Only log, don't throw - let the calling code handle it
      if (error instanceof TypeError && error.message.includes('fetch')) {
        console.warn('Network error caught by global handler:', error);
      }
      throw error; // Re-throw so calling code can handle it
    }
  };
};

/**
 * Safe async wrapper - ensures errors never crash the app
 */
export const safeAsync = async <T>(
  fn: () => Promise<T>,
  errorMessage?: string,
  fallback?: T
): Promise<T | undefined> => {
  try {
    return await fn();
  } catch (error) {
    const message = errorMessage || (error instanceof Error ? error.message : 'Unknown error');
    showError(message, 'warning');
    console.error('Safe async error:', error);
    return fallback;
  }
};

