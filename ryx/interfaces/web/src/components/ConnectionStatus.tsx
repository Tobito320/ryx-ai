import React from 'react';
import { ConnectionStatus as ConnectionStatusType } from '../types';

// Re-export type for backward compatibility (export as ConnectionStatusType to avoid naming conflict)
export type { ConnectionStatusType };

interface ConnectionStatusProps {
  status: ConnectionStatusType;
  className?: string;
}

/**
 * Connection status indicator component
 * Shows visual indicator (colored dot, icon, or banner) for connection state
 */
const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ status, className = '' }) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'connected':
        return {
          color: 'bg-green-500',
          text: 'Connected',
          icon: '●',
          textColor: 'text-green-400',
        };
      case 'disconnected':
        return {
          color: 'bg-red-500',
          text: 'Disconnected',
          icon: '●',
          textColor: 'text-red-400',
        };
      case 'connecting':
        return {
          color: 'bg-yellow-500',
          text: 'Connecting...',
          icon: '●',
          textColor: 'text-yellow-400',
        };
      case 'reconnecting':
        return {
          color: 'bg-yellow-500 animate-pulse',
          text: 'Reconnecting...',
          icon: '●',
          textColor: 'text-yellow-400',
        };
      default:
        return {
          color: 'bg-gray-500',
          text: 'Unknown',
          icon: '●',
          textColor: 'text-gray-400',
        };
    }
  };

  const config = getStatusConfig();

  // Compact version (just dot + text)
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className={`${config.color} w-2 h-2 rounded-full ${status === 'reconnecting' ? 'animate-pulse' : ''}`} />
      <span className={`text-sm font-medium ${config.textColor}`}>
        {config.text}
      </span>
    </div>
  );
};

/**
 * Banner version of connection status (for top of screen)
 */
export const ConnectionStatusBanner: React.FC<{ status: ConnectionStatusType }> = ({ status }) => {
  if (status === 'connected') return null; // Don't show banner when connected

  const getBannerConfig = () => {
    switch (status) {
      case 'disconnected':
        return {
          bg: 'bg-red-900',
          border: 'border-red-700',
          text: 'text-red-100',
          message: 'Backend unavailable. Messages will be queued.',
        };
      case 'connecting':
        return {
          bg: 'bg-yellow-900',
          border: 'border-yellow-700',
          text: 'text-yellow-100',
          message: 'Connecting to backend...',
        };
      case 'reconnecting':
        return {
          bg: 'bg-yellow-900',
          border: 'border-yellow-700',
          text: 'text-yellow-100',
          message: 'Reconnecting to backend...',
        };
      default:
        return {
          bg: 'bg-gray-800',
          border: 'border-gray-700',
          text: 'text-gray-100',
          message: 'Connection status unknown',
        };
    }
  };

  const config = getBannerConfig();

  return (
    <div className={`${config.bg} ${config.border} border-b ${config.text} px-4 py-2 text-sm text-center`}>
      {config.message}
    </div>
  );
};

export default ConnectionStatus;

