import { useState, useEffect, useCallback } from 'react';
import { Model } from '../types';

const API_BASE = process.env.REACT_APP_API_URL || '/api';

export const useModels = () => {
  const [models, setModels] = useState<Model[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchModels = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/models`, {
        signal: AbortSignal.timeout(5000),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      
      const transformedModels: Model[] = (data.models || []).map((model: any) => ({
        id: model.id || model.path?.replace('.gguf', ''),
        name: model.name || model.path?.replace('.gguf', '').replace(/-/g, ' '),
        portRange: '8000-8010',
        status: model.status || 'available',
        size: model.size,
        path: model.path,
      }));

      setModels(transformedModels);
      console.log('✅ Models loaded:', transformedModels.length);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      console.error('❌ Error:', msg);
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshModels = useCallback(async () => {
    await fetchModels();
  }, [fetchModels]);

  useEffect(() => {
    fetchModels();
    const interval = setInterval(fetchModels, 30000);
    return () => clearInterval(interval);
  }, [fetchModels]);

  return {
    models,
    isLoading,
    error,
    refreshModels,
  };
};

