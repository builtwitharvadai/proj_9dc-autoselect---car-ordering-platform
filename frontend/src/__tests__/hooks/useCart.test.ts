/**
 * Comprehensive Test Suite for Cart Operations Hooks
 * 
 * Tests cover:
 * - Query hook behavior (useCart)
 * - Mutation hooks with optimistic updates
 * - Error handling and recovery
 * - Cache invalidation strategies
 * - Network timeout scenarios
 * - API response parsing
 * - Type guards and error classes
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useCart,
  useAddToCart,
  useUpdateCartItem,
  useRemoveCartItem,
  useApplyPromoCode,
  CartApiError,
  isCartApiError,
  cartKeys,
} from '../../hooks/useCart';
import type {
  Cart,
  AddToCartRequest,
  UpdateCartItemRequest,
  ApplyPromotionalCodeRequest,
} from '../../types/cart';

// ============================================================================
// Test Data Factories
// ============================================================================

const createMockCart = (overrides?: Partial<Cart>): Cart => ({
  id: 'cart-123',
  userId: 'user-456',
  items: [],
  itemCount: 0,
  subtotal: 0,
  tax: 0,
  total: 0,
  status: 'active',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
  ...overrides,
});

const createMockCartItem = (id: string) => ({
  id,
  cartId: 'cart-123',
  vehicleId: 'vehicle-789',
  configurationId: 'config-101',
  quantity: 1,
  unitPrice: 50000,
  totalPrice: 50000,
  status: 'active' as const,
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
});

const createAddToCartRequest = (): AddToCartRequest => ({
  vehicleId: 'vehicle-789',
  configurationId: 'config-101',
  quantity: 1,
});

const createUpdateCartItemRequest = (): UpdateCartItemRequest => ({
  quantity: 2,
});

const createApplyPromoCodeRequest = (): ApplyPromotionalCodeRequest => ({
  code: 'SAVE20',
});

// ============================================================================
// Test Utilities
// ============================================================================

const createWrapper = () => {
  const queryClient = new QueryClient({
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

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const setupFetchMock = (response: unknown, options?: { status?: number; ok?: boolean }) => {
  const mockResponse = {
    ok: options?.ok ?? true,
    status: options?.status ?? 200,
    statusText: options?.status === 404 ? 'Not Found' : 'OK',
    json: vi.fn().mockResolvedValue(response),
  };

  global.fetch = vi.fn().mockResolvedValue(mockResponse);
  return mockResponse;
};

const setupFetchError = (error: Error) => {
  global.fetch = vi.fn().mockRejectedValue(error);
};

const setupFetchTimeout = () => {
  const abortError = new Error('The operation was aborted');
  abortError.name = 'AbortError';
  global.fetch = vi.fn().mockRejectedValue(abortError);
};

// ============================================================================
// Unit Tests: Query Keys
// ============================================================================

describe('cartKeys', () => {
  it('should generate correct query key structure', () => {
    expect(cartKeys.all).toEqual(['cart']);
    expect(cartKeys.detail()).toEqual(['cart', 'detail']);
  });

  it('should maintain referential equality for static keys', () => {
    const keys1 = cartKeys.all;
    const keys2 = cartKeys.all;
    expect(keys1).toBe(keys2);
  });

  it('should generate new arrays for detail keys', () => {
    const keys1 = cartKeys.detail();
    const keys2 = cartKeys.detail();
    expect(keys1).toEqual(keys2);
    expect(keys1).not.toBe(keys2);
  });
});

// ============================================================================
// Unit Tests: CartApiError
// ============================================================================

describe('CartApiError', () => {
  it('should create error with message and status code', () => {
    const error = new CartApiError('Test error', 400);

    expect(error.message).toBe('Test error');
    expect(error.statusCode).toBe(400);
    expect(error.name).toBe('CartApiError');
    expect(error).toBeInstanceOf(Error);
  });

  it('should include cart error details', () => {
    const cartError = {
      code: 'INVALID_QUANTITY',
      message: 'Quantity must be positive',
      details: { min: 1 },
    };

    const error = new CartApiError('Validation failed', 400, cartError);

    expect(error.cartError).toEqual(cartError);
  });

  it('should include additional details', () => {
    const details = { field: 'quantity', value: -1 };
    const error = new CartApiError('Invalid input', 400, undefined, details);

    expect(error.details).toEqual(details);
  });

  it('should be identifiable by type guard', () => {
    const error = new CartApiError('Test', 500);
    expect(isCartApiError(error)).toBe(true);
  });
});

// ============================================================================
// Unit Tests: Type Guards
// ============================================================================

describe('isCartApiError', () => {
  it('should return true for CartApiError instances', () => {
    const error = new CartApiError('Test', 500);
    expect(isCartApiError(error)).toBe(true);
  });

  it('should return false for regular Error instances', () => {
    const error = new Error('Test');
    expect(isCartApiError(error)).toBe(false);
  });

  it('should return false for non-error values', () => {
    expect(isCartApiError(null)).toBe(false);
    expect(isCartApiError(undefined)).toBe(false);
    expect(isCartApiError('error')).toBe(false);
    expect(isCartApiError({ message: 'error' })).toBe(false);
  });
});

// ============================================================================
// Integration Tests: useCart Hook
// ============================================================================

describe('useCart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should fetch cart successfully', async () => {
    const mockCart = createMockCart();
    setupFetchMock(mockCart);

    const { result } = renderHook(() => useCart(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockCart);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/cart'),
      expect.objectContaining({
        method: 'GET',
        credentials: 'include',
      }),
    );
  });

  it('should handle loading state', () => {
    setupFetchMock(createMockCart());

    const { result } = renderHook(() => useCart(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it('should handle error state', async () => {
    setupFetchMock(
      { error: { code: 'NOT_FOUND', message: 'Cart not found' } },
      { ok: false, status: 404 },
    );

    const { result } = renderHook(() => useCart(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeInstanceOf(CartApiError);
    expect((result.current.error as CartApiError).statusCode).toBe(404);
  });

  it('should retry failed requests', async () => {
    let callCount = 0;
    global.fetch = vi.fn().mockImplementation(() => {
      callCount++;
      if (callCount < 3) {
        return Promise.reject(new Error('Network error'));
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(createMockCart()),
      });
    });

    const { result } = renderHook(() => useCart(), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => {
        expect(result.current.isSuccess).toBe(true);
      },
      { timeout: 5000 },
    );

    expect(callCount).toBe(3);
  });

  it('should handle timeout errors', async () => {
    setupFetchTimeout();

    const { result } = renderHook(() => useCart(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    const error = result.current.error as CartApiError;
    expect(error.statusCode).toBe(408);
    expect(error.message).toBe('Request timeout');
  });

  it('should handle malformed JSON responses', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.reject(new Error('Invalid JSON')),
    });

    const { result } = renderHook(() => useCart(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    const error = result.current.error as CartApiError;
    expect(error.message).toBe('Failed to parse response JSON');
    expect(error.statusCode).toBe(500);
  });
});

// ============================================================================
// Integration Tests: useAddToCart Hook
// ============================================================================

describe('useAddToCart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should add item to cart successfully', async () => {
    const mockCart = createMockCart({
      items: [createMockCartItem('item-1')],
      itemCount: 1,
    });

    setupFetchMock({ cart: mockCart, message: 'Item added' });

    const { result } = renderHook(() => useAddToCart(), {
      wrapper: createWrapper(),
    });

    const request = createAddToCartRequest();
    result.current.mutate(request);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.cart).toEqual(mockCart);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/cart/items'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(request),
      }),
    );
  });

  it('should perform optimistic update', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    const initialCart = createMockCart({ items: [], itemCount: 0 });
    queryClient.setQueryData(cartKeys.detail(), initialCart);

    setupFetchMock({ cart: createMockCart(), message: 'Added' });

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useAddToCart(), { wrapper });

    result.current.mutate(createAddToCartRequest());

    // Check optimistic update
    const optimisticCart = queryClient.getQueryData<Cart>(cartKeys.detail());
    expect(optimisticCart?.itemCount).toBe(1);
    expect(optimisticCart?.items).toHaveLength(1);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it('should rollback on error', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    const initialCart = createMockCart({ items: [], itemCount: 0 });
    queryClient.setQueryData(cartKeys.detail(), initialCart);

    setupFetchMock(
      { error: { code: 'OUT_OF_STOCK', message: 'Item out of stock' } },
      { ok: false, status: 400 },
    );

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useAddToCart(), { wrapper });

    result.current.mutate(createAddToCartRequest());

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    // Verify rollback
    const currentCart = queryClient.getQueryData<Cart>(cartKeys.detail());
    expect(currentCart).toEqual(initialCart);
  });

  it('should handle validation errors', async () => {
    setupFetchMock(
      {
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Invalid quantity',
          details: { field: 'quantity', min: 1 },
        },
      },
      { ok: false, status: 400 },
    );

    const { result } = renderHook(() => useAddToCart(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(createAddToCartRequest());

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    const error = result.current.error as CartApiError;
    expect(error.cartError?.code).toBe('VALIDATION_ERROR');
    expect(error.cartError?.details).toEqual({ field: 'quantity', min: 1 });
  });
});

// ============================================================================
// Integration Tests: useUpdateCartItem Hook
// ============================================================================

describe('useUpdateCartItem', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should update cart item successfully', async () => {
    const updatedCart = createMockCart({
      items: [{ ...createMockCartItem('item-1'), quantity: 2, totalPrice: 100000 }],
    });

    setupFetchMock({ cart: updatedCart, message: 'Updated' });

    const { result } = renderHook(() => useUpdateCartItem(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      itemId: 'item-1',
      request: createUpdateCartItemRequest(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.cart).toEqual(updatedCart);
  });

  it('should perform optimistic update for quantity change', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    const initialCart = createMockCart({
      items: [createMockCartItem('item-1')],
      itemCount: 1,
    });
    queryClient.setQueryData(cartKeys.detail(), initialCart);

    setupFetchMock({ cart: createMockCart(), message: 'Updated' });

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useUpdateCartItem(), { wrapper });

    result.current.mutate({
      itemId: 'item-1',
      request: { quantity: 3 },
    });

    // Check optimistic update
    const optimisticCart = queryClient.getQueryData<Cart>(cartKeys.detail());
    const updatedItem = optimisticCart?.items.find((item) => item.id === 'item-1');
    expect(updatedItem?.quantity).toBe(3);
    expect(updatedItem?.totalPrice).toBe(150000); // 50000 * 3

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it('should handle item not found error', async () => {
    setupFetchMock(
      { error: { code: 'NOT_FOUND', message: 'Cart item not found' } },
      { ok: false, status: 404 },
    );

    const { result } = renderHook(() => useUpdateCartItem(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      itemId: 'nonexistent',
      request: createUpdateCartItemRequest(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    const error = result.current.error as CartApiError;
    expect(error.statusCode).toBe(404);
  });
});

// ============================================================================
// Integration Tests: useRemoveCartItem Hook
// ============================================================================

describe('useRemoveCartItem', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should remove cart item successfully', async () => {
    const updatedCart = createMockCart({ items: [], itemCount: 0 });
    setupFetchMock({ cart: updatedCart, message: 'Removed' });

    const { result } = renderHook(() => useRemoveCartItem(), {
      wrapper: createWrapper(),
    });

    result.current.mutate('item-1');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.cart).toEqual(updatedCart);
  });

  it('should perform optimistic removal', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    const initialCart = createMockCart({
      items: [createMockCartItem('item-1'), createMockCartItem('item-2')],
      itemCount: 2,
    });
    queryClient.setQueryData(cartKeys.detail(), initialCart);

    setupFetchMock({ cart: createMockCart(), message: 'Removed' });

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useRemoveCartItem(), { wrapper });

    result.current.mutate('item-1');

    // Check optimistic removal
    const optimisticCart = queryClient.getQueryData<Cart>(cartKeys.detail());
    expect(optimisticCart?.items).toHaveLength(1);
    expect(optimisticCart?.items[0]?.id).toBe('item-2');
    expect(optimisticCart?.itemCount).toBe(1);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it('should rollback on removal error', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    const initialCart = createMockCart({
      items: [createMockCartItem('item-1')],
      itemCount: 1,
    });
    queryClient.setQueryData(cartKeys.detail(), initialCart);

    setupFetchMock(
      { error: { code: 'FORBIDDEN', message: 'Cannot remove item' } },
      { ok: false, status: 403 },
    );

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useRemoveCartItem(), { wrapper });

    result.current.mutate('item-1');

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    // Verify rollback
    const currentCart = queryClient.getQueryData<Cart>(cartKeys.detail());
    expect(currentCart).toEqual(initialCart);
  });
});

// ============================================================================
// Integration Tests: useApplyPromoCode Hook
// ============================================================================

describe('useApplyPromoCode', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should apply promo code successfully', async () => {
    const updatedCart = createMockCart({
      promotionalCode: 'SAVE20',
      discount: 10000,
      total: 40000,
    });

    setupFetchMock({ cart: updatedCart, message: 'Promo code applied' });

    const { result } = renderHook(() => useApplyPromoCode(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(createApplyPromoCodeRequest());

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.cart.promotionalCode).toBe('SAVE20');
  });

  it('should perform optimistic update with promo code', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    const initialCart = createMockCart();
    queryClient.setQueryData(cartKeys.detail(), initialCart);

    setupFetchMock({ cart: createMockCart(), message: 'Applied' });

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useApplyPromoCode(), { wrapper });

    result.current.mutate({ code: 'SAVE20' });

    // Check optimistic update
    const optimisticCart = queryClient.getQueryData<Cart>(cartKeys.detail());
    expect(optimisticCart?.promotionalCode).toBe('SAVE20');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it('should handle invalid promo code error', async () => {
    setupFetchMock(
      {
        error: {
          code: 'INVALID_PROMO_CODE',
          message: 'Promotional code is invalid or expired',
        },
      },
      { ok: false, status: 400 },
    );

    const { result } = renderHook(() => useApplyPromoCode(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(createApplyPromoCodeRequest());

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    const error = result.current.error as CartApiError;
    expect(error.cartError?.code).toBe('INVALID_PROMO_CODE');
  });

  it('should rollback on promo code error', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    const initialCart = createMockCart({ promotionalCode: undefined });
    queryClient.setQueryData(cartKeys.detail(), initialCart);

    setupFetchMock(
      { error: { code: 'EXPIRED', message: 'Code expired' } },
      { ok: false, status: 400 },
    );

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useApplyPromoCode(), { wrapper });

    result.current.mutate({ code: 'EXPIRED20' });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    // Verify rollback
    const currentCart = queryClient.getQueryData<Cart>(cartKeys.detail());
    expect(currentCart?.promotionalCode).toBeUndefined();
  });
});

// ============================================================================
// Edge Case Tests
// ============================================================================

describe('Edge Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should handle empty cart response', async () => {
    const emptyCart = createMockCart({ items: [], itemCount: 0 });
    setupFetchMock(emptyCart);

    const { result } = renderHook(() => useCart(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.items).toEqual([]);
    expect(result.current.data?.itemCount).toBe(0);
  });

  it('should handle network errors gracefully', async () => {
    setupFetchError(new Error('Network connection failed'));

    const { result } = renderHook(() => useCart(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    const error = result.current.error as CartApiError;
    expect(error.statusCode).toBe(500);
  });

  it('should handle concurrent mutations', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    const initialCart = createMockCart({
      items: [createMockCartItem('item-1')],
      itemCount: 1,
    });
    queryClient.setQueryData(cartKeys.detail(), initialCart);

    setupFetchMock({ cart: createMockCart(), message: 'Success' });

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result: addResult } = renderHook(() => useAddToCart(), { wrapper });
    const { result: updateResult } = renderHook(() => useUpdateCartItem(), { wrapper });

    // Trigger concurrent mutations
    addResult.current.mutate(createAddToCartRequest());
    updateResult.current.mutate({
      itemId: 'item-1',
      request: { quantity: 2 },
    });

    await waitFor(() => {
      expect(addResult.current.isSuccess || addResult.current.isError).toBe(true);
      expect(updateResult.current.isSuccess || updateResult.current.isError).toBe(true);
    });
  });

  it('should handle server 500 errors', async () => {
    setupFetchMock(
      { error: 'Internal server error' },
      { ok: false, status: 500 },
    );

    const { result } = renderHook(() => useCart(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    const error = result.current.error as CartApiError;
    expect(error.statusCode).toBe(500);
  });

  it('should handle missing environment variables', () => {
    const originalEnv = import.meta.env['VITE_API_BASE_URL'];
    delete import.meta.env['VITE_API_BASE_URL'];

    setupFetchMock(createMockCart());

    const { result } = renderHook(() => useCart(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    // Restore
    import.meta.env['VITE_API_BASE_URL'] = originalEnv;
  });
});

// ============================================================================
// Performance Tests
// ============================================================================

describe('Performance', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should complete fetch within timeout threshold', async () => {
    setupFetchMock(createMockCart());

    const startTime = Date.now();
    const { result } = renderHook(() => useCart(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const duration = Date.now() - startTime;
    expect(duration).toBeLessThan(5000); // Should complete within 5 seconds
  });

  it('should handle large cart with many items', async () => {
    const largeCart = createMockCart({
      items: Array.from({ length: 100 }, (_, i) => createMockCartItem(`item-${i}`)),
      itemCount: 100,
    });

    setupFetchMock(largeCart);

    const { result } = renderHook(() => useCart(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.items).toHaveLength(100);
  });
});