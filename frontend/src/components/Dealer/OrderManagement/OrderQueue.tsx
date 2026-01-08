/**
 * Order Queue Component
 * 
 * Displays dealer-specific orders with comprehensive filtering, sorting, bulk selection,
 * and action capabilities. Implements responsive table design with pagination and
 * real-time updates via WebSocket integration.
 * 
 * Features:
 * - Status-based filtering with multi-select
 * - Search functionality across order numbers and customer names
 * - Bulk selection with action buttons
 * - Responsive table with mobile-optimized layout
 * - Pagination with configurable page sizes
 * - Real-time order updates
 * - Optimistic UI updates for better UX
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import {
  useDealerOrders,
  useBulkOrderOperations,
  type OrderQueueRequest,
  type DealerOrder,
  type DealerOrderStatus,
  type BulkOrderOperationType,
} from '../../hooks/useDealerOrders';
import { useWebSocket } from '../../hooks/useWebSocket';

/**
 * Component props interface
 */
export interface OrderQueueProps {
  readonly dealerId: string;
  readonly className?: string;
  readonly pageSize?: number;
  readonly enableBulkActions?: boolean;
  readonly enableRealtime?: boolean;
  readonly onOrderClick?: (orderId: string) => void;
  readonly onBulkActionComplete?: (successCount: number, failureCount: number) => void;
}

/**
 * Filter state interface
 */
interface FilterState {
  readonly searchQuery: string;
  readonly selectedStatuses: readonly DealerOrderStatus[];
  readonly startDate?: string;
  readonly endDate?: string;
}

/**
 * Sort configuration interface
 */
interface SortConfig {
  readonly field: 'createdAt' | 'updatedAt' | 'orderNumber' | 'totalAmount' | 'status';
  readonly direction: 'asc' | 'desc';
}

/**
 * Available order statuses for filtering
 */
const ORDER_STATUSES: readonly DealerOrderStatus[] = [
  'pending',
  'confirmed',
  'in_production',
  'ready_for_pickup',
  'completed',
  'cancelled',
] as const;

/**
 * Status display names
 */
const STATUS_NAMES: Record<DealerOrderStatus, string> = {
  pending: 'Pending',
  confirmed: 'Confirmed',
  in_production: 'In Production',
  ready_for_pickup: 'Ready for Pickup',
  completed: 'Completed',
  cancelled: 'Cancelled',
} as const;

/**
 * Status badge colors
 */
const STATUS_COLORS: Record<DealerOrderStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  confirmed: 'bg-blue-100 text-blue-800',
  in_production: 'bg-purple-100 text-purple-800',
  ready_for_pickup: 'bg-green-100 text-green-800',
  completed: 'bg-gray-100 text-gray-800',
  cancelled: 'bg-red-100 text-red-800',
} as const;

/**
 * Default page size
 */
const DEFAULT_PAGE_SIZE = 20;

/**
 * Debounce delay for search input (ms)
 */
const SEARCH_DEBOUNCE_MS = 300;

/**
 * Order Queue Component
 */
export default function OrderQueue({
  dealerId,
  className = '',
  pageSize = DEFAULT_PAGE_SIZE,
  enableBulkActions = true,
  enableRealtime = true,
  onOrderClick,
  onBulkActionComplete,
}: OrderQueueProps): JSX.Element {
  // State management
  const [currentPage, setCurrentPage] = useState(1);
  const [filters, setFilters] = useState<FilterState>({
    searchQuery: '',
    selectedStatuses: [],
  });
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    field: 'createdAt',
    direction: 'desc',
  });
  const [selectedOrderIds, setSelectedOrderIds] = useState<Set<string>>(new Set());
  const [searchInput, setSearchInput] = useState('');

  // Debounced search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters((prev) => ({ ...prev, searchQuery: searchInput }));
      setCurrentPage(1);
    }, SEARCH_DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [searchInput]);

  // Build query request
  const queryRequest = useMemo<OrderQueueRequest>(
    () => ({
      filters: {
        dealerId,
        status: filters.selectedStatuses.length > 0 ? filters.selectedStatuses : undefined,
        searchQuery: filters.searchQuery || undefined,
        startDate: filters.startDate,
        endDate: filters.endDate,
      },
      sortOptions: {
        sortBy: sortConfig.field,
        sortDirection: sortConfig.direction,
      },
      page: currentPage,
      pageSize,
    }),
    [dealerId, filters, sortConfig, currentPage, pageSize],
  );

  // Fetch orders
  const {
    data: ordersData,
    isLoading,
    error,
    refetch,
  } = useDealerOrders(queryRequest, {
    staleTime: 30000,
    refetchOnWindowFocus: true,
  });

  // Bulk operations mutation
  const bulkOperationsMutation = useBulkOrderOperations({
    onSuccess: (data) => {
      setSelectedOrderIds(new Set());
      onBulkActionComplete?.(data.successCount, data.failureCount);
    },
  });

  // WebSocket for real-time updates
  useWebSocket({
    enabled: enableRealtime,
    url: `${import.meta.env['VITE_WS_URL'] ?? 'ws://localhost:8000'}/ws/dealer/${dealerId}/orders`,
    onMessage: useCallback(() => {
      void refetch();
    }, [refetch]),
  });

  // Handle status filter toggle
  const handleStatusToggle = useCallback((status: DealerOrderStatus) => {
    setFilters((prev) => {
      const currentStatuses = new Set(prev.selectedStatuses);
      if (currentStatuses.has(status)) {
        currentStatuses.delete(status);
      } else {
        currentStatuses.add(status);
      }
      return {
        ...prev,
        selectedStatuses: Array.from(currentStatuses),
      };
    });
    setCurrentPage(1);
  }, []);

  // Handle sort change
  const handleSortChange = useCallback((field: SortConfig['field']) => {
    setSortConfig((prev) => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  }, []);

  // Handle select all toggle
  const handleSelectAllToggle = useCallback(() => {
    if (!ordersData?.orders) return;

    if (selectedOrderIds.size === ordersData.orders.length) {
      setSelectedOrderIds(new Set());
    } else {
      setSelectedOrderIds(new Set(ordersData.orders.map((order) => order.id)));
    }
  }, [ordersData?.orders, selectedOrderIds.size]);

  // Handle individual order selection
  const handleOrderSelect = useCallback((orderId: string) => {
    setSelectedOrderIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(orderId)) {
        newSet.delete(orderId);
      } else {
        newSet.add(orderId);
      }
      return newSet;
    });
  }, []);

  // Handle bulk action
  const handleBulkAction = useCallback(
    (operation: BulkOrderOperationType, targetStatus?: DealerOrderStatus) => {
      if (selectedOrderIds.size === 0) return;

      bulkOperationsMutation.mutate({
        orderIds: Array.from(selectedOrderIds),
        operation,
        targetStatus,
      });
    },
    [selectedOrderIds, bulkOperationsMutation],
  );

  // Handle order click
  const handleOrderClick = useCallback(
    (orderId: string) => {
      onOrderClick?.(orderId);
    },
    [onOrderClick],
  );

  // Format currency
  const formatCurrency = useCallback((amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  }, []);

  // Format date
  const formatDate = useCallback((dateString: string): string => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(dateString));
  }, []);

  // Render loading state
  if (isLoading && !ordersData) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className={`p-4 bg-red-50 border border-red-200 rounded-lg ${className}`}>
        <p className="text-red-800">Failed to load orders. Please try again.</p>
        <button
          onClick={() => void refetch()}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  const orders = ordersData?.orders ?? [];
  const totalPages = ordersData?.totalPages ?? 1;
  const hasOrders = orders.length > 0;
  const hasSelection = selectedOrderIds.size > 0;
  const isAllSelected = hasOrders && selectedOrderIds.size === orders.length;

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Filters Section */}
      <div className="bg-white p-4 rounded-lg shadow space-y-4">
        {/* Search Input */}
        <div>
          <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
            Search Orders
          </label>
          <input
            id="search"
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search by order number or customer name..."
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Status Filters */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Status</label>
          <div className="flex flex-wrap gap-2">
            {ORDER_STATUSES.map((status) => (
              <button
                key={status}
                onClick={() => handleStatusToggle(status)}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                  filters.selectedStatuses.includes(status)
                    ? STATUS_COLORS[status]
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {STATUS_NAMES[status]}
              </button>
            ))}
          </div>
        </div>

        {/* Active Filters Summary */}
        {(filters.selectedStatuses.length > 0 || filters.searchQuery) && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span>Active filters:</span>
            {filters.selectedStatuses.length > 0 && (
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded">
                {filters.selectedStatuses.length} status{filters.selectedStatuses.length !== 1 ? 'es' : ''}
              </span>
            )}
            {filters.searchQuery && (
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded">
                Search: "{filters.searchQuery}"
              </span>
            )}
            <button
              onClick={() => {
                setFilters({ searchQuery: '', selectedStatuses: [] });
                setSearchInput('');
              }}
              className="text-blue-600 hover:text-blue-800 underline"
            >
              Clear all
            </button>
          </div>
        )}
      </div>

      {/* Bulk Actions Bar */}
      {enableBulkActions && hasSelection && (
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-200 flex items-center justify-between">
          <span className="text-sm font-medium text-blue-900">
            {selectedOrderIds.size} order{selectedOrderIds.size !== 1 ? 's' : ''} selected
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => handleBulkAction('confirm_multiple')}
              disabled={bulkOperationsMutation.isPending}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Confirm Selected
            </button>
            <button
              onClick={() => handleBulkAction('cancel_multiple')}
              disabled={bulkOperationsMutation.isPending}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel Selected
            </button>
            <button
              onClick={() => handleBulkAction('export_selected')}
              disabled={bulkOperationsMutation.isPending}
              className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Export Selected
            </button>
          </div>
        </div>
      )}

      {/* Orders Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {hasOrders ? (
          <>
            {/* Desktop Table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    {enableBulkActions && (
                      <th className="px-6 py-3 text-left">
                        <input
                          type="checkbox"
                          checked={isAllSelected}
                          onChange={handleSelectAllToggle}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                      </th>
                    )}
                    <th
                      onClick={() => handleSortChange('orderNumber')}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    >
                      Order # {sortConfig.field === 'orderNumber' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Customer
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Vehicle
                    </th>
                    <th
                      onClick={() => handleSortChange('status')}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    >
                      Status {sortConfig.field === 'status' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                    </th>
                    <th
                      onClick={() => handleSortChange('totalAmount')}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    >
                      Amount {sortConfig.field === 'totalAmount' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                    </th>
                    <th
                      onClick={() => handleSortChange('createdAt')}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    >
                      Created {sortConfig.field === 'createdAt' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {orders.map((order) => (
                    <tr key={order.id} className="hover:bg-gray-50">
                      {enableBulkActions && (
                        <td className="px-6 py-4 whitespace-nowrap">
                          <input
                            type="checkbox"
                            checked={selectedOrderIds.has(order.id)}
                            onChange={() => handleOrderSelect(order.id)}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          />
                        </td>
                      )}
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                        {order.orderNumber}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{order.customerName}</div>
                        <div className="text-sm text-gray-500">{order.customerEmail}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <img
                            src={order.vehicleImage}
                            alt={order.vehicleName}
                            className="h-10 w-10 rounded object-cover"
                          />
                          <span className="ml-2 text-sm text-gray-900">{order.vehicleName}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${STATUS_COLORS[order.status]}`}>
                          {STATUS_NAMES[order.status]}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatCurrency(order.totalAmount)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(order.createdAt)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <button
                          onClick={() => handleOrderClick(order.id)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards */}
            <div className="md:hidden divide-y divide-gray-200">
              {orders.map((order) => (
                <div key={order.id} className="p-4 space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      {enableBulkActions && (
                        <input
                          type="checkbox"
                          checked={selectedOrderIds.has(order.id)}
                          onChange={() => handleOrderSelect(order.id)}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                      )}
                      <span className="text-sm font-medium text-blue-600">{order.orderNumber}</span>
                    </div>
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${STATUS_COLORS[order.status]}`}>
                      {STATUS_NAMES[order.status]}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <img
                      src={order.vehicleImage}
                      alt={order.vehicleName}
                      className="h-16 w-16 rounded object-cover"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{order.vehicleName}</p>
                      <p className="text-sm text-gray-500 truncate">{order.customerName}</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">{formatDate(order.createdAt)}</span>
                    <span className="font-medium text-gray-900">{formatCurrency(order.totalAmount)}</span>
                  </div>
                  <button
                    onClick={() => handleOrderClick(order.id)}
                    className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    View Details
                  </button>
                </div>
              ))}
            </div>

            {/* Pagination */}
            <div className="bg-gray-50 px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
              <div className="flex-1 flex justify-between sm:hidden">
                <button
                  onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
              <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-gray-700">
                    Showing page <span className="font-medium">{currentPage}</span> of{' '}
                    <span className="font-medium">{totalPages}</span>
                  </p>
                </div>
                <div>
                  <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                    <button
                      onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                      disabled={currentPage === 1}
                      className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                      disabled={currentPage === totalPages}
                      className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="text-center py-12">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No orders found</h3>
            <p className="mt-1 text-sm text-gray-500">
              {filters.searchQuery || filters.selectedStatuses.length > 0
                ? 'Try adjusting your filters'
                : 'Orders will appear here when customers place them'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}