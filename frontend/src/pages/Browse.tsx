import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import VehicleGrid from '../components/VehicleBrowsing/VehicleGrid';
import VehicleList from '../components/VehicleBrowsing/VehicleList';
import FilterSidebar from '../components/VehicleBrowsing/FilterSidebar';
import ViewToggle from '../components/VehicleBrowsing/ViewToggle';
import InfiniteScroll from '../components/VehicleBrowsing/InfiniteScroll';
import { useVehicles } from '../hooks/useVehicles';
import type { VehicleFilters, Vehicle } from '../types/vehicle';

type ViewMode = 'grid' | 'list';

interface BrowseState {
  readonly viewMode: ViewMode;
  readonly isFilterSidebarOpen: boolean;
  readonly page: number;
}

const DEFAULT_PAGE_SIZE = 20;

function parseFiltersFromURL(searchParams: URLSearchParams): VehicleFilters {
  const filters: VehicleFilters = {};

  const make = searchParams.getAll('make');
  if (make.length > 0) {
    filters.make = make;
  }

  const model = searchParams.getAll('model');
  if (model.length > 0) {
    filters.model = model;
  }

  const bodyStyle = searchParams.getAll('bodyStyle');
  if (bodyStyle.length > 0) {
    filters.bodyStyle = bodyStyle as VehicleFilters['bodyStyle'];
  }

  const fuelType = searchParams.getAll('fuelType');
  if (fuelType.length > 0) {
    filters.fuelType = fuelType as VehicleFilters['fuelType'];
  }

  const transmission = searchParams.getAll('transmission');
  if (transmission.length > 0) {
    filters.transmission = transmission as VehicleFilters['transmission'];
  }

  const drivetrain = searchParams.getAll('drivetrain');
  if (drivetrain.length > 0) {
    filters.drivetrain = drivetrain as VehicleFilters['drivetrain'];
  }

  const minPrice = searchParams.get('minPrice');
  const maxPrice = searchParams.get('maxPrice');
  if (minPrice !== null || maxPrice !== null) {
    filters.price = {
      min: minPrice !== null ? Number(minPrice) : undefined,
      max: maxPrice !== null ? Number(maxPrice) : undefined,
    };
  }

  const minYear = searchParams.get('minYear');
  const maxYear = searchParams.get('maxYear');
  if (minYear !== null || maxYear !== null) {
    filters.year = {
      min: minYear !== null ? Number(minYear) : undefined,
      max: maxYear !== null ? Number(maxYear) : undefined,
    };
  }

  const search = searchParams.get('search');
  if (search !== null) {
    filters.search = search;
  }

  const sortBy = searchParams.get('sortBy');
  if (sortBy !== null) {
    filters.sortBy = sortBy as VehicleFilters['sortBy'];
  }

  const sortOrder = searchParams.get('sortOrder');
  if (sortOrder !== null) {
    filters.sortOrder = sortOrder as VehicleFilters['sortOrder'];
  }

  return filters;
}

function serializeFiltersToURL(filters: VehicleFilters): URLSearchParams {
  const params = new URLSearchParams();

  if (filters.make !== undefined && filters.make.length > 0) {
    filters.make.forEach((m) => params.append('make', m));
  }

  if (filters.model !== undefined && filters.model.length > 0) {
    filters.model.forEach((m) => params.append('model', m));
  }

  if (filters.bodyStyle !== undefined && filters.bodyStyle.length > 0) {
    filters.bodyStyle.forEach((b) => params.append('bodyStyle', b));
  }

  if (filters.fuelType !== undefined && filters.fuelType.length > 0) {
    filters.fuelType.forEach((f) => params.append('fuelType', f));
  }

  if (filters.transmission !== undefined && filters.transmission.length > 0) {
    filters.transmission.forEach((t) => params.append('transmission', t));
  }

  if (filters.drivetrain !== undefined && filters.drivetrain.length > 0) {
    filters.drivetrain.forEach((d) => params.append('drivetrain', d));
  }

  if (filters.price !== undefined) {
    if (filters.price.min !== undefined) {
      params.set('minPrice', filters.price.min.toString());
    }
    if (filters.price.max !== undefined) {
      params.set('maxPrice', filters.price.max.toString());
    }
  }

  if (filters.year !== undefined) {
    if (filters.year.min !== undefined) {
      params.set('minYear', filters.year.min.toString());
    }
    if (filters.year.max !== undefined) {
      params.set('maxYear', filters.year.max.toString());
    }
  }

  if (filters.search !== undefined) {
    params.set('search', filters.search);
  }

  if (filters.sortBy !== undefined) {
    params.set('sortBy', filters.sortBy);
  }

  if (filters.sortOrder !== undefined) {
    params.set('sortOrder', filters.sortOrder);
  }

  return params;
}

export default function Browse(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [state, setState] = useState<BrowseState>({
    viewMode: 'grid',
    isFilterSidebarOpen: false,
    page: 1,
  });

  const filters = useMemo(() => parseFiltersFromURL(searchParams), [searchParams]);

  const {
    data: vehiclesData,
    isLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useVehicles({
    filters,
    page: state.page,
    pageSize: DEFAULT_PAGE_SIZE,
  });

  const vehicles = useMemo(() => {
    if (vehiclesData === undefined) return [];
    return vehiclesData.pages.flatMap((page) => page.vehicles);
  }, [vehiclesData]);

  const totalCount = vehiclesData?.pages[0]?.total ?? 0;

  const handleFiltersChange = useCallback(
    (newFilters: VehicleFilters) => {
      const params = serializeFiltersToURL(newFilters);
      setSearchParams(params, { replace: true });
      setState((prev) => ({ ...prev, page: 1 }));
    },
    [setSearchParams],
  );

  const handleViewChange = useCallback((newView: ViewMode) => {
    setState((prev) => ({ ...prev, viewMode: newView }));
  }, []);

  const handleToggleFilterSidebar = useCallback(() => {
    setState((prev) => ({ ...prev, isFilterSidebarOpen: !prev.isFilterSidebarOpen }));
  }, []);

  const handleCloseFilterSidebar = useCallback(() => {
    setState((prev) => ({ ...prev, isFilterSidebarOpen: false }));
  }, []);

  const handleVehicleClick = useCallback(
    (vehicle: Vehicle) => {
      navigate(`/vehicles/${vehicle.id}`);
    },
    [navigate],
  );

  const handleLoadMore = useCallback(async () => {
    if (hasNextPage && !isFetchingNextPage) {
      await fetchNextPage();
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [filters]);

  return (
    <div className="min-h-screen bg-[rgb(var(--color-gray-50))] pt-16">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[rgb(var(--color-gray-900))] sm:text-4xl">
            Browse Vehicles
          </h1>
          <p className="mt-2 text-base text-[rgb(var(--color-gray-600))] sm:text-lg">
            Discover your perfect vehicle from our extensive collection
          </p>
        </div>

        <div className="flex gap-8">
          <FilterSidebar
            filters={filters}
            onFiltersChange={handleFiltersChange}
            isOpen={state.isFilterSidebarOpen}
            onClose={handleCloseFilterSidebar}
            className="w-80 flex-shrink-0"
          />

          <div className="flex-1 min-w-0">
            <div className="mb-6 flex items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <button
                  type="button"
                  onClick={handleToggleFilterSidebar}
                  className="inline-flex items-center gap-2 rounded-[var(--radius-md)] bg-white px-4 py-2 text-sm font-medium text-[rgb(var(--color-gray-700))] shadow-[var(--shadow-sm)] transition-colors duration-[var(--transition-fast)] hover:bg-[rgb(var(--color-gray-50))] focus:outline-none focus:ring-2 focus:ring-[rgb(var(--color-primary-500))] focus:ring-offset-2 lg:hidden"
                  aria-label="Toggle filters"
                >
                  <svg
                    className="h-5 w-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
                    />
                  </svg>
                  Filters
                </button>

                <p className="text-sm text-[rgb(var(--color-gray-600))]">
                  {isLoading ? (
                    'Loading...'
                  ) : (
                    <>
                      Showing {vehicles.length} of {totalCount} vehicles
                    </>
                  )}
                </p>
              </div>

              <ViewToggle defaultView={state.viewMode} onViewChange={handleViewChange} />
            </div>

            {error !== null && error !== undefined ? (
              <div
                className="rounded-[var(--radius-lg)] bg-red-50 p-6 text-center"
                role="alert"
              >
                <svg
                  className="mx-auto h-12 w-12 text-red-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <h3 className="mt-4 text-lg font-medium text-[rgb(var(--color-gray-900))]">
                  Failed to load vehicles
                </h3>
                <p className="mt-2 text-sm text-[rgb(var(--color-gray-600))]">
                  {error instanceof Error ? error.message : 'An unexpected error occurred'}
                </p>
              </div>
            ) : (
              <InfiniteScroll
                onLoadMore={handleLoadMore}
                hasMore={hasNextPage ?? false}
                isLoading={isFetchingNextPage}
                ariaLabel="Vehicle list"
              >
                {state.viewMode === 'grid' ? (
                  <VehicleGrid
                    vehicles={vehicles}
                    isLoading={isLoading}
                    onVehicleClick={handleVehicleClick}
                  />
                ) : (
                  <VehicleList
                    vehicles={vehicles}
                    isLoading={isLoading}
                    onViewDetails={(vehicleId) => {
                      const vehicle = vehicles.find((v) => v.id === vehicleId);
                      if (vehicle !== undefined) {
                        handleVehicleClick(vehicle);
                      }
                    }}
                  />
                )}
              </InfiniteScroll>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}