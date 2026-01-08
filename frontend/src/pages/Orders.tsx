import { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOrders } from '../hooks/useOrders';
import OrderList from '../components/OrderTracking/OrderList';
import type { OrderStatus } from '../types/orders';

/**
 * Orders page props
 */
export interface OrdersProps {
  readonly className?: string;
}

/**
 * Orders page component - Main entry point for order tracking
 * Displays list of customer orders with search, filtering, and navigation to details
 */
export default function Orders({ className = '' }: OrdersProps): JSX.Element {
  const navigate = useNavigate();

  // State management
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<OrderStatus | undefined>(undefined);
  const [currentPage, setCurrentPage] = useState(1);

  // Fetch orders with current filters
  const {
    data: ordersData,
    isLoading,
    isError,
    error,
  } = useOrders(
    {
      status: statusFilter,
      page: currentPage,
      pageSize: 20,
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

  // Handle order click - navigate to detail page
  const handleOrderClick = useCallback(
    (orderId: string) => {
      navigate(`/orders/${orderId}`);
    },
    [navigate],
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

  // Handle page change
  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  // Loading state
  if (isLoading && !ordersData) {
    return (
      <div className={`min-h-screen bg-gray-50 ${className}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="flex flex-col items-center space-y-4">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <p className="text-gray-600">Loading orders...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className={`min-h-screen bg-gray-50 ${className}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <div className="text-red-600 mb-4">
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
              <h3 className="text-lg font-medium text-gray-900 mb-2">Failed to load orders</h3>
              <p className="text-gray-600 mb-4">
                {error instanceof Error ? error.message : 'An unexpected error occurred'}
              </p>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen bg-gray-50 ${className}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">My Orders</h1>
          <p className="text-gray-600">
            Track and manage your vehicle orders. Click on an order to view detailed information
            and timeline.
          </p>
        </div>

        {/* Search and filters */}
        <div className="mb-6 space-y-4">
          {/* Search input */}
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

          {/* Status filter */}
          <div className="flex flex-col sm:flex-row gap-4">
            <select
              value={statusFilter ?? ''}
              onChange={handleStatusFilterChange}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              aria-label="Filter by status"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="payment_processing">Payment Processing</option>
              <option value="confirmed">Confirmed</option>
              <option value="in_production">In Production</option>
              <option value="quality_check">Quality Check</option>
              <option value="ready_for_shipment">Ready for Shipment</option>
              <option value="shipped">Shipped</option>
              <option value="in_transit">In Transit</option>
              <option value="out_for_delivery">Out for Delivery</option>
              <option value="delivered">Delivered</option>
              <option value="cancelled">Cancelled</option>
              <option value="on_hold">On Hold</option>
              <option value="delayed">Delayed</option>
              <option value="returned">Returned</option>
            </select>
          </div>
        </div>

        {/* Order list */}
        <OrderList
          className="mb-8"
          enableSearch={false}
          enableFilters={false}
          onOrderClick={handleOrderClick}
        />

        {/* Pagination */}
        {ordersData && ordersData.totalPages > 1 && (
          <div className="mt-8 flex items-center justify-between">
            <div className="text-sm text-gray-600">
              Page {currentPage} of {ordersData.totalPages} ({ordersData.total} total orders)
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                aria-label="Previous page"
              >
                Previous
              </button>
              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === ordersData.totalPages}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                aria-label="Next page"
              >
                Next
              </button>
            </div>
          </div>
        )}

        {/* Empty state when no orders match filters */}
        {filteredOrders.length === 0 && ordersData && ordersData.orders.length > 0 && (
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
              <p className="mt-1 text-gray-600">Try adjusting your search or filters</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}