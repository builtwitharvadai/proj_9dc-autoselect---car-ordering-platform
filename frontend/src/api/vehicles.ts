/**
 * Vehicle API Client
 * Provides type-safe HTTP client functions for vehicle catalog endpoints
 * Handles fetching, searching, filtering, and pagination with comprehensive error handling
 */

import type {
  Vehicle,
  VehicleListResponse,
  VehicleDetailResponse,
  SearchParams,
  VehicleFilters,
  PriceRangeResponse,
  SearchSuggestionsResponse,
  ApiErrorResponse,
  VehicleSortField,
  SortDirection,
} from '../types/vehicle';

/**
 * API configuration
 */
const API_BASE_URL = import.meta.env['VITE_API_BASE_URL'] ?? 'http://localhost:8000';
const API_VERSION = 'v1';
const API_TIMEOUT = 30000; // 30 seconds

/**
 * API endpoints
 */
const ENDPOINTS = {
  vehicles: `${API_BASE_URL}/api/${API_VERSION}/vehicles`,
  search: `${API_BASE_URL}/api/${API_VERSION}/vehicles/search`,
  suggestions: `${API_BASE_URL}/api/${API_VERSION}/vehicles/suggestions`,
  priceRange: `${API_BASE_URL}/api/${API_VERSION}/vehicles/price-range`,
} as const;

/**
 * Custom error class for API errors
 */
export class VehicleApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'VehicleApiError';
  }
}

/**
 * Type guard for API error responses
 */
function isApiErrorResponse(data: unknown): data is ApiErrorResponse {
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

  // Store timeout ID for cleanup
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
 * Build query string from search parameters
 */
function buildQueryString(params: SearchParams): string {
  const searchParams = new URLSearchParams();

  // Add filters
  if (params.filters) {
    const filters = params.filters;

    if (filters.query) {
      searchParams.append('query', filters.query);
    }

    if (filters.make && filters.make.length > 0) {
      filters.make.forEach((make) => {
        searchParams.append('make', make);
      });
    }

    if (filters.model && filters.model.length > 0) {
      filters.model.forEach((model) => {
        searchParams.append('model', model);
      });
    }

    if (filters.year) {
      if (filters.year.min !== undefined) {
        searchParams.append('year_min', filters.year.min.toString());
      }
      if (filters.year.max !== undefined) {
        searchParams.append('year_max', filters.year.max.toString());
      }
    }

    if (filters.bodyStyle && filters.bodyStyle.length > 0) {
      filters.bodyStyle.forEach((style) => {
        searchParams.append('body_style', style);
      });
    }

    if (filters.fuelType && filters.fuelType.length > 0) {
      filters.fuelType.forEach((type) => {
        searchParams.append('fuel_type', type);
      });
    }

    if (filters.transmission && filters.transmission.length > 0) {
      filters.transmission.forEach((trans) => {
        searchParams.append('transmission', trans);
      });
    }

    if (filters.drivetrain && filters.drivetrain.length > 0) {
      filters.drivetrain.forEach((drive) => {
        searchParams.append('drivetrain', drive);
      });
    }

    if (filters.price) {
      if (filters.price.min !== undefined) {
        searchParams.append('price_min', filters.price.min.toString());
      }
      if (filters.price.max !== undefined) {
        searchParams.append('price_max', filters.price.max.toString());
      }
    }

    if (filters.seatingCapacity) {
      if (filters.seatingCapacity.min !== undefined) {
        searchParams.append('seating_min', filters.seatingCapacity.min.toString());
      }
      if (filters.seatingCapacity.max !== undefined) {
        searchParams.append('seating_max', filters.seatingCapacity.max.toString());
      }
    }

    if (filters.availability && filters.availability.length > 0) {
      filters.availability.forEach((status) => {
        searchParams.append('availability', status);
      });
    }

    if (filters.features && filters.features.length > 0) {
      filters.features.forEach((feature) => {
        searchParams.append('feature', feature);
      });
    }
  }

  // Add sorting
  if (params.sortBy) {
    searchParams.append('sort_by', params.sortBy);
  }
  if (params.sortDirection) {
    searchParams.append('sort_direction', params.sortDirection);
  }

  // Add pagination
  if (params.page !== undefined) {
    searchParams.append('page', params.page.toString());
  }
  if (params.pageSize !== undefined) {
    searchParams.append('page_size', params.pageSize.toString());
  }

  // Add inventory flag
  if (params.includeInventory !== undefined) {
    searchParams.append('include_inventory', params.includeInventory.toString());
  }

  return searchParams.toString();
}

/**
 * Handle fetch response with error handling
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      throw new VehicleApiError(
        `HTTP ${response.status}: ${response.statusText}`,
        response.status,
      );
    }

    if (isApiErrorResponse(errorData)) {
      throw new VehicleApiError(errorData.message, errorData.statusCode, errorData.details);
    }

    throw new VehicleApiError(
      `HTTP ${response.status}: ${response.statusText}`,
      response.status,
      { data: errorData },
    );
  }

  try {
    return await response.json();
  } catch (error) {
    throw new VehicleApiError(
      'Failed to parse response JSON',
      500,
      { originalError: error instanceof Error ? error.message : String(error) },
    );
  }
}

/**
 * Fetch vehicles with optional filters and pagination
 */
export async function fetchVehicles(params: SearchParams = {}): Promise<VehicleListResponse> {
  const controller = createAbortController();

  try {
    const queryString = buildQueryString(params);
    const url = queryString ? `${ENDPOINTS.vehicles}?${queryString}` : ENDPOINTS.vehicles;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });

    return await handleResponse<VehicleListResponse>(response);
  } catch (error) {
    if (error instanceof VehicleApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new VehicleApiError('Request timeout', 408);
      }
      throw new VehicleApiError(error.message, 500, { originalError: error.message });
    }

    throw new VehicleApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Fetch a single vehicle by ID
 */
export async function fetchVehicleById(
  id: string,
  includeInventory: boolean = false,
): Promise<VehicleDetailResponse> {
  const controller = createAbortController();

  try {
    const searchParams = new URLSearchParams();
    if (includeInventory) {
      searchParams.append('include_inventory', 'true');
    }

    const queryString = searchParams.toString();
    const url = queryString
      ? `${ENDPOINTS.vehicles}/${id}?${queryString}`
      : `${ENDPOINTS.vehicles}/${id}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });

    return await handleResponse<VehicleDetailResponse>(response);
  } catch (error) {
    if (error instanceof VehicleApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new VehicleApiError('Request timeout', 408);
      }
      throw new VehicleApiError(error.message, 500, { originalError: error.message });
    }

    throw new VehicleApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Search vehicles with advanced filtering and faceted search
 */
export async function searchVehicles(params: SearchParams): Promise<VehicleListResponse> {
  const controller = createAbortController();

  try {
    const queryString = buildQueryString(params);
    const url = queryString ? `${ENDPOINTS.search}?${queryString}` : ENDPOINTS.search;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });

    return await handleResponse<VehicleListResponse>(response);
  } catch (error) {
    if (error instanceof VehicleApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new VehicleApiError('Request timeout', 408);
      }
      throw new VehicleApiError(error.message, 500, { originalError: error.message });
    }

    throw new VehicleApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Get search suggestions based on query prefix
 */
export async function fetchSearchSuggestions(
  query: string,
  limit: number = 10,
): Promise<SearchSuggestionsResponse> {
  const controller = createAbortController();

  try {
    const searchParams = new URLSearchParams();
    searchParams.append('query', query);
    searchParams.append('limit', limit.toString());

    const url = `${ENDPOINTS.suggestions}?${searchParams.toString()}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });

    return await handleResponse<SearchSuggestionsResponse>(response);
  } catch (error) {
    if (error instanceof VehicleApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new VehicleApiError('Request timeout', 408);
      }
      throw new VehicleApiError(error.message, 500, { originalError: error.message });
    }

    throw new VehicleApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Get price range for vehicles with optional filters
 */
export async function fetchPriceRange(filters?: VehicleFilters): Promise<PriceRangeResponse> {
  const controller = createAbortController();

  try {
    const queryString = buildQueryString({ filters });
    const url = queryString ? `${ENDPOINTS.priceRange}?${queryString}` : ENDPOINTS.priceRange;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });

    return await handleResponse<PriceRangeResponse>(response);
  } catch (error) {
    if (error instanceof VehicleApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new VehicleApiError('Request timeout', 408);
      }
      throw new VehicleApiError(error.message, 500, { originalError: error.message });
    }

    throw new VehicleApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Fetch vehicles with infinite scroll support
 */
export async function fetchVehiclesInfinite(
  page: number,
  pageSize: number = 20,
  filters?: VehicleFilters,
  sortBy?: VehicleSortField,
  sortDirection?: SortDirection,
): Promise<VehicleListResponse> {
  return fetchVehicles({
    filters,
    sortBy,
    sortDirection,
    page,
    pageSize,
  });
}

/**
 * Prefetch next page for infinite scroll
 */
export async function prefetchNextPage(
  currentPage: number,
  pageSize: number,
  filters?: VehicleFilters,
  sortBy?: VehicleSortField,
  sortDirection?: SortDirection,
): Promise<VehicleListResponse> {
  return fetchVehiclesInfinite(currentPage + 1, pageSize, filters, sortBy, sortDirection);
}

/**
 * Batch fetch vehicles by IDs
 */
export async function fetchVehiclesByIds(ids: readonly string[]): Promise<readonly Vehicle[]> {
  const controller = createAbortController();

  try {
    const searchParams = new URLSearchParams();
    ids.forEach((id) => {
      searchParams.append('id', id);
    });

    const url = `${ENDPOINTS.vehicles}?${searchParams.toString()}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });

    const data = await handleResponse<VehicleListResponse>(response);
    return data.vehicles;
  } catch (error) {
    if (error instanceof VehicleApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new VehicleApiError('Request timeout', 408);
      }
      throw new VehicleApiError(error.message, 500, { originalError: error.message });
    }

    throw new VehicleApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}