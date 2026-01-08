/**
 * React Query hooks for vehicle data fetching and management
 * Provides type-safe hooks for vehicle browsing, search, and filtering with caching and background refetching
 */

import {
  useQuery,
  useInfiniteQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseInfiniteQueryOptions,
  type UseMutationOptions,
  type InfiniteData,
} from '@tanstack/react-query';
import type {
  Vehicle,
  VehicleListResponse,
  VehicleDetailResponse,
  SearchParams,
  VehicleFilters,
  SearchFacets,
  PriceRangeResponse,
  ApiErrorResponse,
} from '../types/vehicle';

/**
 * API base URL from environment variables
 */
const API_BASE_URL = import.meta.env['VITE_API_BASE_URL'] ?? 'http://localhost:8000';

/**
 * Query key factory for vehicle-related queries
 */
export const vehicleKeys = {
  all: ['vehicles'] as const,
  lists: () => [...vehicleKeys.all, 'list'] as const,
  list: (params: SearchParams) => [...vehicleKeys.lists(), params] as const,
  details: () => [...vehicleKeys.all, 'detail'] as const,
  detail: (id: string) => [...vehicleKeys.details(), id] as const,
  search: (params: SearchParams) => [...vehicleKeys.all, 'search', params] as const,
  facets: (filters?: VehicleFilters) => [...vehicleKeys.all, 'facets', filters] as const,
  priceRange: (filters?: VehicleFilters) =>
    [...vehicleKeys.all, 'priceRange', filters] as const,
} as const;

/**
 * Default stale time for vehicle queries (5 minutes)
 */
const DEFAULT_STALE_TIME = 5 * 60 * 1000;

/**
 * Default cache time for vehicle queries (10 minutes)
 */
const DEFAULT_CACHE_TIME = 10 * 60 * 1000;

/**
 * Fetch vehicles with pagination and filtering
 */
async function fetchVehicles(params: SearchParams): Promise<VehicleListResponse> {
  const queryParams = new URLSearchParams();

  if (params.filters?.query) {
    queryParams.append('query', params.filters.query);
  }

  if (params.filters?.make && params.filters.make.length > 0) {
    params.filters.make.forEach((make) => queryParams.append('make', make));
  }

  if (params.filters?.model && params.filters.model.length > 0) {
    params.filters.model.forEach((model) => queryParams.append('model', model));
  }

  if (params.filters?.bodyStyle && params.filters.bodyStyle.length > 0) {
    params.filters.bodyStyle.forEach((style) => queryParams.append('body_style', style));
  }

  if (params.filters?.fuelType && params.filters.fuelType.length > 0) {
    params.filters.fuelType.forEach((fuel) => queryParams.append('fuel_type', fuel));
  }

  if (params.filters?.transmission && params.filters.transmission.length > 0) {
    params.filters.transmission.forEach((trans) => queryParams.append('transmission', trans));
  }

  if (params.filters?.drivetrain && params.filters.drivetrain.length > 0) {
    params.filters.drivetrain.forEach((drive) => queryParams.append('drivetrain', drive));
  }

  if (params.filters?.year) {
    if (params.filters.year.min !== undefined) {
      queryParams.append('year_min', params.filters.year.min.toString());
    }
    if (params.filters.year.max !== undefined) {
      queryParams.append('year_max', params.filters.year.max.toString());
    }
  }

  if (params.filters?.price) {
    if (params.filters.price.min !== undefined) {
      queryParams.append('price_min', params.filters.price.min.toString());
    }
    if (params.filters.price.max !== undefined) {
      queryParams.append('price_max', params.filters.price.max.toString());
    }
  }

  if (params.filters?.seatingCapacity) {
    if (params.filters.seatingCapacity.min !== undefined) {
      queryParams.append('seating_min', params.filters.seatingCapacity.min.toString());
    }
    if (params.filters.seatingCapacity.max !== undefined) {
      queryParams.append('seating_max', params.filters.seatingCapacity.max.toString());
    }
  }

  if (params.filters?.availability && params.filters.availability.length > 0) {
    params.filters.availability.forEach((status) => queryParams.append('availability', status));
  }

  if (params.sortBy) {
    queryParams.append('sort_by', params.sortBy);
  }

  if (params.sortDirection) {
    queryParams.append('sort_direction', params.sortDirection);
  }

  if (params.page !== undefined) {
    queryParams.append('page', params.page.toString());
  }

  if (params.pageSize !== undefined) {
    queryParams.append('page_size', params.pageSize.toString());
  }

  if (params.includeInventory !== undefined) {
    queryParams.append('include_inventory', params.includeInventory.toString());
  }

  const url = `${API_BASE_URL}/api/v1/vehicles?${queryParams.toString()}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error: ApiErrorResponse = await response.json();
    throw new Error(error.message ?? 'Failed to fetch vehicles');
  }

  return response.json();
}

/**
 * Fetch a single vehicle by ID
 */
async function fetchVehicleById(id: string): Promise<VehicleDetailResponse> {
  const url = `${API_BASE_URL}/api/v1/vehicles/${id}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error: ApiErrorResponse = await response.json();
    throw new Error(error.message ?? 'Failed to fetch vehicle');
  }

  return response.json();
}

/**
 * Fetch search facets for filtering
 */
async function fetchSearchFacets(filters?: VehicleFilters): Promise<SearchFacets> {
  const queryParams = new URLSearchParams();

  if (filters?.query) {
    queryParams.append('query', filters.query);
  }

  if (filters?.make && filters.make.length > 0) {
    filters.make.forEach((make) => queryParams.append('make', make));
  }

  if (filters?.model && filters.model.length > 0) {
    filters.model.forEach((model) => queryParams.append('model', model));
  }

  const url = `${API_BASE_URL}/api/v1/vehicles/facets?${queryParams.toString()}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error: ApiErrorResponse = await response.json();
    throw new Error(error.message ?? 'Failed to fetch facets');
  }

  return response.json();
}

/**
 * Fetch price range for current filters
 */
async function fetchPriceRange(filters?: VehicleFilters): Promise<PriceRangeResponse> {
  const queryParams = new URLSearchParams();

  if (filters?.make && filters.make.length > 0) {
    filters.make.forEach((make) => queryParams.append('make', make));
  }

  if (filters?.model && filters.model.length > 0) {
    filters.model.forEach((model) => queryParams.append('model', model));
  }

  if (filters?.bodyStyle && filters.bodyStyle.length > 0) {
    filters.bodyStyle.forEach((style) => queryParams.append('body_style', style));
  }

  const url = `${API_BASE_URL}/api/v1/vehicles/price-range?${queryParams.toString()}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error: ApiErrorResponse = await response.json();
    throw new Error(error.message ?? 'Failed to fetch price range');
  }

  return response.json();
}

/**
 * Hook for fetching paginated vehicle list
 */
export function useVehicles(
  params: SearchParams = {},
  options?: Omit<UseQueryOptions<VehicleListResponse, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<VehicleListResponse, Error>({
    queryKey: vehicleKeys.list(params),
    queryFn: () => fetchVehicles(params),
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_CACHE_TIME,
    refetchOnWindowFocus: false,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    ...options,
  });
}

/**
 * Hook for infinite scroll vehicle list
 */
export function useInfiniteVehicles(
  params: Omit<SearchParams, 'page'> = {},
  options?: Omit<
    UseInfiniteQueryOptions<VehicleListResponse, Error, InfiniteData<VehicleListResponse>>,
    'queryKey' | 'queryFn' | 'getNextPageParam' | 'initialPageParam'
  >,
) {
  return useInfiniteQuery<VehicleListResponse, Error, InfiniteData<VehicleListResponse>>({
    queryKey: vehicleKeys.list(params),
    queryFn: ({ pageParam = 1 }) =>
      fetchVehicles({
        ...params,
        page: pageParam as number,
      }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      if (lastPage.metadata.hasNextPage) {
        return lastPage.metadata.page + 1;
      }
      return undefined;
    },
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_CACHE_TIME,
    refetchOnWindowFocus: false,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    ...options,
  });
}

/**
 * Hook for fetching a single vehicle by ID
 */
export function useVehicle(
  id: string,
  options?: Omit<UseQueryOptions<VehicleDetailResponse, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<VehicleDetailResponse, Error>({
    queryKey: vehicleKeys.detail(id),
    queryFn: () => fetchVehicleById(id),
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_CACHE_TIME,
    refetchOnWindowFocus: false,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    enabled: Boolean(id),
    ...options,
  });
}

/**
 * Hook for vehicle search with filters
 */
export function useVehicleSearch(
  params: SearchParams,
  options?: Omit<UseQueryOptions<VehicleListResponse, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<VehicleListResponse, Error>({
    queryKey: vehicleKeys.search(params),
    queryFn: () => fetchVehicles(params),
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_CACHE_TIME,
    refetchOnWindowFocus: false,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    enabled: Boolean(params.filters?.query ?? params.filters),
    ...options,
  });
}

/**
 * Hook for fetching search facets
 */
export function useVehicleFacets(
  filters?: VehicleFilters,
  options?: Omit<UseQueryOptions<SearchFacets, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<SearchFacets, Error>({
    queryKey: vehicleKeys.facets(filters),
    queryFn: () => fetchSearchFacets(filters),
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_CACHE_TIME,
    refetchOnWindowFocus: false,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    ...options,
  });
}

/**
 * Hook for fetching price range
 */
export function usePriceRange(
  filters?: VehicleFilters,
  options?: Omit<UseQueryOptions<PriceRangeResponse, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<PriceRangeResponse, Error>({
    queryKey: vehicleKeys.priceRange(filters),
    queryFn: () => fetchPriceRange(filters),
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_CACHE_TIME,
    refetchOnWindowFocus: false,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    ...options,
  });
}

/**
 * Hook for prefetching vehicle data
 */
export function usePrefetchVehicle() {
  const queryClient = useQueryClient();

  return (id: string) => {
    void queryClient.prefetchQuery({
      queryKey: vehicleKeys.detail(id),
      queryFn: () => fetchVehicleById(id),
      staleTime: DEFAULT_STALE_TIME,
    });
  };
}

/**
 * Hook for invalidating vehicle queries
 */
export function useInvalidateVehicles() {
  const queryClient = useQueryClient();

  return {
    invalidateAll: () => queryClient.invalidateQueries({ queryKey: vehicleKeys.all }),
    invalidateLists: () => queryClient.invalidateQueries({ queryKey: vehicleKeys.lists() }),
    invalidateDetail: (id: string) =>
      queryClient.invalidateQueries({ queryKey: vehicleKeys.detail(id) }),
    invalidateSearch: () =>
      queryClient.invalidateQueries({ queryKey: [...vehicleKeys.all, 'search'] }),
    invalidateFacets: () =>
      queryClient.invalidateQueries({ queryKey: [...vehicleKeys.all, 'facets'] }),
  };
}

/**
 * Hook for optimistic updates
 */
export function useOptimisticVehicleUpdate() {
  const queryClient = useQueryClient();

  return useMutation<Vehicle, Error, { id: string; updates: Partial<Vehicle> }>({
    mutationFn: async ({ id, updates }) => {
      const response = await fetch(`${API_BASE_URL}/api/v1/vehicles/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });

      if (!response.ok) {
        const error: ApiErrorResponse = await response.json();
        throw new Error(error.message ?? 'Failed to update vehicle');
      }

      return response.json();
    },
    onMutate: async ({ id, updates }) => {
      await queryClient.cancelQueries({ queryKey: vehicleKeys.detail(id) });

      const previousVehicle = queryClient.getQueryData<VehicleDetailResponse>(
        vehicleKeys.detail(id),
      );

      if (previousVehicle) {
        queryClient.setQueryData<VehicleDetailResponse>(vehicleKeys.detail(id), {
          ...previousVehicle,
          vehicle: {
            ...previousVehicle.vehicle,
            ...updates,
          },
        });
      }

      return { previousVehicle };
    },
    onError: (_err, { id }, context) => {
      if (context?.previousVehicle) {
        queryClient.setQueryData(vehicleKeys.detail(id), context.previousVehicle);
      }
    },
    onSettled: (_data, _error, { id }) => {
      void queryClient.invalidateQueries({ queryKey: vehicleKeys.detail(id) });
      void queryClient.invalidateQueries({ queryKey: vehicleKeys.lists() });
    },
  });
}

/**
 * Type guard to check if error is an API error
 */
export function isApiError(error: unknown): error is ApiErrorResponse {
  return (
    typeof error === 'object' &&
    error !== null &&
    'error' in error &&
    'message' in error &&
    'statusCode' in error
  );
}

/**
 * Hook for background refetching
 */
export function useBackgroundRefetch(enabled = true) {
  const queryClient = useQueryClient();

  return () => {
    if (enabled) {
      void queryClient.refetchQueries({
        queryKey: vehicleKeys.lists(),
        type: 'active',
      });
    }
  };
}