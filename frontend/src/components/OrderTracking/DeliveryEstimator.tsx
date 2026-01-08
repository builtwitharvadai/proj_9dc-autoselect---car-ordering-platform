import React, { useMemo } from 'react';
import {
  Calendar,
  Clock,
  TrendingUp,
  Package,
  AlertCircle,
  CheckCircle,
  Info,
} from 'lucide-react';
import type {
  DeliveryEstimate,
  Order,
  OrderTimeline,
} from '../../../types/orders';

/**
 * Props for the DeliveryEstimator component
 */
export interface DeliveryEstimatorProps {
  /** Order data containing delivery information */
  readonly order: Order;
  /** Delivery estimate with confidence levels */
  readonly deliveryEstimate: DeliveryEstimate;
  /** Order timeline for progress calculation */
  readonly timeline: OrderTimeline;
  /** Optional CSS class name */
  readonly className?: string;
  /** Whether to show detailed factors */
  readonly showFactors?: boolean;
  /** Whether to show confidence indicator */
  readonly showConfidence?: boolean;
  /** Whether to show progress percentage */
  readonly showProgress?: boolean;
  /** Callback when estimate is refreshed */
  readonly onRefresh?: () => void;
  /** Whether refresh is in progress */
  readonly isRefreshing?: boolean;
}

/**
 * Confidence level display configuration
 */
const CONFIDENCE_CONFIG = {
  high: {
    label: 'High Confidence',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    icon: CheckCircle,
  },
  medium: {
    label: 'Medium Confidence',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    icon: Info,
  },
  low: {
    label: 'Low Confidence',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    icon: AlertCircle,
  },
} as const;

/**
 * Calculate days until delivery from ISO date string
 */
function calculateDaysUntilDelivery(estimatedDate: string): number {
  const now = new Date();
  const delivery = new Date(estimatedDate);
  const diffTime = delivery.getTime() - now.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return Math.max(0, diffDays);
}

/**
 * Format date for display
 */
function formatDeliveryDate(date: string): string {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date(date));
}

/**
 * Format date range for display
 */
function formatDateRange(earliest: string, latest: string): string {
  const earliestDate = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
  }).format(new Date(earliest));

  const latestDate = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
  }).format(new Date(latest));

  return `${earliestDate} - ${latestDate}`;
}

/**
 * Get progress color based on percentage
 */
function getProgressColor(progress: number): string {
  if (progress >= 75) return 'bg-green-500';
  if (progress >= 50) return 'bg-blue-500';
  if (progress >= 25) return 'bg-yellow-500';
  return 'bg-gray-400';
}

/**
 * DeliveryEstimator component displays estimated delivery date with dynamic updates
 * Shows progress percentage and factors affecting delivery time
 */
export default function DeliveryEstimator({
  order,
  deliveryEstimate,
  timeline,
  className = '',
  showFactors = true,
  showConfidence = true,
  showProgress = true,
  onRefresh,
  isRefreshing = false,
}: DeliveryEstimatorProps): JSX.Element {
  // Calculate derived values
  const daysUntilDelivery = useMemo(
    () => calculateDaysUntilDelivery(deliveryEstimate.estimatedDeliveryDate),
    [deliveryEstimate.estimatedDeliveryDate],
  );

  const progressPercentage = useMemo(
    () => Math.round(timeline.progress * 100),
    [timeline.progress],
  );

  const confidenceConfig = CONFIDENCE_CONFIG[deliveryEstimate.confidence];
  const ConfidenceIcon = confidenceConfig.icon;
  const progressColor = getProgressColor(progressPercentage);

  // Format dates
  const estimatedDateFormatted = formatDeliveryDate(
    deliveryEstimate.estimatedDeliveryDate,
  );
  const dateRange = formatDateRange(
    deliveryEstimate.earliestDeliveryDate,
    deliveryEstimate.latestDeliveryDate,
  );

  // Last updated time
  const lastUpdated = useMemo(() => {
    const date = new Date(deliveryEstimate.lastUpdated);
    return new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: 'numeric',
      hour12: true,
    }).format(date);
  }, [deliveryEstimate.lastUpdated]);

  return (
    <div
      className={`rounded-lg border border-gray-200 bg-white p-6 shadow-sm ${className}`}
      role="region"
      aria-label="Delivery estimate"
    >
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-blue-100 p-2">
            <Package className="h-6 w-6 text-blue-600" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              Estimated Delivery
            </h3>
            <p className="text-sm text-gray-500">
              Order #{order.orderNumber}
            </p>
          </div>
        </div>

        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            disabled={isRefreshing}
            className="rounded-md px-3 py-1.5 text-sm font-medium text-blue-600 transition-colors hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Refresh delivery estimate"
          >
            {isRefreshing ? 'Updating...' : 'Refresh'}
          </button>
        )}
      </div>

      {/* Main Delivery Date */}
      <div className="mb-6">
        <div className="mb-2 flex items-center gap-2">
          <Calendar className="h-5 w-5 text-gray-400" aria-hidden="true" />
          <span className="text-sm font-medium text-gray-700">
            Expected Delivery Date
          </span>
        </div>
        <p className="text-2xl font-bold text-gray-900">
          {estimatedDateFormatted}
        </p>
        <p className="mt-1 text-sm text-gray-600">
          {daysUntilDelivery === 0
            ? 'Arriving today'
            : daysUntilDelivery === 1
              ? 'Arriving tomorrow'
              : `Arriving in ${daysUntilDelivery} days`}
        </p>
      </div>

      {/* Date Range */}
      <div className="mb-6 rounded-md bg-gray-50 p-4">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-gray-500" aria-hidden="true" />
          <span className="text-sm font-medium text-gray-700">
            Delivery Window
          </span>
        </div>
        <p className="mt-1 text-sm text-gray-600">{dateRange}</p>
      </div>

      {/* Progress Bar */}
      {showProgress && (
        <div className="mb-6">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">
              Order Progress
            </span>
            <span className="text-sm font-semibold text-gray-900">
              {progressPercentage}%
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className={`h-full transition-all duration-500 ${progressColor}`}
              style={{ width: `${progressPercentage}%` }}
              role="progressbar"
              aria-valuenow={progressPercentage}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Order progress"
            />
          </div>
          <p className="mt-2 text-xs text-gray-500">
            Current stage: {timeline.currentStage.replace(/_/g, ' ')}
          </p>
        </div>
      )}

      {/* Confidence Indicator */}
      {showConfidence && (
        <div
          className={`mb-6 rounded-md border p-3 ${confidenceConfig.bgColor} ${confidenceConfig.borderColor}`}
        >
          <div className="flex items-center gap-2">
            <ConfidenceIcon
              className={`h-5 w-5 ${confidenceConfig.color}`}
              aria-hidden="true"
            />
            <span className={`text-sm font-medium ${confidenceConfig.color}`}>
              {confidenceConfig.label}
            </span>
          </div>
          <p className="mt-1 text-xs text-gray-600">
            Based on current order status and historical delivery data
          </p>
        </div>
      )}

      {/* Delivery Method */}
      {deliveryEstimate.deliveryMethod && (
        <div className="mb-6">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-gray-500" aria-hidden="true" />
            <span className="text-sm font-medium text-gray-700">
              Delivery Method
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-900">
            {deliveryEstimate.deliveryMethod
              .split('_')
              .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
              .join(' ')}
          </p>
        </div>
      )}

      {/* Tracking Information */}
      {deliveryEstimate.trackingNumber && (
        <div className="mb-6 rounded-md border border-gray-200 bg-gray-50 p-4">
          <div className="mb-2 flex items-center gap-2">
            <Package className="h-4 w-4 text-gray-500" aria-hidden="true" />
            <span className="text-sm font-medium text-gray-700">
              Tracking Information
            </span>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-gray-900">
              <span className="font-medium">Carrier:</span>{' '}
              {deliveryEstimate.carrier ?? 'Not available'}
            </p>
            <p className="text-sm text-gray-900">
              <span className="font-medium">Tracking #:</span>{' '}
              {deliveryEstimate.trackingNumber}
            </p>
          </div>
        </div>
      )}

      {/* Factors Affecting Delivery */}
      {showFactors && deliveryEstimate.factors.length > 0 && (
        <div className="mb-4">
          <h4 className="mb-3 text-sm font-medium text-gray-700">
            Factors Affecting Delivery Time
          </h4>
          <ul className="space-y-2" role="list">
            {deliveryEstimate.factors.map((factor, index) => (
              <li key={index} className="flex items-start gap-2">
                <div className="mt-0.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-blue-500" />
                <span className="text-sm text-gray-600">{factor}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Last Updated */}
      <div className="border-t border-gray-200 pt-4">
        <p className="text-xs text-gray-500">
          Last updated: {lastUpdated}
        </p>
      </div>
    </div>
  );
}