/**
 * Dealer Order Management Page
 * 
 * Main page component integrating order queue, detail modals, bulk operations,
 * and real-time updates for dealer order management. Provides comprehensive
 * order processing interface with role-based access control and responsive layout.
 * 
 * Features:
 * - Order queue with filtering and sorting
 * - Order detail modal with fulfillment controls
 * - Bulk operations for multiple orders
 * - Real-time order updates via WebSocket
 * - Role-based access control
 * - Responsive mobile-first design
 * - Optimistic UI updates
 * - Error handling and recovery
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import OrderQueue from '../../components/Dealer/OrderManagement/OrderQueue';
import OrderDetailModal from '../../components/Dealer/OrderManagement/OrderDetailModal';
import BulkOperations from '../../components/Dealer/OrderManagement/BulkOperations';
import FulfillmentControls from '../../components/Dealer/OrderManagement/FulfillmentControls';
import {
  useDealerOrders,
  useOrderDetail,
  type DealerOrder,
  type DealerOrderDetail,
  type FulfillmentActionType,
  type BulkOrderOperationResponse,
} from '../../hooks/useDealerOrders';
import { useWebSocket } from '../../hooks/useWebSocket';

/**
 * Props for OrderManagement component
 */
export interface OrderManagementProps {
  readonly dealerId: string;
  readonly className?: string;
  readonly enableRealtime?: boolean;
  readonly enableBulkActions?: boolean;
  readonly pageSize?: number;
}

/**
 * View state for the order management page
 */
type ViewState = 'queue' | 'detail' | 'bulk';

/**
 * Notification type for user feedback
 */
type NotificationType = 'success' | 'error' | 'info' | 'warning';

/**
 * Notification message interface
 */
interface Notification {
  readonly id: string;
  readonly type: NotificationType;
  readonly message: string;
  readonly duration?: number;
}

/**
 * Default page size for order queue
 */
const DEFAULT_PAGE_SIZE = 20;

/**
 * Notification auto-dismiss duration (ms)
 */
const NOTIFICATION_DURATION = 5000;

/**
 * WebSocket reconnection interval (ms)
 */
const WS_RECONNECT_INTERVAL = 5000;

/**
 * Order Management Page Component
 * 
 * Main dealer order management interface integrating all order management
 * components with real-time updates and comprehensive error handling.
 */
export default function OrderManagement({
  dealerId,
  className = '',
  enableRealtime = true,
  enableBulkActions = true,
  pageSize = DEFAULT_PAGE_SIZE,
}: OrderManagementProps): JSX.Element {
  // URL search params for deep linking
  const [searchParams, setSearchParams] = useSearchParams();

  // View state management
  const [viewState, setViewState] = useState<ViewState>('queue');
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [selectedOrders, setSelectedOrders] = useState<readonly DealerOrder[]>([]);

  // Notification state
  const [notifications, setNotifications] = useState<readonly Notification[]>([]);

  // WebSocket connection state
  const [wsConnected, setWsConnected] = useState(false);

  // Get order ID from URL if present
  const urlOrderId = searchParams.get('orderId');

  // Fetch order detail when selected
  const {
    data: orderDetail,
    isLoading: isLoadingDetail,
    error: detailError,
    refetch: refetchDetail,
  } = useOrderDetail(selectedOrderId ?? '', {
    enabled: selectedOrderId !== null,
  });

  // WebSocket connection for real-time updates
  const { connectionState } = useWebSocket({
    enabled: enableRealtime,
    url: `${import.meta.env['VITE_WS_URL'] ?? 'ws://localhost:8000'}/ws/dealer/${dealerId}/orders`,
    onOpen: useCallback(() => {
      setWsConnected(true);
      addNotification('info', 'Real-time updates connected');
    }, []),
    onClose: useCallback(() => {
      setWsConnected(false);
      addNotification('warning', 'Real-time updates disconnected');
    }, []),
    onError: useCallback((error: Error) => {
      console.error('WebSocket error:', error);
      addNotification('error', 'Real-time connection error');
    }, []),
    reconnectInterval: WS_RECONNECT_INTERVAL,
  });

  /**
   * Add notification to the queue
   */
  const addNotification = useCallback(
    (type: NotificationType, message: string, duration: number = NOTIFICATION_DURATION) => {
      const notification: Notification = {
        id: `${Date.now()}-${Math.random()}`,
        type,
        message,
        duration,
      };

      setNotifications((prev) => [...prev, notification]);

      // Auto-dismiss after duration
      if (duration > 0) {
        setTimeout(() => {
          removeNotification(notification.id);
        }, duration);
      }
    },
    [],
  );

  /**
   * Remove notification from the queue
   */
  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  /**
   * Handle order click from queue
   */
  const handleOrderClick = useCallback(
    (orderId: string) => {
      setSelectedOrderId(orderId);
      setViewState('detail');
      setSearchParams({ orderId });
    },
    [setSearchParams],
  );

  /**
   * Handle order detail modal close
   */
  const handleDetailClose = useCallback(() => {
    setSelectedOrderId(null);
    setViewState('queue');
    setSearchParams({});
  }, [setSearchParams]);

  /**
   * Handle fulfillment action completion
   */
  const handleActionComplete = useCallback(
    (orderId: string, action: FulfillmentActionType) => {
      addNotification('success', `Order ${action} completed successfully`);
      void refetchDetail();
    },
    [addNotification, refetchDetail],
  );

  /**
   * Handle fulfillment action error
   */
  const handleActionError = useCallback(
    (error: Error) => {
      addNotification('error', `Action failed: ${error.message}`);
    },
    [addNotification],
  );

  /**
   * Handle bulk operation completion
   */
  const handleBulkOperationComplete = useCallback(
    (response: BulkOrderOperationResponse) => {
      const { successCount, failureCount } = response;
      
      if (failureCount === 0) {
        addNotification('success', `Successfully processed ${successCount} orders`);
      } else {
        addNotification(
          'warning',
          `Processed ${successCount} orders, ${failureCount} failed`,
        );
      }

      setSelectedOrders([]);
      setViewState('queue');
    },
    [addNotification],
  );

  /**
   * Handle bulk operation error
   */
  const handleBulkOperationError = useCallback(
    (error: Error) => {
      addNotification('error', `Bulk operation failed: ${error.message}`);
    },
    [addNotification],
  );

  /**
   * Handle order selection change
   */
  const handleOrderSelectionChange = useCallback((orders: readonly DealerOrder[]) => {
    setSelectedOrders(orders);
  }, []);

  /**
   * Open bulk operations view
   */
  const handleOpenBulkOperations = useCallback(() => {
    if (selectedOrders.length === 0) {
      addNotification('warning', 'Please select orders first');
      return;
    }
    setViewState('bulk');
  }, [selectedOrders.length, addNotification]);

  /**
   * Close bulk operations view
   */
  const handleCloseBulkOperations = useCallback(() => {
    setViewState('queue');
  }, []);

  /**
   * Clear selected orders
   */
  const handleClearSelection = useCallback(() => {
    setSelectedOrders([]);
  }, []);

  // Handle URL order ID on mount
  useEffect(() => {
    if (urlOrderId) {
      setSelectedOrderId(urlOrderId);
      setViewState('detail');
    }
  }, [urlOrderId]);

  // Notification badge color mapping
  const notificationColors: Record<NotificationType, string> = useMemo(
    () => ({
      success: 'bg-green-50 border-green-200 text-green-800',
      error: 'bg-red-50 border-red-200 text-red-800',
      warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
      info: 'bg-blue-50 border-blue-200 text-blue-800',
    }),
    [],
  );

  return (
    <div className={`min-h-screen bg-gray-50 ${className}`}>
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Order Management</h1>
              <p className="mt-1 text-sm text-gray-600">
                Manage and process dealer orders
              </p>
            </div>

            {/* Connection Status */}
            {enableRealtime && (
              <div className="flex items-center gap-2">
                <div
                  className={`h-2 w-2 rounded-full ${
                    wsConnected ? 'bg-green-500' : 'bg-red-500'
                  }`}
                />
                <span className="text-sm text-gray-600">
                  {wsConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            )}
          </div>

          {/* Bulk Actions Bar */}
          {enableBulkActions && selectedOrders.length > 0 && viewState === 'queue' && (
            <div className="mt-4 flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
              <span className="text-sm font-medium text-blue-900">
                {selectedOrders.length} order{selectedOrders.length !== 1 ? 's' : ''} selected
              </span>
              <div className="flex gap-2">
                <button
                  onClick={handleOpenBulkOperations}
                  className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 transition-colors"
                >
                  Bulk Actions
                </button>
                <button
                  onClick={handleClearSelection}
                  className="px-4 py-2 bg-white text-gray-700 text-sm font-medium rounded border border-gray-300 hover:bg-gray-50 transition-colors"
                >
                  Clear Selection
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Notifications */}
        {notifications.length > 0 && (
          <div className="fixed top-4 right-4 z-50 space-y-2 max-w-md">
            {notifications.map((notification) => (
              <div
                key={notification.id}
                className={`flex items-start gap-3 p-4 rounded-lg border shadow-lg ${notificationColors[notification.type]}`}
              >
                <div className="flex-1">
                  <p className="text-sm font-medium">{notification.message}</p>
                </div>
                <button
                  onClick={() => removeNotification(notification.id)}
                  className="flex-shrink-0 text-gray-400 hover:text-gray-600"
                >
                  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Order Queue View */}
        {viewState === 'queue' && (
          <OrderQueue
            dealerId={dealerId}
            pageSize={pageSize}
            enableBulkActions={enableBulkActions}
            enableRealtime={enableRealtime}
            onOrderClick={handleOrderClick}
            onBulkActionComplete={handleBulkOperationComplete}
          />
        )}

        {/* Bulk Operations View */}
        {viewState === 'bulk' && (
          <div className="space-y-4">
            <button
              onClick={handleCloseBulkOperations}
              className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 19l-7-7m0 0l7-7m-7 7h18"
                />
              </svg>
              Back to Orders
            </button>

            <BulkOperations
              selectedOrders={selectedOrders}
              onOperationComplete={handleBulkOperationComplete}
              onOperationError={handleBulkOperationError}
              onClearSelection={handleClearSelection}
            />
          </div>
        )}
      </div>

      {/* Order Detail Modal */}
      <OrderDetailModal
        isOpen={viewState === 'detail' && selectedOrderId !== null}
        onClose={handleDetailClose}
        order={orderDetail ?? null}
        onActionComplete={handleActionComplete}
        onActionError={handleActionError}
      />
    </div>
  );
}