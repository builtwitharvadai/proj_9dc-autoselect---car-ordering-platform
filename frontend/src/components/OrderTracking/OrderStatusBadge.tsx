/**
 * Order Status Badge Component
 * 
 * Displays order status with appropriate color coding, icons, and accessibility features.
 * Supports all order statuses with consistent styling and responsive design.
 */

import React from 'react';
import {
  CheckCircle,
  Clock,
  Package,
  Truck,
  XCircle,
  AlertCircle,
  PauseCircle,
  RotateCcw,
} from 'lucide-react';
import type { OrderStatus } from '../../../types/orders';

/**
 * Props for OrderStatusBadge component
 */
export interface OrderStatusBadgeProps {
  /** Current order status */
  readonly status: OrderStatus;
  /** Optional additional CSS classes */
  readonly className?: string;
  /** Show icon alongside text */
  readonly showIcon?: boolean;
  /** Size variant */
  readonly size?: 'sm' | 'md' | 'lg';
  /** Optional click handler */
  readonly onClick?: () => void;
  /** Optional aria-label override */
  readonly ariaLabel?: string;
}

/**
 * Status configuration mapping
 */
interface StatusConfig {
  readonly label: string;
  readonly icon: React.ComponentType<{ className?: string }>;
  readonly colorClasses: string;
  readonly ariaLabel: string;
}

/**
 * Status configuration map with colors, icons, and labels
 */
const STATUS_CONFIG: Record<OrderStatus, StatusConfig> = {
  pending: {
    label: 'Pending',
    icon: Clock,
    colorClasses: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    ariaLabel: 'Order status: Pending',
  },
  payment_processing: {
    label: 'Processing Payment',
    icon: Clock,
    colorClasses: 'bg-blue-100 text-blue-800 border-blue-200',
    ariaLabel: 'Order status: Processing Payment',
  },
  confirmed: {
    label: 'Confirmed',
    icon: CheckCircle,
    colorClasses: 'bg-green-100 text-green-800 border-green-200',
    ariaLabel: 'Order status: Confirmed',
  },
  in_production: {
    label: 'In Production',
    icon: Package,
    colorClasses: 'bg-purple-100 text-purple-800 border-purple-200',
    ariaLabel: 'Order status: In Production',
  },
  quality_check: {
    label: 'Quality Check',
    icon: AlertCircle,
    colorClasses: 'bg-indigo-100 text-indigo-800 border-indigo-200',
    ariaLabel: 'Order status: Quality Check',
  },
  ready_for_shipment: {
    label: 'Ready for Shipment',
    icon: Package,
    colorClasses: 'bg-teal-100 text-teal-800 border-teal-200',
    ariaLabel: 'Order status: Ready for Shipment',
  },
  shipped: {
    label: 'Shipped',
    icon: Truck,
    colorClasses: 'bg-blue-100 text-blue-800 border-blue-200',
    ariaLabel: 'Order status: Shipped',
  },
  in_transit: {
    label: 'In Transit',
    icon: Truck,
    colorClasses: 'bg-cyan-100 text-cyan-800 border-cyan-200',
    ariaLabel: 'Order status: In Transit',
  },
  out_for_delivery: {
    label: 'Out for Delivery',
    icon: Truck,
    colorClasses: 'bg-lime-100 text-lime-800 border-lime-200',
    ariaLabel: 'Order status: Out for Delivery',
  },
  delivered: {
    label: 'Delivered',
    icon: CheckCircle,
    colorClasses: 'bg-green-100 text-green-800 border-green-200',
    ariaLabel: 'Order status: Delivered',
  },
  cancelled: {
    label: 'Cancelled',
    icon: XCircle,
    colorClasses: 'bg-red-100 text-red-800 border-red-200',
    ariaLabel: 'Order status: Cancelled',
  },
  on_hold: {
    label: 'On Hold',
    icon: PauseCircle,
    colorClasses: 'bg-orange-100 text-orange-800 border-orange-200',
    ariaLabel: 'Order status: On Hold',
  },
  delayed: {
    label: 'Delayed',
    icon: AlertCircle,
    colorClasses: 'bg-amber-100 text-amber-800 border-amber-200',
    ariaLabel: 'Order status: Delayed',
  },
  returned: {
    label: 'Returned',
    icon: RotateCcw,
    colorClasses: 'bg-gray-100 text-gray-800 border-gray-200',
    ariaLabel: 'Order status: Returned',
  },
} as const;

/**
 * Size configuration for badge variants
 */
const SIZE_CONFIG = {
  sm: {
    container: 'px-2 py-1 text-xs',
    icon: 'h-3 w-3',
    gap: 'gap-1',
  },
  md: {
    container: 'px-3 py-1.5 text-sm',
    icon: 'h-4 w-4',
    gap: 'gap-1.5',
  },
  lg: {
    container: 'px-4 py-2 text-base',
    icon: 'h-5 w-5',
    gap: 'gap-2',
  },
} as const;

/**
 * OrderStatusBadge Component
 * 
 * Displays order status with color-coded badge, icon, and accessible label.
 * Supports multiple sizes and optional click interaction.
 */
export default function OrderStatusBadge({
  status,
  className = '',
  showIcon = true,
  size = 'md',
  onClick,
  ariaLabel,
}: OrderStatusBadgeProps): JSX.Element {
  // Get configuration for current status
  const config = STATUS_CONFIG[status];
  const sizeConfig = SIZE_CONFIG[size];
  const Icon = config.icon;

  // Determine if badge is interactive
  const isInteractive = onClick !== undefined;

  // Build CSS classes
  const baseClasses = 'inline-flex items-center font-medium rounded-full border transition-colors';
  const interactiveClasses = isInteractive
    ? 'cursor-pointer hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
    : '';
  const containerClasses = `${baseClasses} ${config.colorClasses} ${sizeConfig.container} ${sizeConfig.gap} ${interactiveClasses} ${className}`;

  // Handle keyboard interaction for interactive badges
  const handleKeyDown = (event: React.KeyboardEvent<HTMLSpanElement>): void => {
    if (isInteractive && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      onClick();
    }
  };

  return (
    <span
      className={containerClasses}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      role={isInteractive ? 'button' : 'status'}
      tabIndex={isInteractive ? 0 : undefined}
      aria-label={ariaLabel ?? config.ariaLabel}
    >
      {showIcon && (
        <Icon
          className={sizeConfig.icon}
          aria-hidden="true"
        />
      )}
      <span>{config.label}</span>
    </span>
  );
}

/**
 * Type guard to check if a string is a valid OrderStatus
 */
export function isValidOrderStatus(status: string): status is OrderStatus {
  return status in STATUS_CONFIG;
}

/**
 * Get status configuration for a given status
 */
export function getStatusConfig(status: OrderStatus): StatusConfig {
  return STATUS_CONFIG[status];
}

/**
 * Get all available order statuses
 */
export function getAllOrderStatuses(): readonly OrderStatus[] {
  return Object.keys(STATUS_CONFIG) as readonly OrderStatus[];
}

/**
 * Check if status represents a completed state
 */
export function isCompletedStatus(status: OrderStatus): boolean {
  return status === 'delivered' || status === 'cancelled' || status === 'returned';
}

/**
 * Check if status represents an active state
 */
export function isActiveStatus(status: OrderStatus): boolean {
  return !isCompletedStatus(status);
}

/**
 * Check if status represents a problem state
 */
export function isProblemStatus(status: OrderStatus): boolean {
  return status === 'cancelled' || status === 'on_hold' || status === 'delayed' || status === 'returned';
}

/**
 * Check if status represents a successful state
 */
export function isSuccessStatus(status: OrderStatus): boolean {
  return status === 'delivered' || status === 'confirmed';
}