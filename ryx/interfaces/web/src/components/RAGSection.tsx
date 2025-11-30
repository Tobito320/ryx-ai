import React from 'react';

interface RAGSectionProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  directoryPath?: string;
  onDirectoryPathChange?: (path: string) => void;
  disabled?: boolean;
}

/**
 * RAG Options section with toggle and directory path input
 */
const RAGSection: React.FC<RAGSectionProps> = ({
  enabled,
  onToggle,
  directoryPath = '',
  onDirectoryPathChange,
  disabled = false,
}) => {
  return (
    <div className="space-y-3">
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onToggle(e.target.checked)}
          disabled={disabled}
          className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <span className={`text-sm font-medium text-gray-300 ${disabled ? 'opacity-50' : ''}`}>
          Enable RAG
        </span>
      </label>
      
      {enabled && onDirectoryPathChange && (
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">
            Directory Path
          </label>
          <input
            type="text"
            value={directoryPath}
            onChange={(e) => onDirectoryPathChange(e.target.value)}
            placeholder="/path/to/documents"
            disabled={disabled}
            className="w-full px-3 py-2 text-sm rounded bg-gray-700 border border-gray-600 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>
      )}
    </div>
  );
};

export default RAGSection;

