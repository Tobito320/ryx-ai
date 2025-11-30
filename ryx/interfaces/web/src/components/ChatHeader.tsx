import React from 'react';

interface ChatHeaderProps {
  modelName: string;
  connectionStatus: 'connected' | 'disconnected' | 'connecting' | 'reconnecting';
}

/**
 * Chat header component showing model name and status
 */
const ChatHeader: React.FC<ChatHeaderProps> = ({ modelName, connectionStatus }) => {
  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'text-green-400';
      case 'disconnected':
        return 'text-red-400';
      case 'connecting':
      case 'reconnecting':
        return 'text-yellow-400';
      default:
        return 'text-gray-400';
    }
  };

  return (
    <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700 bg-gray-800/50">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-gray-100">{modelName}</h1>
        <span className={`text-xs ${getStatusColor()}`}>
          {connectionStatus === 'connected' && '● Connected'}
          {connectionStatus === 'disconnected' && '● Disconnected'}
          {connectionStatus === 'connecting' && '● Connecting...'}
          {connectionStatus === 'reconnecting' && '● Reconnecting...'}
        </span>
      </div>
    </div>
  );
};

export default ChatHeader;

