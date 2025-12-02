import React from 'react';
import { SearchProvider, SearchProviderConfig } from '../types';

interface SearchProviderSelectorProps {
  providers: SearchProviderConfig[];
  selectedProvider: SearchProvider;
  onProviderChange: (provider: SearchProvider) => void;
  disabled?: boolean;
  showCustomUrl?: boolean;
  customUrl?: string | null;
  onCustomUrlChange?: (url: string | null) => void;
}

/**
 * Dropdown component for selecting search provider
 */
const SearchProviderSelector: React.FC<SearchProviderSelectorProps> = ({
  providers,
  selectedProvider,
  onProviderChange,
  disabled = false,
  showCustomUrl = false,
  customUrl = null,
  onCustomUrlChange,
}) => {
  const enabledProviders = providers.filter((p) => p.enabled);

  return (
    <div className="space-y-2">
      <div>
        <label className="block text-sm font-semibold text-gray-300 mb-2">
          Search Provider
        </label>
        <select
          value={selectedProvider}
          onChange={(e) => onProviderChange(e.target.value as SearchProvider)}
          disabled={disabled}
          className="w-full p-2 rounded bg-gray-700 border border-gray-600 text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {enabledProviders.map((provider) => (
            <option key={provider.id} value={provider.id}>
              {provider.name}
            </option>
          ))}
        </select>
      </div>

      {showCustomUrl && onCustomUrlChange && (
        <div>
          <label className="block text-sm font-semibold text-gray-300 mb-2">
            Custom Search API URL (optional)
          </label>
          <input
            type="text"
            value={customUrl || ''}
            onChange={(e) => onCustomUrlChange(e.target.value || null)}
            placeholder="https://your-searxng-instance.com"
            disabled={disabled}
            className="w-full p-2 rounded bg-gray-700 border border-gray-600 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <p className="text-xs text-gray-400 mt-1">
            Leave empty to use default provider URL
          </p>
        </div>
      )}
    </div>
  );
};

export default SearchProviderSelector;

