import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import {
  useOrders,
  useOrder,
  useOrderWithHistory,
  useOrderHistory,
  useOrderTimeline,
  useDeliveryEstimate,
  useOrderRealtime,
  usePrefetchOrder,
  useInvalidateOrders,
  useOptimisticOrderUpdate,
  useOrderBackgroundRefresh,
  orderKeys,
  OrderApiError,
  isOrderApiError,
} from '../../hooks/useOrders';
import type {
  Order,
  OrderWithHistory,
  OrderListResponse,
  OrderStatusHistory,
  OrderTimeline,
  DeliveryEstimate,
  OrderWebSocketMessage,
} from '../../types/orders';

// Mock useWebSocket hook
vi.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({
    isConnected: true,
    connect: vi.fn(),
    disconnect: vi.fn(),
    send: vi.fn(),
  })),
}));

// Mock environment variables
vi.stubEnv('VITE_API_URL', 'http://localhost:8000');

// Test data factories
const createMockOrder = (overrides: Partial<Order> = {}): Order => ({
  id: 'order-123',
  userId: 'user-456',
  status: 'pending',
  paymentStatus: 'pending',
  fulfillmentStatus: 'pending',
  totalAmount: 50000,
  currency: 'USD',
  items: [],
  shippingAddress: {
    street: '123 Main St',
    city: 'New York',
    state: 'NY',
    zipCode: '10001',
    country: 'USA',
  },
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
  ...overrides,
});

const createMockOrderListResponse = (
  overrides: Partial<OrderListResponse> = {},
): OrderListResponse => ({
  orders: [createMockOrder(), createMockOrder({ id: 'order-456' })],
  total: 2,
  page: 1,
  pageSize: 20,
  totalPages: 1,
  ...overrides,
});

const createMockOrderWithHistory = (
  overrides: Partial<OrderWithHistory> = {},
): OrderWithHistory => ({
  ...createMockOrder(),
  statusHistory: [
    {
      id: 'history-1',
      orderId: 'order-123',
      status: 'pending',
      changedAt: '2024-01-01T00:00:00Z',
      changedBy: 'system',
      notes: 'Order created',
    },
  ],
  ...overrides,
});

const createMockOrderHistory = (): readonly OrderStatusHistory[] => [
  {
    id: 'history-1',
    orderId: 'order-123',
    status: 'pending',
    changedAt: '2024-01-01T00:00:00Z',
    changedBy: 'system',
    notes: 'Order created',
  },
  {
    id: 'history-2',
    orderId: 'order-123',
    status: 'confirmed',
    changedAt: '2024-01-01T01:00:00Z',
    changedBy: 'admin-1',
    notes: 'Order confirmed',
  },
];

const createMockOrderTimeline = (): OrderTimeline => ({
  orderId: 'order-123',
  events: [
    {
      id: 'event-1',
      type: 'order_created',
      timestamp: '2024-01-01T00:00:00Z',
      description: 'Order created',
      metadata: {},
    },
    {
      id: 'event-2',
      type: 'payment_received',
      timestamp: '2024-01-01T00:30:00Z',
      description: 'Payment received',
      metadata: { amount: 50000 },
    },
  ],
  estimatedDelivery: '2024-01-10T00:00:00Z',
});

const createMockDeliveryEstimate = (): DeliveryEstimate => ({
  orderId: 'order-123',
  estimatedDeliveryDate: '2024-01-10T00:00:00Z',
  earliestDeliveryDate: '2024-01-08T00:00:00Z',
  latestDeliveryDate: '2024-01-12T00:00:00Z',
  confidence: 'high',
  trackingNumber: 'TRACK123456',
  carrier: 'FedEx',
  lastUpdated: '2024-01-01T00:00:00Z',
});

// Test wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

// Global fetch mock
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('useOrders Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  describe('🎯 Query Key Generation', () => {
    it('should generate correct query keys for all operations', () => {
      expect(orderKeys.all).toEqual(['orders']);
      expect(orderKeys.lists()).toEqual(['orders', 'list']);
      expect(orderKeys.list({ userId: 'user-1' })).toEqual([
        'orders',
        'list',
        { userId: 'user-1' },
      ]);
      expect(orderKeys.details()).toEqual(['orders', 'detail']);
      expect(orderKeys.detail('order-123')).toEqual(['orders', 'detail', 'order-123']);
      expect(orderKeys.history('order-123')).toEqual(['orders', 'history', 'order-123']);
      expect(orderKeys.timeline('order-123')).toEqual(['orders', 'timeline', 'order-123']);
      expect(orderKeys.deliveryEstimate('order-123')).toEqual([
        'orders',
        'delivery',
        'order-123',
      ]);
    });
  });

  describe('🛡️ OrderApiError', () => {
    it('should create error with all properties', () => {
      const error = new OrderApiError('Test error', 404, 'NOT_FOUND', { detail: 'test' });

      expect(error.message).toBe('Test error');
      expect(error.statusCode).toBe(404);
      expect(error.code).toBe('NOT_FOUND');
      expect(error.details).toEqual({ detail: 'test' });
      expect(error.name).toBe('OrderApiError');
    });

    it('should work with isOrderApiError type guard', () => {
      const error = new OrderApiError('Test error');
      const regularError = new Error('Regular error');

      expect(isOrderApiError(error)).toBe(true);
      expect(isOrderApiError(regularError)).toBe(false);
      expect(isOrderApiError(null)).toBe(false);
      expect(isOrderApiError(undefined)).toBe(false);
      expect(isOrderApiError('string')).toBe(false);
    });
  });

  describe('🧪 useOrders - List Orders', () => {
    it('should fetch orders successfully', async () => {
      const mockResponse = createMockOrderListResponse();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const { result } = renderHook(() => useOrders(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/orders?',
        expect.objectContaining({
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
        }),
      );
    });

    it('should build query params correctly', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => createMockOrderListResponse(),
      });

      const request = {
        userId: 'user-123',
        status: 'confirmed' as const,
        paymentStatus: 'paid' as const,
        fulfillmentStatus: 'shipped' as const,
        startDate: '2024-01-01',
        endDate: '2024-01-31',
        page: 2,
        pageSize: 10,
        sortBy: 'createdAt' as const,
        sortDirection: 'desc' as const,
      };

      renderHook(() => useOrders(request), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const callUrl = mockFetch.mock.calls[0][0] as string;
      expect(callUrl).toContain('user_id=user-123');
      expect(callUrl).toContain('status=confirmed');
      expect(callUrl).toContain('payment_status=paid');
      expect(callUrl).toContain('fulfillment_status=shipped');
      expect(callUrl).toContain('start_date=2024-01-01');
      expect(callUrl).toContain('end_date=2024-01-31');
      expect(callUrl).toContain('page=2');
      expect(callUrl).toContain('page_size=10');
      expect(callUrl).toContain('sort_by=createdAt');
      expect(callUrl).toContain('sort_direction=desc');
    });

    it('should handle API error responses', async () => {
      const errorResponse = {
        message: 'Unauthorized',
        code: 'UNAUTHORIZED',
        details: { reason: 'Invalid token' },
      };

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => errorResponse,
      });

      const { result } = renderHook(() => useOrders(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(OrderApiError);
      expect(result.current.error?.message).toBe('Unauthorized');
      expect(result.current.error?.statusCode).toBe(401);
      expect(result.current.error?.code).toBe('UNAUTHORIZED');
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useOrders(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(Error);
    });

    it('should handle malformed error responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      });

      const { result } = renderHook(() => useOrders(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error?.message).toBe('Failed to fetch orders');
    });

    it('should respect custom query options', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => createMockOrderListResponse(),
      });

      const { result } = renderHook(
        () =>
          useOrders(
            {},
            {
              enabled: false,
              staleTime: 10000,
            },
          ),
        {
          wrapper: createWrapper(),
        },
      );

      expect(result.current.isFetching).toBe(false);
      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe('🧪 useOrder - Single Order', () => {
    it('should fetch single order successfully', async () => {
      const mockOrder = createMockOrder();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockOrder,
      });

      const { result } = renderHook(() => useOrder('order-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockOrder);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/orders/order-123',
        expect.any(Object),
      );
    });

    it('should not fetch when orderId is empty', () => {
      const { result } = renderHook(() => useOrder(''), {
        wrapper: createWrapper(),
      });

      expect(result.current.isFetching).toBe(false);
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('should use placeholder data from list cache', async () => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, gcTime: 0 },
        },
      });

      const mockListResponse = createMockOrderListResponse();
      queryClient.setQueryData(orderKeys.list({}), mockListResponse);

      const wrapper = ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => createMockOrder(),
      });

      const { result } = renderHook(() => useOrder('order-123'), { wrapper });

      expect(result.current.data).toEqual(mockListResponse.orders[0]);
    });

    it('should handle 404 errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({
          message: 'Order not found',
          code: 'NOT_FOUND',
        }),
      });

      const { result } = renderHook(() => useOrder('nonexistent'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error?.statusCode).toBe(404);
      expect(result.current.error?.code).toBe('NOT_FOUND');
    });
  });

  describe('🧪 useOrderWithHistory', () => {
    it('should fetch order with complete history', async () => {
      const mockOrderWithHistory = createMockOrderWithHistory();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockOrderWithHistory,
      });

      const { result } = renderHook(() => useOrderWithHistory('order-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockOrderWithHistory);
      expect(result.current.data?.statusHistory).toHaveLength(1);
    });

    it('should handle empty history', async () => {
      const mockOrderWithHistory = createMockOrderWithHistory({
        statusHistory: [],
      });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockOrderWithHistory,
      });

      const { result } = renderHook(() => useOrderWithHistory('order-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.statusHistory).toEqual([]);
    });
  });

  describe('🧪 useOrderHistory', () => {
    it('should fetch order status history', async () => {
      const mockHistory = createMockOrderHistory();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockHistory,
      });

      const { result } = renderHook(() => useOrderHistory('order-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockHistory);
      expect(result.current.data).toHaveLength(2);
    });

    it('should handle empty history array', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      const { result } = renderHook(() => useOrderHistory('order-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual([]);
    });
  });

  describe('🧪 useOrderTimeline', () => {
    it('should fetch order timeline', async () => {
      const mockTimeline = createMockOrderTimeline();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTimeline,
      });

      const { result } = renderHook(() => useOrderTimeline('order-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockTimeline);
      expect(result.current.data?.events).toHaveLength(2);
    });

    it('should handle timeline with no events', async () => {
      const mockTimeline = createMockOrderTimeline();
      mockTimeline.events = [];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTimeline,
      });

      const { result } = renderHook(() => useOrderTimeline('order-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.events).toEqual([]);
    });
  });

  describe('🧪 useDeliveryEstimate', () => {
    it('should fetch delivery estimate', async () => {
      const mockEstimate = createMockDeliveryEstimate();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockEstimate,
      });

      const { result } = renderHook(() => useDeliveryEstimate('order-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockEstimate);
      expect(result.current.data?.confidence).toBe('high');
    });

    it('should handle missing tracking information', async () => {
      const mockEstimate = createMockDeliveryEstimate();
      delete (mockEstimate as Partial<DeliveryEstimate>).trackingNumber;
      delete (mockEstimate as Partial<DeliveryEstimate>).carrier;

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockEstimate,
      });

      const { result } = renderHook(() => useDeliveryEstimate('order-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.trackingNumber).toBeUndefined();
      expect(result.current.data?.carrier).toBeUndefined();
    });
  });

  describe('🔌 useOrderRealtime - WebSocket Integration', () => {
    it('should handle order status changed message', async () => {
      const onStatusChange = vi.fn();
      const mockMessage: OrderWebSocketMessage = {
        type: 'order_status_changed',
        orderId: 'order-123',
        timestamp: '2024-01-01T00:00:00Z',
        data: {
          oldStatus: 'pending',
          newStatus: 'confirmed',
        },
      };

      const { useWebSocket } = await import('../../hooks/useWebSocket');
      const mockWebSocket = vi.mocked(useWebSocket);

      mockWebSocket.mockImplementation((options) => {
        if (options.onMessage) {
          setTimeout(() => {
            options.onMessage(mockMessage);
          }, 0);
        }
        return {
          isConnected: true,
          connect: vi.fn(),
          disconnect: vi.fn(),
          send: vi.fn(),
        };
      });

      renderHook(() => useOrderRealtime('order-123', { onStatusChange }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(onStatusChange).toHaveBeenCalledWith(mockMessage);
      });
    });

    it('should handle delivery estimate updated message', async () => {
      const onDeliveryUpdate = vi.fn();
      const mockMessage: OrderWebSocketMessage = {
        type: 'delivery_estimate_updated',
        orderId: 'order-123',
        timestamp: '2024-01-01T00:00:00Z',
        data: createMockDeliveryEstimate(),
      };

      const { useWebSocket } = await import('../../hooks/useWebSocket');
      const mockWebSocket = vi.mocked(useWebSocket);

      mockWebSocket.mockImplementation((options) => {
        if (options.onMessage) {
          setTimeout(() => {
            options.onMessage(mockMessage);
          }, 0);
        }
        return {
          isConnected: true,
          connect: vi.fn(),
          disconnect: vi.fn(),
          send: vi.fn(),
        };
      });

      renderHook(() => useOrderRealtime('order-123', { onDeliveryUpdate }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(onDeliveryUpdate).toHaveBeenCalledWith(mockMessage);
      });
    });

    it('should handle timeline updated message', async () => {
      const onTimelineUpdate = vi.fn();
      const mockMessage: OrderWebSocketMessage = {
        type: 'timeline_updated',
        orderId: 'order-123',
        timestamp: '2024-01-01T00:00:00Z',
        data: createMockOrderTimeline(),
      };

      const { useWebSocket } = await import('../../hooks/useWebSocket');
      const mockWebSocket = vi.mocked(useWebSocket);

      mockWebSocket.mockImplementation((options) => {
        if (options.onMessage) {
          setTimeout(() => {
            options.onMessage(mockMessage);
          }, 0);
        }
        return {
          isConnected: true,
          connect: vi.fn(),
          disconnect: vi.fn(),
          send: vi.fn(),
        };
      });

      renderHook(() => useOrderRealtime('order-123', { onTimelineUpdate }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(onTimelineUpdate).toHaveBeenCalledWith(mockMessage);
      });
    });

    it('should ignore messages for different orders', async () => {
      const onStatusChange = vi.fn();
      const mockMessage: OrderWebSocketMessage = {
        type: 'order_status_changed',
        orderId: 'order-456',
        timestamp: '2024-01-01T00:00:00Z',
        data: {
          oldStatus: 'pending',
          newStatus: 'confirmed',
        },
      };

      const { useWebSocket } = await import('../../hooks/useWebSocket');
      const mockWebSocket = vi.mocked(useWebSocket);

      mockWebSocket.mockImplementation((options) => {
        if (options.onMessage) {
          setTimeout(() => {
            options.onMessage(mockMessage);
          }, 0);
        }
        return {
          isConnected: true,
          connect: vi.fn(),
          disconnect: vi.fn(),
          send: vi.fn(),
        };
      });

      renderHook(() => useOrderRealtime('order-123', { onStatusChange }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(onStatusChange).not.toHaveBeenCalled();
      });
    });

    it('should not connect when disabled', () => {
      const { useWebSocket } = vi.mocked(
        require('../../hooks/useWebSocket') as { useWebSocket: ReturnType<typeof vi.fn> },
      );

      renderHook(() => useOrderRealtime('order-123', { enabled: false }), {
        wrapper: createWrapper(),
      });

      expect(useWebSocket).toHaveBeenCalledWith(
        expect.objectContaining({
          enabled: false,
        }),
      );
    });
  });

  describe('🔄 usePrefetchOrder', () => {
    it('should prefetch order data', async () => {
      const mockOrder = createMockOrder();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockOrder,
      });

      const { result } = renderHook(() => usePrefetchOrder(), {
        wrapper: createWrapper(),
      });

      await result.current('order-123');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/orders/order-123',
        expect.any(Object),
      );
    });

    it('should handle prefetch errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => usePrefetchOrder(), {
        wrapper: createWrapper(),
      });

      await expect(result.current('order-123')).rejects.toThrow('Network error');
    });
  });

  describe('🔄 useInvalidateOrders', () => {
    it('should invalidate specific order queries', async () => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, gcTime: 0 },
        },
      });

      const wrapper = ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useInvalidateOrders(), { wrapper });

      await result.current('order-123');

      expect(invalidateQueriesSpy).toHaveBeenCalledWith({
        queryKey: orderKeys.detail('order-123'),
      });
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({
        queryKey: orderKeys.history('order-123'),
      });
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({
        queryKey: orderKeys.timeline('order-123'),
      });
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({
        queryKey: orderKeys.deliveryEstimate('order-123'),
      });
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({
        queryKey: orderKeys.lists(),
      });
    });

    it('should invalidate only list queries when no orderId provided', async () => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, gcTime: 0 },
        },
      });

      const wrapper = ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useInvalidateOrders(), { wrapper });

      await result.current();

      expect(invalidateQueriesSpy).toHaveBeenCalledWith({
        queryKey: orderKeys.lists(),
      });
      expect(invalidateQueriesSpy).toHaveBeenCalledTimes(1);
    });
  });

  describe('⚡ useOptimisticOrderUpdate', () => {
    it('should update order in detail cache', () => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, gcTime: 0 },
        },
      });

      const mockOrder = createMockOrder();
      queryClient.setQueryData(orderKeys.detail('order-123'), mockOrder);

      const wrapper = ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      const { result } = renderHook(() => useOptimisticOrderUpdate(), { wrapper });

      result.current('order-123', (old: Order) => ({
        ...old,
        status: 'confirmed',
      }));

      const updatedOrder = queryClient.getQueryData<Order>(orderKeys.detail('order-123'));
      expect(updatedOrder?.status).toBe('confirmed');
    });

    it('should update order in list cache', () => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, gcTime: 0 },
        },
      });

      const mockListResponse = createMockOrderListResponse();
      queryClient.setQueryData(orderKeys.list({}), mockListResponse);

      const wrapper = ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      const { result } = renderHook(() => useOptimisticOrderUpdate(), { wrapper });

      result.current('order-123', (old: Order) => ({
        ...old,
        status: 'confirmed',
      }));

      const updatedList = queryClient.getQueryData<OrderListResponse>(orderKeys.list({}));
      const updatedOrder = updatedList?.orders.find((o) => o.id === 'order-123');
      expect(updatedOrder?.status).toBe('confirmed');
    });

    it('should handle missing cache data gracefully', () => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, gcTime: 0 },
        },
      });

      const wrapper = ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      const { result } = renderHook(() => useOptimisticOrderUpdate(), { wrapper });

      expect(() => {
        result.current('order-123', (old: Order) => ({
          ...old,
          status: 'confirmed',
        }));
      }).not.toThrow();
    });
  });

  describe('⏱️ useOrderBackgroundRefresh', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should refresh order at specified interval', async () => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, gcTime: 0 },
        },
      });

      const wrapper = ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');

      renderHook(() => useOrderBackgroundRefresh('order-123', { interval: 5000 }), {
        wrapper,
      });

      expect(invalidateQueriesSpy).not.toHaveBeenCalled();

      vi.advanceTimersByTime(5000);

      await waitFor(() => {
        expect(invalidateQueriesSpy).toHaveBeenCalledWith({
          queryKey: orderKeys.detail('order-123'),
        });
      });

      vi.advanceTimersByTime(5000);

      await waitFor(() => {
        expect(invalidateQueriesSpy).toHaveBeenCalledTimes(2);
      });
    });

    it('should not refresh when disabled', () => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, gcTime: 0 },
        },
      });

      const wrapper = ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');

      renderHook(() => useOrderBackgroundRefresh('order-123', { enabled: false }), {
        wrapper,
      });

      vi.advanceTimersByTime(60000);

      expect(invalidateQueriesSpy).not.toHaveBeenCalled();
    });

    it('should cleanup interval on unmount', () => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, gcTime: 0 },
        },
      });

      const wrapper = ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      const clearIntervalSpy = vi.spyOn(global, 'clearInterval');

      const { unmount } = renderHook(() => useOrderBackgroundRefresh('order-123'), {
        wrapper,
      });

      unmount();

      expect(clearIntervalSpy).toHaveBeenCalled();
    });
  });

  describe('🔒 Security & Edge Cases', () => {
    it('should handle XSS in error messages', async () => {
      const xssPayload = '<script>alert("xss")</script>';
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({
          message: xssPayload,
          code: 'VALIDATION_ERROR',
        }),
      });

      const { result } = renderHook(() => useOrders(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error?.message).toBe(xssPayload);
    });

    it('should handle very large order lists', async () => {
      const largeOrderList = createMockOrderListResponse({
        orders: Array.from({ length: 1000 }, (_, i) =>
          createMockOrder({ id: `order-${i}` }),
        ),
        total: 1000,
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => largeOrderList,
      });

      const { result } = renderHook(() => useOrders(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.orders).toHaveLength(1000);
    });

    it('should handle concurrent requests', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => createMockOrder(),
      });

      const { result: result1 } = renderHook(() => useOrder('order-1'), {
        wrapper: createWrapper(),
      });
      const { result: result2 } = renderHook(() => useOrder('order-2'), {
        wrapper: createWrapper(),
      });
      const { result: result3 } = renderHook(() => useOrder('order-3'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result1.current.isSuccess).toBe(true);
        expect(result2.current.isSuccess).toBe(true);
        expect(result3.current.isSuccess).toBe(true);
      });

      expect(mockFetch).toHaveBeenCalledTimes(3);
    });

    it('should handle special characters in order IDs', async () => {
      const specialId = 'order-123!@#$%^&*()';
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => createMockOrder({ id: specialId }),
      });

      const { result } = renderHook(() => useOrder(specialId), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockFetch).toHaveBeenCalledWith(
        `http://localhost:8000/api/v1/orders/${specialId}`,
        expect.any(Object),
      );
    });

    it('should handle empty string parameters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => createMockOrderListResponse(),
      });

      renderHook(
        () =>
          useOrders({
            userId: '',
            status: undefined,
          }),
        {
          wrapper: createWrapper(),
        },
      );

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const callUrl = mockFetch.mock.calls[0][0] as string;
      expect(callUrl).not.toContain('user_id=');
      expect(callUrl).not.toContain('status=');
    });
  });

  describe('⚡ Performance & Caching', () => {
    it('should use stale data while revalidating', async () => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, gcTime: 0 },
        },
      });

      const mockOrder = createMockOrder();
      queryClient.setQueryData(orderKeys.detail('order-123'), mockOrder);

      const wrapper = ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => createMockOrder({ status: 'confirmed' }),
      });

      const { result } = renderHook(() => useOrder('order-123'), { wrapper });

      expect(result.current.data?.status).toBe('pending');

      await waitFor(() => {
        expect(result.current.data?.status).toBe('confirmed');
      });
    });

    it('should deduplicate simultaneous requests', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => createMockOrder(),
      });

      const wrapper = createWrapper();

      renderHook(() => useOrder('order-123'), { wrapper });
      renderHook(() => useOrder('order-123'), { wrapper });
      renderHook(() => useOrder('order-123'), { wrapper });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(1);
      });
    });

    it('should respect cache time settings', async () => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, gcTime: 1000 },
        },
      });

      const wrapper = ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => createMockOrder(),
      });

      const { unmount } = renderHook(() => useOrder('order-123'), { wrapper });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      unmount();

      const cachedData = queryClient.getQueryData(orderKeys.detail('order-123'));
      expect(cachedData).toBeDefined();
    });
  });
});