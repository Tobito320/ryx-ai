/**
 * @file ryx/interfaces/web/src/components/SettingsModal.tsx
 * @description Settings modal for RyxHub configuration.
 * 
 * Features:
 * - Theme toggle (Dracula/Gruvbox)
 * - Model tier selector (fast/balanced/powerful/ultra)
 * - Safety level (normal/strict)
 * - Cache settings
 * - Keyboard shortcuts reference
 */

import React, { useState, useEffect, useCallback } from 'react';

/**
 * Model information interface
 */
export interface Model {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'available' | 'loaded' | 'loading' | 'error';
  path?: string;
  size?: number;
  provider?: string;
}

/**
 * Settings configuration interface
 */
export interface SettingsConfig {
  theme: 'dracula' | 'gruvbox';
  modelTier: 'fast' | 'balanced' | 'powerful' | 'ultra';
  safetyLevel: 'normal' | 'strict';
  cacheEnabled: boolean;
}

/**
 * Props for the SettingsModal component
 */
export interface SettingsModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** Current settings */
  settings: SettingsConfig;
  /** Callback when settings change */
  onSettingsChange: (settings: SettingsConfig) => void;
  /** Custom class name */
  className?: string;
  /** Available models */
  models?: Model[];
  /** Currently active model path */
  activeModel?: string | null;
  /** Model currently being loaded */
  loadingModel?: string | null;
  /** Callback to load a model */
  onLoadModel?: (modelPath: string) => void;
}

// Keyboard shortcuts reference
const KEYBOARD_SHORTCUTS = [
  { keys: 'Ctrl + K', description: 'Toggle chat panel' },
  { keys: '1-5', description: 'Select workflow (1-5)' },
  { keys: 'Ctrl + ?', description: 'Show shortcuts' },
  { keys: 'Enter', description: 'Execute command' },
  { keys: 'Esc', description: 'Close panel/modal' },
];

// Model tier descriptions
const MODEL_TIERS = {
  fast: { label: 'Fast', description: 'Quick responses, lower quality', icon: '⚡' },
  balanced: { label: 'Balanced', description: 'Good balance of speed and quality', icon: '⚖️' },
  powerful: { label: 'Powerful', description: 'High quality, slower', icon: '💪' },
  ultra: { label: 'Ultra', description: 'Best quality, slowest', icon: '🚀' },
};

/**
 * SettingsModal - Modal for configuring RyxHub settings
 */
export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  settings,
  onSettingsChange,
  className = '',
  models = [],
  activeModel = null,
  loadingModel = null,
  onLoadModel,
}) => {
  const [localSettings, setLocalSettings] = useState<SettingsConfig>(settings);

  // Sync local settings when props change
  useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Handle setting change
  const handleChange = useCallback(<K extends keyof SettingsConfig>(
    key: K,
    value: SettingsConfig[K]
  ) => {
    const newSettings = { ...localSettings, [key]: value };
    setLocalSettings(newSettings);
    onSettingsChange(newSettings);
  }, [localSettings, onSettingsChange]);

  if (!isOpen) return null;

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center ${className}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-ryx-bg-elevated border border-ryx-border rounded-ryx-lg shadow-strong animate-scale-in overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-ryx-border">
          <h2 id="settings-title" className="text-lg font-bold text-ryx-foreground font-mono flex items-center gap-2">
            <span>⚙️</span>
            Settings
          </h2>
          <button
            onClick={onClose}
            className="text-ryx-text-muted hover:text-ryx-foreground transition-colors p-1"
            aria-label="Close settings"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto ryx-scrollbar">
          {/* Theme Selection */}
          <div className="space-y-2">
            <label className="text-sm font-semibold text-ryx-foreground font-mono">
              Theme
            </label>
            <div className="flex gap-3">
              {(['dracula', 'gruvbox'] as const).map((theme) => (
                <button
                  key={theme}
                  onClick={() => handleChange('theme', theme)}
                  className={`
                    flex-1 px-4 py-3 rounded-ryx font-mono text-sm
                    border transition-all duration-150
                    ${localSettings.theme === theme
                      ? 'bg-ryx-accent/20 border-ryx-accent text-ryx-foreground'
                      : 'bg-ryx-current-line border-ryx-border text-ryx-text hover:border-ryx-text-muted'
                    }
                  `}
                >
                  {theme === 'dracula' ? '🦇 Dracula' : '🌲 Gruvbox'}
                </button>
              ))}
            </div>
          </div>

          {/* Model Tier Selection */}
          <div className="space-y-2">
            <label className="text-sm font-semibold text-ryx-foreground font-mono">
              Model Tier
            </label>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(MODEL_TIERS).map(([tier, info]) => (
                <button
                  key={tier}
                  onClick={() => handleChange('modelTier', tier as SettingsConfig['modelTier'])}
                  className={`
                    p-3 rounded-ryx font-mono text-left
                    border transition-all duration-150
                    ${localSettings.modelTier === tier
                      ? 'bg-ryx-accent/20 border-ryx-accent'
                      : 'bg-ryx-current-line border-ryx-border hover:border-ryx-text-muted'
                    }
                  `}
                >
                  <div className="flex items-center gap-2">
                    <span>{info.icon}</span>
                    <span className="text-sm font-semibold text-ryx-foreground">{info.label}</span>
                  </div>
                  <p className="text-xs text-ryx-text-muted mt-1">{info.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Safety Level */}
          <div className="space-y-2">
            <label className="text-sm font-semibold text-ryx-foreground font-mono">
              Safety Level
            </label>
            <div className="flex gap-3">
              {(['normal', 'strict'] as const).map((level) => (
                <button
                  key={level}
                  onClick={() => handleChange('safetyLevel', level)}
                  className={`
                    flex-1 px-4 py-3 rounded-ryx font-mono text-sm
                    border transition-all duration-150
                    ${localSettings.safetyLevel === level
                      ? 'bg-ryx-accent/20 border-ryx-accent text-ryx-foreground'
                      : 'bg-ryx-current-line border-ryx-border text-ryx-text hover:border-ryx-text-muted'
                    }
                  `}
                >
                  {level === 'normal' ? '🔓 Normal' : '🔒 Strict'}
                </button>
              ))}
            </div>
          </div>

          {/* Cache Toggle */}
          <div className="flex items-center justify-between p-4 bg-ryx-current-line rounded-ryx">
            <div>
              <span className="text-sm font-semibold text-ryx-foreground font-mono">
                Enable Cache
              </span>
              <p className="text-xs text-ryx-text-muted mt-1">
                Cache responses for faster repeated queries
              </p>
            </div>
            <button
              onClick={() => handleChange('cacheEnabled', !localSettings.cacheEnabled)}
              className={`
                relative w-12 h-6 rounded-full transition-colors duration-200
                ${localSettings.cacheEnabled ? 'bg-ryx-success' : 'bg-ryx-border'}
              `}
              role="switch"
              aria-checked={localSettings.cacheEnabled}
            >
              <span
                className={`
                  absolute top-1 w-4 h-4 bg-white rounded-full transition-transform duration-200
                  ${localSettings.cacheEnabled ? 'translate-x-7' : 'translate-x-1'}
                `}
              />
            </button>
          </div>

          {/* VLLM Models Section */}
          {models.length > 0 && (
            <div className="space-y-2">
              <label className="text-sm font-semibold text-ryx-foreground font-mono flex items-center gap-2">
                <span>🤖</span>
                Available VLLM Models
                <span className="text-xs text-ryx-text-muted font-normal">
                  ({models.filter(m => m.status === 'online' || m.status === 'loaded' || activeModel === m.path).length} active / {models.length} total)
                </span>
              </label>
              <div className="bg-ryx-bg rounded-ryx p-3 max-h-48 overflow-y-auto ryx-scrollbar space-y-2">
                {models.map((model) => (
                  <div
                    key={model.id}
                    className={`
                      p-3 rounded-ryx font-mono text-sm border transition-all duration-150
                      ${activeModel === model.path
                        ? 'bg-ryx-accent/20 border-ryx-accent'
                        : loadingModel === model.path
                        ? 'bg-ryx-orange/10 border-ryx-orange'
                        : 'bg-ryx-current-line border-ryx-border hover:border-ryx-text-muted'
                      }
                      ${onLoadModel && model.path && loadingModel !== model.path ? 'cursor-pointer' : ''}
                    `}
                    onClick={() => {
                      if (onLoadModel && model.path && loadingModel !== model.path && activeModel !== model.path) {
                        onLoadModel(model.path);
                      }
                    }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="text-ryx-foreground font-semibold truncate">{model.name}</div>
                        {model.path && (
                          <div className="text-xs text-ryx-text-muted truncate mt-0.5">{model.path}</div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {loadingModel === model.path ? (
                          <>
                            <div className="w-2 h-2 bg-ryx-orange rounded-full animate-pulse"></div>
                            <span className="text-xs text-ryx-orange">Loading...</span>
                          </>
                        ) : activeModel === model.path ? (
                          <>
                            <div className="w-2 h-2 bg-ryx-success rounded-full"></div>
                            <span className="text-xs text-ryx-success">Active</span>
                          </>
                        ) : model.status === 'online' || model.status === 'loaded' ? (
                          <>
                            <div className="w-2 h-2 bg-ryx-cyan rounded-full"></div>
                            <span className="text-xs text-ryx-cyan">Ready</span>
                          </>
                        ) : (
                          <>
                            <div className="w-2 h-2 bg-ryx-border rounded-full"></div>
                            <span className="text-xs text-ryx-text-muted">Offline</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-ryx-text-muted italic">
                Click on a model to load it. Active models are highlighted in purple.
              </p>
            </div>
          )}

          {/* Keyboard Shortcuts */}
          <div className="space-y-2">
            <label className="text-sm font-semibold text-ryx-foreground font-mono">
              Keyboard Shortcuts
            </label>
            <div className="bg-ryx-bg rounded-ryx p-3 space-y-2">
              {KEYBOARD_SHORTCUTS.map((shortcut) => (
                <div key={shortcut.keys} className="flex items-center justify-between text-sm">
                  <kbd className="px-2 py-1 bg-ryx-current-line text-ryx-cyan rounded text-xs font-mono">
                    {shortcut.keys}
                  </kbd>
                  <span className="text-ryx-text-muted">{shortcut.description}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-ryx-border bg-ryx-bg">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-mono text-ryx-foreground bg-ryx-accent rounded-ryx hover:bg-ryx-purple transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
