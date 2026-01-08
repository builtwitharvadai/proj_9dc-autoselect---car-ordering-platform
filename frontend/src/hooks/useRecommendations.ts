/**
 * React Query hooks for package recommendation operations
 * Provides type-safe hooks for fetching recommendations, popular configurations,
 * and tracking recommendation analytics with caching and performance optimization
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from '@tanstack/react-query';
import type {
  RecommendationRequest,
  RecommendationResponse,
  PackageRecommendation,
  PopularConfiguration,
  RecommendationAnalytics,
  RecommendationAcceptance,
  RecommendationMetrics,
} from '../types/recommendations';

/**
 * API configuration
 */
const API_BASE_URL = import.meta.env['VITE_API_BASE_URL'] ?? 'http://localhost:8000';
const API_VERSION = 'v1';
const API_TIMEOUT = 30000;

/**
 * API endpoints
 */
const ENDPOINTS = {
  recommendations: `${API_BASE_URL}/api/${API_VERSION}/recommendations/packages`,
  popularConfigurations: (vehicleId: string) =>
    `${API_BASE_URL}/api/${API_VERSION}/recommendations/popular/${vehicleId}`,
  trackEvent: `${API_BASE_URL}/api/${API_VERSION}/recommendations/analytics/track`,
  acceptRecommendation: `${API_BASE_URL}/api/${API_VERSION}/recommendations/accept`,
  metrics: `${API_BASE_URL}/api/${API_VERSION}/recommendations/metrics`,
} as const;

/**
 * Query keys for React Query cache management
 */
export const recommendationKeys = {
  all: ['recommendations'] as const,
  packages: (request: RecommendationRequest) =>
    [...recommendationKeys.all, 'packages', request] as const,
  popular: (vehicleId: string) =>
    [...recommendationKeys.all, 'popular', vehicleId] as const,
  metrics: () => [...recommendationKeys.all, 'metrics'] as const,
} as const;

/**
 * Custom error class for recommendation API errors
 */
export class RecommendationApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'RecommendationApiError';
  }
}

/**
 * Type guard for API error responses
 */
function isApiErrorResponse(data: unknown): data is {
  error: string;
  message: string;
  statusCode: number;
  details?: Record<string, unknown>;
} {
  return (
    typeof data === 'object' &&
    data !== null &&
    'error' in data &&
    'message' in data &&
    'statusCode' in data
  );
}

/**
 * Create abort controller with timeout
 */
function createAbortController(timeoutMs: number = API_TIMEOUT): AbortController {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  (controller.signal as AbortSignal & { timeoutId?: NodeJS.Timeout }).timeoutId = timeoutId;

  return controller;
}

/**
 * Cleanup abort controller
 */
function cleanupAbortController(controller: AbortController): void {
  const signal = controller.signal as AbortSignal & { timeoutId?: NodeJS.Timeout };
  if (signal.timeoutId) {
    clearTimeout(signal.timeoutId);
  }
}

/**
 * Handle fetch response with comprehensive error handling
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      throw new RecommendationApiError(
        `HTTP ${response.status}: ${response.statusText}`,
        response.status,
      );
    }

    if (isApiErrorResponse(errorData)) {
      throw new RecommendationApiError(
        errorData.message,
        errorData.statusCode,
        errorData.details,
      );
    }

    throw new RecommendationApiError(
      `HTTP ${response.status}: ${response.statusText}`,
      response.status,
      { data: errorData },
    );
  }

  try {
    return await response.json();
  } catch (error) {
    throw new RecommendationApiError('Failed to parse response JSON', 500, {
      originalError: error instanceof Error ? error.message : String(error),
    });
  }
}

/**
 * Fetch package recommendations
 */
async function fetchPackageRecommendations(
  request: RecommendationRequest,
): Promise<RecommendationResponse> {
  const controller = createAbortController();

  try {
    const queryParams = new URLSearchParams({
      vehicle_id: request.vehicleId,
      ...(request.trimId && { trim_id: request.trimId }),
      ...(request.budget && { budget: request.budget.toString() }),
      ...(request.maxRecommendations && {
        max_recommendations: request.maxRecommendations.toString(),
      }),
      ...(request.includePopularConfigurations !== undefined && {
        include_popular: request.includePopularConfigurations.toString(),
      }),
      ...(request.region && { region: request.region }),
    });

    if (request.selectedPackageIds && request.selectedPackageIds.length > 0) {
      request.selectedPackageIds.forEach((id) => {
        queryParams.append('selected_package_ids', id);
      });
    }

    if (request.selectedOptionIds && request.selectedOptionIds.length > 0) {
      request.selectedOptionIds.forEach((id) => {
        queryParams.append('selected_option_ids', id);
      });
    }

    const response = await fetch(`${ENDPOINTS.recommendations}?${queryParams.toString()}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });

    return await handleResponse<RecommendationResponse>(response);
  } catch (error) {
    if (error instanceof RecommendationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new RecommendationApiError('Request timeout', 408);
      }
      throw new RecommendationApiError(error.message, 500, {
        originalError: error.message,
      });
    }

    throw new RecommendationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Fetch popular configurations for a vehicle
 */
async function fetchPopularConfigurations(
  vehicleId: string,
): Promise<readonly PopularConfiguration[]> {
  const controller = createAbortController();

  try {
    const response = await fetch(ENDPOINTS.popularConfigurations(vehicleId), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });

    return await handleResponse<readonly PopularConfiguration[]>(response);
  } catch (error) {
    if (error instanceof RecommendationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new RecommendationApiError('Request timeout', 408);
      }
      throw new RecommendationApiError(error.message, 500, {
        originalError: error.message,
      });
    }

    throw new RecommendationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Track recommendation analytics event
 */
async function trackRecommendationEvent(
  event: RecommendationAnalytics,
): Promise<void> {
  const controller = createAbortController();

  try {
    const response = await fetch(ENDPOINTS.trackEvent, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(event),
      signal: controller.signal,
    });

    await handleResponse<void>(response);
  } catch (error) {
    if (error instanceof RecommendationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new RecommendationApiError('Request timeout', 408);
      }
      throw new RecommendationApiError(error.message, 500, {
        originalError: error.message,
      });
    }

    throw new RecommendationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Accept a recommendation
 */
async function acceptRecommendation(
  acceptance: RecommendationAcceptance,
): Promise<void> {
  const controller = createAbortController();

  try {
    const response = await fetch(ENDPOINTS.acceptRecommendation, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(acceptance),
      signal: controller.signal,
    });

    await handleResponse<void>(response);
  } catch (error) {
    if (error instanceof RecommendationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new RecommendationApiError('Request timeout', 408);
      }
      throw new RecommendationApiError(error.message, 500, {
        originalError: error.message,
      });
    }

    throw new RecommendationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Fetch recommendation metrics
 */
async function fetchRecommendationMetrics(): Promise<RecommendationMetrics> {
  const controller = createAbortController();

  try {
    const response = await fetch(ENDPOINTS.metrics, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });

    return await handleResponse<RecommendationMetrics>(response);
  } catch (error) {
    if (error instanceof RecommendationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new RecommendationApiError('Request timeout', 408);
      }
      throw new RecommendationApiError(error.message, 500, {
        originalError: error.message,
      });
    }

    throw new RecommendationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Hook to fetch package recommendations with caching
 */
export function usePackageRecommendations(
  request: RecommendationRequest,
  options?: Omit<
    UseQueryOptions<RecommendationResponse, RecommendationApiError>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: recommendationKeys.packages(request),
    queryFn: () => fetchPackageRecommendations(request),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    enabled: Boolean(request.vehicleId),
    retry: 2,
    ...options,
  });
}

/**
 * Hook to fetch popular configurations with caching
 */
export function usePopularConfigurations(
  vehicleId: string,
  options?: Omit<
    UseQueryOptions<readonly PopularConfiguration[], RecommendationApiError>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: recommendationKeys.popular(vehicleId),
    queryFn: () => fetchPopularConfigurations(vehicleId),
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    enabled: Boolean(vehicleId),
    retry: 2,
    ...options,
  });
}

/**
 * Hook to fetch recommendation metrics
 */
export function useRecommendationMetrics(
  options?: Omit<
    UseQueryOptions<RecommendationMetrics, RecommendationApiError>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: recommendationKeys.metrics(),
    queryFn: fetchRecommendationMetrics,
    staleTime: 15 * 60 * 1000, // 15 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    retry: 2,
    ...options,
  });
}

/**
 * Hook to track recommendation events
 */
export function useTrackRecommendation(
  options?: Omit<
    UseMutationOptions<void, RecommendationApiError, RecommendationAnalytics>,
    'mutationFn'
  >,
) {
  return useMutation({
    mutationFn: trackRecommendationEvent,
    retry: 1,
    ...options,
  });
}

/**
 * Hook to accept recommendations with optimistic updates
 */
export function useAcceptRecommendation(
  options?: Omit<
    UseMutationOptions<void, RecommendationApiError, RecommendationAcceptance>,
    'mutationFn'
  >,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: acceptRecommendation,
    onSuccess: (_data, variables) => {
      // Invalidate recommendations for the vehicle
      void queryClient.invalidateQueries({
        queryKey: recommendationKeys.packages({
          vehicleId: variables.vehicleId,
        }),
      });

      // Invalidate metrics
      void queryClient.invalidateQueries({
        queryKey: recommendationKeys.metrics(),
      });
    },
    retry: 1,
    ...options,
  });
}

/**
 * Hook to prefetch package recommendations
 */
export function usePrefetchRecommendations() {
  const queryClient = useQueryClient();

  return (request: RecommendationRequest) => {
    void queryClient.prefetchQuery({
      queryKey: recommendationKeys.packages(request),
      queryFn: () => fetchPackageRecommendations(request),
      staleTime: 5 * 60 * 1000,
    });
  };
}

/**
 * Hook to prefetch popular configurations
 */
export function usePrefetchPopularConfigurations() {
  const queryClient = useQueryClient();

  return (vehicleId: string) => {
    void queryClient.prefetchQuery({
      queryKey: recommendationKeys.popular(vehicleId),
      queryFn: () => fetchPopularConfigurations(vehicleId),
      staleTime: 10 * 60 * 1000,
    });
  };
}

/**
 * Hook to invalidate recommendation queries
 */
export function useInvalidateRecommendations() {
  const queryClient = useQueryClient();

  return {
    invalidateAll: () => {
      void queryClient.invalidateQueries({
        queryKey: recommendationKeys.all,
      });
    },
    invalidatePackages: (request: RecommendationRequest) => {
      void queryClient.invalidateQueries({
        queryKey: recommendationKeys.packages(request),
      });
    },
    invalidatePopular: (vehicleId: string) => {
      void queryClient.invalidateQueries({
        queryKey: recommendationKeys.popular(vehicleId),
      });
    },
    invalidateMetrics: () => {
      void queryClient.invalidateQueries({
        queryKey: recommendationKeys.metrics(),
      });
    },
  };
}

/**
 * Type guard for RecommendationApiError
 */
export function isRecommendationApiError(
  error: unknown,
): error is RecommendationApiError {
  return error instanceof RecommendationApiError;
}

/**
 * Export types for external use
 */
export type {
  RecommendationRequest,
  RecommendationResponse,
  PackageRecommendation,
  PopularConfiguration,
  RecommendationAnalytics,
  RecommendationAcceptance,
  RecommendationMetrics,
};