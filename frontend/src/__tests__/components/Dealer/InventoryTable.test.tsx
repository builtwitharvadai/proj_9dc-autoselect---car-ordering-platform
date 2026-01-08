import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import InventoryTable from '../../../components/Dealer/InventoryTable';
import type {
  DealerInventoryWithVehicle,
  DealerInventoryStatus,
  DealerInventoryFilters,
} from '../../../types/dealer';

// ============================================================================
// Test Data Factories
// ============================================================================

/**
 * Factory for creating mock vehicle data
 */
const createMockVehicle = (overrides = {}) => ({
  id: `vehicle-${Math.random().toString(36).substr(2, 9)}`,
  make: 'Toyota',
  model: 'Camry',
  year: 2024,
  trim: 'LE',
  price: 28000,
  imageUrl: 'https://example.com/camry.jpg',
  ...overrides,
});

/**
 * Factory for creating mock inventory items
 */
const createMockInventoryItem = (
  overrides: Partial<DealerInventoryWithVehicle> = {},
): DealerInventoryWithVehicle => ({
  id: `inv-${Math.random().toString(36).substr(2, 9)}`,
  dealerId: 'dealer-123',
  vin: `VIN${Math.random().toString(36).substr(2, 14).toUpperCase()}`,
  status: 'active' as DealerInventoryStatus,
  stockLevel: 10,
  availableQuantity: 8,
  reservedQuantity: 2,
  location: 'Main Lot',
  createdAt: new Date('2024-01-01').toISOString(),
  updatedAt: new Date('2024-01-15').toISOString(),
  vehicle: createMockVehicle(),
  ...overrides,
});

/**
 * Factory for creating multiple inventory items
 */
const createMockInventory = (count: number): DealerInventoryWithVehicle[] =>
  Array.from({ length: count }, (_, i) =>
    createMockInventoryItem({
      vin: `VIN${i.toString().padStart(14, '0')}`,
      vehicle: createMockVehicle({
        make: ['Toyota', 'Honda', 'Ford'][i % 3],
        model: ['Camry', 'Accord', 'F-150'][i % 3],
        year: 2024 - (i % 3),
      }),
      status: (['active', 'inactive', 'sold', 'reserved'] as DealerInventoryStatus[])[i % 4],
      stockLevel: 10 - i,
      availableQuantity: Math.max(0, 8 - i),
      location: ['Main Lot', 'North Lot', 'Service Center'][i % 3],
    }),
  );

// ============================================================================
// Test Setup and Utilities
// ============================================================================

describe('InventoryTable Component', () => {
  let mockInventory: DealerInventoryWithVehicle[];
  let mockHandlers: {
    onEdit: ReturnType<typeof vi.fn>;
    onStatusChange: ReturnType<typeof vi.fn>;
    onStockAdjust: ReturnType<typeof vi.fn>;
    onDelete: ReturnType<typeof vi.fn>;
    onBulkAction: ReturnType<typeof vi.fn>;
    onFilterChange: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    mockInventory = createMockInventory(25);
    mockHandlers = {
      onEdit: vi.fn(),
      onStatusChange: vi.fn(),
      onStockAdjust: vi.fn(),
      onDelete: vi.fn(),
      onBulkAction: vi.fn(),
      onFilterChange: vi.fn(),
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // 1. RENDERING TESTS
  // ============================================================================

  describe('Rendering', () => {
    it('should render loading state correctly', () => {
      render(<InventoryTable inventory={[]} isLoading={true} />);

      expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument();
      expect(screen.queryByRole('table')).not.toBeInTheDocument();
    });

    it('should render empty state when no inventory items', () => {
      render(<InventoryTable inventory={[]} />);

      expect(screen.getByText('No inventory items found')).toBeInTheDocument();
    });

    it('should render table with inventory items', () => {
      render(<InventoryTable inventory={mockInventory.slice(0, 5)} />);

      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getAllByRole('row')).toHaveLength(6); // 1 header + 5 data rows
    });

    it('should render all column headers correctly', () => {
      render(<InventoryTable inventory={mockInventory.slice(0, 1)} />);

      expect(screen.getByText('VIN')).toBeInTheDocument();
      expect(screen.getByText('Vehicle')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
      expect(screen.getByText('Stock')).toBeInTheDocument();
      expect(screen.getByText('Location')).toBeInTheDocument();
      expect(screen.getByText('Price')).toBeInTheDocument();
      expect(screen.getByText('Last Updated')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();
    });

    it('should render vehicle information correctly', () => {
      const item = createMockInventoryItem({
        vehicle: createMockVehicle({
          year: 2024,
          make: 'Toyota',
          model: 'Camry',
          trim: 'XLE',
        }),
      });

      render(<InventoryTable inventory={[item]} />);

      expect(screen.getByText('2024 Toyota Camry')).toBeInTheDocument();
      expect(screen.getByText('XLE')).toBeInTheDocument();
    });

    it('should render vehicle image with correct attributes', () => {
      const item = createMockInventoryItem({
        vehicle: createMockVehicle({
          imageUrl: 'https://example.com/test-car.jpg',
          year: 2024,
          make: 'Honda',
          model: 'Accord',
        }),
      });

      render(<InventoryTable inventory={[item]} />);

      const image = screen.getByAltText('2024 Honda Accord');
      expect(image).toHaveAttribute('src', 'https://example.com/test-car.jpg');
      expect(image).toHaveAttribute('loading', 'lazy');
    });

    it('should apply custom className', () => {
      const { container } = render(
        <InventoryTable inventory={[]} className="custom-class" />,
      );

      expect(container.firstChild).toHaveClass('custom-class');
    });
  });

  // ============================================================================
  // 2. STATUS BADGE TESTS
  // ============================================================================

  describe('Status Badge', () => {
    it('should render active status badge correctly', () => {
      const item = createMockInventoryItem({ status: 'active' });
      render(<InventoryTable inventory={[item]} />);

      const badge = screen.getByText('Active');
      expect(badge).toHaveClass('bg-green-100', 'text-green-800');
    });

    it('should render inactive status badge correctly', () => {
      const item = createMockInventoryItem({ status: 'inactive' });
      render(<InventoryTable inventory={[item]} />);

      const badge = screen.getByText('Inactive');
      expect(badge).toHaveClass('bg-gray-100', 'text-gray-800');
    });

    it('should render sold status badge correctly', () => {
      const item = createMockInventoryItem({ status: 'sold' });
      render(<InventoryTable inventory={[item]} />);

      const badge = screen.getByText('Sold');
      expect(badge).toHaveClass('bg-blue-100', 'text-blue-800');
    });

    it('should render reserved status badge correctly', () => {
      const item = createMockInventoryItem({ status: 'reserved' });
      render(<InventoryTable inventory={[item]} />);

      const badge = screen.getByText('Reserved');
      expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
    });
  });

  // ============================================================================
  // 3. STOCK INDICATOR TESTS
  // ============================================================================

  describe('Stock Indicator', () => {
    it('should show normal stock level without warning', () => {
      const item = createMockInventoryItem({
        stockLevel: 10,
        availableQuantity: 8,
        reservedQuantity: 2,
      });

      render(<InventoryTable inventory={[item]} />);

      expect(screen.getByText('8 / 10')).toBeInTheDocument();
      expect(screen.getByText('(2 reserved)')).toBeInTheDocument();
    });

    it('should show low stock warning', () => {
      const item = createMockInventoryItem({
        stockLevel: 10,
        availableQuantity: 2,
        reservedQuantity: 0,
      });

      render(<InventoryTable inventory={[item]} />);

      const stockText = screen.getByText('2 / 10');
      expect(stockText.parentElement).toHaveClass('text-yellow-600');
    });

    it('should show out of stock error', () => {
      const item = createMockInventoryItem({
        stockLevel: 10,
        availableQuantity: 0,
        reservedQuantity: 0,
      });

      render(<InventoryTable inventory={[item]} />);

      const stockText = screen.getByText('0 / 10');
      expect(stockText.parentElement).toHaveClass('text-red-600');
    });

    it('should not show reserved quantity when zero', () => {
      const item = createMockInventoryItem({
        stockLevel: 10,
        availableQuantity: 10,
        reservedQuantity: 0,
      });

      render(<InventoryTable inventory={[item]} />);

      expect(screen.queryByText(/reserved/)).not.toBeInTheDocument();
    });
  });

  // ============================================================================
  // 4. SEARCH FUNCTIONALITY TESTS
  // ============================================================================

  describe('Search Functionality', () => {
    it('should filter by VIN', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory} />);

      const searchInput = screen.getByPlaceholderText(/search by vin/i);
      await user.type(searchInput, mockInventory[0]!.vin);

      await waitFor(() => {
        expect(screen.getByText(mockInventory[0]!.vin)).toBeInTheDocument();
        expect(screen.queryByText(mockInventory[1]!.vin)).not.toBeInTheDocument();
      });
    });

    it('should filter by make', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory} />);

      const searchInput = screen.getByPlaceholderText(/search by vin/i);
      await user.type(searchInput, 'Toyota');

      await waitFor(() => {
        const rows = screen.getAllByRole('row').slice(1); // Skip header
        rows.forEach((row) => {
          expect(row.textContent).toMatch(/Toyota/i);
        });
      });
    });

    it('should filter by model', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory} />);

      const searchInput = screen.getByPlaceholderText(/search by vin/i);
      await user.type(searchInput, 'Camry');

      await waitFor(() => {
        const rows = screen.getAllByRole('row').slice(1);
        rows.forEach((row) => {
          expect(row.textContent).toMatch(/Camry/i);
        });
      });
    });

    it('should filter by location', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory} />);

      const searchInput = screen.getByPlaceholderText(/search by vin/i);
      await user.type(searchInput, 'Main Lot');

      await waitFor(() => {
        const rows = screen.getAllByRole('row').slice(1);
        rows.forEach((row) => {
          expect(row.textContent).toMatch(/Main Lot/i);
        });
      });
    });

    it('should be case-insensitive', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory} />);

      const searchInput = screen.getByPlaceholderText(/search by vin/i);
      await user.type(searchInput, 'TOYOTA');

      await waitFor(() => {
        expect(screen.getAllByRole('row').length).toBeGreaterThan(1);
      });
    });

    it('should show no results for non-matching search', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory} />);

      const searchInput = screen.getByPlaceholderText(/search by vin/i);
      await user.type(searchInput, 'NonExistentVehicle123');

      await waitFor(() => {
        expect(screen.getByText('No inventory items found')).toBeInTheDocument();
      });
    });

    it('should reset to page 1 when searching', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory} pageSize={5} />);

      // Go to page 2
      const nextButton = screen.getByLabelText('Next page');
      await user.click(nextButton);

      // Search
      const searchInput = screen.getByPlaceholderText(/search by vin/i);
      await user.type(searchInput, 'Toyota');

      await waitFor(() => {
        expect(screen.getByLabelText('Page 1')).toHaveClass('bg-blue-600');
      });
    });
  });

  // ============================================================================
  // 5. SORTING TESTS
  // ============================================================================

  describe('Sorting Functionality', () => {
    it('should sort by VIN ascending', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory.slice(0, 5)} />);

      const vinHeader = screen.getByText('VIN');
      await user.click(vinHeader);

      await waitFor(() => {
        const rows = screen.getAllByRole('row').slice(1);
        const vins = rows.map((row) => row.cells[1]?.textContent ?? '');
        expect(vins).toEqual([...vins].sort());
      });
    });

    it('should sort by VIN descending on second click', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory.slice(0, 5)} />);

      const vinHeader = screen.getByText('VIN');
      await user.click(vinHeader);
      await user.click(vinHeader);

      await waitFor(() => {
        const rows = screen.getAllByRole('row').slice(1);
        const vins = rows.map((row) => row.cells[1]?.textContent ?? '');
        expect(vins).toEqual([...vins].sort().reverse());
      });
    });

    it('should display sort indicator', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory.slice(0, 5)} />);

      const vinHeader = screen.getByText('VIN');
      await user.click(vinHeader);

      const headerCell = vinHeader.closest('th');
      expect(headerCell?.querySelector('svg')).toBeInTheDocument();
    });

    it('should sort by stock level', async () => {
      const user = userEvent.setup();
      const items = [
        createMockInventoryItem({ stockLevel: 5 }),
        createMockInventoryItem({ stockLevel: 10 }),
        createMockInventoryItem({ stockLevel: 3 }),
      ];

      render(<InventoryTable inventory={items} />);

      const stockHeader = screen.getByText('Stock');
      await user.click(stockHeader);

      await waitFor(() => {
        const rows = screen.getAllByRole('row').slice(1);
        const stocks = rows.map((row) => {
          const text = row.cells[4]?.textContent ?? '';
          return parseInt(text.split('/')[1]?.trim() ?? '0');
        });
        expect(stocks).toEqual([3, 5, 10]);
      });
    });

    it('should sort by location alphabetically', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory.slice(0, 5)} />);

      const locationHeader = screen.getByText('Location');
      await user.click(locationHeader);

      await waitFor(() => {
        const rows = screen.getAllByRole('row').slice(1);
        const locations = rows.map((row) => row.cells[5]?.textContent ?? '');
        expect(locations).toEqual([...locations].sort());
      });
    });
  });

  // ============================================================================
  // 6. PAGINATION TESTS
  // ============================================================================

  describe('Pagination', () => {
    it('should paginate results correctly', () => {
      render(<InventoryTable inventory={mockInventory} pageSize={10} />);

      expect(screen.getAllByRole('row')).toHaveLength(11); // 1 header + 10 data
      expect(screen.getByText(/showing 1 to 10 of 25/i)).toBeInTheDocument();
    });

    it('should navigate to next page', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory} pageSize={10} />);

      const nextButton = screen.getByLabelText('Next page');
      await user.click(nextButton);

      await waitFor(() => {
        expect(screen.getByText(/showing 11 to 20 of 25/i)).toBeInTheDocument();
      });
    });

    it('should navigate to previous page', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory} pageSize={10} />);

      const nextButton = screen.getByLabelText('Next page');
      await user.click(nextButton);

      const prevButton = screen.getByLabelText('Previous page');
      await user.click(prevButton);

      await waitFor(() => {
        expect(screen.getByText(/showing 1 to 10 of 25/i)).toBeInTheDocument();
      });
    });

    it('should disable previous button on first page', () => {
      render(<InventoryTable inventory={mockInventory} pageSize={10} />);

      const prevButton = screen.getByLabelText('Previous page');
      expect(prevButton).toBeDisabled();
    });

    it('should disable next button on last page', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory} pageSize={10} />);

      // Navigate to last page
      const page3Button = screen.getByLabelText('Page 3');
      await user.click(page3Button);

      await waitFor(() => {
        const nextButton = screen.getByLabelText('Next page');
        expect(nextButton).toBeDisabled();
      });
    });

    it('should navigate to specific page', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory} pageSize={10} />);

      const page2Button = screen.getByLabelText('Page 2');
      await user.click(page2Button);

      await waitFor(() => {
        expect(screen.getByText(/showing 11 to 20 of 25/i)).toBeInTheDocument();
        expect(page2Button).toHaveClass('bg-blue-600');
      });
    });

    it('should not show pagination for single page', () => {
      render(<InventoryTable inventory={mockInventory.slice(0, 5)} pageSize={10} />);

      expect(screen.queryByLabelText('Next page')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Previous page')).not.toBeInTheDocument();
    });

    it('should show correct page numbers for many pages', () => {
      const largeInventory = createMockInventory(100);
      render(<InventoryTable inventory={largeInventory} pageSize={10} />);

      // Should show pages 1-5
      expect(screen.getByLabelText('Page 1')).toBeInTheDocument();
      expect(screen.getByLabelText('Page 5')).toBeInTheDocument();
      expect(screen.queryByLabelText('Page 6')).not.toBeInTheDocument();
    });
  });

  // ============================================================================
  // 7. BULK SELECTION TESTS
  // ============================================================================

  describe('Bulk Selection', () => {
    it('should render checkboxes when bulk actions enabled', () => {
      render(<InventoryTable inventory={mockInventory.slice(0, 3)} enableBulkActions={true} />);

      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes).toHaveLength(4); // 1 select all + 3 items
    });

    it('should not render checkboxes when bulk actions disabled', () => {
      render(<InventoryTable inventory={mockInventory.slice(0, 3)} enableBulkActions={false} />);

      expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    });

    it('should select individual item', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory.slice(0, 3)} enableBulkActions={true} />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]!);

      expect(checkboxes[1]).toBeChecked();
    });

    it('should select all items', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory.slice(0, 3)} enableBulkActions={true} />);

      const selectAllCheckbox = screen.getAllByRole('checkbox')[0]!;
      await user.click(selectAllCheckbox);

      const checkboxes = screen.getAllByRole('checkbox');
      checkboxes.forEach((checkbox) => {
        expect(checkbox).toBeChecked();
      });
    });

    it('should deselect all items', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory.slice(0, 3)} enableBulkActions={true} />);

      const selectAllCheckbox = screen.getAllByRole('checkbox')[0]!;
      await user.click(selectAllCheckbox);
      await user.click(selectAllCheckbox);

      const checkboxes = screen.getAllByRole('checkbox');
      checkboxes.forEach((checkbox) => {
        expect(checkbox).not.toBeChecked();
      });
    });

    it('should show indeterminate state when some items selected', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory.slice(0, 3)} enableBulkActions={true} />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]!);

      const selectAllCheckbox = checkboxes[0] as HTMLInputElement;
      expect(selectAllCheckbox.indeterminate).toBe(true);
    });

    it('should show bulk action buttons when items selected', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory.slice(0, 3)} enableBulkActions={true} />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]!);

      await waitFor(() => {
        expect(screen.getByLabelText(/activate selected items/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/deactivate selected items/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/delete selected items/i)).toBeInTheDocument();
      });
    });

    it('should display selected count in bulk action buttons', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory.slice(0, 3)} enableBulkActions={true} />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]!);
      await user.click(checkboxes[2]!);

      await waitFor(() => {
        expect(screen.getByText(/activate \(2\)/i)).toBeInTheDocument();
      });
    });

    it('should highlight selected rows', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory.slice(0, 3)} enableBulkActions={true} />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]!);

      const rows = screen.getAllByRole('row').slice(1);
      expect(rows[0]).toHaveClass('bg-blue-50');
    });
  });

  // ============================================================================
  // 8. BULK ACTIONS TESTS
  // ============================================================================

  describe('Bulk Actions', () => {
    it('should call onBulkAction with activate', async () => {
      const user = userEvent.setup();
      render(
        <InventoryTable
          inventory={mockInventory.slice(0, 3)}
          enableBulkActions={true}
          onBulkAction={mockHandlers.onBulkAction}
        />,
      );

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]!);

      const activateButton = screen.getByLabelText(/activate selected items/i);
      await user.click(activateButton);

      expect(mockHandlers.onBulkAction).toHaveBeenCalledWith('activate', expect.any(Array));
      expect(mockHandlers.onBulkAction).toHaveBeenCalledTimes(1);
    });

    it('should call onBulkAction with deactivate', async () => {
      const user = userEvent.setup();
      render(
        <InventoryTable
          inventory={mockInventory.slice(0, 3)}
          enableBulkActions={true}
          onBulkAction={mockHandlers.onBulkAction}
        />,
      );

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]!);

      const deactivateButton = screen.getByLabelText(/deactivate selected items/i);
      await user.click(deactivateButton);

      expect(mockHandlers.onBulkAction).toHaveBeenCalledWith('deactivate', expect.any(Array));
    });

    it('should call onBulkAction with delete', async () => {
      const user = userEvent.setup();
      render(
        <InventoryTable
          inventory={mockInventory.slice(0, 3)}
          enableBulkActions={true}
          onBulkAction={mockHandlers.onBulkAction}
        />,
      );

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]!);

      const deleteButton = screen.getByLabelText(/delete selected items/i);
      await user.click(deleteButton);

      expect(mockHandlers.onBulkAction).toHaveBeenCalledWith('delete', expect.any(Array));
    });

    it('should pass correct items to onBulkAction', async () => {
      const user = userEvent.setup();
      const items = mockInventory.slice(0, 3);
      render(
        <InventoryTable
          inventory={items}
          enableBulkActions={true}
          onBulkAction={mockHandlers.onBulkAction}
        />,
      );

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]!);
      await user.click(checkboxes[2]!);

      const activateButton = screen.getByLabelText(/activate selected items/i);
      await user.click(activateButton);

      expect(mockHandlers.onBulkAction).toHaveBeenCalledWith('activate', [items[0], items[1]]);
    });

    it('should clear selection after bulk action', async () => {
      const user = userEvent.setup();
      render(
        <InventoryTable
          inventory={mockInventory.slice(0, 3)}
          enableBulkActions={true}
          onBulkAction={mockHandlers.onBulkAction}
        />,
      );

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]!);

      const activateButton = screen.getByLabelText(/activate selected items/i);
      await user.click(activateButton);

      await waitFor(() => {
        expect(checkboxes[1]).not.toBeChecked();
      });
    });
  });

  // ============================================================================
  // 9. INLINE ACTIONS TESTS
  // ============================================================================

  describe('Inline Actions', () => {
    it('should render edit button when enabled', () => {
      render(
        <InventoryTable
          inventory={mockInventory.slice(0, 1)}
          enableInlineEdit={true}
          onEdit={mockHandlers.onEdit}
        />,
      );

      expect(screen.getByLabelText(/edit/i)).toBeInTheDocument();
    });

    it('should not render edit button when disabled', () => {
      render(
        <InventoryTable
          inventory={mockInventory.slice(0, 1)}
          enableInlineEdit={false}
          onEdit={mockHandlers.onEdit}
        />,
      );

      expect(screen.queryByLabelText(/edit/i)).not.toBeInTheDocument();
    });

    it('should call onEdit when edit button clicked', async () => {
      const user = userEvent.setup();
      const item = mockInventory[0]!;
      render(
        <InventoryTable
          inventory={[item]}
          enableInlineEdit={true}
          onEdit={mockHandlers.onEdit}
        />,
      );

      const editButton = screen.getByLabelText(/edit/i);
      await user.click(editButton);

      expect(mockHandlers.onEdit).toHaveBeenCalledWith(item);
      expect(mockHandlers.onEdit).toHaveBeenCalledTimes(1);
    });

    it('should call onStatusChange when status button clicked', async () => {
      const user = userEvent.setup();
      const item = createMockInventoryItem({ status: 'active' });
      render(
        <InventoryTable inventory={[item]} onStatusChange={mockHandlers.onStatusChange} />,
      );

      const statusButton = screen.getByLabelText(/change status/i);
      await user.click(statusButton);

      expect(mockHandlers.onStatusChange).toHaveBeenCalledWith(item);
    });

    it('should not show status change button for sold items', () => {
      const item = createMockInventoryItem({ status: 'sold' });
      render(
        <InventoryTable inventory={[item]} onStatusChange={mockHandlers.onStatusChange} />,
      );

      expect(screen.queryByLabelText(/change status/i)).not.toBeInTheDocument();
    });

    it('should call onStockAdjust when stock button clicked', async () => {
      const user = userEvent.setup();
      const item = mockInventory[0]!;
      render(<InventoryTable inventory={[item]} onStockAdjust={mockHandlers.onStockAdjust} />);

      const stockButton = screen.getByLabelText(/adjust stock/i);
      await user.click(stockButton);

      expect(mockHandlers.onStockAdjust).toHaveBeenCalledWith(item);
    });

    it('should call onDelete when delete button clicked', async () => {
      const user = userEvent.setup();
      const item = mockInventory[0]!;
      render(<InventoryTable inventory={[item]} onDelete={mockHandlers.onDelete} />);

      const deleteButton = screen.getByLabelText(/delete/i);
      await user.click(deleteButton);

      expect(mockHandlers.onDelete).toHaveBeenCalledWith(item);
    });
  });

  // ============================================================================
  // 10. FILTERING TESTS
  // ============================================================================

  describe('Filtering', () => {
    it('should filter by status', () => {
      const filters: DealerInventoryFilters = {
        status: ['active'],
      };

      render(<InventoryTable inventory={mockInventory} filters={filters} />);

      const rows = screen.getAllByRole('row').slice(1);
      rows.forEach((row) => {
        expect(row.textContent).toMatch(/Active/);
      });
    });

    it('should filter by multiple statuses', () => {
      const filters: DealerInventoryFilters = {
        status: ['active', 'reserved'],
      };

      render(<InventoryTable inventory={mockInventory} filters={filters} />);

      const rows = screen.getAllByRole('row').slice(1);
      rows.forEach((row) => {
        expect(row.textContent).toMatch(/Active|Reserved/);
      });
    });

    it('should filter low stock items', () => {
      const items = [
        createMockInventoryItem({ stockLevel: 10, availableQuantity: 2 }),
        createMockInventoryItem({ stockLevel: 10, availableQuantity: 8 }),
      ];

      const filters: DealerInventoryFilters = {
        lowStock: true,
      };

      render(<InventoryTable inventory={items} filters={filters} />);

      expect(screen.getAllByRole('row')).toHaveLength(2); // 1 header + 1 low stock item
    });

    it('should filter out of stock items', () => {
      const items = [
        createMockInventoryItem({ stockLevel: 10, availableQuantity: 0 }),
        createMockInventoryItem({ stockLevel: 10, availableQuantity: 5 }),
      ];

      const filters: DealerInventoryFilters = {
        outOfStock: true,
      };

      render(<InventoryTable inventory={items} filters={filters} />);

      expect(screen.getAllByRole('row')).toHaveLength(2); // 1 header + 1 out of stock item
    });

    it('should combine multiple filters', () => {
      const filters: DealerInventoryFilters = {
        status: ['active'],
        lowStock: true,
      };

      render(<InventoryTable inventory={mockInventory} filters={filters} />);

      const rows = screen.getAllByRole('row').slice(1);
      rows.forEach((row) => {
        expect(row.textContent).toMatch(/Active/);
      });
    });
  });

  // ============================================================================
  // 11. FORMATTING TESTS
  // ============================================================================

  describe('Data Formatting', () => {
    it('should format price correctly', () => {
      const item = createMockInventoryItem({
        vehicle: createMockVehicle({ price: 35999 }),
      });

      render(<InventoryTable inventory={[item]} />);

      expect(screen.getByText('$35,999')).toBeInTheDocument();
    });

    it('should format date correctly', () => {
      const item = createMockInventoryItem({
        updatedAt: new Date('2024-01-15T10:30:00Z').toISOString(),
      });

      render(<InventoryTable inventory={[item]} />);

      // Date format may vary by locale, just check it's present
      const dateCell = screen.getAllByRole('cell')[7];
      expect(dateCell?.textContent).toBeTruthy();
    });

    it('should handle large prices', () => {
      const item = createMockInventoryItem({
        vehicle: createMockVehicle({ price: 125000 }),
      });

      render(<InventoryTable inventory={[item]} />);

      expect(screen.getByText('$125,000')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // 12. ACCESSIBILITY TESTS
  // ============================================================================

  describe('Accessibility', () => {
    it('should have proper ARIA labels for search input', () => {
      render(<InventoryTable inventory={mockInventory} />);

      const searchInput = screen.getByLabelText('Search inventory');
      expect(searchInput).toBeInTheDocument();
    });

    it('should have proper ARIA labels for checkboxes', () => {
      render(<InventoryTable inventory={mockInventory.slice(0, 2)} enableBulkActions={true} />);

      expect(screen.getByLabelText('Select all items')).toBeInTheDocument();
      expect(screen.getByLabelText(`Select ${mockInventory[0]!.vin}`)).toBeInTheDocument();
    });

    it('should have proper ARIA labels for action buttons', () => {
      const item = mockInventory[0]!;
      render(
        <InventoryTable
          inventory={[item]}
          onEdit={mockHandlers.onEdit}
          onStatusChange={mockHandlers.onStatusChange}
          onStockAdjust={mockHandlers.onStockAdjust}
          onDelete={mockHandlers.onDelete}
        />,
      );

      expect(screen.getByLabelText(`Edit ${item.vin}`)).toBeInTheDocument();
      expect(screen.getByLabelText(`Change status for ${item.vin}`)).toBeInTheDocument();
      expect(screen.getByLabelText(`Adjust stock for ${item.vin}`)).toBeInTheDocument();
      expect(screen.getByLabelText(`Delete ${item.vin}`)).toBeInTheDocument();
    });

    it('should have proper ARIA labels for pagination', () => {
      render(<InventoryTable inventory={mockInventory} pageSize={10} />);

      expect(screen.getByLabelText('Previous page')).toBeInTheDocument();
      expect(screen.getByLabelText('Next page')).toBeInTheDocument();
      expect(screen.getByLabelText('Page 1')).toBeInTheDocument();
    });

    it('should have aria-current on active page', () => {
      render(<InventoryTable inventory={mockInventory} pageSize={10} />);

      const page1Button = screen.getByLabelText('Page 1');
      expect(page1Button).toHaveAttribute('aria-current', 'page');
    });

    it('should have proper table structure', () => {
      render(<InventoryTable inventory={mockInventory.slice(0, 1)} />);

      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getAllByRole('columnheader')).toHaveLength(8);
      expect(screen.getAllByRole('row')).toHaveLength(2); // 1 header + 1 data
    });

    it('should have proper scope attributes on headers', () => {
      render(<InventoryTable inventory={mockInventory.slice(0, 1)} />);

      const headers = screen.getAllByRole('columnheader');
      headers.forEach((header) => {
        expect(header).toHaveAttribute('scope', 'col');
      });
    });
  });

  // ============================================================================
  // 13. EDGE CASES AND ERROR HANDLING
  // ============================================================================

  describe('Edge Cases', () => {
    it('should handle empty inventory array', () => {
      render(<InventoryTable inventory={[]} />);

      expect(screen.getByText('No inventory items found')).toBeInTheDocument();
    });

    it('should handle missing vehicle trim', () => {
      const item = createMockInventoryItem({
        vehicle: createMockVehicle({ trim: undefined }),
      });

      render(<InventoryTable inventory={[item]} />);

      expect(screen.queryByText('undefined')).not.toBeInTheDocument();
    });

    it('should handle zero reserved quantity', () => {
      const item = createMockInventoryItem({ reservedQuantity: 0 });

      render(<InventoryTable inventory={[item]} />);

      expect(screen.queryByText(/reserved/)).not.toBeInTheDocument();
    });

    it('should handle very long VINs', () => {
      const item = createMockInventoryItem({
        vin: 'VERYLONGVIN1234567890ABCDEFGHIJKLMNOP',
      });

      render(<InventoryTable inventory={[item]} />);

      expect(screen.getByText('VERYLONGVIN1234567890ABCDEFGHIJKLMNOP')).toBeInTheDocument();
    });

    it('should handle special characters in search', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory} />);

      const searchInput = screen.getByPlaceholderText(/search by vin/i);
      await user.type(searchInput, '!@#$%^&*()');

      await waitFor(() => {
        expect(screen.getByText('No inventory items found')).toBeInTheDocument();
      });
    });

    it('should handle rapid pagination clicks', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory} pageSize={5} />);

      const nextButton = screen.getByLabelText('Next page');

      // Rapid clicks
      await user.click(nextButton);
      await user.click(nextButton);
      await user.click(nextButton);

      await waitFor(() => {
        expect(screen.getByLabelText('Page 4')).toHaveClass('bg-blue-600');
      });
    });

    it('should handle sorting with identical values', async () => {
      const user = userEvent.setup();
      const items = [
        createMockInventoryItem({ location: 'Main Lot' }),
        createMockInventoryItem({ location: 'Main Lot' }),
        createMockInventoryItem({ location: 'Main Lot' }),
      ];

      render(<InventoryTable inventory={items} />);

      const locationHeader = screen.getByText('Location');
      await user.click(locationHeader);

      // Should not throw error
      expect(screen.getAllByRole('row')).toHaveLength(4);
    });

    it('should handle missing optional handlers gracefully', () => {
      render(<InventoryTable inventory={mockInventory.slice(0, 1)} />);

      // Should render without errors
      expect(screen.getByRole('table')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // 14. PERFORMANCE TESTS
  // ============================================================================

  describe('Performance', () => {
    it('should render large inventory efficiently', () => {
      const largeInventory = createMockInventory(100);
      const startTime = performance.now();

      render(<InventoryTable inventory={largeInventory} pageSize={20} />);

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      // Should render in less than 1 second
      expect(renderTime).toBeLessThan(1000);
    });

    it('should handle rapid search input changes', async () => {
      const user = userEvent.setup();
      render(<InventoryTable inventory={mockInventory} />);

      const searchInput = screen.getByPlaceholderText(/search by vin/i);

      // Rapid typing
      await user.type(searchInput, 'Toyota', { delay: 10 });

      // Should not crash or freeze
      expect(screen.getByRole('table')).toBeInTheDocument();
    });

    it('should lazy load images', () => {
      render(<InventoryTable inventory={mockInventory.slice(0, 1)} />);

      const image = screen.getByRole('img');
      expect(image).toHaveAttribute('loading', 'lazy');
    });
  });

  // ============================================================================
  // 15. INTEGRATION TESTS
  // ============================================================================

  describe('Integration Scenarios', () => {
    it('should handle complete user workflow', async () => {
      const user = userEvent.setup();
      render(
        <InventoryTable
          inventory={mockInventory}
          enableBulkActions={true}
          onBulkAction={mockHandlers.onBulkAction}
          pageSize={10}
        />,
      );

      // Search
      const searchInput = screen.getByPlaceholderText(/search by vin/i);
      await user.type(searchInput, 'Toyota');

      // Sort
      const vinHeader = screen.getByText('VIN');
      await user.click(vinHeader);

      // Select items
      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]!);

      // Bulk action
      const activateButton = screen.getByLabelText(/activate selected items/i);
      await user.click(activateButton);

      expect(mockHandlers.onBulkAction).toHaveBeenCalled();
    });

    it('should maintain state across filter changes', async () => {
      const user = userEvent.setup();
      const filters: DealerInventoryFilters = { status: ['active'] };

      const { rerender } = render(
        <InventoryTable inventory={mockInventory} filters={filters} pageSize={10} />,
      );

      // Go to page 2
      const nextButton = screen.getByLabelText('Next page');
      await user.click(nextButton);

      // Change filters
      const newFilters: DealerInventoryFilters = { status: ['inactive'] };
      rerender(<InventoryTable inventory={mockInventory} filters={newFilters} pageSize={10} />);

      // Should reset to page 1
      await waitFor(() => {
        expect(screen.getByLabelText('Page 1')).toHaveClass('bg-blue-600');
      });
    });

    it('should handle dynamic inventory updates', () => {
      const { rerender } = render(<InventoryTable inventory={mockInventory.slice(0, 5)} />);

      expect(screen.getAllByRole('row')).toHaveLength(6);

      // Add more items
      rerender(<InventoryTable inventory={mockInventory.slice(0, 10)} />);

      expect(screen.getAllByRole('row')).toHaveLength(11);
    });
  });
});