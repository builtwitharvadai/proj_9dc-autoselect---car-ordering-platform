/**
 * PromoCodeInput Component Test Suite
 * 
 * Comprehensive tests for promotional code input component covering:
 * - Component rendering and UI states
 * - User interactions and form validation
 * - Promo code application and removal
 * - Error handling and edge cases
 * - Accessibility compliance
 * - Integration with cart hooks
 * 
 * @coverage-target 95%+
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PromoCodeInput from '../../../components/Cart/PromoCodeInput';
import type { PromoCodeInputProps } from '../../../components/Cart/PromoCodeInput';
import type { Cart } from '../../../types/cart';
import * as useCartHooks from '../../../hooks/useCart';

// ============================================================================
// 🏭 Test Data Factories
// ============================================================================

const createMockCart = (overrides?: Partial<Cart>): Cart => ({
  id: 'cart-123',
  userId: 'user-456',
  items: [],
  subtotal: 100.0,
  tax: 10.0,
  total: 110.0,
  promotionalCode: '',
  discount: 0,
  createdAt: new Date('2024-01-01'),
  updatedAt: new Date('2024-01-01'),
  ...overrides,
});

const createMockCartWithPromo = (code = 'SAVE20'): Cart =>
  createMockCart({
    promotionalCode: code,
    discount: 20.0,
    total: 90.0,
  });

// ============================================================================
// 🎭 Mock Setup
// ============================================================================

const createMockMutation = (overrides?: Partial<ReturnType<typeof useCartHooks.useApplyPromoCode>>) => ({
  mutate: vi.fn(),
  mutateAsync: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  error: null,
  data: undefined,
  reset: vi.fn(),
  ...overrides,
});

// ============================================================================
// 🧪 Test Utilities
// ============================================================================

const renderWithProviders = (
  ui: React.ReactElement,
  options?: { queryClient?: QueryClient }
) => {
  const queryClient = options?.queryClient ?? new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        {ui}
      </QueryClientProvider>
    ),
    queryClient,
  };
};

const setupComponent = (props?: Partial<PromoCodeInputProps>) => {
  const defaultProps: PromoCodeInputProps = {
    cart: createMockCart(),
    disabled: false,
    className: '',
    onSuccess: vi.fn(),
    onError: vi.fn(),
    ...props,
  };

  return renderWithProviders(<PromoCodeInput {...defaultProps} />);
};

// ============================================================================
// 🎯 Test Suite: Component Rendering
// ============================================================================

describe('PromoCodeInput - Component Rendering', () => {
  let mockMutation: ReturnType<typeof createMockMutation>;

  beforeEach(() => {
    mockMutation = createMockMutation();
    vi.spyOn(useCartHooks, 'useApplyPromoCode').mockReturnValue(mockMutation);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render input field and apply button', () => {
    setupComponent();

    expect(screen.getByLabelText(/promotional code/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /apply promotional code/i })).toBeInTheDocument();
  });

  it('should render with custom className', () => {
    const { container } = setupComponent({ className: 'custom-class' });

    const promoDiv = container.querySelector('.promo-code-input');
    expect(promoDiv).toHaveClass('custom-class');
  });

  it('should focus input on mount when no promo code applied', () => {
    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    expect(input).toHaveFocus();
  });

  it('should not focus input when promo code is already applied', () => {
    setupComponent({ cart: createMockCartWithPromo() });

    const input = screen.queryByLabelText(/promotional code/i);
    expect(input).not.toBeInTheDocument();
  });

  it('should render applied promo code display', () => {
    setupComponent({ cart: createMockCartWithPromo('SAVE20') });

    expect(screen.getByText(/promotional code applied/i)).toBeInTheDocument();
    expect(screen.getByText('SAVE20')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /remove promotional code/i })).toBeInTheDocument();
  });

  it('should disable input when disabled prop is true', () => {
    setupComponent({ disabled: true });

    const input = screen.getByLabelText(/promotional code/i);
    const button = screen.getByRole('button', { name: /apply promotional code/i });

    expect(input).toBeDisabled();
    expect(button).toBeDisabled();
  });

  it('should disable apply button when input is empty', () => {
    setupComponent();

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    expect(button).toBeDisabled();
  });
});

// ============================================================================
// 🎯 Test Suite: User Interactions
// ============================================================================

describe('PromoCodeInput - User Interactions', () => {
  let mockMutation: ReturnType<typeof createMockMutation>;
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup();
    mockMutation = createMockMutation();
    vi.spyOn(useCartHooks, 'useApplyPromoCode').mockReturnValue(mockMutation);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should update input value on typing', async () => {
    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'save20');

    expect(input).toHaveValue('SAVE20'); // Should be uppercase
  });

  it('should convert input to uppercase', async () => {
    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'lowercase');

    expect(input).toHaveValue('LOWERCASE');
  });

  it('should trim whitespace from input', async () => {
    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, '  SAVE20  ');

    expect(input).toHaveValue('SAVE20');
  });

  it('should enable apply button when input has value', async () => {
    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    const button = screen.getByRole('button', { name: /apply promotional code/i });

    expect(button).toBeDisabled();

    await user.type(input, 'SAVE20');

    expect(button).not.toBeDisabled();
  });

  it('should reset error state when typing after error', async () => {
    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    const button = screen.getByRole('button', { name: /apply promotional code/i });

    // Trigger error by submitting empty
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    // Type to reset error
    await user.type(input, 'S');

    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });

  it('should handle Enter key press to submit', async () => {
    const mockCart = createMockCart();
    mockMutation.mutateAsync.mockResolvedValue({ cart: mockCart });

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'SAVE20{Enter}');

    await waitFor(() => {
      expect(mockMutation.mutateAsync).toHaveBeenCalledWith({ code: 'SAVE20' });
    });
  });

  it('should prevent default form submission', async () => {
    const mockCart = createMockCart();
    mockMutation.mutateAsync.mockResolvedValue({ cart: mockCart });

    const { container } = setupComponent();

    const form = container.querySelector('form');
    const submitHandler = vi.fn((e) => e.preventDefault());
    
    if (form) {
      form.addEventListener('submit', submitHandler);
    }

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'SAVE20');
    
    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    expect(submitHandler).toHaveBeenCalled();
  });
});

// ============================================================================
// 🎯 Test Suite: Promo Code Application
// ============================================================================

describe('PromoCodeInput - Promo Code Application', () => {
  let mockMutation: ReturnType<typeof createMockMutation>;
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup();
    mockMutation = createMockMutation();
    vi.spyOn(useCartHooks, 'useApplyPromoCode').mockReturnValue(mockMutation);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should show validation error when submitting empty code', async () => {
    setupComponent();

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/please enter a promotional code/i);
    });
  });

  it('should show error when applying already applied code', async () => {
    setupComponent({ cart: createMockCartWithPromo('SAVE20') });

    // Switch to input view by removing code first
    const removeButton = screen.getByRole('button', { name: /remove promotional code/i });
    mockMutation.mutateAsync.mockResolvedValue({ cart: createMockCart() });
    await user.click(removeButton);

    await waitFor(() => {
      expect(screen.getByLabelText(/promotional code/i)).toBeInTheDocument();
    });

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'SAVE20');

    const applyButton = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(applyButton);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/this code is already applied/i);
    });
  });

  it('should successfully apply promo code', async () => {
    const mockCart = createMockCartWithPromo('SAVE20');
    mockMutation.mutateAsync.mockResolvedValue({ cart: mockCart });

    const onSuccess = vi.fn();
    setupComponent({ onSuccess });

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'SAVE20');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(mockMutation.mutateAsync).toHaveBeenCalledWith({ code: 'SAVE20' });
    });

    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent(/promotional code applied successfully/i);
    });

    expect(onSuccess).toHaveBeenCalledWith(mockCart);
  });

  it('should show loading state during application', async () => {
    const mockCart = createMockCartWithPromo('SAVE20');
    mockMutation.mutateAsync.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ cart: mockCart }), 100))
    );

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'SAVE20');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    expect(screen.getByText(/applying/i)).toBeInTheDocument();
    expect(button).toBeDisabled();

    await waitFor(() => {
      expect(screen.getByRole('status')).toBeInTheDocument();
    });
  });

  it('should clear input after successful application', async () => {
    const mockCart = createMockCartWithPromo('SAVE20');
    mockMutation.mutateAsync.mockResolvedValue({ cart: mockCart });

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'SAVE20');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    expect(input).toHaveValue('');
  });

  it('should reset success state after 3 seconds', async () => {
    vi.useFakeTimers();

    const mockCart = createMockCartWithPromo('SAVE20');
    mockMutation.mutateAsync.mockResolvedValue({ cart: mockCart });

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'SAVE20');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    vi.advanceTimersByTime(3000);

    await waitFor(() => {
      expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });

    vi.useRealTimers();
  });
});

// ============================================================================
// 🎯 Test Suite: Error Handling
// ============================================================================

describe('PromoCodeInput - Error Handling', () => {
  let mockMutation: ReturnType<typeof createMockMutation>;
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup();
    mockMutation = createMockMutation();
    vi.spyOn(useCartHooks, 'useApplyPromoCode').mockReturnValue(mockMutation);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should handle invalid promotional code error', async () => {
    const error = {
      message: 'Cart operation failed',
      cartError: {
        type: 'INVALID_PROMOTIONAL_CODE' as const,
        message: 'Invalid code',
      },
    };
    mockMutation.mutateAsync.mockRejectedValue(error);

    const onError = vi.fn();
    setupComponent({ onError });

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'INVALID');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/invalid promotional code/i);
    });

    expect(onError).toHaveBeenCalled();
  });

  it('should handle expired promotional code error', async () => {
    const error = {
      message: 'Cart operation failed',
      cartError: {
        type: 'PROMOTIONAL_CODE_EXPIRED' as const,
        message: 'Code expired',
      },
    };
    mockMutation.mutateAsync.mockRejectedValue(error);

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'EXPIRED');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/this promotional code has expired/i);
    });
  });

  it('should handle usage limit error', async () => {
    const error = {
      message: 'Cart operation failed',
      cartError: {
        type: 'PROMOTIONAL_CODE_USAGE_LIMIT' as const,
        message: 'Usage limit reached',
      },
    };
    mockMutation.mutateAsync.mockRejectedValue(error);

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'MAXED');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/usage limit/i);
    });
  });

  it('should handle minimum purchase not met error', async () => {
    const error = {
      message: 'Cart operation failed',
      cartError: {
        type: 'MIN_PURCHASE_NOT_MET' as const,
        message: 'Minimum purchase of $50 required',
      },
    };
    mockMutation.mutateAsync.mockRejectedValue(error);

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'MIN50');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/minimum purchase of \$50 required/i);
    });
  });

  it('should handle generic cart API error', async () => {
    const error = {
      message: 'Network error occurred',
      cartError: null,
    };
    mockMutation.mutateAsync.mockRejectedValue(error);

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'ERROR');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/network error occurred/i);
    });
  });

  it('should handle unknown error type', async () => {
    const error = new Error('Unknown error');
    mockMutation.mutateAsync.mockRejectedValue(error);

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'ERROR');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/unknown error/i);
    });
  });

  it('should handle non-Error object rejection', async () => {
    mockMutation.mutateAsync.mockRejectedValue('String error');

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'ERROR');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/failed to apply promotional code/i);
    });
  });
});

// ============================================================================
// 🎯 Test Suite: Promo Code Removal
// ============================================================================

describe('PromoCodeInput - Promo Code Removal', () => {
  let mockMutation: ReturnType<typeof createMockMutation>;
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup();
    mockMutation = createMockMutation();
    vi.spyOn(useCartHooks, 'useApplyPromoCode').mockReturnValue(mockMutation);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should successfully remove promo code', async () => {
    const mockCart = createMockCart();
    mockMutation.mutateAsync.mockResolvedValue({ cart: mockCart });

    const onSuccess = vi.fn();
    setupComponent({ cart: createMockCartWithPromo('SAVE20'), onSuccess });

    const button = screen.getByRole('button', { name: /remove promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(mockMutation.mutateAsync).toHaveBeenCalledWith({ code: '' });
    });

    expect(onSuccess).toHaveBeenCalledWith(mockCart);
  });

  it('should show loading state during removal', async () => {
    const mockCart = createMockCart();
    mockMutation.mutateAsync.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ cart: mockCart }), 100))
    );

    setupComponent({ cart: createMockCartWithPromo('SAVE20') });

    const button = screen.getByRole('button', { name: /remove promotional code/i });
    await user.click(button);

    expect(screen.getByText(/removing/i)).toBeInTheDocument();
    expect(button).toBeDisabled();

    await waitFor(() => {
      expect(screen.getByLabelText(/promotional code/i)).toBeInTheDocument();
    });
  });

  it('should handle removal error', async () => {
    const error = new Error('Failed to remove code');
    mockMutation.mutateAsync.mockRejectedValue(error);

    const onError = vi.fn();
    setupComponent({ cart: createMockCartWithPromo('SAVE20'), onError });

    const button = screen.getByRole('button', { name: /remove promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/failed to remove code/i);
    });

    expect(onError).toHaveBeenCalled();
  });

  it('should disable remove button when disabled prop is true', () => {
    setupComponent({ cart: createMockCartWithPromo('SAVE20'), disabled: true });

    const button = screen.getByRole('button', { name: /remove promotional code/i });
    expect(button).toBeDisabled();
  });

  it('should switch to input view after successful removal', async () => {
    const mockCart = createMockCart();
    mockMutation.mutateAsync.mockResolvedValue({ cart: mockCart });

    setupComponent({ cart: createMockCartWithPromo('SAVE20') });

    expect(screen.queryByLabelText(/promotional code/i)).not.toBeInTheDocument();

    const button = screen.getByRole('button', { name: /remove promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByLabelText(/promotional code/i)).toBeInTheDocument();
    });
  });
});

// ============================================================================
// 🎯 Test Suite: Accessibility
// ============================================================================

describe('PromoCodeInput - Accessibility', () => {
  let mockMutation: ReturnType<typeof createMockMutation>;

  beforeEach(() => {
    mockMutation = createMockMutation();
    vi.spyOn(useCartHooks, 'useApplyPromoCode').mockReturnValue(mockMutation);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should have proper ARIA labels', () => {
    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    expect(input).toHaveAttribute('id', 'promo-code');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    expect(button).toHaveAttribute('aria-label', 'Apply promotional code');
  });

  it('should mark input as invalid on error', async () => {
    const user = userEvent.setup();
    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    const button = screen.getByRole('button', { name: /apply promotional code/i });

    await user.click(button);

    await waitFor(() => {
      expect(input).toHaveAttribute('aria-invalid', 'true');
    });
  });

  it('should associate error message with input', async () => {
    const user = userEvent.setup();
    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    const button = screen.getByRole('button', { name: /apply promotional code/i });

    await user.click(button);

    await waitFor(() => {
      expect(input).toHaveAttribute('aria-describedby', 'promo-code-error');
      expect(screen.getByRole('alert')).toHaveAttribute('id', 'promo-code-error');
    });
  });

  it('should use role="alert" for error messages', async () => {
    const user = userEvent.setup();
    setupComponent();

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      const alert = screen.getByRole('alert');
      expect(alert).toBeInTheDocument();
    });
  });

  it('should use role="status" for success messages', async () => {
    const user = userEvent.setup();
    const mockCart = createMockCartWithPromo('SAVE20');
    mockMutation.mutateAsync.mockResolvedValue({ cart: mockCart });

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'SAVE20');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      const status = screen.getByRole('status');
      expect(status).toBeInTheDocument();
    });
  });

  it('should hide decorative icons from screen readers', () => {
    setupComponent();

    const svgs = document.querySelectorAll('svg[aria-hidden="true"]');
    expect(svgs.length).toBeGreaterThan(0);
  });

  it('should have proper label for remove button', () => {
    setupComponent({ cart: createMockCartWithPromo('SAVE20') });

    const button = screen.getByRole('button', { name: /remove promotional code/i });
    expect(button).toHaveAttribute('aria-label', 'Remove promotional code');
  });

  it('should use sr-only class for visual label', () => {
    const { container } = setupComponent();

    const label = container.querySelector('label[for="promo-code"]');
    expect(label).toHaveClass('sr-only');
  });
});

// ============================================================================
// 🎯 Test Suite: Edge Cases
// ============================================================================

describe('PromoCodeInput - Edge Cases', () => {
  let mockMutation: ReturnType<typeof createMockMutation>;
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup();
    mockMutation = createMockMutation();
    vi.spyOn(useCartHooks, 'useApplyPromoCode').mockReturnValue(mockMutation);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should handle undefined cart', () => {
    setupComponent({ cart: undefined });

    expect(screen.getByLabelText(/promotional code/i)).toBeInTheDocument();
  });

  it('should handle cart with empty promotional code', () => {
    setupComponent({ cart: createMockCart({ promotionalCode: '' }) });

    expect(screen.getByLabelText(/promotional code/i)).toBeInTheDocument();
    expect(screen.queryByText(/promotional code applied/i)).not.toBeInTheDocument();
  });

  it('should handle very long promo codes', async () => {
    setupComponent();

    const longCode = 'A'.repeat(100);
    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, longCode);

    expect(input).toHaveValue(longCode);
  });

  it('should handle special characters in promo code', async () => {
    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'SAVE-20%');

    expect(input).toHaveValue('SAVE-20%');
  });

  it('should handle rapid successive clicks', async () => {
    const mockCart = createMockCartWithPromo('SAVE20');
    mockMutation.mutateAsync.mockResolvedValue({ cart: mockCart });

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'SAVE20');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    
    // Click multiple times rapidly
    await user.click(button);
    await user.click(button);
    await user.click(button);

    // Should only call once due to disabled state
    await waitFor(() => {
      expect(mockMutation.mutateAsync).toHaveBeenCalledTimes(1);
    });
  });

  it('should handle mutation without onSuccess callback', async () => {
    const mockCart = createMockCartWithPromo('SAVE20');
    mockMutation.mutateAsync.mockResolvedValue({ cart: mockCart });

    setupComponent({ onSuccess: undefined });

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'SAVE20');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('status')).toBeInTheDocument();
    });
  });

  it('should handle mutation without onError callback', async () => {
    const error = new Error('Test error');
    mockMutation.mutateAsync.mockRejectedValue(error);

    setupComponent({ onError: undefined });

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'ERROR');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });

  it('should handle cart error without message', async () => {
    const error = {
      message: 'Cart operation failed',
      cartError: {
        type: 'INVALID_PROMOTIONAL_CODE' as const,
        message: undefined,
      },
    };
    mockMutation.mutateAsync.mockRejectedValue(error);

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'ERROR');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/invalid promotional code/i);
    });
  });

  it('should handle unknown cart error type', async () => {
    const error = {
      message: 'Cart operation failed',
      cartError: {
        type: 'UNKNOWN_ERROR' as any,
        message: 'Custom error message',
      },
    };
    mockMutation.mutateAsync.mockRejectedValue(error);

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'ERROR');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/custom error message/i);
    });
  });
});

// ============================================================================
// 🎯 Test Suite: Integration with Cart Hook
// ============================================================================

describe('PromoCodeInput - Cart Hook Integration', () => {
  let mockMutation: ReturnType<typeof createMockMutation>;
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup();
    mockMutation = createMockMutation();
    vi.spyOn(useCartHooks, 'useApplyPromoCode').mockReturnValue(mockMutation);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should call useApplyPromoCode hook', () => {
    setupComponent();

    expect(useCartHooks.useApplyPromoCode).toHaveBeenCalled();
  });

  it('should pass correct code to mutation', async () => {
    const mockCart = createMockCartWithPromo('SAVE20');
    mockMutation.mutateAsync.mockResolvedValue({ cart: mockCart });

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'SAVE20');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(mockMutation.mutateAsync).toHaveBeenCalledWith({ code: 'SAVE20' });
    });
  });

  it('should pass empty string to remove code', async () => {
    const mockCart = createMockCart();
    mockMutation.mutateAsync.mockResolvedValue({ cart: mockCart });

    setupComponent({ cart: createMockCartWithPromo('SAVE20') });

    const button = screen.getByRole('button', { name: /remove promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(mockMutation.mutateAsync).toHaveBeenCalledWith({ code: '' });
    });
  });

  it('should handle mutation response correctly', async () => {
    const mockCart = createMockCartWithPromo('SAVE20');
    const response = { cart: mockCart };
    mockMutation.mutateAsync.mockResolvedValue(response);

    const onSuccess = vi.fn();
    setupComponent({ onSuccess });

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'SAVE20');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith(mockCart);
    });
  });
});

// ============================================================================
// 🎯 Test Suite: Visual States
// ============================================================================

describe('PromoCodeInput - Visual States', () => {
  let mockMutation: ReturnType<typeof createMockMutation>;

  beforeEach(() => {
    mockMutation = createMockMutation();
    vi.spyOn(useCartHooks, 'useApplyPromoCode').mockReturnValue(mockMutation);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should apply error styling to input on error', async () => {
    const user = userEvent.setup();
    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    const button = screen.getByRole('button', { name: /apply promotional code/i });

    await user.click(button);

    await waitFor(() => {
      expect(input).toHaveClass('border-red-500');
    });
  });

  it('should apply success styling to input on success', async () => {
    const user = userEvent.setup();
    const mockCart = createMockCartWithPromo('SAVE20');
    mockMutation.mutateAsync.mockResolvedValue({ cart: mockCart });

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'SAVE20');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    await waitFor(() => {
      expect(input).toHaveClass('border-green-500');
    });
  });

  it('should apply disabled styling when disabled', () => {
    setupComponent({ disabled: true });

    const input = screen.getByLabelText(/promotional code/i);
    expect(input).toHaveClass('bg-gray-100', 'cursor-not-allowed');
  });

  it('should show spinner during validation', async () => {
    const user = userEvent.setup();
    const mockCart = createMockCartWithPromo('SAVE20');
    mockMutation.mutateAsync.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ cart: mockCart }), 100))
    );

    setupComponent();

    const input = screen.getByLabelText(/promotional code/i);
    await user.type(input, 'SAVE20');

    const button = screen.getByRole('button', { name: /apply promotional code/i });
    await user.click(button);

    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole('status')).toBeInTheDocument();
    });
  });

  it('should display applied code with green background', () => {
    setupComponent({ cart: createMockCartWithPromo('SAVE20') });

    const appliedDiv = screen.getByText(/promotional code applied/i).closest('div');
    expect(appliedDiv).toHaveClass('bg-green-50', 'border-green-200');
  });
});