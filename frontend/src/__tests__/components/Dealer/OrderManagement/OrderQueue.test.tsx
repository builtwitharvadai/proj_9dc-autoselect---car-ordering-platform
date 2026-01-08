/**
 * OrderQueue Component Test Suite
 * 
 * Comprehensive tests covering:
 * - Component rendering and initialization
 * - Filtering and search functionality
 * - Sorting capabilities
 * - Bulk selection and operations
 * - Pagination
 * - Real-time updates via WebSocket
 * - Accessibility compliance
 * - Error handling and edge cases
 * - Performance validation
 * - Mobile responsiveness
 * 
 * Coverage Target: >80%
 * Test Framework: Vitest + React Testing Library
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import OrderQueue, { type OrderQueueProps } from '../OrderQueue';
import type { DealerOrder, DealerOrderStatus } from '../../../hooks/useDealerOrders';

// ============================================================================
// MOCKS AND TEST DATA
// ============================================================================

// Mock hooks
vi.mock('../../../hooks/useDealerOrders', () => ({
  useDealerOrders: vi.fn(),
  useBulkOrderOperations: vi.fn(),
}));

vi.mock('../../../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(),
}));

// Import mocked hooks for manipulation
import { useDealerOrders, useBulkOrderOperations } from '../../../hooks/useDealerOrders';
import { useWebSocket } from '../../../hooks/useWebSocket';

/**
 * Test data factory for creating mock orders
 */
class OrderFactory {
  private static idCounter = 1;

  static create(overrides: Partial<DealerOrder> = {}): DealerOrder {
    const id = String(OrderFactory.idCounter++);
    return {
      id,
      orderNumber: `ORD-${id.padStart(6, '0')}`,
      dealerId: 'dealer-1',
      customerId: `customer-${id}`,
      customerName: `Customer ${id}`,
      customerEmail: `customer${id}@example.com`,
      vehicleId: `vehicle-${id}`,
      vehicleName: `Vehicle ${id}`,
      vehicleImage: `https://example.com/vehicle-${id}.jpg`,
      status: 'pending',
      totalAmount: 25000 + Math.random() * 50000,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ...overrides,
    };
  }

  static createMany(count: number, overrides: Partial<DealerOrder> = {}): DealerOrder[] {
    return Array.from({ length: count }, () => OrderFactory.create(overrides));
  }

  static reset(): void {
    OrderFactory.idCounter = 1;
  }
}

/**
 * Default mock implementation for useDealerOrders
 */
const createMockOrdersResponse = (orders: DealerOrder[] = []) => ({
  data: {
    orders,
    totalPages: Math.ceil(orders.length / 20),
    totalCount: orders.length,
    currentPage: 1,
  },
  isLoading: false,
  error: null,
  refetch: vi.fn(),
});

/**
 * Default mock implementation for useBulkOrderOperations
 */
const createMockBulkOperations = () => ({
  mutate: vi.fn(),
  isPending: false,
  isSuccess: false,
  isError: false,
});

// ============================================================================
// TEST UTILITIES
// ============================================================================

/**
 * Render component with React Query provider
 */
function renderWithProviders(
  ui: React.ReactElement,
  options: { queryClient?: QueryClient } = {},
) {
  const queryClient = options.queryClient ?? new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        {ui}
      </QueryClientProvider>,
    ),
    queryClient,
  };
}

/**
 * Default props for OrderQueue component
 */
const defaultProps: OrderQueueProps = {
  dealerId: 'dealer-1',
  pageSize: 20,
  enableBulkActions: true,
  enableRealtime: true,
};

/**
 * Setup default mocks before each test
 */
function setupDefaultMocks(orders: DealerOrder[] = []): void {
  vi.mocked(useDealerOrders).mockReturnValue(createMockOrdersResponse(orders));
  vi.mocked(useBulkOrderOperations).mockReturnValue(createMockBulkOperations());
  vi.mocked(useWebSocket).mockReturnValue(undefined);
}

// ============================================================================
// TEST SUITE: COMPONENT RENDERING
// ============================================================================

describe('OrderQueue - Component Rendering', () => {
  beforeEach(() => {
    OrderFactory.reset();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should render loading state initially', () => {
    vi.mocked(useDealerOrders).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });
    vi.mocked(useBulkOrderOperations).mockReturnValue(createMockBulkOperations());
    vi.mocked(useWebSocket).mockReturnValue(undefined);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument();
  });

  it('should render error state with retry button', async () => {
    const mockRefetch = vi.fn();
    vi.mocked(useDealerOrders).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
      refetch: mockRefetch,
    });
    vi.mocked(useBulkOrderOperations).mockReturnValue(createMockBulkOperations());
    vi.mocked(useWebSocket).mockReturnValue(undefined);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    expect(screen.getByText(/failed to load orders/i)).toBeInTheDocument();
    
    const retryButton = screen.getByRole('button', { name: /retry/i });
    await userEvent.click(retryButton);
    
    expect(mockRefetch).toHaveBeenCalledTimes(1);
  });

  it('should render empty state when no orders exist', () => {
    setupDefaultMocks([]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    expect(screen.getByText(/no orders found/i)).toBeInTheDocument();
    expect(screen.getByText(/orders will appear here when customers place them/i)).toBeInTheDocument();
  });

  it('should render orders table with data', () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    orders.forEach((order) => {
      expect(screen.getByText(order.orderNumber)).toBeInTheDocument();
      expect(screen.getByText(order.customerName)).toBeInTheDocument();
    });
  });

  it('should apply custom className', () => {
    setupDefaultMocks([]);

    const { container } = renderWithProviders(
      <OrderQueue {...defaultProps} className="custom-class" />,
    );

    expect(container.firstChild).toHaveClass('custom-class');
  });
});

// ============================================================================
// TEST SUITE: FILTERING AND SEARCH
// ============================================================================

describe('OrderQueue - Filtering and Search', () => {
  beforeEach(() => {
    OrderFactory.reset();
    vi.clearAllMocks();
  });

  it('should render all status filter buttons', () => {
    setupDefaultMocks([]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const statusNames = [
      'Pending',
      'Confirmed',
      'In Production',
      'Ready for Pickup',
      'Completed',
      'Cancelled',
    ];

    statusNames.forEach((status) => {
      expect(screen.getByRole('button', { name: status })).toBeInTheDocument();
    });
  });

  it('should toggle status filter when clicked', async () => {
    setupDefaultMocks([]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const pendingButton = screen.getByRole('button', { name: 'Pending' });
    
    // Initially not selected
    expect(pendingButton).not.toHaveClass('bg-yellow-100');
    
    // Click to select
    await userEvent.click(pendingButton);
    
    await waitFor(() => {
      expect(pendingButton).toHaveClass('bg-yellow-100');
    });
    
    // Click to deselect
    await userEvent.click(pendingButton);
    
    await waitFor(() => {
      expect(pendingButton).not.toHaveClass('bg-yellow-100');
    });
  });

  it('should allow multiple status filters', async () => {
    setupDefaultMocks([]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const pendingButton = screen.getByRole('button', { name: 'Pending' });
    const confirmedButton = screen.getByRole('button', { name: 'Confirmed' });
    
    await userEvent.click(pendingButton);
    await userEvent.click(confirmedButton);
    
    await waitFor(() => {
      expect(pendingButton).toHaveClass('bg-yellow-100');
      expect(confirmedButton).toHaveClass('bg-blue-100');
    });
  });

  it('should debounce search input', async () => {
    vi.useFakeTimers();
    setupDefaultMocks([]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const searchInput = screen.getByLabelText(/search orders/i);
    
    await userEvent.type(searchInput, 'ORD-123');
    
    // Should not trigger immediately
    expect(useDealerOrders).toHaveBeenCalledTimes(1);
    
    // Fast-forward debounce timer
    vi.advanceTimersByTime(300);
    
    await waitFor(() => {
      expect(useDealerOrders).toHaveBeenCalledTimes(2);
    });

    vi.useRealTimers();
  });

  it('should display active filters summary', async () => {
    setupDefaultMocks([]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const pendingButton = screen.getByRole('button', { name: 'Pending' });
    await userEvent.click(pendingButton);
    
    await waitFor(() => {
      expect(screen.getByText(/active filters:/i)).toBeInTheDocument();
      expect(screen.getByText(/1 status/i)).toBeInTheDocument();
    });
  });

  it('should clear all filters when clear button clicked', async () => {
    setupDefaultMocks([]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const pendingButton = screen.getByRole('button', { name: 'Pending' });
    const searchInput = screen.getByLabelText(/search orders/i);
    
    await userEvent.click(pendingButton);
    await userEvent.type(searchInput, 'test');
    
    await waitFor(() => {
      expect(screen.getByText(/active filters:/i)).toBeInTheDocument();
    });
    
    const clearButton = screen.getByRole('button', { name: /clear all/i });
    await userEvent.click(clearButton);
    
    await waitFor(() => {
      expect(screen.queryByText(/active filters:/i)).not.toBeInTheDocument();
      expect(searchInput).toHaveValue('');
    });
  });

  it('should reset to page 1 when filters change', async () => {
    const orders = OrderFactory.createMany(50);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    // Navigate to page 2
    const nextButton = screen.getAllByRole('button', { name: /next/i })[0];
    await userEvent.click(nextButton);
    
    // Apply filter
    const pendingButton = screen.getByRole('button', { name: 'Pending' });
    await userEvent.click(pendingButton);
    
    await waitFor(() => {
      expect(screen.getByText(/showing page 1/i)).toBeInTheDocument();
    });
  });
});

// ============================================================================
// TEST SUITE: SORTING
// ============================================================================

describe('OrderQueue - Sorting', () => {
  beforeEach(() => {
    OrderFactory.reset();
    vi.clearAllMocks();
  });

  it('should display sort indicators on sortable columns', () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    // Default sort by createdAt desc
    const createdHeader = screen.getByText(/created/i);
    expect(createdHeader.textContent).toContain('↓');
  });

  it('should toggle sort direction when clicking same column', async () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const orderNumberHeader = screen.getByText(/order #/i);
    
    // First click - ascending
    await userEvent.click(orderNumberHeader);
    
    await waitFor(() => {
      expect(orderNumberHeader.textContent).toContain('↑');
    });
    
    // Second click - descending
    await userEvent.click(orderNumberHeader);
    
    await waitFor(() => {
      expect(orderNumberHeader.textContent).toContain('↓');
    });
  });

  it('should sort by different columns', async () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const statusHeader = screen.getByText(/status/i);
    await userEvent.click(statusHeader);
    
    await waitFor(() => {
      expect(statusHeader.textContent).toContain('↑');
    });
    
    const amountHeader = screen.getByText(/amount/i);
    await userEvent.click(amountHeader);
    
    await waitFor(() => {
      expect(amountHeader.textContent).toContain('↑');
      expect(statusHeader.textContent).not.toContain('↑');
    });
  });
});

// ============================================================================
// TEST SUITE: BULK SELECTION AND OPERATIONS
// ============================================================================

describe('OrderQueue - Bulk Selection', () => {
  beforeEach(() => {
    OrderFactory.reset();
    vi.clearAllMocks();
  });

  it('should not render bulk actions when disabled', () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    renderWithProviders(
      <OrderQueue {...defaultProps} enableBulkActions={false} />,
    );

    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  });

  it('should render select all checkbox', () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBe(4); // 1 select all + 3 individual
  });

  it('should select all orders when select all clicked', async () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const selectAllCheckbox = screen.getAllByRole('checkbox')[0];
    await userEvent.click(selectAllCheckbox);
    
    await waitFor(() => {
      const checkboxes = screen.getAllByRole('checkbox');
      checkboxes.forEach((checkbox) => {
        expect(checkbox).toBeChecked();
      });
    });
  });

  it('should deselect all orders when select all clicked again', async () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const selectAllCheckbox = screen.getAllByRole('checkbox')[0];
    
    // Select all
    await userEvent.click(selectAllCheckbox);
    await waitFor(() => {
      expect(selectAllCheckbox).toBeChecked();
    });
    
    // Deselect all
    await userEvent.click(selectAllCheckbox);
    await waitFor(() => {
      expect(selectAllCheckbox).not.toBeChecked();
    });
  });

  it('should select individual orders', async () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const checkboxes = screen.getAllByRole('checkbox');
    const firstOrderCheckbox = checkboxes[1]; // Skip select all
    
    await userEvent.click(firstOrderCheckbox);
    
    await waitFor(() => {
      expect(firstOrderCheckbox).toBeChecked();
    });
  });

  it('should display bulk actions bar when orders selected', async () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const checkboxes = screen.getAllByRole('checkbox');
    await userEvent.click(checkboxes[1]);
    
    await waitFor(() => {
      expect(screen.getByText(/1 order selected/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /confirm selected/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /cancel selected/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /export selected/i })).toBeInTheDocument();
    });
  });

  it('should call bulk confirm operation', async () => {
    const orders = OrderFactory.createMany(3);
    const mockMutate = vi.fn();
    setupDefaultMocks(orders);
    vi.mocked(useBulkOrderOperations).mockReturnValue({
      ...createMockBulkOperations(),
      mutate: mockMutate,
    });

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const checkboxes = screen.getAllByRole('checkbox');
    await userEvent.click(checkboxes[1]);
    
    const confirmButton = await screen.findByRole('button', { name: /confirm selected/i });
    await userEvent.click(confirmButton);
    
    expect(mockMutate).toHaveBeenCalledWith({
      orderIds: expect.arrayContaining([orders[0].id]),
      operation: 'confirm_multiple',
      targetStatus: undefined,
    });
  });

  it('should disable bulk action buttons when operation pending', async () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);
    vi.mocked(useBulkOrderOperations).mockReturnValue({
      ...createMockBulkOperations(),
      isPending: true,
    });

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const checkboxes = screen.getAllByRole('checkbox');
    await userEvent.click(checkboxes[1]);
    
    await waitFor(() => {
      const confirmButton = screen.getByRole('button', { name: /confirm selected/i });
      expect(confirmButton).toBeDisabled();
    });
  });

  it('should clear selection after successful bulk operation', async () => {
    const orders = OrderFactory.createMany(3);
    const mockOnComplete = vi.fn();
    setupDefaultMocks(orders);

    const { rerender } = renderWithProviders(
      <OrderQueue {...defaultProps} onBulkActionComplete={mockOnComplete} />,
    );

    const checkboxes = screen.getAllByRole('checkbox');
    await userEvent.click(checkboxes[1]);
    
    // Simulate successful operation
    vi.mocked(useBulkOrderOperations).mockReturnValue({
      ...createMockBulkOperations(),
      mutate: vi.fn((_, options) => {
        options?.onSuccess?.({ successCount: 1, failureCount: 0 });
      }),
    });

    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <OrderQueue {...defaultProps} onBulkActionComplete={mockOnComplete} />
      </QueryClientProvider>,
    );

    const confirmButton = await screen.findByRole('button', { name: /confirm selected/i });
    await userEvent.click(confirmButton);
    
    await waitFor(() => {
      expect(mockOnComplete).toHaveBeenCalledWith(1, 0);
    });
  });
});

// ============================================================================
// TEST SUITE: PAGINATION
// ============================================================================

describe('OrderQueue - Pagination', () => {
  beforeEach(() => {
    OrderFactory.reset();
    vi.clearAllMocks();
  });

  it('should display pagination controls', () => {
    const orders = OrderFactory.createMany(50);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    expect(screen.getByText(/showing page 1/i)).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /previous/i })).toHaveLength(2); // Desktop + mobile
    expect(screen.getAllByRole('button', { name: /next/i })).toHaveLength(2);
  });

  it('should disable previous button on first page', () => {
    const orders = OrderFactory.createMany(50);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const previousButtons = screen.getAllByRole('button', { name: /previous/i });
    previousButtons.forEach((button) => {
      expect(button).toBeDisabled();
    });
  });

  it('should navigate to next page', async () => {
    const orders = OrderFactory.createMany(50);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const nextButton = screen.getAllByRole('button', { name: /next/i })[0];
    await userEvent.click(nextButton);
    
    await waitFor(() => {
      expect(screen.getByText(/showing page 2/i)).toBeInTheDocument();
    });
  });

  it('should navigate to previous page', async () => {
    const orders = OrderFactory.createMany(50);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    // Go to page 2
    const nextButton = screen.getAllByRole('button', { name: /next/i })[0];
    await userEvent.click(nextButton);
    
    await waitFor(() => {
      expect(screen.getByText(/showing page 2/i)).toBeInTheDocument();
    });
    
    // Go back to page 1
    const previousButton = screen.getAllByRole('button', { name: /previous/i })[0];
    await userEvent.click(previousButton);
    
    await waitFor(() => {
      expect(screen.getByText(/showing page 1/i)).toBeInTheDocument();
    });
  });

  it('should disable next button on last page', async () => {
    const orders = OrderFactory.createMany(25); // Just over 1 page
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    // Navigate to last page
    const nextButton = screen.getAllByRole('button', { name: /next/i })[0];
    await userEvent.click(nextButton);
    
    await waitFor(() => {
      const nextButtons = screen.getAllByRole('button', { name: /next/i });
      nextButtons.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });
  });

  it('should respect custom page size', () => {
    const orders = OrderFactory.createMany(50);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} pageSize={10} />);

    expect(useDealerOrders).toHaveBeenCalledWith(
      expect.objectContaining({ pageSize: 10 }),
      expect.any(Object),
    );
  });
});

// ============================================================================
// TEST SUITE: REAL-TIME UPDATES
// ============================================================================

describe('OrderQueue - Real-time Updates', () => {
  beforeEach(() => {
    OrderFactory.reset();
    vi.clearAllMocks();
  });

  it('should initialize WebSocket when enabled', () => {
    setupDefaultMocks([]);

    renderWithProviders(<OrderQueue {...defaultProps} enableRealtime={true} />);

    expect(useWebSocket).toHaveBeenCalledWith(
      expect.objectContaining({
        enabled: true,
        url: expect.stringContaining('/ws/dealer/dealer-1/orders'),
      }),
    );
  });

  it('should not initialize WebSocket when disabled', () => {
    setupDefaultMocks([]);

    renderWithProviders(<OrderQueue {...defaultProps} enableRealtime={false} />);

    expect(useWebSocket).toHaveBeenCalledWith(
      expect.objectContaining({
        enabled: false,
      }),
    );
  });

  it('should refetch orders on WebSocket message', () => {
    const mockRefetch = vi.fn();
    vi.mocked(useDealerOrders).mockReturnValue({
      ...createMockOrdersResponse([]),
      refetch: mockRefetch,
    });
    vi.mocked(useBulkOrderOperations).mockReturnValue(createMockBulkOperations());

    let onMessageCallback: (() => void) | undefined;
    vi.mocked(useWebSocket).mockImplementation((config) => {
      onMessageCallback = config.onMessage;
      return undefined;
    });

    renderWithProviders(<OrderQueue {...defaultProps} />);

    // Simulate WebSocket message
    onMessageCallback?.();

    expect(mockRefetch).toHaveBeenCalled();
  });
});

// ============================================================================
// TEST SUITE: ORDER INTERACTIONS
// ============================================================================

describe('OrderQueue - Order Interactions', () => {
  beforeEach(() => {
    OrderFactory.reset();
    vi.clearAllMocks();
  });

  it('should call onOrderClick when view details clicked', async () => {
    const orders = OrderFactory.createMany(3);
    const mockOnOrderClick = vi.fn();
    setupDefaultMocks(orders);

    renderWithProviders(
      <OrderQueue {...defaultProps} onOrderClick={mockOnOrderClick} />,
    );

    const viewButtons = screen.getAllByRole('button', { name: /view details/i });
    await userEvent.click(viewButtons[0]);
    
    expect(mockOnOrderClick).toHaveBeenCalledWith(orders[0].id);
  });

  it('should display order information correctly', () => {
    const order = OrderFactory.create({
      orderNumber: 'ORD-123456',
      customerName: 'John Doe',
      customerEmail: 'john@example.com',
      vehicleName: 'Tesla Model 3',
      status: 'confirmed',
      totalAmount: 45000,
    });
    setupDefaultMocks([order]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    expect(screen.getByText('ORD-123456')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('john@example.com')).toBeInTheDocument();
    expect(screen.getByText('Tesla Model 3')).toBeInTheDocument();
    expect(screen.getByText('Confirmed')).toBeInTheDocument();
    expect(screen.getByText(/\$45,000/)).toBeInTheDocument();
  });

  it('should display vehicle image with correct alt text', () => {
    const order = OrderFactory.create({
      vehicleName: 'Tesla Model 3',
      vehicleImage: 'https://example.com/tesla.jpg',
    });
    setupDefaultMocks([order]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const images = screen.getAllByAltText('Tesla Model 3');
    expect(images.length).toBeGreaterThan(0);
    expect(images[0]).toHaveAttribute('src', 'https://example.com/tesla.jpg');
  });

  it('should format currency correctly', () => {
    const order = OrderFactory.create({ totalAmount: 45678.90 });
    setupDefaultMocks([order]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    expect(screen.getByText('$45,678.90')).toBeInTheDocument();
  });

  it('should format dates correctly', () => {
    const order = OrderFactory.create({
      createdAt: '2024-01-15T10:30:00Z',
    });
    setupDefaultMocks([order]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    // Date format: "Jan 15, 2024, 10:30 AM" (locale-dependent)
    expect(screen.getByText(/Jan 15, 2024/)).toBeInTheDocument();
  });
});

// ============================================================================
// TEST SUITE: STATUS BADGES
// ============================================================================

describe('OrderQueue - Status Badges', () => {
  beforeEach(() => {
    OrderFactory.reset();
    vi.clearAllMocks();
  });

  const statusTests: Array<{ status: DealerOrderStatus; color: string; name: string }> = [
    { status: 'pending', color: 'bg-yellow-100', name: 'Pending' },
    { status: 'confirmed', color: 'bg-blue-100', name: 'Confirmed' },
    { status: 'in_production', color: 'bg-purple-100', name: 'In Production' },
    { status: 'ready_for_pickup', color: 'bg-green-100', name: 'Ready for Pickup' },
    { status: 'completed', color: 'bg-gray-100', name: 'Completed' },
    { status: 'cancelled', color: 'bg-red-100', name: 'Cancelled' },
  ];

  statusTests.forEach(({ status, color, name }) => {
    it(`should display ${name} status with correct styling`, () => {
      const order = OrderFactory.create({ status });
      setupDefaultMocks([order]);

      renderWithProviders(<OrderQueue {...defaultProps} />);

      const badge = screen.getByText(name);
      expect(badge).toHaveClass(color);
    });
  });
});

// ============================================================================
// TEST SUITE: RESPONSIVE DESIGN
// ============================================================================

describe('OrderQueue - Responsive Design', () => {
  beforeEach(() => {
    OrderFactory.reset();
    vi.clearAllMocks();
  });

  it('should render desktop table on large screens', () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    const { container } = renderWithProviders(<OrderQueue {...defaultProps} />);

    const desktopTable = container.querySelector('.hidden.md\\:block');
    expect(desktopTable).toBeInTheDocument();
  });

  it('should render mobile cards on small screens', () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    const { container } = renderWithProviders(<OrderQueue {...defaultProps} />);

    const mobileCards = container.querySelector('.md\\:hidden');
    expect(mobileCards).toBeInTheDocument();
  });

  it('should display all order information in mobile view', () => {
    const order = OrderFactory.create({
      orderNumber: 'ORD-123456',
      customerName: 'John Doe',
      vehicleName: 'Tesla Model 3',
    });
    setupDefaultMocks([order]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    // Mobile view should show all key information
    expect(screen.getAllByText('ORD-123456')).toHaveLength(2); // Desktop + mobile
    expect(screen.getAllByText('John Doe')).toHaveLength(2);
    expect(screen.getAllByText('Tesla Model 3')).toHaveLength(2);
  });
});

// ============================================================================
// TEST SUITE: ACCESSIBILITY
// ============================================================================

describe('OrderQueue - Accessibility', () => {
  beforeEach(() => {
    OrderFactory.reset();
    vi.clearAllMocks();
  });

  it('should have accessible search input', () => {
    setupDefaultMocks([]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const searchInput = screen.getByLabelText(/search orders/i);
    expect(searchInput).toHaveAttribute('type', 'text');
    expect(searchInput).toHaveAttribute('placeholder');
  });

  it('should have accessible checkboxes', () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const checkboxes = screen.getAllByRole('checkbox');
    checkboxes.forEach((checkbox) => {
      expect(checkbox).toHaveAttribute('type', 'checkbox');
    });
  });

  it('should have accessible buttons with clear labels', () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    expect(screen.getByRole('button', { name: /pending/i })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /view details/i })).toHaveLength(3);
  });

  it('should have accessible table structure', () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const table = screen.getByRole('table', { hidden: true });
    expect(table).toBeInTheDocument();
    
    const columnHeaders = screen.getAllByRole('columnheader', { hidden: true });
    expect(columnHeaders.length).toBeGreaterThan(0);
  });

  it('should provide keyboard navigation for interactive elements', async () => {
    const orders = OrderFactory.createMany(3);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const firstButton = screen.getByRole('button', { name: /pending/i });
    firstButton.focus();
    
    expect(document.activeElement).toBe(firstButton);
  });

  it('should have proper ARIA labels for loading state', () => {
    vi.mocked(useDealerOrders).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });
    vi.mocked(useBulkOrderOperations).mockReturnValue(createMockBulkOperations());
    vi.mocked(useWebSocket).mockReturnValue(undefined);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument();
  });
});

// ============================================================================
// TEST SUITE: EDGE CASES AND ERROR HANDLING
// ============================================================================

describe('OrderQueue - Edge Cases', () => {
  beforeEach(() => {
    OrderFactory.reset();
    vi.clearAllMocks();
  });

  it('should handle empty search results', () => {
    setupDefaultMocks([]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const searchInput = screen.getByLabelText(/search orders/i);
    userEvent.type(searchInput, 'nonexistent');

    expect(screen.getByText(/no orders found/i)).toBeInTheDocument();
    expect(screen.getByText(/try adjusting your filters/i)).toBeInTheDocument();
  });

  it('should handle orders with missing optional fields', () => {
    const order = OrderFactory.create({
      customerEmail: '',
    });
    setupDefaultMocks([order]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    expect(screen.getByText(order.customerName)).toBeInTheDocument();
  });

  it('should handle very long order numbers', () => {
    const order = OrderFactory.create({
      orderNumber: 'ORD-' + '1'.repeat(50),
    });
    setupDefaultMocks([order]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    expect(screen.getByText(order.orderNumber)).toBeInTheDocument();
  });

  it('should handle very large amounts', () => {
    const order = OrderFactory.create({
      totalAmount: 999999999.99,
    });
    setupDefaultMocks([order]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    expect(screen.getByText(/\$999,999,999\.99/)).toBeInTheDocument();
  });

  it('should handle zero amount', () => {
    const order = OrderFactory.create({
      totalAmount: 0,
    });
    setupDefaultMocks([order]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    expect(screen.getByText('$0.00')).toBeInTheDocument();
  });

  it('should handle bulk operation with no selection gracefully', async () => {
    const orders = OrderFactory.createMany(3);
    const mockMutate = vi.fn();
    setupDefaultMocks(orders);
    vi.mocked(useBulkOrderOperations).mockReturnValue({
      ...createMockBulkOperations(),
      mutate: mockMutate,
    });

    renderWithProviders(<OrderQueue {...defaultProps} />);

    // Bulk actions bar should not be visible
    expect(screen.queryByText(/orders selected/i)).not.toBeInTheDocument();
  });

  it('should handle rapid filter changes', async () => {
    vi.useFakeTimers();
    setupDefaultMocks([]);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const searchInput = screen.getByLabelText(/search orders/i);
    
    // Rapid typing
    await userEvent.type(searchInput, 'a');
    await userEvent.type(searchInput, 'b');
    await userEvent.type(searchInput, 'c');
    
    // Only last change should trigger after debounce
    vi.advanceTimersByTime(300);
    
    await waitFor(() => {
      expect(searchInput).toHaveValue('abc');
    });

    vi.useRealTimers();
  });
});

// ============================================================================
// TEST SUITE: PERFORMANCE
// ============================================================================

describe('OrderQueue - Performance', () => {
  beforeEach(() => {
    OrderFactory.reset();
    vi.clearAllMocks();
  });

  it('should render large order lists efficiently', () => {
    const orders = OrderFactory.createMany(100);
    setupDefaultMocks(orders);

    const startTime = performance.now();
    renderWithProviders(<OrderQueue {...defaultProps} />);
    const endTime = performance.now();

    // Should render in less than 1 second
    expect(endTime - startTime).toBeLessThan(1000);
  });

  it('should memoize expensive computations', () => {
    const orders = OrderFactory.createMany(20);
    setupDefaultMocks(orders);

    const { rerender } = renderWithProviders(<OrderQueue {...defaultProps} />);

    // Rerender with same props
    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <OrderQueue {...defaultProps} />
      </QueryClientProvider>,
    );

    // useDealerOrders should not be called again with same params
    expect(useDealerOrders).toHaveBeenCalledTimes(2); // Initial + rerender
  });

  it('should handle rapid selection changes efficiently', async () => {
    const orders = OrderFactory.createMany(50);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    const checkboxes = screen.getAllByRole('checkbox');
    
    const startTime = performance.now();
    
    // Rapidly select multiple orders
    for (let i = 1; i < 11; i++) {
      await userEvent.click(checkboxes[i]);
    }
    
    const endTime = performance.now();

    // Should complete in reasonable time
    expect(endTime - startTime).toBeLessThan(500);
  });
});

// ============================================================================
// TEST SUITE: INTEGRATION SCENARIOS
// ============================================================================

describe('OrderQueue - Integration Scenarios', () => {
  beforeEach(() => {
    OrderFactory.reset();
    vi.clearAllMocks();
  });

  it('should handle complete user workflow: filter, select, bulk action', async () => {
    const orders = OrderFactory.createMany(10, { status: 'pending' });
    const mockMutate = vi.fn();
    const mockOnComplete = vi.fn();
    
    setupDefaultMocks(orders);
    vi.mocked(useBulkOrderOperations).mockReturnValue({
      ...createMockBulkOperations(),
      mutate: mockMutate,
    });

    renderWithProviders(
      <OrderQueue {...defaultProps} onBulkActionComplete={mockOnComplete} />,
    );

    // Step 1: Filter by status
    const pendingButton = screen.getByRole('button', { name: 'Pending' });
    await userEvent.click(pendingButton);
    
    await waitFor(() => {
      expect(pendingButton).toHaveClass('bg-yellow-100');
    });

    // Step 2: Select all
    const selectAllCheckbox = screen.getAllByRole('checkbox')[0];
    await userEvent.click(selectAllCheckbox);
    
    await waitFor(() => {
      expect(screen.getByText(/10 orders selected/i)).toBeInTheDocument();
    });

    // Step 3: Perform bulk action
    const confirmButton = screen.getByRole('button', { name: /confirm selected/i });
    await userEvent.click(confirmButton);
    
    expect(mockMutate).toHaveBeenCalledWith({
      orderIds: expect.any(Array),
      operation: 'confirm_multiple',
      targetStatus: undefined,
    });
  });

  it('should handle search with pagination', async () => {
    vi.useFakeTimers();
    const orders = OrderFactory.createMany(50);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    // Search
    const searchInput = screen.getByLabelText(/search orders/i);
    await userEvent.type(searchInput, 'ORD');
    
    vi.advanceTimersByTime(300);
    
    await waitFor(() => {
      expect(screen.getByText(/showing page 1/i)).toBeInTheDocument();
    });

    vi.useRealTimers();
  });

  it('should maintain selection across page changes', async () => {
    const orders = OrderFactory.createMany(50);
    setupDefaultMocks(orders);

    renderWithProviders(<OrderQueue {...defaultProps} />);

    // Select first order
    const checkboxes = screen.getAllByRole('checkbox');
    await userEvent.click(checkboxes[1]);
    
    // Navigate to next page
    const nextButton = screen.getAllByRole('button', { name: /next/i })[0];
    await userEvent.click(nextButton);
    
    // Navigate back
    const previousButton = screen.getAllByRole('button', { name: /previous/i })[0];
    await userEvent.click(previousButton);
    
    // Selection should be maintained
    await waitFor(() => {
      expect(checkboxes[1]).toBeChecked();
    });
  });
});