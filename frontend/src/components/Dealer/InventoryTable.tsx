import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import {
  DealerInventoryWithVehicle,
  DealerInventoryStatus,
  DealerInventoryFilters,
  isLowStock,
  isOutOfStock,
  isAvailableForSale,
} from '../../types/dealer';

/**
 * Sort configuration for inventory table
 */
type SortField =
  | 'vin'
  | 'make'
  | 'model'
  | 'year'
  | 'status'
  | 'stockLevel'
  | 'availableQuantity'
  | 'location'
  | 'updatedAt';

type SortDirection = 'asc' | 'desc';

interface SortConfig {
  readonly field: SortField;
  readonly direction: SortDirection;
}

/**
 * Column configuration for the inventory table
 */
interface ColumnConfig {
  readonly key: string;
  readonly label: string;
  readonly sortable: boolean;
  readonly width?: string;
  readonly align?: 'left' | 'center' | 'right';
}

/**
 * Props for the InventoryTable component
 */
interface InventoryTableProps {
  readonly inventory: readonly DealerInventoryWithVehicle[];
  readonly isLoading?: boolean;
  readonly onEdit?: (item: DealerInventoryWithVehicle) => void;
  readonly onStatusChange?: (item: DealerInventoryWithVehicle) => void;
  readonly onStockAdjust?: (item: DealerInventoryWithVehicle) => void;
  readonly onDelete?: (item: DealerInventoryWithVehicle) => void;
  readonly onBulkAction?: (
    action: 'activate' | 'deactivate' | 'delete',
    items: readonly DealerInventoryWithVehicle[],
  ) => void;
  readonly filters?: DealerInventoryFilters;
  readonly onFilterChange?: (filters: DealerInventoryFilters) => void;
  readonly className?: string;
  readonly enableBulkActions?: boolean;
  readonly enableInlineEdit?: boolean;
  readonly pageSize?: number;
}

/**
 * Status badge component for inventory status display
 */
const StatusBadge: React.FC<{ readonly status: DealerInventoryStatus }> = ({ status }) => {
  const statusConfig: Record<
    DealerInventoryStatus,
    { readonly label: string; readonly className: string }
  > = {
    active: { label: 'Active', className: 'bg-green-100 text-green-800' },
    inactive: { label: 'Inactive', className: 'bg-gray-100 text-gray-800' },
    sold: { label: 'Sold', className: 'bg-blue-100 text-blue-800' },
    reserved: { label: 'Reserved', className: 'bg-yellow-100 text-yellow-800' },
  };

  const config = statusConfig[status];

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
};

/**
 * Stock level indicator with visual warnings
 */
const StockIndicator: React.FC<{ readonly item: DealerInventoryWithVehicle }> = ({ item }) => {
  const isLow = isLowStock(item);
  const isOut = isOutOfStock(item);

  let className = 'text-gray-900';
  let icon = null;

  if (isOut) {
    className = 'text-red-600 font-semibold';
    icon = (
      <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
          clipRule="evenodd"
        />
      </svg>
    );
  } else if (isLow) {
    className = 'text-yellow-600 font-medium';
    icon = (
      <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
          clipRule="evenodd"
        />
      </svg>
    );
  }

  return (
    <div className={`flex items-center ${className}`}>
      {icon}
      <span>
        {item.availableQuantity} / {item.stockLevel}
      </span>
      {item.reservedQuantity > 0 && (
        <span className="ml-2 text-xs text-gray-500">({item.reservedQuantity} reserved)</span>
      )}
    </div>
  );
};

/**
 * Dealer Inventory Management Table Component
 *
 * Provides comprehensive inventory management with:
 * - Sortable columns
 * - Filterable data
 * - Bulk selection and actions
 * - Inline editing capabilities
 * - Pagination
 * - Responsive design
 */
export default function InventoryTable({
  inventory,
  isLoading = false,
  onEdit,
  onStatusChange,
  onStockAdjust,
  onDelete,
  onBulkAction,
  filters,
  onFilterChange,
  className = '',
  enableBulkActions = true,
  enableInlineEdit = true,
  pageSize = 20,
}: InventoryTableProps): JSX.Element {
  // State management
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    field: 'updatedAt',
    direction: 'desc',
  });
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const tableRef = useRef<HTMLDivElement>(null);

  // Column configuration
  const columns: readonly ColumnConfig[] = useMemo(
    () => [
      { key: 'vin', label: 'VIN', sortable: true, width: '150px' },
      { key: 'vehicle', label: 'Vehicle', sortable: true, width: '250px' },
      { key: 'status', label: 'Status', sortable: true, width: '120px', align: 'center' },
      { key: 'stock', label: 'Stock', sortable: true, width: '150px', align: 'center' },
      { key: 'location', label: 'Location', sortable: true, width: '150px' },
      { key: 'price', label: 'Price', sortable: false, width: '120px', align: 'right' },
      { key: 'updated', label: 'Last Updated', sortable: true, width: '150px' },
      { key: 'actions', label: 'Actions', sortable: false, width: '150px', align: 'center' },
    ],
    [],
  );

  // Filter and sort inventory
  const filteredAndSortedInventory = useMemo(() => {
    let filtered = [...inventory];

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (item) =>
          item.vin.toLowerCase().includes(query) ||
          item.vehicle.make.toLowerCase().includes(query) ||
          item.vehicle.model.toLowerCase().includes(query) ||
          item.location.toLowerCase().includes(query),
      );
    }

    // Apply status filter
    if (filters?.status && filters.status.length > 0) {
      filtered = filtered.filter((item) => filters.status?.includes(item.status));
    }

    // Apply low stock filter
    if (filters?.lowStock) {
      filtered = filtered.filter((item) => isLowStock(item));
    }

    // Apply out of stock filter
    if (filters?.outOfStock) {
      filtered = filtered.filter((item) => isOutOfStock(item));
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aValue: string | number;
      let bValue: string | number;

      switch (sortConfig.field) {
        case 'vin':
          aValue = a.vin;
          bValue = b.vin;
          break;
        case 'make':
          aValue = a.vehicle.make;
          bValue = b.vehicle.make;
          break;
        case 'model':
          aValue = a.vehicle.model;
          bValue = b.vehicle.model;
          break;
        case 'year':
          aValue = a.vehicle.year;
          bValue = b.vehicle.year;
          break;
        case 'status':
          aValue = a.status;
          bValue = b.status;
          break;
        case 'stockLevel':
          aValue = a.stockLevel;
          bValue = b.stockLevel;
          break;
        case 'availableQuantity':
          aValue = a.availableQuantity;
          bValue = b.availableQuantity;
          break;
        case 'location':
          aValue = a.location;
          bValue = b.location;
          break;
        case 'updatedAt':
          aValue = new Date(a.updatedAt).getTime();
          bValue = new Date(b.updatedAt).getTime();
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [inventory, searchQuery, filters, sortConfig]);

  // Pagination
  const totalPages = Math.ceil(filteredAndSortedInventory.length / pageSize);
  const paginatedInventory = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return filteredAndSortedInventory.slice(startIndex, startIndex + pageSize);
  }, [filteredAndSortedInventory, currentPage, pageSize]);

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, filters]);

  // Handle sort
  const handleSort = useCallback((field: SortField) => {
    setSortConfig((prev) => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  }, []);

  // Handle selection
  const handleSelectAll = useCallback(
    (checked: boolean) => {
      if (checked) {
        setSelectedItems(new Set(paginatedInventory.map((item) => item.id)));
      } else {
        setSelectedItems(new Set());
      }
    },
    [paginatedInventory],
  );

  const handleSelectItem = useCallback((id: string, checked: boolean) => {
    setSelectedItems((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  }, []);

  // Handle bulk actions
  const handleBulkAction = useCallback(
    (action: 'activate' | 'deactivate' | 'delete') => {
      const selectedInventory = inventory.filter((item) => selectedItems.has(item.id));
      if (selectedInventory.length > 0 && onBulkAction) {
        onBulkAction(action, selectedInventory);
        setSelectedItems(new Set());
      }
    },
    [inventory, selectedItems, onBulkAction],
  );

  // Format date
  const formatDate = useCallback((dateString: string): string => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  }, []);

  // Format price
  const formatPrice = useCallback((price: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(price);
  }, []);

  const allSelected =
    paginatedInventory.length > 0 &&
    paginatedInventory.every((item) => selectedItems.has(item.id));
  const someSelected = paginatedInventory.some((item) => selectedItems.has(item.id));

  if (isLoading) {
    return (
      <div className={`flex items-center justify-center py-12 ${className}`}>
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className={`flex flex-col ${className}`}>
      {/* Search and bulk actions bar */}
      <div className="mb-4 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search by VIN, make, model, or location..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            aria-label="Search inventory"
          />
        </div>

        {enableBulkActions && selectedItems.size > 0 && (
          <div className="flex gap-2">
            <button
              onClick={() => handleBulkAction('activate')}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              aria-label="Activate selected items"
            >
              Activate ({selectedItems.size})
            </button>
            <button
              onClick={() => handleBulkAction('deactivate')}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
              aria-label="Deactivate selected items"
            >
              Deactivate ({selectedItems.size})
            </button>
            <button
              onClick={() => handleBulkAction('delete')}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              aria-label="Delete selected items"
            >
              Delete ({selectedItems.size})
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div ref={tableRef} className="overflow-x-auto shadow-md rounded-lg">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {enableBulkActions && (
                <th scope="col" className="px-6 py-3 w-12">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={(input) => {
                      if (input) {
                        input.indeterminate = someSelected && !allSelected;
                      }
                    }}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    aria-label="Select all items"
                  />
                </th>
              )}
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className={`px-6 py-3 text-${column.align ?? 'left'} text-xs font-medium text-gray-500 uppercase tracking-wider ${
                    column.sortable ? 'cursor-pointer hover:bg-gray-100' : ''
                  }`}
                  style={{ width: column.width }}
                  onClick={() => column.sortable && handleSort(column.key as SortField)}
                >
                  <div className="flex items-center gap-2">
                    {column.label}
                    {column.sortable && sortConfig.field === column.key && (
                      <svg
                        className={`w-4 h-4 transform ${sortConfig.direction === 'desc' ? 'rotate-180' : ''}`}
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {paginatedInventory.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length + (enableBulkActions ? 1 : 0)}
                  className="px-6 py-12 text-center text-gray-500"
                >
                  No inventory items found
                </td>
              </tr>
            ) : (
              paginatedInventory.map((item) => (
                <tr
                  key={item.id}
                  className={`hover:bg-gray-50 ${selectedItems.has(item.id) ? 'bg-blue-50' : ''}`}
                >
                  {enableBulkActions && (
                    <td className="px-6 py-4 whitespace-nowrap">
                      <input
                        type="checkbox"
                        checked={selectedItems.has(item.id)}
                        onChange={(e) => handleSelectItem(item.id, e.target.checked)}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        aria-label={`Select ${item.vin}`}
                      />
                    </td>
                  )}
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {item.vin}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <img
                        src={item.vehicle.imageUrl}
                        alt={`${item.vehicle.year} ${item.vehicle.make} ${item.vehicle.model}`}
                        className="h-10 w-16 object-cover rounded"
                        loading="lazy"
                      />
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">
                          {item.vehicle.year} {item.vehicle.make} {item.vehicle.model}
                        </div>
                        {item.vehicle.trim && (
                          <div className="text-sm text-gray-500">{item.vehicle.trim}</div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <StockIndicator item={item} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item.location}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    {formatPrice(item.vehicle.price)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(item.updatedAt)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <div className="flex items-center justify-center gap-2">
                      {enableInlineEdit && onEdit && (
                        <button
                          onClick={() => onEdit(item)}
                          className="text-blue-600 hover:text-blue-900"
                          aria-label={`Edit ${item.vin}`}
                        >
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                          </svg>
                        </button>
                      )}
                      {onStatusChange && isAvailableForSale(item) && (
                        <button
                          onClick={() => onStatusChange(item)}
                          className="text-yellow-600 hover:text-yellow-900"
                          aria-label={`Change status for ${item.vin}`}
                        >
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path
                              fillRule="evenodd"
                              d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"
                              clipRule="evenodd"
                            />
                          </svg>
                        </button>
                      )}
                      {onStockAdjust && (
                        <button
                          onClick={() => onStockAdjust(item)}
                          className="text-green-600 hover:text-green-900"
                          aria-label={`Adjust stock for ${item.vin}`}
                        >
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM14 11a1 1 0 011 1v1h1a1 1 0 110 2h-1v1a1 1 0 11-2 0v-1h-1a1 1 0 110-2h1v-1a1 1 0 011-1z" />
                          </svg>
                        </button>
                      )}
                      {onDelete && (
                        <button
                          onClick={() => onDelete(item)}
                          className="text-red-600 hover:text-red-900"
                          aria-label={`Delete ${item.vin}`}
                        >
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path
                              fillRule="evenodd"
                              d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                              clipRule="evenodd"
                            />
                          </svg>
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <div className="text-sm text-gray-700">
            Showing {(currentPage - 1) * pageSize + 1} to{' '}
            {Math.min(currentPage * pageSize, filteredAndSortedInventory.length)} of{' '}
            {filteredAndSortedInventory.length} results
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              aria-label="Previous page"
            >
              Previous
            </button>
            <div className="flex gap-1">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum: number;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (currentPage <= 3) {
                  pageNum = i + 1;
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = currentPage - 2 + i;
                }
                return (
                  <button
                    key={pageNum}
                    onClick={() => setCurrentPage(pageNum)}
                    className={`px-4 py-2 border rounded-lg ${
                      currentPage === pageNum
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'border-gray-300 hover:bg-gray-50'
                    }`}
                    aria-label={`Page ${pageNum}`}
                    aria-current={currentPage === pageNum ? 'page' : undefined}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>
            <button
              onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              aria-label="Next page"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}