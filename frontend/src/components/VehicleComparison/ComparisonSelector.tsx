/**
 * Vehicle Comparison Selector Component
 * 
 * Provides interface for selecting vehicles to add to comparison with search,
 * filtering, and visual indication of selected vehicles. Supports up to 4
 * vehicle selections with real-time availability checking.
 * 
 * @module components/VehicleComparison/ComparisonSelector
 */

import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useComparison } from '../../hooks/useComparison';
import { useVehicles } from '../../hooks/useVehicles';
import type { Vehicle, VehicleFilters } from '../../types/vehicle';

/**
 * Component props interface
 */
interface ComparisonSelectorProps {
  readonly className?: string;
  readonly onVehicleAdded?: (vehicle: Vehicle) => void;
  readonly onVehicleRemoved?: (vehicleId: string) => void;
  readonly onMaxReached?: () => void;
  readonly autoFocus?: boolean;
  readonly showSelectedCount?: boolean;
}

/**
 * Default page size for vehicle results
 */
const DEFAULT_PAGE_SIZE = 12;

/**
 * Debounce delay for search input (ms)
 */
const SEARCH_DEBOUNCE_MS = 300;

/**
 * Vehicle Comparison Selector Component
 * 
 * Renders search interface with vehicle cards for comparison selection.
 * Includes real-time search, filtering, and visual feedback for selected vehicles.
 * 
 * @example
 * ```tsx
 * <ComparisonSelector
 *   onVehicleAdded={(vehicle) => console.log('Added:', vehicle)}
 *   onMaxReached={() => alert('Maximum 4 vehicles')}
 *   showSelectedCount
 * />
 * ```
 */
export default function ComparisonSelector({
  className = '',
  onVehicleAdded,
  onVehicleRemoved,
  onMaxReached,
  autoFocus = false,
  showSelectedCount = true,
}: ComparisonSelectorProps): JSX.Element {
  const {
    vehicles: selectedVehicles,
    addVehicle,
    removeVehicle,
    isVehicleInComparison,
    canAddMore,
    count: selectedCount,
    maxVehicles,
  } = useComparison({
    onVehicleAdded,
    onVehicleRemoved,
    onMaxReached,
  });

  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [filters, setFilters] = useState<VehicleFilters>({});
  const [currentPage, setCurrentPage] = useState(1);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Auto-focus search input on mount
   */
  useEffect(() => {
    if (autoFocus && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [autoFocus]);

  /**
   * Debounce search query updates
   */
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setCurrentPage(1);
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [searchQuery]);

  /**
   * Build search parameters
   */
  const searchParams = useMemo(
    () => ({
      filters: {
        ...filters,
        query: debouncedQuery || undefined,
      },
      page: currentPage,
      pageSize: DEFAULT_PAGE_SIZE,
      sortBy: 'relevance' as const,
    }),
    [filters, debouncedQuery, currentPage]
  );

  /**
   * Fetch vehicles with search and filters
   */
  const {
    data: vehiclesData,
    isLoading,
    isError,
    error,
  } = useVehicles(searchParams, {
    keepPreviousData: true,
  });

  /**
   * Handle search input change
   */
  const handleSearchChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setSearchQuery(value);
  }, []);

  /**
   * Handle search clear
   */
  const handleSearchClear = useCallback(() => {
    setSearchQuery('');
    setDebouncedQuery('');
    setCurrentPage(1);
    if (searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, []);

  /**
   * Handle vehicle selection toggle
   */
  const handleVehicleToggle = useCallback(
    (vehicle: Vehicle) => {
      const isSelected = isVehicleInComparison(vehicle.id);

      if (isSelected) {
        removeVehicle(vehicle.id);
      } else {
        if (!canAddMore) {
          onMaxReached?.();
          return;
        }
        addVehicle(vehicle);
      }
    },
    [isVehicleInComparison, removeVehicle, canAddMore, addVehicle, onMaxReached]
  );

  /**
   * Handle filter changes
   */
  const handleFilterChange = useCallback((newFilters: Partial<VehicleFilters>) => {
    setFilters((prev) => ({
      ...prev,
      ...newFilters,
    }));
    setCurrentPage(1);
  }, []);

  /**
   * Handle pagination
   */
  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  /**
   * Calculate total pages
   */
  const totalPages = useMemo(() => {
    if (!vehiclesData?.metadata) {
      return 1;
    }
    return Math.ceil(vehiclesData.metadata.total / DEFAULT_PAGE_SIZE);
  }, [vehiclesData?.metadata]);

  /**
   * Render vehicle card
   */
  const renderVehicleCard = useCallback(
    (vehicle: Vehicle) => {
      const isSelected = isVehicleInComparison(vehicle.id);
      const isDisabled = !isSelected && !canAddMore;

      return (
        <div
          key={vehicle.id}
          className={`
            relative rounded-lg border-2 p-4 transition-all duration-200
            ${isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white'}
            ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-lg cursor-pointer'}
          `}
          onClick={() => !isDisabled && handleVehicleToggle(vehicle)}
          role="button"
          tabIndex={isDisabled ? -1 : 0}
          aria-pressed={isSelected}
          aria-label={`${isSelected ? 'Remove' : 'Add'} ${vehicle.year} ${vehicle.make} ${vehicle.model} ${isSelected ? 'from' : 'to'} comparison`}
          onKeyDown={(e) => {
            if ((e.key === 'Enter' || e.key === ' ') && !isDisabled) {
              e.preventDefault();
              handleVehicleToggle(vehicle);
            }
          }}
        >
          {isSelected && (
            <div className="absolute top-2 right-2 z-10">
              <div className="flex items-center justify-center w-8 h-8 bg-blue-500 rounded-full">
                <svg
                  className="w-5 h-5 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
            </div>
          )}

          <div className="space-y-3">
            <div className="aspect-video bg-gray-100 rounded-md overflow-hidden">
              {vehicle.imageUrl ? (
                <img
                  src={vehicle.imageUrl}
                  alt={`${vehicle.year} ${vehicle.make} ${vehicle.model}`}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-400">
                  <svg
                    className="w-16 h-16"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                  </svg>
                </div>
              )}
            </div>

            <div>
              <h3 className="font-semibold text-lg text-gray-900">
                {vehicle.year} {vehicle.make} {vehicle.model}
              </h3>
              {vehicle.trim && (
                <p className="text-sm text-gray-600">{vehicle.trim}</p>
              )}
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xl font-bold text-gray-900">
                ${vehicle.price.toLocaleString()}
              </span>
              {vehicle.availability && (
                <span
                  className={`
                    px-2 py-1 text-xs font-medium rounded-full
                    ${vehicle.availability === 'available' ? 'bg-green-100 text-green-800' : ''}
                    ${vehicle.availability === 'reserved' ? 'bg-yellow-100 text-yellow-800' : ''}
                    ${vehicle.availability === 'sold' ? 'bg-red-100 text-red-800' : ''}
                    ${vehicle.availability === 'unavailable' ? 'bg-gray-100 text-gray-800' : ''}
                  `}
                >
                  {vehicle.availability}
                </span>
              )}
            </div>

            <button
              type="button"
              className={`
                w-full py-2 px-4 rounded-md font-medium transition-colors
                ${isSelected ? 'bg-red-500 hover:bg-red-600 text-white' : 'bg-blue-500 hover:bg-blue-600 text-white'}
                ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''}
              `}
              onClick={(e) => {
                e.stopPropagation();
                if (!isDisabled) {
                  handleVehicleToggle(vehicle);
                }
              }}
              disabled={isDisabled}
              aria-label={`${isSelected ? 'Remove' : 'Add'} vehicle ${isSelected ? 'from' : 'to'} comparison`}
            >
              {isSelected ? 'Remove from Comparison' : 'Add to Comparison'}
            </button>
          </div>
        </div>
      );
    },
    [isVehicleInComparison, canAddMore, handleVehicleToggle]
  );

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header with selected count */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">
          Select Vehicles to Compare
        </h2>
        {showSelectedCount && (
          <div className="text-sm text-gray-600">
            <span className="font-semibold">{selectedCount}</span> / {maxVehicles} selected
          </div>
        )}
      </div>

      {/* Search bar */}
      <div className="relative">
        <div className="relative">
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={handleSearchChange}
            placeholder="Search by make, model, or year..."
            className="w-full px-4 py-3 pl-12 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            aria-label="Search vehicles"
          />
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">
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
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
          {searchQuery && (
            <button
              type="button"
              onClick={handleSearchClear}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              aria-label="Clear search"
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
          )}
        </div>
      </div>

      {/* Selected vehicles preview */}
      {selectedCount > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-semibold text-gray-900 mb-2">Selected for Comparison:</h3>
          <div className="flex flex-wrap gap-2">
            {selectedVehicles.map((vehicle) => (
              <div
                key={vehicle.id}
                className="inline-flex items-center gap-2 bg-white px-3 py-1 rounded-full border border-blue-300"
              >
                <span className="text-sm text-gray-700">
                  {vehicle.year} {vehicle.make} {vehicle.model}
                </span>
                <button
                  type="button"
                  onClick={() => removeVehicle(vehicle.id)}
                  className="text-gray-400 hover:text-red-500"
                  aria-label={`Remove ${vehicle.year} ${vehicle.make} ${vehicle.model} from comparison`}
                >
                  <svg
                    className="w-4 h-4"
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
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          <p className="font-semibold">Error loading vehicles</p>
          <p className="text-sm mt-1">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
        </div>
      )}

      {/* Vehicle grid */}
      {!isLoading && !isError && vehiclesData && (
        <>
          {vehiclesData.vehicles.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 text-lg">No vehicles found</p>
              <p className="text-gray-400 text-sm mt-2">
                Try adjusting your search or filters
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {vehiclesData.vehicles.map(renderVehicleCard)}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button
                type="button"
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="px-4 py-2 border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                aria-label="Previous page"
              >
                Previous
              </button>
              <div className="flex items-center gap-2">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const page = i + 1;
                  return (
                    <button
                      key={page}
                      type="button"
                      onClick={() => handlePageChange(page)}
                      className={`
                        px-4 py-2 border rounded-md
                        ${currentPage === page ? 'bg-blue-500 text-white border-blue-500' : 'border-gray-300 hover:bg-gray-50'}
                      `}
                      aria-label={`Page ${page}`}
                      aria-current={currentPage === page ? 'page' : undefined}
                    >
                      {page}
                    </button>
                  );
                })}
              </div>
              <button
                type="button"
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="px-4 py-2 border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                aria-label="Next page"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}