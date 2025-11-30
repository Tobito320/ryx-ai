import { useState, useEffect, useCallback } from 'react';
import { RAGFile } from '../types';
import { getStorageItem, setStorageItem } from '../utils/storage';

const RAG_FILES_STORAGE_KEY = 'rag_files';

/**
 * Hook to manage RAG files with localStorage persistence
 */
export const useRAGFiles = () => {
  const [files, setFiles] = useState<RAGFile[]>([]);

  // Load files from localStorage on mount
  useEffect(() => {
    try {
      const storedFiles = getStorageItem<RAGFile[]>(RAG_FILES_STORAGE_KEY, []);
      if (storedFiles) {
        setFiles(storedFiles);
      }
    } catch (error) {
      console.error('Failed to load RAG files from localStorage:', error);
    }
  }, []);

  // Save files to localStorage whenever they change
  useEffect(() => {
    try {
      setStorageItem(RAG_FILES_STORAGE_KEY, files);
    } catch (error) {
      console.error('Failed to save RAG files to localStorage:', error);
    }
  }, [files]);

  const addFile = useCallback((path: string) => {
    // Extract filename from path
    const fileName = path.split('/').pop() || path.split('\\').pop() || 'unknown';
    
    // Check if file already exists
    if (files.some((f) => f.path === path)) {
      return false;
    }

    // For demo purposes, generate a mock file size
    // In production, you'd fetch this from the backend
    const mockSize = Math.floor(Math.random() * 100000) + 1000;

    const newFile: RAGFile = {
      id: `rag-file-${Date.now()}-${Math.random()}`,
      name: fileName,
      path: path,
      size: mockSize,
      addedAt: Date.now(),
    };

    setFiles((prev) => [...prev, newFile]);
    return true;
  }, [files]);

  const removeFile = useCallback((fileId: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  }, []);

  const clearFiles = useCallback(() => {
    setFiles([]);
  }, []);

  return {
    files,
    addFile,
    removeFile,
    clearFiles,
  };
};

