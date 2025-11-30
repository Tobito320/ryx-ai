/**
 * Utility functions for localStorage operations with error handling
 */

export class StorageError extends Error {
  constructor(message: string, public code: string) {
    super(message);
    this.name = 'StorageError';
  }
}

/**
 * Safely get item from localStorage
 */
export const getStorageItem = <T>(key: string, defaultValue: T | null = null): T | null => {
  try {
    const item = localStorage.getItem(key);
    if (item === null) {
      return defaultValue;
    }
    return JSON.parse(item) as T;
  } catch (error) {
    console.error(`Failed to get item from localStorage (key: ${key}):`, error);
    return defaultValue;
  }
};

/**
 * Safely set item in localStorage
 * Handles quota exceeded errors gracefully
 */
export const setStorageItem = <T>(key: string, value: T): boolean => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (error) {
    if (error instanceof DOMException) {
      if (error.code === 22 || error.code === 1014) {
        // QuotaExceededError
        console.error('localStorage quota exceeded. Clearing old data...');
        throw new StorageError(
          'Storage quota exceeded. Please clear some data.',
          'QUOTA_EXCEEDED'
        );
      } else if (error.code === 18) {
        // SecurityError
        console.error('localStorage access denied (security error)');
        throw new StorageError(
          'Storage access denied. Check browser settings.',
          'SECURITY_ERROR'
        );
      }
    }
    console.error(`Failed to set item in localStorage (key: ${key}):`, error);
    throw new StorageError(
      error instanceof Error ? error.message : 'Unknown storage error',
      'UNKNOWN_ERROR'
    );
  }
};

/**
 * Safely remove item from localStorage
 */
export const removeStorageItem = (key: string): boolean => {
  try {
    localStorage.removeItem(key);
    return true;
  } catch (error) {
    console.error(`Failed to remove item from localStorage (key: ${key}):`, error);
    return false;
  }
};

/**
 * Clear all localStorage items with a specific prefix
 */
export const clearStoragePrefix = (prefix: string): number => {
  let cleared = 0;
  try {
    const keys = Object.keys(localStorage);
    keys.forEach((key) => {
      if (key.startsWith(prefix)) {
        localStorage.removeItem(key);
        cleared++;
      }
    });
  } catch (error) {
    console.error('Failed to clear storage prefix:', error);
  }
  return cleared;
};

/**
 * Get storage usage information
 */
export const getStorageInfo = (): { used: number; available: number; quota: number } => {
  try {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      // Modern browsers
      return {
        used: 0,
        available: 0,
        quota: 0,
      };
    }
  } catch (error) {
    console.error('Failed to get storage info:', error);
  }

  // Fallback: estimate based on localStorage
  let used = 0;
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key) {
        used += localStorage.getItem(key)?.length || 0;
      }
    }
  } catch (error) {
    console.error('Failed to estimate storage usage:', error);
  }

  // Typical localStorage quota is 5-10MB
  const quota = 5 * 1024 * 1024; // 5MB estimate
  return {
    used,
    available: quota - used,
    quota,
  };
};

/**
 * Clear all chat-related data from localStorage
 */
export const clearAllChatData = (): { cleared: number; errors: string[] } => {
  const errors: string[] = [];
  let cleared = 0;

  const keysToClear = [
    'chat_sessions',
    'selected_session',
    'chat_message_queue',
  ];

  // Clear all message histories (they have dynamic keys)
  try {
    const keys = Object.keys(localStorage);
    keys.forEach((key) => {
      if (key.startsWith('chat_messages_')) {
        try {
          localStorage.removeItem(key);
          cleared++;
        } catch (error) {
          errors.push(`Failed to clear ${key}`);
        }
      }
    });
  } catch (error) {
    errors.push('Failed to enumerate localStorage keys');
  }

  // Clear fixed keys
  keysToClear.forEach((key) => {
    try {
      if (localStorage.getItem(key)) {
        localStorage.removeItem(key);
        cleared++;
      }
    } catch (error) {
      errors.push(`Failed to clear ${key}`);
    }
  });

  return { cleared, errors };
};

