/**
 * @file ryx/interfaces/web/src/components/Header.tsx
 * @description RyxHub header component with logo, settings, and user profile.
 * 
 * Features:
 * - RyxHub logo with purple accent
 * - Settings button
 * - User profile button
 * - Dracula/Hyprland theme styling
 */

import React from 'react';

/**
 * Props for the Header component
 */
export interface HeaderProps {
  /** Current workflow name to display */
  workflowName?: string;
  /** Callback when settings button is clicked */
  onSettingsClick?: () => void;
  /** Callback when user profile is clicked */
  onProfileClick?: () => void;
  /** Custom class name */
  className?: string;
}

/**
 * Header - The top navigation bar for RyxHub
 */
export const Header: React.FC<HeaderProps> = ({
  workflowName,
  onSettingsClick,
  onProfileClick,
  className = '',
}) => {
  return (
    <header
      className={`flex items-center justify-between px-6 py-3 border-b border-ryx-border bg-ryx-bg-elevated ${className}`}
      role="banner"
    >
      {/* Logo and Workflow Name */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl text-ryx-accent" role="img" aria-label="RyxHub logo">
            🟣
          </span>
          <h1 className="text-xl font-bold text-ryx-foreground font-mono tracking-tight">
            RYXHUB
          </h1>
        </div>
        {workflowName && (
          <span className="text-sm text-ryx-text-muted font-mono">
            / {workflowName}
          </span>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        {/* Settings Button */}
        <button
          onClick={onSettingsClick}
          className="flex items-center gap-2 px-3 py-2 text-sm font-mono text-ryx-foreground bg-ryx-current-line rounded-ryx hover:bg-ryx-bg-hover transition-colors duration-150"
          title="Settings"
          aria-label="Open settings"
        >
          <span role="img" aria-hidden="true">⚙️</span>
          <span className="hidden sm:inline">Settings</span>
        </button>

        {/* User Profile Button */}
        <button
          onClick={onProfileClick}
          className="flex items-center justify-center w-9 h-9 text-sm font-mono text-ryx-foreground bg-ryx-accent/20 rounded-full hover:bg-ryx-accent/30 transition-colors duration-150 border border-ryx-accent/40"
          title="User Profile"
          aria-label="Open user profile"
        >
          <span role="img" aria-hidden="true">👤</span>
        </button>
      </div>
    </header>
  );
};

export default Header;
