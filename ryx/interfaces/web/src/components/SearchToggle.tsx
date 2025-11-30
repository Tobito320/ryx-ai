import React from 'react';

interface SearchToggleProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  disabled?: boolean;
}

/**
 * Toggle switch component for enabling/disabling search feature
 */
const SearchToggle: React.FC<SearchToggleProps> = ({
  enabled,
  onToggle,
  disabled = false,
}) => {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={enabled}
        onChange={(e) => onToggle(e.target.checked)}
        disabled={disabled}
        className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      />
      <span className={`text-gray-300 ${disabled ? 'opacity-50' : ''}`}>
        Enable Search
      </span>
    </label>
  );
};

export default SearchToggle;

