/**
 * Global error handler utilities
 * Provides robust error handling for API responses and network errors
 */

import { ApiError } from '../services/api';

/**
 * Check if a response is an HTML error page
 */
export const isHtmlErrorPage = async (response: Response): Promise<boolean> => {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('text/html')) {
    return true;
  }
  
  try {
    const text = await response.clone().text();
    return text.trim().startsWith('<!DOCTYPE') || text.trim().startsWith('<html');
  } catch {
    return false;
  }
};

/**
 * Extract error message from various error types
 */
export const getErrorMessage = (error: unknown): string => {
  if (error instanceof ApiError) {
    return error.message;
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  if (typeof error === 'string') {
    return error;
  }
  
  return 'An unknown error occurred';
};

/**
 * Check if error is a network/connection error
 */
export const isNetworkError = (error: unknown): boolean => {
  if (error instanceof ApiError) {
    return error.isNetworkError || error.isTimeout;
  }
  
  if (error instanceof TypeError) {
    return error.message.includes('fetch') || error.message.includes('network');
  }
  
  if (error instanceof DOMException) {
    return error.name === 'AbortError' || error.name === 'NetworkError';
  }
  
  return false;
};

/**
 * Format error for user display
 */
export const formatErrorForUser = (error: unknown): string => {
  const message = getErrorMessage(error);
  
  if (isNetworkError(error)) {
    if (message.includes('HTML error page')) {
      return 'Backend server is not responding. Please check if the API server is running at http://localhost:8000';
    }
    return 'Network error: Unable to connect to the backend. Please check your connection.';
  }
  
  return message;
};

