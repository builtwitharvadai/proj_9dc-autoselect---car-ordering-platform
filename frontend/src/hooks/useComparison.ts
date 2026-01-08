/**
 * Vehicle Comparison Hook
 * 
 * Custom hook providing comparison functionality with state management,
 * vehicle selection/deselection, and comparison utilities.
 * Includes localStorage persistence and URL state management.
 * 
 * @module hooks/useComparison
 */

import { useCallback, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useComparison as useComparisonContext } from '../contexts/ComparisonContext';
import type { Vehicle } from '../types/vehicle';

/**
 * URL parameter key for comparison vehicle IDs
 */
const COMPARISON_URL_PARAM = 'compare';

/**
 * Separator for multiple vehicle IDs in URL
 */
const URL_ID_SEPARATOR = ',';

/**
 * Hook return type with comparison functionality
 */
interface UseComparisonReturn {
  readonly vehicles: readonly Vehicle[];
  readonly isComparing: boolean;
  readonly canAddMore: boolean;
  readonly count: number;
  readonly maxVehicles: number;
  addVehicle: (vehicle: Vehicle) => boolean;
  removeVehicle: (vehicleId: string) => void;
  clearComparison: () => void;
  isVehicleInComparison: (vehicleId: string) => boolean;
  toggleVehicle: (vehicle: Vehicle) => void;
  syncWithUrl: () => void;
  getComparisonUrl: () => string;
  canCompare: boolean;
}

/**
 * Hook options for customization
 */
interface UseComparisonOptions {
  readonly syncUrl?: boolean;
  readonly onVehicleAdded?: (vehicle: Vehicle) => void;
  readonly onVehicleRemoved?: (vehicleId: string) => void;
  readonly onComparisonCleared?: () => void;
  readonly onMaxReached?: () => void;
}

/**
 * Maximum number of vehicles that can be compared
 */
const MAX_COMPARISON_VEHICLES = 4;

/**
 * Minimum number of vehicles required for comparison
 */
const MIN_COMPARISON_VEHICLES = 2;

/**
 * Parse vehicle IDs from URL parameter
 */
function parseVehicleIdsFromUrl(urlParam: string | null): readonly string[] {
  if (!urlParam) {
    return [];
  }

  try {
    const ids = urlParam
      .split(URL_ID_SEPARATOR)
      .map((id) => id.trim())
      .filter((id) => id.length > 0);

    // Validate UUID format (basic check)
    const validIds = ids.filter((id) => {
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      return uuidRegex.test(id);
    });

    // Enforce maximum limit
    return validIds.slice(0, MAX_COMPARISON_VEHICLES);
  } catch (error) {
    console.error('[useComparison] Failed to parse vehicle IDs from URL:', error);
    return [];
  }
}

/**
 * Format vehicle IDs for URL parameter
 */
function formatVehicleIdsForUrl(vehicleIds: readonly string[]): string {
  return vehicleIds.join(URL_ID_SEPARATOR);
}

/**
 * Custom hook for vehicle comparison functionality
 * 
 * Provides comparison state management with localStorage persistence
 * and optional URL synchronization. Supports up to 4 vehicles for
 * side-by-side comparison.
 * 
 * @param options - Hook configuration options
 * 
 * @example
 * ```tsx
 * function VehicleCard({ vehicle }: { vehicle: Vehicle }) {
 *   const {
 *     addVehicle,
 *     removeVehicle,
 *     isVehicleInComparison,
 *     canAddMore
 *   } = useComparison({ syncUrl: true });
 *   
 *   const isInComparison = isVehicleInComparison(vehicle.id);
 *   
 *   const handleToggle = () => {
 *     if (isInComparison) {
 *       removeVehicle(vehicle.id);
 *     } else if (canAddMore) {
 *       addVehicle(vehicle);
 *     }
 *   };
 *   
 *   return (
 *     <button onClick={handleToggle} disabled={!canAddMore && !isInComparison}>
 *       {isInComparison ? 'Remove from' : 'Add to'} Comparison
 *     </button>
 *   );
 * }
 * ```
 */
export function useComparison(options: UseComparisonOptions = {}): UseComparisonReturn {
  const {
    syncUrl = false,
    onVehicleAdded,
    onVehicleRemoved,
    onComparisonCleared,
    onMaxReached,
  } = options;

  const context = useComparisonContext();
  const [searchParams, setSearchParams] = useSearchParams();

  /**
   * Sync comparison state with URL parameters
   */
  const syncWithUrl = useCallback(() => {
    if (!syncUrl) {
      return;
    }

    const vehicleIds = context.vehicles.map((v) => v.id);
    const currentUrlIds = parseVehicleIdsFromUrl(searchParams.get(COMPARISON_URL_PARAM));

    // Check if URL needs updating
    const urlNeedsUpdate =
      vehicleIds.length !== currentUrlIds.length ||
      vehicleIds.some((id, index) => id !== currentUrlIds[index]);

    if (urlNeedsUpdate) {
      const newParams = new URLSearchParams(searchParams);

      if (vehicleIds.length > 0) {
        newParams.set(COMPARISON_URL_PARAM, formatVehicleIdsForUrl(vehicleIds));
      } else {
        newParams.delete(COMPARISON_URL_PARAM);
      }

      setSearchParams(newParams, { replace: true });
      console.info('[useComparison] Synced comparison state to URL:', vehicleIds);
    }
  }, [syncUrl, context.vehicles, searchParams, setSearchParams]);

  /**
   * Sync URL to comparison state on mount (if URL sync enabled)
   */
  useEffect(() => {
    if (!syncUrl) {
      return;
    }

    const urlIds = parseVehicleIdsFromUrl(searchParams.get(COMPARISON_URL_PARAM));
    const currentIds = context.vehicles.map((v) => v.id);

    // Only sync if URL has IDs that aren't in current state
    const hasNewIds = urlIds.some((id) => !currentIds.includes(id));

    if (hasNewIds && urlIds.length > 0) {
      console.info('[useComparison] URL contains comparison IDs, but vehicles need to be loaded separately');
      // Note: Actual vehicle loading should be handled by the component
      // This hook only manages the comparison state
    }
  }, [syncUrl, searchParams, context.vehicles]);

  /**
   * Sync URL when comparison state changes
   */
  useEffect(() => {
    if (syncUrl) {
      syncWithUrl();
    }
  }, [syncUrl, syncWithUrl]);

  /**
   * Enhanced add vehicle with callbacks
   */
  const addVehicle = useCallback(
    (vehicle: Vehicle): boolean => {
      const success = context.addVehicle(vehicle);

      if (success) {
        onVehicleAdded?.(vehicle);
      } else if (context.vehicles.length >= MAX_COMPARISON_VEHICLES) {
        onMaxReached?.();
      }

      return success;
    },
    [context, onVehicleAdded, onMaxReached]
  );

  /**
   * Enhanced remove vehicle with callbacks
   */
  const removeVehicle = useCallback(
    (vehicleId: string): void => {
      context.removeVehicle(vehicleId);
      onVehicleRemoved?.(vehicleId);
    },
    [context, onVehicleRemoved]
  );

  /**
   * Enhanced clear comparison with callbacks
   */
  const clearComparison = useCallback((): void => {
    context.clearComparison();
    onComparisonCleared?.();
  }, [context, onComparisonCleared]);

  /**
   * Generate comparison page URL with current vehicle IDs
   */
  const getComparisonUrl = useCallback((): string => {
    const vehicleIds = context.vehicles.map((v) => v.id);
    if (vehicleIds.length === 0) {
      return '/compare';
    }

    const params = new URLSearchParams();
    params.set(COMPARISON_URL_PARAM, formatVehicleIdsForUrl(vehicleIds));
    return `/compare?${params.toString()}`;
  }, [context.vehicles]);

  /**
   * Check if comparison can be performed (minimum vehicles met)
   */
  const canCompare = useMemo(
    () => context.vehicles.length >= MIN_COMPARISON_VEHICLES,
    [context.vehicles.length]
  );

  /**
   * Memoized return value
   */
  return useMemo(
    () => ({
      vehicles: context.vehicles,
      isComparing: context.isComparing,
      canAddMore: context.canAddMore,
      count: context.count,
      maxVehicles: MAX_COMPARISON_VEHICLES,
      addVehicle,
      removeVehicle,
      clearComparison,
      isVehicleInComparison: context.isVehicleInComparison,
      toggleVehicle: context.toggleVehicle,
      syncWithUrl,
      getComparisonUrl,
      canCompare,
    }),
    [
      context.vehicles,
      context.isComparing,
      context.canAddMore,
      context.count,
      context.isVehicleInComparison,
      context.toggleVehicle,
      addVehicle,
      removeVehicle,
      clearComparison,
      syncWithUrl,
      getComparisonUrl,
      canCompare,
    ]
  );
}

/**
 * Export constants for use in other components
 */
export { MAX_COMPARISON_VEHICLES, MIN_COMPARISON_VEHICLES, COMPARISON_URL_PARAM };

/**
 * Utility function to parse comparison IDs from URL
 * Useful for server-side rendering or initial data loading
 */
export function getComparisonIdsFromUrl(url: string): readonly string[] {
  try {
    const urlObj = new URL(url, 'http://localhost');
    const compareParam = urlObj.searchParams.get(COMPARISON_URL_PARAM);
    return parseVehicleIdsFromUrl(compareParam);
  } catch (error) {
    console.error('[useComparison] Failed to parse comparison IDs from URL:', error);
    return [];
  }
}

/**
 * Utility function to check if URL contains comparison parameters
 */
export function hasComparisonInUrl(url: string): boolean {
  try {
    const urlObj = new URL(url, 'http://localhost');
    return urlObj.searchParams.has(COMPARISON_URL_PARAM);
  } catch (error) {
    console.error('[useComparison] Failed to check comparison in URL:', error);
    return false;
  }
}