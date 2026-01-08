/**
 * React Query hooks for saved configuration operations
 * Provides type-safe hooks for managing saved configurations with caching and optimistic updates
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from '@tanstack/react-query';
import type {
  SavedConfiguration,
  SavedConfigurationWithVehicle,
  SaveConfigurationRequest,
  SaveConfigurationResponse,
  UpdateSavedConfigurationRequest,
  ShareConfigurationRequest,
  ShareConfigurationResponse,
  SavedConfigurationListRequest,
  SavedConfigurationListResponse,
} from '../types/savedConfiguration';

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
  savedConfigurations: `${API_BASE_URL}/api/${API_VERSION}/saved-configurations`,
  savedConfiguration: (id: string) =>
    `${API_BASE_URL}/api/${API_VERSION}/saved-configurations/${id}`,
  shareConfiguration: (id: string) =>
    `${API_BASE_URL}/api/${API_VERSION}/saved-configurations/${id}/share`,
} as const;

/**
 * Query keys for React Query cache management
 */
export const savedConfigurationKeys = {
  all: ['savedConfigurations'] as const,
  lists: () => [...savedConfigurationKeys.all, 'list'] as const,
  list: (params: SavedConfigurationListRequest) =>
    [...savedConfigurationKeys.lists(), params] as const,
  details: () => [...savedConfigurationKeys.all, 'detail'] as const,
  detail: (id: string) => [...savedConfigurationKeys.details(), id] as const,
  shared: (token: string) => [...savedConfigurationKeys.all, 'shared', token] as const,
} as const;

/**
 * Custom error class for saved configuration API errors
 */
export class SavedConfigurationApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'SavedConfigurationApiError';
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
 * Get authentication token from storage
 */
function getAuthToken(): string | null {
  try {
    return localStorage.getItem('authToken');
  } catch {
    return null;
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
      throw new SavedConfigurationApiError(
        `HTTP ${response.status}: ${response.statusText}`,
        response.status,
      );
    }

    if (isApiErrorResponse(errorData)) {
      throw new SavedConfigurationApiError(
        errorData.message,
        errorData.statusCode,
        errorData.details,
      );
    }

    throw new SavedConfigurationApiError(
      `HTTP ${response.status}: ${response.statusText}`,
      response.status,
      { data: errorData },
    );
  }

  try {
    return await response.json();
  } catch (error) {
    throw new SavedConfigurationApiError('Failed to parse response JSON', 500, {
      originalError: error instanceof Error ? error.message : String(error),
    });
  }
}

/**
 * Fetch saved configurations list
 */
async function fetchSavedConfigurations(
  request: SavedConfigurationListRequest = {},
): Promise<SavedConfigurationListResponse> {
  const controller = createAbortController();
  const token = getAuthToken();

  if (!token) {
    throw new SavedConfigurationApiError('Authentication required', 401);
  }

  try {
    const params = new URLSearchParams();
    if (request.page !== undefined) {
      params.append('page', request.page.toString());
    }
    if (request.pageSize !== undefined) {
      params.append('pageSize', request.pageSize.toString());
    }
    if (request.status) {
      params.append('status', request.status);
    }
    if (request.visibility) {
      params.append('visibility', request.visibility);
    }
    if (request.sortBy) {
      params.append('sortBy', request.sortBy);
    }
    if (request.sortDirection) {
      params.append('sortDirection', request.sortDirection);
    }
    if (request.search) {
      params.append('search', request.search);
    }

    const url = `${ENDPOINTS.savedConfigurations}?${params.toString()}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      signal: controller.signal,
    });

    return await handleResponse<SavedConfigurationListResponse>(response);
  } catch (error) {
    if (error instanceof SavedConfigurationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new SavedConfigurationApiError('Request timeout', 408);
      }
      throw new SavedConfigurationApiError(error.message, 500, {
        originalError: error.message,
      });
    }

    throw new SavedConfigurationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Fetch single saved configuration
 */
async function fetchSavedConfiguration(id: string): Promise<SavedConfigurationWithVehicle> {
  const controller = createAbortController();
  const token = getAuthToken();

  if (!token) {
    throw new SavedConfigurationApiError('Authentication required', 401);
  }

  try {
    const response = await fetch(ENDPOINTS.savedConfiguration(id), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      signal: controller.signal,
    });

    return await handleResponse<SavedConfigurationWithVehicle>(response);
  } catch (error) {
    if (error instanceof SavedConfigurationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new SavedConfigurationApiError('Request timeout', 408);
      }
      throw new SavedConfigurationApiError(error.message, 500, {
        originalError: error.message,
      });
    }

    throw new SavedConfigurationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Save new configuration
 */
async function saveConfiguration(
  request: SaveConfigurationRequest,
): Promise<SaveConfigurationResponse> {
  const controller = createAbortController();
  const token = getAuthToken();

  if (!token) {
    throw new SavedConfigurationApiError('Authentication required', 401);
  }

  try {
    const response = await fetch(ENDPOINTS.savedConfigurations, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    return await handleResponse<SaveConfigurationResponse>(response);
  } catch (error) {
    if (error instanceof SavedConfigurationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new SavedConfigurationApiError('Request timeout', 408);
      }
      throw new SavedConfigurationApiError(error.message, 500, {
        originalError: error.message,
      });
    }

    throw new SavedConfigurationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Update saved configuration
 */
async function updateSavedConfiguration(
  id: string,
  request: UpdateSavedConfigurationRequest,
): Promise<SavedConfiguration> {
  const controller = createAbortController();
  const token = getAuthToken();

  if (!token) {
    throw new SavedConfigurationApiError('Authentication required', 401);
  }

  try {
    const response = await fetch(ENDPOINTS.savedConfiguration(id), {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    return await handleResponse<SavedConfiguration>(response);
  } catch (error) {
    if (error instanceof SavedConfigurationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new SavedConfigurationApiError('Request timeout', 408);
      }
      throw new SavedConfigurationApiError(error.message, 500, {
        originalError: error.message,
      });
    }

    throw new SavedConfigurationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Delete saved configuration
 */
async function deleteSavedConfiguration(id: string): Promise<void> {
  const controller = createAbortController();
  const token = getAuthToken();

  if (!token) {
    throw new SavedConfigurationApiError('Authentication required', 401);
  }

  try {
    const response = await fetch(ENDPOINTS.savedConfiguration(id), {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      await handleResponse(response);
    }
  } catch (error) {
    if (error instanceof SavedConfigurationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new SavedConfigurationApiError('Request timeout', 408);
      }
      throw new SavedConfigurationApiError(error.message, 500, {
        originalError: error.message,
      });
    }

    throw new SavedConfigurationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Share configuration
 */
async function shareConfiguration(
  request: ShareConfigurationRequest,
): Promise<ShareConfigurationResponse> {
  const controller = createAbortController();
  const token = getAuthToken();

  if (!token) {
    throw new SavedConfigurationApiError('Authentication required', 401);
  }

  try {
    const response = await fetch(ENDPOINTS.shareConfiguration(request.configurationId), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        visibility: request.visibility,
        expiresInDays: request.expiresInDays,
      }),
      signal: controller.signal,
    });

    return await handleResponse<ShareConfigurationResponse>(response);
  } catch (error) {
    if (error instanceof SavedConfigurationApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new SavedConfigurationApiError('Request timeout', 408);
      }
      throw new SavedConfigurationApiError(error.message, 500, {
        originalError: error.message,
      });
    }

    throw new SavedConfigurationApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Hook to fetch saved configurations list with caching
 */
export function useSavedConfigurations(
  request: SavedConfigurationListRequest = {},
  options?: Omit<
    UseQueryOptions<SavedConfigurationListResponse, SavedConfigurationApiError>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: savedConfigurationKeys.list(request),
    queryFn: () => fetchSavedConfigurations(request),
    staleTime: 2 * 60 * 1000,
    gcTime: 5 * 60 * 1000,
    retry: 2,
    ...options,
  });
}

/**
 * Hook to fetch single saved configuration
 */
export function useSavedConfiguration(
  id: string,
  options?: Omit<
    UseQueryOptions<SavedConfigurationWithVehicle, SavedConfigurationApiError>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery({
    queryKey: savedConfigurationKeys.detail(id),
    queryFn: () => fetchSavedConfiguration(id),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    enabled: Boolean(id),
    retry: 2,
    ...options,
  });
}

/**
 * Hook to save configuration with optimistic updates
 */
export function useSaveConfiguration(
  options?: Omit<
    UseMutationOptions<SaveConfigurationResponse, SavedConfigurationApiError, SaveConfigurationRequest>,
    'mutationFn'
  >,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: saveConfiguration,
    onSuccess: (data) => {
      queryClient.setQueryData(savedConfigurationKeys.detail(data.id), data);

      void queryClient.invalidateQueries({
        queryKey: savedConfigurationKeys.lists(),
      });
    },
    retry: 1,
    ...options,
  });
}

/**
 * Hook to update saved configuration with optimistic updates
 */
export function useUpdateSavedConfiguration(
  options?: Omit<
    UseMutationOptions<
      SavedConfiguration,
      SavedConfigurationApiError,
      { id: string; request: UpdateSavedConfigurationRequest }
    >,
    'mutationFn'
  >,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, request }) => updateSavedConfiguration(id, request),
    onMutate: async ({ id, request }) => {
      await queryClient.cancelQueries({
        queryKey: savedConfigurationKeys.detail(id),
      });

      const previousConfig = queryClient.getQueryData<SavedConfigurationWithVehicle>(
        savedConfigurationKeys.detail(id),
      );

      if (previousConfig) {
        queryClient.setQueryData<SavedConfigurationWithVehicle>(
          savedConfigurationKeys.detail(id),
          {
            ...previousConfig,
            ...request,
            updatedAt: new Date().toISOString(),
          },
        );
      }

      return { previousConfig };
    },
    onError: (_error, { id }, context) => {
      if (context?.previousConfig) {
        queryClient.setQueryData(savedConfigurationKeys.detail(id), context.previousConfig);
      }
    },
    onSuccess: (data, { id }) => {
      queryClient.setQueryData(savedConfigurationKeys.detail(id), data);

      void queryClient.invalidateQueries({
        queryKey: savedConfigurationKeys.lists(),
      });
    },
    retry: 1,
    ...options,
  });
}

/**
 * Hook to delete saved configuration
 */
export function useDeleteSavedConfiguration(
  options?: Omit<
    UseMutationOptions<void, SavedConfigurationApiError, string>,
    'mutationFn'
  >,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteSavedConfiguration,
    onSuccess: (_data, id) => {
      queryClient.removeQueries({
        queryKey: savedConfigurationKeys.detail(id),
      });

      void queryClient.invalidateQueries({
        queryKey: savedConfigurationKeys.lists(),
      });
    },
    retry: 1,
    ...options,
  });
}

/**
 * Hook to share configuration
 */
export function useShareConfiguration(
  options?: Omit<
    UseMutationOptions<ShareConfigurationResponse, SavedConfigurationApiError, ShareConfigurationRequest>,
    'mutationFn'
  >,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: shareConfiguration,
    onSuccess: (data, request) => {
      const configId = request.configurationId;

      const previousConfig = queryClient.getQueryData<SavedConfigurationWithVehicle>(
        savedConfigurationKeys.detail(configId),
      );

      if (previousConfig) {
        queryClient.setQueryData<SavedConfigurationWithVehicle>(
          savedConfigurationKeys.detail(configId),
          {
            ...previousConfig,
            shareToken: data.shareToken,
            shareUrl: data.shareUrl,
            sharedAt: new Date().toISOString(),
            visibility: data.visibility,
          },
        );
      }

      void queryClient.invalidateQueries({
        queryKey: savedConfigurationKeys.lists(),
      });
    },
    retry: 1,
    ...options,
  });
}

/**
 * Hook to prefetch saved configurations
 */
export function usePrefetchSavedConfigurations() {
  const queryClient = useQueryClient();

  return (request: SavedConfigurationListRequest = {}) => {
    void queryClient.prefetchQuery({
      queryKey: savedConfigurationKeys.list(request),
      queryFn: () => fetchSavedConfigurations(request),
      staleTime: 2 * 60 * 1000,
    });
  };
}

/**
 * Hook to invalidate saved configuration queries
 */
export function useInvalidateSavedConfigurations() {
  const queryClient = useQueryClient();

  return {
    invalidateAll: () => {
      void queryClient.invalidateQueries({
        queryKey: savedConfigurationKeys.all,
      });
    },
    invalidateLists: () => {
      void queryClient.invalidateQueries({
        queryKey: savedConfigurationKeys.lists(),
      });
    },
    invalidateDetail: (id: string) => {
      void queryClient.invalidateQueries({
        queryKey: savedConfigurationKeys.detail(id),
      });
    },
  };
}

/**
 * Type guard for SavedConfigurationApiError
 */
export function isSavedConfigurationApiError(
  error: unknown,
): error is SavedConfigurationApiError {
  return error instanceof SavedConfigurationApiError;
}

/**
 * Export types for external use
 */
export type {
  SavedConfiguration,
  SavedConfigurationWithVehicle,
  SaveConfigurationRequest,
  SaveConfigurationResponse,
  UpdateSavedConfigurationRequest,
  ShareConfigurationRequest,
  ShareConfigurationResponse,
  SavedConfigurationListRequest,
  SavedConfigurationListResponse,
};