/**
 * Order Detail Page Component
 * 
 * Comprehensive order detail page integrating timeline, order items, customer info,
 * payment details, and delivery information. Includes real-time updates via WebSocket
 * and responsive design for mobile, tablet, and desktop.
 * 
 * @module components/OrderTracking/OrderDetailPage
 */

import { memo, useMemo, useCallback, useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Package,
  Truck,
  CreditCard,
  MapPin,
  User,
  Calendar,
  DollarSign,
  FileText,
  AlertCircle,
  RefreshCw,
  ArrowLeft,
  Download,
  Share2,
  Phone,
  Mail,
  CheckCircle,
  Clock,
  XCircle,
} from 'lucide-react';
import { OrderTimeline } from './OrderTimeline';
import { OrderStatusBadge } from './OrderStatusBadge';
import { DeliveryEstimator } from './DeliveryEstimator';
import {
  useOrderWithHistory,
  useOrderTimeline,
  useDeliveryEstimate,
  useOrderRealtime,
  useInvalidateOrders,
  isOrderApiError,
} from '../../hooks/useOrders';
import type {
  Order,
  OrderWithHistory,
  OrderTimeline as OrderTimelineType,
  DeliveryEstimate,
  OrderStatusChangedMessage,
  DeliveryEstimateUpdatedMessage,
  TimelineUpdatedMessage,
} from '../../types/orders';

/**
 * Props for OrderDetailPage component
 */
export interface OrderDetailPageProps {
  /** Optional CSS class name */
  readonly className?: string;
  /** Enable real-time updates (default: true) */
  readonly enableRealtime?: boolean;
  /** Enable auto-refresh (default: true) */
  readonly enableAutoRefresh?: boolean;
  /** Auto-refresh interval in ms (default: 60000) */
  readonly autoRefreshInterval?: number;
  /** Callback when order is updated */
  readonly onOrderUpdate?: (order: Order) => void;
  /** Callback when navigation back is requested */
  readonly onBack?: () => void;
}

/**
 * Loading skeleton component
 */
const LoadingSkeleton = memo(() => (
  <div className="animate-pulse space-y-6">
    <div className="h-8 w-64 rounded bg-gray-200" />
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2 space-y-6">
        <div className="h-96 rounded-lg bg-gray-200" />
        <div className="h-64 rounded-lg bg-gray-200" />
      </div>
      <div className="space-y-6">
        <div className="h-48 rounded-lg bg-gray-200" />
        <div className="h-48 rounded-lg bg-gray-200" />
      </div>
    </div>
  </div>
));

LoadingSkeleton.displayName = 'LoadingSkeleton';

/**
 * Error display component
 */
interface ErrorDisplayProps {
  readonly error: Error;
  readonly onRetry: () => void;
}

const ErrorDisplay = memo<ErrorDisplayProps>(({ error, onRetry }) => (
  <div className="flex min-h-[400px] items-center justify-center">
    <div className="max-w-md rounded-lg border border-red-200 bg-red-50 p-6 text-center">
      <AlertCircle className="mx-auto mb-4 h-12 w-12 text-red-600" aria-hidden="true" />
      <h2 className="mb-2 text-xl font-semibold text-red-900">
        Failed to Load Order
      </h2>
      <p className="mb-4 text-sm text-red-700">
        {isOrderApiError(error) ? error.message : 'An unexpected error occurred'}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="inline-flex items-center gap-2 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
      >
        <RefreshCw className="h-4 w-4" aria-hidden="true" />
        Try Again
      </button>
    </div>
  </div>
));

ErrorDisplay.displayName = 'ErrorDisplay';

/**
 * Order items section component
 */
interface OrderItemsSectionProps {
  readonly order: OrderWithHistory;
}

const OrderItemsSection = memo<OrderItemsSectionProps>(({ order }) => {
  const formatCurrency = useCallback((amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  }, []);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <Package className="h-5 w-5 text-gray-600" aria-hidden="true" />
        <h2 className="text-lg font-semibold text-gray-900">Order Items</h2>
      </div>

      <div className="space-y-4">
        {order.items.map((item) => (
          <div
            key={item.id}
            className="flex gap-4 rounded-lg border border-gray-100 p-4"
          >
            <div className="flex-1">
              <h3 className="font-medium text-gray-900">
                {item.vehicleName ?? 'Vehicle'}
              </h3>
              {item.configurationName && (
                <p className="mt-1 text-sm text-gray-600">
                  Configuration: {item.configurationName}
                </p>
              )}
              <div className="mt-2 flex items-center gap-4 text-sm text-gray-600">
                <span>Quantity: {item.quantity}</span>
                <span>Unit Price: {formatCurrency(item.unitPrice)}</span>
              </div>
            </div>
            <div className="text-right">
              <p className="font-semibold text-gray-900">
                {formatCurrency(item.totalPrice)}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 space-y-2 border-t border-gray-200 pt-4">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Subtotal</span>
          <span className="font-medium text-gray-900">
            {formatCurrency(order.subtotal)}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Tax</span>
          <span className="font-medium text-gray-900">
            {formatCurrency(order.taxAmount)}
          </span>
        </div>
        {order.discountAmount > 0 && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Discount</span>
            <span className="font-medium text-green-600">
              -{formatCurrency(order.discountAmount)}
            </span>
          </div>
        )}
        <div className="flex justify-between border-t border-gray-200 pt-2 text-base">
          <span className="font-semibold text-gray-900">Total</span>
          <span className="font-bold text-gray-900">
            {formatCurrency(order.totalAmount)}
          </span>
        </div>
      </div>
    </div>
  );
});

OrderItemsSection.displayName = 'OrderItemsSection';

/**
 * Customer information section component
 */
interface CustomerInfoSectionProps {
  readonly order: OrderWithHistory;
}

const CustomerInfoSection = memo<CustomerInfoSectionProps>(({ order }) => (
  <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
    <div className="mb-4 flex items-center gap-2">
      <User className="h-5 w-5 text-gray-600" aria-hidden="true" />
      <h2 className="text-lg font-semibold text-gray-900">Customer Information</h2>
    </div>

    <div className="space-y-3">
      <div>
        <p className="text-sm font-medium text-gray-600">Name</p>
        <p className="mt-1 text-base text-gray-900">
          {order.customerInfo.firstName} {order.customerInfo.lastName}
        </p>
      </div>

      <div>
        <p className="text-sm font-medium text-gray-600">Email</p>
        <a
          href={`mailto:${order.customerInfo.email}`}
          className="mt-1 flex items-center gap-2 text-base text-blue-600 hover:text-blue-700"
        >
          <Mail className="h-4 w-4" aria-hidden="true" />
          {order.customerInfo.email}
        </a>
      </div>

      <div>
        <p className="text-sm font-medium text-gray-600">Phone</p>
        <a
          href={`tel:${order.customerInfo.phone}`}
          className="mt-1 flex items-center gap-2 text-base text-blue-600 hover:text-blue-700"
        >
          <Phone className="h-4 w-4" aria-hidden="true" />
          {order.customerInfo.phone}
        </a>
      </div>
    </div>
  </div>
));

CustomerInfoSection.displayName = 'CustomerInfoSection';

/**
 * Delivery address section component
 */
interface DeliveryAddressSectionProps {
  readonly order: OrderWithHistory;
}

const DeliveryAddressSection = memo<DeliveryAddressSectionProps>(({ order }) => (
  <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
    <div className="mb-4 flex items-center gap-2">
      <MapPin className="h-5 w-5 text-gray-600" aria-hidden="true" />
      <h2 className="text-lg font-semibold text-gray-900">Delivery Address</h2>
    </div>

    <address className="not-italic text-gray-900">
      <p>{order.deliveryAddress.street}</p>
      {order.deliveryAddress.unit && <p>Unit {order.deliveryAddress.unit}</p>}
      <p>
        {order.deliveryAddress.city}, {order.deliveryAddress.state}{' '}
        {order.deliveryAddress.postalCode}
      </p>
      <p>{order.deliveryAddress.country}</p>
    </address>
  </div>
));

DeliveryAddressSection.displayName = 'DeliveryAddressSection';

/**
 * Payment information section component
 */
interface PaymentInfoSectionProps {
  readonly order: OrderWithHistory;
}

const PaymentInfoSection = memo<PaymentInfoSectionProps>(({ order }) => {
  const getPaymentStatusIcon = useCallback((status: string) => {
    switch (status) {
      case 'completed':
      case 'captured':
        return <CheckCircle className="h-5 w-5 text-green-600" aria-hidden="true" />;
      case 'pending':
      case 'processing':
        return <Clock className="h-5 w-5 text-yellow-600" aria-hidden="true" />;
      case 'failed':
      case 'cancelled':
        return <XCircle className="h-5 w-5 text-red-600" aria-hidden="true" />;
      default:
        return <CreditCard className="h-5 w-5 text-gray-600" aria-hidden="true" />;
    }
  }, []);

  const getPaymentStatusColor = useCallback((status: string): string => {
    switch (status) {
      case 'completed':
      case 'captured':
        return 'text-green-600';
      case 'pending':
      case 'processing':
        return 'text-yellow-600';
      case 'failed':
      case 'cancelled':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  }, []);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <CreditCard className="h-5 w-5 text-gray-600" aria-hidden="true" />
        <h2 className="text-lg font-semibold text-gray-900">Payment Information</h2>
      </div>

      <div className="space-y-3">
        <div>
          <p className="text-sm font-medium text-gray-600">Payment Method</p>
          <p className="mt-1 text-base text-gray-900">
            {order.paymentMethod.replace(/_/g, ' ')}
          </p>
        </div>

        <div>
          <p className="text-sm font-medium text-gray-600">Payment Status</p>
          <div className="mt-1 flex items-center gap-2">
            {getPaymentStatusIcon(order.paymentStatus)}
            <span className={`text-base font-medium ${getPaymentStatusColor(order.paymentStatus)}`}>
              {order.paymentStatus.replace(/_/g, ' ')}
            </span>
          </div>
        </div>

        {order.paymentIntentId && (
          <div>
            <p className="text-sm font-medium text-gray-600">Transaction ID</p>
            <p className="mt-1 font-mono text-sm text-gray-900">
              {order.paymentIntentId}
            </p>
          </div>
        )}
      </div>
    </div>
  );
});

PaymentInfoSection.displayName = 'PaymentInfoSection';

/**
 * Order Detail Page Component
 * 
 * Displays comprehensive order information with real-time updates.
 */
export const OrderDetailPage = memo<OrderDetailPageProps>(({
  className = '',
  enableRealtime = true,
  enableAutoRefresh = true,
  autoRefreshInterval = 60000,
  onOrderUpdate,
  onBack,
}) => {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const invalidateOrders = useInvalidateOrders();

  const [isRefreshing, setIsRefreshing] = useState(false);

  // Fetch order data
  const {
    data: orderData,
    isLoading: isOrderLoading,
    error: orderError,
    refetch: refetchOrder,
  } = useOrderWithHistory(orderId ?? '', {
    enabled: Boolean(orderId),
  });

  // Fetch timeline data
  const {
    data: timelineData,
    isLoading: isTimelineLoading,
    refetch: refetchTimeline,
  } = useOrderTimeline(orderId ?? '', {
    enabled: Boolean(orderId),
  });

  // Fetch delivery estimate
  const {
    data: deliveryEstimate,
    isLoading: isDeliveryLoading,
    refetch: refetchDelivery,
  } = useDeliveryEstimate(orderId ?? '', {
    enabled: Boolean(orderId),
  });

  // Real-time updates
  const handleStatusChange = useCallback(
    (message: OrderStatusChangedMessage) => {
      if (onOrderUpdate && orderData) {
        onOrderUpdate({
          ...orderData,
          status: message.data.newStatus,
          fulfillmentStatus: message.data.fulfillmentStatus,
        });
      }
    },
    [orderData, onOrderUpdate],
  );

  const handleDeliveryUpdate = useCallback(
    (_message: DeliveryEstimateUpdatedMessage) => {
      void refetchDelivery();
    },
    [refetchDelivery],
  );

  const handleTimelineUpdate = useCallback(
    (_message: TimelineUpdatedMessage) => {
      void refetchTimeline();
    },
    [refetchTimeline],
  );

  useOrderRealtime(orderId ?? '', {
    enabled: enableRealtime && Boolean(orderId),
    onStatusChange: handleStatusChange,
    onDeliveryUpdate: handleDeliveryUpdate,
    onTimelineUpdate: handleTimelineUpdate,
  });

  // Auto-refresh
  useEffect(() => {
    if (!enableAutoRefresh || !orderId) return;

    const interval = setInterval(() => {
      void invalidateOrders(orderId);
    }, autoRefreshInterval);

    return () => clearInterval(interval);
  }, [enableAutoRefresh, orderId, autoRefreshInterval, invalidateOrders]);

  // Refresh handler
  const handleRefresh = useCallback(async () => {
    if (!orderId) return;

    setIsRefreshing(true);
    try {
      await Promise.all([
        refetchOrder(),
        refetchTimeline(),
        refetchDelivery(),
      ]);
    } finally {
      setIsRefreshing(false);
    }
  }, [orderId, refetchOrder, refetchTimeline, refetchDelivery]);

  // Navigation handlers
  const handleBack = useCallback(() => {
    if (onBack) {
      onBack();
    } else {
      navigate('/orders');
    }
  }, [onBack, navigate]);

  // Loading state
  const isLoading = isOrderLoading || isTimelineLoading || isDeliveryLoading;

  // Error state
  if (orderError) {
    return (
      <div className={`container mx-auto px-4 py-8 ${className}`}>
        <ErrorDisplay error={orderError} onRetry={handleRefresh} />
      </div>
    );
  }

  // Loading state
  if (isLoading || !orderData) {
    return (
      <div className={`container mx-auto px-4 py-8 ${className}`}>
        <LoadingSkeleton />
      </div>
    );
  }

  return (
    <div className={`container mx-auto px-4 py-8 ${className}`}>
      {/* Header */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={handleBack}
            className="rounded-md p-2 text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900"
            aria-label="Go back"
          >
            <ArrowLeft className="h-5 w-5" aria-hidden="true" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 md:text-3xl">
              Order #{orderData.orderNumber}
            </h1>
            <p className="mt-1 text-sm text-gray-600">
              Placed on{' '}
              {new Intl.DateTimeFormat('en-US', {
                dateStyle: 'long',
                timeStyle: 'short',
              }).format(new Date(orderData.createdAt))}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <OrderStatusBadge status={orderData.status} />
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="rounded-md p-2 text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Refresh order"
          >
            <RefreshCw
              className={`h-5 w-5 ${isRefreshing ? 'animate-spin' : ''}`}
              aria-hidden="true"
            />
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left column - Timeline and Items */}
        <div className="lg:col-span-2 space-y-6">
          {/* Timeline */}
          {timelineData && (
            <OrderTimeline
              timeline={timelineData}
              enableAnimations={true}
              showEstimatedDates={true}
              showDescriptions={true}
            />
          )}

          {/* Order Items */}
          <OrderItemsSection order={orderData} />
        </div>

        {/* Right column - Delivery, Customer, Payment */}
        <div className="space-y-6">
          {/* Delivery Estimator */}
          {deliveryEstimate && timelineData && (
            <DeliveryEstimator
              order={orderData}
              deliveryEstimate={deliveryEstimate}
              timeline={timelineData}
              showFactors={true}
              showConfidence={true}
              showProgress={true}
              onRefresh={handleRefresh}
              isRefreshing={isRefreshing}
            />
          )}

          {/* Customer Information */}
          <CustomerInfoSection order={orderData} />

          {/* Delivery Address */}
          <DeliveryAddressSection order={orderData} />

          {/* Payment Information */}
          <PaymentInfoSection order={orderData} />
        </div>
      </div>
    </div>
  );
});

OrderDetailPage.displayName = 'OrderDetailPage';

export default OrderDetailPage;