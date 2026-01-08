/**
 * Fulfillment Controls Component
 * 
 * Provides action controls for individual dealer orders including status updates,
 * note addition, manufacturer coordination, and delivery scheduling with validation
 * and confirmation flows.
 */

import { useState, useCallback, useMemo } from 'react';
import type {
  DealerOrder,
  DealerOrderStatus,
  FulfillmentActionType,
  FulfillmentActionRequest,
} from '../../types/dealer';
import { useOrderFulfillment } from '../../hooks/useDealerOrders';

/**
 * Props for FulfillmentControls component
 */
export interface FulfillmentControlsProps {
  readonly order: DealerOrder;
  readonly onActionComplete?: (orderId: string, newStatus: DealerOrderStatus) => void;
  readonly onActionError?: (error: Error) => void;
  readonly className?: string;
  readonly disabled?: boolean;
  readonly compact?: boolean;
}

/**
 * Action button configuration
 */
interface ActionButton {
  readonly action: FulfillmentActionType;
  readonly label: string;
  readonly icon: string;
  readonly variant: 'primary' | 'secondary' | 'success' | 'warning' | 'danger';
  readonly requiresConfirmation: boolean;
  readonly requiresNote: boolean;
  readonly requiresDate: boolean;
}

/**
 * Confirmation dialog state
 */
interface ConfirmationState {
  readonly isOpen: boolean;
  readonly action: FulfillmentActionType | null;
  readonly notes: string;
  readonly estimatedDate: string;
}

/**
 * Available actions based on order status
 */
const ACTION_CONFIGS: Record<DealerOrderStatus, readonly ActionButton[]> = {
  pending: [
    {
      action: 'confirm',
      label: 'Confirm Order',
      icon: '✓',
      variant: 'success',
      requiresConfirmation: true,
      requiresNote: false,
      requiresDate: true,
    },
    {
      action: 'cancel',
      label: 'Cancel Order',
      icon: '✕',
      variant: 'danger',
      requiresConfirmation: true,
      requiresNote: true,
      requiresDate: false,
    },
  ],
  confirmed: [
    {
      action: 'start_production',
      label: 'Start Production',
      icon: '⚙',
      variant: 'primary',
      requiresConfirmation: true,
      requiresNote: false,
      requiresDate: true,
    },
    {
      action: 'cancel',
      label: 'Cancel Order',
      icon: '✕',
      variant: 'danger',
      requiresConfirmation: true,
      requiresNote: true,
      requiresDate: false,
    },
  ],
  in_production: [
    {
      action: 'mark_ready',
      label: 'Mark Ready for Pickup',
      icon: '📦',
      variant: 'success',
      requiresConfirmation: true,
      requiresNote: false,
      requiresDate: false,
    },
    {
      action: 'add_note',
      label: 'Add Note',
      icon: '📝',
      variant: 'secondary',
      requiresConfirmation: false,
      requiresNote: true,
      requiresDate: false,
    },
  ],
  ready_for_pickup: [
    {
      action: 'complete',
      label: 'Complete Order',
      icon: '✓',
      variant: 'success',
      requiresConfirmation: true,
      requiresNote: false,
      requiresDate: false,
    },
    {
      action: 'add_note',
      label: 'Add Note',
      icon: '📝',
      variant: 'secondary',
      requiresConfirmation: false,
      requiresNote: true,
      requiresDate: false,
    },
  ],
  completed: [
    {
      action: 'add_note',
      label: 'Add Note',
      icon: '📝',
      variant: 'secondary',
      requiresConfirmation: false,
      requiresNote: true,
      requiresDate: false,
    },
  ],
  cancelled: [],
} as const;

/**
 * Button variant styles
 */
const VARIANT_STYLES: Record<ActionButton['variant'], string> = {
  primary: 'bg-blue-600 hover:bg-blue-700 text-white',
  secondary: 'bg-gray-600 hover:bg-gray-700 text-white',
  success: 'bg-green-600 hover:bg-green-700 text-white',
  warning: 'bg-yellow-600 hover:bg-yellow-700 text-white',
  danger: 'bg-red-600 hover:bg-red-700 text-white',
} as const;

/**
 * FulfillmentControls Component
 * 
 * Renders action buttons for order fulfillment with validation and confirmation flows
 */
export default function FulfillmentControls({
  order,
  onActionComplete,
  onActionError,
  className = '',
  disabled = false,
  compact = false,
}: FulfillmentControlsProps): JSX.Element {
  // State management
  const [confirmation, setConfirmation] = useState<ConfirmationState>({
    isOpen: false,
    action: null,
    notes: '',
    estimatedDate: '',
  });

  // Mutation hook for fulfillment actions
  const { mutate: executeFulfillment, isPending } = useOrderFulfillment({
    onSuccess: (response) => {
      setConfirmation({
        isOpen: false,
        action: null,
        notes: '',
        estimatedDate: '',
      });
      onActionComplete?.(response.orderId, response.newStatus);
    },
    onError: (error) => {
      onActionError?.(error);
    },
  });

  // Get available actions for current order status
  const availableActions = useMemo(
    () => ACTION_CONFIGS[order.status] ?? [],
    [order.status],
  );

  // Handle action button click
  const handleActionClick = useCallback((action: ActionButton) => {
    if (action.requiresConfirmation || action.requiresNote || action.requiresDate) {
      setConfirmation({
        isOpen: true,
        action: action.action,
        notes: '',
        estimatedDate: '',
      });
    } else {
      executeAction(action.action, '', '');
    }
  }, []);

  // Execute fulfillment action
  const executeAction = useCallback(
    (action: FulfillmentActionType, notes: string, estimatedDate: string) => {
      const request: FulfillmentActionRequest = {
        orderId: order.id,
        action,
        notes: notes.trim() || undefined,
        estimatedCompletionDate: estimatedDate || undefined,
      };

      executeFulfillment(request);
    },
    [order.id, executeFulfillment],
  );

  // Handle confirmation dialog submit
  const handleConfirmationSubmit = useCallback(() => {
    if (!confirmation.action) return;

    const actionConfig = availableActions.find((a) => a.action === confirmation.action);
    if (!actionConfig) return;

    // Validate required fields
    if (actionConfig.requiresNote && !confirmation.notes.trim()) {
      return;
    }

    if (actionConfig.requiresDate && !confirmation.estimatedDate) {
      return;
    }

    executeAction(confirmation.action, confirmation.notes, confirmation.estimatedDate);
  }, [confirmation, availableActions, executeAction]);

  // Handle confirmation dialog cancel
  const handleConfirmationCancel = useCallback(() => {
    setConfirmation({
      isOpen: false,
      action: null,
      notes: '',
      estimatedDate: '',
    });
  }, []);

  // Get current action config for confirmation dialog
  const currentActionConfig = useMemo(
    () => availableActions.find((a) => a.action === confirmation.action),
    [availableActions, confirmation.action],
  );

  // Render nothing if no actions available
  if (availableActions.length === 0) {
    return <div className={className} />;
  }

  const isDisabled = disabled || isPending;

  return (
    <>
      {/* Action Buttons */}
      <div className={`flex ${compact ? 'gap-2' : 'gap-3'} ${className}`}>
        {availableActions.map((action) => (
          <button
            key={action.action}
            type="button"
            onClick={() => handleActionClick(action)}
            disabled={isDisabled}
            className={`
              ${compact ? 'px-3 py-1.5 text-sm' : 'px-4 py-2'}
              rounded-lg font-medium transition-colors
              disabled:opacity-50 disabled:cursor-not-allowed
              focus:outline-none focus:ring-2 focus:ring-offset-2
              ${VARIANT_STYLES[action.variant]}
            `}
            aria-label={action.label}
          >
            <span className="flex items-center gap-2">
              <span aria-hidden="true">{action.icon}</span>
              <span>{action.label}</span>
            </span>
          </button>
        ))}
      </div>

      {/* Confirmation Dialog */}
      {confirmation.isOpen && currentActionConfig && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirmation-title"
        >
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            {/* Dialog Header */}
            <h2 id="confirmation-title" className="text-xl font-semibold mb-4">
              {currentActionConfig.label}
            </h2>

            {/* Dialog Content */}
            <div className="space-y-4">
              {/* Order Information */}
              <div className="bg-gray-50 rounded-lg p-3 text-sm">
                <p className="font-medium">Order #{order.orderNumber}</p>
                <p className="text-gray-600">{order.customerName}</p>
                <p className="text-gray-600">{order.vehicleName}</p>
              </div>

              {/* Notes Field */}
              {(currentActionConfig.requiresNote || currentActionConfig.action === 'add_note') && (
                <div>
                  <label htmlFor="action-notes" className="block text-sm font-medium mb-2">
                    Notes {currentActionConfig.requiresNote && <span className="text-red-500">*</span>}
                  </label>
                  <textarea
                    id="action-notes"
                    value={confirmation.notes}
                    onChange={(e) =>
                      setConfirmation((prev) => ({ ...prev, notes: e.target.value }))
                    }
                    rows={4}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter notes..."
                    required={currentActionConfig.requiresNote}
                  />
                </div>
              )}

              {/* Estimated Date Field */}
              {currentActionConfig.requiresDate && (
                <div>
                  <label htmlFor="estimated-date" className="block text-sm font-medium mb-2">
                    Estimated Completion Date <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="date"
                    id="estimated-date"
                    value={confirmation.estimatedDate}
                    onChange={(e) =>
                      setConfirmation((prev) => ({ ...prev, estimatedDate: e.target.value }))
                    }
                    min={new Date().toISOString().split('T')[0]}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
              )}
            </div>

            {/* Dialog Actions */}
            <div className="flex gap-3 mt-6">
              <button
                type="button"
                onClick={handleConfirmationCancel}
                disabled={isPending}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmationSubmit}
                disabled={isPending}
                className={`
                  flex-1 px-4 py-2 rounded-lg font-medium
                  disabled:opacity-50 disabled:cursor-not-allowed
                  ${VARIANT_STYLES[currentActionConfig.variant]}
                `}
              >
                {isPending ? 'Processing...' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}