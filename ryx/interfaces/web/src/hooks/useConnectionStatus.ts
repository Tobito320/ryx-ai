import { useState, useEffect, useCallback } from 'react';
import { ConnectionStatus as ConnectionStatusType } from '../types';
import { apiService } from '../services/api';

/**
 * Hook to monitor backend connection status
 * Periodically checks backend health and updates connection status
 */
export const useConnectionStatus = (checkInterval: number = 5000) => {
  const [status, setStatus] = useState<ConnectionStatusType>('connecting');
  const [lastChecked, setLastChecked] = useState<Date>(new Date());

  const checkConnection = useCallback(async () => {
    try {
      // Use a timeout to prevent hanging
      const healthCheckPromise = apiService.healthCheck();
      const timeoutPromise = new Promise<boolean>((resolve) => {
        setTimeout(() => resolve(false), 3000);
      });
      
      const isHealthy = await Promise.race([healthCheckPromise, timeoutPromise]);
      setStatus(isHealthy ? 'connected' : 'disconnected');
      setLastChecked(new Date());
    } catch (error) {
      // Silently handle errors - don't crash, just mark as disconnected
      setStatus('disconnected');
      setLastChecked(new Date());
      // Don't log to console in production to avoid noise
      if (process.env.NODE_ENV === 'development') {
        console.debug('Health check failed (expected when backend is down):', error);
      }
    }
  }, []);

  useEffect(() => {
    // Initial check
    checkConnection();

    // Set up periodic health checks
    const interval = setInterval(() => {
      checkConnection();
    }, checkInterval);

    return () => clearInterval(interval);
  }, [checkConnection, checkInterval]);

  // Manual refresh function
  const refresh = useCallback(() => {
    setStatus('connecting');
    checkConnection();
  }, [checkConnection]);

  return {
    status,
    lastChecked,
    refresh,
    checkConnection,
  };
};

