import React from 'react';
import { SearchResult } from '../types';

interface SearchResultsProps {
  results: SearchResult[];
  query: string;
  provider: string;
  className?: string;
}

/**
 * Component to display search results in a user-friendly format
 */
const SearchResults: React.FC<SearchResultsProps> = ({
  results,
  query,
  provider,
  className = '',
}) => {
  if (!results || results.length === 0) {
    return null;
  }

  return (
    <div className={`bg-gray-800 border border-gray-700 rounded-lg p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-300">
          Search Results ({results.length})
        </h4>
        <span className="text-xs text-gray-500">via {provider}</span>
      </div>
      <div className="space-y-3">
        {results.slice(0, 5).map((result, index) => (
          <div key={index} className="border-l-2 border-blue-500 pl-3">
            <a
              href={result.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:text-blue-300 font-medium text-sm block mb-1"
            >
              {result.title}
            </a>
            <p className="text-gray-400 text-xs mb-1">{result.snippet}</p>
            <span className="text-gray-500 text-xs">{result.url}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SearchResults;

