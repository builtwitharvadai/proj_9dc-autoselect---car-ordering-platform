/**
 * Order tracking API client for AutoSelect platform
 * Provides type-safe functions for order management, status tracking, and delivery estimation
 */

const API_BASE_URL = import.meta.env['VITE_API_BASE_URL'] ?? 'http://localhost:8000';
const API_TIMEOUT = 30000;
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000;

/**
 * Custom error class for order API operations
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
    Object.setPrototypeOf(this, OrderApiError.prototype);
  }
}

/**
 * Type guard for OrderApiError
 */
export function isOrderApiError(error: unknown): error is OrderApiError {
  return error instanceof OrderApiError;
}

/**
 * Request configuration interface
 */
interface RequestConfig {
  readonly method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  readonly endpoint: string;
  readonly body?: unknown;
  readonly params?: Record<string, string | number | boolean | undefined>;
  readonly headers?: Record<string, string>;
  readonly timeout?: number;
  readonly retries?: number;
}

/**
 * Build URL with query parameters
 */
function buildUrl(endpoint: string, params?: Record<string, string | number | boolean | undefined>): string {
  const url = new URL(`${API_BASE_URL}${endpoint}`);
  
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.append(key, String(value));
      }
    });
  }
  
  return url.toString();
}

/**
 * Sleep utility for retry delays
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Execute HTTP request with retry logic
 */
async function executeRequest<T>(config: RequestConfig): Promise<T> {
  const {
    method,
    endpoint,
    body,
    params,
    headers = {},
    timeout = API_TIMEOUT,
    retries = MAX_RETRIES,
  } = config;

  const url = buildUrl(endpoint, params);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  let lastError: Error | null = null;
  let attempt = 0;

  while (attempt < retries) {
    try {
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...headers,
        },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new OrderApiError(
          errorData['message'] ?? `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          errorData['code'],
          errorData['details'],
        );
      }

      const data = await response.json();
      return data as T;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      if (error instanceof OrderApiError && error.statusCode && error.statusCode < 500) {
        throw error;
      }

      if (error instanceof Error && error.name === 'AbortError') {
        throw new OrderApiError('Request timeout', 408, 'TIMEOUT');
      }

      attempt++;
      if (attempt < retries) {
        await sleep(RETRY_DELAY * attempt);
      }
    }
  }

  clearTimeout(timeoutId);
  throw new OrderApiError(
    `Request failed after ${retries} attempts: ${lastError?.message ?? 'Unknown error'}`,
    503,
    'MAX_RETRIES_EXCEEDED',
    { originalError: lastError },
  );
}

/**
 * Fetch list of orders with optional filters
 */
export async function fetchOrders(
  request: import('../types/orders').OrderListRequest = {},
): Promise<import('../types/orders').OrderListResponse> {
  return executeRequest({
    method: 'GET',
    endpoint: '/api/v1/orders',
    params: {
      user_id: request.userId,
      status: request.status,
      payment_status: request.paymentStatus,
      fulfillment_status: request.fulfillmentStatus,
      start_date: request.startDate,
      end_date: request.endDate,
      page: request.page,
      page_size: request.pageSize,
      sort_by: request.sortBy,
      sort_direction: request.sortDirection,
    },
  });
}

/**
 * Fetch single order by ID
 */
export async function fetchOrderById(
  orderId: string,
): Promise<import('../types/orders').Order> {
  if (!orderId || typeof orderId !== 'string') {
    throw new OrderApiError('Invalid order ID', 400, 'INVALID_ORDER_ID');
  }

  return executeRequest({
    method: 'GET',
    endpoint: `/api/v1/orders/${orderId}`,
  });
}

/**
 * Fetch order with complete history and timeline
 */
export async function fetchOrderWithHistory(
  orderId: string,
): Promise<import('../types/orders').OrderWithHistory> {
  if (!orderId || typeof orderId !== 'string') {
    throw new OrderApiError('Invalid order ID', 400, 'INVALID_ORDER_ID');
  }

  return executeRequest({
    method: 'GET',
    endpoint: `/api/v1/orders/${orderId}/history`,
  });
}

/**
 * Fetch order status history
 */
export async function fetchOrderStatusHistory(
  orderId: string,
): Promise<readonly import('../types/orders').OrderStatusHistory[]> {
  if (!orderId || typeof orderId !== 'string') {
    throw new OrderApiError('Invalid order ID', 400, 'INVALID_ORDER_ID');
  }

  return executeRequest({
    method: 'GET',
    endpoint: `/api/v1/orders/${orderId}/status-history`,
  });
}

/**
 * Fetch order timeline for visual tracking
 */
export async function fetchOrderTimeline(
  orderId: string,
): Promise<import('../types/orders').OrderTimeline> {
  if (!orderId || typeof orderId !== 'string') {
    throw new OrderApiError('Invalid order ID', 400, 'INVALID_ORDER_ID');
  }

  return executeRequest({
    method: 'GET',
    endpoint: `/api/v1/orders/${orderId}/timeline`,
  });
}

/**
 * Fetch delivery estimate for order
 */
export async function fetchDeliveryEstimate(
  orderId: string,
): Promise<import('../types/orders').DeliveryEstimate> {
  if (!orderId || typeof orderId !== 'string') {
    throw new OrderApiError('Invalid order ID', 400, 'INVALID_ORDER_ID');
  }

  return executeRequest({
    method: 'GET',
    endpoint: `/api/v1/orders/${orderId}/delivery-estimate`,
  });
}

/**
 * Create new order
 */
export async function createOrder(
  request: import('../types/orders').OrderCreateRequest,
): Promise<import('../types/orders').Order> {
  if (!request.items || request.items.length === 0) {
    throw new OrderApiError('Order must contain at least one item', 400, 'EMPTY_ORDER');
  }

  if (!request.customerInfo || !request.deliveryAddress) {
    throw new OrderApiError('Customer info and delivery address are required', 400, 'MISSING_REQUIRED_FIELDS');
  }

  return executeRequest({
    method: 'POST',
    endpoint: '/api/v1/orders',
    body: request,
  });
}

/**
 * Update order status
 */
export async function updateOrderStatus(
  orderId: string,
  request: import('../types/orders').OrderStatusUpdateRequest,
): Promise<import('../types/orders').Order> {
  if (!orderId || typeof orderId !== 'string') {
    throw new OrderApiError('Invalid order ID', 400, 'INVALID_ORDER_ID');
  }

  if (!request.status) {
    throw new OrderApiError('Status is required', 400, 'MISSING_STATUS');
  }

  return executeRequest({
    method: 'PATCH',
    endpoint: `/api/v1/orders/${orderId}/status`,
    body: request,
  });
}

/**
 * Cancel order
 */
export async function cancelOrder(
  orderId: string,
  reason?: string,
): Promise<import('../types/orders').Order> {
  if (!orderId || typeof orderId !== 'string') {
    throw new OrderApiError('Invalid order ID', 400, 'INVALID_ORDER_ID');
  }

  return executeRequest({
    method: 'POST',
    endpoint: `/api/v1/orders/${orderId}/cancel`,
    body: { reason },
  });
}

/**
 * Prefetch order data for caching
 */
export async function prefetchOrder(orderId: string): Promise<void> {
  try {
    await fetchOrderById(orderId);
  } catch (error) {
    console.warn(`Failed to prefetch order ${orderId}:`, error);
  }
}

/**
 * Prefetch multiple orders
 */
export async function prefetchOrders(orderIds: readonly string[]): Promise<void> {
  await Promise.allSettled(orderIds.map((id) => prefetchOrder(id)));
}

/**
 * Batch fetch orders by IDs
 */
export async function fetchOrdersByIds(
  orderIds: readonly string[],
): Promise<readonly import('../types/orders').Order[]> {
  if (!orderIds || orderIds.length === 0) {
    return [];
  }

  const uniqueIds = [...new Set(orderIds)];
  const results = await Promise.allSettled(
    uniqueIds.map((id) => fetchOrderById(id)),
  );

  return results
    .filter((result): result is PromiseFulfilledResult<import('../types/orders').Order> => 
      result.status === 'fulfilled'
    )
    .map((result) => result.value);
}

/**
 * Export order types for convenience
 */
export type {
  Order,
  OrderWithHistory,
  OrderItem,
  OrderStatus,
  PaymentStatus,
  FulfillmentStatus,
  OrderStatusHistory,
  OrderTimeline,
  OrderTimelineStage,
  DeliveryEstimate,
  OrderListRequest,
  OrderListResponse,
  OrderCreateRequest,
  OrderStatusUpdateRequest,
} from '../types/orders';