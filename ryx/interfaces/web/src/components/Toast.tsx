import React, { useEffect } from 'react';
import { Toast, ToastType } from '../types';

// Re-export types for backward compatibility
export type { Toast, ToastType };

interface ToastProps {
  toast: Toast;
  onDismiss: (id: string) => void;
}

/**
 * Individual toast notification component
 */
const ToastItem: React.FC<ToastProps> = ({ toast, onDismiss }) => {
  useEffect(() => {
    // Only auto-dismiss if duration is set and > 0
    // duration === undefined or 0 means persistent
    if (toast.duration !== undefined && toast.duration > 0) {
      const timer = setTimeout(() => {
        onDismiss(toast.id);
      }, toast.duration);

      return () => clearTimeout(timer);
    }
  }, [toast.id, toast.duration, onDismiss]);

  const getToastStyles = () => {
    // Smaller, more compact styles for persistent toasts
    const baseStyles = 'flex items-center justify-between px-3 py-2 rounded-lg shadow-lg border text-sm min-w-[280px] max-w-sm';
    
    switch (toast.type) {
      case 'success':
        return `${baseStyles} bg-green-800/95 border-green-700 text-green-100 backdrop-blur-sm`;
      case 'error':
        return `${baseStyles} bg-red-800/95 border-red-700 text-red-100 backdrop-blur-sm`;
      case 'warning':
        return `${baseStyles} bg-yellow-800/95 border-yellow-700 text-yellow-100 backdrop-blur-sm`;
      case 'info':
        return `${baseStyles} bg-blue-800/95 border-blue-700 text-blue-100 backdrop-blur-sm`;
      default:
        return `${baseStyles} bg-gray-800/95 border-gray-700 text-gray-100 backdrop-blur-sm`;
    }
  };

  const getIcon = () => {
    switch (toast.type) {
      case 'success':
        return '✓';
      case 'error':
        return '✕';
      case 'warning':
        return '⚠';
      case 'info':
        return 'ℹ';
      default:
        return '';
    }
  };

  return (
    <div className={getToastStyles()}>
      <div className="flex items-center gap-3">
        <span className="text-xl font-bold">{getIcon()}</span>
        <p className="flex-1">{toast.message}</p>
      </div>
      <button
        onClick={() => onDismiss(toast.id)}
        className="ml-4 text-current opacity-70 hover:opacity-100 transition-opacity"
        aria-label="Dismiss notification"
      >
        ✕
      </button>
    </div>
  );
};

interface ToastContainerProps {
  toasts: Toast[];
  onDismiss: (id: string) => void;
  position?: 'top-left' | 'top-right' | 'top-center' | 'bottom-left' | 'bottom-right' | 'bottom-center';
}

/**
 * Toast container that displays all active toasts
 * Positioned at bottom-right by default (less intrusive)
 */
export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onDismiss, position = 'bottom-right' }) => {
  if (toasts.length === 0) return null;

  const getPositionClasses = () => {
    switch (position) {
      case 'top-left': return 'top-4 left-4';
      case 'top-center': return 'top-4 left-1/2 -translate-x-1/2';
      case 'top-right': return 'top-4 right-4';
      case 'bottom-left': return 'bottom-4 left-4';
      case 'bottom-center': return 'bottom-4 left-1/2 -translate-x-1/2';
      case 'bottom-right':
      default: return 'bottom-4 right-4';
    }
  };

  return (
    <div className={`fixed ${getPositionClasses()} z-50 flex flex-col gap-2 pointer-events-none`}>
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto animate-slide-in">
          <ToastItem toast={toast} onDismiss={onDismiss} />
        </div>
      ))}
    </div>
  );
};

/**
 * Hook to manage toast notifications
 * Usage: const { showToast, toasts, dismissToast } = useToast();
 */
export const useToast = () => {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const showToast = React.useCallback((message: string, type: ToastType = 'info', duration: number = 5000) => {
    const id = `toast-${Date.now()}-${Math.random()}`;
    const newToast: Toast = {
      id,
      message,
      type,
      duration: duration === 0 ? undefined : duration, // 0 means persistent
    };

    setToasts((prev) => [...prev, newToast]);
    return id;
  }, []);

  /**
   * Show a persistent toast that doesn't auto-dismiss
   * Returns the toast ID for later dismissal
   */
  const showPersistentToast = React.useCallback((message: string, type: ToastType = 'info') => {
    return showToast(message, type, 0); // 0 = persistent
  }, [showToast]);

  /**
   * Update an existing toast's message
   */
  const updateToast = React.useCallback((id: string, updates: Partial<Toast>) => {
    setToasts((prev) =>
      prev.map((toast) => (toast.id === id ? { ...toast, ...updates } : toast))
    );
  }, []);

  const dismissToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const dismissAll = React.useCallback(() => {
    setToasts([]);
  }, []);

  return {
    toasts,
    showToast,
    showPersistentToast,
    updateToast,
    dismissToast,
    dismissAll,
  };
};

