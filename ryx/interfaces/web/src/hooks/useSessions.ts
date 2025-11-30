import { useState, useEffect, useCallback } from 'react';
import { Session } from '../types';
import { getStorageItem, setStorageItem } from '../utils/storage';

const SESSIONS_STORAGE_KEY = 'chat_sessions';
const SELECTED_SESSION_KEY = 'selected_session';

/**
 * Hook to manage chat sessions with localStorage persistence
 */
export const useSessions = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  // Load sessions from localStorage on mount
  useEffect(() => {
    try {
      const storedSessions = getStorageItem<Session[]>(SESSIONS_STORAGE_KEY, []);
      const storedSelected = getStorageItem<string>(SELECTED_SESSION_KEY, null);

      if (storedSessions && storedSessions.length > 0) {
        setSessions(storedSessions);

        if (storedSelected && storedSessions.find((s) => s.id === storedSelected)) {
          setSelectedSessionId(storedSelected);
        } else {
          setSelectedSessionId(storedSessions[0].id);
        }
      } else {
        // Create default session if none exist
        const defaultSession: Session = {
          id: 'default-session',
          name: 'Default Session',
          createdAt: Date.now(),
          lastActive: Date.now(),
	  messageCount: 0,
        };
        setSessions([defaultSession]);
        setSelectedSessionId(defaultSession.id);
      }
    } catch (error) {
      console.error('Failed to load sessions from localStorage:', error);
      // Create default session on error
      const defaultSession: Session = {
        id: 'default-session',
        name: 'Default Session',
        createdAt: Date.now(),
        lastActive: Date.now(),
	messageCount: 0,
      };
      setSessions([defaultSession]);
      setSelectedSessionId(defaultSession.id);
    }
  }, []);

  // Save sessions to localStorage whenever they change
  useEffect(() => {
    try {
      setStorageItem(SESSIONS_STORAGE_KEY, sessions);
    } catch (error) {
      if (error instanceof Error && 'code' in error && error.code === 'QUOTA_EXCEEDED') {
        console.error('Storage quota exceeded. Please clear some data.');
      } else {
        console.error('Failed to save sessions to localStorage:', error);
      }
    }
  }, [sessions]);

  // Save selected session to localStorage
  useEffect(() => {
    if (selectedSessionId) {
      try {
        setStorageItem(SELECTED_SESSION_KEY, selectedSessionId);
      } catch (error) {
        console.error('Failed to save selected session to localStorage:', error);
      }
    }
  }, [selectedSessionId]);

  const createSession = useCallback((name?: string, modelName?: string) => {
    const newSession: Session = {
      id: `session-${Date.now()}-${Math.random()}`,
      name: name || `Session ${sessions.length + 1}`,
      createdAt: Date.now(),
      lastActive: Date.now(),
      modelName: modelName,
      messageCount: 0,
    };

    setSessions((prev) => [...prev, newSession]);
    setSelectedSessionId(newSession.id);
    return newSession;
  }, [sessions.length]);

  const deleteSession = useCallback((sessionId: string) => {
    if (sessions.length <= 1) {
      // Don't allow deleting the last session
      return;
    }

    setSessions((prev) => {
      const filtered = prev.filter((s) => s.id !== sessionId);
      if (selectedSessionId === sessionId && filtered.length > 0) {
        setSelectedSessionId(filtered[0].id);
      }
      return filtered;
    });
  }, [sessions.length, selectedSessionId]);

  const selectSession = useCallback((sessionId: string) => {
    const session = sessions.find((s) => s.id === sessionId);
    if (session) {
      setSelectedSessionId(sessionId);
      // Update last active time
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId ? { ...s, lastActive: Date.now() } : s
        )
      );
    }
  }, [sessions]);

  const updateSessionName = useCallback((sessionId: string, name: string) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId ? { ...s, name } : s))
    );
  }, []);

  const selectedSession = sessions.find((s) => s.id === selectedSessionId) || null;

  return {
    sessions,
    selectedSession,
    selectedSessionId,
    createSession,
    deleteSession,
    selectSession,
    updateSessionName,
  };
};

