import { useQuery, useMutation, useQueryClient, UseQueryOptions, UseMutationOptions } from '@tanstack/react-query';
import { useCallback, useEffect, useRef } from 'react';
import type {
  Order,
  OrderWithHistory,
  OrderListRequest,
  OrderListResponse,
  OrderStatusHistory,
  OrderTimeline,
  DeliveryEstimate,
  OrderWebSocketMessage,
  OrderStatusChangedMessage,
  DeliveryEstimateUpdatedMessage,
  TimelineUpdatedMessage,
} from '../types/orders';
import { useWebSocket } from './useWebSocket';

/**
 * API base URL from environment variables
 */
const API_BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

/**
 * Query keys for React Query cache management
 */
export const orderKeys = {
  all: ['orders'] as const,
  lists: () => [...orderKeys.all, 'list'] as const,
  list: (params: OrderListRequest) => [...orderKeys.lists(), params] as const,
  details: () => [...orderKeys.all, 'detail'] as const,
  detail: (id: string) => [...orderKeys.details(), id] as const,
  history: (id: string) => [...orderKeys.all, 'history', id] as const,
  timeline: (id: string) => [...orderKeys.all, 'timeline', id] as const,
  deliveryEstimate: (id: string) => [...orderKeys.all, 'delivery', id] as const,
} as const;

/**
 * Order API error class for typed error handling
 */
export class OrderApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
    public readonly code?: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = 'OrderApiError';
  }
}

/**
 * Type guard for OrderApiError
 */
export function isOrderApiError(error: unknown): error is OrderApiError {
  return error instanceof OrderApiError;
}

/**
 * Fetch orders list with filters and pagination
 */
async function fetchOrders(request: OrderListRequest = {}): Promise<OrderListResponse> {
  const params = new URLSearchParams();

  if (request.userId) {
    params.append('user_id', request.userId);
  }
  if (request.status) {
    params.append('status', request.status);
  }
  if (request.paymentStatus) {
    params.append('payment_status', request.paymentStatus);
  }
  if (request.fulfillmentStatus) {
    params.append('fulfillment_status', request.fulfillmentStatus);
  }
  if (request.startDate) {
    params.append('start_date', request.startDate);
  }
  if (request.endDate) {
    params.append('end_date', request.endDate);
  }
  if (request.page !== undefined) {
    params.append('page', request.page.toString());
  }
  if (request.pageSize !== undefined) {
    params.append('page_size', request.pageSize.toString());
  }
  if (request.sortBy) {
    params.append('sort_by', request.sortBy);
  }
  if (request.sortDirection) {
    params.append('sort_direction', request.sortDirection);
  }

  const url = `${API_BASE_URL}/api/v1/orders?${params.toString()}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new OrderApiError(
      errorData['message'] ?? 'Failed to fetch orders',
      response.status,
      errorData['code'],
      errorData,
    );
  }

  return response.json();
}

/**
 * Fetch single order by ID
 */
async function fetchOrder(orderId: string): Promise<Order> {
  const url = `${API_BASE_URL}/api/v1/orders/${orderId}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new OrderApiError(
      errorData['message'] ?? 'Failed to fetch order',
      response.status,
      errorData['code'],
      errorData,
    );
  }

  return response.json();
}

/**
 * Fetch order with complete history
 */
async function fetchOrderWithHistory(orderId: string): Promise<OrderWithHistory> {
  const url = `${API_BASE_URL}/api/v1/orders/${orderId}/history`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new OrderApiError(
      errorData['message'] ?? 'Failed to fetch order history',
      response.status,
      errorData['code'],
      errorData,
    );
  }

  return response.json();
}

/**
 * Fetch order status history
 */
async function fetchOrderHistory(orderId: string): Promise<readonly OrderStatusHistory[]> {
  const url = `${API_BASE_URL}/api/v1/orders/${orderId}/status-history`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new OrderApiError(
      errorData['message'] ?? 'Failed to fetch order status history',
      response.status,
      errorData['code'],
      errorData,
    );
  }

  return response.json();
}

/**
 * Fetch order timeline
 */
async function fetchOrderTimeline(orderId: string): Promise<OrderTimeline> {
  const url = `${API_BASE_URL}/api/v1/orders/${orderId}/timeline`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new OrderApiError(
      errorData['message'] ?? 'Failed to fetch order timeline',
      response.status,
      errorData['code'],
      errorData,
    );
  }

  return response.json();
}

/**
 * Fetch delivery estimate
 */
async function fetchDeliveryEstimate(orderId: string): Promise<DeliveryEstimate> {
  const url = `${API_BASE_URL}/api/v1/orders/${orderId}/delivery-estimate`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new OrderApiError(
      errorData['message'] ?? 'Failed to fetch delivery estimate',
      response.status,
      errorData['code'],
      errorData,
    );
  }

  return response.json();
}

/**
 * Hook for fetching orders list with filters and pagination
 */
export function useOrders(
  request: OrderListRequest = {},
  options?: Omit<UseQueryOptions<OrderListResponse, OrderApiError>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<OrderListResponse, OrderApiError>({
    queryKey: orderKeys.list(request),
    queryFn: () => fetchOrders(request),
    staleTime: 30000,
    gcTime: 300000,
    ...options,
  });
}

/**
 * Hook for fetching single order
 */
export function useOrder(
  orderId: string,
  options?: Omit<UseQueryOptions<Order, OrderApiError>, 'queryKey' | 'queryFn'>,
) {
  const queryClient = useQueryClient();

  return useQuery<Order, OrderApiError>({
    queryKey: orderKeys.detail(orderId),
    queryFn: () => fetchOrder(orderId),
    staleTime: 60000,
    gcTime: 300000,
    enabled: Boolean(orderId),
    ...options,
    placeholderData: () => {
      const listData = queryClient.getQueriesData<OrderListResponse>({
        queryKey: orderKeys.lists(),
      });

      for (const [, data] of listData) {
        if (data?.orders) {
          const order = data.orders.find((o) => o.id === orderId);
          if (order) {
            return order;
          }
        }
      }

      return undefined;
    },
  });
}

/**
 * Hook for fetching order with complete history
 */
export function useOrderWithHistory(
  orderId: string,
  options?: Omit<UseQueryOptions<OrderWithHistory, OrderApiError>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<OrderWithHistory, OrderApiError>({
    queryKey: orderKeys.detail(orderId),
    queryFn: () => fetchOrderWithHistory(orderId),
    staleTime: 60000,
    gcTime: 300000,
    enabled: Boolean(orderId),
    ...options,
  });
}

/**
 * Hook for fetching order status history
 */
export function useOrderHistory(
  orderId: string,
  options?: Omit<UseQueryOptions<readonly OrderStatusHistory[], OrderApiError>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<readonly OrderStatusHistory[], OrderApiError>({
    queryKey: orderKeys.history(orderId),
    queryFn: () => fetchOrderHistory(orderId),
    staleTime: 60000,
    gcTime: 300000,
    enabled: Boolean(orderId),
    ...options,
  });
}

/**
 * Hook for fetching order timeline
 */
export function useOrderTimeline(
  orderId: string,
  options?: Omit<UseQueryOptions<OrderTimeline, OrderApiError>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<OrderTimeline, OrderApiError>({
    queryKey: orderKeys.timeline(orderId),
    queryFn: () => fetchOrderTimeline(orderId),
    staleTime: 60000,
    gcTime: 300000,
    enabled: Boolean(orderId),
    ...options,
  });
}

/**
 * Hook for fetching delivery estimate
 */
export function useDeliveryEstimate(
  orderId: string,
  options?: Omit<UseQueryOptions<DeliveryEstimate, OrderApiError>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<DeliveryEstimate, OrderApiError>({
    queryKey: orderKeys.deliveryEstimate(orderId),
    queryFn: () => fetchDeliveryEstimate(orderId),
    staleTime: 60000,
    gcTime: 300000,
    enabled: Boolean(orderId),
    ...options,
  });
}

/**
 * Hook for real-time order updates via WebSocket
 */
export function useOrderRealtime(
  orderId: string,
  options: {
    readonly enabled?: boolean;
    readonly onStatusChange?: (message: OrderStatusChangedMessage) => void;
    readonly onDeliveryUpdate?: (message: DeliveryEstimateUpdatedMessage) => void;
    readonly onTimelineUpdate?: (message: TimelineUpdatedMessage) => void;
  } = {},
) {
  const queryClient = useQueryClient();
  const { enabled = true, onStatusChange, onDeliveryUpdate, onTimelineUpdate } = options;

  const handleMessage = useCallback(
    (message: OrderWebSocketMessage) => {
      if (message.orderId !== orderId) {
        return;
      }

      switch (message.type) {
        case 'order_status_changed': {
          const statusMessage = message as OrderStatusChangedMessage;
          void queryClient.invalidateQueries({ queryKey: orderKeys.detail(orderId) });
          void queryClient.invalidateQueries({ queryKey: orderKeys.history(orderId) });
          void queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
          if (onStatusChange) {
            onStatusChange(statusMessage);
          }
          break;
        }
        case 'delivery_estimate_updated': {
          const deliveryMessage = message as DeliveryEstimateUpdatedMessage;
          queryClient.setQueryData(orderKeys.deliveryEstimate(orderId), deliveryMessage.data);
          void queryClient.invalidateQueries({ queryKey: orderKeys.detail(orderId) });
          if (onDeliveryUpdate) {
            onDeliveryUpdate(deliveryMessage);
          }
          break;
        }
        case 'timeline_updated': {
          const timelineMessage = message as TimelineUpdatedMessage;
          queryClient.setQueryData(orderKeys.timeline(orderId), timelineMessage.data);
          void queryClient.invalidateQueries({ queryKey: orderKeys.detail(orderId) });
          if (onTimelineUpdate) {
            onTimelineUpdate(timelineMessage);
          }
          break;
        }
        case 'shipping_info_updated':
        case 'order_cancelled':
        case 'order_delayed': {
          void queryClient.invalidateQueries({ queryKey: orderKeys.detail(orderId) });
          void queryClient.invalidateQueries({ queryKey: orderKeys.history(orderId) });
          void queryClient.invalidateQueries({ queryKey: orderKeys.timeline(orderId) });
          void queryClient.invalidateQueries({ queryKey: orderKeys.deliveryEstimate(orderId) });
          void queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
          break;
        }
      }
    },
    [orderId, queryClient, onStatusChange, onDeliveryUpdate, onTimelineUpdate],
  );

  const websocket = useWebSocket({
    orderId,
    onMessage: handleMessage,
    enabled: enabled && Boolean(orderId),
    autoConnect: true,
    reconnection: true,
  });

  return websocket;
}

/**
 * Hook for prefetching order data
 */
export function usePrefetchOrder() {
  const queryClient = useQueryClient();

  return useCallback(
    async (orderId: string) => {
      await queryClient.prefetchQuery({
        queryKey: orderKeys.detail(orderId),
        queryFn: () => fetchOrder(orderId),
        staleTime: 60000,
      });
    },
    [queryClient],
  );
}

/**
 * Hook for invalidating order queries
 */
export function useInvalidateOrders() {
  const queryClient = useQueryClient();

  return useCallback(
    async (orderId?: string) => {
      if (orderId) {
        await queryClient.invalidateQueries({ queryKey: orderKeys.detail(orderId) });
        await queryClient.invalidateQueries({ queryKey: orderKeys.history(orderId) });
        await queryClient.invalidateQueries({ queryKey: orderKeys.timeline(orderId) });
        await queryClient.invalidateQueries({ queryKey: orderKeys.deliveryEstimate(orderId) });
      }
      await queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
    },
    [queryClient],
  );
}

/**
 * Hook for optimistic order updates
 */
export function useOptimisticOrderUpdate() {
  const queryClient = useQueryClient();

  return useCallback(
    <T extends Order | OrderWithHistory>(orderId: string, updater: (old: T) => T) => {
      queryClient.setQueryData<T>(orderKeys.detail(orderId), updater);

      queryClient.setQueriesData<OrderListResponse>(
        { queryKey: orderKeys.lists() },
        (old) => {
          if (!old) {
            return old;
          }

          return {
            ...old,
            orders: old.orders.map((order) =>
              order.id === orderId ? updater(order as T) : order,
            ),
          };
        },
      );
    },
    [queryClient],
  );
}

/**
 * Hook for background order refresh
 */
export function useOrderBackgroundRefresh(
  orderId: string,
  options: {
    readonly enabled?: boolean;
    readonly interval?: number;
  } = {},
) {
  const { enabled = true, interval = 60000 } = options;
  const queryClient = useQueryClient();
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled || !orderId) {
      return;
    }

    const refresh = () => {
      void queryClient.invalidateQueries({ queryKey: orderKeys.detail(orderId) });
    };

    intervalRef.current = window.setInterval(refresh, interval);

    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [enabled, orderId, interval, queryClient]);
}

/**
 * Export types for external use
 */
export type {
  Order,
  OrderWithHistory,
  OrderListRequest,
  OrderListResponse,
  OrderStatusHistory,
  OrderTimeline,
  DeliveryEstimate,
  OrderWebSocketMessage,
  OrderStatusChangedMessage,
  DeliveryEstimateUpdatedMessage,
  TimelineUpdatedMessage,
};