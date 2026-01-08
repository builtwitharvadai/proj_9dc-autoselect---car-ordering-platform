import { useEffect, useState, useCallback } from 'react';
import type { VehicleInventory, VehicleAvailability } from '../../types/vehicle';

/**
 * Availability status configuration with styling and messaging
 */
interface AvailabilityConfig {
  readonly label: string;
  readonly description: string;
  readonly color: string;
  readonly bgColor: string;
  readonly borderColor: string;
  readonly icon: string;
  readonly priority: number;
}

/**
 * Availability indicator component props
 */
interface AvailabilityIndicatorProps {
  readonly inventory?: VehicleInventory;
  readonly availability: VehicleAvailability;
  readonly showRefresh?: boolean;
  readonly onRefresh?: () => void | Promise<void>;
  readonly className?: string;
  readonly compact?: boolean;
  readonly showQuantity?: boolean;
}

/**
 * Availability status configurations
 */
const AVAILABILITY_CONFIG: Record<VehicleAvailability, AvailabilityConfig> = {
  available: {
    label: 'Available',
    description: 'In stock and ready for purchase',
    color: 'text-green-700',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    icon: '✓',
    priority: 1,
  },
  reserved: {
    label: 'Reserved',
    description: 'Currently reserved by another customer',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    icon: '⏳',
    priority: 2,
  },
  sold: {
    label: 'Sold',
    description: 'This vehicle has been sold',
    color: 'text-red-700',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    icon: '✕',
    priority: 3,
  },
  unavailable: {
    label: 'Unavailable',
    description: 'Not currently available for purchase',
    color: 'text-gray-700',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
    icon: '○',
    priority: 4,
  },
} as const;

/**
 * Low stock threshold
 */
const LOW_STOCK_THRESHOLD = 3;

/**
 * Determine effective availability status based on inventory
 */
function getEffectiveAvailability(
  availability: VehicleAvailability,
  inventory?: VehicleInventory,
): VehicleAvailability {
  if (!inventory) {
    return availability;
  }

  // Check if actually available based on inventory
  if (availability === 'available' && inventory.availableQuantity <= 0) {
    return 'unavailable';
  }

  return availability;
}

/**
 * Check if stock is low
 */
function isLowStock(inventory?: VehicleInventory): boolean {
  if (!inventory) {
    return false;
  }

  return (
    inventory.availableQuantity > 0 &&
    inventory.availableQuantity <= LOW_STOCK_THRESHOLD
  );
}

/**
 * Format quantity display
 */
function formatQuantity(inventory?: VehicleInventory): string {
  if (!inventory) {
    return 'Stock information unavailable';
  }

  const { availableQuantity, quantity, reservedQuantity } = inventory;

  if (availableQuantity === 0) {
    return 'Out of stock';
  }

  if (availableQuantity === 1) {
    return '1 unit available';
  }

  if (isLowStock(inventory)) {
    return `Only ${availableQuantity} units left`;
  }

  const parts: string[] = [`${availableQuantity} available`];

  if (reservedQuantity > 0) {
    parts.push(`${reservedQuantity} reserved`);
  }

  if (quantity > availableQuantity + reservedQuantity) {
    parts.push(`${quantity - availableQuantity - reservedQuantity} sold`);
  }

  return parts.join(' • ');
}

/**
 * AvailabilityIndicator Component
 * 
 * Displays real-time vehicle availability status with stock information
 * and optional refresh capability.
 * 
 * Features:
 * - Color-coded status indicators
 * - Stock quantity display
 * - Low stock warnings
 * - Manual refresh capability
 * - Compact and full display modes
 * - Accessibility compliant
 */
export default function AvailabilityIndicator({
  inventory,
  availability,
  showRefresh = false,
  onRefresh,
  className = '',
  compact = false,
  showQuantity = true,
}: AvailabilityIndicatorProps): JSX.Element {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const effectiveAvailability = getEffectiveAvailability(availability, inventory);
  const config = AVAILABILITY_CONFIG[effectiveAvailability];
  const lowStock = isLowStock(inventory);

  /**
   * Handle refresh action
   */
  const handleRefresh = useCallback(async () => {
    if (!onRefresh || isRefreshing) {
      return;
    }

    setIsRefreshing(true);

    try {
      await Promise.resolve(onRefresh());
      setLastRefreshed(new Date());
    } catch (error) {
      console.error('Failed to refresh availability:', error);
    } finally {
      setIsRefreshing(false);
    }
  }, [onRefresh, isRefreshing]);

  /**
   * Auto-refresh on mount if refresh handler provided
   */
  useEffect(() => {
    if (showRefresh && onRefresh) {
      void handleRefresh();
    }
  }, [showRefresh, onRefresh, handleRefresh]);

  /**
   * Format last refreshed time
   */
  const formatLastRefreshed = useCallback((): string => {
    const now = new Date();
    const diffMs = now.getTime() - lastRefreshed.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);

    if (diffSec < 60) {
      return 'Just now';
    }

    if (diffMin < 60) {
      return `${diffMin} minute${diffMin === 1 ? '' : 's'} ago`;
    }

    const diffHour = Math.floor(diffMin / 60);
    return `${diffHour} hour${diffHour === 1 ? '' : 's'} ago`;
  }, [lastRefreshed]);

  if (compact) {
    return (
      <div
        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border ${config.bgColor} ${config.borderColor} ${className}`}
        role="status"
        aria-label={`Vehicle availability: ${config.label}`}
      >
        <span
          className={`text-sm font-medium ${config.color}`}
          aria-hidden="true"
        >
          {config.icon}
        </span>
        <span className={`text-sm font-medium ${config.color}`}>
          {config.label}
        </span>
        {lowStock && (
          <span
            className="text-xs font-semibold text-orange-600"
            aria-label="Low stock warning"
          >
            Low Stock
          </span>
        )}
      </div>
    );
  }

  return (
    <div
      className={`rounded-lg border ${config.borderColor} ${config.bgColor} p-4 ${className}`}
      role="region"
      aria-label="Vehicle availability information"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <span
              className={`text-lg font-semibold ${config.color}`}
              aria-hidden="true"
            >
              {config.icon}
            </span>
            <h3 className={`text-lg font-semibold ${config.color}`}>
              {config.label}
            </h3>
            {lowStock && (
              <span
                className="inline-flex items-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-semibold text-orange-800"
                role="alert"
                aria-label="Low stock alert"
              >
                Low Stock
              </span>
            )}
          </div>

          <p className={`text-sm ${config.color}`}>
            {config.description}
          </p>

          {showQuantity && inventory && (
            <div className="mt-3 space-y-1">
              <p className="text-sm font-medium text-gray-900">
                {formatQuantity(inventory)}
              </p>
              {inventory.location && (
                <p className="text-xs text-gray-600">
                  Location: {inventory.location}
                </p>
              )}
            </div>
          )}

          {showRefresh && (
            <p className="text-xs text-gray-500">
              Last updated: {formatLastRefreshed()}
            </p>
          )}
        </div>

        {showRefresh && onRefresh && (
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="inline-flex items-center justify-center rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Refresh availability status"
          >
            <svg
              className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`}
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            <span className="ml-2">
              {isRefreshing ? 'Refreshing...' : 'Refresh'}
            </span>
          </button>
        )}
      </div>
    </div>
  );
}