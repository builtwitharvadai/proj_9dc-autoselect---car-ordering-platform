/**
 * Dealer Order Management Hooks
 * 
 * React Query hooks for dealer order operations including order queue management,
 * fulfillment actions, and bulk operations with optimistic updates and caching.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
  type QueryKey,
} from '@tanstack/react-query';
import type {
  DealerOrder,
  DealerOrderDetail,
  OrderQueueRequest,
  OrderQueueResponse,
  FulfillmentActionRequest,
  FulfillmentActionResponse,
  BulkOrderOperationRequest,
  BulkOrderOperationResponse,
  DealerOrderStatus,
} from '../types/dealer';

const API_BASE_URL = import.meta.env['VITE_API_BASE_URL'] ?? 'http://localhost:8000';

/**
 * Query key factory for dealer orders
 */
export const dealerOrderKeys = {
  all: ['dealer-orders'] as const,
  lists: () => [...dealerOrderKeys.all, 'list'] as const,
  list: (params: OrderQueueRequest) => [...dealerOrderKeys.lists(), params] as const,
  details: () => [...dealerOrderKeys.all, 'detail'] as const,
  detail: (id: string) => [...dealerOrderKeys.details(), id] as const,
} as const;

/**
 * Custom error class for dealer order API errors
 */
export class DealerOrderApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
    public readonly code?: string,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'DealerOrderApiError';
  }
}

/**
 * Type guard for DealerOrderApiError
 */
export function isDealerOrderApiError(error: unknown): error is DealerOrderApiError {
  return error instanceof DealerOrderApiError;
}

/**
 * Fetch dealer orders with filtering and pagination
 */
async function fetchDealerOrders(request: OrderQueueRequest): Promise<OrderQueueResponse> {
  const params = new URLSearchParams();

  if (request.filters?.dealerId) {
    params.append('dealer_id', request.filters.dealerId);
  }
  if (request.filters?.status?.length) {
    request.filters.status.forEach((status) => params.append('status', status));
  }
  if (request.filters?.customerId) {
    params.append('customer_id', request.filters.customerId);
  }
  if (request.filters?.vehicleId) {
    params.append('vehicle_id', request.filters.vehicleId);
  }
  if (request.filters?.orderNumber) {
    params.append('order_number', request.filters.orderNumber);
  }
  if (request.filters?.searchQuery) {
    params.append('search', request.filters.searchQuery);
  }
  if (request.filters?.startDate) {
    params.append('start_date', request.filters.startDate);
  }
  if (request.filters?.endDate) {
    params.append('end_date', request.filters.endDate);
  }
  if (request.filters?.minAmount !== undefined) {
    params.append('min_amount', request.filters.minAmount.toString());
  }
  if (request.filters?.maxAmount !== undefined) {
    params.append('max_amount', request.filters.maxAmount.toString());
  }

  if (request.sortOptions?.sortBy) {
    params.append('sort_by', request.sortOptions.sortBy);
  }
  if (request.sortOptions?.sortDirection) {
    params.append('sort_direction', request.sortOptions.sortDirection);
  }

  if (request.page !== undefined) {
    params.append('page', request.page.toString());
  }
  if (request.pageSize !== undefined) {
    params.append('page_size', request.pageSize.toString());
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/dealer/orders?${params.toString()}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new DealerOrderApiError(
      errorData.message ?? 'Failed to fetch dealer orders',
      response.status,
      errorData.code,
      errorData.details,
    );
  }

  return response.json();
}

/**
 * Fetch single dealer order with full details
 */
async function fetchDealerOrderDetail(orderId: string): Promise<DealerOrderDetail> {
  const response = await fetch(`${API_BASE_URL}/api/v1/dealer/orders/${orderId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new DealerOrderApiError(
      errorData.message ?? 'Failed to fetch order details',
      response.status,
      errorData.code,
      errorData.details,
    );
  }

  return response.json();
}

/**
 * Execute fulfillment action on an order
 */
async function executeFulfillmentAction(
  request: FulfillmentActionRequest,
): Promise<FulfillmentActionResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/dealer/orders/${request.orderId}/fulfillment`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        action: request.action,
        notes: request.notes,
        estimated_completion_date: request.estimatedCompletionDate,
      }),
    },
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new DealerOrderApiError(
      errorData.message ?? 'Failed to execute fulfillment action',
      response.status,
      errorData.code,
      errorData.details,
    );
  }

  return response.json();
}

/**
 * Execute bulk operation on multiple orders
 */
async function executeBulkOperation(
  request: BulkOrderOperationRequest,
): Promise<BulkOrderOperationResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/dealer/orders/bulk`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
      order_ids: request.orderIds,
      operation: request.operation,
      target_status: request.targetStatus,
      notes: request.notes,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new DealerOrderApiError(
      errorData.message ?? 'Failed to execute bulk operation',
      response.status,
      errorData.code,
      errorData.details,
    );
  }

  return response.json();
}

/**
 * Hook to fetch dealer orders with filtering and pagination
 */
export function useDealerOrders(
  request: OrderQueueRequest = {},
  options?: Omit<
    UseQueryOptions<OrderQueueResponse, DealerOrderApiError>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery<OrderQueueResponse, DealerOrderApiError>({
    queryKey: dealerOrderKeys.list(request),
    queryFn: () => fetchDealerOrders(request),
    staleTime: 30000,
    gcTime: 300000,
    ...options,
  });
}

/**
 * Hook to fetch single dealer order with full details
 */
export function useDealerOrderDetail(
  orderId: string,
  options?: Omit<UseQueryOptions<DealerOrderDetail, DealerOrderApiError>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<DealerOrderDetail, DealerOrderApiError>({
    queryKey: dealerOrderKeys.detail(orderId),
    queryFn: () => fetchDealerOrderDetail(orderId),
    staleTime: 60000,
    gcTime: 300000,
    enabled: Boolean(orderId),
    ...options,
  });
}

/**
 * Hook to execute fulfillment actions with optimistic updates
 */
export function useOrderFulfillment(
  options?: Omit<
    UseMutationOptions<
      FulfillmentActionResponse,
      DealerOrderApiError,
      FulfillmentActionRequest
    >,
    'mutationFn'
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<FulfillmentActionResponse, DealerOrderApiError, FulfillmentActionRequest>({
    mutationFn: executeFulfillmentAction,
    onMutate: async (request) => {
      const detailKey = dealerOrderKeys.detail(request.orderId);
      await queryClient.cancelQueries({ queryKey: detailKey });

      const previousOrder = queryClient.getQueryData<DealerOrderDetail>(detailKey);

      if (previousOrder) {
        const optimisticStatus = getOptimisticStatus(request.action);
        if (optimisticStatus) {
          queryClient.setQueryData<DealerOrderDetail>(detailKey, {
            ...previousOrder,
            status: optimisticStatus,
          });
        }
      }

      return { previousOrder };
    },
    onError: (_error, request, context) => {
      if (context?.previousOrder) {
        queryClient.setQueryData(dealerOrderKeys.detail(request.orderId), context.previousOrder);
      }
    },
    onSuccess: (_data, request) => {
      void queryClient.invalidateQueries({ queryKey: dealerOrderKeys.detail(request.orderId) });
      void queryClient.invalidateQueries({ queryKey: dealerOrderKeys.lists() });
    },
    ...options,
  });
}

/**
 * Hook to execute bulk operations on multiple orders
 */
export function useBulkOrderOperations(
  options?: Omit<
    UseMutationOptions<
      BulkOrderOperationResponse,
      DealerOrderApiError,
      BulkOrderOperationRequest
    >,
    'mutationFn'
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<BulkOrderOperationResponse, DealerOrderApiError, BulkOrderOperationRequest>({
    mutationFn: executeBulkOperation,
    onMutate: async (request) => {
      await queryClient.cancelQueries({ queryKey: dealerOrderKeys.lists() });

      const previousLists = queryClient.getQueriesData<OrderQueueResponse>({
        queryKey: dealerOrderKeys.lists(),
      });

      if (request.targetStatus && request.operation === 'update_status') {
        previousLists.forEach(([queryKey]) => {
          const currentData = queryClient.getQueryData<OrderQueueResponse>(queryKey);
          if (currentData) {
            queryClient.setQueryData<OrderQueueResponse>(queryKey, {
              ...currentData,
              orders: currentData.orders.map((order) =>
                request.orderIds.includes(order.id)
                  ? { ...order, status: request.targetStatus as DealerOrderStatus }
                  : order,
              ),
            });
          }
        });
      }

      return { previousLists };
    },
    onError: (_error, _request, context) => {
      if (context?.previousLists) {
        context.previousLists.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
    },
    onSuccess: (_data, request) => {
      void queryClient.invalidateQueries({ queryKey: dealerOrderKeys.lists() });
      request.orderIds.forEach((orderId) => {
        void queryClient.invalidateQueries({ queryKey: dealerOrderKeys.detail(orderId) });
      });
    },
    ...options,
  });
}

/**
 * Hook to prefetch dealer order detail
 */
export function usePrefetchDealerOrderDetail() {
  const queryClient = useQueryClient();

  return (orderId: string) => {
    void queryClient.prefetchQuery({
      queryKey: dealerOrderKeys.detail(orderId),
      queryFn: () => fetchDealerOrderDetail(orderId),
      staleTime: 60000,
    });
  };
}

/**
 * Hook to invalidate dealer order queries
 */
export function useInvalidateDealerOrders() {
  const queryClient = useQueryClient();

  return {
    invalidateAll: () => {
      void queryClient.invalidateQueries({ queryKey: dealerOrderKeys.all });
    },
    invalidateLists: () => {
      void queryClient.invalidateQueries({ queryKey: dealerOrderKeys.lists() });
    },
    invalidateDetail: (orderId: string) => {
      void queryClient.invalidateQueries({ queryKey: dealerOrderKeys.detail(orderId) });
    },
  };
}

/**
 * Hook to get cached dealer order detail
 */
export function useCachedDealerOrderDetail(orderId: string): DealerOrderDetail | undefined {
  const queryClient = useQueryClient();
  return queryClient.getQueryData<DealerOrderDetail>(dealerOrderKeys.detail(orderId));
}

/**
 * Hook to set dealer order detail cache
 */
export function useSetDealerOrderDetailCache() {
  const queryClient = useQueryClient();

  return (orderId: string, data: DealerOrderDetail) => {
    queryClient.setQueryData<DealerOrderDetail>(dealerOrderKeys.detail(orderId), data);
  };
}

/**
 * Helper function to determine optimistic status based on action
 */
function getOptimisticStatus(
  action: FulfillmentActionRequest['action'],
): DealerOrderStatus | null {
  const statusMap: Record<string, DealerOrderStatus> = {
    confirm: 'confirmed',
    start_production: 'in_production',
    mark_ready: 'ready_for_pickup',
    complete: 'completed',
    cancel: 'cancelled',
  };

  return statusMap[action] ?? null;
}

/**
 * Export types for external use
 */
export type {
  DealerOrder,
  DealerOrderDetail,
  OrderQueueRequest,
  OrderQueueResponse,
  FulfillmentActionRequest,
  FulfillmentActionResponse,
  BulkOrderOperationRequest,
  BulkOrderOperationResponse,
  DealerOrderStatus,
};