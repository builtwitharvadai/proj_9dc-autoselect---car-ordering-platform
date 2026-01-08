import React, { useMemo } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Package,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Activity,
} from 'lucide-react';
import type { DealerDashboardStats } from '../../types/dealer';

/**
 * Props for the DashboardStats component
 */
interface DashboardStatsProps {
  readonly stats: DealerDashboardStats;
  readonly isLoading?: boolean;
  readonly className?: string;
  readonly onRefresh?: () => void;
}

/**
 * Individual stat card configuration
 */
interface StatCard {
  readonly id: string;
  readonly label: string;
  readonly value: number;
  readonly icon: React.ComponentType<{ className?: string }>;
  readonly color: string;
  readonly bgColor: string;
  readonly trend?: {
    readonly value: number;
    readonly isPositive: boolean;
  };
  readonly description?: string;
}

/**
 * Dashboard statistics and analytics component
 * Displays inventory statistics, charts, and key performance indicators
 * Includes total inventory, low stock alerts, and recent activity
 */
export default function DashboardStats({
  stats,
  isLoading = false,
  className = '',
  onRefresh,
}: DashboardStatsProps): JSX.Element {
  /**
   * Calculate derived metrics and trends
   */
  const metrics = useMemo(() => {
    const activePercentage =
      stats.totalVehicles > 0
        ? Math.round((stats.activeVehicles / stats.totalVehicles) * 100)
        : 0;

    const availabilityRate =
      stats.totalStockLevel > 0
        ? Math.round((stats.availableStockLevel / stats.totalStockLevel) * 100)
        : 0;

    const reservationRate =
      stats.totalStockLevel > 0
        ? Math.round((stats.reservedStockLevel / stats.totalStockLevel) * 100)
        : 0;

    return {
      activePercentage,
      availabilityRate,
      reservationRate,
    };
  }, [stats]);

  /**
   * Configure stat cards with data and styling
   */
  const statCards: readonly StatCard[] = useMemo(
    () => [
      {
        id: 'total-vehicles',
        label: 'Total Vehicles',
        value: stats.totalVehicles,
        icon: Package,
        color: 'text-blue-600',
        bgColor: 'bg-blue-50',
        description: 'All vehicles in inventory',
      },
      {
        id: 'active-vehicles',
        label: 'Active Vehicles',
        value: stats.activeVehicles,
        icon: CheckCircle,
        color: 'text-green-600',
        bgColor: 'bg-green-50',
        trend: {
          value: metrics.activePercentage,
          isPositive: metrics.activePercentage >= 70,
        },
        description: `${metrics.activePercentage}% of total inventory`,
      },
      {
        id: 'available-stock',
        label: 'Available Stock',
        value: stats.availableStockLevel,
        icon: Activity,
        color: 'text-emerald-600',
        bgColor: 'bg-emerald-50',
        trend: {
          value: metrics.availabilityRate,
          isPositive: metrics.availabilityRate >= 80,
        },
        description: `${metrics.availabilityRate}% availability rate`,
      },
      {
        id: 'reserved-vehicles',
        label: 'Reserved',
        value: stats.reservedVehicles,
        icon: Clock,
        color: 'text-amber-600',
        bgColor: 'bg-amber-50',
        description: `${stats.reservedStockLevel} units reserved`,
      },
      {
        id: 'low-stock',
        label: 'Low Stock Alerts',
        value: stats.lowStockCount,
        icon: AlertTriangle,
        color: 'text-orange-600',
        bgColor: 'bg-orange-50',
        trend: {
          value: stats.lowStockCount,
          isPositive: false,
        },
        description: 'Vehicles below threshold',
      },
      {
        id: 'out-of-stock',
        label: 'Out of Stock',
        value: stats.outOfStockCount,
        icon: XCircle,
        color: 'text-red-600',
        bgColor: 'bg-red-50',
        trend: {
          value: stats.outOfStockCount,
          isPositive: false,
        },
        description: 'Requires immediate attention',
      },
      {
        id: 'sold-vehicles',
        label: 'Sold Vehicles',
        value: stats.soldVehicles,
        icon: TrendingUp,
        color: 'text-purple-600',
        bgColor: 'bg-purple-50',
        description: 'Total sales',
      },
      {
        id: 'inactive-vehicles',
        label: 'Inactive',
        value: stats.inactiveVehicles,
        icon: TrendingDown,
        color: 'text-gray-600',
        bgColor: 'bg-gray-50',
        description: 'Not currently listed',
      },
    ],
    [stats, metrics],
  );

  /**
   * Format last updated timestamp
   */
  const lastUpdatedText = useMemo(() => {
    if (!stats.lastUpdatedAt) {
      return 'Never updated';
    }

    const date = new Date(stats.lastUpdatedAt);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) {
      return 'Just now';
    }
    if (diffMins < 60) {
      return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`;
    }

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) {
      return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
    }

    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
  }, [stats.lastUpdatedAt]);

  /**
   * Render loading skeleton
   */
  if (isLoading) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="flex items-center justify-between">
          <div className="h-8 w-48 animate-pulse rounded bg-gray-200" />
          <div className="h-10 w-32 animate-pulse rounded bg-gray-200" />
        </div>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <div
              key={`skeleton-${index}`}
              className="animate-pulse rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
            >
              <div className="mb-4 h-12 w-12 rounded-lg bg-gray-200" />
              <div className="mb-2 h-4 w-24 rounded bg-gray-200" />
              <div className="mb-2 h-8 w-16 rounded bg-gray-200" />
              <div className="h-3 w-32 rounded bg-gray-200" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            Inventory Dashboard
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Last updated: {lastUpdatedText}
          </p>
        </div>
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            aria-label="Refresh dashboard statistics"
          >
            <Activity className="h-4 w-4" aria-hidden="true" />
            Refresh
          </button>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => {
          const Icon = card.icon;
          const hasTrend = card.trend !== undefined;
          const trendIcon = hasTrend
            ? card.trend.isPositive
              ? TrendingUp
              : TrendingDown
            : null;
          const TrendIcon = trendIcon;

          return (
            <div
              key={card.id}
              className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
            >
              {/* Icon */}
              <div className={`mb-4 inline-flex rounded-lg ${card.bgColor} p-3`}>
                <Icon className={`h-6 w-6 ${card.color}`} aria-hidden="true" />
              </div>

              {/* Label */}
              <p className="mb-2 text-sm font-medium text-gray-600">
                {card.label}
              </p>

              {/* Value */}
              <div className="mb-2 flex items-baseline gap-2">
                <p className="text-3xl font-bold text-gray-900">
                  {card.value.toLocaleString()}
                </p>
                {hasTrend && TrendIcon && (
                  <span
                    className={`inline-flex items-center gap-1 text-sm font-medium ${
                      card.trend.isPositive ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    <TrendIcon className="h-4 w-4" aria-hidden="true" />
                    {card.trend.value}%
                  </span>
                )}
              </div>

              {/* Description */}
              {card.description && (
                <p className="text-sm text-gray-500">{card.description}</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Stock Health */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">
            Stock Health
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Availability Rate</span>
              <span className="text-sm font-semibold text-gray-900">
                {metrics.availabilityRate}%
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
              <div
                className="h-full rounded-full bg-emerald-500 transition-all duration-300"
                style={{ width: `${metrics.availabilityRate}%` }}
                role="progressbar"
                aria-valuenow={metrics.availabilityRate}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Availability rate"
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Reservation Rate</span>
              <span className="text-sm font-semibold text-gray-900">
                {metrics.reservationRate}%
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
              <div
                className="h-full rounded-full bg-amber-500 transition-all duration-300"
                style={{ width: `${metrics.reservationRate}%` }}
                role="progressbar"
                aria-valuenow={metrics.reservationRate}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Reservation rate"
              />
            </div>
          </div>
        </div>

        {/* Status Distribution */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">
            Status Distribution
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-green-500" />
                <span className="text-sm text-gray-600">Active</span>
              </div>
              <span className="text-sm font-semibold text-gray-900">
                {stats.activeVehicles}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-amber-500" />
                <span className="text-sm text-gray-600">Reserved</span>
              </div>
              <span className="text-sm font-semibold text-gray-900">
                {stats.reservedVehicles}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-purple-500" />
                <span className="text-sm text-gray-600">Sold</span>
              </div>
              <span className="text-sm font-semibold text-gray-900">
                {stats.soldVehicles}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-gray-500" />
                <span className="text-sm text-gray-600">Inactive</span>
              </div>
              <span className="text-sm font-semibold text-gray-900">
                {stats.inactiveVehicles}
              </span>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">
            Recent Activity
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Recent Updates</span>
              <span className="text-sm font-semibold text-gray-900">
                {stats.recentUpdates}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Total Stock</span>
              <span className="text-sm font-semibold text-gray-900">
                {stats.totalStockLevel.toLocaleString()} units
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Available</span>
              <span className="text-sm font-semibold text-emerald-600">
                {stats.availableStockLevel.toLocaleString()} units
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Reserved</span>
              <span className="text-sm font-semibold text-amber-600">
                {stats.reservedStockLevel.toLocaleString()} units
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Alerts Section */}
      {(stats.lowStockCount > 0 || stats.outOfStockCount > 0) && (
        <div className="rounded-lg border border-orange-200 bg-orange-50 p-6">
          <div className="flex items-start gap-3">
            <AlertTriangle
              className="h-6 w-6 flex-shrink-0 text-orange-600"
              aria-hidden="true"
            />
            <div className="flex-1">
              <h3 className="mb-2 text-lg font-semibold text-orange-900">
                Inventory Alerts
              </h3>
              <div className="space-y-2 text-sm text-orange-800">
                {stats.lowStockCount > 0 && (
                  <p>
                    <strong>{stats.lowStockCount}</strong> vehicle
                    {stats.lowStockCount === 1 ? '' : 's'} with low stock levels
                  </p>
                )}
                {stats.outOfStockCount > 0 && (
                  <p>
                    <strong>{stats.outOfStockCount}</strong> vehicle
                    {stats.outOfStockCount === 1 ? '' : 's'} out of stock
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}