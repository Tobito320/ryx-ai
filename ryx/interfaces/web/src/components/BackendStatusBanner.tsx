import React from 'react';
import { ConnectionStatus } from '../types';
import { useToast } from './Toast';

interface BackendStatusBannerProps {
  status: ConnectionStatus;
  showNotification?: boolean;
}

/**
 * Banner component that shows backend status
 * DEPRECATED: Replaced by persistent toast notification
 * This component now returns null to avoid blocking the UI
 * Use useConnectionToast hook instead for non-intrusive notifications
 */
const BackendStatusBanner: React.FC<BackendStatusBannerProps> = () => {
  // Return null - banner is replaced by toast notification
  // Kept for backward compatibility but doesn't render anything
  return null;
};

export default BackendStatusBanner;

