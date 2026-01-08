/**
 * Bulk Operations Component for Dealer Order Management
 * 
 * Provides interface for executing bulk operations on multiple orders including:
 * - Bulk status updates
 * - Bulk order confirmation
 * - Bulk order cancellation
 * - Bulk export functionality
 * 
 * Features:
 * - Action selection with validation
 * - Confirmation dialogs with operation preview
 * - Real-time progress tracking
 * - Detailed results display with error handling
 * - Permission-based action availability
 */

import { useState, useCallback, useMemo } from 'react';
import {
  useBulkOrderOperations,
  type BulkOrderOperationRequest,
  type BulkOrderOperationResponse,
  type BulkOrderOperationType,
  type DealerOrderStatus,
} from '../../hooks/useDealerOrders';
import type { DealerOrder } from '../../types/dealer';

/**
 * Available bulk operation types
 */
const BULK_OPERATIONS: readonly {
  readonly type: BulkOrderOperationType;
  readonly label: string;
  readonly description: string;
  readonly requiresStatus?: boolean;
  readonly requiresNotes?: boolean;
  readonly confirmationRequired: boolean;
  readonly dangerLevel: 'low' | 'medium' | 'high';
}[] = [
  {
    type: 'confirm_multiple',
    label: 'Confirm Orders',
    description: 'Confirm selected pending orders',
    confirmationRequired: true,
    dangerLevel: 'low',
  },
  {
    type: 'cancel_multiple',
    label: 'Cancel Orders',
    description: 'Cancel selected orders',
    requiresNotes: true,
    confirmationRequired: true,
    dangerLevel: 'high',
  },
  {
    type: 'update_status',
    label: 'Update Status',
    description: 'Update status for selected orders',
    requiresStatus: true,
    confirmationRequired: true,
    dangerLevel: 'medium',
  },
  {
    type: 'export_selected',
    label: 'Export Orders',
    description: 'Export selected orders to CSV',
    confirmationRequired: false,
    dangerLevel: 'low',
  },
] as const;

/**
 * Available target statuses for bulk updates
 */
const TARGET_STATUSES: readonly {
  readonly value: DealerOrderStatus;
  readonly label: string;
}[] = [
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'in_production', label: 'In Production' },
  { value: 'ready_for_pickup', label: 'Ready for Pickup' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
] as const;

/**
 * Operation execution state
 */
type OperationState = 'idle' | 'confirming' | 'executing' | 'completed' | 'error';

/**
 * Props for BulkOperations component
 */
export interface BulkOperationsProps {
  readonly selectedOrders: readonly DealerOrder[];
  readonly onOperationComplete?: (response: BulkOrderOperationResponse) => void;
  readonly onOperationError?: (error: Error) => void;
  readonly onClearSelection?: () => void;
  readonly className?: string;
  readonly disabled?: boolean;
}

/**
 * BulkOperations Component
 * 
 * Provides interface for executing bulk operations on multiple dealer orders
 * with validation, confirmation, progress tracking, and results display.
 */
export default function BulkOperations({
  selectedOrders,
  onOperationComplete,
  onOperationError,
  onClearSelection,
  className = '',
  disabled = false,
}: BulkOperationsProps): JSX.Element {
  // State management
  const [operationState, setOperationState] = useState<OperationState>('idle');
  const [selectedOperation, setSelectedOperation] = useState<BulkOrderOperationType | null>(null);
  const [targetStatus, setTargetStatus] = useState<DealerOrderStatus | null>(null);
  const [notes, setNotes] = useState('');
  const [operationResult, setOperationResult] = useState<BulkOrderOperationResponse | null>(null);

  // Bulk operations mutation
  const bulkOperationsMutation = useBulkOrderOperations({
    onSuccess: (response) => {
      setOperationResult(response);
      setOperationState('completed');
      onOperationComplete?.(response);
    },
    onError: (error) => {
      setOperationState('error');
      onOperationError?.(error);
    },
  });

  // Get selected operation details
  const operationDetails = useMemo(() => {
    if (!selectedOperation) return null;
    return BULK_OPERATIONS.find((op) => op.type === selectedOperation) ?? null;
  }, [selectedOperation]);

  // Validate operation can be executed
  const canExecuteOperation = useMemo(() => {
    if (!selectedOperation || selectedOrders.length === 0 || disabled) {
      return false;
    }

    const details = operationDetails;
    if (!details) return false;

    // Check if status is required and provided
    if (details.requiresStatus && !targetStatus) {
      return false;
    }

    // Check if notes are required and provided
    if (details.requiresNotes && notes.trim().length === 0) {
      return false;
    }

    return true;
  }, [selectedOperation, selectedOrders.length, disabled, operationDetails, targetStatus, notes]);

  // Handle operation selection
  const handleOperationSelect = useCallback((operation: BulkOrderOperationType) => {
    setSelectedOperation(operation);
    setTargetStatus(null);
    setNotes('');
    setOperationResult(null);
    setOperationState('idle');
  }, []);

  // Handle confirmation dialog open
  const handleConfirmOperation = useCallback(() => {
    if (!canExecuteOperation) return;
    setOperationState('confirming');
  }, [canExecuteOperation]);

  // Handle operation execution
  const handleExecuteOperation = useCallback(() => {
    if (!selectedOperation || !canExecuteOperation) return;

    setOperationState('executing');

    const request: BulkOrderOperationRequest = {
      orderIds: selectedOrders.map((order) => order.id),
      operation: selectedOperation,
      targetStatus: targetStatus ?? undefined,
      notes: notes.trim() || undefined,
    };

    bulkOperationsMutation.mutate(request);
  }, [selectedOperation, canExecuteOperation, selectedOrders, targetStatus, notes, bulkOperationsMutation]);

  // Handle cancel confirmation
  const handleCancelConfirmation = useCallback(() => {
    setOperationState('idle');
  }, []);

  // Handle reset after completion
  const handleReset = useCallback(() => {
    setSelectedOperation(null);
    setTargetStatus(null);
    setNotes('');
    setOperationResult(null);
    setOperationState('idle');
    onClearSelection?.();
  }, [onClearSelection]);

  // Calculate success rate
  const successRate = useMemo(() => {
    if (!operationResult) return 0;
    if (operationResult.totalOrders === 0) return 0;
    return (operationResult.successCount / operationResult.totalOrders) * 100;
  }, [operationResult]);

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Bulk Operations</h3>
        <p className="mt-1 text-sm text-gray-600">
          {selectedOrders.length} order{selectedOrders.length !== 1 ? 's' : ''} selected
        </p>
      </div>

      {/* Operation Selection */}
      {operationState === 'idle' && (
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Operation
            </label>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {BULK_OPERATIONS.map((operation) => (
                <button
                  key={operation.type}
                  type="button"
                  onClick={() => handleOperationSelect(operation.type)}
                  disabled={disabled || selectedOrders.length === 0}
                  className={`
                    relative p-4 text-left border rounded-lg transition-all
                    ${selectedOperation === operation.type
                      ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-500'
                      : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
                    }
                    ${disabled || selectedOrders.length === 0
                      ? 'opacity-50 cursor-not-allowed'
                      : 'cursor-pointer'
                    }
                  `}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">
                        {operation.label}
                      </p>
                      <p className="mt-1 text-xs text-gray-600">
                        {operation.description}
                      </p>
                    </div>
                    {operation.dangerLevel === 'high' && (
                      <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                        High Risk
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Additional Options */}
          {selectedOperation && operationDetails && (
            <div className="space-y-4 pt-4 border-t border-gray-200">
              {/* Target Status Selection */}
              {operationDetails.requiresStatus && (
                <div>
                  <label htmlFor="target-status" className="block text-sm font-medium text-gray-700 mb-2">
                    Target Status *
                  </label>
                  <select
                    id="target-status"
                    value={targetStatus ?? ''}
                    onChange={(e) => setTargetStatus(e.target.value as DealerOrderStatus)}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    disabled={disabled}
                  >
                    <option value="">Select status...</option>
                    {TARGET_STATUSES.map((status) => (
                      <option key={status.value} value={status.value}>
                        {status.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Notes Input */}
              {operationDetails.requiresNotes && (
                <div>
                  <label htmlFor="operation-notes" className="block text-sm font-medium text-gray-700 mb-2">
                    Notes *
                  </label>
                  <textarea
                    id="operation-notes"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={3}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Enter reason or notes for this operation..."
                    disabled={disabled}
                  />
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedOperation(null)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  disabled={disabled}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmOperation}
                  disabled={!canExecuteOperation}
                  className={`
                    px-4 py-2 text-sm font-medium text-white rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2
                    ${operationDetails.dangerLevel === 'high'
                      ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
                      : 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500'
                    }
                    ${!canExecuteOperation ? 'opacity-50 cursor-not-allowed' : ''}
                  `}
                >
                  Continue
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Confirmation Dialog */}
      {operationState === 'confirming' && operationDetails && (
        <div className="p-6 space-y-4">
          <div className="flex items-start gap-3">
            <div className={`
              flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center
              ${operationDetails.dangerLevel === 'high' ? 'bg-red-100' : 'bg-yellow-100'}
            `}>
              <svg
                className={`w-6 h-6 ${operationDetails.dangerLevel === 'high' ? 'text-red-600' : 'text-yellow-600'}`}
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
            <div className="flex-1">
              <h4 className="text-base font-semibold text-gray-900">
                Confirm {operationDetails.label}
              </h4>
              <p className="mt-2 text-sm text-gray-600">
                You are about to {operationDetails.description.toLowerCase()} for{' '}
                <span className="font-semibold">{selectedOrders.length}</span> order
                {selectedOrders.length !== 1 ? 's' : ''}.
              </p>
              {targetStatus && (
                <p className="mt-2 text-sm text-gray-600">
                  Target status: <span className="font-semibold">{TARGET_STATUSES.find((s) => s.value === targetStatus)?.label}</span>
                </p>
              )}
              {notes && (
                <div className="mt-2">
                  <p className="text-sm font-medium text-gray-700">Notes:</p>
                  <p className="mt-1 text-sm text-gray-600">{notes}</p>
                </div>
              )}
              <p className="mt-3 text-sm font-medium text-gray-900">
                This action cannot be undone. Are you sure you want to continue?
              </p>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={handleCancelConfirmation}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleExecuteOperation}
              className={`
                px-4 py-2 text-sm font-medium text-white rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2
                ${operationDetails.dangerLevel === 'high'
                  ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
                  : 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500'
                }
              `}
            >
              Confirm {operationDetails.label}
            </button>
          </div>
        </div>
      )}

      {/* Executing State */}
      {operationState === 'executing' && (
        <div className="p-6">
          <div className="flex items-center justify-center py-8">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent" />
              <p className="mt-4 text-sm font-medium text-gray-900">
                Processing operation...
              </p>
              <p className="mt-1 text-xs text-gray-600">
                Please wait while we process {selectedOrders.length} order{selectedOrders.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Results Display */}
      {operationState === 'completed' && operationResult && (
        <div className="p-6 space-y-4">
          {/* Success Summary */}
          <div className={`
            p-4 rounded-lg border
            ${successRate === 100
              ? 'bg-green-50 border-green-200'
              : successRate > 0
                ? 'bg-yellow-50 border-yellow-200'
                : 'bg-red-50 border-red-200'
            }
          `}>
            <div className="flex items-start gap-3">
              <div className={`
                flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
                ${successRate === 100
                  ? 'bg-green-100'
                  : successRate > 0
                    ? 'bg-yellow-100'
                    : 'bg-red-100'
                }
              `}>
                <svg
                  className={`w-5 h-5 ${
                    successRate === 100
                      ? 'text-green-600'
                      : successRate > 0
                        ? 'text-yellow-600'
                        : 'text-red-600'
                  }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  {successRate === 100 ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  )}
                </svg>
              </div>
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-gray-900">
                  Operation {successRate === 100 ? 'Completed Successfully' : 'Completed with Errors'}
                </h4>
                <div className="mt-2 text-sm text-gray-700">
                  <p>
                    <span className="font-medium">{operationResult.successCount}</span> of{' '}
                    <span className="font-medium">{operationResult.totalOrders}</span> orders processed successfully
                  </p>
                  {operationResult.failureCount > 0 && (
                    <p className="mt-1 text-red-700">
                      <span className="font-medium">{operationResult.failureCount}</span> order
                      {operationResult.failureCount !== 1 ? 's' : ''} failed
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Error Details */}
          {operationResult.errors.length > 0 && (
            <div className="border border-red-200 rounded-lg overflow-hidden">
              <div className="bg-red-50 px-4 py-3 border-b border-red-200">
                <h5 className="text-sm font-semibold text-red-900">
                  Failed Orders ({operationResult.errors.length})
                </h5>
              </div>
              <div className="max-h-60 overflow-y-auto">
                <ul className="divide-y divide-red-100">
                  {operationResult.errors.map((error, index) => (
                    <li key={index} className="px-4 py-3 bg-white hover:bg-red-50">
                      <p className="text-sm font-medium text-gray-900">
                        Order ID: {error.orderId}
                      </p>
                      <p className="mt-1 text-xs text-red-700">{error.error}</p>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={handleReset}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Done
            </button>
          </div>
        </div>
      )}

      {/* Error State */}
      {operationState === 'error' && (
        <div className="p-6">
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-red-900">Operation Failed</h4>
                <p className="mt-1 text-sm text-red-700">
                  An error occurred while processing the bulk operation. Please try again.
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={handleReset}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}