/**
 * Vehicle Comparison Page Component
 * 
 * Main comparison page that integrates vehicle selector, comparison table,
 * and action buttons. Provides comprehensive vehicle comparison functionality
 * with empty states, loading states, and error handling.
 * 
 * @module components/VehicleComparison/ComparisonPage
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useComparison } from '../../hooks/useComparison';
import ComparisonTable from './ComparisonTable';
import ComparisonSelector from './ComparisonSelector';
import ComparisonActions from './ComparisonActions';
import type { Vehicle } from '../../types/vehicle';

/**
 * Component props interface
 */
interface ComparisonPageProps {
  readonly className?: string;
  readonly maxVehicles?: number;
  readonly enableUrlSync?: boolean;
  readonly showSelector?: boolean;
  readonly onComparisonComplete?: (vehicles: readonly Vehicle[]) => void;
}

/**
 * Page view state type
 */
type PageView = 'selector' | 'comparison';

/**
 * Toast notification type
 */
interface ToastNotification {
  readonly id: string;
  readonly type: 'success' | 'error' | 'warning' | 'info';
  readonly message: string;
  readonly duration?: number;
}

/**
 * Generate unique ID for toast notifications
 */
function generateToastId(): string {
  return `toast-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Vehicle Comparison Page Component
 * 
 * Integrates all comparison functionality including vehicle selection,
 * comparison table display, and action buttons. Handles URL synchronization,
 * empty states, loading states, and user notifications.
 * 
 * @example
 * ```tsx
 * <ComparisonPage
 *   maxVehicles={4}
 *   enableUrlSync
 *   onComparisonComplete={(vehicles) => console.log('Compared:', vehicles)}
 * />
 * ```
 */
export default function ComparisonPage({
  className = '',
  maxVehicles = 4,
  enableUrlSync = true,
  showSelector = true,
  onComparisonComplete,
}: ComparisonPageProps): JSX.Element {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [currentView, setCurrentView] = useState<PageView>('selector');
  const [toasts, setToasts] = useState<readonly ToastNotification[]>([]);
  const [isInitializing, setIsInitializing] = useState(true);

  const {
    vehicles,
    addVehicle,
    removeVehicle,
    clearComparison,
    isVehicleInComparison,
    canAddMore,
    count: vehicleCount,
    loadFromUrl,
    getComparisonUrl,
  } = useComparison({
    maxVehicles,
    onVehicleAdded: (vehicle) => {
      console.info('[ComparisonPage] Vehicle added to comparison', {
        vehicleId: vehicle.id,
        vehicleName: `${vehicle.year} ${vehicle.make} ${vehicle.model}`,
        totalCount: vehicleCount + 1,
      });
      showToast('success', `Added ${vehicle.year} ${vehicle.make} ${vehicle.model} to comparison`);
    },
    onVehicleRemoved: (vehicleId) => {
      console.info('[ComparisonPage] Vehicle removed from comparison', {
        vehicleId,
        totalCount: vehicleCount - 1,
      });
      showToast('info', 'Vehicle removed from comparison');
    },
    onMaxReached: () => {
      console.warn('[ComparisonPage] Maximum vehicles reached', {
        maxVehicles,
        currentCount: vehicleCount,
      });
      showToast('warning', `Maximum ${maxVehicles} vehicles can be compared at once`);
    },
  });

  /**
   * Show toast notification
   */
  const showToast = useCallback(
    (type: ToastNotification['type'], message: string, duration = 3000): void => {
      const toast: ToastNotification = {
        id: generateToastId(),
        type,
        message,
        duration,
      };

      setToasts((prev) => [...prev, toast]);

      if (duration > 0) {
        setTimeout(() => {
          setToasts((prev) => prev.filter((t) => t.id !== toast.id));
        }, duration);
      }
    },
    []
  );

  /**
   * Dismiss toast notification
   */
  const dismissToast = useCallback((toastId: string): void => {
    setToasts((prev) => prev.filter((t) => t.id !== toastId));
  }, []);

  /**
   * Initialize comparison from URL parameters
   */
  useEffect(() => {
    if (!enableUrlSync) {
      setIsInitializing(false);
      return;
    }

    const vehicleIds = searchParams.get('vehicles');
    if (vehicleIds) {
      const ids = vehicleIds.split(',').filter(Boolean);
      if (ids.length > 0) {
        console.info('[ComparisonPage] Loading comparison from URL', {
          vehicleIds: ids,
          count: ids.length,
        });

        loadFromUrl(ids)
          .then(() => {
            setCurrentView('comparison');
            console.info('[ComparisonPage] Successfully loaded comparison from URL');
          })
          .catch((error) => {
            console.error('[ComparisonPage] Failed to load comparison from URL', {
              error: error instanceof Error ? error.message : 'Unknown error',
              vehicleIds: ids,
            });
            showToast('error', 'Failed to load comparison from URL');
          })
          .finally(() => {
            setIsInitializing(false);
          });
        return;
      }
    }

    setIsInitializing(false);
  }, [enableUrlSync, searchParams, loadFromUrl, showToast]);

  /**
   * Sync comparison state to URL
   */
  useEffect(() => {
    if (!enableUrlSync || isInitializing) {
      return;
    }

    if (vehicles.length > 0) {
      const vehicleIds = vehicles.map((v) => v.id).join(',');
      setSearchParams({ vehicles: vehicleIds }, { replace: true });
    } else {
      setSearchParams({}, { replace: true });
    }
  }, [vehicles, enableUrlSync, isInitializing, setSearchParams]);

  /**
   * Handle view change
   */
  const handleViewChange = useCallback((view: PageView): void => {
    setCurrentView(view);
    console.info('[ComparisonPage] View changed', { view });
  }, []);

  /**
   * Handle vehicle added
   */
  const handleVehicleAdded = useCallback(
    (vehicle: Vehicle): void => {
      addVehicle(vehicle);
      if (vehicleCount + 1 >= 2) {
        setCurrentView('comparison');
      }
    },
    [addVehicle, vehicleCount]
  );

  /**
   * Handle vehicle removed
   */
  const handleVehicleRemoved = useCallback(
    (vehicleId: string): void => {
      removeVehicle(vehicleId);
      if (vehicleCount - 1 === 0) {
        setCurrentView('selector');
      }
    },
    [removeVehicle, vehicleCount]
  );

  /**
   * Handle clear comparison
   */
  const handleClearComparison = useCallback((): boolean => {
    const confirmed = window.confirm(
      `Are you sure you want to clear all ${vehicleCount} vehicle${vehicleCount === 1 ? '' : 's'} from comparison?`
    );

    if (confirmed) {
      clearComparison();
      setCurrentView('selector');
      showToast('info', 'Comparison cleared');
      console.info('[ComparisonPage] Comparison cleared by user');
    }

    return confirmed;
  }, [clearComparison, vehicleCount, showToast]);

  /**
   * Handle export start
   */
  const handleExportStart = useCallback((): void => {
    console.info('[ComparisonPage] PDF export started', {
      vehicleCount,
    });
    showToast('info', 'Generating PDF...', 0);
  }, [vehicleCount, showToast]);

  /**
   * Handle export complete
   */
  const handleExportComplete = useCallback((): void => {
    console.info('[ComparisonPage] PDF export completed successfully');
    setToasts((prev) => prev.filter((t) => t.message !== 'Generating PDF...'));
    showToast('success', 'PDF exported successfully');
    onComparisonComplete?.(vehicles);
  }, [vehicles, showToast, onComparisonComplete]);

  /**
   * Handle export error
   */
  const handleExportError = useCallback(
    (error: Error): void => {
      console.error('[ComparisonPage] PDF export failed', {
        error: error.message,
        stack: error.stack,
      });
      setToasts((prev) => prev.filter((t) => t.message !== 'Generating PDF...'));
      showToast('error', `Export failed: ${error.message}`);
    },
    [showToast]
  );

  /**
   * Handle share success
   */
  const handleShareSuccess = useCallback((): void => {
    console.info('[ComparisonPage] Comparison link shared successfully');
    showToast('success', 'Comparison link copied to clipboard');
  }, [showToast]);

  /**
   * Handle share error
   */
  const handleShareError = useCallback(
    (error: Error): void => {
      console.error('[ComparisonPage] Share failed', {
        error: error.message,
      });
      showToast('error', `Share failed: ${error.message}`);
    },
    [showToast]
  );

  /**
   * Check if comparison is ready
   */
  const isComparisonReady = useMemo(() => vehicles.length >= 2, [vehicles.length]);

  /**
   * Render loading state
   */
  if (isInitializing) {
    return (
      <div className={`min-h-screen bg-gray-50 ${className}`}>
        <div className="container mx-auto px-4 py-8">
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4" />
              <p className="text-gray-600 text-lg">Loading comparison...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen bg-gray-50 ${className}`}>
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-20 shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Vehicle Comparison</h1>
              <p className="text-gray-600 mt-1">
                Compare up to {maxVehicles} vehicles side-by-side
              </p>
            </div>

            {/* View Toggle */}
            {showSelector && vehicles.length > 0 && (
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleViewChange('selector')}
                  className={`
                    px-4 py-2 rounded-lg font-medium transition-colors
                    ${currentView === 'selector' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}
                  `}
                  aria-pressed={currentView === 'selector'}
                >
                  Select Vehicles
                </button>
                <button
                  type="button"
                  onClick={() => handleViewChange('comparison')}
                  disabled={!isComparisonReady}
                  className={`
                    px-4 py-2 rounded-lg font-medium transition-colors
                    ${currentView === 'comparison' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}
                    disabled:opacity-50 disabled:cursor-not-allowed
                  `}
                  aria-pressed={currentView === 'comparison'}
                >
                  View Comparison
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        {/* Empty State */}
        {vehicles.length === 0 && currentView === 'selector' && (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <div className="max-w-md mx-auto">
              <svg
                className="w-24 h-24 mx-auto text-gray-400 mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
                />
              </svg>
              <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                Start Your Comparison
              </h2>
              <p className="text-gray-600 mb-6">
                Select at least 2 vehicles to begin comparing specifications, features, and pricing
                side-by-side.
              </p>
              <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span>You can compare up to {maxVehicles} vehicles at once</span>
              </div>
            </div>
          </div>
        )}

        {/* Vehicle Selector View */}
        {showSelector && currentView === 'selector' && (
          <div className="space-y-6">
            <ComparisonSelector
              onVehicleAdded={handleVehicleAdded}
              onVehicleRemoved={handleVehicleRemoved}
              showSelectedCount
              autoFocus
            />
          </div>
        )}

        {/* Comparison View */}
        {currentView === 'comparison' && (
          <div className="space-y-6">
            {/* Action Bar */}
            {vehicles.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm p-4">
                <div className="flex items-center justify-between flex-wrap gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-700 font-medium">
                      Comparing {vehicles.length} vehicle{vehicles.length === 1 ? '' : 's'}
                    </span>
                    {!isComparisonReady && (
                      <span className="text-sm text-amber-600">
                        (Add at least 2 vehicles to compare)
                      </span>
                    )}
                  </div>
                  <ComparisonActions
                    onExportStart={handleExportStart}
                    onExportComplete={handleExportComplete}
                    onExportError={handleExportError}
                    onClearConfirm={handleClearComparison}
                    onShareSuccess={handleShareSuccess}
                    onShareError={handleShareError}
                    showExport={isComparisonReady}
                    showShare={isComparisonReady}
                    showClear
                  />
                </div>
              </div>
            )}

            {/* Comparison Table */}
            {isComparisonReady ? (
              <div className="bg-white rounded-lg shadow-sm overflow-hidden">
                <ComparisonTable
                  vehicles={vehicles}
                  onRemoveVehicle={handleVehicleRemoved}
                  highlightDifferences
                />
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-sm p-12 text-center">
                <p className="text-gray-600 text-lg">
                  Add at least 2 vehicles to start comparing
                </p>
                {showSelector && (
                  <button
                    type="button"
                    onClick={() => handleViewChange('selector')}
                    className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Select Vehicles
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Toast Notifications */}
      {toasts.length > 0 && (
        <div
          className="fixed bottom-4 right-4 z-50 space-y-2"
          role="region"
          aria-label="Notifications"
          aria-live="polite"
        >
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg
                min-w-[300px] max-w-md animate-slide-in-right
                ${toast.type === 'success' ? 'bg-green-600 text-white' : ''}
                ${toast.type === 'error' ? 'bg-red-600 text-white' : ''}
                ${toast.type === 'warning' ? 'bg-amber-600 text-white' : ''}
                ${toast.type === 'info' ? 'bg-blue-600 text-white' : ''}
              `}
              role="alert"
            >
              <div className="flex-1">{toast.message}</div>
              <button
                type="button"
                onClick={() => dismissToast(toast.id)}
                className="text-white hover:text-gray-200 transition-colors"
                aria-label="Dismiss notification"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}