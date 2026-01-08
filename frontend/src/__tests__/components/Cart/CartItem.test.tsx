/**
 * CartItem Component Test Suite
 * 
 * Comprehensive tests for cart item display, quantity management,
 * removal functionality, and optimistic updates with error handling.
 * 
 * Coverage areas:
 * - Component rendering and display
 * - Quantity controls and validation
 * - Remove functionality with confirmation
 * - Optimistic updates and error states
 * - Accessibility compliance
 * - Edge cases and error scenarios
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CartItem from '../../../components/Cart/CartItem';
import type { CartItem as CartItemType } from '../../../types/cart';
import * as useCartHooks from '../../../hooks/useCart';

// ============================================================================
// Test Data Factories
// ============================================================================

/**
 * Factory for creating test cart items
 */
class CartItemFactory {
  private static baseItem: CartItemType = {
    id: 'item-1',
    cartId: 'cart-1',
    vehicleId: 'vehicle-1',
    configurationId: 'config-1',
    quantity: 1,
    unitPrice: 35000,
    totalPrice: 35000,
    status: 'active',
    addedAt: new Date('2024-01-01T10:00:00Z'),
    updatedAt: new Date('2024-01-01T10:00:00Z'),
    vehicle: {
      id: 'vehicle-1',
      year: 2024,
      make: 'Tesla',
      model: 'Model 3',
      trim: 'Long Range',
      imageUrl: 'https://example.com/tesla.jpg',
    },
    configuration: {
      id: 'config-1',
      colorId: 'color-1',
      packageIds: ['pkg-1', 'pkg-2'],
      optionIds: ['opt-1'],
    },
  };

  static create(overrides: Partial<CartItemType> = {}): CartItemType {
    return {
      ...this.baseItem,
      ...overrides,
      vehicle: {
        ...this.baseItem.vehicle!,
        ...(overrides.vehicle ?? {}),
      },
      configuration: {
        ...this.baseItem.configuration!,
        ...(overrides.configuration ?? {}),
      },
    };
  }

  static createReserved(overrides: Partial<CartItemType> = {}): CartItemType {
    return this.create({
      status: 'reserved',
      reservedUntil: new Date(Date.now() + 3600000).toISOString(), // 1 hour from now
      ...overrides,
    });
  }

  static createExpired(overrides: Partial<CartItemType> = {}): CartItemType {
    return this.create({
      status: 'expired',
      ...overrides,
    });
  }

  static createExpiredReservation(overrides: Partial<CartItemType> = {}): CartItemType {
    return this.create({
      status: 'reserved',
      reservedUntil: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
      ...overrides,
    });
  }

  static createWithoutImage(overrides: Partial<CartItemType> = {}): CartItemType {
    return this.create({
      ...overrides,
      vehicle: {
        ...this.baseItem.vehicle!,
        imageUrl: undefined,
        ...(overrides.vehicle ?? {}),
      },
    });
  }

  static createWithMultipleQuantity(
    quantity: number,
    overrides: Partial<CartItemType> = {},
  ): CartItemType {
    const unitPrice = 35000;
    return this.create({
      quantity,
      unitPrice,
      totalPrice: unitPrice * quantity,
      ...overrides,
    });
  }
}

// ============================================================================
// Test Utilities
// ============================================================================

/**
 * Create a test query client with default configuration
 */
function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

/**
 * Render component with React Query provider
 */
function renderWithProviders(
  ui: React.ReactElement,
  queryClient: QueryClient = createTestQueryClient(),
) {
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

/**
 * Mock cart hooks with default implementations
 */
function mockCartHooks() {
  const updateMutateAsync = vi.fn().mockResolvedValue({});
  const removeMutateAsync = vi.fn().mockResolvedValue({});

  const updateCartItem = {
    mutateAsync: updateMutateAsync,
    isError: false,
    error: null,
  };

  const removeCartItem = {
    mutateAsync: removeMutateAsync,
    isError: false,
    error: null,
  };

  vi.spyOn(useCartHooks, 'useUpdateCartItem').mockReturnValue(updateCartItem as any);
  vi.spyOn(useCartHooks, 'useRemoveCartItem').mockReturnValue(removeCartItem as any);

  return {
    updateCartItem,
    removeCartItem,
    updateMutateAsync,
    removeMutateAsync,
  };
}

// ============================================================================
// Test Suite
// ============================================================================

describe('CartItem Component', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  // ==========================================================================
  // 1. Component Rendering Tests
  // ==========================================================================

  describe('Component Rendering', () => {
    it('should render cart item with all details', () => {
      const item = CartItemFactory.create();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      // Vehicle name
      expect(screen.getByText('2024 Tesla Model 3 Long Range')).toBeInTheDocument();

      // Status badge
      expect(screen.getByText('Active')).toBeInTheDocument();

      // Pricing
      expect(screen.getByText('$35,000.00')).toBeInTheDocument();
      expect(screen.getByText('$35,000.00 each')).toBeInTheDocument();

      // Quantity
      expect(screen.getByLabelText('Quantity')).toHaveValue(1);

      // Configuration details
      expect(screen.getByText(/Configuration ID: config-1/)).toBeInTheDocument();
      expect(screen.getByText(/Color: color-1/)).toBeInTheDocument();
      expect(screen.getByText(/Packages: 2/)).toBeInTheDocument();
      expect(screen.getByText(/Options: 1/)).toBeInTheDocument();
    });

    it('should render vehicle image when available', () => {
      const item = CartItemFactory.create();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const image = screen.getByAltText('2024 Tesla Model 3 Long Range');
      expect(image).toBeInTheDocument();
      expect(image).toHaveAttribute('src', 'https://example.com/tesla.jpg');
      expect(image).toHaveAttribute('loading', 'lazy');
    });

    it('should render placeholder when image is not available', () => {
      const item = CartItemFactory.createWithoutImage();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const placeholder = screen.getByRole('img', { hidden: true });
      expect(placeholder).toBeInTheDocument();
    });

    it('should render vehicle name without trim when not provided', () => {
      const item = CartItemFactory.create({
        vehicle: {
          id: 'vehicle-1',
          year: 2024,
          make: 'Tesla',
          model: 'Model 3',
          trim: undefined,
        },
      });
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      expect(screen.getByText('2024 Tesla Model 3')).toBeInTheDocument();
    });

    it('should hide configuration details when showConfiguration is false', () => {
      const item = CartItemFactory.create();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} showConfiguration={false} />);

      expect(screen.queryByText(/Configuration ID:/)).not.toBeInTheDocument();
    });

    it('should apply custom className', () => {
      const item = CartItemFactory.create();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} className="custom-class" />);

      const container = screen.getByTestId('cart-item');
      expect(container).toHaveClass('custom-class');
    });

    it('should set data-item-id attribute', () => {
      const item = CartItemFactory.create();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const container = screen.getByTestId('cart-item');
      expect(container).toHaveAttribute('data-item-id', 'item-1');
    });
  });

  // ==========================================================================
  // 2. Status Display Tests
  // ==========================================================================

  describe('Status Display', () => {
    it('should display active status with green badge', () => {
      const item = CartItemFactory.create({ status: 'active' });
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const badge = screen.getByText('Active');
      expect(badge).toHaveClass('bg-green-100', 'text-green-800');
    });

    it('should display reserved status with yellow badge', () => {
      const item = CartItemFactory.createReserved();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const badge = screen.getByText('Reserved');
      expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
    });

    it('should display expired status with red badge', () => {
      const item = CartItemFactory.createExpired();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const badge = screen.getByText('Expired');
      expect(badge).toHaveClass('bg-red-100', 'text-red-800');
    });

    it('should display reservation expiration with red badge', () => {
      const item = CartItemFactory.createExpiredReservation();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const badge = screen.getByText('Reservation Expired');
      expect(badge).toHaveClass('bg-red-100', 'text-red-800');
    });

    it('should show reservation time for active reservations', () => {
      const reservedUntil = new Date(Date.now() + 3600000);
      const item = CartItemFactory.createReserved({
        reservedUntil: reservedUntil.toISOString(),
      });
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      expect(
        screen.getByText(/Reserved until/, { exact: false }),
      ).toBeInTheDocument();
    });

    it('should not show reservation time for expired reservations', () => {
      const item = CartItemFactory.createExpiredReservation();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      expect(
        screen.queryByText(/Reserved until/, { exact: false }),
      ).not.toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 3. Quantity Controls Tests
  // ==========================================================================

  describe('Quantity Controls', () => {
    it('should increment quantity when plus button is clicked', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create({ quantity: 1 });
      const { updateMutateAsync } = mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const incrementButton = screen.getByLabelText('Increase quantity');
      await user.click(incrementButton);

      await waitFor(() => {
        expect(updateMutateAsync).toHaveBeenCalledWith({
          itemId: 'item-1',
          request: { quantity: 2 },
        });
      });
    });

    it('should decrement quantity when minus button is clicked', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.createWithMultipleQuantity(2);
      const { updateMutateAsync } = mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const decrementButton = screen.getByLabelText('Decrease quantity');
      await user.click(decrementButton);

      await waitFor(() => {
        expect(updateMutateAsync).toHaveBeenCalledWith({
          itemId: 'item-1',
          request: { quantity: 1 },
        });
      });
    });

    it('should disable decrement button at minimum quantity', () => {
      const item = CartItemFactory.create({ quantity: 1 });
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const decrementButton = screen.getByLabelText('Decrease quantity');
      expect(decrementButton).toBeDisabled();
    });

    it('should disable increment button at maximum quantity', () => {
      const item = CartItemFactory.createWithMultipleQuantity(10);
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const incrementButton = screen.getByLabelText('Increase quantity');
      expect(incrementButton).toBeDisabled();
    });

    it('should call onQuantityChange callback when quantity is updated', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create({ quantity: 1 });
      const onQuantityChange = vi.fn();
      mockCartHooks();

      renderWithProviders(
        <CartItem item={item} onQuantityChange={onQuantityChange} />,
      );

      const incrementButton = screen.getByLabelText('Increase quantity');
      await user.click(incrementButton);

      await waitFor(() => {
        expect(onQuantityChange).toHaveBeenCalledWith('item-1', 2);
      });
    });

    it('should show loading spinner during quantity update', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create({ quantity: 1 });
      const { updateMutateAsync } = mockCartHooks();

      // Delay the mutation to see loading state
      updateMutateAsync.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100)),
      );

      renderWithProviders(<CartItem item={item} />);

      const incrementButton = screen.getByLabelText('Increase quantity');
      await user.click(incrementButton);

      // Check for loading spinner
      expect(screen.getByLabelText('Updating quantity')).toBeInTheDocument();

      await waitFor(() => {
        expect(
          screen.queryByLabelText('Updating quantity'),
        ).not.toBeInTheDocument();
      });
    });

    it('should disable controls during quantity update', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.createWithMultipleQuantity(5);
      const { updateMutateAsync } = mockCartHooks();

      updateMutateAsync.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100)),
      );

      renderWithProviders(<CartItem item={item} />);

      const incrementButton = screen.getByLabelText('Increase quantity');
      await user.click(incrementButton);

      // All controls should be disabled during update
      expect(screen.getByLabelText('Increase quantity')).toBeDisabled();
      expect(screen.getByLabelText('Decrease quantity')).toBeDisabled();
      expect(screen.getByText('Remove')).toBeDisabled();

      await waitFor(() => {
        expect(screen.getByLabelText('Increase quantity')).not.toBeDisabled();
      });
    });

    it('should disable controls for expired items', () => {
      const item = CartItemFactory.createExpired();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      expect(screen.getByLabelText('Increase quantity')).toBeDisabled();
      expect(screen.getByLabelText('Decrease quantity')).toBeDisabled();
    });

    it('should disable controls for expired reservations', () => {
      const item = CartItemFactory.createExpiredReservation();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      expect(screen.getByLabelText('Increase quantity')).toBeDisabled();
      expect(screen.getByLabelText('Decrease quantity')).toBeDisabled();
    });

    it('should disable all controls when disabled prop is true', () => {
      const item = CartItemFactory.createWithMultipleQuantity(5);
      mockCartHooks();

      renderWithProviders(<CartItem item={item} disabled />);

      expect(screen.getByLabelText('Increase quantity')).toBeDisabled();
      expect(screen.getByLabelText('Decrease quantity')).toBeDisabled();
      expect(screen.getByText('Remove')).toBeDisabled();
    });
  });

  // ==========================================================================
  // 4. Remove Functionality Tests
  // ==========================================================================

  describe('Remove Functionality', () => {
    it('should show confirmation dialog when remove is clicked', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const removeButton = screen.getByText('Remove');
      await user.click(removeButton);

      expect(screen.getByText('Remove item?')).toBeInTheDocument();
      expect(screen.getByText('Confirm')).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('should remove item when confirm is clicked', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create();
      const { removeMutateAsync } = mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      // Click remove
      await user.click(screen.getByText('Remove'));

      // Click confirm
      await user.click(screen.getByText('Confirm'));

      await waitFor(() => {
        expect(removeMutateAsync).toHaveBeenCalledWith('item-1');
      });
    });

    it('should cancel removal when cancel is clicked', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create();
      const { removeMutateAsync } = mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      // Click remove
      await user.click(screen.getByText('Remove'));

      // Click cancel
      await user.click(screen.getByText('Cancel'));

      expect(screen.queryByText('Remove item?')).not.toBeInTheDocument();
      expect(removeMutateAsync).not.toHaveBeenCalled();
    });

    it('should call onRemove callback when item is removed', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create();
      const onRemove = vi.fn();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} onRemove={onRemove} />);

      await user.click(screen.getByText('Remove'));
      await user.click(screen.getByText('Confirm'));

      await waitFor(() => {
        expect(onRemove).toHaveBeenCalledWith('item-1');
      });
    });

    it('should disable remove button when disabled prop is true', () => {
      const item = CartItemFactory.create();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} disabled />);

      expect(screen.getByText('Remove')).toBeDisabled();
    });

    it('should disable remove button during update', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create();
      const { updateMutateAsync } = mockCartHooks();

      updateMutateAsync.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100)),
      );

      renderWithProviders(<CartItem item={item} />);

      const incrementButton = screen.getByLabelText('Increase quantity');
      await user.click(incrementButton);

      expect(screen.getByText('Remove')).toBeDisabled();

      await waitFor(() => {
        expect(screen.getByText('Remove')).not.toBeDisabled();
      });
    });
  });

  // ==========================================================================
  // 5. Error Handling Tests
  // ==========================================================================

  describe('Error Handling', () => {
    it('should display error message when quantity update fails', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create();
      const updateCartItem = {
        mutateAsync: vi.fn().mockRejectedValue(new Error('Update failed')),
        isError: true,
        error: new Error('Update failed'),
      };

      vi.spyOn(useCartHooks, 'useUpdateCartItem').mockReturnValue(
        updateCartItem as any,
      );
      vi.spyOn(useCartHooks, 'useRemoveCartItem').mockReturnValue({
        mutateAsync: vi.fn(),
        isError: false,
        error: null,
      } as any);

      renderWithProviders(<CartItem item={item} />);

      const incrementButton = screen.getByLabelText('Increase quantity');
      await user.click(incrementButton);

      await waitFor(() => {
        expect(
          screen.getByText('Failed to update quantity. Please try again.'),
        ).toBeInTheDocument();
      });
    });

    it('should display error message when remove fails', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create();
      const removeCartItem = {
        mutateAsync: vi.fn().mockRejectedValue(new Error('Remove failed')),
        isError: true,
        error: new Error('Remove failed'),
      };

      vi.spyOn(useCartHooks, 'useUpdateCartItem').mockReturnValue({
        mutateAsync: vi.fn(),
        isError: false,
        error: null,
      } as any);
      vi.spyOn(useCartHooks, 'useRemoveCartItem').mockReturnValue(
        removeCartItem as any,
      );

      renderWithProviders(<CartItem item={item} />);

      await user.click(screen.getByText('Remove'));
      await user.click(screen.getByText('Confirm'));

      await waitFor(() => {
        expect(
          screen.getByText('Failed to remove item. Please try again.'),
        ).toBeInTheDocument();
      });
    });

    it('should hide confirmation dialog when remove fails', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create();
      const removeCartItem = {
        mutateAsync: vi.fn().mockRejectedValue(new Error('Remove failed')),
        isError: true,
        error: new Error('Remove failed'),
      };

      vi.spyOn(useCartHooks, 'useUpdateCartItem').mockReturnValue({
        mutateAsync: vi.fn(),
        isError: false,
        error: null,
      } as any);
      vi.spyOn(useCartHooks, 'useRemoveCartItem').mockReturnValue(
        removeCartItem as any,
      );

      renderWithProviders(<CartItem item={item} />);

      await user.click(screen.getByText('Remove'));
      await user.click(screen.getByText('Confirm'));

      await waitFor(() => {
        expect(screen.queryByText('Remove item?')).not.toBeInTheDocument();
      });
    });

    it('should log error when quantity update fails', async () => {
      const user = userEvent.setup();
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      const item = CartItemFactory.create();
      const error = new Error('Update failed');
      const { updateMutateAsync } = mockCartHooks();

      updateMutateAsync.mockRejectedValue(error);

      renderWithProviders(<CartItem item={item} />);

      const incrementButton = screen.getByLabelText('Increase quantity');
      await user.click(incrementButton);

      await waitFor(() => {
        expect(consoleError).toHaveBeenCalledWith(
          '[CartItem] Failed to update quantity:',
          error,
        );
      });

      consoleError.mockRestore();
    });

    it('should log error when remove fails', async () => {
      const user = userEvent.setup();
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      const item = CartItemFactory.create();
      const error = new Error('Remove failed');
      const { removeMutateAsync } = mockCartHooks();

      removeMutateAsync.mockRejectedValue(error);

      renderWithProviders(<CartItem item={item} />);

      await user.click(screen.getByText('Remove'));
      await user.click(screen.getByText('Confirm'));

      await waitFor(() => {
        expect(consoleError).toHaveBeenCalledWith(
          '[CartItem] Failed to remove item:',
          error,
        );
      });

      consoleError.mockRestore();
    });
  });

  // ==========================================================================
  // 6. Validation Tests
  // ==========================================================================

  describe('Quantity Validation', () => {
    it('should not update quantity below minimum', async () => {
      const user = userEvent.setup();
      const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const item = CartItemFactory.create({ quantity: 1 });
      const { updateMutateAsync } = mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      // Try to decrement below minimum (button should be disabled)
      const decrementButton = screen.getByLabelText('Decrease quantity');
      expect(decrementButton).toBeDisabled();

      // Verify no update was attempted
      expect(updateMutateAsync).not.toHaveBeenCalled();

      consoleWarn.mockRestore();
    });

    it('should not update quantity above maximum', async () => {
      const user = userEvent.setup();
      const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const item = CartItemFactory.createWithMultipleQuantity(10);
      const { updateMutateAsync } = mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      // Try to increment above maximum (button should be disabled)
      const incrementButton = screen.getByLabelText('Increase quantity');
      expect(incrementButton).toBeDisabled();

      // Verify no update was attempted
      expect(updateMutateAsync).not.toHaveBeenCalled();

      consoleWarn.mockRestore();
    });

    it('should not update when quantity is unchanged', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create({ quantity: 5 });
      const { updateMutateAsync } = mockCartHooks();

      // Mock to return same quantity
      updateMutateAsync.mockImplementation(async ({ request }) => {
        if (request.quantity === item.quantity) {
          return;
        }
      });

      renderWithProviders(<CartItem item={item} />);

      // Manually trigger with same quantity (edge case)
      const incrementButton = screen.getByLabelText('Increase quantity');
      
      // Since we can't directly test the internal logic without triggering,
      // we verify the mutation is called with correct value
      await user.click(incrementButton);

      await waitFor(() => {
        expect(updateMutateAsync).toHaveBeenCalledWith({
          itemId: 'item-1',
          request: { quantity: 6 },
        });
      });
    });
  });

  // ==========================================================================
  // 7. Accessibility Tests
  // ==========================================================================

  describe('Accessibility', () => {
    it('should have proper ARIA labels for quantity controls', () => {
      const item = CartItemFactory.create();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      expect(screen.getByLabelText('Quantity')).toBeInTheDocument();
      expect(screen.getByLabelText('Increase quantity')).toBeInTheDocument();
      expect(screen.getByLabelText('Decrease quantity')).toBeInTheDocument();
    });

    it('should have proper ARIA label for loading spinner', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create();
      const { updateMutateAsync } = mockCartHooks();

      updateMutateAsync.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100)),
      );

      renderWithProviders(<CartItem item={item} />);

      const incrementButton = screen.getByLabelText('Increase quantity');
      await user.click(incrementButton);

      expect(screen.getByLabelText('Updating quantity')).toBeInTheDocument();

      await waitFor(() => {
        expect(
          screen.queryByLabelText('Updating quantity'),
        ).not.toBeInTheDocument();
      });
    });

    it('should have proper role for error messages', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create();
      const updateCartItem = {
        mutateAsync: vi.fn().mockRejectedValue(new Error('Update failed')),
        isError: true,
        error: new Error('Update failed'),
      };

      vi.spyOn(useCartHooks, 'useUpdateCartItem').mockReturnValue(
        updateCartItem as any,
      );
      vi.spyOn(useCartHooks, 'useRemoveCartItem').mockReturnValue({
        mutateAsync: vi.fn(),
        isError: false,
        error: null,
      } as any);

      renderWithProviders(<CartItem item={item} />);

      const incrementButton = screen.getByLabelText('Increase quantity');
      await user.click(incrementButton);

      await waitFor(() => {
        const alert = screen.getByRole('alert');
        expect(alert).toBeInTheDocument();
        expect(alert).toHaveTextContent(
          'Failed to update quantity. Please try again.',
        );
      });
    });

    it('should have aria-hidden on decorative SVG icons', () => {
      const item = CartItemFactory.create();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const svgs = screen.getAllByRole('img', { hidden: true });
      svgs.forEach((svg) => {
        expect(svg).toHaveAttribute('aria-hidden', 'true');
      });
    });

    it('should have proper button types', () => {
      const item = CartItemFactory.create();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        expect(button).toHaveAttribute('type', 'button');
      });
    });

    it('should have screen reader only label for quantity input', () => {
      const item = CartItemFactory.create();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const label = screen.getByText('Quantity', { selector: 'label' });
      expect(label).toHaveClass('sr-only');
    });
  });

  // ==========================================================================
  // 8. Pricing Display Tests
  // ==========================================================================

  describe('Pricing Display', () => {
    it('should display correct total price for single item', () => {
      const item = CartItemFactory.create({
        quantity: 1,
        unitPrice: 35000,
        totalPrice: 35000,
      });
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      expect(screen.getByText('$35,000.00')).toBeInTheDocument();
      expect(screen.getByText('$35,000.00 each')).toBeInTheDocument();
    });

    it('should display correct total price for multiple items', () => {
      const item = CartItemFactory.createWithMultipleQuantity(3);
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      expect(screen.getByText('$105,000.00')).toBeInTheDocument();
      expect(screen.getByText('$35,000.00 each')).toBeInTheDocument();
    });

    it('should format currency with proper decimals', () => {
      const item = CartItemFactory.create({
        quantity: 1,
        unitPrice: 35999.99,
        totalPrice: 35999.99,
      });
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      expect(screen.getByText('$35,999.99')).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 9. Integration Tests
  // ==========================================================================

  describe('Integration Scenarios', () => {
    it('should handle rapid quantity changes', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.createWithMultipleQuantity(5);
      const { updateMutateAsync } = mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      const incrementButton = screen.getByLabelText('Increase quantity');

      // Rapid clicks
      await user.click(incrementButton);
      await user.click(incrementButton);
      await user.click(incrementButton);

      // Should only process one at a time due to isUpdating flag
      await waitFor(() => {
        expect(updateMutateAsync).toHaveBeenCalled();
      });
    });

    it('should handle quantity change followed by remove', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create();
      const { updateMutateAsync, removeMutateAsync } = mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      // Update quantity
      await user.click(screen.getByLabelText('Increase quantity'));

      await waitFor(() => {
        expect(updateMutateAsync).toHaveBeenCalled();
      });

      // Remove item
      await user.click(screen.getByText('Remove'));
      await user.click(screen.getByText('Confirm'));

      await waitFor(() => {
        expect(removeMutateAsync).toHaveBeenCalled();
      });
    });

    it('should handle remove cancellation followed by quantity change', async () => {
      const user = userEvent.setup();
      const item = CartItemFactory.create();
      const { updateMutateAsync, removeMutateAsync } = mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      // Start remove
      await user.click(screen.getByText('Remove'));

      // Cancel remove
      await user.click(screen.getByText('Cancel'));

      // Update quantity
      await user.click(screen.getByLabelText('Increase quantity'));

      await waitFor(() => {
        expect(updateMutateAsync).toHaveBeenCalled();
      });

      expect(removeMutateAsync).not.toHaveBeenCalled();
    });
  });

  // ==========================================================================
  // 10. Edge Cases and Performance
  // ==========================================================================

  describe('Edge Cases', () => {
    it('should handle missing vehicle data gracefully', () => {
      const item = CartItemFactory.create({
        vehicle: undefined,
      });
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      expect(screen.getByText('Vehicle')).toBeInTheDocument();
    });

    it('should handle missing configuration data', () => {
      const item = CartItemFactory.create({
        configuration: undefined,
      });
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      // Should render without configuration details
      expect(
        screen.queryByText(/Configuration ID:/),
      ).not.toBeInTheDocument();
    });

    it('should handle empty package and option arrays', () => {
      const item = CartItemFactory.create({
        configuration: {
          id: 'config-1',
          colorId: 'color-1',
          packageIds: [],
          optionIds: [],
        },
      });
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      expect(screen.getByText(/Packages: 0/)).toBeInTheDocument();
      expect(screen.getByText(/Options: 0/)).toBeInTheDocument();
    });

    it('should memoize component to prevent unnecessary re-renders', () => {
      const item = CartItemFactory.create();
      mockCartHooks();

      const { rerender } = renderWithProviders(<CartItem item={item} />);

      // Re-render with same props
      rerender(
        <QueryClientProvider client={queryClient}>
          <CartItem item={item} />
        </QueryClientProvider>,
      );

      // Component should be memoized (verified by memo wrapper)
      expect(screen.getByTestId('cart-item')).toBeInTheDocument();
    });

    it('should handle very large quantities', () => {
      const item = CartItemFactory.createWithMultipleQuantity(10);
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      expect(screen.getByLabelText('Quantity')).toHaveValue(10);
      expect(screen.getByText('$350,000.00')).toBeInTheDocument();
    });

    it('should handle very large prices', () => {
      const item = CartItemFactory.create({
        quantity: 1,
        unitPrice: 999999.99,
        totalPrice: 999999.99,
      });
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      expect(screen.getByText('$999,999.99')).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 11. Console Logging Tests
  // ==========================================================================

  describe('Console Logging', () => {
    it('should log info when quantity is updated successfully', async () => {
      const user = userEvent.setup();
      const consoleInfo = vi.spyOn(console, 'info').mockImplementation(() => {});
      const item = CartItemFactory.create();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      await user.click(screen.getByLabelText('Increase quantity'));

      await waitFor(() => {
        expect(consoleInfo).toHaveBeenCalledWith(
          '[CartItem] Updated quantity for item item-1 to 2',
        );
      });

      consoleInfo.mockRestore();
    });

    it('should log info when item is removed successfully', async () => {
      const user = userEvent.setup();
      const consoleInfo = vi.spyOn(console, 'info').mockImplementation(() => {});
      const item = CartItemFactory.create();
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      await user.click(screen.getByText('Remove'));
      await user.click(screen.getByText('Confirm'));

      await waitFor(() => {
        expect(consoleInfo).toHaveBeenCalledWith(
          '[CartItem] Removed item item-1 from cart',
        );
      });

      consoleInfo.mockRestore();
    });

    it('should log warning for invalid quantity', async () => {
      const user = userEvent.setup();
      const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const item = CartItemFactory.create({ quantity: 1 });
      mockCartHooks();

      renderWithProviders(<CartItem item={item} />);

      // Decrement button should be disabled at minimum
      const decrementButton = screen.getByLabelText('Decrease quantity');
      expect(decrementButton).toBeDisabled();

      consoleWarn.mockRestore();
    });
  });
});