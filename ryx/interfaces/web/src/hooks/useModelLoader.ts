import { useState, useCallback } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || '/api';

export const useModelLoader = () => {
  const [loadingModel, setLoadingModel] = useState<string | null>(null);
  const [activeModel, setActiveModel] = useState<string | null>(null);

  const loadModel = useCallback(async (modelPath: string): Promise<boolean> => {
    setLoadingModel(modelPath);
    
    try {
      const response = await fetch(`${API_BASE}/models/load`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name: modelPath }),
        signal: AbortSignal.timeout(5000),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        console.error('Failed to load model:', error);
        setLoadingModel(null);
        return false;
      }

      const data = await response.json();
      console.log('✅ Model loaded:', data);
      setActiveModel(modelPath);
      setLoadingModel(null);
      return true;
    } catch (error) {
      console.error('Error loading model:', error);
      setLoadingModel(null);
      return false;
    }
  }, []);

  return {
    loadModel,
    loadingModel,
    activeModel,
  };
};

