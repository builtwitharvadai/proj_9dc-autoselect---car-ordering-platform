/**
 * Order tracking type definitions for AutoSelect platform
 * Provides comprehensive type safety for order management, status tracking, and delivery estimation
 */

/**
 * Order status enumeration representing the complete order lifecycle
 */
export type OrderStatus =
  | 'pending'
  | 'payment_processing'
  | 'confirmed'
  | 'in_production'
  | 'quality_check'
  | 'ready_for_shipment'
  | 'shipped'
  | 'in_transit'
  | 'out_for_delivery'
  | 'delivered'
  | 'cancelled'
  | 'on_hold'
  | 'delayed'
  | 'returned';

/**
 * Payment status for order transactions
 */
export type PaymentStatus =
  | 'pending'
  | 'authorized'
  | 'captured'
  | 'failed'
  | 'refunded'
  | 'partially_refunded';

/**
 * Fulfillment status tracking physical order processing
 */
export type FulfillmentStatus =
  | 'pending'
  | 'processing'
  | 'ready'
  | 'shipped'
  | 'in_transit'
  | 'delivered'
  | 'cancelled';

/**
 * Timeline stage for visual progress tracking
 */
export type TimelineStage =
  | 'order_placed'
  | 'payment_confirmed'
  | 'in_production'
  | 'quality_check'
  | 'shipped'
  | 'in_transit'
  | 'out_for_delivery'
  | 'delivered';

/**
 * Timeline stage status for UI rendering
 */
export type TimelineStageStatus = 'completed' | 'current' | 'upcoming' | 'skipped';

/**
 * Delivery method options
 */
export type DeliveryMethod = 'standard' | 'express' | 'overnight' | 'pickup';

/**
 * Order item representing a configured vehicle in the order
 */
export interface OrderItem {
  readonly id: string;
  readonly orderId: string;
  readonly vehicleId: string;
  readonly vehicleName: string;
  readonly vehicleImage: string;
  readonly configurationId: string;
  readonly vin?: string;
  readonly quantity: number;
  readonly unitPrice: number;
  readonly subtotal: number;
  readonly customizations: readonly string[];
  readonly packageIds: readonly string[];
  readonly optionIds: readonly string[];
  readonly createdAt: string;
  readonly updatedAt: string;
}

/**
 * Customer information for order delivery
 */
export interface CustomerInfo {
  readonly firstName: string;
  readonly lastName: string;
  readonly email: string;
  readonly phone: string;
}

/**
 * Delivery address information
 */
export interface DeliveryAddress {
  readonly street: string;
  readonly city: string;
  readonly state: string;
  readonly postalCode: string;
  readonly country: string;
  readonly additionalInfo?: string;
}

/**
 * Trade-in vehicle information
 */
export interface TradeInInfo {
  readonly vehicleId?: string;
  readonly make: string;
  readonly model: string;
  readonly year: number;
  readonly vin: string;
  readonly estimatedValue: number;
  readonly condition: string;
  readonly mileage: number;
}

/**
 * Order status history entry for audit trail
 */
export interface OrderStatusHistory {
  readonly id: string;
  readonly orderId: string;
  readonly status: OrderStatus;
  readonly previousStatus?: OrderStatus;
  readonly reason?: string;
  readonly notes?: string;
  readonly changedBy?: string;
  readonly changedAt: string;
  readonly metadata?: Record<string, unknown>;
}

/**
 * Timeline stage definition for progress visualization
 */
export interface OrderTimelineStage {
  readonly stage: TimelineStage;
  readonly status: TimelineStageStatus;
  readonly title: string;
  readonly description: string;
  readonly completedAt?: string;
  readonly estimatedAt?: string;
  readonly icon: string;
  readonly metadata?: Record<string, unknown>;
}

/**
 * Complete order timeline for visual tracking
 */
export interface OrderTimeline {
  readonly orderId: string;
  readonly stages: readonly OrderTimelineStage[];
  readonly currentStage: TimelineStage;
  readonly progress: number;
  readonly lastUpdated: string;
}

/**
 * Delivery estimate with confidence levels
 */
export interface DeliveryEstimate {
  readonly orderId: string;
  readonly estimatedDeliveryDate: string;
  readonly earliestDeliveryDate: string;
  readonly latestDeliveryDate: string;
  readonly confidence: 'high' | 'medium' | 'low';
  readonly deliveryMethod: DeliveryMethod;
  readonly trackingNumber?: string;
  readonly carrier?: string;
  readonly lastUpdated: string;
  readonly factors: readonly string[];
}

/**
 * Shipping information for order delivery
 */
export interface ShippingInfo {
  readonly carrier: string;
  readonly trackingNumber: string;
  readonly trackingUrl?: string;
  readonly shippedAt: string;
  readonly estimatedDelivery: string;
  readonly deliveryMethod: DeliveryMethod;
  readonly shippingCost: number;
}

/**
 * Complete order entity with all related information
 */
export interface Order {
  readonly id: string;
  readonly orderNumber: string;
  readonly userId: string;
  readonly status: OrderStatus;
  readonly paymentStatus: PaymentStatus;
  readonly fulfillmentStatus: FulfillmentStatus;
  readonly items: readonly OrderItem[];
  readonly customerInfo: CustomerInfo;
  readonly deliveryAddress: DeliveryAddress;
  readonly tradeInInfo?: TradeInInfo;
  readonly shippingInfo?: ShippingInfo;
  readonly subtotal: number;
  readonly taxAmount: number;
  readonly shippingCost: number;
  readonly discountAmount: number;
  readonly tradeInCredit: number;
  readonly total: number;
  readonly promotionalCode?: string;
  readonly notes?: string;
  readonly createdAt: string;
  readonly updatedAt: string;
  readonly confirmedAt?: string;
  readonly shippedAt?: string;
  readonly deliveredAt?: string;
  readonly cancelledAt?: string;
  readonly metadata?: Record<string, unknown>;
}

/**
 * Order with complete history for detailed tracking
 */
export interface OrderWithHistory extends Order {
  readonly statusHistory: readonly OrderStatusHistory[];
  readonly timeline: OrderTimeline;
  readonly deliveryEstimate: DeliveryEstimate;
}

/**
 * Order list request parameters
 */
export interface OrderListRequest {
  readonly userId?: string;
  readonly status?: OrderStatus;
  readonly paymentStatus?: PaymentStatus;
  readonly fulfillmentStatus?: FulfillmentStatus;
  readonly startDate?: string;
  readonly endDate?: string;
  readonly page?: number;
  readonly pageSize?: number;
  readonly sortBy?: 'createdAt' | 'updatedAt' | 'orderNumber' | 'total';
  readonly sortDirection?: 'asc' | 'desc';
}

/**
 * Order list response with pagination
 */
export interface OrderListResponse {
  readonly orders: readonly Order[];
  readonly total: number;
  readonly page: number;
  readonly pageSize: number;
  readonly totalPages: number;
}

/**
 * Order creation request
 */
export interface OrderCreateRequest {
  readonly items: readonly {
    readonly vehicleId: string;
    readonly configurationId: string;
    readonly quantity: number;
  }[];
  readonly customerInfo: CustomerInfo;
  readonly deliveryAddress: DeliveryAddress;
  readonly tradeInInfo?: TradeInInfo;
  readonly promotionalCode?: string;
  readonly notes?: string;
  readonly paymentMethodId: string;
}

/**
 * Order status update request
 */
export interface OrderStatusUpdateRequest {
  readonly status: OrderStatus;
  readonly reason?: string;
  readonly notes?: string;
}

/**
 * WebSocket message types for real-time updates
 */
export type OrderWebSocketMessageType =
  | 'order_status_changed'
  | 'delivery_estimate_updated'
  | 'timeline_updated'
  | 'shipping_info_updated'
  | 'order_cancelled'
  | 'order_delayed';

/**
 * WebSocket message for real-time order updates
 */
export interface OrderWebSocketMessage {
  readonly type: OrderWebSocketMessageType;
  readonly orderId: string;
  readonly timestamp: string;
  readonly data: unknown;
}

/**
 * Order status change WebSocket message
 */
export interface OrderStatusChangedMessage extends OrderWebSocketMessage {
  readonly type: 'order_status_changed';
  readonly data: {
    readonly previousStatus: OrderStatus;
    readonly newStatus: OrderStatus;
    readonly reason?: string;
  };
}

/**
 * Delivery estimate update WebSocket message
 */
export interface DeliveryEstimateUpdatedMessage extends OrderWebSocketMessage {
  readonly type: 'delivery_estimate_updated';
  readonly data: DeliveryEstimate;
}

/**
 * Timeline update WebSocket message
 */
export interface TimelineUpdatedMessage extends OrderWebSocketMessage {
  readonly type: 'timeline_updated';
  readonly data: OrderTimeline;
}

/**
 * Type guards for order status checks
 */
export function isOrderPending(order: Order): boolean {
  return order.status === 'pending';
}

export function isOrderConfirmed(order: Order): boolean {
  return order.status === 'confirmed';
}

export function isOrderInProduction(order: Order): boolean {
  return order.status === 'in_production';
}

export function isOrderShipped(order: Order): boolean {
  return order.status === 'shipped' || order.status === 'in_transit';
}

export function isOrderDelivered(order: Order): boolean {
  return order.status === 'delivered';
}

export function isOrderCancelled(order: Order): boolean {
  return order.status === 'cancelled';
}

export function isOrderActive(order: Order): boolean {
  return !['delivered', 'cancelled', 'returned'].includes(order.status);
}

export function canCancelOrder(order: Order): boolean {
  return ['pending', 'payment_processing', 'confirmed'].includes(order.status);
}

/**
 * Type guard for order with history
 */
export function hasOrderHistory(
  order: Order | OrderWithHistory,
): order is OrderWithHistory {
  return 'statusHistory' in order && 'timeline' in order && 'deliveryEstimate' in order;
}

/**
 * Type guard for order with shipping info
 */
export function hasShippingInfo(
  order: Order,
): order is Order & { readonly shippingInfo: ShippingInfo } {
  return order.shippingInfo !== undefined;
}

/**
 * Type guard for order with trade-in
 */
export function hasTradeIn(
  order: Order,
): order is Order & { readonly tradeInInfo: TradeInInfo } {
  return order.tradeInInfo !== undefined;
}

/**
 * Order status display names
 */
export const ORDER_STATUS_NAMES: Record<OrderStatus, string> = {
  pending: 'Pending',
  payment_processing: 'Processing Payment',
  confirmed: 'Confirmed',
  in_production: 'In Production',
  quality_check: 'Quality Check',
  ready_for_shipment: 'Ready for Shipment',
  shipped: 'Shipped',
  in_transit: 'In Transit',
  out_for_delivery: 'Out for Delivery',
  delivered: 'Delivered',
  cancelled: 'Cancelled',
  on_hold: 'On Hold',
  delayed: 'Delayed',
  returned: 'Returned',
} as const;

/**
 * Timeline stage display names
 */
export const TIMELINE_STAGE_NAMES: Record<TimelineStage, string> = {
  order_placed: 'Order Placed',
  payment_confirmed: 'Payment Confirmed',
  in_production: 'In Production',
  quality_check: 'Quality Check',
  shipped: 'Shipped',
  in_transit: 'In Transit',
  out_for_delivery: 'Out for Delivery',
  delivered: 'Delivered',
} as const;

/**
 * Delivery method display names
 */
export const DELIVERY_METHOD_NAMES: Record<DeliveryMethod, string> = {
  standard: 'Standard Delivery',
  express: 'Express Delivery',
  overnight: 'Overnight Delivery',
  pickup: 'Pickup',
} as const;

/**
 * Order constraints and limits
 */
export const ORDER_CONSTRAINTS = {
  MIN_ITEMS: 1,
  MAX_ITEMS: 10,
  MIN_QUANTITY: 1,
  MAX_QUANTITY: 5,
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
} as const;

/**
 * Utility function to format order number
 */
export function formatOrderNumber(orderNumber: string): string {
  return orderNumber.toUpperCase();
}

/**
 * Utility function to calculate days until delivery
 */
export function calculateDaysUntilDelivery(estimatedDate: string): number {
  const now = new Date();
  const delivery = new Date(estimatedDate);
  const diffTime = delivery.getTime() - now.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return Math.max(0, diffDays);
}

/**
 * Utility function to calculate order progress percentage
 */
export function calculateOrderProgress(timeline: OrderTimeline): number {
  return Math.round(timeline.progress * 100);
}

/**
 * Utility function to get current timeline stage
 */
export function getCurrentTimelineStage(
  timeline: OrderTimeline,
): OrderTimelineStage | undefined {
  return timeline.stages.find((stage) => stage.status === 'current');
}

/**
 * Utility function to get completed timeline stages
 */
export function getCompletedTimelineStages(
  timeline: OrderTimeline,
): readonly OrderTimelineStage[] {
  return timeline.stages.filter((stage) => stage.status === 'completed');
}

/**
 * Utility function to format currency
 */
export function formatOrderCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

/**
 * Utility function to format date
 */
export function formatOrderDate(date: string): string {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date(date));
}

/**
 * Utility function to format date with time
 */
export function formatOrderDateTime(date: string): string {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
  }).format(new Date(date));
}