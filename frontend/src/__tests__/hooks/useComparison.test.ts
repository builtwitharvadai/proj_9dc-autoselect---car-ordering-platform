/**
 * Comprehensive Test Suite for useComparison Hook
 * 
 * Tests comparison state management, vehicle selection/deselection,
 * URL synchronization, localStorage persistence, and callback handling.
 * 
 * Coverage Target: >80%
 * Test Categories: Unit, Integration, Edge Cases
 * 
 * @module __tests__/hooks/useComparison.test
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { MemoryRouter, useSearchParams } from 'react-router-dom';
import { ReactNode } from 'react';
import {
  useComparison,
  MAX_COMPARISON_VEHICLES,
  MIN_COMPARISON_VEHICLES,
  COMPARISON_URL_PARAM,
  getComparisonIdsFromUrl,
  hasComparisonInUrl,
} from '../../hooks/useComparison';
import { ComparisonProvider } from '../../contexts/ComparisonContext';
import type { Vehicle } from '../../types/vehicle';

// ============================================================================
// 🏭 Test Data Factories
// ============================================================================

/**
 * Factory for creating test vehicle objects
 */
class VehicleFactory {
  private static counter = 0;

  static create(overrides: Partial<Vehicle> = {}): Vehicle {
    this.counter++;
    return {
      id: `vehicle-${this.counter}`,
      make: 'Toyota',
      model: 'Camry',
      year: 2024,
      price: 30000,
      trim: 'LE',
      engine: '2.5L 4-Cylinder',
      transmission: 'Automatic',
      drivetrain: 'FWD',
      fuelType: 'Gasoline',
      mpgCity: 28,
      mpgHighway: 39,
      horsepower: 203,
      torque: 184,
      seating: 5,
      ...overrides,
    };
  }

  static createMany(count: number, overrides: Partial<Vehicle> = {}): Vehicle[] {
    return Array.from({ length: count }, () => this.create(overrides));
  }

  static reset(): void {
    this.counter = 0;
  }
}

// ============================================================================
// 🎭 Test Utilities and Mocks
// ============================================================================

/**
 * Wrapper component providing necessary context and routing
 */
interface WrapperProps {
  children: ReactNode;
  initialUrl?: string;
}

function createWrapper(initialUrl = '/'): React.FC<WrapperProps> {
  return function Wrapper({ children }: WrapperProps) {
    return (
      <MemoryRouter initialEntries={[initialUrl]}>
        <ComparisonProvider>{children}</ComparisonProvider>
      </MemoryRouter>
    );
  };
}

/**
 * Mock localStorage for testing persistence
 */
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string): string | null => store[key] ?? null,
    setItem: (key: string, value: string): void => {
      store[key] = value;
    },
    removeItem: (key: string): void => {
      delete store[key];
    },
    clear: (): void => {
      store = {};
    },
    get length(): number {
      return Object.keys(store).length;
    },
    key: (index: number): string | null => Object.keys(store)[index] ?? null,
  };
})();

// ============================================================================
// 🧪 Test Suite Setup
// ============================================================================

describe('useComparison Hook', () => {
  beforeEach(() => {
    VehicleFactory.reset();
    localStorageMock.clear();
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
      writable: true,
    });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 🎯 Unit Tests - Basic Functionality
  // ==========================================================================

  describe('Basic Functionality', () => {
    it('should initialize with empty comparison state', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      expect(result.current.vehicles).toEqual([]);
      expect(result.current.count).toBe(0);
      expect(result.current.isComparing).toBe(false);
      expect(result.current.canAddMore).toBe(true);
      expect(result.current.canCompare).toBe(false);
      expect(result.current.maxVehicles).toBe(MAX_COMPARISON_VEHICLES);
    });

    it('should add a vehicle to comparison', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicle = VehicleFactory.create();

      act(() => {
        const success = result.current.addVehicle(vehicle);
        expect(success).toBe(true);
      });

      expect(result.current.vehicles).toHaveLength(1);
      expect(result.current.vehicles[0]).toEqual(vehicle);
      expect(result.current.count).toBe(1);
      expect(result.current.isComparing).toBe(true);
    });

    it('should remove a vehicle from comparison', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicle = VehicleFactory.create();

      act(() => {
        result.current.addVehicle(vehicle);
      });

      expect(result.current.vehicles).toHaveLength(1);

      act(() => {
        result.current.removeVehicle(vehicle.id);
      });

      expect(result.current.vehicles).toHaveLength(0);
      expect(result.current.count).toBe(0);
      expect(result.current.isComparing).toBe(false);
    });

    it('should clear all vehicles from comparison', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicles = VehicleFactory.createMany(3);

      act(() => {
        vehicles.forEach((vehicle) => result.current.addVehicle(vehicle));
      });

      expect(result.current.vehicles).toHaveLength(3);

      act(() => {
        result.current.clearComparison();
      });

      expect(result.current.vehicles).toHaveLength(0);
      expect(result.current.count).toBe(0);
      expect(result.current.isComparing).toBe(false);
    });

    it('should check if vehicle is in comparison', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicle = VehicleFactory.create();

      expect(result.current.isVehicleInComparison(vehicle.id)).toBe(false);

      act(() => {
        result.current.addVehicle(vehicle);
      });

      expect(result.current.isVehicleInComparison(vehicle.id)).toBe(true);
    });

    it('should toggle vehicle in comparison', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicle = VehicleFactory.create();

      act(() => {
        result.current.toggleVehicle(vehicle);
      });

      expect(result.current.vehicles).toHaveLength(1);
      expect(result.current.isVehicleInComparison(vehicle.id)).toBe(true);

      act(() => {
        result.current.toggleVehicle(vehicle);
      });

      expect(result.current.vehicles).toHaveLength(0);
      expect(result.current.isVehicleInComparison(vehicle.id)).toBe(false);
    });
  });

  // ==========================================================================
  // 🔢 Unit Tests - Vehicle Limits
  // ==========================================================================

  describe('Vehicle Limits', () => {
    it('should enforce maximum vehicle limit', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicles = VehicleFactory.createMany(MAX_COMPARISON_VEHICLES + 1);

      act(() => {
        vehicles.forEach((vehicle) => result.current.addVehicle(vehicle));
      });

      expect(result.current.vehicles).toHaveLength(MAX_COMPARISON_VEHICLES);
      expect(result.current.canAddMore).toBe(false);
    });

    it('should return false when adding vehicle beyond limit', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicles = VehicleFactory.createMany(MAX_COMPARISON_VEHICLES + 1);

      act(() => {
        vehicles.slice(0, MAX_COMPARISON_VEHICLES).forEach((vehicle) => {
          result.current.addVehicle(vehicle);
        });
      });

      let addResult: boolean = false;
      act(() => {
        addResult = result.current.addVehicle(vehicles[MAX_COMPARISON_VEHICLES]!);
      });

      expect(addResult).toBe(false);
      expect(result.current.vehicles).toHaveLength(MAX_COMPARISON_VEHICLES);
    });

    it('should allow adding more vehicles after removing one', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicles = VehicleFactory.createMany(MAX_COMPARISON_VEHICLES + 1);

      act(() => {
        vehicles.slice(0, MAX_COMPARISON_VEHICLES).forEach((vehicle) => {
          result.current.addVehicle(vehicle);
        });
      });

      expect(result.current.canAddMore).toBe(false);

      act(() => {
        result.current.removeVehicle(vehicles[0]!.id);
      });

      expect(result.current.canAddMore).toBe(true);

      act(() => {
        result.current.addVehicle(vehicles[MAX_COMPARISON_VEHICLES]!);
      });

      expect(result.current.vehicles).toHaveLength(MAX_COMPARISON_VEHICLES);
    });

    it('should update canCompare based on minimum vehicles', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      expect(result.current.canCompare).toBe(false);

      const vehicles = VehicleFactory.createMany(MIN_COMPARISON_VEHICLES);

      act(() => {
        result.current.addVehicle(vehicles[0]!);
      });

      expect(result.current.canCompare).toBe(false);

      act(() => {
        result.current.addVehicle(vehicles[1]!);
      });

      expect(result.current.canCompare).toBe(true);
    });
  });

  // ==========================================================================
  // 🔗 Integration Tests - Callbacks
  // ==========================================================================

  describe('Callback Handling', () => {
    it('should call onVehicleAdded callback when vehicle is added', () => {
      const onVehicleAdded = vi.fn();
      const { result } = renderHook(() => useComparison({ onVehicleAdded }), {
        wrapper: createWrapper(),
      });

      const vehicle = VehicleFactory.create();

      act(() => {
        result.current.addVehicle(vehicle);
      });

      expect(onVehicleAdded).toHaveBeenCalledTimes(1);
      expect(onVehicleAdded).toHaveBeenCalledWith(vehicle);
    });

    it('should not call onVehicleAdded when adding fails', () => {
      const onVehicleAdded = vi.fn();
      const { result } = renderHook(() => useComparison({ onVehicleAdded }), {
        wrapper: createWrapper(),
      });

      const vehicles = VehicleFactory.createMany(MAX_COMPARISON_VEHICLES + 1);

      act(() => {
        vehicles.slice(0, MAX_COMPARISON_VEHICLES).forEach((vehicle) => {
          result.current.addVehicle(vehicle);
        });
      });

      onVehicleAdded.mockClear();

      act(() => {
        result.current.addVehicle(vehicles[MAX_COMPARISON_VEHICLES]!);
      });

      expect(onVehicleAdded).not.toHaveBeenCalled();
    });

    it('should call onMaxReached when maximum limit is reached', () => {
      const onMaxReached = vi.fn();
      const { result } = renderHook(() => useComparison({ onMaxReached }), {
        wrapper: createWrapper(),
      });

      const vehicles = VehicleFactory.createMany(MAX_COMPARISON_VEHICLES + 1);

      act(() => {
        vehicles.forEach((vehicle) => result.current.addVehicle(vehicle));
      });

      expect(onMaxReached).toHaveBeenCalled();
    });

    it('should call onVehicleRemoved callback when vehicle is removed', () => {
      const onVehicleRemoved = vi.fn();
      const { result } = renderHook(() => useComparison({ onVehicleRemoved }), {
        wrapper: createWrapper(),
      });

      const vehicle = VehicleFactory.create();

      act(() => {
        result.current.addVehicle(vehicle);
      });

      act(() => {
        result.current.removeVehicle(vehicle.id);
      });

      expect(onVehicleRemoved).toHaveBeenCalledTimes(1);
      expect(onVehicleRemoved).toHaveBeenCalledWith(vehicle.id);
    });

    it('should call onComparisonCleared callback when comparison is cleared', () => {
      const onComparisonCleared = vi.fn();
      const { result } = renderHook(() => useComparison({ onComparisonCleared }), {
        wrapper: createWrapper(),
      });

      const vehicles = VehicleFactory.createMany(2);

      act(() => {
        vehicles.forEach((vehicle) => result.current.addVehicle(vehicle));
      });

      act(() => {
        result.current.clearComparison();
      });

      expect(onComparisonCleared).toHaveBeenCalledTimes(1);
    });
  });

  // ==========================================================================
  // 🌐 Integration Tests - URL Synchronization
  // ==========================================================================

  describe('URL Synchronization', () => {
    it('should not sync to URL when syncUrl is false', () => {
      const initialUrl = '/';
      const { result } = renderHook(
        () => {
          const comparison = useComparison({ syncUrl: false });
          const [searchParams] = useSearchParams();
          return { comparison, searchParams };
        },
        {
          wrapper: createWrapper(initialUrl),
        }
      );

      const vehicle = VehicleFactory.create();

      act(() => {
        result.current.comparison.addVehicle(vehicle);
      });

      expect(result.current.searchParams.has(COMPARISON_URL_PARAM)).toBe(false);
    });

    it('should sync to URL when syncUrl is true', async () => {
      const initialUrl = '/';
      const { result } = renderHook(
        () => {
          const comparison = useComparison({ syncUrl: true });
          const [searchParams] = useSearchParams();
          return { comparison, searchParams };
        },
        {
          wrapper: createWrapper(initialUrl),
        }
      );

      const vehicle = VehicleFactory.create();

      act(() => {
        result.current.comparison.addVehicle(vehicle);
      });

      await waitFor(() => {
        expect(result.current.searchParams.has(COMPARISON_URL_PARAM)).toBe(true);
      });
    });

    it('should generate correct comparison URL', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicles = VehicleFactory.createMany(2);

      act(() => {
        vehicles.forEach((vehicle) => result.current.addVehicle(vehicle));
      });

      const url = result.current.getComparisonUrl();
      expect(url).toContain('/compare?');
      expect(url).toContain(COMPARISON_URL_PARAM);
      expect(url).toContain(vehicles[0]!.id);
      expect(url).toContain(vehicles[1]!.id);
    });

    it('should return base URL when no vehicles in comparison', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const url = result.current.getComparisonUrl();
      expect(url).toBe('/compare');
    });

    it('should manually sync with URL', async () => {
      const { result } = renderHook(
        () => {
          const comparison = useComparison({ syncUrl: true });
          const [searchParams] = useSearchParams();
          return { comparison, searchParams };
        },
        {
          wrapper: createWrapper(),
        }
      );

      const vehicle = VehicleFactory.create();

      act(() => {
        result.current.comparison.addVehicle(vehicle);
      });

      act(() => {
        result.current.comparison.syncWithUrl();
      });

      await waitFor(() => {
        expect(result.current.searchParams.has(COMPARISON_URL_PARAM)).toBe(true);
      });
    });
  });

  // ==========================================================================
  // 🛡️ Edge Cases and Error Handling
  // ==========================================================================

  describe('Edge Cases', () => {
    it('should handle adding duplicate vehicle', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicle = VehicleFactory.create();

      act(() => {
        result.current.addVehicle(vehicle);
        result.current.addVehicle(vehicle);
      });

      expect(result.current.vehicles).toHaveLength(1);
    });

    it('should handle removing non-existent vehicle', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicle = VehicleFactory.create();

      act(() => {
        result.current.addVehicle(vehicle);
      });

      expect(result.current.vehicles).toHaveLength(1);

      act(() => {
        result.current.removeVehicle('non-existent-id');
      });

      expect(result.current.vehicles).toHaveLength(1);
    });

    it('should handle clearing empty comparison', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      expect(() => {
        act(() => {
          result.current.clearComparison();
        });
      }).not.toThrow();

      expect(result.current.vehicles).toHaveLength(0);
    });

    it('should handle toggling with empty comparison', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicle = VehicleFactory.create();

      expect(() => {
        act(() => {
          result.current.toggleVehicle(vehicle);
        });
      }).not.toThrow();

      expect(result.current.vehicles).toHaveLength(1);
    });

    it('should maintain immutability of vehicles array', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicle = VehicleFactory.create();

      act(() => {
        result.current.addVehicle(vehicle);
      });

      const vehiclesRef1 = result.current.vehicles;

      act(() => {
        result.current.addVehicle(VehicleFactory.create());
      });

      const vehiclesRef2 = result.current.vehicles;

      expect(vehiclesRef1).not.toBe(vehiclesRef2);
    });
  });

  // ==========================================================================
  // 🔧 Utility Functions Tests
  // ==========================================================================

  describe('Utility Functions', () => {
    describe('getComparisonIdsFromUrl', () => {
      it('should parse vehicle IDs from valid URL', () => {
        const vehicleIds = ['id-1', 'id-2', 'id-3'];
        const url = `http://example.com/compare?${COMPARISON_URL_PARAM}=${vehicleIds.join(',')}`;

        const result = getComparisonIdsFromUrl(url);

        expect(result).toEqual(vehicleIds);
      });

      it('should return empty array for URL without comparison param', () => {
        const url = 'http://example.com/compare';

        const result = getComparisonIdsFromUrl(url);

        expect(result).toEqual([]);
      });

      it('should handle malformed URLs gracefully', () => {
        const url = 'not-a-valid-url';

        const result = getComparisonIdsFromUrl(url);

        expect(result).toEqual([]);
      });

      it('should filter out invalid UUID formats', () => {
        const validId = '550e8400-e29b-41d4-a716-446655440000';
        const invalidId = 'invalid-id';
        const url = `http://example.com/compare?${COMPARISON_URL_PARAM}=${validId},${invalidId}`;

        const result = getComparisonIdsFromUrl(url);

        expect(result).toEqual([validId]);
      });

      it('should enforce maximum vehicle limit in URL parsing', () => {
        const vehicleIds = Array.from(
          { length: MAX_COMPARISON_VEHICLES + 2 },
          (_, i) => `550e8400-e29b-41d4-a716-44665544000${i}`
        );
        const url = `http://example.com/compare?${COMPARISON_URL_PARAM}=${vehicleIds.join(',')}`;

        const result = getComparisonIdsFromUrl(url);

        expect(result).toHaveLength(MAX_COMPARISON_VEHICLES);
      });
    });

    describe('hasComparisonInUrl', () => {
      it('should return true when comparison param exists', () => {
        const url = `http://example.com/compare?${COMPARISON_URL_PARAM}=id-1,id-2`;

        const result = hasComparisonInUrl(url);

        expect(result).toBe(true);
      });

      it('should return false when comparison param does not exist', () => {
        const url = 'http://example.com/compare';

        const result = hasComparisonInUrl(url);

        expect(result).toBe(false);
      });

      it('should handle malformed URLs gracefully', () => {
        const url = 'not-a-valid-url';

        const result = hasComparisonInUrl(url);

        expect(result).toBe(false);
      });

      it('should return true even with empty comparison param', () => {
        const url = `http://example.com/compare?${COMPARISON_URL_PARAM}=`;

        const result = hasComparisonInUrl(url);

        expect(result).toBe(true);
      });
    });
  });

  // ==========================================================================
  // ⚡ Performance Tests
  // ==========================================================================

  describe('Performance', () => {
    it('should handle rapid vehicle additions efficiently', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicles = VehicleFactory.createMany(MAX_COMPARISON_VEHICLES);

      const startTime = performance.now();

      act(() => {
        vehicles.forEach((vehicle) => result.current.addVehicle(vehicle));
      });

      const endTime = performance.now();
      const executionTime = endTime - startTime;

      expect(executionTime).toBeLessThan(100); // Should complete in < 100ms
      expect(result.current.vehicles).toHaveLength(MAX_COMPARISON_VEHICLES);
    });

    it('should handle rapid vehicle removals efficiently', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicles = VehicleFactory.createMany(MAX_COMPARISON_VEHICLES);

      act(() => {
        vehicles.forEach((vehicle) => result.current.addVehicle(vehicle));
      });

      const startTime = performance.now();

      act(() => {
        vehicles.forEach((vehicle) => result.current.removeVehicle(vehicle.id));
      });

      const endTime = performance.now();
      const executionTime = endTime - startTime;

      expect(executionTime).toBeLessThan(100); // Should complete in < 100ms
      expect(result.current.vehicles).toHaveLength(0);
    });

    it('should memoize return values to prevent unnecessary re-renders', () => {
      const { result, rerender } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const initialReturn = result.current;

      rerender();

      expect(result.current).toBe(initialReturn);
    });
  });

  // ==========================================================================
  // 🔄 State Consistency Tests
  // ==========================================================================

  describe('State Consistency', () => {
    it('should maintain consistent state across multiple operations', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicles = VehicleFactory.createMany(3);

      act(() => {
        result.current.addVehicle(vehicles[0]!);
        result.current.addVehicle(vehicles[1]!);
        result.current.addVehicle(vehicles[2]!);
      });

      expect(result.current.count).toBe(3);
      expect(result.current.vehicles).toHaveLength(3);
      expect(result.current.isComparing).toBe(true);

      act(() => {
        result.current.removeVehicle(vehicles[1]!.id);
      });

      expect(result.current.count).toBe(2);
      expect(result.current.vehicles).toHaveLength(2);
      expect(result.current.isComparing).toBe(true);

      act(() => {
        result.current.clearComparison();
      });

      expect(result.current.count).toBe(0);
      expect(result.current.vehicles).toHaveLength(0);
      expect(result.current.isComparing).toBe(false);
    });

    it('should correctly update canAddMore flag', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      expect(result.current.canAddMore).toBe(true);

      const vehicles = VehicleFactory.createMany(MAX_COMPARISON_VEHICLES);

      act(() => {
        vehicles.forEach((vehicle, index) => {
          result.current.addVehicle(vehicle);
          if (index < MAX_COMPARISON_VEHICLES - 1) {
            expect(result.current.canAddMore).toBe(true);
          }
        });
      });

      expect(result.current.canAddMore).toBe(false);

      act(() => {
        result.current.removeVehicle(vehicles[0]!.id);
      });

      expect(result.current.canAddMore).toBe(true);
    });

    it('should correctly update canCompare flag', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      expect(result.current.canCompare).toBe(false);

      const vehicles = VehicleFactory.createMany(MIN_COMPARISON_VEHICLES);

      act(() => {
        result.current.addVehicle(vehicles[0]!);
      });

      expect(result.current.canCompare).toBe(false);

      act(() => {
        result.current.addVehicle(vehicles[1]!);
      });

      expect(result.current.canCompare).toBe(true);

      act(() => {
        result.current.removeVehicle(vehicles[0]!.id);
      });

      expect(result.current.canCompare).toBe(false);
    });
  });

  // ==========================================================================
  // 🎭 Complex Scenarios
  // ==========================================================================

  describe('Complex Scenarios', () => {
    it('should handle complete user workflow', () => {
      const onVehicleAdded = vi.fn();
      const onVehicleRemoved = vi.fn();
      const onComparisonCleared = vi.fn();

      const { result } = renderHook(
        () =>
          useComparison({
            syncUrl: true,
            onVehicleAdded,
            onVehicleRemoved,
            onComparisonCleared,
          }),
        {
          wrapper: createWrapper(),
        }
      );

      const vehicles = VehicleFactory.createMany(4);

      // Add vehicles one by one
      act(() => {
        result.current.addVehicle(vehicles[0]!);
      });
      expect(onVehicleAdded).toHaveBeenCalledTimes(1);
      expect(result.current.canCompare).toBe(false);

      act(() => {
        result.current.addVehicle(vehicles[1]!);
      });
      expect(onVehicleAdded).toHaveBeenCalledTimes(2);
      expect(result.current.canCompare).toBe(true);

      act(() => {
        result.current.addVehicle(vehicles[2]!);
      });
      expect(onVehicleAdded).toHaveBeenCalledTimes(3);

      // Remove one vehicle
      act(() => {
        result.current.removeVehicle(vehicles[1]!.id);
      });
      expect(onVehicleRemoved).toHaveBeenCalledTimes(1);
      expect(result.current.vehicles).toHaveLength(2);

      // Add another vehicle
      act(() => {
        result.current.addVehicle(vehicles[3]!);
      });
      expect(onVehicleAdded).toHaveBeenCalledTimes(4);
      expect(result.current.vehicles).toHaveLength(3);

      // Clear comparison
      act(() => {
        result.current.clearComparison();
      });
      expect(onComparisonCleared).toHaveBeenCalledTimes(1);
      expect(result.current.vehicles).toHaveLength(0);
    });

    it('should handle toggle operations correctly', () => {
      const { result } = renderHook(() => useComparison(), {
        wrapper: createWrapper(),
      });

      const vehicle = VehicleFactory.create();

      // Toggle on
      act(() => {
        result.current.toggleVehicle(vehicle);
      });
      expect(result.current.isVehicleInComparison(vehicle.id)).toBe(true);

      // Toggle off
      act(() => {
        result.current.toggleVehicle(vehicle);
      });
      expect(result.current.isVehicleInComparison(vehicle.id)).toBe(false);

      // Toggle on again
      act(() => {
        result.current.toggleVehicle(vehicle);
      });
      expect(result.current.isVehicleInComparison(vehicle.id)).toBe(true);
    });
  });
});