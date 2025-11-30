import React, { useEffect } from 'react';
import { setupGlobalErrorHandlers, registerErrorToastCallback } from '../utils/globalErrorHandler';
import { useToast } from './Toast';

/**
 * Global error handler component
 * Sets up error handlers and integrates with toast system
 * Should be placed at the root of the app
 */
const GlobalErrorHandler: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { showToast } = useToast();

  useEffect(() => {
    // Register toast callback for global error handler
    registerErrorToastCallback((message, type) => {
      showToast(message, type, 5000);
    });

    // Setup global error handlers
    setupGlobalErrorHandlers();

    // Cleanup on unmount
    return () => {
      // Note: We don't remove global handlers on unmount
      // as they should persist for the app lifetime
    };
  }, [showToast]);

  return <>{children}</>;
};

export default GlobalErrorHandler;

