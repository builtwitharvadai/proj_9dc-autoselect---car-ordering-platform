import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import InventoryTable from '../../components/Dealer/InventoryTable';
import BulkUploader from '../../components/Dealer/BulkUploader';
import VehicleEditForm from '../../components/Dealer/VehicleEditForm';
import DashboardStats from '../../components/Dealer/DashboardStats';
import type {
  DealerInventoryWithVehicle,
  DealerInventoryFilters,
  DealerDashboardStats as DashboardStatsType,
} from '../../types/dealer';

/**
 * API base URL from environment
 */
const API_BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

/**
 * Dashboard view modes
 */
type DashboardView = 'overview' | 'inventory' | 'upload' | 'edit' | 'orders';

/**
 * API response for inventory list
 */
interface InventoryListResponse {
  readonly inventory: readonly DealerInventoryWithVehicle[];
  readonly total: number;
  readonly page: number;
  readonly pageSize: number;
  readonly totalPages: number;
}

/**
 * API response for dashboard statistics
 */
interface StatsResponse {
  readonly stats: DashboardStatsType;
}

/**
 * Order summary statistics
 */
interface OrderSummaryStats {
  readonly totalOrders: number;
  readonly pendingOrders: number;
  readonly processingOrders: number;
  readonly completedOrders: number;
}

/**
 * Props for the InventoryDashboard component
 */
interface InventoryDashboardProps {
  readonly dealerId: string;
  readonly className?: string;
}

/**
 * Dealer Inventory Management Dashboard
 *
 * Main dashboard page integrating all dealer components with proper layout,
 * navigation, and responsive design. Includes role-based access control.
 *
 * Features:
 * - Real-time inventory statistics
 * - Sortable and filterable inventory table
 * - Bulk CSV upload functionality
 * - Individual vehicle editing
 * - Stock level adjustments
 * - Vehicle status management
 * - Order management navigation
 * - Responsive design for all screen sizes
 * - Role-based access control
 */
export default function InventoryDashboard({
  dealerId,
  className = '',
}: InventoryDashboardProps): JSX.Element {
  // State management
  const [currentView, setCurrentView] = useState<DashboardView>('overview');
  const [inventory, setInventory] = useState<readonly DealerInventoryWithVehicle[]>([]);
  const [stats, setStats] = useState<DashboardStatsType | null>(null);
  const [orderStats, setOrderStats] = useState<OrderSummaryStats | null>(null);
  const [filters, setFilters] = useState<DealerInventoryFilters>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<DealerInventoryWithVehicle | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const navigate = useNavigate();

  /**
   * Fetch inventory data from API
   */
  const fetchInventory = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const queryParams = new URLSearchParams();
      queryParams.append('dealerId', dealerId);

      if (filters.status && filters.status.length > 0) {
        filters.status.forEach((status) => queryParams.append('status', status));
      }
      if (filters.lowStock) {
        queryParams.append('lowStock', 'true');
      }
      if (filters.outOfStock) {
        queryParams.append('outOfStock', 'true');
      }

      const response = await fetch(
        `${API_BASE_URL}/api/v1/dealer/inventory?${queryParams.toString()}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('authToken') ?? ''}`,
          },
        },
      );

      if (!response.ok) {
        if (response.status === 401) {
          navigate('/login');
          return;
        }
        if (response.status === 403) {
          throw new Error('Access denied. Dealer role required.');
        }
        throw new Error(`Failed to fetch inventory: ${response.statusText}`);
      }

      const data = (await response.json()) as InventoryListResponse;
      setInventory(data.inventory);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load inventory';
      setError(errorMessage);
      console.error('Error fetching inventory:', err);
    } finally {
      setIsLoading(false);
    }
  }, [dealerId, filters, navigate]);

  /**
   * Fetch dashboard statistics from API
   */
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/dealer/stats?dealerId=${dealerId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('authToken') ?? ''}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          navigate('/login');
          return;
        }
        throw new Error(`Failed to fetch statistics: ${response.statusText}`);
      }

      const data = (await response.json()) as StatsResponse;
      setStats(data.stats);
    } catch (err) {
      console.error('Error fetching statistics:', err);
    }
  }, [dealerId, navigate]);

  /**
   * Fetch order summary statistics from API
   */
  const fetchOrderStats = useCallback(async () => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/dealer/orders/summary?dealerId=${dealerId}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('authToken') ?? ''}`,
          },
        },
      );

      if (!response.ok) {
        if (response.status === 401) {
          navigate('/login');
          return;
        }
        throw new Error(`Failed to fetch order statistics: ${response.statusText}`);
      }

      const data = (await response.json()) as { readonly stats: OrderSummaryStats };
      setOrderStats(data.stats);
    } catch (err) {
      console.error('Error fetching order statistics:', err);
    }
  }, [dealerId, navigate]);

  /**
   * Refresh all dashboard data
   */
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([fetchInventory(), fetchStats(), fetchOrderStats()]);
    } finally {
      setIsRefreshing(false);
    }
  }, [fetchInventory, fetchStats, fetchOrderStats]);

  /**
   * Handle vehicle edit action
   */
  const handleEdit = useCallback((item: DealerInventoryWithVehicle) => {
    setSelectedItem(item);
    setCurrentView('edit');
  }, []);

  /**
   * Handle vehicle status change
   */
  const handleStatusChange = useCallback(
    async (item: DealerInventoryWithVehicle) => {
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/v1/dealer/inventory/${item.id}/status`,
          {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${localStorage.getItem('authToken') ?? ''}`,
            },
            body: JSON.stringify({
              status: item.status === 'active' ? 'inactive' : 'active',
            }),
          },
        );

        if (!response.ok) {
          throw new Error('Failed to update status');
        }

        await handleRefresh();
      } catch (err) {
        console.error('Error updating status:', err);
        setError(err instanceof Error ? err.message : 'Failed to update status');
      }
    },
    [handleRefresh],
  );

  /**
   * Handle stock level adjustment
   */
  const handleStockAdjust = useCallback(
    async (item: DealerInventoryWithVehicle) => {
      const newStockLevel = prompt(
        `Enter new stock level for ${item.vehicle.make} ${item.vehicle.model} (Current: ${item.stockLevel}):`,
        item.stockLevel.toString(),
      );

      if (newStockLevel === null) return;

      const stockLevel = parseInt(newStockLevel, 10);
      if (isNaN(stockLevel) || stockLevel < 0) {
        alert('Please enter a valid stock level (0 or greater)');
        return;
      }

      try {
        const response = await fetch(
          `${API_BASE_URL}/api/v1/dealer/inventory/${item.id}/stock`,
          {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${localStorage.getItem('authToken') ?? ''}`,
            },
            body: JSON.stringify({ stockLevel }),
          },
        );

        if (!response.ok) {
          throw new Error('Failed to update stock level');
        }

        await handleRefresh();
      } catch (err) {
        console.error('Error updating stock level:', err);
        setError(err instanceof Error ? err.message : 'Failed to update stock level');
      }
    },
    [handleRefresh],
  );

  /**
   * Handle vehicle deletion
   */
  const handleDelete = useCallback(
    async (item: DealerInventoryWithVehicle) => {
      if (
        !confirm(
          `Are you sure you want to delete ${item.vehicle.make} ${item.vehicle.model} (${item.vin})?`,
        )
      ) {
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/dealer/inventory/${item.id}`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('authToken') ?? ''}`,
          },
        });

        if (!response.ok) {
          throw new Error('Failed to delete vehicle');
        }

        await handleRefresh();
      } catch (err) {
        console.error('Error deleting vehicle:', err);
        setError(err instanceof Error ? err.message : 'Failed to delete vehicle');
      }
    },
    [handleRefresh],
  );

  /**
   * Handle bulk actions
   */
  const handleBulkAction = useCallback(
    async (action: 'activate' | 'deactivate' | 'delete', items: readonly DealerInventoryWithVehicle[]) => {
      if (items.length === 0) return;

      const confirmMessage =
        action === 'delete'
          ? `Are you sure you want to delete ${items.length} vehicle(s)?`
          : `Are you sure you want to ${action} ${items.length} vehicle(s)?`;

      if (!confirm(confirmMessage)) return;

      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/dealer/inventory/bulk`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('authToken') ?? ''}`,
          },
          body: JSON.stringify({
            action,
            inventoryIds: items.map((item) => item.id),
          }),
        });

        if (!response.ok) {
          throw new Error(`Failed to ${action} vehicles`);
        }

        await handleRefresh();
      } catch (err) {
        console.error(`Error performing bulk ${action}:`, err);
        setError(err instanceof Error ? err.message : `Failed to ${action} vehicles`);
      }
    },
    [handleRefresh],
  );

  /**
   * Handle upload completion
   */
  const handleUploadComplete = useCallback(
    async (response: {
      readonly uploadId: string;
      readonly successCount: number;
      readonly errorCount: number;
    }) => {
      console.log('Upload completed:', response);
      await handleRefresh();
      setCurrentView('inventory');
    },
    [handleRefresh],
  );

  /**
   * Handle vehicle edit save
   */
  const handleEditSave = useCallback(async () => {
    await handleRefresh();
    setSelectedItem(null);
    setCurrentView('inventory');
  }, [handleRefresh]);

  /**
   * Handle vehicle edit cancel
   */
  const handleEditCancel = useCallback(() => {
    setSelectedItem(null);
    setCurrentView('inventory');
  }, []);

  /**
   * Handle navigation to order management
   */
  const handleNavigateToOrders = useCallback(() => {
    navigate(`/dealer/orders?dealerId=${dealerId}`);
  }, [navigate, dealerId]);

  /**
   * Initial data fetch
   */
  useEffect(() => {
    void fetchInventory();
    void fetchStats();
    void fetchOrderStats();
  }, [fetchInventory, fetchStats, fetchOrderStats]);

  /**
   * Navigation items configuration
   */
  const navigationItems = useMemo(
    () => [
      { id: 'overview' as const, label: 'Overview', icon: '📊' },
      { id: 'inventory' as const, label: 'Inventory', icon: '🚗' },
      { id: 'upload' as const, label: 'Bulk Upload', icon: '📤' },
      { id: 'orders' as const, label: 'Orders', icon: '📦' },
    ],
    [],
  );

  return (
    <div className={`min-h-screen bg-gray-50 ${className}`}>
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Dealer Dashboard</h1>
              <p className="mt-1 text-sm text-gray-500">Manage your vehicle inventory</p>
            </div>
            <button
              type="button"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              aria-label="Refresh dashboard data"
            >
              <svg
                className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              {isRefreshing ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {navigationItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  if (item.id === 'orders') {
                    handleNavigateToOrders();
                  } else {
                    setCurrentView(item.id);
                  }
                }}
                className={`flex items-center gap-2 px-3 py-4 border-b-2 text-sm font-medium transition-colors focus:outline-none ${
                  currentView === item.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                aria-current={currentView === item.id ? 'page' : undefined}
              >
                <span aria-hidden="true">{item.icon}</span>
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start gap-3">
              <svg
                className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5"
                fill="currentColor"
                viewBox="0 0 20 20"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-red-900">Error</h3>
                <p className="mt-1 text-sm text-red-700">{error}</p>
              </div>
              <button
                type="button"
                onClick={() => setError(null)}
                className="text-red-600 hover:text-red-800 focus:outline-none"
                aria-label="Dismiss error"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path
                    fillRule="evenodd"
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* View Content */}
        {currentView === 'overview' && (
          <>
            <DashboardStats
              stats={
                stats ?? {
                  totalVehicles: 0,
                  activeVehicles: 0,
                  inactiveVehicles: 0,
                  soldVehicles: 0,
                  reservedVehicles: 0,
                  lowStockCount: 0,
                  outOfStockCount: 0,
                  totalStockLevel: 0,
                  availableStockLevel: 0,
                  reservedStockLevel: 0,
                  recentUpdates: 0,
                  lastUpdatedAt: new Date().toISOString(),
                }
              }
              isLoading={isLoading}
              onRefresh={handleRefresh}
            />

            {/* Order Summary Section */}
            {orderStats && (
              <div className="mt-8">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-gray-900">Order Summary</h2>
                  <button
                    type="button"
                    onClick={handleNavigateToOrders}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    View All Orders →
                  </button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-white rounded-lg border border-gray-200 p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600">Total Orders</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">
                          {orderStats.totalOrders}
                        </p>
                      </div>
                      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                        <span className="text-2xl">📦</span>
                      </div>
                    </div>
                  </div>
                  <div className="bg-white rounded-lg border border-gray-200 p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600">Pending</p>
                        <p className="text-2xl font-bold text-yellow-600 mt-1">
                          {orderStats.pendingOrders}
                        </p>
                      </div>
                      <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                        <span className="text-2xl">⏳</span>
                      </div>
                    </div>
                  </div>
                  <div className="bg-white rounded-lg border border-gray-200 p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600">Processing</p>
                        <p className="text-2xl font-bold text-blue-600 mt-1">
                          {orderStats.processingOrders}
                        </p>
                      </div>
                      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                        <span className="text-2xl">⚙️</span>
                      </div>
                    </div>
                  </div>
                  <div className="bg-white rounded-lg border border-gray-200 p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-600">Completed</p>
                        <p className="text-2xl font-bold text-green-600 mt-1">
                          {orderStats.completedOrders}
                        </p>
                      </div>
                      <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                        <span className="text-2xl">✅</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {currentView === 'inventory' && (
          <InventoryTable
            inventory={inventory}
            isLoading={isLoading}
            onEdit={handleEdit}
            onStatusChange={handleStatusChange}
            onStockAdjust={handleStockAdjust}
            onDelete={handleDelete}
            onBulkAction={handleBulkAction}
            filters={filters}
            onFilterChange={setFilters}
            enableBulkActions={true}
            enableInlineEdit={true}
          />
        )}

        {currentView === 'upload' && (
          <BulkUploader
            dealerId={dealerId}
            onUploadComplete={handleUploadComplete}
            onUploadError={(err) => setError(err.message)}
          />
        )}

        {currentView === 'edit' && selectedItem && (
          <VehicleEditForm
            item={selectedItem}
            onSave={handleEditSave}
            onCancel={handleEditCancel}
          />
        )}
      </main>
    </div>
  );
}