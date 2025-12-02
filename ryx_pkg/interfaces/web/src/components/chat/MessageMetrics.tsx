import React from 'react';
import { ChatMessage } from '../../types';

interface MessageMetricsProps {
  metrics?: ChatMessage['performanceMetrics'];
  className?: string;
}

/**
 * Performance metrics display for messages
 */
const MessageMetrics: React.FC<MessageMetricsProps> = ({ metrics, className = '' }) => {
  if (!metrics) return null;

  const formatTime = (seconds?: number) => {
    if (!seconds) return 'N/A';
    return `${seconds.toFixed(2)}s`;
  };

  const formatTokens = (tokens?: number) => {
    if (!tokens) return 'N/A';
    return tokens.toString();
  };

  const formatTokensPerSecond = (tps?: number) => {
    if (!tps) return 'N/A';
    return `${Math.round(tps)} tok/s`;
  };

  return (
    <div className={`flex items-center gap-3 text-xs text-gray-400 mt-2 pt-2 border-t border-gray-700/30 ${className}`}>
      {metrics.totalTime !== undefined && (
        <span>{formatTime(metrics.totalTime)}</span>
      )}
      {metrics.ttft !== undefined && (
        <>
          <span>•</span>
          <span>TTFT: {formatTime(metrics.ttft)}</span>
        </>
      )}
      {(metrics.inputTokens !== undefined || metrics.outputTokens !== undefined) && (
        <>
          <span>•</span>
          <span>
            {formatTokens(metrics.inputTokens || 0)}+{formatTokens(metrics.outputTokens || 0)} tokens
          </span>
        </>
      )}
      {metrics.tokensPerSecond !== undefined && (
        <>
          <span>•</span>
          <span>{formatTokensPerSecond(metrics.tokensPerSecond)}</span>
        </>
      )}
    </div>
  );
};

export default MessageMetrics;

