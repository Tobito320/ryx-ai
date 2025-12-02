/**
 * Keyboard shortcut utilities
 */

export type KeyboardShortcut = {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean; // Cmd on Mac
};

/**
 * Check if a keyboard event matches a shortcut
 */
export const matchesShortcut = (
  event: KeyboardEvent,
  shortcut: KeyboardShortcut
): boolean => {
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  const ctrlKey = isMac ? event.metaKey : event.ctrlKey;
  const altKey = event.altKey;
  const shiftKey = event.shiftKey;

  if (shortcut.ctrl !== undefined && shortcut.ctrl !== ctrlKey) return false;
  if (shortcut.shift !== undefined && shortcut.shift !== shiftKey) return false;
  if (shortcut.alt !== undefined && shortcut.alt !== altKey) return false;
  if (shortcut.meta !== undefined && shortcut.meta !== event.metaKey) return false;

  return event.key.toLowerCase() === shortcut.key.toLowerCase();
};

/**
 * Common keyboard shortcuts
 */
export const SHORTCUTS = {
  NEW_SESSION: { key: 'k', ctrl: true } as KeyboardShortcut,
  FOCUS_INPUT: { key: 'l', ctrl: true } as KeyboardShortcut,
  CLEAR_CHAT: { key: 'k', ctrl: true, shift: true } as KeyboardShortcut,
} as const;

