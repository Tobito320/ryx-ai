import { useEffect, useRef } from 'react';
import { ConnectionStatus } from '../types';
import { useToast } from '../components/Toast';

/**
 * Hook to manage persistent connection status toast
 * Shows a small, non-intrusive toast when backend is unavailable
 * Auto-dismisses when connection is restored
 */
export const useConnectionToast = (connectionStatus: ConnectionStatus) => {
  const { showPersistentToast, updateToast, dismissToast } = useToast();
  const toastIdRef = useRef<string | null>(null);

  useEffect(() => {
    // Show persistent toast when disconnected
    if (connectionStatus === 'disconnected' || connectionStatus === 'reconnecting') {
      const message = connectionStatus === 'reconnecting' 
        ? 'Backend unavailable. Retrying to connect...'
        : 'Backend unavailable. Retrying to connect...';

      if (toastIdRef.current) {
        // Update existing toast
        updateToast(toastIdRef.current, { message, type: 'warning' });
      } else {
        // Create new persistent toast
        const id = showPersistentToast(message, 'warning');
        toastIdRef.current = id;
      }
    }
    // Dismiss toast when connected
    else if (connectionStatus === 'connected' && toastIdRef.current) {
      dismissToast(toastIdRef.current);
      toastIdRef.current = null;
    }
    // Handle connecting state
    else if (connectionStatus === 'connecting' && !toastIdRef.current) {
      const id = showPersistentToast('Connecting to backend...', 'info');
      toastIdRef.current = id;
    }
  }, [connectionStatus, showPersistentToast, updateToast, dismissToast]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (toastIdRef.current) {
        dismissToast(toastIdRef.current);
      }
    };
  }, [dismissToast]);
};

