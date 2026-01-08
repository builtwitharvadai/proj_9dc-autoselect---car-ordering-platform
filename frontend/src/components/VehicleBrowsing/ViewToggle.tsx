import { useState, useEffect } from 'react';
import { Grid3x3, List } from 'lucide-react';

type ViewMode = 'grid' | 'list';

interface ViewToggleProps {
  className?: string;
  defaultView?: ViewMode;
  onViewChange?: (view: ViewMode) => void;
}

const VIEW_MODE_STORAGE_KEY = 'vehicle-browse-view-mode';

export default function ViewToggle({
  className = '',
  defaultView = 'grid',
  onViewChange,
}: ViewToggleProps): JSX.Element {
  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    try {
      const stored = localStorage.getItem(VIEW_MODE_STORAGE_KEY);
      if (stored === 'grid' || stored === 'list') {
        return stored;
      }
    } catch (error) {
      console.error('Failed to read view mode from localStorage:', error);
    }
    return defaultView;
  });

  useEffect(() => {
    try {
      localStorage.setItem(VIEW_MODE_STORAGE_KEY, viewMode);
    } catch (error) {
      console.error('Failed to save view mode to localStorage:', error);
    }
  }, [viewMode]);

  const handleViewChange = (newView: ViewMode): void => {
    if (newView === viewMode) {
      return;
    }

    setViewMode(newView);

    if (onViewChange) {
      onViewChange(newView);
    }
  };

  return (
    <div
      className={`inline-flex rounded-lg border border-gray-300 bg-white p-1 shadow-sm ${className}`}
      role="group"
      aria-label="View toggle"
    >
      <button
        type="button"
        onClick={() => handleViewChange('grid')}
        className={`inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-medium transition-all duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
          viewMode === 'grid'
            ? 'bg-blue-600 text-white shadow-sm'
            : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
        }`}
        aria-label="Grid view"
        aria-pressed={viewMode === 'grid'}
      >
        <Grid3x3 className="h-5 w-5" aria-hidden="true" />
        <span className="ml-2 hidden sm:inline">Grid</span>
      </button>

      <button
        type="button"
        onClick={() => handleViewChange('list')}
        className={`inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-medium transition-all duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
          viewMode === 'list'
            ? 'bg-blue-600 text-white shadow-sm'
            : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
        }`}
        aria-label="List view"
        aria-pressed={viewMode === 'list'}
      >
        <List className="h-5 w-5" aria-hidden="true" />
        <span className="ml-2 hidden sm:inline">List</span>
      </button>
    </div>
  );
}