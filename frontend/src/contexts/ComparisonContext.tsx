/**
 * Vehicle Comparison Context
 * 
 * Manages state for vehicle comparison feature with localStorage persistence.
 * Supports up to 4 vehicles for side-by-side comparison.
 * 
 * @module contexts/ComparisonContext
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  type ReactNode,
} from 'react';
import type { Vehicle } from '../types/vehicle';

/**
 * Maximum number of vehicles that can be compared simultaneously
 */
const MAX_COMPARISON_VEHICLES = 4;

/**
 * LocalStorage key for persisting comparison state
 */
const STORAGE_KEY = 'autoselect_comparison_vehicles';

/**
 * Comparison context state interface
 */
interface ComparisonContextState {
  readonly vehicles: readonly Vehicle[];
  readonly isComparing: boolean;
  readonly canAddMore: boolean;
  readonly count: number;
  addVehicle: (vehicle: Vehicle) => boolean;
  removeVehicle: (vehicleId: string) => void;
  clearComparison: () => void;
  isVehicleInComparison: (vehicleId: string) => boolean;
  toggleVehicle: (vehicle: Vehicle) => void;
}

/**
 * Context provider props
 */
interface ComparisonProviderProps {
  readonly children: ReactNode;
}

/**
 * Comparison context with undefined default
 */
const ComparisonContext = createContext<ComparisonContextState | undefined>(undefined);

/**
 * Load vehicles from localStorage with error handling
 */
function loadVehiclesFromStorage(): readonly Vehicle[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return [];
    }

    const parsed = JSON.parse(stored) as unknown;
    
    if (!Array.isArray(parsed)) {
      console.warn('[ComparisonContext] Invalid stored data format, expected array');
      return [];
    }

    // Validate each vehicle has required properties
    const vehicles = parsed.filter((item): item is Vehicle => {
      return (
        typeof item === 'object' &&
        item !== null &&
        'id' in item &&
        'make' in item &&
        'model' in item &&
        'year' in item
      );
    });

    // Enforce maximum limit
    return vehicles.slice(0, MAX_COMPARISON_VEHICLES);
  } catch (error) {
    console.error('[ComparisonContext] Failed to load vehicles from storage:', error);
    return [];
  }
}

/**
 * Save vehicles to localStorage with error handling
 */
function saveVehiclesToStorage(vehicles: readonly Vehicle[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(vehicles));
  } catch (error) {
    console.error('[ComparisonContext] Failed to save vehicles to storage:', error);
  }
}

/**
 * Comparison Context Provider
 * 
 * Provides vehicle comparison state management with localStorage persistence.
 * Automatically syncs state across browser tabs/windows.
 */
export function ComparisonProvider({ children }: ComparisonProviderProps): JSX.Element {
  const [vehicles, setVehicles] = useState<readonly Vehicle[]>(() => 
    loadVehiclesFromStorage()
  );

  // Persist to localStorage whenever vehicles change
  useEffect(() => {
    saveVehiclesToStorage(vehicles);
  }, [vehicles]);

  // Sync state across tabs/windows
  useEffect(() => {
    const handleStorageChange = (event: StorageEvent): void => {
      if (event.key === STORAGE_KEY) {
        const newVehicles = loadVehiclesFromStorage();
        setVehicles(newVehicles);
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  /**
   * Add vehicle to comparison
   * Returns true if added successfully, false if limit reached or already exists
   */
  const addVehicle = useCallback((vehicle: Vehicle): boolean => {
    if (vehicles.length >= MAX_COMPARISON_VEHICLES) {
      console.warn(
        `[ComparisonContext] Cannot add vehicle: maximum of ${MAX_COMPARISON_VEHICLES} vehicles allowed`
      );
      return false;
    }

    if (vehicles.some((v) => v.id === vehicle.id)) {
      console.warn('[ComparisonContext] Vehicle already in comparison:', vehicle.id);
      return false;
    }

    setVehicles((prev) => [...prev, vehicle]);
    console.info('[ComparisonContext] Added vehicle to comparison:', vehicle.id);
    return true;
  }, [vehicles]);

  /**
   * Remove vehicle from comparison by ID
   */
  const removeVehicle = useCallback((vehicleId: string): void => {
    setVehicles((prev) => {
      const filtered = prev.filter((v) => v.id !== vehicleId);
      if (filtered.length === prev.length) {
        console.warn('[ComparisonContext] Vehicle not found in comparison:', vehicleId);
      } else {
        console.info('[ComparisonContext] Removed vehicle from comparison:', vehicleId);
      }
      return filtered;
    });
  }, []);

  /**
   * Clear all vehicles from comparison
   */
  const clearComparison = useCallback((): void => {
    setVehicles([]);
    console.info('[ComparisonContext] Cleared all vehicles from comparison');
  }, []);

  /**
   * Check if vehicle is in comparison
   */
  const isVehicleInComparison = useCallback(
    (vehicleId: string): boolean => {
      return vehicles.some((v) => v.id === vehicleId);
    },
    [vehicles]
  );

  /**
   * Toggle vehicle in comparison (add if not present, remove if present)
   */
  const toggleVehicle = useCallback(
    (vehicle: Vehicle): void => {
      if (isVehicleInComparison(vehicle.id)) {
        removeVehicle(vehicle.id);
      } else {
        addVehicle(vehicle);
      }
    },
    [isVehicleInComparison, removeVehicle, addVehicle]
  );

  /**
   * Memoized context value to prevent unnecessary re-renders
   */
  const contextValue = useMemo<ComparisonContextState>(
    () => ({
      vehicles,
      isComparing: vehicles.length > 0,
      canAddMore: vehicles.length < MAX_COMPARISON_VEHICLES,
      count: vehicles.length,
      addVehicle,
      removeVehicle,
      clearComparison,
      isVehicleInComparison,
      toggleVehicle,
    }),
    [vehicles, addVehicle, removeVehicle, clearComparison, isVehicleInComparison, toggleVehicle]
  );

  return (
    <ComparisonContext.Provider value={contextValue}>
      {children}
    </ComparisonContext.Provider>
  );
}

/**
 * Hook to access comparison context
 * 
 * @throws {Error} If used outside ComparisonProvider
 * 
 * @example
 * ```tsx
 * function VehicleCard({ vehicle }: { vehicle: Vehicle }) {
 *   const { addVehicle, isVehicleInComparison } = useComparison();
 *   const isInComparison = isVehicleInComparison(vehicle.id);
 *   
 *   return (
 *     <button onClick={() => addVehicle(vehicle)}>
 *       {isInComparison ? 'Remove from' : 'Add to'} Comparison
 *     </button>
 *   );
 * }
 * ```
 */
export function useComparison(): ComparisonContextState {
  const context = useContext(ComparisonContext);
  
  if (context === undefined) {
    throw new Error(
      '[useComparison] Hook must be used within ComparisonProvider. ' +
      'Wrap your component tree with <ComparisonProvider>.'
    );
  }
  
  return context;
}

/**
 * Export maximum comparison limit for use in other components
 */
export { MAX_COMPARISON_VEHICLES };