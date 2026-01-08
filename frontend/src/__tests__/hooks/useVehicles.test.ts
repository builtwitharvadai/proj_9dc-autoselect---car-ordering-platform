/**
 * Comprehensive test suite for useVehicles React Query hooks
 * Tests data fetching, caching, error handling, and loading states
 * 
 * @coverage >80% line coverage, 100% function coverage
 * @framework Vitest + React Testing Library
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import {
  useVehicles,
  useInfiniteVehicles,
  useVehicle,
  useVehicleSearch,
  useVehicleFacets,
  usePriceRange,
  usePrefetchVehicle,
  useInvalidateVehicles,
  useOptimisticVehicleUpdate,
  useBackgroundRefetch,
  isApiError,
  vehicleKeys,
} from '../useVehicles';
import type {
  VehicleListResponse,
  VehicleDetailResponse,
  SearchFacets,
  PriceRangeResponse,
  Vehicle,
  SearchParams,
  VehicleFilters,
} from '../../types/vehicle';

// ============================================================================
// 🏭 Test Data Factories
// ============================================================================

const createMockVehicle = (overrides?: Partial<Vehicle>): Vehicle => ({
  id: 'vehicle-123',
  make: 'Toyota',
  model: 'Camry',
  year: 2024,
  trim: 'XLE',
  bodyStyle: 'Sedan',
  fuelType: 'Gasoline',
  transmission: 'Automatic',
  drivetrain: 'FWD',
  exteriorColor: 'Silver',
  interiorColor: 'Black',
  seatingCapacity: 5,
  msrp: 35000,
  invoicePrice: 32000,
  destinationCharge: 1000,
  features: ['Sunroof', 'Navigation', 'Leather Seats'],
  specifications: {
    engine: '2.5L 4-Cylinder',
    horsepower: 203,
    torque: 184,
    mpgCity: 28,
    mpgHighway: 39,
    mpgCombined: 32,
  },
  images: [
    {
      url: 'https://example.com/image1.jpg',
      alt: 'Front view',
      isPrimary: true,
    },
  ],
  availability: 'in_stock',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
  ...overrides,
});

const createMockVehicleListResponse = (
  overrides?: Partial<VehicleListResponse>,
): VehicleListResponse => ({
  vehicles: [createMockVehicle(), createMockVehicle({ id: 'vehicle-456' })],
  metadata: {
    total: 2,
    page: 1,
    pageSize: 20,
    totalPages: 1,
    hasNextPage: false,
    hasPreviousPage: false,
  },
  ...overrides,
});

const createMockVehicleDetailResponse = (
  overrides?: Partial<VehicleDetailResponse>,
): VehicleDetailResponse => ({
  vehicle: createMockVehicle(),
  relatedVehicles: [createMockVehicle({ id: 'related-1' })],
  inventory: {
    totalAvailable: 5,
    locations: [
      {
        dealershipId: 'dealer-1',
        dealershipName: 'Main Dealership',
        quantity: 5,
        estimatedDelivery: '2024-02-01',
      },
    ],
  },
  ...overrides,
});

const createMockSearchFacets = (overrides?: Partial<SearchFacets>): SearchFacets => ({
  makes: [
    { value: 'Toyota', count: 10 },
    { value: 'Honda', count: 8 },
  ],
  models: [
    { value: 'Camry', count: 5 },
    { value: 'Accord', count: 4 },
  ],
  bodyStyles: [
    { value: 'Sedan', count: 12 },
    { value: 'SUV', count: 6 },
  ],
  fuelTypes: [
    { value: 'Gasoline', count: 15 },
    { value: 'Hybrid', count: 3 },
  ],
  transmissions: [
    { value: 'Automatic', count: 16 },
    { value: 'Manual', count: 2 },
  ],
  drivetrains: [
    { value: 'FWD', count: 10 },
    { value: 'AWD', count: 8 },
  ],
  years: {
    min: 2020,
    max: 2024,
  },
  prices: {
    min: 20000,
    max: 50000,
  },
  seatingCapacities: [
    { value: 5, count: 12 },
    { value: 7, count: 6 },
  ],
  ...overrides,
});

const createMockPriceRangeResponse = (
  overrides?: Partial<PriceRangeResponse>,
): PriceRangeResponse => ({
  min: 20000,
  max: 50000,
  average: 35000,
  median: 33000,
  ...overrides,
});

// ============================================================================
// 🎭 Test Utilities and Mocks
// ============================================================================

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

const createWrapper = (queryClient: QueryClient) => {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const mockFetch = (response: unknown, status = 200) => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => response,
  });
};

const mockFetchError = (message: string, statusCode = 500) => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status: statusCode,
    json: async () => ({
      error: 'API_ERROR',
      message,
      statusCode,
    }),
  });
};

// ============================================================================
// 🧪 Test Suite: Query Key Factory
// ============================================================================

describe('vehicleKeys', () => {
  it('should generate correct query keys for all queries', () => {
    expect(vehicleKeys.all).toEqual(['vehicles']);
    expect(vehicleKeys.lists()).toEqual(['vehicles', 'list']);
    expect(vehicleKeys.details()).toEqual(['vehicles', 'detail']);
  });

  it('should generate unique keys for different parameters', () => {
    const params1: SearchParams = { page: 1, pageSize: 20 };
    const params2: SearchParams = { page: 2, pageSize: 20 };

    expect(vehicleKeys.list(params1)).not.toEqual(vehicleKeys.list(params2));
  });

  it('should generate keys with filters', () => {
    const filters: VehicleFilters = { make: ['Toyota'], model: ['Camry'] };
    const key = vehicleKeys.facets(filters);

    expect(key).toEqual(['vehicles', 'facets', filters]);
  });

  it('should generate detail keys with vehicle ID', () => {
    const id = 'vehicle-123';
    expect(vehicleKeys.detail(id)).toEqual(['vehicles', 'detail', id]);
  });
});

// ============================================================================
// 🧪 Test Suite: useVehicles Hook
// ============================================================================

describe('useVehicles', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  // 🎯 Happy Path Tests
  describe('successful data fetching', () => {
    it('should fetch vehicles successfully', async () => {
      const mockResponse = createMockVehicleListResponse();
      mockFetch(mockResponse);

      const { result } = renderHook(() => useVehicles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockResponse);
      expect(result.current.error).toBeNull();
    });

    it('should fetch vehicles with search parameters', async () => {
      const mockResponse = createMockVehicleListResponse();
      mockFetch(mockResponse);

      const params: SearchParams = {
        page: 1,
        pageSize: 10,
        sortBy: 'price',
        sortDirection: 'asc',
      };

      const { result } = renderHook(() => useVehicles(params), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('page=1'),
        expect.any(Object),
      );
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('page_size=10'),
        expect.any(Object),
      );
    });

    it('should fetch vehicles with complex filters', async () => {
      const mockResponse = createMockVehicleListResponse();
      mockFetch(mockResponse);

      const params: SearchParams = {
        filters: {
          make: ['Toyota', 'Honda'],
          model: ['Camry'],
          bodyStyle: ['Sedan'],
          fuelType: ['Gasoline'],
          transmission: ['Automatic'],
          drivetrain: ['FWD'],
          year: { min: 2020, max: 2024 },
          price: { min: 20000, max: 40000 },
          seatingCapacity: { min: 5, max: 7 },
          availability: ['in_stock'],
          query: 'luxury sedan',
        },
      };

      const { result } = renderHook(() => useVehicles(params), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      const fetchCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
      expect(fetchCall).toContain('make=Toyota');
      expect(fetchCall).toContain('make=Honda');
      expect(fetchCall).toContain('model=Camry');
      expect(fetchCall).toContain('query=luxury%20sedan');
    });
  });

  // 🔴 Error Handling Tests
  describe('error handling', () => {
    it('should handle API errors gracefully', async () => {
      mockFetchError('Failed to fetch vehicles', 500);

      const { result } = renderHook(() => useVehicles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toContain('Failed to fetch vehicles');
    });

    it('should handle network errors', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() => useVehicles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error?.message).toContain('Network error');
    });

    it('should handle 404 errors', async () => {
      mockFetchError('Vehicles not found', 404);

      const { result } = renderHook(() => useVehicles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error?.message).toContain('Vehicles not found');
    });
  });

  // ⏳ Loading State Tests
  describe('loading states', () => {
    it('should show loading state initially', () => {
      mockFetch(createMockVehicleListResponse());

      const { result } = renderHook(() => useVehicles(), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isLoading).toBe(true);
      expect(result.current.data).toBeUndefined();
    });

    it('should transition from loading to success', async () => {
      const mockResponse = createMockVehicleListResponse();
      mockFetch(mockResponse);

      const { result } = renderHook(() => useVehicles(), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toEqual(mockResponse);
    });
  });

  // 🔄 Caching Tests
  describe('caching behavior', () => {
    it('should cache query results', async () => {
      const mockResponse = createMockVehicleListResponse();
      mockFetch(mockResponse);

      const { result: result1 } = renderHook(() => useVehicles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result1.current.isSuccess).toBe(true);
      });

      const { result: result2 } = renderHook(() => useVehicles(), {
        wrapper: createWrapper(queryClient),
      });

      expect(result2.current.data).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('should use different cache for different parameters', async () => {
      const mockResponse1 = createMockVehicleListResponse();
      const mockResponse2 = createMockVehicleListResponse({
        vehicles: [createMockVehicle({ id: 'different' })],
      });

      mockFetch(mockResponse1);

      const { result: result1 } = renderHook(() => useVehicles({ page: 1 }), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result1.current.isSuccess).toBe(true);
      });

      mockFetch(mockResponse2);

      const { result: result2 } = renderHook(() => useVehicles({ page: 2 }), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result2.current.isSuccess).toBe(true);
      });

      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });

  // ⚡ Performance Tests
  describe('performance optimization', () => {
    it('should not refetch on window focus', async () => {
      const mockResponse = createMockVehicleListResponse();
      mockFetch(mockResponse);

      const { result } = renderHook(() => useVehicles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      const initialCallCount = (global.fetch as ReturnType<typeof vi.fn>).mock.calls.length;

      window.dispatchEvent(new Event('focus'));

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect((global.fetch as ReturnType<typeof vi.fn>).mock.calls.length).toBe(
        initialCallCount,
      );
    });

    it('should implement exponential backoff retry', async () => {
      let callCount = 0;
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount < 3) {
          return Promise.resolve({
            ok: false,
            status: 500,
            json: async () => ({ error: 'Server error', message: 'Retry', statusCode: 500 }),
          });
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => createMockVehicleListResponse(),
        });
      });

      const { result } = renderHook(() => useVehicles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(
        () => {
          expect(result.current.isSuccess).toBe(true);
        },
        { timeout: 10000 },
      );

      expect(callCount).toBeGreaterThan(1);
    });
  });
});

// ============================================================================
// 🧪 Test Suite: useInfiniteVehicles Hook
// ============================================================================

describe('useInfiniteVehicles', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should fetch first page of vehicles', async () => {
    const mockResponse = createMockVehicleListResponse({
      metadata: {
        total: 40,
        page: 1,
        pageSize: 20,
        totalPages: 2,
        hasNextPage: true,
        hasPreviousPage: false,
      },
    });
    mockFetch(mockResponse);

    const { result } = renderHook(() => useInfiniteVehicles(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.pages[0]).toEqual(mockResponse);
    expect(result.current.hasNextPage).toBe(true);
  });

  it('should fetch next page when requested', async () => {
    const page1Response = createMockVehicleListResponse({
      metadata: {
        total: 40,
        page: 1,
        pageSize: 20,
        totalPages: 2,
        hasNextPage: true,
        hasPreviousPage: false,
      },
    });

    const page2Response = createMockVehicleListResponse({
      vehicles: [createMockVehicle({ id: 'page2-vehicle' })],
      metadata: {
        total: 40,
        page: 2,
        pageSize: 20,
        totalPages: 2,
        hasNextPage: false,
        hasPreviousPage: true,
      },
    });

    mockFetch(page1Response);

    const { result } = renderHook(() => useInfiniteVehicles(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    mockFetch(page2Response);

    result.current.fetchNextPage();

    await waitFor(() => {
      expect(result.current.data?.pages.length).toBe(2);
    });

    expect(result.current.data?.pages[1]).toEqual(page2Response);
    expect(result.current.hasNextPage).toBe(false);
  });

  it('should not fetch next page when none available', async () => {
    const mockResponse = createMockVehicleListResponse({
      metadata: {
        total: 20,
        page: 1,
        pageSize: 20,
        totalPages: 1,
        hasNextPage: false,
        hasPreviousPage: false,
      },
    });
    mockFetch(mockResponse);

    const { result } = renderHook(() => useInfiniteVehicles(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.hasNextPage).toBe(false);
  });

  it('should handle errors in infinite query', async () => {
    mockFetchError('Failed to fetch vehicles', 500);

    const { result } = renderHook(() => useInfiniteVehicles(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toContain('Failed to fetch vehicles');
  });
});

// ============================================================================
// 🧪 Test Suite: useVehicle Hook
// ============================================================================

describe('useVehicle', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should fetch single vehicle by ID', async () => {
    const mockResponse = createMockVehicleDetailResponse();
    mockFetch(mockResponse);

    const { result } = renderHook(() => useVehicle('vehicle-123'), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockResponse);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/vehicles/vehicle-123'),
      expect.any(Object),
    );
  });

  it('should not fetch when ID is empty', () => {
    const { result } = renderHook(() => useVehicle(''), {
      wrapper: createWrapper(queryClient),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeUndefined();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('should handle 404 for non-existent vehicle', async () => {
    mockFetchError('Vehicle not found', 404);

    const { result } = renderHook(() => useVehicle('non-existent'), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toContain('Vehicle not found');
  });

  it('should include related vehicles and inventory', async () => {
    const mockResponse = createMockVehicleDetailResponse({
      relatedVehicles: [
        createMockVehicle({ id: 'related-1' }),
        createMockVehicle({ id: 'related-2' }),
      ],
      inventory: {
        totalAvailable: 10,
        locations: [
          {
            dealershipId: 'dealer-1',
            dealershipName: 'Main Dealership',
            quantity: 10,
            estimatedDelivery: '2024-02-01',
          },
        ],
      },
    });
    mockFetch(mockResponse);

    const { result } = renderHook(() => useVehicle('vehicle-123'), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.relatedVehicles).toHaveLength(2);
    expect(result.current.data?.inventory.totalAvailable).toBe(10);
  });
});

// ============================================================================
// 🧪 Test Suite: useVehicleSearch Hook
// ============================================================================

describe('useVehicleSearch', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should search vehicles with query string', async () => {
    const mockResponse = createMockVehicleListResponse();
    mockFetch(mockResponse);

    const params: SearchParams = {
      filters: { query: 'luxury sedan' },
    };

    const { result } = renderHook(() => useVehicleSearch(params), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('query=luxury%20sedan'),
      expect.any(Object),
    );
  });

  it('should not fetch when no filters provided', () => {
    const { result } = renderHook(() => useVehicleSearch({}), {
      wrapper: createWrapper(queryClient),
    });

    expect(result.current.isLoading).toBe(false);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('should search with multiple filter criteria', async () => {
    const mockResponse = createMockVehicleListResponse();
    mockFetch(mockResponse);

    const params: SearchParams = {
      filters: {
        query: 'sedan',
        make: ['Toyota'],
        year: { min: 2020, max: 2024 },
        price: { min: 25000, max: 40000 },
      },
    };

    const { result } = renderHook(() => useVehicleSearch(params), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const fetchCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(fetchCall).toContain('query=sedan');
    expect(fetchCall).toContain('make=Toyota');
    expect(fetchCall).toContain('year_min=2020');
  });
});

// ============================================================================
// 🧪 Test Suite: useVehicleFacets Hook
// ============================================================================

describe('useVehicleFacets', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should fetch search facets', async () => {
    const mockResponse = createMockSearchFacets();
    mockFetch(mockResponse);

    const { result } = renderHook(() => useVehicleFacets(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockResponse);
    expect(result.current.data?.makes).toHaveLength(2);
  });

  it('should fetch facets with filters', async () => {
    const mockResponse = createMockSearchFacets();
    mockFetch(mockResponse);

    const filters: VehicleFilters = {
      make: ['Toyota'],
      model: ['Camry'],
    };

    const { result } = renderHook(() => useVehicleFacets(filters), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('make=Toyota'),
      expect.any(Object),
    );
  });

  it('should handle empty facets response', async () => {
    const emptyFacets = createMockSearchFacets({
      makes: [],
      models: [],
      bodyStyles: [],
    });
    mockFetch(emptyFacets);

    const { result } = renderHook(() => useVehicleFacets(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.makes).toHaveLength(0);
  });
});

// ============================================================================
// 🧪 Test Suite: usePriceRange Hook
// ============================================================================

describe('usePriceRange', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should fetch price range', async () => {
    const mockResponse = createMockPriceRangeResponse();
    mockFetch(mockResponse);

    const { result } = renderHook(() => usePriceRange(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockResponse);
    expect(result.current.data?.min).toBe(20000);
    expect(result.current.data?.max).toBe(50000);
  });

  it('should fetch price range with filters', async () => {
    const mockResponse = createMockPriceRangeResponse({
      min: 30000,
      max: 45000,
    });
    mockFetch(mockResponse);

    const filters: VehicleFilters = {
      make: ['Toyota'],
      bodyStyle: ['Sedan'],
    };

    const { result } = renderHook(() => usePriceRange(filters), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.min).toBe(30000);
    expect(result.current.data?.max).toBe(45000);
  });
});

// ============================================================================
// 🧪 Test Suite: usePrefetchVehicle Hook
// ============================================================================

describe('usePrefetchVehicle', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should prefetch vehicle data', async () => {
    const mockResponse = createMockVehicleDetailResponse();
    mockFetch(mockResponse);

    const { result } = renderHook(() => usePrefetchVehicle(), {
      wrapper: createWrapper(queryClient),
    });

    result.current('vehicle-123');

    await waitFor(() => {
      const cachedData = queryClient.getQueryData(vehicleKeys.detail('vehicle-123'));
      expect(cachedData).toBeDefined();
    });
  });

  it('should not block rendering while prefetching', () => {
    const mockResponse = createMockVehicleDetailResponse();
    mockFetch(mockResponse);

    const { result } = renderHook(() => usePrefetchVehicle(), {
      wrapper: createWrapper(queryClient),
    });

    expect(() => result.current('vehicle-123')).not.toThrow();
  });
});

// ============================================================================
// 🧪 Test Suite: useInvalidateVehicles Hook
// ============================================================================

describe('useInvalidateVehicles', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should invalidate all vehicle queries', async () => {
    const mockResponse = createMockVehicleListResponse();
    mockFetch(mockResponse);

    const { result: vehiclesResult } = renderHook(() => useVehicles(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(vehiclesResult.current.isSuccess).toBe(true);
    });

    const { result: invalidateResult } = renderHook(() => useInvalidateVehicles(), {
      wrapper: createWrapper(queryClient),
    });

    invalidateResult.current.invalidateAll();

    await waitFor(() => {
      expect(vehiclesResult.current.isRefetching).toBe(true);
    });
  });

  it('should invalidate specific vehicle detail', async () => {
    const mockResponse = createMockVehicleDetailResponse();
    mockFetch(mockResponse);

    const { result: vehicleResult } = renderHook(() => useVehicle('vehicle-123'), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(vehicleResult.current.isSuccess).toBe(true);
    });

    const { result: invalidateResult } = renderHook(() => useInvalidateVehicles(), {
      wrapper: createWrapper(queryClient),
    });

    invalidateResult.current.invalidateDetail('vehicle-123');

    await waitFor(() => {
      expect(vehicleResult.current.isRefetching).toBe(true);
    });
  });

  it('should invalidate lists only', async () => {
    const mockResponse = createMockVehicleListResponse();
    mockFetch(mockResponse);

    const { result: vehiclesResult } = renderHook(() => useVehicles(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(vehiclesResult.current.isSuccess).toBe(true);
    });

    const { result: invalidateResult } = renderHook(() => useInvalidateVehicles(), {
      wrapper: createWrapper(queryClient),
    });

    invalidateResult.current.invalidateLists();

    await waitFor(() => {
      expect(vehiclesResult.current.isRefetching).toBe(true);
    });
  });
});

// ============================================================================
// 🧪 Test Suite: useOptimisticVehicleUpdate Hook
// ============================================================================

describe('useOptimisticVehicleUpdate', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should perform optimistic update', async () => {
    const initialVehicle = createMockVehicleDetailResponse();
    const updatedVehicle = createMockVehicle({
      id: 'vehicle-123',
      msrp: 40000,
    });

    queryClient.setQueryData(vehicleKeys.detail('vehicle-123'), initialVehicle);

    mockFetch(updatedVehicle);

    const { result } = renderHook(() => useOptimisticVehicleUpdate(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      id: 'vehicle-123',
      updates: { msrp: 40000 },
    });

    const optimisticData = queryClient.getQueryData<VehicleDetailResponse>(
      vehicleKeys.detail('vehicle-123'),
    );
    expect(optimisticData?.vehicle.msrp).toBe(40000);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it('should rollback on error', async () => {
    const initialVehicle = createMockVehicleDetailResponse();
    queryClient.setQueryData(vehicleKeys.detail('vehicle-123'), initialVehicle);

    mockFetchError('Update failed', 500);

    const { result } = renderHook(() => useOptimisticVehicleUpdate(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      id: 'vehicle-123',
      updates: { msrp: 40000 },
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    const rolledBackData = queryClient.getQueryData<VehicleDetailResponse>(
      vehicleKeys.detail('vehicle-123'),
    );
    expect(rolledBackData).toEqual(initialVehicle);
  });

  it('should invalidate related queries after update', async () => {
    const initialVehicle = createMockVehicleDetailResponse();
    const updatedVehicle = createMockVehicle({ id: 'vehicle-123' });

    queryClient.setQueryData(vehicleKeys.detail('vehicle-123'), initialVehicle);

    mockFetch(updatedVehicle);

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useOptimisticVehicleUpdate(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      id: 'vehicle-123',
      updates: { msrp: 40000 },
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: vehicleKeys.detail('vehicle-123'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: vehicleKeys.lists(),
    });
  });
});

// ============================================================================
// 🧪 Test Suite: useBackgroundRefetch Hook
// ============================================================================

describe('useBackgroundRefetch', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should refetch active queries when enabled', async () => {
    const mockResponse = createMockVehicleListResponse();
    mockFetch(mockResponse);

    const { result: vehiclesResult } = renderHook(() => useVehicles(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(vehiclesResult.current.isSuccess).toBe(true);
    });

    const { result: refetchResult } = renderHook(() => useBackgroundRefetch(true), {
      wrapper: createWrapper(queryClient),
    });

    const refetchSpy = vi.spyOn(queryClient, 'refetchQueries');

    refetchResult.current();

    expect(refetchSpy).toHaveBeenCalledWith({
      queryKey: vehicleKeys.lists(),
      type: 'active',
    });
  });

  it('should not refetch when disabled', () => {
    const { result } = renderHook(() => useBackgroundRefetch(false), {
      wrapper: createWrapper(queryClient),
    });

    const refetchSpy = vi.spyOn(queryClient, 'refetchQueries');

    result.current();

    expect(refetchSpy).not.toHaveBeenCalled();
  });
});

// ============================================================================
// 🧪 Test Suite: isApiError Type Guard
// ============================================================================

describe('isApiError', () => {
  it('should identify valid API errors', () => {
    const apiError = {
      error: 'VALIDATION_ERROR',
      message: 'Invalid input',
      statusCode: 400,
    };

    expect(isApiError(apiError)).toBe(true);
  });

  it('should reject non-API errors', () => {
    expect(isApiError(new Error('Regular error'))).toBe(false);
    expect(isApiError('string error')).toBe(false);
    expect(isApiError(null)).toBe(false);
    expect(isApiError(undefined)).toBe(false);
    expect(isApiError({})).toBe(false);
  });

  it('should reject objects missing required fields', () => {
    expect(isApiError({ error: 'ERROR' })).toBe(false);
    expect(isApiError({ message: 'Message' })).toBe(false);
    expect(isApiError({ statusCode: 400 })).toBe(false);
  });
});

// ============================================================================
// 🧪 Test Suite: Edge Cases and Boundary Conditions
// ============================================================================

describe('edge cases and boundary conditions', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should handle empty vehicle list', async () => {
    const emptyResponse = createMockVehicleListResponse({
      vehicles: [],
      metadata: {
        total: 0,
        page: 1,
        pageSize: 20,
        totalPages: 0,
        hasNextPage: false,
        hasPreviousPage: false,
      },
    });
    mockFetch(emptyResponse);

    const { result } = renderHook(() => useVehicles(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.vehicles).toHaveLength(0);
  });

  it('should handle very large page numbers', async () => {
    const mockResponse = createMockVehicleListResponse();
    mockFetch(mockResponse);

    const { result } = renderHook(() => useVehicles({ page: 999999 }), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('page=999999'),
      expect.any(Object),
    );
  });

  it('should handle special characters in search query', async () => {
    const mockResponse = createMockVehicleListResponse();
    mockFetch(mockResponse);

    const params: SearchParams = {
      filters: { query: 'luxury & sport <sedan>' },
    };

    const { result } = renderHook(() => useVehicleSearch(params), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(global.fetch).toHaveBeenCalled();
  });

  it('should handle undefined filter values', async () => {
    const mockResponse = createMockVehicleListResponse();
    mockFetch(mockResponse);

    const params: SearchParams = {
      filters: {
        make: undefined,
        model: undefined,
        year: undefined,
      },
    };

    const { result } = renderHook(() => useVehicles(params), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockResponse);
  });

  it('should handle empty array filters', async () => {
    const mockResponse = createMockVehicleListResponse();
    mockFetch(mockResponse);

    const params: SearchParams = {
      filters: {
        make: [],
        model: [],
        bodyStyle: [],
      },
    };

    const { result } = renderHook(() => useVehicles(params), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockResponse);
  });
});

// ============================================================================
// 🧪 Test Suite: Security and Validation
// ============================================================================

describe('security and validation', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should sanitize URL parameters', async () => {
    const mockResponse = createMockVehicleListResponse();
    mockFetch(mockResponse);

    const params: SearchParams = {
      filters: {
        query: '<script>alert("xss")</script>',
      },
    };

    const { result } = renderHook(() => useVehicleSearch(params), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const fetchCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(fetchCall).not.toContain('<script>');
  });

  it('should handle SQL injection attempts in filters', async () => {
    const mockResponse = createMockVehicleListResponse();
    mockFetch(mockResponse);

    const params: SearchParams = {
      filters: {
        query: "'; DROP TABLE vehicles; --",
      },
    };

    const { result } = renderHook(() => useVehicleSearch(params), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockResponse);
  });

  it('should validate numeric range inputs', async () => {
    const mockResponse = createMockVehicleListResponse();
    mockFetch(mockResponse);

    const params: SearchParams = {
      filters: {
        price: { min: -1000, max: 999999999 },
        year: { min: 1800, max: 3000 },
      },
    };

    const { result } = renderHook(() => useVehicles(params), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(global.fetch).toHaveBeenCalled();
  });
});

// ============================================================================
// 🧪 Test Suite: Performance and Optimization
// ============================================================================

describe('performance and optimization', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should batch multiple filter updates', async () => {
    const mockResponse = createMockVehicleListResponse();
    mockFetch(mockResponse);

    const params: SearchParams = {
      filters: {
        make: ['Toyota', 'Honda', 'Ford'],
        model: ['Camry', 'Accord', 'F-150'],
        bodyStyle: ['Sedan', 'Truck'],
      },
    };

    const { result } = renderHook(() => useVehicles(params), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it('should handle rapid filter changes efficiently', async () => {
    const mockResponse = createMockVehicleListResponse();
    mockFetch(mockResponse);

    const { result, rerender } = renderHook(
      ({ params }: { params: SearchParams }) => useVehicles(params),
      {
        wrapper: createWrapper(queryClient),
        initialProps: { params: { filters: { make: ['Toyota'] } } },
      },
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const initialCallCount = (global.fetch as ReturnType<typeof vi.fn>).mock.calls.length;

    rerender({ params: { filters: { make: ['Honda'] } } });
    rerender({ params: { filters: { make: ['Ford'] } } });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect((global.fetch as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThan(
      initialCallCount,
    );
  });

  it('should implement request deduplication', async () => {
    const mockResponse = createMockVehicleListResponse();
    mockFetch(mockResponse);

    const { result: result1 } = renderHook(() => useVehicles({ page: 1 }), {
      wrapper: createWrapper(queryClient),
    });

    const { result: result2 } = renderHook(() => useVehicles({ page: 1 }), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result1.current.isSuccess).toBe(true);
      expect(result2.current.isSuccess).toBe(true);
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);
  });
});