import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Settings,
  Package,
  DollarSign,
  MapPin,
  BarChart3,
  Shield,
  AlertCircle,
  CheckCircle,
  Clock,
  Users,
  FileText,
  TrendingUp,
  Activity,
  Database,
  Globe,
  Lock,
  Unlock,
  RefreshCw,
  Download,
  Upload,
  Eye,
  EyeOff,
  Bell,
  BellOff,
  Save,
  X,
  ChevronRight,
  Home,
} from 'lucide-react';

/**
 * Props for the ConfigurationManagement page component
 */
interface ConfigurationManagementProps {
  readonly className?: string;
}

/**
 * Navigation item configuration
 */
interface NavigationItem {
  readonly id: string;
  readonly label: string;
  readonly icon: React.ComponentType<{ className?: string }>;
  readonly path: string;
  readonly description: string;
  readonly requiresPermission?: string;
}

/**
 * Quick stat card data
 */
interface QuickStat {
  readonly id: string;
  readonly label: string;
  readonly value: string | number;
  readonly change?: string;
  readonly isPositive?: boolean;
  readonly icon: React.ComponentType<{ className?: string }>;
  readonly color: 'blue' | 'green' | 'purple' | 'orange' | 'red';
}

/**
 * Recent activity item
 */
interface ActivityItem {
  readonly id: string;
  readonly type: 'create' | 'update' | 'delete' | 'status_change';
  readonly title: string;
  readonly description: string;
  readonly timestamp: string;
  readonly user?: string;
}

/**
 * System status indicator
 */
interface SystemStatus {
  readonly component: string;
  readonly status: 'operational' | 'degraded' | 'down';
  readonly message?: string;
  readonly lastChecked: string;
}

/**
 * Configuration Management Page Component
 * Main dashboard for dealer configuration management with navigation to different
 * management sections, quick stats, recent activity, and system status
 */
export default function ConfigurationManagement({
  className = '',
}: ConfigurationManagementProps): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();

  // State management
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [quickStats, setQuickStats] = useState<readonly QuickStat[]>([]);
  const [recentActivity, setRecentActivity] = useState<readonly ActivityItem[]>([]);
  const [systemStatus, setSystemStatus] = useState<readonly SystemStatus[]>([]);
  const [showSystemStatus, setShowSystemStatus] = useState(false);

  /**
   * Navigation items configuration
   */
  const navigationItems: readonly NavigationItem[] = useMemo(
    () => [
      {
        id: 'options',
        label: 'Vehicle Options',
        icon: Settings,
        path: '/dealer/configuration/options',
        description: 'Manage available vehicle options and features',
        requiresPermission: 'canManageOptions',
      },
      {
        id: 'packages',
        label: 'Option Packages',
        icon: Package,
        path: '/dealer/configuration/packages',
        description: 'Configure option packages and bundles',
        requiresPermission: 'canManagePackages',
      },
      {
        id: 'pricing',
        label: 'Pricing Rules',
        icon: DollarSign,
        path: '/dealer/configuration/pricing',
        description: 'Set up pricing rules and discounts',
        requiresPermission: 'canManagePricing',
      },
      {
        id: 'regions',
        label: 'Regional Settings',
        icon: MapPin,
        path: '/dealer/configuration/regions',
        description: 'Configure regional availability and pricing',
        requiresPermission: 'canManageOptions',
      },
      {
        id: 'analytics',
        label: 'Analytics & Reports',
        icon: BarChart3,
        path: '/dealer/configuration/analytics',
        description: 'View performance metrics and reports',
        requiresPermission: 'canViewReports',
      },
      {
        id: 'permissions',
        label: 'Access Control',
        icon: Shield,
        path: '/dealer/configuration/permissions',
        description: 'Manage user permissions and roles',
        requiresPermission: 'canManageUsers',
      },
    ],
    [],
  );

  /**
   * Load dashboard data on mount
   */
  useEffect(() => {
    void loadDashboardData();
  }, []);

  /**
   * Load dashboard data
   */
  const loadDashboardData = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      // TODO: Replace with actual API calls
      // Simulate API delay
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // Mock quick stats
      setQuickStats([
        {
          id: 'active-options',
          label: 'Active Options',
          value: 156,
          change: '+12%',
          isPositive: true,
          icon: Settings,
          color: 'blue',
        },
        {
          id: 'active-packages',
          label: 'Active Packages',
          value: 24,
          change: '+8%',
          isPositive: true,
          icon: Package,
          color: 'green',
        },
        {
          id: 'pricing-rules',
          label: 'Pricing Rules',
          value: 18,
          change: '-2%',
          isPositive: false,
          icon: DollarSign,
          color: 'purple',
        },
        {
          id: 'active-regions',
          label: 'Active Regions',
          value: 5,
          change: '0%',
          isPositive: true,
          icon: MapPin,
          color: 'orange',
        },
      ]);

      // Mock recent activity
      setRecentActivity([
        {
          id: 'activity-1',
          type: 'update',
          title: 'Pricing rule updated',
          description: 'Summer discount package modified',
          timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          user: 'John Doe',
        },
        {
          id: 'activity-2',
          type: 'create',
          title: 'New option added',
          description: 'Premium sound system added to catalog',
          timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
          user: 'Jane Smith',
        },
        {
          id: 'activity-3',
          type: 'update',
          title: 'Regional settings changed',
          description: 'Updated availability for West Coast region',
          timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          user: 'Mike Johnson',
        },
      ]);

      // Mock system status
      setSystemStatus([
        {
          component: 'Configuration API',
          status: 'operational',
          lastChecked: new Date().toISOString(),
        },
        {
          component: 'Pricing Engine',
          status: 'operational',
          lastChecked: new Date().toISOString(),
        },
        {
          component: 'Database',
          status: 'operational',
          lastChecked: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to load dashboard data';
      setError(errorMessage);
      console.error('Dashboard data loading error:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Handle navigation to section
   */
  const handleNavigate = useCallback(
    (path: string): void => {
      navigate(path);
    },
    [navigate],
  );

  /**
   * Handle refresh
   */
  const handleRefresh = useCallback((): void => {
    void loadDashboardData();
  }, [loadDashboardData]);

  /**
   * Format timestamp for display
   */
  const formatTimestamp = useCallback((timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) {
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`;
    }
    if (diffHours < 24) {
      return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
    }
    if (diffDays < 7) {
      return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
    }
    return date.toLocaleDateString();
  }, []);

  /**
   * Get activity icon
   */
  const getActivityIcon = useCallback(
    (type: ActivityItem['type']): React.ComponentType<{ className?: string }> => {
      switch (type) {
        case 'create':
          return CheckCircle;
        case 'update':
          return RefreshCw;
        case 'delete':
          return X;
        case 'status_change':
          return Activity;
        default:
          return FileText;
      }
    },
    [],
  );

  /**
   * Get activity color
   */
  const getActivityColor = useCallback((type: ActivityItem['type']): string => {
    switch (type) {
      case 'create':
        return 'text-green-600 bg-green-100';
      case 'update':
        return 'text-blue-600 bg-blue-100';
      case 'delete':
        return 'text-red-600 bg-red-100';
      case 'status_change':
        return 'text-purple-600 bg-purple-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  }, []);

  /**
   * Get status color
   */
  const getStatusColor = useCallback((status: SystemStatus['status']): string => {
    switch (status) {
      case 'operational':
        return 'text-green-600 bg-green-100';
      case 'degraded':
        return 'text-yellow-600 bg-yellow-100';
      case 'down':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  }, []);

  /**
   * Get status icon
   */
  const getStatusIcon = useCallback(
    (status: SystemStatus['status']): React.ComponentType<{ className?: string }> => {
      switch (status) {
        case 'operational':
          return CheckCircle;
        case 'degraded':
          return AlertCircle;
        case 'down':
          return X;
        default:
          return Clock;
      }
    },
    [],
  );

  /**
   * Render loading state
   */
  if (isLoading) {
    return (
      <div className={`min-h-screen bg-gray-50 ${className}`}>
        <div className="flex h-screen items-center justify-center">
          <div className="text-center">
            <RefreshCw className="mx-auto h-12 w-12 animate-spin text-blue-600" />
            <p className="mt-4 text-lg text-gray-600">Loading dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  /**
   * Render error state
   */
  if (error) {
    return (
      <div className={`min-h-screen bg-gray-50 ${className}`}>
        <div className="flex h-screen items-center justify-center">
          <div className="max-w-md rounded-lg border border-red-200 bg-white p-6 text-center shadow-sm">
            <AlertCircle className="mx-auto h-12 w-12 text-red-600" />
            <h2 className="mt-4 text-xl font-semibold text-gray-900">
              Failed to Load Dashboard
            </h2>
            <p className="mt-2 text-gray-600">{error}</p>
            <button
              type="button"
              onClick={handleRefresh}
              className="mt-6 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
            >
              <RefreshCw className="h-4 w-4" />
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen bg-gray-50 ${className}`}>
      {/* Header */}
      <div className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <button
                  type="button"
                  onClick={() => navigate('/dealer/dashboard')}
                  className="flex items-center gap-1 transition-colors hover:text-gray-700"
                >
                  <Home className="h-4 w-4" />
                  Dashboard
                </button>
                <ChevronRight className="h-4 w-4" />
                <span>Configuration Management</span>
              </div>
              <h1 className="mt-2 text-2xl font-bold text-gray-900">
                Configuration Management
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                Manage vehicle options, packages, pricing rules, and regional settings
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setShowSystemStatus(!showSystemStatus)}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50"
                aria-label="Toggle system status"
              >
                {showSystemStatus ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
                System Status
              </button>
              <button
                type="button"
                onClick={handleRefresh}
                disabled={isLoading}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                aria-label="Refresh dashboard"
              >
                <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* System Status Banner */}
        {showSystemStatus && (
          <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">System Status</h2>
            <div className="space-y-3">
              {systemStatus.map((status) => {
                const StatusIcon = getStatusIcon(status.status);
                return (
                  <div
                    key={status.component}
                    className="flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${getStatusColor(status.status)}`}
                      >
                        <StatusIcon className="h-3 w-3" />
                        {status.status}
                      </span>
                      <span className="text-sm font-medium text-gray-900">
                        {status.component}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">
                      Last checked: {formatTimestamp(status.lastChecked)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Quick Stats */}
        <div className="mb-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {quickStats.map((stat) => {
            const Icon = stat.icon;
            const colorClasses = {
              blue: 'bg-blue-50 text-blue-600',
              green: 'bg-green-50 text-green-600',
              purple: 'bg-purple-50 text-purple-600',
              orange: 'bg-orange-50 text-orange-600',
              red: 'bg-red-50 text-red-600',
            };

            return (
              <div
                key={stat.id}
                className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
              >
                <div className={`mb-4 inline-flex rounded-lg ${colorClasses[stat.color]} p-3`}>
                  <Icon className="h-6 w-6" />
                </div>
                <p className="mb-2 text-sm font-medium text-gray-600">{stat.label}</p>
                <div className="flex items-baseline gap-2">
                  <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
                  {stat.change && (
                    <span
                      className={`inline-flex items-center gap-1 text-sm font-medium ${
                        stat.isPositive ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {stat.isPositive ? (
                        <TrendingUp className="h-4 w-4" />
                      ) : (
                        <TrendingUp className="h-4 w-4 rotate-180" />
                      )}
                      {stat.change}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Navigation Grid */}
        <div className="mb-8">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            Configuration Sections
          </h2>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {navigationItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleNavigate(item.path)}
                  className="group rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm transition-all hover:border-blue-300 hover:shadow-md"
                >
                  <div className="mb-4 inline-flex rounded-lg bg-blue-50 p-3 text-blue-600 transition-colors group-hover:bg-blue-100">
                    <Icon className="h-6 w-6" />
                  </div>
                  <h3 className="mb-2 text-base font-semibold text-gray-900 transition-colors group-hover:text-blue-600">
                    {item.label}
                  </h3>
                  <p className="text-sm text-gray-500">{item.description}</p>
                  <div className="mt-4 flex items-center gap-2 text-sm font-medium text-blue-600">
                    Manage
                    <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Recent Activity</h2>
            <button
              type="button"
              onClick={() => navigate('/dealer/configuration/activity')}
              className="text-sm font-medium text-blue-600 transition-colors hover:text-blue-700"
            >
              View All
            </button>
          </div>
          <div className="space-y-4">
            {recentActivity.length === 0 ? (
              <div className="py-8 text-center">
                <Activity className="mx-auto h-12 w-12 text-gray-400" />
                <p className="mt-2 text-sm text-gray-500">No recent activity</p>
              </div>
            ) : (
              recentActivity.map((activity) => {
                const Icon = getActivityIcon(activity.type);
                return (
                  <div key={activity.id} className="flex items-start gap-4">
                    <div className={`rounded-lg ${getActivityColor(activity.type)} p-2`}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{activity.title}</p>
                      <p className="text-sm text-gray-500">{activity.description}</p>
                      <div className="mt-1 flex items-center gap-2 text-xs text-gray-400">
                        {activity.user && (
                          <>
                            <Users className="h-3 w-3" />
                            <span>{activity.user}</span>
                            <span>•</span>
                          </>
                        )}
                        <Clock className="h-3 w-3" />
                        <span>{formatTimestamp(activity.timestamp)}</span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}