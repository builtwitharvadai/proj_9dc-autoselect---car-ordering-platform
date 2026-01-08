import { useState, useCallback, useMemo } from 'react';
import { useOrders } from '../../hooks/useOrders';
import type { Order, OrderStatus } from '../../types/orders';

/**
 * Order list component props
 */
export interface OrderListProps {
  readonly className?: string;
  readonly userId?: string;
  readonly pageSize?: number;
  readonly enableSearch?: boolean;
  readonly enableFilters?: boolean;
  readonly onOrderClick?: (orderId: string) => void;
}

/**
 * Order status badge color mapping
 */
const STATUS_COLORS: Record<OrderStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  payment_processing: 'bg-blue-100 text-blue-800 border-blue-200',
  confirmed: 'bg-green-100 text-green-800 border-green-200',
  in_production: 'bg-purple-100 text-purple-800 border-purple-200',
  quality_check: 'bg-indigo-100 text-indigo-800 border-indigo-200',
  ready_for_shipment: 'bg-cyan-100 text-cyan-800 border-cyan-200',
  shipped: 'bg-blue-100 text-blue-800 border-blue-200',
  in_transit: 'bg-blue-100 text-blue-800 border-blue-200',
  out_for_delivery: 'bg-green-100 text-green-800 border-green-200',
  delivered: 'bg-green-100 text-green-800 border-green-200',
  cancelled: 'bg-red-100 text-red-800 border-red-200',
  on_hold: 'bg-orange-100 text-orange-800 border-orange-200',
  delayed: 'bg-orange-100 text-orange-800 border-orange-200',
  returned: 'bg-gray-100 text-gray-800 border-gray-200',
} as const;

/**
 * Order list component displaying customer orders with status badges
 * Includes responsive grid layout, search/filter functionality, and pagination
 */
export default function OrderList({
  className = '',
  userId,
  pageSize = 20,
  enableSearch = true,
  enableFilters = true,
  onOrderClick,
}: OrderListProps): JSX.Element {
  // State management
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<OrderStatus | undefined>(undefined);
  const [sortBy, setSortBy] = useState<'createdAt' | 'updatedAt' | 'orderNumber' | 'total'>(
    'createdAt',
  );
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  // Fetch orders with filters
  const {
    data: ordersData,
    isLoading,
    isError,
    error,
  } = useOrders(
    {
      userId,
      status: statusFilter,
      page: currentPage,
      pageSize,
      sortBy,
      sortDirection,
    },
    {
      keepPreviousData: true,
      staleTime: 30000,
    },
  );

  // Filter orders by search query
  const filteredOrders = useMemo(() => {
    if (!ordersData?.orders) {
      return [];
    }

    if (!searchQuery.trim()) {
      return ordersData.orders;
    }

    const query = searchQuery.toLowerCase();
    return ordersData.orders.filter(
      (order) =>
        order.orderNumber.toLowerCase().includes(query) ||
        order.customerInfo.email.toLowerCase().includes(query) ||
        order.customerInfo.firstName.toLowerCase().includes(query) ||
        order.customerInfo.lastName.toLowerCase().includes(query),
    );
  }, [ordersData?.orders, searchQuery]);

  // Handle order click
  const handleOrderClick = useCallback(
    (orderId: string) => {
      if (onOrderClick) {
        onOrderClick(orderId);
      }
    },
    [onOrderClick],
  );

  // Handle search input change
  const handleSearchChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value);
    setCurrentPage(1);
  }, []);

  // Handle status filter change
  const handleStatusFilterChange = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) => {
      const value = event.target.value;
      setStatusFilter(value ? (value as OrderStatus) : undefined);
      setCurrentPage(1);
    },
    [],
  );

  // Handle sort change
  const handleSortChange = useCallback((event: React.ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value as 'createdAt' | 'updatedAt' | 'orderNumber' | 'total';
    setSortBy(value);
    setCurrentPage(1);
  }, []);

  // Handle sort direction toggle
  const handleSortDirectionToggle = useCallback(() => {
    setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    setCurrentPage(1);
  }, []);

  // Handle pagination
  const handlePreviousPage = useCallback(() => {
    setCurrentPage((prev) => Math.max(1, prev - 1));
  }, []);

  const handleNextPage = useCallback(() => {
    if (ordersData && currentPage < ordersData.totalPages) {
      setCurrentPage((prev) => prev + 1);
    }
  }, [ordersData, currentPage]);

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
    }).format(new Date(dateString));
  }, []);

  // Get status badge classes
  const getStatusBadgeClasses = useCallback((status: OrderStatus): string => {
    return `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${STATUS_COLORS[status]}`;
  }, []);

  // Format status text
  const formatStatusText = useCallback((status: OrderStatus): string => {
    return status
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }, []);

  // Loading state
  if (isLoading && !ordersData) {
    return (
      <div className={`flex items-center justify-center min-h-[400px] ${className}`}>
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="text-gray-600">Loading orders...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className={`flex items-center justify-center min-h-[400px] ${className}`}>
        <div className="text-center">
          <div className="text-red-600 mb-2">
            <svg
              className="mx-auto h-12 w-12"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-1">Failed to load orders</h3>
          <p className="text-gray-600">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
        </div>
      </div>
    );
  }

  // Empty state
  if (!filteredOrders.length) {
    return (
      <div className={`${className}`}>
        {/* Search and filters */}
        {(enableSearch || enableFilters) && (
          <div className="mb-6 space-y-4">
            {enableSearch && (
              <div className="relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={handleSearchChange}
                  placeholder="Search by order number, email, or name..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  aria-label="Search orders"
                />
                <svg
                  className="absolute left-3 top-2.5 h-5 w-5 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>
            )}

            {enableFilters && (
              <div className="flex flex-col sm:flex-row gap-4">
                <select
                  value={statusFilter ?? ''}
                  onChange={handleStatusFilterChange}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  aria-label="Filter by status"
                >
                  <option value="">All Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="confirmed">Confirmed</option>
                  <option value="in_production">In Production</option>
                  <option value="shipped">Shipped</option>
                  <option value="delivered">Delivered</option>
                  <option value="cancelled">Cancelled</option>
                </select>

                <select
                  value={sortBy}
                  onChange={handleSortChange}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  aria-label="Sort by"
                >
                  <option value="createdAt">Order Date</option>
                  <option value="updatedAt">Last Updated</option>
                  <option value="orderNumber">Order Number</option>
                  <option value="total">Total Amount</option>
                </select>

                <button
                  onClick={handleSortDirectionToggle}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  aria-label={`Sort ${sortDirection === 'asc' ? 'descending' : 'ascending'}`}
                >
                  <svg
                    className={`h-5 w-5 text-gray-600 transition-transform ${sortDirection === 'desc' ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 11l5-5m0 0l5 5m-5-5v12"
                    />
                  </svg>
                </button>
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
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
            <h3 className="mt-2 text-lg font-medium text-gray-900">No orders found</h3>
            <p className="mt-1 text-gray-600">
              {searchQuery || statusFilter
                ? 'Try adjusting your search or filters'
                : 'You have no orders yet'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`${className}`}>
      {/* Search and filters */}
      {(enableSearch || enableFilters) && (
        <div className="mb-6 space-y-4">
          {enableSearch && (
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={handleSearchChange}
                placeholder="Search by order number, email, or name..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                aria-label="Search orders"
              />
              <svg
                className="absolute left-3 top-2.5 h-5 w-5 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>
          )}

          {enableFilters && (
            <div className="flex flex-col sm:flex-row gap-4">
              <select
                value={statusFilter ?? ''}
                onChange={handleStatusFilterChange}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                aria-label="Filter by status"
              >
                <option value="">All Statuses</option>
                <option value="pending">Pending</option>
                <option value="confirmed">Confirmed</option>
                <option value="in_production">In Production</option>
                <option value="shipped">Shipped</option>
                <option value="delivered">Delivered</option>
                <option value="cancelled">Cancelled</option>
              </select>

              <select
                value={sortBy}
                onChange={handleSortChange}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                aria-label="Sort by"
              >
                <option value="createdAt">Order Date</option>
                <option value="updatedAt">Last Updated</option>
                <option value="orderNumber">Order Number</option>
                <option value="total">Total Amount</option>
              </select>

              <button
                onClick={handleSortDirectionToggle}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                aria-label={`Sort ${sortDirection === 'asc' ? 'descending' : 'ascending'}`}
              >
                <svg
                  className={`h-5 w-5 text-gray-600 transition-transform ${sortDirection === 'desc' ? 'rotate-180' : ''}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M7 11l5-5m0 0l5 5m-5-5v12"
                  />
                </svg>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Order grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredOrders.map((order) => (
          <div
            key={order.id}
            onClick={() => handleOrderClick(order.id)}
            className="bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow cursor-pointer"
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleOrderClick(order.id);
              }
            }}
          >
            <div className="p-6">
              {/* Order header */}
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">{order.orderNumber}</h3>
                  <p className="text-sm text-gray-600">{formatDate(order.createdAt)}</p>
                </div>
                <span className={getStatusBadgeClasses(order.status)}>
                  {formatStatusText(order.status)}
                </span>
              </div>

              {/* Order items */}
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-2">
                  {order.items.length} {order.items.length === 1 ? 'item' : 'items'}
                </p>
                <div className="space-y-2">
                  {order.items.slice(0, 2).map((item) => (
                    <div key={item.id} className="flex items-center space-x-3">
                      <img
                        src={item.vehicleImage}
                        alt={item.vehicleName}
                        className="w-12 h-12 object-cover rounded"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {item.vehicleName}
                        </p>
                        <p className="text-xs text-gray-600">Qty: {item.quantity}</p>
                      </div>
                    </div>
                  ))}
                  {order.items.length > 2 && (
                    <p className="text-xs text-gray-600">+{order.items.length - 2} more</p>
                  )}
                </div>
              </div>

              {/* Order total */}
              <div className="pt-4 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Total</span>
                  <span className="text-lg font-semibold text-gray-900">
                    {formatCurrency(order.total)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {ordersData && ordersData.totalPages > 1 && (
        <div className="mt-8 flex items-center justify-between">
          <div className="text-sm text-gray-600">
            Page {currentPage} of {ordersData.totalPages} ({ordersData.total} total orders)
          </div>
          <div className="flex space-x-2">
            <button
              onClick={handlePreviousPage}
              disabled={currentPage === 1}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              aria-label="Previous page"
            >
              Previous
            </button>
            <button
              onClick={handleNextPage}
              disabled={currentPage === ordersData.totalPages}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              aria-label="Next page"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Loading overlay for pagination */}
      {isLoading && ordersData && (
        <div className="fixed inset-0 bg-black bg-opacity-10 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 shadow-lg">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </div>
      )}
    </div>
  );
}