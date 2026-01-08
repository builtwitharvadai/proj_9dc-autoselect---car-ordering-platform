/**
 * Vehicle Detail Hook
 * React Query hook for fetching individual vehicle details with caching and error handling
 * Includes related vehicles suggestions and inventory information
 */

import { useQuery, useQueryClient, type UseQueryOptions } from '@tanstack/react-query';
import { fetchVehicleById } from '../api/vehicles';
import type { VehicleDetailResponse, Vehicle } from '../types/vehicle';

/**
 * Query key factory for vehicle detail queries
 */
export const vehicleDetailKeys = {
  all: ['vehicle-detail'] as const,
  detail: (id: string, includeInventory: boolean = false) =>
    [...vehicleDetailKeys.all, id, { includeInventory }] as const,
} as const;

/**
 * Hook options interface
 */
interface UseVehicleDetailOptions
  extends Omit<
    UseQueryOptions<VehicleDetailResponse, Error>,
    'queryKey' | 'queryFn'
  > {
  readonly includeInventory?: boolean;
}

/**
 * Hook for fetching individual vehicle details
 * 
 * Features:
 * - Automatic caching with React Query
 * - Related vehicles suggestions
 * - Optional inventory information
 * - Comprehensive error handling
 * - Stale-while-revalidate pattern
 * 
 * @param id - Vehicle ID to fetch
 * @param options - Query options including includeInventory flag
 * @returns Query result with vehicle detail data
 * 
 * @example
 * ```tsx
 * const { data, isLoading, error } = useVehicleDetail('vehicle-123', {
 *   includeInventory: true,
 *   staleTime: 5 * 60 * 1000, // 5 minutes
 * });
 * 
 * if (isLoading) return <LoadingSpinner />;
 * if (error) return <ErrorMessage error={error} />;
 * if (!data) return null;
 * 
 * return (
 *   <VehicleDetailPage 
 *     vehicle={data.vehicle}
 *     relatedVehicles={data.relatedVehicles}
 *   />
 * );
 * ```
 */
export function useVehicleDetail(
  id: string,
  options: UseVehicleDetailOptions = {},
) {
  const { includeInventory = false, ...queryOptions } = options;

  return useQuery<VehicleDetailResponse, Error>({
    queryKey: vehicleDetailKeys.detail(id, includeInventory),
    queryFn: async () => {
      if (!id || id.trim() === '') {
        throw new Error('Vehicle ID is required');
      }

      try {
        return await fetchVehicleById(id, includeInventory);
      } catch (error) {
        if (error instanceof Error) {
          throw error;
        }
        throw new Error('Failed to fetch vehicle details');
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
    retry: (failureCount, error) => {
      // Don't retry on 404 errors
      if (error instanceof Error && error.message.includes('404')) {
        return false;
      }
      // Retry up to 2 times for other errors
      return failureCount < 2;
    },
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    enabled: Boolean(id && id.trim() !== ''),
    ...queryOptions,
  });
}

/**
 * Hook for prefetching vehicle detail data
 * Useful for optimistic navigation and hover states
 * 
 * @returns Prefetch function
 * 
 * @example
 * ```tsx
 * const prefetchVehicleDetail = usePrefetchVehicleDetail();
 * 
 * <Link
 *   to={`/vehicles/${vehicle.id}`}
 *   onMouseEnter={() => prefetchVehicleDetail(vehicle.id)}
 * >
 *   {vehicle.make} {vehicle.model}
 * </Link>
 * ```
 */
export function usePrefetchVehicleDetail() {
  const queryClient = useQueryClient();

  return (id: string, includeInventory: boolean = false) => {
    if (!id || id.trim() === '') {
      return;
    }

    void queryClient.prefetchQuery({
      queryKey: vehicleDetailKeys.detail(id, includeInventory),
      queryFn: () => fetchVehicleById(id, includeInventory),
      staleTime: 5 * 60 * 1000,
    });
  };
}

/**
 * Hook for invalidating vehicle detail cache
 * Useful after updates or deletions
 * 
 * @returns Invalidation functions
 * 
 * @example
 * ```tsx
 * const { invalidateVehicle, invalidateAllVehicleDetails } = useInvalidateVehicleDetail();
 * 
 * const handleUpdate = async () => {
 *   await updateVehicle(vehicleId, data);
 *   await invalidateVehicle(vehicleId);
 * };
 * ```
 */
export function useInvalidateVehicleDetail() {
  const queryClient = useQueryClient();

  const invalidateVehicle = async (id: string) => {
    await queryClient.invalidateQueries({
      queryKey: vehicleDetailKeys.detail(id),
    });
  };

  const invalidateAllVehicleDetails = async () => {
    await queryClient.invalidateQueries({
      queryKey: vehicleDetailKeys.all,
    });
  };

  return {
    invalidateVehicle,
    invalidateAllVehicleDetails,
  };
}

/**
 * Hook for getting cached vehicle detail data without triggering a fetch
 * Useful for accessing already-loaded data
 * 
 * @param id - Vehicle ID
 * @param includeInventory - Whether to include inventory data
 * @returns Cached vehicle detail data or undefined
 * 
 * @example
 * ```tsx
 * const cachedVehicle = useCachedVehicleDetail(vehicleId);
 * 
 * if (cachedVehicle) {
 *   // Use cached data immediately
 *   return <QuickPreview vehicle={cachedVehicle.vehicle} />;
 * }
 * ```
 */
export function useCachedVehicleDetail(
  id: string,
  includeInventory: boolean = false,
): VehicleDetailResponse | undefined {
  const queryClient = useQueryClient();

  return queryClient.getQueryData<VehicleDetailResponse>(
    vehicleDetailKeys.detail(id, includeInventory),
  );
}

/**
 * Hook for setting vehicle detail data in cache
 * Useful for optimistic updates
 * 
 * @returns Set cache function
 * 
 * @example
 * ```tsx
 * const setVehicleDetailCache = useSetVehicleDetailCache();
 * 
 * const handleOptimisticUpdate = (updatedVehicle: Vehicle) => {
 *   setVehicleDetailCache(updatedVehicle.id, {
 *     vehicle: updatedVehicle,
 *     relatedVehicles: [],
 *   });
 * };
 * ```
 */
export function useSetVehicleDetailCache() {
  const queryClient = useQueryClient();

  return (
    id: string,
    data: VehicleDetailResponse,
    includeInventory: boolean = false,
  ) => {
    queryClient.setQueryData<VehicleDetailResponse>(
      vehicleDetailKeys.detail(id, includeInventory),
      data,
    );
  };
}

/**
 * Hook for extracting related vehicles from detail response
 * Provides type-safe access to related vehicles with fallback
 * 
 * @param vehicleDetailData - Vehicle detail response data
 * @returns Array of related vehicles
 * 
 * @example
 * ```tsx
 * const { data } = useVehicleDetail(vehicleId);
 * const relatedVehicles = useRelatedVehicles(data);
 * 
 * return (
 *   <RelatedVehiclesSection vehicles={relatedVehicles} />
 * );
 * ```
 */
export function useRelatedVehicles(
  vehicleDetailData: VehicleDetailResponse | undefined,
): readonly Vehicle[] {
  if (!vehicleDetailData?.relatedVehicles) {
    return [];
  }

  return vehicleDetailData.relatedVehicles;
}

/**
 * Hook for checking if vehicle detail is available in cache
 * Useful for conditional rendering and prefetch decisions
 * 
 * @param id - Vehicle ID
 * @param includeInventory - Whether to check for inventory data
 * @returns Boolean indicating if data is cached
 * 
 * @example
 * ```tsx
 * const isVehicleCached = useIsVehicleDetailCached(vehicleId);
 * 
 * if (!isVehicleCached) {
 *   prefetchVehicleDetail(vehicleId);
 * }
 * ```
 */
export function useIsVehicleDetailCached(
  id: string,
  includeInventory: boolean = false,
): boolean {
  const queryClient = useQueryClient();

  const queryState = queryClient.getQueryState(
    vehicleDetailKeys.detail(id, includeInventory),
  );

  return Boolean(queryState?.data);
}

/**
 * Type guard for checking if vehicle detail response has related vehicles
 * 
 * @param response - Vehicle detail response
 * @returns Type predicate for related vehicles
 */
export function hasRelatedVehicles(
  response: VehicleDetailResponse | undefined,
): response is VehicleDetailResponse & {
  readonly relatedVehicles: readonly Vehicle[];
} {
  return Boolean(
    response?.relatedVehicles && response.relatedVehicles.length > 0,
  );
}