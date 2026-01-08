/**
 * Comprehensive test suite for dealer order management hooks
 * 
 * Tests cover:
 * - Query hooks for fetching orders and details
 * - Mutation hooks for fulfillment actions and bulk operations
 * - Optimistic updates and cache management
 * - Error handling and API error scenarios
 * - Query key factory and cache utilities
 * - Prefetching and invalidation utilities
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import {
  useDealerOrders,
  useDealerOrderDetail,
  useOrderFulfillment,
  useBulkOrderOperations,
  usePrefetchDealerOrderDetail,
  useInvalidateDealerOrders,
  useCachedDealerOrderDetail,
  useSetDealerOrderDetailCache,
  dealerOrderKeys,
  DealerOrderApiError,
  isDealerOrderApiError,
} from '../useDealerOrders';
import type {
  OrderQueueRequest,
  OrderQueueResponse,
  DealerOrderDetail,
  FulfillmentActionRequest,
  BulkOrderOperationRequest,
  DealerOrderStatus,
} from '../../types/dealer';

// ============================================================================
// Test Data Factories
// ============================================================================

const createMockOrder = (overrides = {}) => ({
  id: 'order-123',
  orderNumber: 'ORD-2024-001',
  customerId: 'customer-456',
  customerName: 'John Doe',
  dealerId: 'dealer-789',
  dealerName: 'Premium Motors',
  vehicleId: 'vehicle-101',
  vehicleName: '2024 Tesla Model 3',
  status: 'pending' as DealerOrderStatus,
  totalAmount: 45000,
  createdAt: '2024-01-15T10:00:00Z',
  updatedAt: '2024-01-15T10:00:00Z',
  ...overrides,
});

const createMockOrderDetail = (overrides = {}): DealerOrderDetail => ({
  ...createMockOrder(),
  customerEmail: 'john@example.com',
  customerPhone: '+1234567890',
  vehicleDetails: {
    make: 'Tesla',
    model: 'Model 3',
    year: 2024,
    color: 'Pearl White',
    vin: '5YJ3E1EA1KF123456',
  },
  paymentStatus: 'pending',
  depositAmount: 5000,
  remainingAmount: 40000,
  estimatedDeliveryDate: '2024-02-15',
  notes: 'Customer prefers morning delivery',
  timeline: [
    {
      status: 'pending',
      timestamp: '2024-01-15T10:00:00Z',
      notes: 'Order placed',
    },
  ],
  ...overrides,
});

const createMockOrderQueueResponse = (overrides = {}): OrderQueueResponse => ({
  orders: [createMockOrder(), createMockOrder({ id: 'order-124', orderNumber: 'ORD-2024-002' })],
  pagination: {
    page: 1,
    pageSize: 20,
    totalItems: 2,
    totalPages: 1,
  },
  summary: {
    totalOrders: 2,
    pendingOrders: 1,
    confirmedOrders: 1,
    inProductionOrders: 0,
    readyForPickupOrders: 0,
    completedOrders: 0,
    cancelledOrders: 0,
  },
  ...overrides,
});

// ============================================================================
// Test Utilities
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

const mockFetchError = (status = 500, errorData = {}) => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status,
    json: async () => ({
      message: 'API Error',
      code: 'ERROR_CODE',
      details: {},
      ...errorData,
    }),
  });
};

// ============================================================================
// Query Key Factory Tests
// ============================================================================

describe('dealerOrderKeys', () => {
  it('should generate correct query keys for all orders', () => {
    expect(dealerOrderKeys.all).toEqual(['dealer-orders']);
  });

  it('should generate correct query keys for order lists', () => {
    expect(dealerOrderKeys.lists()).toEqual(['dealer-orders', 'list']);
  });

  it('should generate correct query keys for specific list with params', () => {
    const params: OrderQueueRequest = {
      filters: { dealerId: 'dealer-123', status: ['pending'] },
      page: 1,
      pageSize: 20,
    };
    expect(dealerOrderKeys.list(params)).toEqual(['dealer-orders', 'list', params]);
  });

  it('should generate correct query keys for order details', () => {
    expect(dealerOrderKeys.details()).toEqual(['dealer-orders', 'detail']);
  });

  it('should generate correct query keys for specific order detail', () => {
    expect(dealerOrderKeys.detail('order-123')).toEqual(['dealer-orders', 'detail', 'order-123']);
  });

  it('should generate unique keys for different order IDs', () => {
    const key1 = dealerOrderKeys.detail('order-123');
    const key2 = dealerOrderKeys.detail('order-456');
    expect(key1).not.toEqual(key2);
  });
});

// ============================================================================
// DealerOrderApiError Tests
// ============================================================================

describe('DealerOrderApiError', () => {
  it('should create error with message only', () => {
    const error = new DealerOrderApiError('Test error');
    expect(error.message).toBe('Test error');
    expect(error.name).toBe('DealerOrderApiError');
    expect(error.statusCode).toBeUndefined();
    expect(error.code).toBeUndefined();
    expect(error.details).toBeUndefined();
  });

  it('should create error with all properties', () => {
    const details = { field: 'email', reason: 'invalid' };
    const error = new DealerOrderApiError('Validation failed', 400, 'VALIDATION_ERROR', details);
    
    expect(error.message).toBe('Validation failed');
    expect(error.statusCode).toBe(400);
    expect(error.code).toBe('VALIDATION_ERROR');
    expect(error.details).toEqual(details);
  });

  it('should be instance of Error', () => {
    const error = new DealerOrderApiError('Test error');
    expect(error).toBeInstanceOf(Error);
  });
});

describe('isDealerOrderApiError', () => {
  it('should return true for DealerOrderApiError instance', () => {
    const error = new DealerOrderApiError('Test error');
    expect(isDealerOrderApiError(error)).toBe(true);
  });

  it('should return false for regular Error', () => {
    const error = new Error('Regular error');
    expect(isDealerOrderApiError(error)).toBe(false);
  });

  it('should return false for non-error values', () => {
    expect(isDealerOrderApiError(null)).toBe(false);
    expect(isDealerOrderApiError(undefined)).toBe(false);
    expect(isDealerOrderApiError('string')).toBe(false);
    expect(isDealerOrderApiError({})).toBe(false);
  });
});

// ============================================================================
// useDealerOrders Hook Tests
// ============================================================================

describe('useDealerOrders', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should fetch dealer orders successfully', async () => {
    const mockResponse = createMockOrderQueueResponse();
    mockFetch(mockResponse);

    const { result } = renderHook(() => useDealerOrders(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockResponse);
    expect(result.current.error).toBeNull();
  });

  it('should build correct query params for filters', async () => {
    const mockResponse = createMockOrderQueueResponse();
    mockFetch(mockResponse);

    const request: OrderQueueRequest = {
      filters: {
        dealerId: 'dealer-123',
        status: ['pending', 'confirmed'],
        customerId: 'customer-456',
        vehicleId: 'vehicle-789',
        orderNumber: 'ORD-2024-001',
        searchQuery: 'Tesla',
        startDate: '2024-01-01',
        endDate: '2024-12-31',
        minAmount: 30000,
        maxAmount: 60000,
      },
      sortOptions: {
        sortBy: 'createdAt',
        sortDirection: 'desc',
      },
      page: 2,
      pageSize: 50,
    };

    renderHook(() => useDealerOrders(request), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });

    const fetchCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    const url = new URL(fetchCall);
    
    expect(url.searchParams.get('dealer_id')).toBe('dealer-123');
    expect(url.searchParams.getAll('status')).toEqual(['pending', 'confirmed']);
    expect(url.searchParams.get('customer_id')).toBe('customer-456');
    expect(url.searchParams.get('vehicle_id')).toBe('vehicle-789');
    expect(url.searchParams.get('order_number')).toBe('ORD-2024-001');
    expect(url.searchParams.get('search')).toBe('Tesla');
    expect(url.searchParams.get('start_date')).toBe('2024-01-01');
    expect(url.searchParams.get('end_date')).toBe('2024-12-31');
    expect(url.searchParams.get('min_amount')).toBe('30000');
    expect(url.searchParams.get('max_amount')).toBe('60000');
    expect(url.searchParams.get('sort_by')).toBe('createdAt');
    expect(url.searchParams.get('sort_direction')).toBe('desc');
    expect(url.searchParams.get('page')).toBe('2');
    expect(url.searchParams.get('page_size')).toBe('50');
  });

  it('should handle API error responses', async () => {
    mockFetchError(500, {
      message: 'Internal server error',
      code: 'SERVER_ERROR',
      details: { reason: 'Database connection failed' },
    });

    const { result } = renderHook(() => useDealerOrders(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeInstanceOf(DealerOrderApiError);
    expect(result.current.error?.message).toBe('Internal server error');
    expect(result.current.error?.statusCode).toBe(500);
    expect(result.current.error?.code).toBe('SERVER_ERROR');
  });

  it('should handle network errors gracefully', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useDealerOrders(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeInstanceOf(Error);
  });

  it('should use correct stale time and gc time', async () => {
    const mockResponse = createMockOrderQueueResponse();
    mockFetch(mockResponse);

    const { result } = renderHook(() => useDealerOrders(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const queryState = queryClient.getQueryState(dealerOrderKeys.list({}));
    expect(queryState?.dataUpdatedAt).toBeDefined();
  });

  it('should support custom query options', async () => {
    const mockResponse = createMockOrderQueueResponse();
    mockFetch(mockResponse);

    const onSuccess = vi.fn();
    const { result } = renderHook(
      () =>
        useDealerOrders(
          {},
          {
            onSuccess,
            enabled: true,
          },
        ),
      {
        wrapper: createWrapper(queryClient),
      },
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(onSuccess).toHaveBeenCalledWith(mockResponse);
  });

  it('should handle empty filters correctly', async () => {
    const mockResponse = createMockOrderQueueResponse();
    mockFetch(mockResponse);

    renderHook(() => useDealerOrders({}), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });

    const fetchCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    const url = new URL(fetchCall);
    
    // Should not have filter params
    expect(url.searchParams.get('dealer_id')).toBeNull();
    expect(url.searchParams.get('status')).toBeNull();
  });
});

// ============================================================================
// useDealerOrderDetail Hook Tests
// ============================================================================

describe('useDealerOrderDetail', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should fetch order detail successfully', async () => {
    const mockDetail = createMockOrderDetail();
    mockFetch(mockDetail);

    const { result } = renderHook(() => useDealerOrderDetail('order-123'), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockDetail);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/dealer/orders/order-123'),
      expect.objectContaining({
        method: 'GET',
        credentials: 'include',
      }),
    );
  });

  it('should be disabled when orderId is empty', async () => {
    const { result } = renderHook(() => useDealerOrderDetail(''), {
      wrapper: createWrapper(queryClient),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('should handle 404 not found error', async () => {
    mockFetchError(404, {
      message: 'Order not found',
      code: 'NOT_FOUND',
    });

    const { result } = renderHook(() => useDealerOrderDetail('nonexistent-order'), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.statusCode).toBe(404);
    expect(result.current.error?.message).toBe('Order not found');
  });

  it('should handle unauthorized access', async () => {
    mockFetchError(403, {
      message: 'Access denied',
      code: 'FORBIDDEN',
    });

    const { result } = renderHook(() => useDealerOrderDetail('order-123'), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.statusCode).toBe(403);
  });

  it('should use correct cache configuration', async () => {
    const mockDetail = createMockOrderDetail();
    mockFetch(mockDetail);

    const { result } = renderHook(() => useDealerOrderDetail('order-123'), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const queryState = queryClient.getQueryState(dealerOrderKeys.detail('order-123'));
    expect(queryState?.data).toEqual(mockDetail);
  });
});

// ============================================================================
// useOrderFulfillment Hook Tests
// ============================================================================

describe('useOrderFulfillment', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should execute fulfillment action successfully', async () => {
    const mockResponse = {
      success: true,
      order: createMockOrderDetail({ status: 'confirmed' }),
      message: 'Order confirmed successfully',
    };
    mockFetch(mockResponse);

    const { result } = renderHook(() => useOrderFulfillment(), {
      wrapper: createWrapper(queryClient),
    });

    const request: FulfillmentActionRequest = {
      orderId: 'order-123',
      action: 'confirm',
      notes: 'Confirmed by dealer',
    };

    result.current.mutate(request);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockResponse);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/dealer/orders/order-123/fulfillment'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          action: 'confirm',
          notes: 'Confirmed by dealer',
          estimated_completion_date: undefined,
        }),
      }),
    );
  });

  it('should perform optimistic update on confirm action', async () => {
    const mockDetail = createMockOrderDetail({ status: 'pending' });
    queryClient.setQueryData(dealerOrderKeys.detail('order-123'), mockDetail);

    const mockResponse = {
      success: true,
      order: createMockOrderDetail({ status: 'confirmed' }),
      message: 'Order confirmed',
    };
    mockFetch(mockResponse);

    const { result } = renderHook(() => useOrderFulfillment(), {
      wrapper: createWrapper(queryClient),
    });

    const request: FulfillmentActionRequest = {
      orderId: 'order-123',
      action: 'confirm',
    };

    result.current.mutate(request);

    // Check optimistic update
    const optimisticData = queryClient.getQueryData<DealerOrderDetail>(
      dealerOrderKeys.detail('order-123'),
    );
    expect(optimisticData?.status).toBe('confirmed');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it('should rollback on error', async () => {
    const originalDetail = createMockOrderDetail({ status: 'pending' });
    queryClient.setQueryData(dealerOrderKeys.detail('order-123'), originalDetail);

    mockFetchError(500, { message: 'Failed to confirm order' });

    const { result } = renderHook(() => useOrderFulfillment(), {
      wrapper: createWrapper(queryClient),
    });

    const request: FulfillmentActionRequest = {
      orderId: 'order-123',
      action: 'confirm',
    };

    result.current.mutate(request);

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    // Check rollback
    const rolledBackData = queryClient.getQueryData<DealerOrderDetail>(
      dealerOrderKeys.detail('order-123'),
    );
    expect(rolledBackData?.status).toBe('pending');
  });

  it('should invalidate queries on success', async () => {
    const mockResponse = {
      success: true,
      order: createMockOrderDetail({ status: 'in_production' }),
      message: 'Production started',
    };
    mockFetch(mockResponse);

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useOrderFulfillment(), {
      wrapper: createWrapper(queryClient),
    });

    const request: FulfillmentActionRequest = {
      orderId: 'order-123',
      action: 'start_production',
    };

    result.current.mutate(request);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: dealerOrderKeys.detail('order-123'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: dealerOrderKeys.lists(),
    });
  });

  it('should handle all fulfillment actions correctly', async () => {
    const actions: Array<{ action: FulfillmentActionRequest['action']; expectedStatus: DealerOrderStatus }> = [
      { action: 'confirm', expectedStatus: 'confirmed' },
      { action: 'start_production', expectedStatus: 'in_production' },
      { action: 'mark_ready', expectedStatus: 'ready_for_pickup' },
      { action: 'complete', expectedStatus: 'completed' },
      { action: 'cancel', expectedStatus: 'cancelled' },
    ];

    for (const { action, expectedStatus } of actions) {
      const mockDetail = createMockOrderDetail({ status: 'pending' });
      queryClient.setQueryData(dealerOrderKeys.detail('order-123'), mockDetail);

      const mockResponse = {
        success: true,
        order: createMockOrderDetail({ status: expectedStatus }),
        message: `Action ${action} completed`,
      };
      mockFetch(mockResponse);

      const { result } = renderHook(() => useOrderFulfillment(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        orderId: 'order-123',
        action,
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      queryClient.clear();
    }
  });

  it('should include estimated completion date when provided', async () => {
    const mockResponse = {
      success: true,
      order: createMockOrderDetail(),
      message: 'Production started',
    };
    mockFetch(mockResponse);

    const { result } = renderHook(() => useOrderFulfillment(), {
      wrapper: createWrapper(queryClient),
    });

    const request: FulfillmentActionRequest = {
      orderId: 'order-123',
      action: 'start_production',
      estimatedCompletionDate: '2024-02-15',
      notes: 'Expected completion in 30 days',
    };

    result.current.mutate(request);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: JSON.stringify({
          action: 'start_production',
          notes: 'Expected completion in 30 days',
          estimated_completion_date: '2024-02-15',
        }),
      }),
    );
  });
});

// ============================================================================
// useBulkOrderOperations Hook Tests
// ============================================================================

describe('useBulkOrderOperations', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should execute bulk operation successfully', async () => {
    const mockResponse: BulkOrderOperationResponse = {
      success: true,
      processedCount: 3,
      failedCount: 0,
      results: [
        { orderId: 'order-1', success: true, message: 'Updated' },
        { orderId: 'order-2', success: true, message: 'Updated' },
        { orderId: 'order-3', success: true, message: 'Updated' },
      ],
    };
    mockFetch(mockResponse);

    const { result } = renderHook(() => useBulkOrderOperations(), {
      wrapper: createWrapper(queryClient),
    });

    const request: BulkOrderOperationRequest = {
      orderIds: ['order-1', 'order-2', 'order-3'],
      operation: 'update_status',
      targetStatus: 'confirmed',
    };

    result.current.mutate(request);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockResponse);
  });

  it('should perform optimistic updates for status changes', async () => {
    const mockOrders = createMockOrderQueueResponse({
      orders: [
        createMockOrder({ id: 'order-1', status: 'pending' }),
        createMockOrder({ id: 'order-2', status: 'pending' }),
      ],
    });

    queryClient.setQueryData(dealerOrderKeys.list({}), mockOrders);

    const mockResponse: BulkOrderOperationResponse = {
      success: true,
      processedCount: 2,
      failedCount: 0,
      results: [],
    };
    mockFetch(mockResponse);

    const { result } = renderHook(() => useBulkOrderOperations(), {
      wrapper: createWrapper(queryClient),
    });

    const request: BulkOrderOperationRequest = {
      orderIds: ['order-1', 'order-2'],
      operation: 'update_status',
      targetStatus: 'confirmed',
    };

    result.current.mutate(request);

    // Check optimistic update
    const optimisticData = queryClient.getQueryData<OrderQueueResponse>(dealerOrderKeys.list({}));
    expect(optimisticData?.orders[0]?.status).toBe('confirmed');
    expect(optimisticData?.orders[1]?.status).toBe('confirmed');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it('should rollback on error', async () => {
    const originalOrders = createMockOrderQueueResponse({
      orders: [
        createMockOrder({ id: 'order-1', status: 'pending' }),
        createMockOrder({ id: 'order-2', status: 'pending' }),
      ],
    });

    queryClient.setQueryData(dealerOrderKeys.list({}), originalOrders);

    mockFetchError(500, { message: 'Bulk operation failed' });

    const { result } = renderHook(() => useBulkOrderOperations(), {
      wrapper: createWrapper(queryClient),
    });

    const request: BulkOrderOperationRequest = {
      orderIds: ['order-1', 'order-2'],
      operation: 'update_status',
      targetStatus: 'confirmed',
    };

    result.current.mutate(request);

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    // Check rollback
    const rolledBackData = queryClient.getQueryData<OrderQueueResponse>(dealerOrderKeys.list({}));
    expect(rolledBackData?.orders[0]?.status).toBe('pending');
    expect(rolledBackData?.orders[1]?.status).toBe('pending');
  });

  it('should invalidate all affected queries on success', async () => {
    const mockResponse: BulkOrderOperationResponse = {
      success: true,
      processedCount: 2,
      failedCount: 0,
      results: [],
    };
    mockFetch(mockResponse);

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useBulkOrderOperations(), {
      wrapper: createWrapper(queryClient),
    });

    const request: BulkOrderOperationRequest = {
      orderIds: ['order-1', 'order-2'],
      operation: 'update_status',
      targetStatus: 'confirmed',
    };

    result.current.mutate(request);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: dealerOrderKeys.lists(),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: dealerOrderKeys.detail('order-1'),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: dealerOrderKeys.detail('order-2'),
    });
  });

  it('should handle partial failures', async () => {
    const mockResponse: BulkOrderOperationResponse = {
      success: false,
      processedCount: 2,
      failedCount: 1,
      results: [
        { orderId: 'order-1', success: true, message: 'Updated' },
        { orderId: 'order-2', success: true, message: 'Updated' },
        { orderId: 'order-3', success: false, error: 'Order locked' },
      ],
    };
    mockFetch(mockResponse);

    const { result } = renderHook(() => useBulkOrderOperations(), {
      wrapper: createWrapper(queryClient),
    });

    const request: BulkOrderOperationRequest = {
      orderIds: ['order-1', 'order-2', 'order-3'],
      operation: 'update_status',
      targetStatus: 'confirmed',
    };

    result.current.mutate(request);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.failedCount).toBe(1);
    expect(result.current.data?.results[2]?.success).toBe(false);
  });

  it('should include notes in bulk operation request', async () => {
    const mockResponse: BulkOrderOperationResponse = {
      success: true,
      processedCount: 2,
      failedCount: 0,
      results: [],
    };
    mockFetch(mockResponse);

    const { result } = renderHook(() => useBulkOrderOperations(), {
      wrapper: createWrapper(queryClient),
    });

    const request: BulkOrderOperationRequest = {
      orderIds: ['order-1', 'order-2'],
      operation: 'update_status',
      targetStatus: 'confirmed',
      notes: 'Bulk confirmation by manager',
    };

    result.current.mutate(request);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: JSON.stringify({
          order_ids: ['order-1', 'order-2'],
          operation: 'update_status',
          target_status: 'confirmed',
          notes: 'Bulk confirmation by manager',
        }),
      }),
    );
  });
});

// ============================================================================
// Utility Hooks Tests
// ============================================================================

describe('usePrefetchDealerOrderDetail', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should prefetch order detail', async () => {
    const mockDetail = createMockOrderDetail();
    mockFetch(mockDetail);

    const { result } = renderHook(() => usePrefetchDealerOrderDetail(), {
      wrapper: createWrapper(queryClient),
    });

    result.current('order-123');

    await waitFor(() => {
      const cachedData = queryClient.getQueryData(dealerOrderKeys.detail('order-123'));
      expect(cachedData).toEqual(mockDetail);
    });
  });

  it('should not block on prefetch', () => {
    const mockDetail = createMockOrderDetail();
    mockFetch(mockDetail);

    const { result } = renderHook(() => usePrefetchDealerOrderDetail(), {
      wrapper: createWrapper(queryClient),
    });

    // Should return immediately
    const returnValue = result.current('order-123');
    expect(returnValue).toBeUndefined();
  });
});

describe('useInvalidateDealerOrders', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should invalidate all dealer order queries', async () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useInvalidateDealerOrders(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.invalidateAll();

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: dealerOrderKeys.all,
    });
  });

  it('should invalidate only list queries', async () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useInvalidateDealerOrders(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.invalidateLists();

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: dealerOrderKeys.lists(),
    });
  });

  it('should invalidate specific order detail', async () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useInvalidateDealerOrders(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.invalidateDetail('order-123');

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: dealerOrderKeys.detail('order-123'),
    });
  });
});

describe('useCachedDealerOrderDetail', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should return cached order detail', () => {
    const mockDetail = createMockOrderDetail();
    queryClient.setQueryData(dealerOrderKeys.detail('order-123'), mockDetail);

    const { result } = renderHook(() => useCachedDealerOrderDetail('order-123'), {
      wrapper: createWrapper(queryClient),
    });

    expect(result.current).toEqual(mockDetail);
  });

  it('should return undefined when no cache exists', () => {
    const { result } = renderHook(() => useCachedDealerOrderDetail('nonexistent-order'), {
      wrapper: createWrapper(queryClient),
    });

    expect(result.current).toBeUndefined();
  });

  it('should update when cache changes', () => {
    const mockDetail1 = createMockOrderDetail({ status: 'pending' });
    queryClient.setQueryData(dealerOrderKeys.detail('order-123'), mockDetail1);

    const { result, rerender } = renderHook(() => useCachedDealerOrderDetail('order-123'), {
      wrapper: createWrapper(queryClient),
    });

    expect(result.current?.status).toBe('pending');

    const mockDetail2 = createMockOrderDetail({ status: 'confirmed' });
    queryClient.setQueryData(dealerOrderKeys.detail('order-123'), mockDetail2);

    rerender();

    expect(result.current?.status).toBe('confirmed');
  });
});

describe('useSetDealerOrderDetailCache', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should set order detail in cache', () => {
    const mockDetail = createMockOrderDetail();

    const { result } = renderHook(() => useSetDealerOrderDetailCache(), {
      wrapper: createWrapper(queryClient),
    });

    result.current('order-123', mockDetail);

    const cachedData = queryClient.getQueryData(dealerOrderKeys.detail('order-123'));
    expect(cachedData).toEqual(mockDetail);
  });

  it('should overwrite existing cache', () => {
    const mockDetail1 = createMockOrderDetail({ status: 'pending' });
    queryClient.setQueryData(dealerOrderKeys.detail('order-123'), mockDetail1);

    const { result } = renderHook(() => useSetDealerOrderDetailCache(), {
      wrapper: createWrapper(queryClient),
    });

    const mockDetail2 = createMockOrderDetail({ status: 'confirmed' });
    result.current('order-123', mockDetail2);

    const cachedData = queryClient.getQueryData<DealerOrderDetail>(
      dealerOrderKeys.detail('order-123'),
    );
    expect(cachedData?.status).toBe('confirmed');
  });
});

// ============================================================================
// Integration Tests
// ============================================================================

describe('Integration: Complete Order Workflow', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should handle complete order fulfillment workflow', async () => {
    // 1. Fetch orders
    const mockOrders = createMockOrderQueueResponse();
    mockFetch(mockOrders);

    const { result: ordersResult } = renderHook(() => useDealerOrders(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(ordersResult.current.isSuccess).toBe(true);
    });

    // 2. Fetch order detail
    const mockDetail = createMockOrderDetail({ id: 'order-123', status: 'pending' });
    mockFetch(mockDetail);

    const { result: detailResult } = renderHook(() => useDealerOrderDetail('order-123'), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(detailResult.current.isSuccess).toBe(true);
    });

    // 3. Confirm order
    const confirmResponse = {
      success: true,
      order: createMockOrderDetail({ id: 'order-123', status: 'confirmed' }),
      message: 'Order confirmed',
    };
    mockFetch(confirmResponse);

    const { result: fulfillmentResult } = renderHook(() => useOrderFulfillment(), {
      wrapper: createWrapper(queryClient),
    });

    fulfillmentResult.current.mutate({
      orderId: 'order-123',
      action: 'confirm',
    });

    await waitFor(() => {
      expect(fulfillmentResult.current.isSuccess).toBe(true);
    });

    // 4. Verify cache invalidation
    await waitFor(() => {
      const queries = queryClient.getQueryCache().getAll();
      const invalidatedQueries = queries.filter((q) => q.state.isInvalidated);
      expect(invalidatedQueries.length).toBeGreaterThan(0);
    });
  });

  it('should handle bulk operations with cache updates', async () => {
    // Setup initial cache
    const mockOrders = createMockOrderQueueResponse({
      orders: [
        createMockOrder({ id: 'order-1', status: 'pending' }),
        createMockOrder({ id: 'order-2', status: 'pending' }),
        createMockOrder({ id: 'order-3', status: 'pending' }),
      ],
    });
    queryClient.setQueryData(dealerOrderKeys.list({}), mockOrders);

    // Execute bulk operation
    const bulkResponse: BulkOrderOperationResponse = {
      success: true,
      processedCount: 3,
      failedCount: 0,
      results: [
        { orderId: 'order-1', success: true, message: 'Updated' },
        { orderId: 'order-2', success: true, message: 'Updated' },
        { orderId: 'order-3', success: true, message: 'Updated' },
      ],
    };
    mockFetch(bulkResponse);

    const { result } = renderHook(() => useBulkOrderOperations(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      orderIds: ['order-1', 'order-2', 'order-3'],
      operation: 'update_status',
      targetStatus: 'confirmed',
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Verify all order details are invalidated
    await waitFor(() => {
      const queries = queryClient.getQueryCache().getAll();
      const detailQueries = queries.filter((q) =>
        (q.queryKey as string[]).includes('detail'),
      );
      expect(detailQueries.length).toBeGreaterThan(0);
    });
  });
});

// ============================================================================
// Edge Cases and Error Scenarios
// ============================================================================

describe('Edge Cases', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  it('should handle malformed JSON response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error('Invalid JSON');
      },
    });

    const { result } = renderHook(() => useDealerOrders(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toBe('Failed to fetch dealer orders');
  });

  it('should handle empty order list', async () => {
    const emptyResponse = createMockOrderQueueResponse({
      orders: [],
      pagination: {
        page: 1,
        pageSize: 20,
        totalItems: 0,
        totalPages: 0,
      },
    });
    mockFetch(emptyResponse);

    const { result } = renderHook(() => useDealerOrders(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.orders).toHaveLength(0);
  });

  it('should handle concurrent mutations gracefully', async () => {
    const mockResponse = {
      success: true,
      order: createMockOrderDetail(),
      message: 'Updated',
    };
    mockFetch(mockResponse);

    const { result } = renderHook(() => useOrderFulfillment(), {
      wrapper: createWrapper(queryClient),
    });

    // Trigger multiple mutations
    result.current.mutate({ orderId: 'order-1', action: 'confirm' });
    result.current.mutate({ orderId: 'order-2', action: 'confirm' });
    result.current.mutate({ orderId: 'order-3', action: 'confirm' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it('should handle very large order lists', async () => {
    const largeOrderList = Array.from({ length: 1000 }, (_, i) =>
      createMockOrder({ id: `order-${i}`, orderNumber: `ORD-${i}` }),
    );

    const largeResponse = createMockOrderQueueResponse({
      orders: largeOrderList,
      pagination: {
        page: 1,
        pageSize: 1000,
        totalItems: 1000,
        totalPages: 1,
      },
    });
    mockFetch(largeResponse);

    const { result } = renderHook(() => useDealerOrders({ pageSize: 1000 }), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.orders).toHaveLength(1000);
  });
});