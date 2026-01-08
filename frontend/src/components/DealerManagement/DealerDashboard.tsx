import React, { useState, useMemo, useCallback } from 'react';
import {
  Settings,
  Package,
  DollarSign,
  BarChart3,
  Upload,
  Download,
  Filter,
  Search,
  RefreshCw,
  Plus,
  Edit,
  Trash2,
  Eye,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  TrendingDown,
  Users,
  MapPin,
  Calendar,
  FileText,
  Save,
  X,
} from 'lucide-react';
import type {
  DealerConfiguration,
  PricingRule,
  RegionSettings,
  RuleStatus,
  ConfigurationRuleType,
  RuleScope,
} from '../../types/dealerManagement';

/**
 * Props for the DealerDashboard component
 */
interface DealerDashboardProps {
  readonly dealerId: string;
  readonly dealerName: string;
  readonly className?: string;
  readonly onConfigurationChange?: (config: DealerConfiguration) => void;
  readonly onError?: (error: Error) => void;
}

/**
 * Dashboard tab types
 */
type DashboardTab =
  | 'overview'
  | 'options'
  | 'packages'
  | 'pricing'
  | 'regions'
  | 'analytics';

/**
 * Tab configuration
 */
interface TabConfig {
  readonly id: DashboardTab;
  readonly label: string;
  readonly icon: React.ComponentType<{ className?: string }>;
  readonly description: string;
}

/**
 * Filter state for lists
 */
interface FilterState {
  readonly search: string;
  readonly status?: RuleStatus;
  readonly type?: ConfigurationRuleType;
  readonly scope?: RuleScope;
}

/**
 * Main dealer management dashboard component
 * Provides comprehensive interface for managing vehicle options, packages,
 * pricing rules, and regional settings with role-based access control
 */
export default function DealerDashboard({
  dealerId,
  dealerName,
  className = '',
  onConfigurationChange,
  onError,
}: DealerDashboardProps): JSX.Element {
  // State management
  const [activeTab, setActiveTab] = useState<DashboardTab>('overview');
  const [isLoading, setIsLoading] = useState(false);
  const [filters, setFilters] = useState<FilterState>({
    search: '',
  });
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);

  // Mock data - in production, this would come from API
  const [configuration] = useState<DealerConfiguration>({
    id: 'config-1',
    dealerId,
    dealerName,
    regionId: 'region-1',
    availableVehicles: [],
    availableOptions: [],
    availablePackages: [],
    pricingRules: [],
    customPricing: [],
    inventorySettings: {
      autoReserveInventory: true,
      reservationDurationMinutes: 15,
      lowStockThreshold: 5,
      allowBackorders: false,
      maxBackorderQuantity: 0,
      notifyOnLowStock: true,
      notifyOnOutOfStock: true,
    },
    displaySettings: {
      showMSRP: true,
      showDealerPrice: true,
      showSavings: true,
      showInventoryCount: true,
      highlightPopularOptions: true,
      defaultSortOrder: 'popularity',
      itemsPerPage: 20,
      enableComparison: true,
      maxComparisonItems: 3,
    },
    notificationSettings: {
      emailNotifications: true,
      smsNotifications: false,
      notifyOnNewOrder: true,
      notifyOnInventoryChange: true,
      notifyOnPriceChange: true,
      notifyOnConfigurationUpdate: false,
      notificationRecipients: [],
    },
    permissions: {
      canManageInventory: true,
      canManagePricing: true,
      canManageOptions: true,
      canManagePackages: true,
      canViewReports: true,
      canExportData: true,
      canImportData: true,
      canManageUsers: false,
    },
    isActive: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  });

  /**
   * Tab configurations
   */
  const tabs: readonly TabConfig[] = useMemo(
    () => [
      {
        id: 'overview',
        label: 'Overview',
        icon: BarChart3,
        description: 'Dashboard overview and key metrics',
      },
      {
        id: 'options',
        label: 'Options',
        icon: Settings,
        description: 'Manage vehicle options and features',
      },
      {
        id: 'packages',
        label: 'Packages',
        icon: Package,
        description: 'Configure option packages and bundles',
      },
      {
        id: 'pricing',
        label: 'Pricing Rules',
        icon: DollarSign,
        description: 'Set up pricing rules and discounts',
      },
      {
        id: 'regions',
        label: 'Regional Settings',
        icon: MapPin,
        description: 'Configure regional availability and pricing',
      },
      {
        id: 'analytics',
        label: 'Analytics',
        icon: TrendingUp,
        description: 'View performance metrics and reports',
      },
    ],
    [],
  );

  /**
   * Handle tab change
   */
  const handleTabChange = useCallback((tab: DashboardTab) => {
    setActiveTab(tab);
    setSelectedItems(new Set());
    setFilters({ search: '' });
  }, []);

  /**
   * Handle filter change
   */
  const handleFilterChange = useCallback(
    (updates: Partial<FilterState>) => {
      setFilters((prev) => ({ ...prev, ...updates }));
    },
    [],
  );

  /**
   * Handle bulk action
   */
  const handleBulkAction = useCallback(
    async (action: string) => {
      if (selectedItems.size === 0) {
        return;
      }

      setIsLoading(true);
      try {
        // Implement bulk action logic
        console.log(`Performing ${action} on ${selectedItems.size} items`);
        setSelectedItems(new Set());
      } catch (error) {
        if (onError) {
          onError(
            error instanceof Error ? error : new Error('Bulk action failed'),
          );
        }
      } finally {
        setIsLoading(false);
      }
    },
    [selectedItems, onError],
  );

  /**
   * Handle export
   */
  const handleExport = useCallback(async () => {
    setIsLoading(true);
    try {
      // Implement export logic
      console.log('Exporting configuration data');
    } catch (error) {
      if (onError) {
        onError(
          error instanceof Error ? error : new Error('Export failed'),
        );
      }
    } finally {
      setIsLoading(false);
    }
  }, [onError]);

  /**
   * Handle import
   */
  const handleImport = useCallback(async () => {
    setIsLoading(true);
    try {
      // Implement import logic
      console.log('Importing configuration data');
    } catch (error) {
      if (onError) {
        onError(
          error instanceof Error ? error : new Error('Import failed'),
        );
      }
    } finally {
      setIsLoading(false);
    }
  }, [onError]);

  /**
   * Render tab content
   */
  const renderTabContent = useCallback(() => {
    switch (activeTab) {
      case 'overview':
        return (
          <div className="space-y-6">
            {/* Quick Stats */}
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                icon={Package}
                label="Active Options"
                value="156"
                change="+12%"
                isPositive={true}
                color="blue"
              />
              <StatCard
                icon={Settings}
                label="Active Packages"
                value="24"
                change="+8%"
                isPositive={true}
                color="green"
              />
              <StatCard
                icon={DollarSign}
                label="Pricing Rules"
                value="18"
                change="-2%"
                isPositive={false}
                color="purple"
              />
              <StatCard
                icon={MapPin}
                label="Active Regions"
                value="5"
                change="0%"
                isPositive={true}
                color="orange"
              />
            </div>

            {/* Recent Activity */}
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-gray-900">
                Recent Activity
              </h3>
              <div className="space-y-4">
                <ActivityItem
                  icon={Edit}
                  title="Pricing rule updated"
                  description="Summer discount package modified"
                  timestamp="2 hours ago"
                  type="update"
                />
                <ActivityItem
                  icon={Plus}
                  title="New option added"
                  description="Premium sound system added to catalog"
                  timestamp="5 hours ago"
                  type="create"
                />
                <ActivityItem
                  icon={Settings}
                  title="Regional settings changed"
                  description="Updated availability for West Coast region"
                  timestamp="1 day ago"
                  type="update"
                />
              </div>
            </div>
          </div>
        );

      case 'options':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                Vehicle Options Management
              </h3>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setShowFilters(!showFilters)}
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50"
                >
                  <Filter className="h-4 w-4" />
                  Filters
                </button>
                <button
                  type="button"
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
                >
                  <Plus className="h-4 w-4" />
                  Add Option
                </button>
              </div>
            </div>

            {showFilters && (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Search
                    </label>
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                      <input
                        type="text"
                        value={filters.search}
                        onChange={(e) =>
                          handleFilterChange({ search: e.target.value })
                        }
                        placeholder="Search options..."
                        className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Status
                    </label>
                    <select
                      value={filters.status ?? ''}
                      onChange={(e) =>
                        handleFilterChange({
                          status: e.target.value as RuleStatus,
                        })
                      }
                      className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      <option value="">All Status</option>
                      <option value="active">Active</option>
                      <option value="inactive">Inactive</option>
                      <option value="scheduled">Scheduled</option>
                      <option value="expired">Expired</option>
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Category
                    </label>
                    <select className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500">
                      <option value="">All Categories</option>
                      <option value="exterior">Exterior</option>
                      <option value="interior">Interior</option>
                      <option value="technology">Technology</option>
                      <option value="safety">Safety</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-gray-200 bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        Option Name
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        Category
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        Price
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 bg-white">
                    <tr className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                      </td>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">
                        Premium Sound System
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        Technology
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        $1,200
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                          <CheckCircle className="h-3 w-3" />
                          Active
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex gap-2">
                          <button
                            type="button"
                            className="text-blue-600 hover:text-blue-700"
                            aria-label="Edit option"
                          >
                            <Edit className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            className="text-gray-600 hover:text-gray-700"
                            aria-label="View option"
                          >
                            <Eye className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            className="text-red-600 hover:text-red-700"
                            aria-label="Delete option"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        );

      case 'packages':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                Package Configuration
              </h3>
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
              >
                <Plus className="h-4 w-4" />
                Create Package
              </button>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <PackageCard
                name="Technology Package"
                description="Advanced tech features bundle"
                optionCount={5}
                price={3500}
                discount={15}
                status="active"
              />
              <PackageCard
                name="Safety Package"
                description="Comprehensive safety features"
                optionCount={7}
                price={2800}
                discount={10}
                status="active"
              />
            </div>
          </div>
        );

      case 'pricing':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                Pricing Rules Management
              </h3>
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
              >
                <Plus className="h-4 w-4" />
                Add Rule
              </button>
            </div>

            <div className="space-y-4">
              <PricingRuleCard
                name="Summer Promotion"
                type="discount"
                scope="global"
                status="active"
                effectiveFrom="2024-06-01"
                effectiveTo="2024-08-31"
                priority={1}
              />
              <PricingRuleCard
                name="Regional Adjustment"
                type="pricing"
                scope="regional"
                status="active"
                effectiveFrom="2024-01-01"
                priority={2}
              />
            </div>
          </div>
        );

      case 'regions':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                Regional Settings
              </h3>
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
              >
                <Plus className="h-4 w-4" />
                Add Region
              </button>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <RegionCard
                name="West Coast"
                code="US-WC"
                currency="USD"
                taxRate={8.5}
                optionCount={145}
                packageCount={22}
                isActive={true}
              />
              <RegionCard
                name="East Coast"
                code="US-EC"
                currency="USD"
                taxRate={7.0}
                optionCount={138}
                packageCount={20}
                isActive={true}
              />
            </div>
          </div>
        );

      case 'analytics':
        return (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-gray-900">
              Performance Analytics
            </h3>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
                <h4 className="mb-4 text-base font-semibold text-gray-900">
                  Popular Options
                </h4>
                <div className="space-y-3">
                  <AnalyticsItem
                    label="Premium Sound System"
                    value="342"
                    percentage={85}
                  />
                  <AnalyticsItem
                    label="Leather Seats"
                    value="298"
                    percentage={74}
                  />
                  <AnalyticsItem
                    label="Sunroof"
                    value="256"
                    percentage={64}
                  />
                </div>
              </div>

              <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
                <h4 className="mb-4 text-base font-semibold text-gray-900">
                  Package Performance
                </h4>
                <div className="space-y-3">
                  <AnalyticsItem
                    label="Technology Package"
                    value="156"
                    percentage={92}
                  />
                  <AnalyticsItem
                    label="Safety Package"
                    value="134"
                    percentage={79}
                  />
                  <AnalyticsItem
                    label="Comfort Package"
                    value="98"
                    percentage={58}
                  />
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  }, [activeTab, filters, showFilters, handleFilterChange]);

  return (
    <div className={`min-h-screen bg-gray-50 ${className}`}>
      {/* Header */}
      <div className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Dealer Management
              </h1>
              <p className="mt-1 text-sm text-gray-500">{dealerName}</p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleImport}
                disabled={isLoading || !configuration.permissions.canImportData}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Upload className="h-4 w-4" />
                Import
              </button>
              <button
                type="button"
                onClick={handleExport}
                disabled={isLoading || !configuration.permissions.canExportData}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Download className="h-4 w-4" />
                Export
              </button>
              <button
                type="button"
                onClick={() => window.location.reload()}
                disabled={isLoading}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <RefreshCw
                  className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`}
                />
                Refresh
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="mt-6 border-b border-gray-200">
            <nav className="-mb-px flex space-x-8 overflow-x-auto">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => handleTabChange(tab.id)}
                    className={`flex items-center gap-2 whitespace-nowrap border-b-2 px-1 py-4 text-sm font-medium transition-colors ${
                      isActive
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    }`}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <Icon className="h-5 w-5" />
                    {tab.label}
                  </button>
                );
              })}
            </nav>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {renderTabContent()}
      </div>

      {/* Bulk Actions Bar */}
      {selectedItems.size > 0 && (
        <div className="fixed bottom-0 left-0 right-0 border-t border-gray-200 bg-white shadow-lg">
          <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium text-gray-900">
                  {selectedItems.size} item{selectedItems.size === 1 ? '' : 's'}{' '}
                  selected
                </span>
                <button
                  type="button"
                  onClick={() => setSelectedItems(new Set())}
                  className="text-sm text-gray-600 hover:text-gray-700"
                >
                  Clear selection
                </button>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleBulkAction('activate')}
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50"
                >
                  <CheckCircle className="h-4 w-4" />
                  Activate
                </button>
                <button
                  type="button"
                  onClick={() => handleBulkAction('deactivate')}
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50"
                >
                  <XCircle className="h-4 w-4" />
                  Deactivate
                </button>
                <button
                  type="button"
                  onClick={() => handleBulkAction('delete')}
                  className="inline-flex items-center gap-2 rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 shadow-sm transition-colors hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Stat card component
 */
interface StatCardProps {
  readonly icon: React.ComponentType<{ className?: string }>;
  readonly label: string;
  readonly value: string;
  readonly change: string;
  readonly isPositive: boolean;
  readonly color: 'blue' | 'green' | 'purple' | 'orange';
}

function StatCard({
  icon: Icon,
  label,
  value,
  change,
  isPositive,
  color,
}: StatCardProps): JSX.Element {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    orange: 'bg-orange-50 text-orange-600',
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className={`mb-4 inline-flex rounded-lg ${colorClasses[color]} p-3`}>
        <Icon className="h-6 w-6" />
      </div>
      <p className="mb-2 text-sm font-medium text-gray-600">{label}</p>
      <div className="flex items-baseline gap-2">
        <p className="text-3xl font-bold text-gray-900">{value}</p>
        <span
          className={`inline-flex items-center gap-1 text-sm font-medium ${
            isPositive ? 'text-green-600' : 'text-red-600'
          }`}
        >
          {isPositive ? (
            <TrendingUp className="h-4 w-4" />
          ) : (
            <TrendingDown className="h-4 w-4" />
          )}
          {change}
        </span>
      </div>
    </div>
  );
}

/**
 * Activity item component
 */
interface ActivityItemProps {
  readonly icon: React.ComponentType<{ className?: string }>;
  readonly title: string;
  readonly description: string;
  readonly timestamp: string;
  readonly type: 'create' | 'update' | 'delete';
}

function ActivityItem({
  icon: Icon,
  title,
  description,
  timestamp,
  type,
}: ActivityItemProps): JSX.Element {
  const typeColors = {
    create: 'bg-green-100 text-green-600',
    update: 'bg-blue-100 text-blue-600',
    delete: 'bg-red-100 text-red-600',
  };

  return (
    <div className="flex items-start gap-4">
      <div className={`rounded-lg ${typeColors[type]} p-2`}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium text-gray-900">{title}</p>
        <p className="text-sm text-gray-500">{description}</p>
        <p className="mt-1 text-xs text-gray-400">{timestamp}</p>
      </div>
    </div>
  );
}

/**
 * Package card component
 */
interface PackageCardProps {
  readonly name: string;
  readonly description: string;
  readonly optionCount: number;
  readonly price: number;
  readonly discount: number;
  readonly status: 'active' | 'inactive';
}

function PackageCard({
  name,
  description,
  optionCount,
  price,
  discount,
  status,
}: PackageCardProps): JSX.Element {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h4 className="text-base font-semibold text-gray-900">{name}</h4>
          <p className="mt-1 text-sm text-gray-500">{description}</p>
        </div>
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${
            status === 'active'
              ? 'bg-green-100 text-green-800'
              : 'bg-gray-100 text-gray-800'
          }`}
        >
          {status === 'active' ? (
            <CheckCircle className="h-3 w-3" />
          ) : (
            <XCircle className="h-3 w-3" />
          )}
          {status}
        </span>
      </div>
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Options included</span>
          <span className="font-medium text-gray-900">{optionCount}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Package price</span>
          <span className="font-medium text-gray-900">
            ${price.toLocaleString()}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Discount</span>
          <span className="font-medium text-green-600">{discount}%</span>
        </div>
      </div>
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
        >
          Edit
        </button>
        <button
          type="button"
          className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          View Details
        </button>
      </div>
    </div>
  );
}

/**
 * Pricing rule card component
 */
interface PricingRuleCardProps {
  readonly name: string;
  readonly type: ConfigurationRuleType;
  readonly scope: RuleScope;
  readonly status: RuleStatus;
  readonly effectiveFrom: string;
  readonly effectiveTo?: string;
  readonly priority: number;
}

function PricingRuleCard({
  name,
  type,
  scope,
  status,
  effectiveFrom,
  effectiveTo,
  priority,
}: PricingRuleCardProps): JSX.Element {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h4 className="text-base font-semibold text-gray-900">{name}</h4>
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
              Priority {priority}
            </span>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-800">
              {type}
            </span>
            <span className="inline-flex items-center gap-1 rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-800">
              {scope}
            </span>
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                status === 'active'
                  ? 'bg-green-100 text-green-800'
                  : status === 'scheduled'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-gray-100 text-gray-800'
              }`}
            >
              {status === 'active' ? (
                <CheckCircle className="h-3 w-3" />
              ) : status === 'scheduled' ? (
                <Clock className="h-3 w-3" />
              ) : (
                <XCircle className="h-3 w-3" />
              )}
              {status}
            </span>
          </div>
          <div className="mt-3 flex items-center gap-4 text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              From: {new Date(effectiveFrom).toLocaleDateString()}
            </span>
            {effectiveTo && (
              <span className="flex items-center gap-1">
                To: {new Date(effectiveTo).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            className="text-blue-600 hover:text-blue-700"
            aria-label="Edit rule"
          >
            <Edit className="h-5 w-5" />
          </button>
          <button
            type="button"
            className="text-gray-600 hover:text-gray-700"
            aria-label="View rule"
          >
            <Eye className="h-5 w-5" />
          </button>
          <button
            type="button"
            className="text-red-600 hover:text-red-700"
            aria-label="Delete rule"
          >
            <Trash2 className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Region card component
 */
interface RegionCardProps {
  readonly name: string;
  readonly code: string;
  readonly currency: string;
  readonly taxRate: number;
  readonly optionCount: number;
  readonly packageCount: number;
  readonly isActive: boolean;
}

function RegionCard({
  name,
  code,
  currency,
  taxRate,
  optionCount,
  packageCount,
  isActive,
}: RegionCardProps): JSX.Element {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h4 className="text-base font-semibold text-gray-900">{name}</h4>
          <p className="mt-1 text-sm text-gray-500">{code}</p>
        </div>
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${
            isActive
              ? 'bg-green-100 text-green-800'
              : 'bg-gray-100 text-gray-800'
          }`}
        >
          {isActive ? (
            <CheckCircle className="h-3 w-3" />
          ) : (
            <XCircle className="h-3 w-3" />
          )}
          {isActive ? 'Active' : 'Inactive'}
        </span>
      </div>
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Currency</span>
          <span className="font-medium text-gray-900">{currency}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Tax rate</span>
          <span className="font-medium text-gray-900">{taxRate}%</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Available options</span>
          <span className="font-medium text-gray-900">{optionCount}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Available packages</span>
          <span className="font-medium text-gray-900">{packageCount}</span>
        </div>
      </div>
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
        >
          Edit
        </button>
        <button
          type="button"
          className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          Configure
        </button>
      </div>
    </div>
  );
}

/**
 * Analytics item component
 */
interface AnalyticsItemProps {
  readonly label: string;
  readonly value: string;
  readonly percentage: number;
}

function AnalyticsItem({
  label,
  value,
  percentage,
}: AnalyticsItemProps): JSX.Element {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="font-medium text-gray-900">{label}</span>
        <span className="text-gray-600">{value} selections</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
        <div
          className="h-full rounded-full bg-blue-600 transition-all duration-300"
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={percentage}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${label} popularity`}
        />
      </div>
    </div>
  );
}