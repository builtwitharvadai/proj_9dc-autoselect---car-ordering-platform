/**
 * Cart Item Component
 * Individual cart item with quantity controls, pricing, and remove functionality
 * Implements optimistic updates and comprehensive error handling
 */

import { memo, useCallback, useState } from 'react';
import type { CartItem as CartItemType } from '../../types/cart';
import { useUpdateCartItem, useRemoveCartItem } from '../../hooks/useCart';
import { formatCurrency } from '../../types/cart';

/**
 * Cart item component props
 */
export interface CartItemProps {
  readonly item: CartItemType;
  readonly className?: string;
  readonly disabled?: boolean;
  readonly onQuantityChange?: (itemId: string, quantity: number) => void;
  readonly onRemove?: (itemId: string) => void;
  readonly showConfiguration?: boolean;
}

/**
 * Quantity constraints
 */
const MIN_QUANTITY = 1;
const MAX_QUANTITY = 10;

/**
 * Individual cart item component with quantity controls
 */
function CartItem({
  item,
  className = '',
  disabled = false,
  onQuantityChange,
  onRemove,
  showConfiguration = true,
}: CartItemProps): JSX.Element {
  const [isUpdating, setIsUpdating] = useState(false);
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false);

  const updateCartItem = useUpdateCartItem();
  const removeCartItem = useRemoveCartItem();

  /**
   * Handle quantity change with validation and optimistic updates
   */
  const handleQuantityChange = useCallback(
    async (newQuantity: number) => {
      if (disabled || isUpdating) {
        return;
      }

      // Validate quantity bounds
      if (newQuantity < MIN_QUANTITY || newQuantity > MAX_QUANTITY) {
        console.warn(
          `[CartItem] Invalid quantity ${newQuantity}, must be between ${MIN_QUANTITY} and ${MAX_QUANTITY}`,
        );
        return;
      }

      // Skip if quantity unchanged
      if (newQuantity === item.quantity) {
        return;
      }

      setIsUpdating(true);

      try {
        await updateCartItem.mutateAsync({
          itemId: item.id,
          request: { quantity: newQuantity },
        });

        // Notify parent component
        onQuantityChange?.(item.id, newQuantity);

        console.info(`[CartItem] Updated quantity for item ${item.id} to ${newQuantity}`);
      } catch (error) {
        console.error('[CartItem] Failed to update quantity:', error);
      } finally {
        setIsUpdating(false);
      }
    },
    [disabled, isUpdating, item.id, item.quantity, updateCartItem, onQuantityChange],
  );

  /**
   * Handle quantity increment
   */
  const handleIncrement = useCallback(() => {
    const newQuantity = Math.min(item.quantity + 1, MAX_QUANTITY);
    void handleQuantityChange(newQuantity);
  }, [item.quantity, handleQuantityChange]);

  /**
   * Handle quantity decrement
   */
  const handleDecrement = useCallback(() => {
    const newQuantity = Math.max(item.quantity - 1, MIN_QUANTITY);
    void handleQuantityChange(newQuantity);
  }, [item.quantity, handleQuantityChange]);

  /**
   * Handle remove item with confirmation
   */
  const handleRemove = useCallback(async () => {
    if (disabled || isUpdating) {
      return;
    }

    if (!showRemoveConfirm) {
      setShowRemoveConfirm(true);
      return;
    }

    setIsUpdating(true);

    try {
      await removeCartItem.mutateAsync(item.id);

      // Notify parent component
      onRemove?.(item.id);

      console.info(`[CartItem] Removed item ${item.id} from cart`);
    } catch (error) {
      console.error('[CartItem] Failed to remove item:', error);
      setShowRemoveConfirm(false);
    } finally {
      setIsUpdating(false);
    }
  }, [disabled, isUpdating, showRemoveConfirm, item.id, removeCartItem, onRemove]);

  /**
   * Cancel remove confirmation
   */
  const handleCancelRemove = useCallback(() => {
    setShowRemoveConfirm(false);
  }, []);

  /**
   * Get vehicle display name
   */
  const vehicleName = item.vehicle
    ? `${item.vehicle.year} ${item.vehicle.make} ${item.vehicle.model}${item.vehicle.trim ? ` ${item.vehicle.trim}` : ''}`
    : 'Vehicle';

  /**
   * Check if item is reserved
   */
  const isReserved = item.status === 'reserved' && item.reservedUntil !== undefined;

  /**
   * Check if reservation is expired
   */
  const isReservationExpired =
    isReserved && new Date(item.reservedUntil!) < new Date();

  /**
   * Get status badge color
   */
  const getStatusColor = (): string => {
    if (item.status === 'expired' || isReservationExpired) {
      return 'bg-red-100 text-red-800';
    }
    if (item.status === 'reserved') {
      return 'bg-yellow-100 text-yellow-800';
    }
    return 'bg-green-100 text-green-800';
  };

  /**
   * Get status text
   */
  const getStatusText = (): string => {
    if (item.status === 'expired') {
      return 'Expired';
    }
    if (isReservationExpired) {
      return 'Reservation Expired';
    }
    if (item.status === 'reserved') {
      return 'Reserved';
    }
    return 'Active';
  };

  return (
    <div
      className={`bg-white rounded-lg shadow-sm border border-gray-200 p-4 ${className}`}
      data-testid="cart-item"
      data-item-id={item.id}
    >
      <div className="flex gap-4">
        {/* Vehicle Image */}
        <div className="flex-shrink-0">
          {item.vehicle?.imageUrl ? (
            <img
              src={item.vehicle.imageUrl}
              alt={vehicleName}
              className="w-24 h-24 object-cover rounded-md"
              loading="lazy"
            />
          ) : (
            <div className="w-24 h-24 bg-gray-200 rounded-md flex items-center justify-center">
              <svg
                className="w-12 h-12 text-gray-400"
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
          )}
        </div>

        {/* Item Details */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-gray-900 truncate">
                {vehicleName}
              </h3>

              {/* Status Badge */}
              <span
                className={`inline-block mt-1 px-2 py-1 text-xs font-medium rounded-full ${getStatusColor()}`}
              >
                {getStatusText()}
              </span>

              {/* Configuration Details */}
              {showConfiguration && item.configuration && (
                <div className="mt-2 text-sm text-gray-600">
                  <p>Configuration ID: {item.configuration.id}</p>
                  {item.configuration.colorId && (
                    <p>Color: {item.configuration.colorId}</p>
                  )}
                  {item.configuration.packageIds.length > 0 && (
                    <p>Packages: {item.configuration.packageIds.length}</p>
                  )}
                  {item.configuration.optionIds.length > 0 && (
                    <p>Options: {item.configuration.optionIds.length}</p>
                  )}
                </div>
              )}

              {/* Reservation Info */}
              {isReserved && !isReservationExpired && (
                <p className="mt-2 text-sm text-yellow-700">
                  Reserved until{' '}
                  {new Date(item.reservedUntil!).toLocaleString()}
                </p>
              )}
            </div>

            {/* Pricing */}
            <div className="text-right">
              <p className="text-lg font-semibold text-gray-900">
                {formatCurrency(item.totalPrice)}
              </p>
              <p className="text-sm text-gray-600">
                {formatCurrency(item.unitPrice)} each
              </p>
            </div>
          </div>

          {/* Quantity Controls and Remove Button */}
          <div className="mt-4 flex items-center justify-between">
            {/* Quantity Controls */}
            <div className="flex items-center gap-2">
              <label htmlFor={`quantity-${item.id}`} className="sr-only">
                Quantity
              </label>
              <button
                type="button"
                onClick={handleDecrement}
                disabled={
                  disabled ||
                  isUpdating ||
                  item.quantity <= MIN_QUANTITY ||
                  item.status === 'expired' ||
                  isReservationExpired
                }
                className="w-8 h-8 flex items-center justify-center rounded-md border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                aria-label="Decrease quantity"
              >
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
                    d="M20 12H4"
                  />
                </svg>
              </button>

              <input
                id={`quantity-${item.id}`}
                type="number"
                min={MIN_QUANTITY}
                max={MAX_QUANTITY}
                value={item.quantity}
                readOnly
                disabled={disabled || isUpdating}
                className="w-16 text-center border border-gray-300 rounded-md py-1 text-gray-900 disabled:opacity-50"
                aria-label="Quantity"
              />

              <button
                type="button"
                onClick={handleIncrement}
                disabled={
                  disabled ||
                  isUpdating ||
                  item.quantity >= MAX_QUANTITY ||
                  item.status === 'expired' ||
                  isReservationExpired
                }
                className="w-8 h-8 flex items-center justify-center rounded-md border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                aria-label="Increase quantity"
              >
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
                    d="M12 4v16m8-8H4"
                  />
                </svg>
              </button>

              {isUpdating && (
                <div
                  className="ml-2 w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"
                  role="status"
                  aria-label="Updating quantity"
                />
              )}
            </div>

            {/* Remove Button */}
            {!showRemoveConfirm ? (
              <button
                type="button"
                onClick={handleRemove}
                disabled={disabled || isUpdating}
                className="text-red-600 hover:text-red-700 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Remove
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-700">Remove item?</span>
                <button
                  type="button"
                  onClick={handleRemove}
                  disabled={disabled || isUpdating}
                  className="px-3 py-1 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Confirm
                </button>
                <button
                  type="button"
                  onClick={handleCancelRemove}
                  disabled={disabled || isUpdating}
                  className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>

          {/* Error Messages */}
          {updateCartItem.isError && (
            <div
              className="mt-2 p-2 bg-red-50 border border-red-200 rounded-md"
              role="alert"
            >
              <p className="text-sm text-red-800">
                Failed to update quantity. Please try again.
              </p>
            </div>
          )}

          {removeCartItem.isError && (
            <div
              className="mt-2 p-2 bg-red-50 border border-red-200 rounded-md"
              role="alert"
            >
              <p className="text-sm text-red-800">
                Failed to remove item. Please try again.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default memo(CartItem);