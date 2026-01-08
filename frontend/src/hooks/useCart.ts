/**
 * Cart Operations React Query Hooks
 * Provides type-safe hooks for cart operations with optimistic updates,
 * error handling, and automatic refetch on window focus
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  Cart,
  AddToCartRequest,
  AddToCartResponse,
  UpdateCartItemRequest,
  UpdateCartItemResponse,
  RemoveCartItemResponse,
  ApplyPromotionalCodeRequest,
  ApplyPromotionalCodeResponse,
  CartError,
} from '../types/cart';

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
  cart: `${API_BASE_URL}/api/${API_VERSION}/cart`,
  addToCart: `${API_BASE_URL}/api/${API_VERSION}/cart/items`,
  updateCartItem: (itemId: string) =>
    `${API_BASE_URL}/api/${API_VERSION}/cart/items/${itemId}`,
  removeCartItem: (itemId: string) =>
    `${API_BASE_URL}/api/${API_VERSION}/cart/items/${itemId}`,
  applyPromoCode: `${API_BASE_URL}/api/${API_VERSION}/cart/promo-code`,
} as const;

/**
 * Query keys for cart operations
 */
export const cartKeys = {
  all: ['cart'] as const,
  detail: () => [...cartKeys.all, 'detail'] as const,
} as const;

/**
 * Custom error class for cart API errors
 */
export class CartApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly cartError?: CartError,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'CartApiError';
  }
}

/**
 * Type guard for cart error responses
 */
function isCartErrorResponse(data: unknown): data is { error: CartError } {
  return (
    typeof data === 'object' &&
    data !== null &&
    'error' in data &&
    typeof (data as { error: unknown }).error === 'object'
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
 * Handle fetch response with error handling
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      throw new CartApiError(
        `HTTP ${response.status}: ${response.statusText}`,
        response.status,
      );
    }

    if (isCartErrorResponse(errorData)) {
      throw new CartApiError(
        errorData.error.message,
        response.status,
        errorData.error,
        errorData.error.details,
      );
    }

    throw new CartApiError(
      `HTTP ${response.status}: ${response.statusText}`,
      response.status,
      undefined,
      { data: errorData },
    );
  }

  try {
    return await response.json();
  } catch (error) {
    throw new CartApiError(
      'Failed to parse response JSON',
      500,
      undefined,
      { originalError: error instanceof Error ? error.message : String(error) },
    );
  }
}

/**
 * Fetch current cart
 */
async function fetchCart(): Promise<Cart> {
  const controller = createAbortController();

  try {
    const response = await fetch(ENDPOINTS.cart, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      signal: controller.signal,
    });

    return await handleResponse<Cart>(response);
  } catch (error) {
    if (error instanceof CartApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new CartApiError('Request timeout', 408);
      }
      throw new CartApiError(error.message, 500, undefined, {
        originalError: error.message,
      });
    }

    throw new CartApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Add item to cart
 */
async function addToCart(request: AddToCartRequest): Promise<AddToCartResponse> {
  const controller = createAbortController();

  try {
    const response = await fetch(ENDPOINTS.addToCart, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    return await handleResponse<AddToCartResponse>(response);
  } catch (error) {
    if (error instanceof CartApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new CartApiError('Request timeout', 408);
      }
      throw new CartApiError(error.message, 500, undefined, {
        originalError: error.message,
      });
    }

    throw new CartApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Update cart item quantity
 */
async function updateCartItem(
  itemId: string,
  request: UpdateCartItemRequest,
): Promise<UpdateCartItemResponse> {
  const controller = createAbortController();

  try {
    const response = await fetch(ENDPOINTS.updateCartItem(itemId), {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    return await handleResponse<UpdateCartItemResponse>(response);
  } catch (error) {
    if (error instanceof CartApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new CartApiError('Request timeout', 408);
      }
      throw new CartApiError(error.message, 500, undefined, {
        originalError: error.message,
      });
    }

    throw new CartApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Remove item from cart
 */
async function removeCartItem(itemId: string): Promise<RemoveCartItemResponse> {
  const controller = createAbortController();

  try {
    const response = await fetch(ENDPOINTS.removeCartItem(itemId), {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      signal: controller.signal,
    });

    return await handleResponse<RemoveCartItemResponse>(response);
  } catch (error) {
    if (error instanceof CartApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new CartApiError('Request timeout', 408);
      }
      throw new CartApiError(error.message, 500, undefined, {
        originalError: error.message,
      });
    }

    throw new CartApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Apply promotional code to cart
 */
async function applyPromoCode(
  request: ApplyPromotionalCodeRequest,
): Promise<ApplyPromotionalCodeResponse> {
  const controller = createAbortController();

  try {
    const response = await fetch(ENDPOINTS.applyPromoCode, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    return await handleResponse<ApplyPromotionalCodeResponse>(response);
  } catch (error) {
    if (error instanceof CartApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new CartApiError('Request timeout', 408);
      }
      throw new CartApiError(error.message, 500, undefined, {
        originalError: error.message,
      });
    }

    throw new CartApiError('Unknown error occurred', 500);
  } finally {
    cleanupAbortController(controller);
  }
}

/**
 * Hook to fetch current cart with automatic refetch on window focus
 */
export function useCart() {
  return useQuery({
    queryKey: cartKeys.detail(),
    queryFn: fetchCart,
    staleTime: 30000,
    refetchOnWindowFocus: true,
    refetchOnMount: true,
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}

/**
 * Hook to add item to cart with optimistic updates
 */
export function useAddToCart() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: addToCart,
    onMutate: async (request) => {
      await queryClient.cancelQueries({ queryKey: cartKeys.detail() });

      const previousCart = queryClient.getQueryData<Cart>(cartKeys.detail());

      if (previousCart) {
        const optimisticCart: Cart = {
          ...previousCart,
          items: [
            ...previousCart.items,
            {
              id: `temp-${Date.now()}`,
              cartId: previousCart.id,
              vehicleId: request.vehicleId,
              configurationId: request.configurationId,
              quantity: request.quantity,
              unitPrice: 0,
              totalPrice: 0,
              status: 'active',
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            },
          ],
          itemCount: previousCart.itemCount + 1,
        };

        queryClient.setQueryData(cartKeys.detail(), optimisticCart);
      }

      return { previousCart };
    },
    onError: (_error, _variables, context) => {
      if (context?.previousCart) {
        queryClient.setQueryData(cartKeys.detail(), context.previousCart);
      }
    },
    onSuccess: (data) => {
      queryClient.setQueryData(cartKeys.detail(), data.cart);
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: cartKeys.detail() });
    },
  });
}

/**
 * Hook to update cart item quantity with optimistic updates
 */
export function useUpdateCartItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ itemId, request }: { itemId: string; request: UpdateCartItemRequest }) =>
      updateCartItem(itemId, request),
    onMutate: async ({ itemId, request }) => {
      await queryClient.cancelQueries({ queryKey: cartKeys.detail() });

      const previousCart = queryClient.getQueryData<Cart>(cartKeys.detail());

      if (previousCart) {
        const optimisticCart: Cart = {
          ...previousCart,
          items: previousCart.items.map((item) =>
            item.id === itemId
              ? {
                  ...item,
                  quantity: request.quantity,
                  totalPrice: item.unitPrice * request.quantity,
                  updatedAt: new Date().toISOString(),
                }
              : item,
          ),
        };

        queryClient.setQueryData(cartKeys.detail(), optimisticCart);
      }

      return { previousCart };
    },
    onError: (_error, _variables, context) => {
      if (context?.previousCart) {
        queryClient.setQueryData(cartKeys.detail(), context.previousCart);
      }
    },
    onSuccess: (data) => {
      queryClient.setQueryData(cartKeys.detail(), data.cart);
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: cartKeys.detail() });
    },
  });
}

/**
 * Hook to remove item from cart with optimistic updates
 */
export function useRemoveCartItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: removeCartItem,
    onMutate: async (itemId) => {
      await queryClient.cancelQueries({ queryKey: cartKeys.detail() });

      const previousCart = queryClient.getQueryData<Cart>(cartKeys.detail());

      if (previousCart) {
        const optimisticCart: Cart = {
          ...previousCart,
          items: previousCart.items.filter((item) => item.id !== itemId),
          itemCount: previousCart.itemCount - 1,
        };

        queryClient.setQueryData(cartKeys.detail(), optimisticCart);
      }

      return { previousCart };
    },
    onError: (_error, _variables, context) => {
      if (context?.previousCart) {
        queryClient.setQueryData(cartKeys.detail(), context.previousCart);
      }
    },
    onSuccess: (data) => {
      queryClient.setQueryData(cartKeys.detail(), data.cart);
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: cartKeys.detail() });
    },
  });
}

/**
 * Hook to apply promotional code with optimistic updates
 */
export function useApplyPromoCode() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: applyPromoCode,
    onMutate: async (request) => {
      await queryClient.cancelQueries({ queryKey: cartKeys.detail() });

      const previousCart = queryClient.getQueryData<Cart>(cartKeys.detail());

      if (previousCart) {
        const optimisticCart: Cart = {
          ...previousCart,
          promotionalCode: request.code,
        };

        queryClient.setQueryData(cartKeys.detail(), optimisticCart);
      }

      return { previousCart };
    },
    onError: (_error, _variables, context) => {
      if (context?.previousCart) {
        queryClient.setQueryData(cartKeys.detail(), context.previousCart);
      }
    },
    onSuccess: (data) => {
      queryClient.setQueryData(cartKeys.detail(), data.cart);
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: cartKeys.detail() });
    },
  });
}

/**
 * Type guard for CartApiError
 */
export function isCartApiError(error: unknown): error is CartApiError {
  return error instanceof CartApiError;
}

/**
 * Export types for external use
 */
export type {
  Cart,
  AddToCartRequest,
  AddToCartResponse,
  UpdateCartItemRequest,
  UpdateCartItemResponse,
  RemoveCartItemResponse,
  ApplyPromotionalCodeRequest,
  ApplyPromotionalCodeResponse,
  CartError,
};