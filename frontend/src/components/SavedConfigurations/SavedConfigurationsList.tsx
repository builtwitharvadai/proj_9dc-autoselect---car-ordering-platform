/**
 * Saved Configurations List Component
 * Displays user's saved vehicle configurations with management actions
 */

import { useState, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  useSavedConfigurations,
  useDeleteSavedConfiguration,
  useShareConfiguration,
  type SavedConfigurationWithVehicle,
  type SavedConfigurationListRequest,
} from '../../hooks/useSavedConfigurations';
import {
  formatConfigurationPrice,
  CONFIGURATION_STATUS_NAMES,
  CONFIGURATION_VISIBILITY_NAMES,
  isActiveConfiguration,
  isSharedConfiguration,
} from '../../types/savedConfiguration';

/**
 * Component props
 */
export interface SavedConfigurationsListProps {
  readonly className?: string;
  readonly onEdit?: (configId: string) => void;
  readonly onCompare?: (configIds: readonly string[]) => void;
  readonly enableCompare?: boolean;
  readonly pageSize?: number;
}

/**
 * Sort field options
 */
type SortField = 'name' | 'createdAt' | 'updatedAt' | 'viewCount';

/**
 * Sort configuration
 */
interface SortConfig {
  readonly field: SortField;
  readonly direction: 'asc' | 'desc';
}

/**
 * Configuration card action state
 */
interface ActionState {
  readonly configId: string;
  readonly action: 'delete' | 'share' | null;
  readonly isProcessing: boolean;
}

/**
 * Default page size
 */
const DEFAULT_PAGE_SIZE = 20;

/**
 * Maximum configurations for comparison
 */
const MAX_COMPARE_SELECTIONS = 3;

/**
 * Saved Configurations List Component
 */
export default function SavedConfigurationsList({
  className = '',
  onEdit,
  onCompare,
  enableCompare = true,
  pageSize = DEFAULT_PAGE_SIZE,
}: SavedConfigurationsListProps): JSX.Element {
  // State management
  const [currentPage, setCurrentPage] = useState(1);
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    field: 'updatedAt',
    direction: 'desc',
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedForCompare, setSelectedForCompare] = useState<Set<string>>(new Set());
  const [actionState, setActionState] = useState<ActionState>({
    configId: '',
    action: null,
    isProcessing: false,
  });
  const [shareResult, setShareResult] = useState<{
    readonly configId: string;
    readonly shareUrl: string;
  } | null>(null);

  // Build query parameters
  const queryParams = useMemo<SavedConfigurationListRequest>(
    () => ({
      page: currentPage,
      pageSize,
      sortBy: sortConfig.field,
      sortDirection: sortConfig.direction,
      search: searchQuery.trim() || undefined,
      status: 'active',
    }),
    [currentPage, pageSize, sortConfig, searchQuery],
  );

  // Fetch configurations
  const {
    data: configurationsData,
    isLoading,
    isError,
    error,
    refetch,
  } = useSavedConfigurations(queryParams, {
    staleTime: 60000,
    retry: 2,
  });

  // Delete mutation
  const deleteMutation = useDeleteSavedConfiguration({
    onSuccess: () => {
      setActionState({ configId: '', action: null, isProcessing: false });
      void refetch();
    },
    onError: () => {
      setActionState({ configId: '', action: null, isProcessing: false });
    },
  });

  // Share mutation
  const shareMutation = useShareConfiguration({
    onSuccess: (data, variables) => {
      setShareResult({
        configId: variables.configurationId,
        shareUrl: data.shareUrl,
      });
      setActionState({ configId: '', action: null, isProcessing: false });
      void refetch();
    },
    onError: () => {
      setActionState({ configId: '', action: null, isProcessing: false });
    },
  });

  // Handle sort change
  const handleSortChange = useCallback((field: SortField) => {
    setSortConfig((prev) => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
    setCurrentPage(1);
  }, []);

  // Handle search
  const handleSearchChange = useCallback((query: string) => {
    setSearchQuery(query);
    setCurrentPage(1);
  }, []);

  // Handle page change
  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  // Handle delete
  const handleDelete = useCallback(
    (configId: string) => {
      setActionState({ configId, action: 'delete', isProcessing: true });
      deleteMutation.mutate(configId);
    },
    [deleteMutation],
  );

  // Handle share
  const handleShare = useCallback(
    (configId: string) => {
      setActionState({ configId, action: 'share', isProcessing: true });
      shareMutation.mutate({
        configurationId: configId,
        visibility: 'shared',
      });
    },
    [shareMutation],
  );

  // Handle compare selection
  const handleCompareToggle = useCallback((configId: string) => {
    setSelectedForCompare((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(configId)) {
        newSet.delete(configId);
      } else if (newSet.size < MAX_COMPARE_SELECTIONS) {
        newSet.add(configId);
      }
      return newSet;
    });
  }, []);

  // Handle compare action
  const handleCompare = useCallback(() => {
    if (onCompare && selectedForCompare.size >= 2) {
      onCompare(Array.from(selectedForCompare));
    }
  }, [onCompare, selectedForCompare]);

  // Handle copy share URL
  const handleCopyShareUrl = useCallback(async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = url;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
    }
  }, []);

  // Close share modal
  const handleCloseShareModal = useCallback(() => {
    setShareResult(null);
  }, []);

  // Render loading state
  if (isLoading) {
    return (
      <div className={`saved-configurations-list ${className}`}>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
          <span className="ml-3 text-gray-600">Loading configurations...</span>
        </div>
      </div>
    );
  }

  // Render error state
  if (isError) {
    return (
      <div className={`saved-configurations-list ${className}`}>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-800 mb-2">Error Loading Configurations</h3>
          <p className="text-red-600 mb-4">
            {error instanceof Error ? error.message : 'Failed to load saved configurations'}
          </p>
          <button
            onClick={() => void refetch()}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Render empty state
  if (!configurationsData || configurationsData.configurations.length === 0) {
    return (
      <div className={`saved-configurations-list ${className}`}>
        <div className="text-center py-12">
          <svg
            className="mx-auto h-24 w-24 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <h3 className="mt-4 text-lg font-semibold text-gray-900">No Saved Configurations</h3>
          <p className="mt-2 text-gray-600">
            {searchQuery
              ? 'No configurations match your search'
              : 'Start configuring a vehicle to save your first configuration'}
          </p>
          {searchQuery && (
            <button
              onClick={() => handleSearchChange('')}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Clear Search
            </button>
          )}
        </div>
      </div>
    );
  }

  const { configurations, total, totalPages } = configurationsData;

  return (
    <div className={`saved-configurations-list ${className}`}>
      {/* Header */}
      <div className="mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Saved Configurations</h2>
            <p className="mt-1 text-sm text-gray-600">
              {total} {total === 1 ? 'configuration' : 'configurations'} saved
            </p>
          </div>

          {/* Search */}
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Search configurations..."
              className="w-full sm:w-64 pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
        </div>

        {/* Sort and Compare Actions */}
        <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">Sort by:</span>
            <select
              value={sortConfig.field}
              onChange={(e) => handleSortChange(e.target.value as SortField)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="updatedAt">Last Modified</option>
              <option value="createdAt">Date Created</option>
              <option value="name">Name</option>
              <option value="viewCount">Most Viewed</option>
            </select>
            <button
              onClick={() =>
                setSortConfig((prev) => ({
                  ...prev,
                  direction: prev.direction === 'asc' ? 'desc' : 'asc',
                }))
              }
              className="p-1.5 text-gray-600 hover:text-gray-900 transition-colors"
              aria-label={`Sort ${sortConfig.direction === 'asc' ? 'descending' : 'ascending'}`}
            >
              <svg
                className={`h-5 w-5 transform ${sortConfig.direction === 'desc' ? 'rotate-180' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 15l7-7 7 7"
                />
              </svg>
            </button>
          </div>

          {enableCompare && selectedForCompare.size > 0 && (
            <button
              onClick={handleCompare}
              disabled={selectedForCompare.size < 2}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              Compare Selected ({selectedForCompare.size})
            </button>
          )}
        </div>
      </div>

      {/* Configuration Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {configurations.map((config) => (
          <ConfigurationCard
            key={config.id}
            configuration={config}
            isSelected={selectedForCompare.has(config.id)}
            isProcessing={
              actionState.configId === config.id && actionState.isProcessing
            }
            onEdit={onEdit}
            onDelete={handleDelete}
            onShare={handleShare}
            onCompareToggle={enableCompare ? handleCompareToggle : undefined}
            canSelectForCompare={
              enableCompare &&
              (selectedForCompare.has(config.id) ||
                selectedForCompare.size < MAX_COMPARE_SELECTIONS)
            }
          />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-2">
          <button
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="Previous page"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>

          <span className="px-4 py-2 text-sm text-gray-700">
            Page {currentPage} of {totalPages}
          </span>

          <button
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="Next page"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>
        </div>
      )}

      {/* Share Modal */}
      {shareResult && (
        <ShareModal
          shareUrl={shareResult.shareUrl}
          onClose={handleCloseShareModal}
          onCopy={handleCopyShareUrl}
        />
      )}
    </div>
  );
}

/**
 * Configuration Card Props
 */
interface ConfigurationCardProps {
  readonly configuration: SavedConfigurationWithVehicle;
  readonly isSelected: boolean;
  readonly isProcessing: boolean;
  readonly onEdit?: (configId: string) => void;
  readonly onDelete: (configId: string) => void;
  readonly onShare: (configId: string) => void;
  readonly onCompareToggle?: (configId: string) => void;
  readonly canSelectForCompare: boolean;
}

/**
 * Configuration Card Component
 */
function ConfigurationCard({
  configuration,
  isSelected,
  isProcessing,
  onEdit,
  onDelete,
  onShare,
  onCompareToggle,
  canSelectForCompare,
}: ConfigurationCardProps): JSX.Element {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleDeleteClick = useCallback(() => {
    setShowDeleteConfirm(true);
  }, []);

  const handleDeleteConfirm = useCallback(() => {
    onDelete(configuration.id);
    setShowDeleteConfirm(false);
  }, [configuration.id, onDelete]);

  const handleDeleteCancel = useCallback(() => {
    setShowDeleteConfirm(false);
  }, []);

  return (
    <div
      className={`bg-white rounded-lg shadow-md overflow-hidden transition-all ${
        isSelected ? 'ring-2 ring-blue-500' : ''
      } ${isProcessing ? 'opacity-50 pointer-events-none' : ''}`}
    >
      {/* Vehicle Image */}
      <div className="relative h-48 bg-gray-200">
        {configuration.vehicle.imageUrl ? (
          <img
            src={configuration.vehicle.imageUrl}
            alt={`${configuration.vehicle.year} ${configuration.vehicle.make} ${configuration.vehicle.model}`}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <svg
              className="h-16 w-16 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              />
            </svg>
          </div>
        )}

        {/* Compare Checkbox */}
        {onCompareToggle && (
          <div className="absolute top-2 left-2">
            <label className="flex items-center gap-2 bg-white rounded-lg px-3 py-1.5 shadow-md cursor-pointer">
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => onCompareToggle(configuration.id)}
                disabled={!canSelectForCompare && !isSelected}
                className="h-4 w-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-gray-700">Compare</span>
            </label>
          </div>
        )}

        {/* Status Badge */}
        {isSharedConfiguration(configuration) && (
          <div className="absolute top-2 right-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
              Shared
            </span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Configuration Name */}
        <h3 className="text-lg font-semibold text-gray-900 mb-1 truncate">
          {configuration.name}
        </h3>

        {/* Vehicle Details */}
        <p className="text-sm text-gray-600 mb-3">
          {configuration.vehicle.year} {configuration.vehicle.make}{' '}
          {configuration.vehicle.model}
          {configuration.vehicle.trim && ` ${configuration.vehicle.trim}`}
        </p>

        {/* Pricing */}
        <div className="mb-4">
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-bold text-gray-900">
              {formatConfigurationPrice(configuration.pricing.total)}
            </span>
            <span className="text-sm text-gray-500">Total</span>
          </div>
          <div className="mt-1 text-xs text-gray-500">
            Base: {formatConfigurationPrice(configuration.pricing.basePrice)} • Options:{' '}
            {formatConfigurationPrice(configuration.pricing.optionsPrice)}
          </div>
        </div>

        {/* Metadata */}
        <div className="flex items-center justify-between text-xs text-gray-500 mb-4">
          <span>
            Updated {new Date(configuration.updatedAt).toLocaleDateString()}
          </span>
          {configuration.viewCount > 0 && (
            <span>{configuration.viewCount} views</span>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Link
            to={`/configure/${configuration.vehicleId}?config=${configuration.id}`}
            className="flex-1 px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors text-center"
          >
            View
          </Link>

          {onEdit && (
            <button
              onClick={() => onEdit(configuration.id)}
              className="px-3 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
              aria-label="Edit configuration"
            >
              <svg
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                />
              </svg>
            </button>
          )}

          <button
            onClick={() => onShare(configuration.id)}
            className="px-3 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
            aria-label="Share configuration"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
              />
            </svg>
          </button>

          <button
            onClick={handleDeleteClick}
            className="px-3 py-2 border border-red-300 text-red-700 text-sm font-medium rounded-lg hover:bg-red-50 transition-colors"
            aria-label="Delete configuration"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Delete Configuration?
            </h3>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete "{configuration.name}"? This action cannot be
              undone.
            </p>
            <div className="flex items-center gap-3">
              <button
                onClick={handleDeleteConfirm}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Delete
              </button>
              <button
                onClick={handleDeleteCancel}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Share Modal Props
 */
interface ShareModalProps {
  readonly shareUrl: string;
  readonly onClose: () => void;
  readonly onCopy: (url: string) => void;
}

/**
 * Share Modal Component
 */
function ShareModal({ shareUrl, onClose, onCopy }: ShareModalProps): JSX.Element {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    await onCopy(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [shareUrl, onCopy]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Share Configuration</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <p className="text-gray-600 mb-4">
          Share this link with others to let them view your configuration:
        </p>

        <div className="flex items-center gap-2 mb-6">
          <input
            type="text"
            value={shareUrl}
            readOnly
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm"
          />
          <button
            onClick={handleCopy}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>

        <button
          onClick={onClose}
          className="w-full px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  );
}