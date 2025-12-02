import React from 'react';
import { FolderIcon, PlusIcon } from '@heroicons/react/20/solid';
import RAGFileList from './RAGFileList';
import { RAGFile } from '../../types';

interface EnhancedRAGSectionProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  directoryPath: string;
  onDirectoryPathChange: (path: string) => void;
  files: RAGFile[];
  onAddFile: () => void;
  onRemoveFile: (fileId: string) => void;
  disabled?: boolean;
}

/**
 * Enhanced RAG section with file list and better UI
 */
const EnhancedRAGSection: React.FC<EnhancedRAGSectionProps> = ({
  enabled,
  onToggle,
  directoryPath,
  onDirectoryPathChange,
  files,
  onAddFile,
  onRemoveFile,
  disabled = false,
}) => {
  return (
    <div className="mb-6 pb-4 border-b border-gray-700/50">
      <div className="flex items-center gap-2 mb-3">
        <FolderIcon className="w-4 h-4 text-gray-400" />
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          RAG
        </h3>
      </div>

      <div className="space-y-3">
        {/* Toggle */}
        <label className="flex items-center justify-between gap-2 cursor-pointer group">
          <span className={`text-sm font-medium text-gray-300 ${disabled ? 'opacity-50' : ''}`}>
            Enable RAG
          </span>
          <div className="relative">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => onToggle(e.target.checked)}
              disabled={disabled}
              className="sr-only"
            />
            <div
              className={`w-11 h-6 rounded-full transition-colors duration-200 ${
                enabled
                  ? 'bg-blue-600'
                  : 'bg-gray-600'
              } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
              onClick={() => !disabled && onToggle(!enabled)}
            >
              <div
                className={`w-5 h-5 bg-white rounded-full shadow-md transform transition-transform duration-200 ${
                  enabled ? 'translate-x-5' : 'translate-x-0.5'
                } ${disabled ? '' : 'translate-y-0.5'}`}
              />
            </div>
          </div>
        </label>

        {/* Directory Path Input */}
        {enabled && (
          <div className="space-y-2">
            <label htmlFor="rag-path" className="block text-xs font-medium text-gray-400">
              Enter directory path for RAG
            </label>
            <div className="flex gap-2">
              <input
                id="rag-path"
                type="text"
                value={directoryPath}
                onChange={(e) => onDirectoryPathChange(e.target.value)}
                placeholder="/path/to/documents"
                disabled={disabled}
                className="flex-1 px-3 py-2 text-sm rounded-lg bg-gray-700/50 border border-gray-600/50 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                onClick={onAddFile}
                disabled={disabled || !directoryPath.trim()}
                className="px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-1.5 text-sm font-medium"
              >
                <PlusIcon className="w-4 h-4" />
                Add
              </button>
            </div>

            {/* File List */}
            <RAGFileList files={files} onRemove={onRemoveFile} disabled={disabled} />
          </div>
        )}
      </div>
    </div>
  );
};

export default EnhancedRAGSection;

