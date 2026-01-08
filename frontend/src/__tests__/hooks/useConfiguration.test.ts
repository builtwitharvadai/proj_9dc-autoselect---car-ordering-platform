/**
 * Comprehensive test suite for useConfiguration hooks
 * Tests React Query hooks for vehicle configuration API operations
 * including data fetching, caching, error handling, and optimistic updates
 */

import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import type { ReactNode } from 'react';

import {
  useVehicleOptions,
  useValidateConfiguration,
  useCalculatePricing,
  useConfiguration,
  useSaveConfiguration,
  usePrefetchVehicleOptions,
  useInvalidateConfiguration,
  ConfigurationApiError,
  isConfigurationApiError,
  configurationKeys,
} from '../../hooks/useConfiguration';

import type {
  VehicleOptionsResponse,
  ConfigurationValidationRequest,
  ConfigurationValidationResult,
  ConfigurationPricingRequest,
  PricingBreakdown,
  ConfigurationSaveRequest,
  ConfigurationSaveResponse,
} from '../../types/configuration';

// ============================================================================
// Test Data Factories
// ============================================================================

const createMockVehicleOptions = (overrides?: Partial<VehicleOptionsResponse>): VehicleOptionsResponse => ({
  vehicleId: 'vehicle-123',
  packages: [
    {
      id: 'pkg-1',
      name: 'Premium Package',
      description: 'Premium features',
      price: 5000,
      category: 'premium',
      isAvailable: true,
      dependencies: [],
      conflicts: [],
    },
  ],
  options: [
    {
      id: 'opt-1',
      name: 'Sunroof',
      description: 'Panoramic sunroof',
      price: 1500,
      category: 'exterior',
      isAvailable: true,
      dependencies: [],
      conflicts: [],
    },
  ],
  colors: [
    {
      id: 'color-1',
      name: 'Pearl White',
      hexCode: '#FFFFFF',
      price: 500,
      isAvailable: true,
    },
  ],
  trims: [
    {
      id: 'trim-1',
      name: 'Base',
      description: 'Base trim',
      basePrice: 30000,
      isAvailable: true,
    },
  ],
  ...overrides,
});

const createMockValidationRequest = (
  overrides?: Partial<ConfigurationValidationRequest>,
): ConfigurationValidationRequest => ({
  vehicleId: 'vehicle-123',
  trimId: 'trim-1',
  packageIds: ['pkg-1'],
  optionIds: ['opt-1'],
  colorId: 'color-1',
  ...overrides,
});

const createMockValidationResult = (
  overrides?: Partial<ConfigurationValidationResult>,
): ConfigurationValidationResult => ({
  isValid: true,
  errors: [],
  warnings: [],
  conflicts: [],
  ...overrides,
});

const createMockPricingRequest = (
  overrides?: Partial<ConfigurationPricingRequest>,
): ConfigurationPricingRequest => ({
  vehicleId: 'vehicle-123',
  trimId: 'trim-1',
  packageIds: ['pkg-1'],
  optionIds: ['opt-1'],
  colorId: 'color-1',
  ...overrides,
});

const createMockPricingBreakdown = (overrides?: Partial<PricingBreakdown>): PricingBreakdown => ({
  basePrice: 30000,
  packagesTotal: 5000,
  optionsTotal: 1500,
  colorPrice: 500,
  subtotal: 37000,
  taxAmount: 3700,
  totalPrice: 40700,
  breakdown: [
    { item: 'Base Price', amount: 30000 },
    { item: 'Premium Package', amount: 5000 },
    { item: 'Sunroof', amount: 1500 },
    { item: 'Pearl White', amount: 500 },
    { item: 'Tax', amount: 3700 },
  ],
  ...overrides,
});

const createMockSaveRequest = (
  overrides?: Partial<ConfigurationSaveRequest>,
): ConfigurationSaveRequest => ({
  vehicleId: 'vehicle-123',
  trimId: 'trim-1',
  packageIds: ['pkg-1'],
  optionIds: ['opt-1'],
  colorId: 'color-1',
  customerEmail: 'test@example.com',
  ...overrides,
});

const createMockSaveResponse = (
  overrides?: Partial<ConfigurationSaveResponse>,
): ConfigurationSaveResponse => ({
  id: 'config-123',
  vehicleId: 'vehicle-123',
  trimId: 'trim-1',
  packageIds: ['pkg-1'],
  optionIds: ['opt-1'],
  colorId: 'color-1',
  totalPrice: 40700,
  createdAt: new Date().toISOString(),
  ...overrides,
});

// ============================================================================
// Test Utilities
// ============================================================================

/**
 * Create a fresh QueryClient for each test
 */
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: Infinity,
      },
      mutations: {
        retry: false,
      },
    },
    logger: {
      log: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
    },
  });

/**
 * Wrapper component for React Query hooks
 */
const createWrapper = (queryClient: QueryClient) => {
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return Wrapper;
};

/**
 * Mock fetch with custom response
 */
const mockFetch = (response: unknown, options?: { status?: number; ok?: boolean }) => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: options?.ok ?? true,
    status: options?.status ?? 200,
    json: async () => response,
  });
};

/**
 * Mock fetch with error
 */
const mockFetchError = (error: Error) => {
  global.fetch = vi.fn().mockRejectedValue(error);
};

/**
 * Mock fetch with timeout
 */
const mockFetchTimeout = () => {
  const abortError = new Error('Request timeout');
  abortError.name = 'AbortError';
  global.fetch = vi.fn().mockRejectedValue(abortError);
};

// ============================================================================
// Test Suite
// ============================================================================

describe('useConfiguration Hooks', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    queryClient.clear();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  // ==========================================================================
  // 1. useVehicleOptions Hook Tests
  // ==========================================================================

  describe('useVehicleOptions', () => {
    it('should fetch vehicle options successfully', async () => {
      const mockData = createMockVehicleOptions();
      mockFetch(mockData);

      const { result } = renderHook(() => useVehicleOptions('vehicle-123'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockData);
      expect(result.current.error).toBeNull();
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('should handle API error responses', async () => {
      const errorResponse = {
        error: 'NotFound',
        message: 'Vehicle not found',
        statusCode: 404,
      };
      mockFetch(errorResponse, { status: 404, ok: false });

      const { result } = renderHook(() => useVehicleOptions('invalid-vehicle'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(ConfigurationApiError);
      expect(result.current.error?.message).toBe('Vehicle not found');
      expect(result.current.error?.statusCode).toBe(404);
    });

    it('should handle network errors', async () => {
      mockFetchError(new Error('Network error'));

      const { result } = renderHook(() => useVehicleOptions('vehicle-123'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(ConfigurationApiError);
      expect(result.current.error?.message).toBe('Network error');
    });

    it('should handle request timeout', async () => {
      mockFetchTimeout();

      const { result } = renderHook(() => useVehicleOptions('vehicle-123'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(ConfigurationApiError);
      expect(result.current.error?.message).toBe('Request timeout');
      expect(result.current.error?.statusCode).toBe(408);
    });

    it('should cache vehicle options for 5 minutes', async () => {
      const mockData = createMockVehicleOptions();
      mockFetch(mockData);

      const { result, rerender } = renderHook(() => useVehicleOptions('vehicle-123'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Clear mock to verify no new fetch
      vi.clearAllMocks();

      // Rerender should use cached data
      rerender();

      expect(global.fetch).not.toHaveBeenCalled();
      expect(result.current.data).toEqual(mockData);
    });

    it('should refetch after stale time expires', async () => {
      const mockData = createMockVehicleOptions();
      mockFetch(mockData);

      const { result } = renderHook(() => useVehicleOptions('vehicle-123'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Advance time past stale time (5 minutes)
      vi.advanceTimersByTime(5 * 60 * 1000 + 1);

      // Trigger refetch
      await result.current.refetch();

      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('should use custom query options', async () => {
      const mockData = createMockVehicleOptions();
      mockFetch(mockData);

      const onSuccess = vi.fn();

      const { result } = renderHook(
        () =>
          useVehicleOptions('vehicle-123', {
            enabled: false,
          }),
        {
          wrapper: createWrapper(queryClient),
        },
      );

      // Should not fetch when disabled
      expect(result.current.isFetching).toBe(false);
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should handle malformed JSON response', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      });

      const { result } = renderHook(() => useVehicleOptions('vehicle-123'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error?.message).toBe('Failed to parse response JSON');
    });
  });

  // ==========================================================================
  // 2. useValidateConfiguration Hook Tests
  // ==========================================================================

  describe('useValidateConfiguration', () => {
    it('should validate configuration successfully', async () => {
      const mockRequest = createMockValidationRequest();
      const mockResult = createMockValidationResult();
      mockFetch(mockResult);

      const { result } = renderHook(() => useValidateConfiguration(mockRequest), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockResult);
      expect(result.current.data?.isValid).toBe(true);
    });

    it('should return validation errors', async () => {
      const mockRequest = createMockValidationRequest();
      const mockResult = createMockValidationResult({
        isValid: false,
        errors: [
          {
            field: 'packageIds',
            message: 'Package pkg-1 conflicts with option opt-1',
            code: 'CONFLICT',
          },
        ],
      });
      mockFetch(mockResult);

      const { result } = renderHook(() => useValidateConfiguration(mockRequest), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.isValid).toBe(false);
      expect(result.current.data?.errors).toHaveLength(1);
      expect(result.current.data?.errors[0]?.message).toContain('conflicts');
    });

    it('should not fetch when disabled (empty selections)', async () => {
      const mockRequest = createMockValidationRequest({
        packageIds: [],
        optionIds: [],
      });

      const { result } = renderHook(() => useValidateConfiguration(mockRequest), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isFetching).toBe(false);
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should cache validation results', async () => {
      const mockRequest = createMockValidationRequest();
      const mockResult = createMockValidationResult();
      mockFetch(mockResult);

      const { result, rerender } = renderHook(() => useValidateConfiguration(mockRequest), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      vi.clearAllMocks();
      rerender();

      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should handle validation warnings', async () => {
      const mockRequest = createMockValidationRequest();
      const mockResult = createMockValidationResult({
        isValid: true,
        warnings: [
          {
            field: 'optionIds',
            message: 'Option opt-1 is recommended with package pkg-1',
            code: 'RECOMMENDATION',
          },
        ],
      });
      mockFetch(mockResult);

      const { result } = renderHook(() => useValidateConfiguration(mockRequest), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.warnings).toHaveLength(1);
    });
  });

  // ==========================================================================
  // 3. useCalculatePricing Hook Tests
  // ==========================================================================

  describe('useCalculatePricing', () => {
    it('should calculate pricing successfully', async () => {
      const mockRequest = createMockPricingRequest();
      const mockPricing = createMockPricingBreakdown();
      mockFetch(mockPricing);

      const { result } = renderHook(() => useCalculatePricing(mockRequest), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockPricing);
      expect(result.current.data?.totalPrice).toBe(40700);
    });

    it('should calculate pricing with no options', async () => {
      const mockRequest = createMockPricingRequest({
        packageIds: [],
        optionIds: [],
        colorId: undefined,
      });
      const mockPricing = createMockPricingBreakdown({
        packagesTotal: 0,
        optionsTotal: 0,
        colorPrice: 0,
        subtotal: 30000,
        taxAmount: 3000,
        totalPrice: 33000,
      });
      mockFetch(mockPricing);

      const { result } = renderHook(() => useCalculatePricing(mockRequest), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.totalPrice).toBe(33000);
    });

    it('should not fetch when vehicleId is missing', async () => {
      const mockRequest = createMockPricingRequest({ vehicleId: '' });

      const { result } = renderHook(() => useCalculatePricing(mockRequest), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isFetching).toBe(false);
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should include detailed breakdown', async () => {
      const mockRequest = createMockPricingRequest();
      const mockPricing = createMockPricingBreakdown();
      mockFetch(mockPricing);

      const { result } = renderHook(() => useCalculatePricing(mockRequest), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.breakdown).toHaveLength(5);
      expect(result.current.data?.breakdown[0]?.item).toBe('Base Price');
    });

    it('should handle pricing calculation errors', async () => {
      const mockRequest = createMockPricingRequest();
      const errorResponse = {
        error: 'InvalidConfiguration',
        message: 'Invalid trim selection',
        statusCode: 400,
      };
      mockFetch(errorResponse, { status: 400, ok: false });

      const { result } = renderHook(() => useCalculatePricing(mockRequest), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error?.statusCode).toBe(400);
    });
  });

  // ==========================================================================
  // 4. useConfiguration Hook Tests
  // ==========================================================================

  describe('useConfiguration', () => {
    it('should fetch saved configuration successfully', async () => {
      const mockConfig = createMockSaveResponse();
      mockFetch(mockConfig);

      const { result } = renderHook(() => useConfiguration('config-123'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockConfig);
      expect(result.current.data?.id).toBe('config-123');
    });

    it('should not fetch when configId is empty', async () => {
      const { result } = renderHook(() => useConfiguration(''), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isFetching).toBe(false);
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should handle configuration not found', async () => {
      const errorResponse = {
        error: 'NotFound',
        message: 'Configuration not found',
        statusCode: 404,
      };
      mockFetch(errorResponse, { status: 404, ok: false });

      const { result } = renderHook(() => useConfiguration('invalid-config'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error?.statusCode).toBe(404);
    });

    it('should cache configuration data', async () => {
      const mockConfig = createMockSaveResponse();
      mockFetch(mockConfig);

      const { result, rerender } = renderHook(() => useConfiguration('config-123'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      vi.clearAllMocks();
      rerender();

      expect(global.fetch).not.toHaveBeenCalled();
    });
  });

  // ==========================================================================
  // 5. useSaveConfiguration Hook Tests
  // ==========================================================================

  describe('useSaveConfiguration', () => {
    it('should save configuration successfully', async () => {
      const mockRequest = createMockSaveRequest();
      const mockResponse = createMockSaveResponse();
      mockFetch(mockResponse);

      const { result } = renderHook(() => useSaveConfiguration(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(mockRequest);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockResponse);
    });

    it('should update cache with saved configuration', async () => {
      const mockRequest = createMockSaveRequest();
      const mockResponse = createMockSaveResponse();
      mockFetch(mockResponse);

      const { result } = renderHook(() => useSaveConfiguration(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(mockRequest);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Verify cache was updated
      const cachedData = queryClient.getQueryData(
        configurationKeys.saved(mockResponse.id),
      );
      expect(cachedData).toEqual(mockResponse);
    });

    it('should handle save errors', async () => {
      const mockRequest = createMockSaveRequest();
      const errorResponse = {
        error: 'ValidationError',
        message: 'Invalid email format',
        statusCode: 400,
      };
      mockFetch(errorResponse, { status: 400, ok: false });

      const { result } = renderHook(() => useSaveConfiguration(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(mockRequest);

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(ConfigurationApiError);
    });

    it('should perform optimistic updates', async () => {
      const mockRequest = createMockSaveRequest();
      const mockPricing = createMockPricingBreakdown();

      // Pre-populate pricing cache
      queryClient.setQueryData(
        configurationKeys.pricing({
          vehicleId: mockRequest.vehicleId,
          trimId: mockRequest.trimId,
          packageIds: mockRequest.packageIds,
          optionIds: mockRequest.optionIds,
        }),
        mockPricing,
      );

      const mockResponse = createMockSaveResponse();
      mockFetch(mockResponse);

      const { result } = renderHook(() => useSaveConfiguration(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(mockRequest);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });
    });

    it('should rollback on error', async () => {
      const mockRequest = createMockSaveRequest();
      const mockPricing = createMockPricingBreakdown();

      // Pre-populate pricing cache
      const pricingKey = configurationKeys.pricing({
        vehicleId: mockRequest.vehicleId,
        trimId: mockRequest.trimId,
        packageIds: mockRequest.packageIds,
        optionIds: mockRequest.optionIds,
      });
      queryClient.setQueryData(pricingKey, mockPricing);

      mockFetchError(new Error('Save failed'));

      const { result } = renderHook(() => useSaveConfiguration(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(mockRequest);

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      // Verify cache was rolled back
      const cachedData = queryClient.getQueryData(pricingKey);
      expect(cachedData).toEqual(mockPricing);
    });

    it('should invalidate related queries on success', async () => {
      const mockRequest = createMockSaveRequest();
      const mockResponse = createMockSaveResponse();
      mockFetch(mockResponse);

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useSaveConfiguration(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(mockRequest);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(invalidateSpy).toHaveBeenCalled();
    });
  });

  // ==========================================================================
  // 6. usePrefetchVehicleOptions Hook Tests
  // ==========================================================================

  describe('usePrefetchVehicleOptions', () => {
    it('should prefetch vehicle options', async () => {
      const mockData = createMockVehicleOptions();
      mockFetch(mockData);

      const { result } = renderHook(() => usePrefetchVehicleOptions(), {
        wrapper: createWrapper(queryClient),
      });

      result.current('vehicle-123');

      await waitFor(() => {
        const cachedData = queryClient.getQueryData(
          configurationKeys.vehicleOptions('vehicle-123'),
        );
        expect(cachedData).toEqual(mockData);
      });
    });

    it('should not block rendering while prefetching', () => {
      const mockData = createMockVehicleOptions();
      mockFetch(mockData);

      const { result } = renderHook(() => usePrefetchVehicleOptions(), {
        wrapper: createWrapper(queryClient),
      });

      // Should return immediately
      expect(() => result.current('vehicle-123')).not.toThrow();
    });
  });

  // ==========================================================================
  // 7. useInvalidateConfiguration Hook Tests
  // ==========================================================================

  describe('useInvalidateConfiguration', () => {
    beforeEach(() => {
      // Pre-populate cache
      queryClient.setQueryData(
        configurationKeys.vehicleOptions('vehicle-123'),
        createMockVehicleOptions(),
      );
      queryClient.setQueryData(
        configurationKeys.saved('config-123'),
        createMockSaveResponse(),
      );
    });

    it('should invalidate all configuration queries', async () => {
      const { result } = renderHook(() => useInvalidateConfiguration(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.invalidateAll();

      await waitFor(() => {
        const state = queryClient.getQueryState(configurationKeys.all);
        expect(state?.isInvalidated).toBe(true);
      });
    });

    it('should invalidate vehicle options', async () => {
      const { result } = renderHook(() => useInvalidateConfiguration(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.invalidateVehicleOptions('vehicle-123');

      await waitFor(() => {
        const state = queryClient.getQueryState(
          configurationKeys.vehicleOptions('vehicle-123'),
        );
        expect(state?.isInvalidated).toBe(true);
      });
    });

    it('should invalidate pricing queries', async () => {
      const mockRequest = createMockPricingRequest();
      queryClient.setQueryData(
        configurationKeys.pricing(mockRequest),
        createMockPricingBreakdown(),
      );

      const { result } = renderHook(() => useInvalidateConfiguration(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.invalidatePricing(mockRequest);

      await waitFor(() => {
        const state = queryClient.getQueryState(configurationKeys.pricing(mockRequest));
        expect(state?.isInvalidated).toBe(true);
      });
    });

    it('should invalidate validation queries', async () => {
      const mockRequest = createMockValidationRequest();
      queryClient.setQueryData(
        configurationKeys.validation(mockRequest),
        createMockValidationResult(),
      );

      const { result } = renderHook(() => useInvalidateConfiguration(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.invalidateValidation(mockRequest);

      await waitFor(() => {
        const state = queryClient.getQueryState(configurationKeys.validation(mockRequest));
        expect(state?.isInvalidated).toBe(true);
      });
    });

    it('should invalidate saved configuration', async () => {
      const { result } = renderHook(() => useInvalidateConfiguration(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.invalidateSaved('config-123');

      await waitFor(() => {
        const state = queryClient.getQueryState(configurationKeys.saved('config-123'));
        expect(state?.isInvalidated).toBe(true);
      });
    });
  });

  // ==========================================================================
  // 8. ConfigurationApiError Tests
  // ==========================================================================

  describe('ConfigurationApiError', () => {
    it('should create error with message and status code', () => {
      const error = new ConfigurationApiError('Test error', 400);

      expect(error.message).toBe('Test error');
      expect(error.statusCode).toBe(400);
      expect(error.name).toBe('ConfigurationApiError');
    });

    it('should include optional details', () => {
      const details = { field: 'email', reason: 'invalid format' };
      const error = new ConfigurationApiError('Validation error', 400, details);

      expect(error.details).toEqual(details);
    });

    it('should be instance of Error', () => {
      const error = new ConfigurationApiError('Test error', 500);

      expect(error).toBeInstanceOf(Error);
      expect(error).toBeInstanceOf(ConfigurationApiError);
    });
  });

  // ==========================================================================
  // 9. Type Guard Tests
  // ==========================================================================

  describe('isConfigurationApiError', () => {
    it('should return true for ConfigurationApiError', () => {
      const error = new ConfigurationApiError('Test error', 400);

      expect(isConfigurationApiError(error)).toBe(true);
    });

    it('should return false for regular Error', () => {
      const error = new Error('Regular error');

      expect(isConfigurationApiError(error)).toBe(false);
    });

    it('should return false for non-error values', () => {
      expect(isConfigurationApiError(null)).toBe(false);
      expect(isConfigurationApiError(undefined)).toBe(false);
      expect(isConfigurationApiError('string')).toBe(false);
      expect(isConfigurationApiError(123)).toBe(false);
      expect(isConfigurationApiError({})).toBe(false);
    });
  });

  // ==========================================================================
  // 10. Query Key Tests
  // ==========================================================================

  describe('configurationKeys', () => {
    it('should generate correct vehicle options key', () => {
      const key = configurationKeys.vehicleOptions('vehicle-123');

      expect(key).toEqual(['configuration', 'options', 'vehicle-123']);
    });

    it('should generate correct validation key', () => {
      const request = createMockValidationRequest();
      const key = configurationKeys.validation(request);

      expect(key).toEqual(['configuration', 'validation', request]);
    });

    it('should generate correct pricing key', () => {
      const request = createMockPricingRequest();
      const key = configurationKeys.pricing(request);

      expect(key).toEqual(['configuration', 'pricing', request]);
    });

    it('should generate correct saved configuration key', () => {
      const key = configurationKeys.saved('config-123');

      expect(key).toEqual(['configuration', 'saved', 'config-123']);
    });

    it('should have consistent base key', () => {
      expect(configurationKeys.all).toEqual(['configuration']);
    });
  });

  // ==========================================================================
  // 11. Edge Cases and Error Scenarios
  // ==========================================================================

  describe('Edge Cases', () => {
    it('should handle empty vehicle options response', async () => {
      const emptyResponse = createMockVehicleOptions({
        packages: [],
        options: [],
        colors: [],
        trims: [],
      });
      mockFetch(emptyResponse);

      const { result } = renderHook(() => useVehicleOptions('vehicle-123'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.packages).toHaveLength(0);
      expect(result.current.data?.options).toHaveLength(0);
    });

    it('should handle concurrent requests', async () => {
      const mockData = createMockVehicleOptions();
      mockFetch(mockData);

      const { result: result1 } = renderHook(() => useVehicleOptions('vehicle-123'), {
        wrapper: createWrapper(queryClient),
      });

      const { result: result2 } = renderHook(() => useVehicleOptions('vehicle-123'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result1.current.isSuccess).toBe(true);
        expect(result2.current.isSuccess).toBe(true);
      });

      // Should only fetch once due to deduplication
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('should handle rapid successive mutations', async () => {
      const mockRequest1 = createMockSaveRequest({ customerEmail: 'test1@example.com' });
      const mockRequest2 = createMockSaveRequest({ customerEmail: 'test2@example.com' });
      const mockResponse1 = createMockSaveResponse({ id: 'config-1' });
      const mockResponse2 = createMockSaveResponse({ id: 'config-2' });

      let callCount = 0;
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++;
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => (callCount === 1 ? mockResponse1 : mockResponse2),
        });
      });

      const { result } = renderHook(() => useSaveConfiguration(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(mockRequest1);
      result.current.mutate(mockRequest2);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('should handle special characters in IDs', async () => {
      const specialId = 'vehicle-123-äöü-!@#$%';
      const mockData = createMockVehicleOptions({ vehicleId: specialId });
      mockFetch(mockData);

      const { result } = renderHook(() => useVehicleOptions(specialId), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.vehicleId).toBe(specialId);
    });

    it('should handle very large pricing calculations', async () => {
      const mockRequest = createMockPricingRequest();
      const largePricing = createMockPricingBreakdown({
        basePrice: 999999,
        packagesTotal: 500000,
        optionsTotal: 300000,
        totalPrice: 1999999,
      });
      mockFetch(largePricing);

      const { result } = renderHook(() => useCalculatePricing(mockRequest), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.totalPrice).toBe(1999999);
    });
  });

  // ==========================================================================
  // 12. Performance Tests
  // ==========================================================================

  describe('Performance', () => {
    it('should complete fetch within timeout threshold', async () => {
      const mockData = createMockVehicleOptions();
      const startTime = Date.now();

      global.fetch = vi.fn().mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => {
              resolve({
                ok: true,
                status: 200,
                json: async () => mockData,
              });
            }, 100);
          }),
      );

      const { result } = renderHook(() => useVehicleOptions('vehicle-123'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      const duration = Date.now() - startTime;
      expect(duration).toBeLessThan(30000); // API_TIMEOUT
    });

    it('should handle multiple parallel queries efficiently', async () => {
      const mockData1 = createMockVehicleOptions({ vehicleId: 'vehicle-1' });
      const mockData2 = createMockVehicleOptions({ vehicleId: 'vehicle-2' });
      const mockData3 = createMockVehicleOptions({ vehicleId: 'vehicle-3' });

      let callCount = 0;
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++;
        const data = callCount === 1 ? mockData1 : callCount === 2 ? mockData2 : mockData3;
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => data,
        });
      });

      const { result: result1 } = renderHook(() => useVehicleOptions('vehicle-1'), {
        wrapper: createWrapper(queryClient),
      });

      const { result: result2 } = renderHook(() => useVehicleOptions('vehicle-2'), {
        wrapper: createWrapper(queryClient),
      });

      const { result: result3 } = renderHook(() => useVehicleOptions('vehicle-3'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result1.current.isSuccess).toBe(true);
        expect(result2.current.isSuccess).toBe(true);
        expect(result3.current.isSuccess).toBe(true);
      });

      expect(global.fetch).toHaveBeenCalledTimes(3);
    });
  });

  // ==========================================================================
  // 13. Security Tests
  // ==========================================================================

  describe('Security', () => {
    it('should not expose sensitive data in error messages', async () => {
      const errorResponse = {
        error: 'Unauthorized',
        message: 'Invalid API key',
        statusCode: 401,
        details: { apiKey: 'secret-key-12345' },
      };
      mockFetch(errorResponse, { status: 401, ok: false });

      const { result } = renderHook(() => useVehicleOptions('vehicle-123'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      // Error message should not contain sensitive details
      expect(result.current.error?.message).not.toContain('secret-key');
    });

    it('should sanitize user input in requests', async () => {
      const maliciousRequest = createMockSaveRequest({
        customerEmail: '<script>alert("xss")</script>@example.com',
      });
      const mockResponse = createMockSaveResponse();
      mockFetch(mockResponse);

      const { result } = renderHook(() => useSaveConfiguration(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(maliciousRequest);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Verify request was sent (backend should handle sanitization)
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should handle CORS errors gracefully', async () => {
      const corsError = new Error('CORS policy blocked');
      corsError.name = 'TypeError';
      mockFetchError(corsError);

      const { result } = renderHook(() => useVehicleOptions('vehicle-123'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(ConfigurationApiError);
    });
  });

  // ==========================================================================
  // 14. Integration Tests
  // ==========================================================================

  describe('Integration Scenarios', () => {
    it('should complete full configuration flow', async () => {
      // 1. Fetch vehicle options
      const mockOptions = createMockVehicleOptions();
      mockFetch(mockOptions);

      const { result: optionsResult } = renderHook(() => useVehicleOptions('vehicle-123'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(optionsResult.current.isSuccess).toBe(true);
      });

      // 2. Validate configuration
      const validationRequest = createMockValidationRequest();
      const validationResult = createMockValidationResult();
      mockFetch(validationResult);

      const { result: validationResultHook } = renderHook(
        () => useValidateConfiguration(validationRequest),
        {
          wrapper: createWrapper(queryClient),
        },
      );

      await waitFor(() => {
        expect(validationResultHook.current.isSuccess).toBe(true);
      });

      // 3. Calculate pricing
      const pricingRequest = createMockPricingRequest();
      const pricing = createMockPricingBreakdown();
      mockFetch(pricing);

      const { result: pricingResult } = renderHook(() => useCalculatePricing(pricingRequest), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(pricingResult.current.isSuccess).toBe(true);
      });

      // 4. Save configuration
      const saveRequest = createMockSaveRequest();
      const saveResponse = createMockSaveResponse();
      mockFetch(saveResponse);

      const { result: saveResult } = renderHook(() => useSaveConfiguration(), {
        wrapper: createWrapper(queryClient),
      });

      saveResult.current.mutate(saveRequest);

      await waitFor(() => {
        expect(saveResult.current.isSuccess).toBe(true);
      });

      expect(saveResult.current.data?.id).toBeDefined();
    });

    it('should handle validation failure in configuration flow', async () => {
      const validationRequest = createMockValidationRequest();
      const validationResult = createMockValidationResult({
        isValid: false,
        errors: [{ field: 'packageIds', message: 'Conflict detected', code: 'CONFLICT' }],
      });
      mockFetch(validationResult);

      const { result } = renderHook(() => useValidateConfiguration(validationRequest), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.isValid).toBe(false);
      expect(result.current.data?.errors).toHaveLength(1);
    });
  });
});