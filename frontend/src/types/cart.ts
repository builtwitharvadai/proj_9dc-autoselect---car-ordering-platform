/**
 * Cart type definitions for AutoSelect frontend application
 * Provides comprehensive type-safe interfaces for shopping cart operations
 */

/**
 * Cart item status types
 */
export type CartItemStatus = 'active' | 'reserved' | 'expired';

/**
 * Cart status types
 */
export type CartStatus = 'active' | 'expired' | 'converted';

/**
 * Promotional code discount types
 */
export type DiscountType = 'percentage' | 'fixed_amount';

/**
 * Cart item representing a vehicle configuration in the cart
 */
export interface CartItem {
  readonly id: string;
  readonly cartId: string;
  readonly vehicleId: string;
  readonly configurationId?: string;
  readonly quantity: number;
  readonly unitPrice: number;
  readonly totalPrice: number;
  readonly status: CartItemStatus;
  readonly reservationId?: string;
  readonly reservedUntil?: string;
  readonly createdAt: string;
  readonly updatedAt: string;
  readonly vehicle?: {
    readonly id: string;
    readonly make: string;
    readonly model: string;
    readonly year: number;
    readonly trim?: string;
    readonly imageUrl?: string;
  };
  readonly configuration?: {
    readonly id: string;
    readonly trimId?: string;
    readonly colorId?: string;
    readonly packageIds: readonly string[];
    readonly optionIds: readonly string[];
  };
}

/**
 * Shopping cart containing items and pricing information
 */
export interface Cart {
  readonly id: string;
  readonly userId?: string;
  readonly sessionId?: string;
  readonly items: readonly CartItem[];
  readonly itemCount: number;
  readonly subtotal: number;
  readonly taxAmount: number;
  readonly taxRate: number;
  readonly discountAmount: number;
  readonly total: number;
  readonly promotionalCode?: string;
  readonly status: CartStatus;
  readonly expiresAt: string;
  readonly createdAt: string;
  readonly updatedAt: string;
}

/**
 * Promotional code details
 */
export interface PromotionalCode {
  readonly code: string;
  readonly discountType: DiscountType;
  readonly discountValue: number;
  readonly minPurchaseAmount?: number;
  readonly maxDiscountAmount?: number;
  readonly validFrom: string;
  readonly validUntil: string;
  readonly usageLimit?: number;
  readonly usageCount: number;
  readonly isActive: boolean;
}

/**
 * Cart summary with calculated totals
 */
export interface CartSummary {
  readonly itemCount: number;
  readonly subtotal: number;
  readonly taxAmount: number;
  readonly taxRate: number;
  readonly discountAmount: number;
  readonly promotionalCode?: string;
  readonly total: number;
  readonly formattedSubtotal: string;
  readonly formattedTaxAmount: string;
  readonly formattedDiscountAmount: string;
  readonly formattedTotal: string;
}

/**
 * Request to add item to cart
 */
export interface AddToCartRequest {
  readonly vehicleId: string;
  readonly configurationId?: string;
  readonly quantity: number;
}

/**
 * Request to update cart item quantity
 */
export interface UpdateCartItemRequest {
  readonly quantity: number;
}

/**
 * Request to apply promotional code
 */
export interface ApplyPromotionalCodeRequest {
  readonly code: string;
}

/**
 * Response after adding item to cart
 */
export interface AddToCartResponse {
  readonly cart: Cart;
  readonly addedItem: CartItem;
}

/**
 * Response after updating cart item
 */
export interface UpdateCartItemResponse {
  readonly cart: Cart;
  readonly updatedItem: CartItem;
}

/**
 * Response after removing cart item
 */
export interface RemoveCartItemResponse {
  readonly cart: Cart;
  readonly removedItemId: string;
}

/**
 * Response after applying promotional code
 */
export interface ApplyPromotionalCodeResponse {
  readonly cart: Cart;
  readonly promotionalCode: PromotionalCode;
  readonly discountAmount: number;
}

/**
 * Cart error types
 */
export type CartErrorType =
  | 'CART_NOT_FOUND'
  | 'ITEM_NOT_FOUND'
  | 'INVALID_QUANTITY'
  | 'INSUFFICIENT_INVENTORY'
  | 'INVALID_PROMOTIONAL_CODE'
  | 'PROMOTIONAL_CODE_EXPIRED'
  | 'PROMOTIONAL_CODE_USAGE_LIMIT'
  | 'MIN_PURCHASE_NOT_MET'
  | 'CART_EXPIRED'
  | 'RESERVATION_EXPIRED'
  | 'VALIDATION_ERROR';

/**
 * Cart operation error
 */
export interface CartError {
  readonly type: CartErrorType;
  readonly message: string;
  readonly field?: string;
  readonly details?: Record<string, unknown>;
}

/**
 * Cart validation result
 */
export interface CartValidationResult {
  readonly isValid: boolean;
  readonly errors: readonly CartError[];
  readonly warnings: readonly CartError[];
}

/**
 * Cart item with availability information
 */
export interface CartItemWithAvailability extends CartItem {
  readonly isAvailable: boolean;
  readonly availableQuantity: number;
  readonly isReserved: boolean;
  readonly reservationExpired: boolean;
}

/**
 * Cart with validation and availability
 */
export interface CartWithValidation extends Cart {
  readonly validation: CartValidationResult;
  readonly items: readonly CartItemWithAvailability[];
}

/**
 * Type guard to check if cart has items
 */
export function hasItems(cart: Cart): cart is Cart & { readonly items: readonly [CartItem, ...CartItem[]] } {
  return cart.items.length > 0;
}

/**
 * Type guard to check if cart has promotional code
 */
export function hasPromotionalCode(
  cart: Cart,
): cart is Cart & { readonly promotionalCode: string } {
  return cart.promotionalCode !== undefined && cart.promotionalCode.length > 0;
}

/**
 * Type guard to check if cart is expired
 */
export function isCartExpired(cart: Cart): boolean {
  return new Date(cart.expiresAt) < new Date();
}

/**
 * Type guard to check if cart item is reserved
 */
export function isItemReserved(
  item: CartItem,
): item is CartItem & { readonly reservationId: string; readonly reservedUntil: string } {
  return item.reservationId !== undefined && item.reservedUntil !== undefined;
}

/**
 * Type guard to check if item reservation is expired
 */
export function isReservationExpired(item: CartItem): boolean {
  if (!isItemReserved(item)) {
    return false;
  }
  return new Date(item.reservedUntil) < new Date();
}

/**
 * Type guard to check if cart is anonymous
 */
export function isAnonymousCart(cart: Cart): cart is Cart & { readonly sessionId: string } {
  return cart.userId === undefined && cart.sessionId !== undefined;
}

/**
 * Type guard to check if cart is authenticated
 */
export function isAuthenticatedCart(cart: Cart): cart is Cart & { readonly userId: string } {
  return cart.userId !== undefined;
}

/**
 * Helper type for partial cart updates
 */
export type PartialCartUpdate = Partial<
  Omit<Cart, 'id' | 'items' | 'createdAt' | 'updatedAt'>
>;

/**
 * Helper type for cart with required items
 */
export type CartWithItems = Cart & {
  readonly items: readonly [CartItem, ...CartItem[]];
};

/**
 * Helper type for cart with promotional code
 */
export type CartWithPromoCode = Cart & {
  readonly promotionalCode: string;
  readonly discountAmount: number;
};

/**
 * Cart item quantity constraints
 */
export const CART_ITEM_CONSTRAINTS = {
  MIN_QUANTITY: 1,
  MAX_QUANTITY: 10,
  DEFAULT_QUANTITY: 1,
} as const;

/**
 * Cart expiration settings
 */
export const CART_EXPIRATION = {
  ANONYMOUS_DAYS: 7,
  AUTHENTICATED_DAYS: 30,
  RESERVATION_MINUTES: 15,
} as const;

/**
 * Cart status display names
 */
export const CART_STATUS_NAMES: Record<CartStatus, string> = {
  active: 'Active',
  expired: 'Expired',
  converted: 'Converted to Order',
} as const;

/**
 * Cart item status display names
 */
export const CART_ITEM_STATUS_NAMES: Record<CartItemStatus, string> = {
  active: 'Active',
  reserved: 'Reserved',
  expired: 'Expired',
} as const;

/**
 * Discount type display names
 */
export const DISCOUNT_TYPE_NAMES: Record<DiscountType, string> = {
  percentage: 'Percentage',
  fixed_amount: 'Fixed Amount',
} as const;

/**
 * Format currency amount
 */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

/**
 * Calculate cart item total
 */
export function calculateItemTotal(item: CartItem): number {
  return item.unitPrice * item.quantity;
}

/**
 * Calculate cart subtotal
 */
export function calculateSubtotal(items: readonly CartItem[]): number {
  return items.reduce((sum, item) => sum + calculateItemTotal(item), 0);
}

/**
 * Calculate tax amount
 */
export function calculateTaxAmount(subtotal: number, taxRate: number): number {
  return subtotal * taxRate;
}

/**
 * Calculate discount amount
 */
export function calculateDiscountAmount(
  subtotal: number,
  promoCode: PromotionalCode,
): number {
  if (promoCode.discountType === 'percentage') {
    const discount = subtotal * (promoCode.discountValue / 100);
    return promoCode.maxDiscountAmount
      ? Math.min(discount, promoCode.maxDiscountAmount)
      : discount;
  }
  return promoCode.discountValue;
}

/**
 * Calculate cart total
 */
export function calculateTotal(
  subtotal: number,
  taxAmount: number,
  discountAmount: number,
): number {
  return Math.max(0, subtotal + taxAmount - discountAmount);
}

/**
 * Create cart summary from cart
 */
export function createCartSummary(cart: Cart): CartSummary {
  return {
    itemCount: cart.itemCount,
    subtotal: cart.subtotal,
    taxAmount: cart.taxAmount,
    taxRate: cart.taxRate,
    discountAmount: cart.discountAmount,
    promotionalCode: cart.promotionalCode,
    total: cart.total,
    formattedSubtotal: formatCurrency(cart.subtotal),
    formattedTaxAmount: formatCurrency(cart.taxAmount),
    formattedDiscountAmount: formatCurrency(cart.discountAmount),
    formattedTotal: formatCurrency(cart.total),
  };
}