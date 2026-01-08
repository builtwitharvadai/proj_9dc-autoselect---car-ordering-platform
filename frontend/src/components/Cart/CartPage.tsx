/**
 * CartPage - Main shopping cart interface component
 * Displays cart items, promotional code section, cart summary, and checkout button
 * Includes empty cart state and comprehensive loading/error states
 */

import { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../../contexts/CartContext';
import type { CartItem } from '../../types/cart';

/**
 * Cart page component props
 */
interface CartPageProps {
  readonly className?: string;
  readonly onCheckout?: () => void;
  readonly enablePromoCode?: boolean;
  readonly showEmptyState?: boolean;
}

/**
 * Promotional code form state
 */
interface PromoCodeState {
  readonly code: string;
  readonly isApplying: boolean;
  readonly error: string | null;
}

/**
 * Cart item action state for optimistic updates
 */
interface ItemActionState {
  readonly itemId: string;
  readonly action: 'update' | 'remove';
  readonly isProcessing: boolean;
}

/**
 * Format currency value
 */
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/**
 * Cart item component
 */
function CartItemRow({
  item,
  onQuantityChange,
  onRemove,
  isProcessing,
}: {
  readonly item: CartItem;
  readonly onQuantityChange: (itemId: string, quantity: number) => Promise<void>;
  readonly onRemove: (itemId: string) => Promise<void>;
  readonly isProcessing: boolean;
}): JSX.Element {
  const [quantity, setQuantity] = useState(item.quantity);
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false);

  const handleQuantityChange = useCallback(
    async (newQuantity: number) => {
      if (newQuantity < 1 || newQuantity > 99) {
        return;
      }

      setQuantity(newQuantity);
      await onQuantityChange(item.id, newQuantity);
    },
    [item.id, onQuantityChange],
  );

  const handleRemove = useCallback(async () => {
    setShowRemoveConfirm(false);
    await onRemove(item.id);
  }, [item.id, onRemove]);

  return (
    <div className="flex flex-col gap-4 border-b border-gray-200 py-6 last:border-b-0">
      <div className="flex gap-4">
        {/* Item Image */}
        <div className="h-24 w-24 flex-shrink-0 overflow-hidden rounded-md border border-gray-200">
          <div className="h-full w-full bg-gray-100 flex items-center justify-center">
            <svg
              className="h-12 w-12 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
        </div>

        {/* Item Details */}
        <div className="flex flex-1 flex-col">
          <div className="flex justify-between">
            <div>
              <h3 className="text-base font-medium text-gray-900">
                Vehicle Configuration #{item.configurationId?.slice(0, 8) ?? item.vehicleId.slice(0, 8)}
              </h3>
              <p className="mt-1 text-sm text-gray-500">Vehicle ID: {item.vehicleId.slice(0, 8)}</p>
              {item.configurationId && (
                <p className="mt-1 text-sm text-gray-500">Config ID: {item.configurationId.slice(0, 8)}</p>
              )}
            </div>
            <p className="text-base font-medium text-gray-900">{formatCurrency(item.totalPrice)}</p>
          </div>

          {/* Quantity Controls */}
          <div className="mt-4 flex items-center gap-4">
            <div className="flex items-center gap-2">
              <label htmlFor={`quantity-${item.id}`} className="text-sm text-gray-700">
                Quantity:
              </label>
              <div className="flex items-center border border-gray-300 rounded-md">
                <button
                  type="button"
                  onClick={() => handleQuantityChange(quantity - 1)}
                  disabled={isProcessing || quantity <= 1}
                  className="px-3 py-1 text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Decrease quantity"
                >
                  −
                </button>
                <input
                  id={`quantity-${item.id}`}
                  type="number"
                  min="1"
                  max="99"
                  value={quantity}
                  onChange={(e) => {
                    const value = parseInt(e.target.value, 10);
                    if (!isNaN(value)) {
                      void handleQuantityChange(value);
                    }
                  }}
                  disabled={isProcessing}
                  className="w-16 border-x border-gray-300 px-2 py-1 text-center text-sm focus:outline-none disabled:opacity-50"
                  aria-label="Item quantity"
                />
                <button
                  type="button"
                  onClick={() => handleQuantityChange(quantity + 1)}
                  disabled={isProcessing || quantity >= 99}
                  className="px-3 py-1 text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Increase quantity"
                >
                  +
                </button>
              </div>
            </div>

            {/* Remove Button */}
            {!showRemoveConfirm ? (
              <button
                type="button"
                onClick={() => setShowRemoveConfirm(true)}
                disabled={isProcessing}
                className="text-sm font-medium text-red-600 hover:text-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Remove
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-700">Remove item?</span>
                <button
                  type="button"
                  onClick={handleRemove}
                  disabled={isProcessing}
                  className="text-sm font-medium text-red-600 hover:text-red-500 disabled:opacity-50"
                >
                  Yes
                </button>
                <button
                  type="button"
                  onClick={() => setShowRemoveConfirm(false)}
                  disabled={isProcessing}
                  className="text-sm font-medium text-gray-600 hover:text-gray-500 disabled:opacity-50"
                >
                  No
                </button>
              </div>
            )}
          </div>

          {/* Unit Price */}
          <p className="mt-2 text-sm text-gray-500">
            Unit price: {formatCurrency(item.unitPrice)}
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * Empty cart state component
 */
function EmptyCartState({ onContinueShopping }: { readonly onContinueShopping: () => void }): JSX.Element {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <svg
        className="h-24 w-24 text-gray-400 mb-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"
        />
      </svg>
      <h2 className="text-2xl font-semibold text-gray-900 mb-2">Your cart is empty</h2>
      <p className="text-gray-600 mb-6 text-center max-w-md">
        Start adding vehicles to your cart to see them here. Browse our inventory to find your perfect vehicle.
      </p>
      <button
        type="button"
        onClick={onContinueShopping}
        className="px-6 py-3 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
      >
        Continue Shopping
      </button>
    </div>
  );
}

/**
 * Promotional code section component
 */
function PromoCodeSection({
  hasPromoCode,
  onApply,
  onRemove,
  disabled,
}: {
  readonly hasPromoCode: boolean;
  readonly onApply: (code: string) => Promise<void>;
  readonly onRemove: () => Promise<void>;
  readonly disabled: boolean;
}): JSX.Element {
  const [promoState, setPromoState] = useState<PromoCodeState>({
    code: '',
    isApplying: false,
    error: null,
  });

  const handleApply = useCallback(async () => {
    if (!promoState.code.trim()) {
      setPromoState((prev) => ({ ...prev, error: 'Please enter a promotional code' }));
      return;
    }

    setPromoState((prev) => ({ ...prev, isApplying: true, error: null }));

    try {
      await onApply(promoState.code.trim());
      setPromoState({ code: '', isApplying: false, error: null });
    } catch (error) {
      setPromoState((prev) => ({
        ...prev,
        isApplying: false,
        error: error instanceof Error ? error.message : 'Failed to apply promotional code',
      }));
    }
  }, [promoState.code, onApply]);

  const handleRemove = useCallback(async () => {
    setPromoState((prev) => ({ ...prev, isApplying: true, error: null }));

    try {
      await onRemove();
      setPromoState({ code: '', isApplying: false, error: null });
    } catch (error) {
      setPromoState((prev) => ({
        ...prev,
        isApplying: false,
        error: error instanceof Error ? error.message : 'Failed to remove promotional code',
      }));
    }
  }, [onRemove]);

  if (hasPromoCode) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-md p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg
              className="h-5 w-5 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="text-sm font-medium text-green-900">Promotional code applied</span>
          </div>
          <button
            type="button"
            onClick={handleRemove}
            disabled={disabled || promoState.isApplying}
            className="text-sm font-medium text-green-700 hover:text-green-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Remove
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <label htmlFor="promo-code" className="block text-sm font-medium text-gray-700">
        Promotional Code
      </label>
      <div className="flex gap-2">
        <input
          id="promo-code"
          type="text"
          value={promoState.code}
          onChange={(e) => setPromoState((prev) => ({ ...prev, code: e.target.value, error: null }))}
          disabled={disabled || promoState.isApplying}
          placeholder="Enter code"
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:bg-gray-100"
          aria-describedby={promoState.error ? 'promo-code-error' : undefined}
        />
        <button
          type="button"
          onClick={handleApply}
          disabled={disabled || promoState.isApplying || !promoState.code.trim()}
          className="px-4 py-2 bg-gray-800 text-white font-medium rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {promoState.isApplying ? 'Applying...' : 'Apply'}
        </button>
      </div>
      {promoState.error && (
        <p id="promo-code-error" className="text-sm text-red-600" role="alert">
          {promoState.error}
        </p>
      )}
    </div>
  );
}

/**
 * Cart summary component
 */
function CartSummary({
  subtotal,
  total,
  itemCount,
  hasPromoCode,
  onCheckout,
  isLoading,
}: {
  readonly subtotal: number;
  readonly total: number;
  readonly itemCount: number;
  readonly hasPromoCode: boolean;
  readonly onCheckout: () => void;
  readonly isLoading: boolean;
}): JSX.Element {
  const discount = subtotal - total;
  const hasDiscount = discount > 0;

  return (
    <div className="bg-gray-50 rounded-lg p-6 space-y-4">
      <h2 className="text-lg font-semibold text-gray-900">Order Summary</h2>

      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Subtotal ({itemCount} {itemCount === 1 ? 'item' : 'items'})</span>
          <span className="font-medium text-gray-900">{formatCurrency(subtotal)}</span>
        </div>

        {hasDiscount && (
          <div className="flex justify-between text-sm">
            <span className="text-green-600">Discount</span>
            <span className="font-medium text-green-600">-{formatCurrency(discount)}</span>
          </div>
        )}

        <div className="border-t border-gray-200 pt-2">
          <div className="flex justify-between">
            <span className="text-base font-semibold text-gray-900">Total</span>
            <span className="text-base font-semibold text-gray-900">{formatCurrency(total)}</span>
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={onCheckout}
        disabled={isLoading}
        className="w-full px-6 py-3 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? 'Processing...' : 'Proceed to Checkout'}
      </button>

      <p className="text-xs text-gray-500 text-center">
        Taxes and shipping calculated at checkout
      </p>
    </div>
  );
}

/**
 * Main cart page component
 */
export default function CartPage({
  className = '',
  onCheckout,
  enablePromoCode = true,
  showEmptyState = true,
}: CartPageProps): JSX.Element {
  const navigate = useNavigate();
  const {
    cart,
    isLoading,
    error,
    itemCount,
    subtotal,
    total,
    hasItems,
    hasPromotionalCode,
    updateCartItem,
    removeCartItem,
    applyPromotionalCode,
    removePromotionalCode,
  } = useCart();

  const [itemActionState, setItemActionState] = useState<ItemActionState | null>(null);

  const handleQuantityChange = useCallback(
    async (itemId: string, quantity: number) => {
      setItemActionState({ itemId, action: 'update', isProcessing: true });

      try {
        await updateCartItem(itemId, { quantity });
      } catch (err) {
        console.error('Failed to update cart item:', err);
      } finally {
        setItemActionState(null);
      }
    },
    [updateCartItem],
  );

  const handleRemoveItem = useCallback(
    async (itemId: string) => {
      setItemActionState({ itemId, action: 'remove', isProcessing: true });

      try {
        await removeCartItem(itemId);
      } catch (err) {
        console.error('Failed to remove cart item:', err);
      } finally {
        setItemActionState(null);
      }
    },
    [removeCartItem],
  );

  const handleApplyPromoCode = useCallback(
    async (code: string) => {
      await applyPromotionalCode({ code });
    },
    [applyPromotionalCode],
  );

  const handleRemovePromoCode = useCallback(async () => {
    await removePromotionalCode();
  }, [removePromotionalCode]);

  const handleCheckout = useCallback(() => {
    if (onCheckout) {
      onCheckout();
    } else {
      navigate('/checkout');
    }
  }, [onCheckout, navigate]);

  const handleContinueShopping = useCallback(() => {
    navigate('/browse');
  }, [navigate]);

  const isItemProcessing = useCallback(
    (itemId: string): boolean => {
      return itemActionState?.itemId === itemId && itemActionState.isProcessing;
    },
    [itemActionState],
  );

  const cartItems = useMemo(() => cart?.items ?? [], [cart?.items]);

  if (isLoading && !cart) {
    return (
      <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 ${className}`}>
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 ${className}`}>
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <svg
              className="h-5 w-5 text-red-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error loading cart</h3>
              <p className="mt-1 text-sm text-red-700">{error.message}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!hasItems && showEmptyState) {
    return (
      <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 ${className}`}>
        <EmptyCartState onContinueShopping={handleContinueShopping} />
      </div>
    );
  }

  return (
    <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 ${className}`}>
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Shopping Cart</h1>

      <div className="lg:grid lg:grid-cols-12 lg:gap-8">
        {/* Cart Items */}
        <div className="lg:col-span-8">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Cart Items ({itemCount})
            </h2>

            <div className="divide-y divide-gray-200">
              {cartItems.map((item) => (
                <CartItemRow
                  key={item.id}
                  item={item}
                  onQuantityChange={handleQuantityChange}
                  onRemove={handleRemoveItem}
                  isProcessing={isItemProcessing(item.id)}
                />
              ))}
            </div>
          </div>

          {/* Promotional Code Section */}
          {enablePromoCode && (
            <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <PromoCodeSection
                hasPromoCode={hasPromotionalCode}
                onApply={handleApplyPromoCode}
                onRemove={handleRemovePromoCode}
                disabled={isLoading}
              />
            </div>
          )}
        </div>

        {/* Cart Summary */}
        <div className="mt-8 lg:mt-0 lg:col-span-4">
          <div className="sticky top-4">
            <CartSummary
              subtotal={subtotal}
              total={total}
              itemCount={itemCount}
              hasPromoCode={hasPromotionalCode}
              onCheckout={handleCheckout}
              isLoading={isLoading}
            />
          </div>
        </div>
      </div>
    </div>
  );
}