/**
 * React Query hooks for vehicle configuration API operations
 * Provides type-safe hooks for fetching options, validating configurations,
 * calculating pricing, and saving configurations with caching and optimistic updates
 */

import { useMutation, useQuery, useQueryClient, type UseQueryOptions } from '@tanstack/react-query';
import type {
  ConfigurationPricingRequest,
  ConfigurationSaveRequest,
  ConfigurationSaveResponse,
  ConfigurationValidationRequest,
  ConfigurationValidationResult,
  PricingBreakdown,
  VehicleOptionsResponse,
} from '../types/configuration';

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
  vehicleOptions: (vehicleId: string) =>
    `${API_BASE_URL}/api/${API_VERSION}/configuration/vehicles/${vehicleId}/options`,
  validateConfiguration: `${API_BASE_URL}/api/${API_VERSION}/configuration/validate`,
  calculatePricing: `${API_BASE_URL}/api/${API_VERSION}/configuration/pricing`,
  saveConfiguration: `${API_BASE_URL}/api/${API_VERSION}/configuration`,
  getConfiguration: (configId: string) =>
    `${API_BASE_URL}/api/${API_VERSION}/configuration/${configId}`,
} as const;

/**
 * Query keys for React Query cache management
 */
export const configurationKeys = {
  all: ['configuration'] as const,
  vehicleOptions: (vehicleId: string) =>
    [...configurationKeys.all, 'options', vehicleId] as const,
  validation: (request: ConfigurationValidationRequest) =>
    [...configurationKeys.all, 'validation', request] as const,
  pricing: (request: ConfigurationPricingRequest) =>
    [...configurationKeys.all, 'pricing', request] as const,
  saved: (configId: string) => [...configurationKeys.all, 'saved', configId] as const,
} as const;

/**
 * Custom error class for configuration API errors
 */
export class ConfigurationApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'ConfigurationApiError';
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
      throw new ConfigurationApiError(
        `HTTP ${response.status}: ${response.statusText}`,
        response.status,
      );
    }

    if (isApiErrorResponse(errorData)) {
      throw new ConfigurationApiError(errorData.message, errorData.statusCode, errorData.details);
    }

    throw new ConfigurationApiError(
      `HTTP ${response.status}: ${response.statusText}`,
      response.status,
      { data: errorData },
    );
  }

  try {
    return await response.json();
  } catch (error) {
    throw new ConfigurationApiError('Failed to parse response JSON', 500, {
      originalError: error instanceof Error ? error.message : String(error),
    });
  }
}

/**
 * Fetch vehicle options, packages, colors, and trims
 */
async function fetchVehicleOptions(vehicleId: string): Promise<VehicleOptionsResponse> {
  const controller = createAbortController();

  try {
    const response = await fetch(ENDPOINTS.vehicleOptions(vehicleId), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });

    return await handleResponse<VehicleOptionsResponse>(response);
  } catch (error) {
    if (error instanceof ConfigurationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new ConfigurationApiError('Request timeout', 408);
      }
      throw new ConfigurationApiError(error.message, 500, { originalError: error.message });
    }

    throw new ConfigurationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Validate configuration selections
 */
async function validateConfiguration(
  request: ConfigurationValidationRequest,
): Promise<ConfigurationValidationResult> {
  const controller = createAbortController();

  try {
    const response = await fetch(ENDPOINTS.validateConfiguration, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    return await handleResponse<ConfigurationValidationResult>(response);
  } catch (error) {
    if (error instanceof ConfigurationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new ConfigurationApiError('Request timeout', 408);
      }
      throw new ConfigurationApiError(error.message, 500, { originalError: error.message });
    }

    throw new ConfigurationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Calculate pricing for configuration
 */
async function calculatePricing(
  request: ConfigurationPricingRequest,
): Promise<PricingBreakdown> {
  const controller = createAbortController();

  try {
    const response = await fetch(ENDPOINTS.calculatePricing, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    return await handleResponse<PricingBreakdown>(response);
  } catch (error) {
    if (error instanceof ConfigurationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new ConfigurationApiError('Request timeout', 408);
      }
      throw new ConfigurationApiError(error.message, 500, { originalError: error.message });
    }

    throw new ConfigurationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Save configuration
 */
async function saveConfiguration(
  request: ConfigurationSaveRequest,
): Promise<ConfigurationSaveResponse> {
  const controller = createAbortController();

  try {
    const response = await fetch(ENDPOINTS.saveConfiguration, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    return await handleResponse<ConfigurationSaveResponse>(response);
  } catch (error) {
    if (error instanceof ConfigurationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new ConfigurationApiError('Request timeout', 408);
      }
      throw new ConfigurationApiError(error.message, 500, { originalError: error.message });
    }

    throw new ConfigurationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Fetch saved configuration by ID
 */
async function fetchConfiguration(configId: string): Promise<ConfigurationSaveResponse> {
  const controller = createAbortController();

  try {
    const response = await fetch(ENDPOINTS.getConfiguration(configId), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });

    return await handleResponse<ConfigurationSaveResponse>(response);
  } catch (error) {
    if (error instanceof ConfigurationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new ConfigurationApiError('Request timeout', 408);
      }
      throw new ConfigurationApiError(error.message, 500, { originalError: error.message });
    }

    throw new ConfigurationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Hook to fetch vehicle options with caching
 */
export function useVehicleOptions(
  vehicleId: string,
  options?: Omit<
    UseQueryOptions<VehicleOptionsResponse, ConfigurationApiError>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: configurationKeys.vehicleOptions(vehicleId),
    queryFn: () => fetchVehicleOptions(vehicleId),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
    ...options,
  });
}

/**
 * Hook to validate configuration with caching
 */
export function useValidateConfiguration(
  request: ConfigurationValidationRequest,
  options?: Omit<
    UseQueryOptions<ConfigurationValidationResult, ConfigurationApiError>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: configurationKeys.validation(request),
    queryFn: () => validateConfiguration(request),
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000, // 5 minutes
    enabled: Boolean(request.vehicleId && (request.packageIds.length > 0 || request.optionIds.length > 0)),
    retry: 1,
    ...options,
  });
}

/**
 * Hook to calculate pricing with caching
 */
export function useCalculatePricing(
  request: ConfigurationPricingRequest,
  options?: Omit<UseQueryOptions<PricingBreakdown, ConfigurationApiError>, 'queryKey' | 'queryFn'>,
) {
  return useQuery({
    queryKey: configurationKeys.pricing(request),
    queryFn: () => calculatePricing(request),
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000, // 5 minutes
    enabled: Boolean(request.vehicleId),
    retry: 1,
    ...options,
  });
}

/**
 * Hook to fetch saved configuration
 */
export function useConfiguration(
  configId: string,
  options?: Omit<
    UseQueryOptions<ConfigurationSaveResponse, ConfigurationApiError>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: configurationKeys.saved(configId),
    queryFn: () => fetchConfiguration(configId),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    enabled: Boolean(configId),
    retry: 2,
    ...options,
  });
}

/**
 * Hook to save configuration with optimistic updates
 */
export function useSaveConfiguration() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: saveConfiguration,
    onMutate: async (request: ConfigurationSaveRequest) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: configurationKeys.all,
      });

      // Snapshot previous value
      const previousPricing = queryClient.getQueryData<PricingBreakdown>(
        configurationKeys.pricing({
          vehicleId: request.vehicleId,
          trimId: request.trimId,
          packageIds: request.packageIds,
          optionIds: request.optionIds,
        }),
      );

      // Return context with snapshot
      return { previousPricing };
    },
    onError: (_error, _request, context) => {
      // Rollback on error
      if (context?.previousPricing) {
        queryClient.setQueryData(
          configurationKeys.pricing({
            vehicleId: _request.vehicleId,
            trimId: _request.trimId,
            packageIds: _request.packageIds,
            optionIds: _request.optionIds,
          }),
          context.previousPricing,
        );
      }
    },
    onSuccess: (data) => {
      // Update cache with saved configuration
      queryClient.setQueryData(configurationKeys.saved(data.id), data);

      // Invalidate related queries
      void queryClient.invalidateQueries({
        queryKey: configurationKeys.pricing({
          vehicleId: data.vehicleId,
          trimId: data.trimId,
          packageIds: data.packageIds,
          optionIds: data.optionIds,
        }),
      });
    },
    retry: 1,
  });
}

/**
 * Hook to prefetch vehicle options
 */
export function usePrefetchVehicleOptions() {
  const queryClient = useQueryClient();

  return (vehicleId: string) => {
    void queryClient.prefetchQuery({
      queryKey: configurationKeys.vehicleOptions(vehicleId),
      queryFn: () => fetchVehicleOptions(vehicleId),
      staleTime: 5 * 60 * 1000,
    });
  };
}

/**
 * Hook to invalidate configuration queries
 */
export function useInvalidateConfiguration() {
  const queryClient = useQueryClient();

  return {
    invalidateAll: () => {
      void queryClient.invalidateQueries({
        queryKey: configurationKeys.all,
      });
    },
    invalidateVehicleOptions: (vehicleId: string) => {
      void queryClient.invalidateQueries({
        queryKey: configurationKeys.vehicleOptions(vehicleId),
      });
    },
    invalidatePricing: (request: ConfigurationPricingRequest) => {
      void queryClient.invalidateQueries({
        queryKey: configurationKeys.pricing(request),
      });
    },
    invalidateValidation: (request: ConfigurationValidationRequest) => {
      void queryClient.invalidateQueries({
        queryKey: configurationKeys.validation(request),
      });
    },
    invalidateSaved: (configId: string) => {
      void queryClient.invalidateQueries({
        queryKey: configurationKeys.saved(configId),
      });
    },
  };
}

/**
 * Type guard for ConfigurationApiError
 */
export function isConfigurationApiError(error: unknown): error is ConfigurationApiError {
  return error instanceof ConfigurationApiError;
}

/**
 * Export types for external use
 */
export type {
  ConfigurationPricingRequest,
  ConfigurationSaveRequest,
  ConfigurationSaveResponse,
  ConfigurationValidationRequest,
  ConfigurationValidationResult,
  PricingBreakdown,
  VehicleOptionsResponse,
};