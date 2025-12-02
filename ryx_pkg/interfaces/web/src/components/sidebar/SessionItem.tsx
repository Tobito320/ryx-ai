import React from 'react';
import { EllipsisVerticalIcon, TrashIcon, PencilIcon } from '@heroicons/react/20/solid';
import { Session } from '../../types';
import Dropdown from '../ui/Dropdown';

interface SessionItemProps {
  session: Session;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onRename?: () => void;
}

/**
 * Enhanced session item with menu dropdown
 */
const SessionItem: React.FC<SessionItemProps> = ({
  session,
  isSelected,
  onSelect,
  onDelete,
  onRename,
}) => {
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  const dropdownItems = [
    ...(onRename
      ? [
          {
            label: 'Rename',
            icon: <PencilIcon className="w-4 h-4" />,
            onClick: onRename,
          },
        ]
      : []),
    {
      label: 'Delete',
      icon: <TrashIcon className="w-4 h-4" />,
      onClick: onDelete,
      danger: true,
    },
  ];

  return (
    <div
      className={`group relative p-3 rounded-lg cursor-pointer transition-all duration-200 ${
        isSelected
          ? 'bg-blue-600/20 border border-blue-500/50 shadow-md shadow-blue-500/10'
          : 'bg-gray-700/30 border border-transparent hover:bg-gray-700/50 hover:border-gray-600/50'
      }`}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <div className="text-sm font-semibold text-gray-100 truncate">
              {session.name}
            </div>
            {session.modelName && (
              <span className="text-xs px-1.5 py-0.5 bg-gray-700/50 text-gray-400 rounded">
                {session.modelName}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <span>{formatTime(session.lastActive)}</span>
            <span>•</span>
            <span>{formatDate(session.lastActive)}</span>
          </div>
        </div>
        <div
          className="opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
          onClick={(e) => e.stopPropagation()}
        >
          <Dropdown
            trigger={<EllipsisVerticalIcon className="w-5 h-5 text-gray-400" />}
            items={dropdownItems}
            align="right"
          />
        </div>
      </div>
    </div>
  );
};

export default SessionItem;

