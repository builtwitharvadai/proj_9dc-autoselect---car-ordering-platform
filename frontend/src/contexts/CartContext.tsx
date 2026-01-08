/**
 * CartContext - React Context for cart state management
 * Provides local cart state, optimistic update handlers, and cart operations
 * with React Query integration for server state synchronization
 */

import {
  createContext,
  useContext,
  useCallback,
  useMemo,
  useReducer,
  useEffect,
  type ReactNode,
} from 'react';
import { useQueryClient, useMutation, useQuery } from '@tanstack/react-query';
import type {
  Cart,
  CartItem,
  AddToCartRequest,
  UpdateCartItemRequest,
  ApplyPromotionalCodeRequest,
  CartError,
  CartValidationResult,
} from '../types/cart';

/**
 * Cart action types for reducer
 */
type CartAction =
  | { type: 'SET_CART'; payload: Cart }
  | { type: 'ADD_ITEM_OPTIMISTIC'; payload: { item: CartItem; tempId: string } }
  | { type: 'UPDATE_ITEM_OPTIMISTIC'; payload: { itemId: string; quantity: number } }
  | { type: 'REMOVE_ITEM_OPTIMISTIC'; payload: { itemId: string } }
  | { type: 'APPLY_PROMO_OPTIMISTIC'; payload: { code: string } }
  | { type: 'ROLLBACK_OPTIMISTIC'; payload: Cart }
  | { type: 'SET_ERROR'; payload: CartError | null }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'CLEAR_CART' };

/**
 * Cart state interface
 */
interface CartState {
  readonly cart: Cart | null;
  readonly isLoading: boolean;
  readonly error: CartError | null;
  readonly optimisticUpdates: Map<string, Cart>;
}

/**
 * Cart context value interface
 */
interface CartContextValue {
  readonly cart: Cart | null;
  readonly isLoading: boolean;
  readonly error: CartError | null;
  readonly itemCount: number;
  readonly subtotal: number;
  readonly total: number;
  readonly hasItems: boolean;
  readonly hasPromotionalCode: boolean;
  readonly validation: CartValidationResult | null;
  readonly addToCart: (request: AddToCartRequest) => Promise<void>;
  readonly updateCartItem: (itemId: string, request: UpdateCartItemRequest) => Promise<void>;
  readonly removeCartItem: (itemId: string) => Promise<void>;
  readonly applyPromotionalCode: (request: ApplyPromotionalCodeRequest) => Promise<void>;
  readonly removePromotionalCode: () => Promise<void>;
  readonly clearCart: () => void;
  readonly refreshCart: () => Promise<void>;
}

/**
 * Cart provider props
 */
interface CartProviderProps {
  readonly children: ReactNode;
  readonly userId?: string;
  readonly sessionId?: string;
  readonly enableOptimisticUpdates?: boolean;
  readonly enableAutoRefresh?: boolean;
  readonly autoRefreshInterval?: number;
}

/**
 * API base URL from environment
 */
const API_BASE_URL = import.meta.env['VITE_API_BASE_URL'] ?? 'http://localhost:8000';

/**
 * Cart API endpoints
 */
const CART_ENDPOINTS = {
  getCart: `${API_BASE_URL}/api/v1/cart`,
  addItem: `${API_BASE_URL}/api/v1/cart/items`,
  updateItem: (itemId: string) => `${API_BASE_URL}/api/v1/cart/items/${itemId}`,
  removeItem: (itemId: string) => `${API_BASE_URL}/api/v1/cart/items/${itemId}`,
  applyPromo: `${API_BASE_URL}/api/v1/cart/promotional-code`,
  removePromo: `${API_BASE_URL}/api/v1/cart/promotional-code`,
} as const;

/**
 * Cart query keys
 */
const cartKeys = {
  all: ['cart'] as const,
  detail: (userId?: string, sessionId?: string) =>
    [...cartKeys.all, 'detail', { userId, sessionId }] as const,
} as const;

/**
 * Initial cart state
 */
const initialState: CartState = {
  cart: null,
  isLoading: false,
  error: null,
  optimisticUpdates: new Map(),
};

/**
 * Cart reducer for state management
 */
function cartReducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case 'SET_CART':
      return {
        ...state,
        cart: action.payload,
        error: null,
        optimisticUpdates: new Map(),
      };

    case 'ADD_ITEM_OPTIMISTIC': {
      if (!state.cart) {
        return state;
      }

      const optimisticCart: Cart = {
        ...state.cart,
        items: [...state.cart.items, action.payload.item],
        itemCount: state.cart.itemCount + action.payload.item.quantity,
        subtotal: state.cart.subtotal + action.payload.item.totalPrice,
        total: state.cart.total + action.payload.item.totalPrice,
        updatedAt: new Date().toISOString(),
      };

      const updates = new Map(state.optimisticUpdates);
      updates.set(action.payload.tempId, state.cart);

      return {
        ...state,
        cart: optimisticCart,
        optimisticUpdates: updates,
      };
    }

    case 'UPDATE_ITEM_OPTIMISTIC': {
      if (!state.cart) {
        return state;
      }

      const itemIndex = state.cart.items.findIndex((item) => item.id === action.payload.itemId);
      if (itemIndex === -1) {
        return state;
      }

      const item = state.cart.items[itemIndex];
      if (!item) {
        return state;
      }

      const quantityDelta = action.payload.quantity - item.quantity;
      const priceDelta = item.unitPrice * quantityDelta;

      const updatedItems = [...state.cart.items];
      updatedItems[itemIndex] = {
        ...item,
        quantity: action.payload.quantity,
        totalPrice: item.unitPrice * action.payload.quantity,
        updatedAt: new Date().toISOString(),
      };

      const optimisticCart: Cart = {
        ...state.cart,
        items: updatedItems,
        itemCount: state.cart.itemCount + quantityDelta,
        subtotal: state.cart.subtotal + priceDelta,
        total: state.cart.total + priceDelta,
        updatedAt: new Date().toISOString(),
      };

      const updates = new Map(state.optimisticUpdates);
      updates.set(action.payload.itemId, state.cart);

      return {
        ...state,
        cart: optimisticCart,
        optimisticUpdates: updates,
      };
    }

    case 'REMOVE_ITEM_OPTIMISTIC': {
      if (!state.cart) {
        return state;
      }

      const item = state.cart.items.find((i) => i.id === action.payload.itemId);
      if (!item) {
        return state;
      }

      const optimisticCart: Cart = {
        ...state.cart,
        items: state.cart.items.filter((i) => i.id !== action.payload.itemId),
        itemCount: state.cart.itemCount - item.quantity,
        subtotal: state.cart.subtotal - item.totalPrice,
        total: state.cart.total - item.totalPrice,
        updatedAt: new Date().toISOString(),
      };

      const updates = new Map(state.optimisticUpdates);
      updates.set(action.payload.itemId, state.cart);

      return {
        ...state,
        cart: optimisticCart,
        optimisticUpdates: updates,
      };
    }

    case 'APPLY_PROMO_OPTIMISTIC': {
      if (!state.cart) {
        return state;
      }

      const optimisticCart: Cart = {
        ...state.cart,
        promotionalCode: action.payload.code,
        updatedAt: new Date().toISOString(),
      };

      const updates = new Map(state.optimisticUpdates);
      updates.set('promo', state.cart);

      return {
        ...state,
        cart: optimisticCart,
        optimisticUpdates: updates,
      };
    }

    case 'ROLLBACK_OPTIMISTIC':
      return {
        ...state,
        cart: action.payload,
        optimisticUpdates: new Map(),
      };

    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
      };

    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      };

    case 'CLEAR_CART':
      return {
        ...state,
        cart: null,
        error: null,
        optimisticUpdates: new Map(),
      };

    default:
      return state;
  }
}

/**
 * Cart context
 */
const CartContext = createContext<CartContextValue | undefined>(undefined);

/**
 * Fetch cart from API
 */
async function fetchCart(userId?: string, sessionId?: string): Promise<Cart> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (userId) {
    headers['Authorization'] = `Bearer ${userId}`;
  }

  const params = new URLSearchParams();
  if (sessionId) {
    params.set('session_id', sessionId);
  }

  const url = `${CART_ENDPOINTS.getCart}${params.toString() ? `?${params.toString()}` : ''}`;

  const response = await fetch(url, {
    method: 'GET',
    headers,
    credentials: 'include',
  });

  if (!response.ok) {
    const error = (await response.json()) as { message?: string };
    throw new Error(error.message ?? 'Failed to fetch cart');
  }

  return response.json() as Promise<Cart>;
}

/**
 * Add item to cart via API
 */
async function addItemToCart(
  request: AddToCartRequest,
  userId?: string,
  sessionId?: string,
): Promise<Cart> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (userId) {
    headers['Authorization'] = `Bearer ${userId}`;
  }

  const params = new URLSearchParams();
  if (sessionId) {
    params.set('session_id', sessionId);
  }

  const url = `${CART_ENDPOINTS.addItem}${params.toString() ? `?${params.toString()}` : ''}`;

  const response = await fetch(url, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = (await response.json()) as { message?: string };
    throw new Error(error.message ?? 'Failed to add item to cart');
  }

  const result = (await response.json()) as { cart: Cart };
  return result.cart;
}

/**
 * Update cart item via API
 */
async function updateItemInCart(
  itemId: string,
  request: UpdateCartItemRequest,
  userId?: string,
  sessionId?: string,
): Promise<Cart> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (userId) {
    headers['Authorization'] = `Bearer ${userId}`;
  }

  const params = new URLSearchParams();
  if (sessionId) {
    params.set('session_id', sessionId);
  }

  const url = `${CART_ENDPOINTS.updateItem(itemId)}${params.toString() ? `?${params.toString()}` : ''}`;

  const response = await fetch(url, {
    method: 'PATCH',
    headers,
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = (await response.json()) as { message?: string };
    throw new Error(error.message ?? 'Failed to update cart item');
  }

  const result = (await response.json()) as { cart: Cart };
  return result.cart;
}

/**
 * Remove item from cart via API
 */
async function removeItemFromCart(
  itemId: string,
  userId?: string,
  sessionId?: string,
): Promise<Cart> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (userId) {
    headers['Authorization'] = `Bearer ${userId}`;
  }

  const params = new URLSearchParams();
  if (sessionId) {
    params.set('session_id', sessionId);
  }

  const url = `${CART_ENDPOINTS.removeItem(itemId)}${params.toString() ? `?${params.toString()}` : ''}`;

  const response = await fetch(url, {
    method: 'DELETE',
    headers,
    credentials: 'include',
  });

  if (!response.ok) {
    const error = (await response.json()) as { message?: string };
    throw new Error(error.message ?? 'Failed to remove cart item');
  }

  const result = (await response.json()) as { cart: Cart };
  return result.cart;
}

/**
 * Apply promotional code via API
 */
async function applyPromoCode(
  request: ApplyPromotionalCodeRequest,
  userId?: string,
  sessionId?: string,
): Promise<Cart> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (userId) {
    headers['Authorization'] = `Bearer ${userId}`;
  }

  const params = new URLSearchParams();
  if (sessionId) {
    params.set('session_id', sessionId);
  }

  const url = `${CART_ENDPOINTS.applyPromo}${params.toString() ? `?${params.toString()}` : ''}`;

  const response = await fetch(url, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = (await response.json()) as { message?: string };
    throw new Error(error.message ?? 'Failed to apply promotional code');
  }

  const result = (await response.json()) as { cart: Cart };
  return result.cart;
}

/**
 * Remove promotional code via API
 */
async function removePromoCode(userId?: string, sessionId?: string): Promise<Cart> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (userId) {
    headers['Authorization'] = `Bearer ${userId}`;
  }

  const params = new URLSearchParams();
  if (sessionId) {
    params.set('session_id', sessionId);
  }

  const url = `${CART_ENDPOINTS.removePromo}${params.toString() ? `?${params.toString()}` : ''}`;

  const response = await fetch(url, {
    method: 'DELETE',
    headers,
    credentials: 'include',
  });

  if (!response.ok) {
    const error = (await response.json()) as { message?: string };
    throw new Error(error.message ?? 'Failed to remove promotional code');
  }

  const result = (await response.json()) as { cart: Cart };
  return result.cart;
}

/**
 * Cart provider component
 */
export function CartProvider({
  children,
  userId,
  sessionId,
  enableOptimisticUpdates = true,
  enableAutoRefresh = true,
  autoRefreshInterval = 60000,
}: CartProviderProps): JSX.Element {
  const [state, dispatch] = useReducer(cartReducer, initialState);
  const queryClient = useQueryClient();

  const queryKey = useMemo(() => cartKeys.detail(userId, sessionId), [userId, sessionId]);

  const { data: cartData, refetch } = useQuery({
    queryKey,
    queryFn: () => fetchCart(userId, sessionId),
    staleTime: 30000,
    refetchOnWindowFocus: enableAutoRefresh,
    refetchInterval: enableAutoRefresh ? autoRefreshInterval : false,
  });

  useEffect(() => {
    if (cartData) {
      dispatch({ type: 'SET_CART', payload: cartData });
    }
  }, [cartData]);

  const addToCartMutation = useMutation({
    mutationFn: (request: AddToCartRequest) => addItemToCart(request, userId, sessionId),
    onMutate: async (request) => {
      if (!enableOptimisticUpdates || !state.cart) {
        return;
      }

      await queryClient.cancelQueries({ queryKey });

      const tempId = `temp-${Date.now()}`;
      const optimisticItem: CartItem = {
        id: tempId,
        cartId: state.cart.id,
        vehicleId: request.vehicleId,
        configurationId: request.configurationId,
        quantity: request.quantity,
        unitPrice: 0,
        totalPrice: 0,
        status: 'active',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      dispatch({ type: 'ADD_ITEM_OPTIMISTIC', payload: { item: optimisticItem, tempId } });
    },
    onSuccess: (cart) => {
      dispatch({ type: 'SET_CART', payload: cart });
      void queryClient.invalidateQueries({ queryKey });
    },
    onError: (_error, _variables, context) => {
      if (context && state.optimisticUpdates.size > 0) {
        const previousCart = Array.from(state.optimisticUpdates.values())[0];
        if (previousCart) {
          dispatch({ type: 'ROLLBACK_OPTIMISTIC', payload: previousCart });
        }
      }
      dispatch({
        type: 'SET_ERROR',
        payload: {
          type: 'VALIDATION_ERROR',
          message: 'Failed to add item to cart',
        },
      });
    },
  });

  const updateCartItemMutation = useMutation({
    mutationFn: ({ itemId, request }: { itemId: string; request: UpdateCartItemRequest }) =>
      updateItemInCart(itemId, request, userId, sessionId),
    onMutate: async ({ itemId, request }) => {
      if (!enableOptimisticUpdates) {
        return;
      }

      await queryClient.cancelQueries({ queryKey });

      dispatch({
        type: 'UPDATE_ITEM_OPTIMISTIC',
        payload: { itemId, quantity: request.quantity },
      });
    },
    onSuccess: (cart) => {
      dispatch({ type: 'SET_CART', payload: cart });
      void queryClient.invalidateQueries({ queryKey });
    },
    onError: (_error, { itemId }) => {
      const previousCart = state.optimisticUpdates.get(itemId);
      if (previousCart) {
        dispatch({ type: 'ROLLBACK_OPTIMISTIC', payload: previousCart });
      }
      dispatch({
        type: 'SET_ERROR',
        payload: {
          type: 'VALIDATION_ERROR',
          message: 'Failed to update cart item',
        },
      });
    },
  });

  const removeCartItemMutation = useMutation({
    mutationFn: (itemId: string) => removeItemFromCart(itemId, userId, sessionId),
    onMutate: async (itemId) => {
      if (!enableOptimisticUpdates) {
        return;
      }

      await queryClient.cancelQueries({ queryKey });

      dispatch({ type: 'REMOVE_ITEM_OPTIMISTIC', payload: { itemId } });
    },
    onSuccess: (cart) => {
      dispatch({ type: 'SET_CART', payload: cart });
      void queryClient.invalidateQueries({ queryKey });
    },
    onError: (_error, itemId) => {
      const previousCart = state.optimisticUpdates.get(itemId);
      if (previousCart) {
        dispatch({ type: 'ROLLBACK_OPTIMISTIC', payload: previousCart });
      }
      dispatch({
        type: 'SET_ERROR',
        payload: {
          type: 'VALIDATION_ERROR',
          message: 'Failed to remove cart item',
        },
      });
    },
  });

  const applyPromoMutation = useMutation({
    mutationFn: (request: ApplyPromotionalCodeRequest) =>
      applyPromoCode(request, userId, sessionId),
    onMutate: async (request) => {
      if (!enableOptimisticUpdates) {
        return;
      }

      await queryClient.cancelQueries({ queryKey });

      dispatch({ type: 'APPLY_PROMO_OPTIMISTIC', payload: { code: request.code } });
    },
    onSuccess: (cart) => {
      dispatch({ type: 'SET_CART', payload: cart });
      void queryClient.invalidateQueries({ queryKey });
    },
    onError: () => {
      const previousCart = state.optimisticUpdates.get('promo');
      if (previousCart) {
        dispatch({ type: 'ROLLBACK_OPTIMISTIC', payload: previousCart });
      }
      dispatch({
        type: 'SET_ERROR',
        payload: {
          type: 'INVALID_PROMOTIONAL_CODE',
          message: 'Failed to apply promotional code',
        },
      });
    },
  });

  const removePromoMutation = useMutation({
    mutationFn: () => removePromoCode(userId, sessionId),
    onSuccess: (cart) => {
      dispatch({ type: 'SET_CART', payload: cart });
      void queryClient.invalidateQueries({ queryKey });
    },
    onError: () => {
      dispatch({
        type: 'SET_ERROR',
        payload: {
          type: 'VALIDATION_ERROR',
          message: 'Failed to remove promotional code',
        },
      });
    },
  });

  const addToCart = useCallback(
    async (request: AddToCartRequest) => {
      await addToCartMutation.mutateAsync(request);
    },
    [addToCartMutation],
  );

  const updateCartItem = useCallback(
    async (itemId: string, request: UpdateCartItemRequest) => {
      await updateCartItemMutation.mutateAsync({ itemId, request });
    },
    [updateCartItemMutation],
  );

  const removeCartItem = useCallback(
    async (itemId: string) => {
      await removeCartItemMutation.mutateAsync(itemId);
    },
    [removeCartItemMutation],
  );

  const applyPromotionalCode = useCallback(
    async (request: ApplyPromotionalCodeRequest) => {
      await applyPromoMutation.mutateAsync(request);
    },
    [applyPromoMutation],
  );

  const removePromotionalCode = useCallback(async () => {
    await removePromoMutation.mutateAsync();
  }, [removePromoMutation]);

  const clearCart = useCallback(() => {
    dispatch({ type: 'CLEAR_CART' });
  }, []);

  const refreshCart = useCallback(async () => {
    await refetch();
  }, [refetch]);

  const value = useMemo<CartContextValue>(
    () => ({
      cart: state.cart,
      isLoading: state.isLoading,
      error: state.error,
      itemCount: state.cart?.itemCount ?? 0,
      subtotal: state.cart?.subtotal ?? 0,
      total: state.cart?.total ?? 0,
      hasItems: (state.cart?.items.length ?? 0) > 0,
      hasPromotionalCode: Boolean(state.cart?.promotionalCode),
      validation: null,
      addToCart,
      updateCartItem,
      removeCartItem,
      applyPromotionalCode,
      removePromotionalCode,
      clearCart,
      refreshCart,
    }),
    [
      state.cart,
      state.isLoading,
      state.error,
      addToCart,
      updateCartItem,
      removeCartItem,
      applyPromotionalCode,
      removePromotionalCode,
      clearCart,
      refreshCart,
    ],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

/**
 * Hook to use cart context
 */
export function useCart(): CartContextValue {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
}