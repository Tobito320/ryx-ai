import React from 'react';
import { PlusIcon, ServerIcon } from '@heroicons/react/20/solid';
import { Model } from '../../types';

interface ModelsSectionProps {
  models: Model[];
  onNewChat: (modelId: string) => void;
  disabled?: boolean;
}

/**
 * Models section showing available models with port range
 */
const ModelsSection: React.FC<ModelsSectionProps> = ({
  models,
  onNewChat,
  disabled = false,
}) => {
  // Group models by port range
  const modelsByPort = models.reduce((acc, model) => {
    const key = model.portRange || 'default';
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(model);
    return acc;
  }, {} as Record<string, Model[]>);

  return (
    <div className="mb-6 pb-4 border-b border-gray-700/50">
      <div className="flex items-center gap-2 mb-3">
        <ServerIcon className="w-4 h-4 text-gray-400" />
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Models
        </h3>
      </div>

      {Object.entries(modelsByPort).map(([portRange, portModels]) => (
        <div key={portRange} className="mb-3 last:mb-0">
          {portRange !== 'default' && (
            <div className="text-xs text-gray-500 mb-2 px-1">
              on {portRange}
            </div>
          )}
          <div className="space-y-2">
            {portModels.map((model) => (
              <div
                key={model.id}
                className="flex items-center justify-between p-2.5 rounded-lg bg-gray-700/30 border border-gray-600/30 hover:bg-gray-700/50 hover:border-gray-600/50 transition-all group"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-200 truncate">
                    {model.name}
                  </div>
                  {model.status && (
                    <div className="flex items-center gap-1.5 mt-1">
                      <div
                        className={`w-1.5 h-1.5 rounded-full ${
                          model.status === 'available'
                            ? 'bg-green-400'
                            : model.status === 'loading'
                            ? 'bg-yellow-400 animate-pulse'
                            : 'bg-gray-500'
                        }`}
                      />
                      <span className="text-xs text-gray-400 capitalize">
                        {model.status}
                      </span>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => onNewChat(model.id)}
                  disabled={disabled || model.status !== 'available'}
                  className="ml-2 px-2.5 py-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-md transition-colors flex items-center gap-1.5 opacity-0 group-hover:opacity-100"
                >
                  <PlusIcon className="w-3.5 h-3.5" />
                  Chat
                </button>
              </div>
            ))}
          </div>
        </div>
      ))}

      {models.length === 0 && (
        <div className="text-sm text-gray-500 italic py-2">
          No models available
        </div>
      )}
    </div>
  );
};

export default ModelsSection;

