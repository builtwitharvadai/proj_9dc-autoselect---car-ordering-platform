/**
 * Cart Summary Component
 * Displays pricing breakdown with subtotal, discounts, taxes, and total
 * Includes responsive design and loading states during calculations
 */

import { memo, useMemo } from 'react';
import type { Cart } from '../../types/cart';
import { formatCurrency } from '../../types/cart';

/**
 * Cart summary component props
 */
export interface CartSummaryProps {
  /** Cart data with pricing information */
  readonly cart: Cart | undefined;
  /** Loading state during calculations */
  readonly isLoading?: boolean;
  /** Additional CSS classes */
  readonly className?: string;
  /** Checkout button click handler */
  readonly onCheckout?: () => void;
  /** Show checkout button */
  readonly showCheckoutButton?: boolean;
  /** Disable checkout button */
  readonly disableCheckout?: boolean;
}

/**
 * Cart summary component displaying pricing breakdown
 */
function CartSummary({
  cart,
  isLoading = false,
  className = '',
  onCheckout,
  showCheckoutButton = true,
  disableCheckout = false,
}: CartSummaryProps): JSX.Element {
  // Calculate if checkout should be disabled
  const isCheckoutDisabled = useMemo(() => {
    if (disableCheckout || isLoading) return true;
    if (!cart) return true;
    if (cart.items.length === 0) return true;
    return false;
  }, [disableCheckout, isLoading, cart]);

  // Format tax rate as percentage
  const taxRatePercentage = useMemo(() => {
    if (!cart) return '0.00';
    return (cart.taxRate * 100).toFixed(2);
  }, [cart]);

  // Handle checkout button click
  const handleCheckout = (): void => {
    if (!isCheckoutDisabled && onCheckout) {
      onCheckout();
    }
  };

  // Loading skeleton
  if (isLoading && !cart) {
    return (
      <div
        className={`bg-white rounded-lg shadow-md p-6 ${className}`}
        role="status"
        aria-label="Loading cart summary"
      >
        <div className="space-y-4">
          <div className="h-6 bg-gray-200 rounded animate-pulse" />
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded animate-pulse" />
            <div className="h-4 bg-gray-200 rounded animate-pulse" />
            <div className="h-4 bg-gray-200 rounded animate-pulse" />
          </div>
          <div className="border-t pt-4">
            <div className="h-6 bg-gray-200 rounded animate-pulse" />
          </div>
          {showCheckoutButton && (
            <div className="h-12 bg-gray-200 rounded animate-pulse" />
          )}
        </div>
      </div>
    );
  }

  // Empty cart state
  if (!cart || cart.items.length === 0) {
    return (
      <div
        className={`bg-white rounded-lg shadow-md p-6 ${className}`}
        role="region"
        aria-label="Cart summary"
      >
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Order Summary</h2>
        <div className="text-center py-8">
          <p className="text-gray-500">Your cart is empty</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`bg-white rounded-lg shadow-md p-6 ${className}`}
      role="region"
      aria-label="Cart summary"
    >
      {/* Header */}
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Order Summary</h2>

      {/* Pricing breakdown */}
      <div className="space-y-3 mb-4">
        {/* Subtotal */}
        <div className="flex justify-between items-center">
          <span className="text-gray-600">
            Subtotal ({cart.itemCount} {cart.itemCount === 1 ? 'item' : 'items'})
          </span>
          <span className="font-medium text-gray-900" aria-label="Subtotal amount">
            {formatCurrency(cart.subtotal)}
          </span>
        </div>

        {/* Promotional discount */}
        {cart.promotionalCode && cart.discountAmount > 0 && (
          <div className="flex justify-between items-center text-green-600">
            <span className="flex items-center gap-2">
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                />
              </svg>
              <span>
                Promo ({cart.promotionalCode})
              </span>
            </span>
            <span className="font-medium" aria-label="Discount amount">
              -{formatCurrency(cart.discountAmount)}
            </span>
          </div>
        )}

        {/* Tax */}
        <div className="flex justify-between items-center">
          <span className="text-gray-600">
            Tax ({taxRatePercentage}%)
          </span>
          <span className="font-medium text-gray-900" aria-label="Tax amount">
            {formatCurrency(cart.taxAmount)}
          </span>
        </div>
      </div>

      {/* Total */}
      <div className="border-t border-gray-200 pt-4 mb-6">
        <div className="flex justify-between items-center">
          <span className="text-lg font-semibold text-gray-900">Total</span>
          <span
            className="text-2xl font-bold text-gray-900"
            aria-label="Total amount"
          >
            {isLoading ? (
              <span className="inline-block w-24 h-8 bg-gray-200 rounded animate-pulse" />
            ) : (
              formatCurrency(cart.total)
            )}
          </span>
        </div>
      </div>

      {/* Checkout button */}
      {showCheckoutButton && (
        <button
          type="button"
          onClick={handleCheckout}
          disabled={isCheckoutDisabled}
          className={`w-full py-3 px-4 rounded-lg font-semibold text-white transition-colors duration-200 ${
            isCheckoutDisabled
              ? 'bg-gray-300 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
          }`}
          aria-label="Proceed to checkout"
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <svg
                className="animate-spin h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <span>Processing...</span>
            </span>
          ) : (
            'Proceed to Checkout'
          )}
        </button>
      )}

      {/* Additional information */}
      <div className="mt-4 text-sm text-gray-500 text-center">
        <p>Shipping calculated at checkout</p>
      </div>
    </div>
  );
}

/**
 * Memoized cart summary component
 * Prevents unnecessary re-renders when props haven't changed
 */
export default memo(CartSummary);