import React from 'react';
import { DocumentIcon, XMarkIcon } from '@heroicons/react/20/solid';
import { RAGFile } from '../../types';

interface RAGFileListProps {
  files: RAGFile[];
  onRemove: (fileId: string) => void;
  disabled?: boolean;
}

/**
 * List of added RAG files with remove functionality
 */
const RAGFileList: React.FC<RAGFileListProps> = ({ files, onRemove, disabled = false }) => {
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} bytes`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (files.length === 0) {
    return null;
  }

  return (
    <div className="mt-3 space-y-1.5">
      {files.map((file) => (
        <div
          key={file.id}
          className="flex items-center justify-between p-2 rounded-md bg-gray-700/30 border border-gray-600/30 hover:bg-gray-700/50 transition-colors group"
        >
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <DocumentIcon className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-gray-200 truncate">
                {file.name}
              </div>
              <div className="text-xs text-gray-500">{formatFileSize(file.size)}</div>
            </div>
          </div>
          <button
            onClick={() => onRemove(file.id)}
            disabled={disabled}
            className="ml-2 p-1 text-gray-400 hover:text-red-400 hover:bg-red-500/20 rounded transition-colors opacity-0 group-hover:opacity-100 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Remove file"
          >
            <XMarkIcon className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
};

export default RAGFileList;

