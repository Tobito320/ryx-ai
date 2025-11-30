import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { SearchProvider, SearchProviderConfig } from '../types';
import { getStorageItem, setStorageItem } from '../utils/storage';

interface SearchContextType {
  searchEnabled: boolean;
  toggleSearch: (enabled: boolean) => void;
  selectedProvider: SearchProvider;
  setSelectedProvider: (provider: SearchProvider) => void;
  providers: SearchProviderConfig[];
  updateProvider: (providerId: SearchProvider, config: Partial<SearchProviderConfig>) => void;
  searchApiUrl: string | null;
  setSearchApiUrl: (url: string | null) => void;
}

const SearchContext = createContext<SearchContextType | undefined>(undefined);

// Default search providers
const DEFAULT_PROVIDERS: SearchProviderConfig[] = [
  {
    id: 'searxng',
    name: 'SearXNG',
    enabled: true,
  },
  {
    id: 'duckduckgo',
    name: 'DuckDuckGo',
    enabled: true,
  },
  {
    id: 'google',
    name: 'Google',
    enabled: true,
  },
  {
    id: 'bing',
    name: 'Bing',
    enabled: true,
  },
  {
    id: 'brave',
    name: 'Brave Search',
    enabled: true,
  },
];

const SEARCH_ENABLED_KEY = 'search_enabled';
const SEARCH_PROVIDER_KEY = 'search_provider';
const SEARCH_API_URL_KEY = 'search_api_url';
const SEARCH_PROVIDERS_KEY = 'search_providers';

export const SearchProviderContext: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [searchEnabled, setSearchEnabled] = useState<boolean>(() => {
    return getStorageItem<boolean>(SEARCH_ENABLED_KEY, false) || false;
  });

  const [selectedProvider, setSelectedProviderState] = useState<SearchProvider>(() => {
    return getStorageItem<SearchProvider>(SEARCH_PROVIDER_KEY, 'searxng') || 'searxng';
  });

  const [providers, setProviders] = useState<SearchProviderConfig[]>(() => {
    const stored = getStorageItem<SearchProviderConfig[]>(SEARCH_PROVIDERS_KEY, null);
    return stored || DEFAULT_PROVIDERS;
  });

  const [searchApiUrl, setSearchApiUrlState] = useState<string | null>(() => {
    return getStorageItem<string | null>(SEARCH_API_URL_KEY, null);
  });

  // Persist search enabled state
  useEffect(() => {
    try {
      setStorageItem(SEARCH_ENABLED_KEY, searchEnabled);
    } catch (error) {
      console.error('Failed to save search enabled state:', error);
    }
  }, [searchEnabled]);

  // Persist selected provider
  useEffect(() => {
    try {
      setStorageItem(SEARCH_PROVIDER_KEY, selectedProvider);
    } catch (error) {
      console.error('Failed to save selected provider:', error);
    }
  }, [selectedProvider]);

  // Persist providers config
  useEffect(() => {
    try {
      setStorageItem(SEARCH_PROVIDERS_KEY, providers);
    } catch (error) {
      console.error('Failed to save providers config:', error);
    }
  }, [providers]);

  // Persist search API URL
  useEffect(() => {
    try {
      setStorageItem(SEARCH_API_URL_KEY, searchApiUrl);
    } catch (error) {
      console.error('Failed to save search API URL:', error);
    }
  }, [searchApiUrl]);

  const toggleSearch = useCallback((enabled: boolean) => {
    setSearchEnabled(enabled);
  }, []);

  const setSelectedProvider = useCallback((provider: SearchProvider) => {
    // Verify provider exists and is enabled
    const providerConfig = providers.find((p) => p.id === provider);
    if (providerConfig && providerConfig.enabled) {
      setSelectedProviderState(provider);
    } else {
      // Fallback to first enabled provider or searxng
      const fallback = providers.find((p) => p.enabled) || DEFAULT_PROVIDERS[0];
      setSelectedProviderState(fallback.id);
    }
  }, [providers]);

  const updateProvider = useCallback((providerId: SearchProvider, config: Partial<SearchProviderConfig>) => {
    setProviders((prev) =>
      prev.map((p) => (p.id === providerId ? { ...p, ...config } : p))
    );
  }, []);

  const setSearchApiUrl = useCallback((url: string | null) => {
    setSearchApiUrlState(url);
  }, []);

  return (
    <SearchContext.Provider
      value={{
        searchEnabled,
        toggleSearch,
        selectedProvider,
        setSelectedProvider,
        providers,
        updateProvider,
        searchApiUrl,
        setSearchApiUrl,
      }}
    >
      {children}
    </SearchContext.Provider>
  );
};

export const useSearch = (): SearchContextType => {
  const context = useContext(SearchContext);
  if (context === undefined) {
    throw new Error('useSearch must be used within a SearchProviderContext');
  }
  return context;
};

