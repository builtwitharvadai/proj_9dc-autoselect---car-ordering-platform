/**
 * Order Detail Modal Component
 * 
 * Modal component for displaying complete order information with fulfillment actions.
 * Provides comprehensive order details, customer information, vehicle configuration,
 * status update controls, and notes management for dealer order processing.
 */

import { Fragment, useState, useCallback, useMemo } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import {
  XMarkIcon,
  TruckIcon,
  UserIcon,
  CreditCardIcon,
  ClipboardDocumentListIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ChatBubbleLeftRightIcon,
} from '@heroicons/react/24/outline';
import type {
  DealerOrderDetail,
  DealerOrderStatus,
  FulfillmentActionType,
} from '../../types/dealer';
import { useOrderFulfillment } from '../../hooks/useDealerOrders';

/**
 * Props for OrderDetailModal component
 */
export interface OrderDetailModalProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly order: DealerOrderDetail | null;
  readonly onActionComplete?: (orderId: string, action: FulfillmentActionType) => void;
  readonly onActionError?: (error: Error) => void;
  readonly className?: string;
}

/**
 * Status badge color mapping
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
 * Available fulfillment actions per status
 */
const AVAILABLE_ACTIONS: Record<DealerOrderStatus, readonly FulfillmentActionType[]> = {
  pending: ['confirm', 'cancel'],
  confirmed: ['start_production', 'cancel'],
  in_production: ['mark_ready', 'cancel'],
  ready_for_pickup: ['complete'],
  completed: [],
  cancelled: [],
} as const;

/**
 * Action button configurations
 */
const ACTION_CONFIG: Record<
  FulfillmentActionType,
  {
    readonly label: string;
    readonly icon: typeof CheckCircleIcon;
    readonly colorClass: string;
  }
> = {
  confirm: {
    label: 'Confirm Order',
    icon: CheckCircleIcon,
    colorClass: 'bg-blue-600 hover:bg-blue-700 text-white',
  },
  start_production: {
    label: 'Start Production',
    icon: TruckIcon,
    colorClass: 'bg-purple-600 hover:bg-purple-700 text-white',
  },
  mark_ready: {
    label: 'Mark Ready',
    icon: CheckCircleIcon,
    colorClass: 'bg-green-600 hover:bg-green-700 text-white',
  },
  complete: {
    label: 'Complete Order',
    icon: CheckCircleIcon,
    colorClass: 'bg-gray-600 hover:bg-gray-700 text-white',
  },
  cancel: {
    label: 'Cancel Order',
    icon: XCircleIcon,
    colorClass: 'bg-red-600 hover:bg-red-700 text-white',
  },
  add_note: {
    label: 'Add Note',
    icon: ChatBubbleLeftRightIcon,
    colorClass: 'bg-gray-600 hover:bg-gray-700 text-white',
  },
} as const;

/**
 * Order Detail Modal Component
 */
export default function OrderDetailModal({
  isOpen,
  onClose,
  order,
  onActionComplete,
  onActionError,
  className = '',
}: OrderDetailModalProps): JSX.Element {
  const [notes, setNotes] = useState('');
  const [estimatedDate, setEstimatedDate] = useState('');
  const [showNoteInput, setShowNoteInput] = useState(false);

  const fulfillmentMutation = useOrderFulfillment({
    onSuccess: (data) => {
      if (order) {
        onActionComplete?.(order.id, data.action);
      }
      setNotes('');
      setEstimatedDate('');
      setShowNoteInput(false);
    },
    onError: (error) => {
      onActionError?.(error);
    },
  });

  /**
   * Handle fulfillment action execution
   */
  const handleAction = useCallback(
    (action: FulfillmentActionType) => {
      if (!order) return;

      fulfillmentMutation.mutate({
        orderId: order.id,
        action,
        notes: notes || undefined,
        estimatedCompletionDate: estimatedDate || undefined,
      });
    },
    [order, notes, estimatedDate, fulfillmentMutation],
  );

  /**
   * Handle note submission
   */
  const handleAddNote = useCallback(() => {
    if (!order || !notes.trim()) return;

    fulfillmentMutation.mutate({
      orderId: order.id,
      action: 'add_note',
      notes: notes.trim(),
    });
  }, [order, notes, fulfillmentMutation]);

  /**
   * Get available actions for current order status
   */
  const availableActions = useMemo(() => {
    if (!order) return [];
    return AVAILABLE_ACTIONS[order.status];
  }, [order]);

  /**
   * Format currency
   */
  const formatCurrency = useCallback((amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  }, []);

  /**
   * Format date
   */
  const formatDate = useCallback((dateString: string): string => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(dateString));
  }, []);

  if (!order) {
    return <Fragment />;
  }

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className={`relative z-50 ${className}`} onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-4xl transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                {/* Header */}
                <div className="flex items-start justify-between mb-6">
                  <div>
                    <Dialog.Title
                      as="h3"
                      className="text-2xl font-semibold leading-6 text-gray-900"
                    >
                      Order #{order.orderNumber}
                    </Dialog.Title>
                    <div className="mt-2 flex items-center gap-2">
                      <span
                        className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[order.status]}`}
                      >
                        {STATUS_NAMES[order.status]}
                      </span>
                      <span className="text-sm text-gray-500">
                        Created {formatDate(order.createdAt)}
                      </span>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    onClick={onClose}
                  >
                    <span className="sr-only">Close</span>
                    <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                  </button>
                </div>

                {/* Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Customer Information */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <UserIcon className="h-5 w-5 text-gray-400" />
                      <h4 className="text-lg font-medium text-gray-900">Customer Information</h4>
                    </div>
                    <dl className="space-y-2">
                      <div>
                        <dt className="text-sm font-medium text-gray-500">Name</dt>
                        <dd className="text-sm text-gray-900">{order.customer.name}</dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-gray-500">Email</dt>
                        <dd className="text-sm text-gray-900">{order.customer.email}</dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-gray-500">Phone</dt>
                        <dd className="text-sm text-gray-900">{order.customer.phone}</dd>
                      </div>
                      {order.customer.address && (
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Address</dt>
                          <dd className="text-sm text-gray-900">{order.customer.address}</dd>
                        </div>
                      )}
                    </dl>
                  </div>

                  {/* Vehicle Information */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <TruckIcon className="h-5 w-5 text-gray-400" />
                      <h4 className="text-lg font-medium text-gray-900">Vehicle Information</h4>
                    </div>
                    <div className="mb-3">
                      <img
                        src={order.vehicle.imageUrl}
                        alt={order.vehicleName}
                        className="w-full h-32 object-cover rounded-lg"
                      />
                    </div>
                    <dl className="space-y-2">
                      <div>
                        <dt className="text-sm font-medium text-gray-500">Vehicle</dt>
                        <dd className="text-sm text-gray-900">
                          {order.vehicle.year} {order.vehicle.make} {order.vehicle.model}
                          {order.vehicle.trim && ` ${order.vehicle.trim}`}
                        </dd>
                      </div>
                      {order.vin && (
                        <div>
                          <dt className="text-sm font-medium text-gray-500">VIN</dt>
                          <dd className="text-sm text-gray-900 font-mono">{order.vin}</dd>
                        </div>
                      )}
                      <div>
                        <dt className="text-sm font-medium text-gray-500">Price</dt>
                        <dd className="text-sm text-gray-900">
                          {formatCurrency(order.vehicle.price)}
                        </dd>
                      </div>
                    </dl>
                  </div>

                  {/* Configuration Details */}
                  {order.configuration && (
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <ClipboardDocumentListIcon className="h-5 w-5 text-gray-400" />
                        <h4 className="text-lg font-medium text-gray-900">Configuration</h4>
                      </div>
                      <dl className="space-y-2">
                        {order.configuration.options.length > 0 && (
                          <div>
                            <dt className="text-sm font-medium text-gray-500">Options</dt>
                            <dd className="text-sm text-gray-900">
                              <ul className="list-disc list-inside">
                                {order.configuration.options.map((option, index) => (
                                  <li key={index}>{option}</li>
                                ))}
                              </ul>
                            </dd>
                          </div>
                        )}
                        {order.configuration.packages.length > 0 && (
                          <div>
                            <dt className="text-sm font-medium text-gray-500">Packages</dt>
                            <dd className="text-sm text-gray-900">
                              <ul className="list-disc list-inside">
                                {order.configuration.packages.map((pkg, index) => (
                                  <li key={index}>{pkg}</li>
                                ))}
                              </ul>
                            </dd>
                          </div>
                        )}
                        {Object.keys(order.configuration.customizations).length > 0 && (
                          <div>
                            <dt className="text-sm font-medium text-gray-500">Customizations</dt>
                            <dd className="text-sm text-gray-900">
                              <ul className="list-disc list-inside">
                                {Object.entries(order.configuration.customizations).map(
                                  ([key, value]) => (
                                    <li key={key}>
                                      {key}: {value}
                                    </li>
                                  ),
                                )}
                              </ul>
                            </dd>
                          </div>
                        )}
                      </dl>
                    </div>
                  )}

                  {/* Payment Information */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <CreditCardIcon className="h-5 w-5 text-gray-400" />
                      <h4 className="text-lg font-medium text-gray-900">Payment Information</h4>
                    </div>
                    <dl className="space-y-2">
                      <div>
                        <dt className="text-sm font-medium text-gray-500">Total Amount</dt>
                        <dd className="text-lg font-semibold text-gray-900">
                          {formatCurrency(order.totalAmount)}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-gray-500">Deposit</dt>
                        <dd className="text-sm text-gray-900">
                          {formatCurrency(order.depositAmount)}
                        </dd>
                      </div>
                    </dl>
                  </div>
                </div>

                {/* Status History */}
                {order.statusHistory.length > 0 && (
                  <div className="mt-6 bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <ClockIcon className="h-5 w-5 text-gray-400" />
                      <h4 className="text-lg font-medium text-gray-900">Status History</h4>
                    </div>
                    <div className="space-y-3">
                      {order.statusHistory.map((history, index) => (
                        <div key={index} className="flex items-start gap-3">
                          <div className="flex-shrink-0">
                            <span
                              className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[history.status]}`}
                            >
                              {STATUS_NAMES[history.status]}
                            </span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-gray-900">
                              Changed by {history.changedBy}
                            </p>
                            <p className="text-xs text-gray-500">
                              {formatDate(history.changedAt)}
                            </p>
                            {history.notes && (
                              <p className="mt-1 text-sm text-gray-600">{history.notes}</p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Notes Section */}
                <div className="mt-6 bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <ChatBubbleLeftRightIcon className="h-5 w-5 text-gray-400" />
                      <h4 className="text-lg font-medium text-gray-900">Notes</h4>
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowNoteInput(!showNoteInput)}
                      className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                    >
                      {showNoteInput ? 'Cancel' : 'Add Note'}
                    </button>
                  </div>

                  {showNoteInput && (
                    <div className="mb-4">
                      <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        rows={3}
                        className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                        placeholder="Enter note..."
                      />
                      <button
                        type="button"
                        onClick={handleAddNote}
                        disabled={!notes.trim() || fulfillmentMutation.isPending}
                        className="mt-2 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {fulfillmentMutation.isPending ? 'Adding...' : 'Add Note'}
                      </button>
                    </div>
                  )}

                  {order.notes && (
                    <div className="text-sm text-gray-600 mb-2">
                      <p className="font-medium text-gray-700">Customer Notes:</p>
                      <p>{order.notes}</p>
                    </div>
                  )}

                  {order.dealerNotes && (
                    <div className="text-sm text-gray-600">
                      <p className="font-medium text-gray-700">Dealer Notes:</p>
                      <p>{order.dealerNotes}</p>
                    </div>
                  )}
                </div>

                {/* Action Buttons */}
                {availableActions.length > 0 && (
                  <div className="mt-6 border-t border-gray-200 pt-6">
                    <div className="space-y-4">
                      {availableActions.includes('start_production') && (
                        <div>
                          <label
                            htmlFor="estimated-date"
                            className="block text-sm font-medium text-gray-700 mb-2"
                          >
                            Estimated Completion Date
                          </label>
                          <input
                            type="date"
                            id="estimated-date"
                            value={estimatedDate}
                            onChange={(e) => setEstimatedDate(e.target.value)}
                            className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                          />
                        </div>
                      )}

                      <div className="flex flex-wrap gap-3">
                        {availableActions.map((action) => {
                          const config = ACTION_CONFIG[action];
                          const Icon = config.icon;

                          return (
                            <button
                              key={action}
                              type="button"
                              onClick={() => handleAction(action)}
                              disabled={fulfillmentMutation.isPending}
                              className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed ${config.colorClass}`}
                            >
                              <Icon className="h-5 w-5 mr-2" aria-hidden="true" />
                              {fulfillmentMutation.isPending ? 'Processing...' : config.label}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}