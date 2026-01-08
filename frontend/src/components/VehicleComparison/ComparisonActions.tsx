/**
 * Comparison Actions Component
 * 
 * Action bar with buttons for clearing comparison, exporting to PDF,
 * sharing comparison URL, and other comparison utilities.
 * Provides comprehensive comparison management functionality.
 * 
 * @module components/VehicleComparison/ComparisonActions
 */

import { useCallback, useState, useMemo } from 'react';
import { useComparison } from '../../hooks/useComparison';

/**
 * Component props interface
 */
interface ComparisonActionsProps {
  readonly className?: string;
  readonly onExportStart?: () => void;
  readonly onExportComplete?: () => void;
  readonly onExportError?: (error: Error) => void;
  readonly onClearConfirm?: () => boolean;
  readonly onShareSuccess?: () => void;
  readonly onShareError?: (error: Error) => void;
  readonly showExport?: boolean;
  readonly showShare?: boolean;
  readonly showClear?: boolean;
  readonly disabled?: boolean;
}

/**
 * Export status type
 */
type ExportStatus = 'idle' | 'exporting' | 'success' | 'error';

/**
 * Share status type
 */
type ShareStatus = 'idle' | 'copying' | 'success' | 'error';

/**
 * Comparison Actions Component
 * 
 * Provides action buttons for comparison functionality including:
 * - Clear comparison
 * - Export to PDF
 * - Share comparison URL
 * - Copy comparison link
 * 
 * @example
 * ```tsx
 * <ComparisonActions
 *   onExportComplete={() => console.log('Export complete')}
 *   onShareSuccess={() => console.log('Link copied')}
 * />
 * ```
 */
export default function ComparisonActions({
  className = '',
  onExportStart,
  onExportComplete,
  onExportError,
  onClearConfirm,
  onShareSuccess,
  onShareError,
  showExport = true,
  showShare = true,
  showClear = true,
  disabled = false,
}: ComparisonActionsProps): JSX.Element {
  const {
    vehicles,
    clearComparison,
    canCompare,
    getComparisonUrl,
  } = useComparison();

  const [exportStatus, setExportStatus] = useState<ExportStatus>('idle');
  const [shareStatus, setShareStatus] = useState<ShareStatus>('idle');
  const [showClearConfirmation, setShowClearConfirmation] = useState(false);

  /**
   * Check if actions should be disabled
   */
  const isDisabled = useMemo(
    () => disabled || vehicles.length === 0,
    [disabled, vehicles.length]
  );

  /**
   * Check if export is available
   */
  const canExport = useMemo(
    () => canCompare && !isDisabled,
    [canCompare, isDisabled]
  );

  /**
   * Handle export to PDF
   */
  const handleExport = useCallback(async (): Promise<void> => {
    if (!canExport || exportStatus === 'exporting') {
      return;
    }

    try {
      setExportStatus('exporting');
      onExportStart?.();

      console.info('[ComparisonActions] Starting PDF export', {
        vehicleCount: vehicles.length,
        vehicleIds: vehicles.map((v) => v.id),
      });

      // Dynamic import of PDF generator to reduce bundle size
      const { generateComparisonPDF } = await import('../../utils/pdfGenerator');

      // Generate PDF with current comparison data
      await generateComparisonPDF(vehicles);

      setExportStatus('success');
      onExportComplete?.();

      console.info('[ComparisonActions] PDF export completed successfully');

      // Reset status after delay
      setTimeout(() => {
        setExportStatus('idle');
      }, 3000);
    } catch (error) {
      const exportError = error instanceof Error ? error : new Error('PDF export failed');
      
      console.error('[ComparisonActions] PDF export failed:', {
        error: exportError.message,
        stack: exportError.stack,
        vehicleCount: vehicles.length,
      });

      setExportStatus('error');
      onExportError?.(exportError);

      // Reset status after delay
      setTimeout(() => {
        setExportStatus('idle');
      }, 3000);
    }
  }, [canExport, exportStatus, vehicles, onExportStart, onExportComplete, onExportError]);

  /**
   * Handle share comparison URL
   */
  const handleShare = useCallback(async (): Promise<void> => {
    if (isDisabled || shareStatus === 'copying') {
      return;
    }

    try {
      setShareStatus('copying');

      const comparisonUrl = getComparisonUrl();
      const fullUrl = `${window.location.origin}${comparisonUrl}`;

      console.info('[ComparisonActions] Sharing comparison URL', {
        url: fullUrl,
        vehicleCount: vehicles.length,
      });

      // Try native share API first (mobile devices)
      if (navigator.share) {
        await navigator.share({
          title: 'Vehicle Comparison',
          text: `Compare ${vehicles.length} vehicles`,
          url: fullUrl,
        });

        setShareStatus('success');
        onShareSuccess?.();

        console.info('[ComparisonActions] Shared via native share API');
      } else {
        // Fallback to clipboard
        await navigator.clipboard.writeText(fullUrl);

        setShareStatus('success');
        onShareSuccess?.();

        console.info('[ComparisonActions] Copied comparison URL to clipboard');
      }

      // Reset status after delay
      setTimeout(() => {
        setShareStatus('idle');
      }, 3000);
    } catch (error) {
      const shareError = error instanceof Error ? error : new Error('Share failed');
      
      console.error('[ComparisonActions] Share failed:', {
        error: shareError.message,
        stack: shareError.stack,
      });

      setShareStatus('error');
      onShareError?.(shareError);

      // Reset status after delay
      setTimeout(() => {
        setShareStatus('idle');
      }, 3000);
    }
  }, [isDisabled, shareStatus, vehicles, getComparisonUrl, onShareSuccess, onShareError]);

  /**
   * Handle clear comparison with confirmation
   */
  const handleClear = useCallback((): void => {
    if (isDisabled) {
      return;
    }

    // Check if custom confirmation handler exists
    if (onClearConfirm) {
      const shouldClear = onClearConfirm();
      if (shouldClear) {
        clearComparison();
        console.info('[ComparisonActions] Comparison cleared via custom confirmation');
      }
      return;
    }

    // Show built-in confirmation
    setShowClearConfirmation(true);
  }, [isDisabled, onClearConfirm, clearComparison]);

  /**
   * Confirm clear action
   */
  const confirmClear = useCallback((): void => {
    clearComparison();
    setShowClearConfirmation(false);
    console.info('[ComparisonActions] Comparison cleared', {
      vehicleCount: vehicles.length,
    });
  }, [clearComparison, vehicles.length]);

  /**
   * Cancel clear action
   */
  const cancelClear = useCallback((): void => {
    setShowClearConfirmation(false);
  }, []);

  /**
   * Get export button text based on status
   */
  const exportButtonText = useMemo(() => {
    switch (exportStatus) {
      case 'exporting':
        return 'Exporting...';
      case 'success':
        return 'Exported!';
      case 'error':
        return 'Export Failed';
      default:
        return 'Export to PDF';
    }
  }, [exportStatus]);

  /**
   * Get share button text based on status
   */
  const shareButtonText = useMemo(() => {
    switch (shareStatus) {
      case 'copying':
        return 'Copying...';
      case 'success':
        return 'Copied!';
      case 'error':
        return 'Copy Failed';
      default:
        return 'Share Comparison';
    }
  }, [shareStatus]);

  return (
    <>
      <div
        className={`flex flex-wrap items-center gap-3 ${className}`}
        role="toolbar"
        aria-label="Comparison actions"
      >
        {/* Export to PDF Button */}
        {showExport && (
          <button
            type="button"
            onClick={handleExport}
            disabled={!canExport || exportStatus === 'exporting'}
            className={`
              inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium
              transition-all duration-200 focus:outline-none focus:ring-2
              focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed
              ${
                exportStatus === 'success'
                  ? 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500'
                  : exportStatus === 'error'
                    ? 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500'
                    : 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500'
              }
            `}
            aria-label={exportButtonText}
            aria-busy={exportStatus === 'exporting'}
          >
            {exportStatus === 'exporting' ? (
              <svg
                className="animate-spin h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            ) : exportStatus === 'success' ? (
              <svg
                className="h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            ) : exportStatus === 'error' ? (
              <svg
                className="h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            ) : (
              <svg
                className="h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0015.414 6L12 2.586A2 2 0 0010.586 2H6zm5 6a1 1 0 10-2 0v3.586l-1.293-1.293a1 1 0 10-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 11.586V8z"
                  clipRule="evenodd"
                />
              </svg>
            )}
            <span>{exportButtonText}</span>
          </button>
        )}

        {/* Share Button */}
        {showShare && (
          <button
            type="button"
            onClick={handleShare}
            disabled={isDisabled || shareStatus === 'copying'}
            className={`
              inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium
              transition-all duration-200 focus:outline-none focus:ring-2
              focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed
              ${
                shareStatus === 'success'
                  ? 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500'
                  : shareStatus === 'error'
                    ? 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500'
                    : 'bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-500'
              }
            `}
            aria-label={shareButtonText}
            aria-busy={shareStatus === 'copying'}
          >
            {shareStatus === 'copying' ? (
              <svg
                className="animate-spin h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            ) : shareStatus === 'success' ? (
              <svg
                className="h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            ) : shareStatus === 'error' ? (
              <svg
                className="h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            ) : (
              <svg
                className="h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z" />
              </svg>
            )}
            <span>{shareButtonText}</span>
          </button>
        )}

        {/* Clear Button */}
        {showClear && (
          <button
            type="button"
            onClick={handleClear}
            disabled={isDisabled}
            className="
              inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium
              bg-red-600 text-white hover:bg-red-700 transition-all duration-200
              focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500
              disabled:opacity-50 disabled:cursor-not-allowed
            "
            aria-label="Clear comparison"
          >
            <svg
              className="h-5 w-5"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            <span>Clear All</span>
          </button>
        )}
      </div>

      {/* Clear Confirmation Modal */}
      {showClearConfirmation && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
          role="dialog"
          aria-modal="true"
          aria-labelledby="clear-confirmation-title"
        >
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h2
              id="clear-confirmation-title"
              className="text-xl font-semibold text-gray-900 mb-4"
            >
              Clear Comparison?
            </h2>
            <p className="text-gray-600 mb-6">
              Are you sure you want to clear all {vehicles.length} vehicle
              {vehicles.length === 1 ? '' : 's'} from the comparison? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                type="button"
                onClick={cancelClear}
                className="
                  px-4 py-2 rounded-lg font-medium text-gray-700 bg-gray-100
                  hover:bg-gray-200 transition-colors duration-200
                  focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500
                "
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmClear}
                className="
                  px-4 py-2 rounded-lg font-medium text-white bg-red-600
                  hover:bg-red-700 transition-colors duration-200
                  focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500
                "
              >
                Clear All
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}