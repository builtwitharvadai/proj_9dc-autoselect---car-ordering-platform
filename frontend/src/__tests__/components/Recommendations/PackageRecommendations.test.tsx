/**
 * PackageRecommendations Component Test Suite
 * 
 * Comprehensive tests covering:
 * - Component rendering and display logic
 * - User interactions and event handling
 * - Analytics tracking integration
 * - State management and selection logic
 * - Error handling and edge cases
 * - Accessibility compliance
 * - Performance optimization
 * 
 * @coverage-target 85%+
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PackageRecommendations from '../../../components/Recommendations/PackageRecommendations';
import type { PackageRecommendation, PopularConfiguration } from '../../../types/recommendations';

// ============================================================================
// 🏭 Test Data Factories
// ============================================================================

const createMockRecommendation = (overrides?: Partial<PackageRecommendation>): PackageRecommendation => ({
  id: `rec-${Math.random().toString(36).substring(7)}`,
  packageId: `pkg-${Math.random().toString(36).substring(7)}`,
  name: 'Premium Package',
  description: 'Includes advanced safety features and premium audio',
  basePrice: 5000,
  discountedPrice: 4500,
  savingsAmount: 500,
  savingsPercentage: 10,
  confidence: 'high',
  reasons: ['frequently_bought_together', 'high_value'],
  includedOptions: ['opt-1', 'opt-2', 'opt-3'],
  compatibleWithSelection: true,
  popularityScore: 85,
  imageUrl: 'https://example.com/package.jpg',
  ...overrides,
});

const createMockPopularConfiguration = (
  overrides?: Partial<PopularConfiguration>,
): PopularConfiguration => ({
  id: `config-${Math.random().toString(36).substring(7)}`,
  vehicleId: 'vehicle-1',
  vehicleName: 'Model X',
  trimName: 'Premium',
  packageIds: ['pkg-1', 'pkg-2'],
  optionIds: ['opt-1', 'opt-2'],
  totalPrice: 45000,
  popularityCount: 150,
  averageRating: 4.5,
  ...overrides,
});

// ============================================================================
// 🎭 Mock Setup
// ============================================================================

const mockUsePackageRecommendations = vi.fn();
const mockUseTrackRecommendation = vi.fn();
const mockUseAcceptRecommendation = vi.fn();

vi.mock('../../../hooks/useRecommendations', () => ({
  usePackageRecommendations: () => mockUsePackageRecommendations(),
  useTrackRecommendation: () => mockUseTrackRecommendation(),
  useAcceptRecommendation: () => mockUseAcceptRecommendation(),
}));

// ============================================================================
// 🧪 Test Utilities
// ============================================================================

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const renderWithProviders = (
  ui: React.ReactElement,
  { queryClient = createQueryClient() } = {},
) => {
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  return {
    ...render(ui, { wrapper: Wrapper }),
    queryClient,
  };
};

const defaultProps = {
  vehicleId: 'vehicle-123',
  trimId: 'trim-456',
  selectedPackageIds: [],
  selectedOptionIds: [],
  maxRecommendations: 5,
};

// ============================================================================
// 🎯 Test Suite
// ============================================================================

describe('PackageRecommendations Component', () => {
  let trackMutate: ReturnType<typeof vi.fn>;
  let acceptMutate: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    trackMutate = vi.fn();
    acceptMutate = vi.fn();

    mockUseTrackRecommendation.mockReturnValue({
      mutate: trackMutate,
      isPending: false,
    });

    mockUseAcceptRecommendation.mockReturnValue({
      mutate: acceptMutate,
      isPending: false,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ==========================================================================
  // 📊 Loading States
  // ==========================================================================

  describe('Loading States', () => {
    it('should display loading skeleton while fetching recommendations', () => {
      mockUsePackageRecommendations.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument();
      expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
    });

    it('should render correct number of skeleton cards', () => {
      mockUsePackageRecommendations.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      });

      const { container } = renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const skeletonCards = container.querySelectorAll('.animate-pulse > .space-y-3 > div');
      expect(skeletonCards).toHaveLength(3);
    });
  });

  // ==========================================================================
  // ❌ Error Handling
  // ==========================================================================

  describe('Error Handling', () => {
    it('should display error message when recommendations fail to load', () => {
      const errorMessage = 'Failed to fetch recommendations';
      mockUsePackageRecommendations.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error(errorMessage),
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByText('Failed to load recommendations')).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    it('should provide retry functionality on error', async () => {
      const refetch = vi.fn();
      mockUsePackageRecommendations.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Network error'),
        refetch,
      });

      const user = userEvent.setup();
      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const retryButton = screen.getByRole('button', { name: /try again/i });
      await user.click(retryButton);

      expect(refetch).toHaveBeenCalledTimes(1);
    });

    it('should handle non-Error error objects gracefully', () => {
      mockUsePackageRecommendations.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { message: 'Custom error' },
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByText('An unexpected error occurred')).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 🎨 Empty States
  // ==========================================================================

  describe('Empty States', () => {
    it('should display empty state when no recommendations available', () => {
      mockUsePackageRecommendations.mockReturnValue({
        data: {
          recommendations: [],
          metadata: { processingTimeMs: 50 },
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByText('No recommendations available')).toBeInTheDocument();
      expect(
        screen.getByText(/We couldn't find any package recommendations/i),
      ).toBeInTheDocument();
    });

    it('should filter out incompatible recommendations', () => {
      const recommendations = [
        createMockRecommendation({ compatibleWithSelection: false }),
        createMockRecommendation({ compatibleWithSelection: false }),
      ];

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations, metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByText('No recommendations available')).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 🎯 Recommendation Display
  // ==========================================================================

  describe('Recommendation Display', () => {
    it('should render recommendation cards with correct information', () => {
      const recommendation = createMockRecommendation({
        name: 'Sport Package',
        description: 'Enhanced performance features',
        discountedPrice: 3500,
        savingsAmount: 500,
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: {
          recommendations: [recommendation],
          metadata: { processingTimeMs: 50 },
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByText('Sport Package')).toBeInTheDocument();
      expect(screen.getByText('Enhanced performance features')).toBeInTheDocument();
      expect(screen.getByText('$3,500')).toBeInTheDocument();
      expect(screen.getByText(/You save \$500/i)).toBeInTheDocument();
    });

    it('should display confidence badges correctly', () => {
      const recommendations = [
        createMockRecommendation({ confidence: 'high' }),
        createMockRecommendation({ confidence: 'medium' }),
        createMockRecommendation({ confidence: 'low' }),
      ];

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations, metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByText('Highly Recommended')).toBeInTheDocument();
      expect(screen.getByText('Recommended')).toBeInTheDocument();
      expect(screen.getByText('Consider')).toBeInTheDocument();
    });

    it('should show savings percentage badge for significant savings', () => {
      const recommendation = createMockRecommendation({
        savingsAmount: 1000,
        savingsPercentage: 20,
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByText('Save 20%')).toBeInTheDocument();
    });

    it('should display recommendation reasons', () => {
      const recommendation = createMockRecommendation({
        reasons: ['frequently_bought_together', 'high_value'],
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByText('Why we recommend this:')).toBeInTheDocument();
      expect(screen.getByText('Frequently Bought Together')).toBeInTheDocument();
      expect(screen.getByText('High Value')).toBeInTheDocument();
    });

    it('should show included options count', () => {
      const recommendation = createMockRecommendation({
        includedOptions: ['opt-1', 'opt-2', 'opt-3'],
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByText('Includes 3 options')).toBeInTheDocument();
    });

    it('should display popularity indicator for high-confidence popular packages', () => {
      const recommendation = createMockRecommendation({
        confidence: 'high',
        popularityScore: 85,
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByText('Popular choice')).toBeInTheDocument();
    });

    it('should render package images when available', () => {
      const recommendation = createMockRecommendation({
        name: 'Luxury Package',
        imageUrl: 'https://example.com/luxury.jpg',
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const image = screen.getByAltText('Luxury Package');
      expect(image).toBeInTheDocument();
      expect(image).toHaveAttribute('src', 'https://example.com/luxury.jpg');
      expect(image).toHaveAttribute('loading', 'lazy');
    });

    it('should respect maxRecommendations prop', () => {
      const recommendations = Array.from({ length: 10 }, (_, i) =>
        createMockRecommendation({ name: `Package ${i + 1}` }),
      );

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations, metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} maxRecommendations={3} />);

      expect(screen.getByText('Package 1')).toBeInTheDocument();
      expect(screen.getByText('Package 2')).toBeInTheDocument();
      expect(screen.getByText('Package 3')).toBeInTheDocument();
      expect(screen.queryByText('Package 4')).not.toBeInTheDocument();
    });

    it('should display total potential savings in header', () => {
      const recommendations = [
        createMockRecommendation({ savingsAmount: 500 }),
        createMockRecommendation({ savingsAmount: 300 }),
        createMockRecommendation({ savingsAmount: 200 }),
      ];

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations, metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByText(/Save up to \$1,000/i)).toBeInTheDocument();
    });

    it('should display processing time metadata', () => {
      const recommendation = createMockRecommendation();

      mockUsePackageRecommendations.mockReturnValue({
        data: {
          recommendations: [recommendation],
          metadata: { processingTimeMs: 125 },
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByText('Generated in 125ms')).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 🖱️ User Interactions
  // ==========================================================================

  describe('User Interactions', () => {
    it('should handle package selection', async () => {
      const onPackageSelect = vi.fn();
      const recommendation = createMockRecommendation({ packageId: 'pkg-123' });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const user = userEvent.setup();
      renderWithProviders(
        <PackageRecommendations {...defaultProps} onPackageSelect={onPackageSelect} />,
      );

      const addButton = screen.getByRole('button', { name: /add package/i });
      await user.click(addButton);

      expect(onPackageSelect).toHaveBeenCalledWith('pkg-123');
      expect(screen.getByRole('button', { name: /selected/i })).toBeInTheDocument();
    });

    it('should handle package deselection', async () => {
      const onPackageDeselect = vi.fn();
      const recommendation = createMockRecommendation({ packageId: 'pkg-123' });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const user = userEvent.setup();
      renderWithProviders(
        <PackageRecommendations
          {...defaultProps}
          selectedPackageIds={['pkg-123']}
          onPackageDeselect={onPackageDeselect}
        />,
      );

      const selectedButton = screen.getByRole('button', { name: /selected/i });
      await user.click(selectedButton);

      expect(onPackageDeselect).toHaveBeenCalledWith('pkg-123');
      expect(screen.getByRole('button', { name: /add package/i })).toBeInTheDocument();
    });

    it('should track recommendation click events', async () => {
      const recommendation = createMockRecommendation({
        id: 'rec-123',
        packageId: 'pkg-123',
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const user = userEvent.setup();
      renderWithProviders(
        <PackageRecommendations {...defaultProps} userId="user-1" sessionId="session-1" />,
      );

      const card = screen.getByRole('button', { pressed: false });
      await user.click(card);

      expect(trackMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          recommendationId: 'rec-123',
          eventType: 'recommendation_clicked',
          userId: 'user-1',
          sessionId: 'session-1',
          vehicleId: 'vehicle-123',
          packageId: 'pkg-123',
          position: 0,
        }),
      );
    });

    it('should track recommendation acceptance', async () => {
      const recommendation = createMockRecommendation({
        id: 'rec-123',
        packageId: 'pkg-123',
        discountedPrice: 4500,
        savingsAmount: 500,
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const user = userEvent.setup();
      renderWithProviders(
        <PackageRecommendations {...defaultProps} userId="user-1" sessionId="session-1" />,
      );

      const addButton = screen.getByRole('button', { name: /add package/i });
      await user.click(addButton);

      expect(trackMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          eventType: 'recommendation_accepted',
        }),
      );

      expect(acceptMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          recommendationId: 'rec-123',
          packageId: 'pkg-123',
          userId: 'user-1',
          sessionId: 'session-1',
          vehicleId: 'vehicle-123',
          finalPrice: 4500,
          savingsRealized: 500,
        }),
      );
    });

    it('should track recommendation dismissal', async () => {
      const recommendation = createMockRecommendation({ id: 'rec-123' });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const user = userEvent.setup();
      renderWithProviders(
        <PackageRecommendations {...defaultProps} selectedPackageIds={['pkg-123']} />,
      );

      const selectedButton = screen.getByRole('button', { name: /selected/i });
      await user.click(selectedButton);

      expect(trackMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          eventType: 'recommendation_dismissed',
        }),
      );
    });

    it('should handle keyboard navigation', async () => {
      const recommendation = createMockRecommendation();

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const user = userEvent.setup();
      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const card = screen.getByRole('button', { pressed: false });
      card.focus();
      await user.keyboard('{Enter}');

      expect(trackMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          eventType: 'recommendation_clicked',
        }),
      );
    });

    it('should prevent event propagation on button click', async () => {
      const recommendation = createMockRecommendation();
      const cardClickHandler = vi.fn();

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const user = userEvent.setup();
      const { container } = renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const card = container.querySelector('[role="button"][tabindex="0"]');
      card?.addEventListener('click', cardClickHandler);

      const addButton = screen.getByRole('button', { name: /add package/i });
      await user.click(addButton);

      expect(cardClickHandler).not.toHaveBeenCalled();
    });

    it('should disable button during acceptance mutation', () => {
      const recommendation = createMockRecommendation();

      mockUseAcceptRecommendation.mockReturnValue({
        mutate: acceptMutate,
        isPending: true,
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add package/i });
      expect(addButton).toBeDisabled();
    });
  });

  // ==========================================================================
  // 🎪 Popular Configurations
  // ==========================================================================

  describe('Popular Configurations', () => {
    it('should display popular configurations when enabled', () => {
      const recommendation = createMockRecommendation();
      const popularConfig = createMockPopularConfiguration({
        vehicleName: 'Model S',
        trimName: 'Performance',
        popularityCount: 200,
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: {
          recommendations: [recommendation],
          popularConfigurations: [popularConfig],
          metadata: { processingTimeMs: 50 },
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(
        <PackageRecommendations {...defaultProps} showPopularConfigurations={true} />,
      );

      expect(
        screen.getByText('Popular Configurations for Similar Vehicles'),
      ).toBeInTheDocument();
      expect(screen.getByText('Model S')).toBeInTheDocument();
      expect(screen.getByText('Performance')).toBeInTheDocument();
      expect(screen.getByText('200 buyers')).toBeInTheDocument();
    });

    it('should hide popular configurations when disabled', () => {
      const recommendation = createMockRecommendation();
      const popularConfig = createMockPopularConfiguration();

      mockUsePackageRecommendations.mockReturnValue({
        data: {
          recommendations: [recommendation],
          popularConfigurations: [popularConfig],
          metadata: { processingTimeMs: 50 },
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(
        <PackageRecommendations {...defaultProps} showPopularConfigurations={false} />,
      );

      expect(
        screen.queryByText('Popular Configurations for Similar Vehicles'),
      ).not.toBeInTheDocument();
    });

    it('should display rating for popular configurations', () => {
      const recommendation = createMockRecommendation();
      const popularConfig = createMockPopularConfiguration({
        averageRating: 4.7,
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: {
          recommendations: [recommendation],
          popularConfigurations: [popularConfig],
          metadata: { processingTimeMs: 50 },
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(
        <PackageRecommendations {...defaultProps} showPopularConfigurations={true} />,
      );

      expect(screen.getByText('4.7 rating')).toBeInTheDocument();
    });

    it('should limit popular configurations to 3', () => {
      const recommendation = createMockRecommendation();
      const popularConfigs = Array.from({ length: 5 }, (_, i) =>
        createMockPopularConfiguration({ vehicleName: `Model ${i + 1}` }),
      );

      mockUsePackageRecommendations.mockReturnValue({
        data: {
          recommendations: [recommendation],
          popularConfigurations: popularConfigs,
          metadata: { processingTimeMs: 50 },
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(
        <PackageRecommendations {...defaultProps} showPopularConfigurations={true} />,
      );

      expect(screen.getByText('Model 1')).toBeInTheDocument();
      expect(screen.getByText('Model 2')).toBeInTheDocument();
      expect(screen.getByText('Model 3')).toBeInTheDocument();
      expect(screen.queryByText('Model 4')).not.toBeInTheDocument();
    });
  });

  // ==========================================================================
  // ♿ Accessibility
  // ==========================================================================

  describe('Accessibility', () => {
    it('should have proper ARIA attributes on recommendation cards', () => {
      const recommendation = createMockRecommendation();

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const card = screen.getByRole('button', { pressed: false });
      expect(card).toHaveAttribute('tabIndex', '0');
    });

    it('should update aria-pressed when recommendation is selected', async () => {
      const recommendation = createMockRecommendation();

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const user = userEvent.setup();
      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const card = screen.getByRole('button', { pressed: false });
      const addButton = within(card).getByRole('button', { name: /add package/i });

      await user.click(addButton);

      await waitFor(() => {
        expect(screen.getByRole('button', { pressed: true })).toBeInTheDocument();
      });
    });

    it('should have descriptive alt text for images', () => {
      const recommendation = createMockRecommendation({
        name: 'Technology Package',
        imageUrl: 'https://example.com/tech.jpg',
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const image = screen.getByAltText('Technology Package');
      expect(image).toBeInTheDocument();
    });

    it('should hide decorative SVG icons from screen readers', () => {
      const recommendation = createMockRecommendation();

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const { container } = renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const svgs = container.querySelectorAll('svg[aria-hidden="true"]');
      expect(svgs.length).toBeGreaterThan(0);
    });

    it('should support keyboard navigation with Space key', async () => {
      const recommendation = createMockRecommendation();

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const user = userEvent.setup();
      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const card = screen.getByRole('button', { pressed: false });
      card.focus();
      await user.keyboard(' ');

      expect(trackMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          eventType: 'recommendation_clicked',
        }),
      );
    });
  });

  // ==========================================================================
  // 🎨 Visual States
  // ==========================================================================

  describe('Visual States', () => {
    it('should apply selected styling to selected recommendations', async () => {
      const recommendation = createMockRecommendation();

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const user = userEvent.setup();
      const { container } = renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add package/i });
      await user.click(addButton);

      await waitFor(() => {
        const selectedCard = container.querySelector('.border-blue-500');
        expect(selectedCard).toBeInTheDocument();
      });
    });

    it('should apply confidence-specific badge colors', () => {
      const recommendations = [
        createMockRecommendation({ confidence: 'high', name: 'High Confidence' }),
        createMockRecommendation({ confidence: 'medium', name: 'Medium Confidence' }),
        createMockRecommendation({ confidence: 'low', name: 'Low Confidence' }),
      ];

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations, metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const { container } = renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(container.querySelector('.bg-green-100')).toBeInTheDocument();
      expect(container.querySelector('.bg-yellow-100')).toBeInTheDocument();
      expect(container.querySelector('.bg-gray-100')).toBeInTheDocument();
    });

    it('should apply custom className prop', () => {
      const recommendation = createMockRecommendation();

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const { container } = renderWithProviders(
        <PackageRecommendations {...defaultProps} className="custom-class" />,
      );

      expect(container.querySelector('.custom-class')).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 🔄 State Management
  // ==========================================================================

  describe('State Management', () => {
    it('should initialize with selectedPackageIds prop', () => {
      const recommendation = createMockRecommendation({ packageId: 'pkg-123' });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(
        <PackageRecommendations {...defaultProps} selectedPackageIds={['pkg-123']} />,
      );

      expect(screen.getByRole('button', { name: /selected/i })).toBeInTheDocument();
    });

    it('should maintain selection state across re-renders', async () => {
      const recommendation = createMockRecommendation({ packageId: 'pkg-123' });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const user = userEvent.setup();
      const { rerender } = renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add package/i });
      await user.click(addButton);

      rerender(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByRole('button', { name: /selected/i })).toBeInTheDocument();
    });

    it('should refetch recommendations after acceptance', async () => {
      const refetch = vi.fn();
      const recommendation = createMockRecommendation();

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch,
      });

      mockUseAcceptRecommendation.mockReturnValue({
        mutate: (data, options) => {
          acceptMutate(data);
          options?.onSuccess?.();
        },
        isPending: false,
      });

      const user = userEvent.setup();
      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add package/i });
      await user.click(addButton);

      await waitFor(() => {
        expect(refetch).toHaveBeenCalled();
      });
    });
  });

  // ==========================================================================
  // 🔧 Query Configuration
  // ==========================================================================

  describe('Query Configuration', () => {
    it('should pass correct parameters to usePackageRecommendations', () => {
      const recommendation = createMockRecommendation();

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(
        <PackageRecommendations
          vehicleId="vehicle-123"
          trimId="trim-456"
          selectedPackageIds={['pkg-1']}
          selectedOptionIds={['opt-1', 'opt-2']}
          budget={50000}
          maxRecommendations={3}
          showPopularConfigurations={true}
          region="US-CA"
        />,
      );

      expect(mockUsePackageRecommendations).toHaveBeenCalledWith(
        {
          vehicleId: 'vehicle-123',
          trimId: 'trim-456',
          selectedPackageIds: ['pkg-1'],
          selectedOptionIds: ['opt-1', 'opt-2'],
          budget: 50000,
          maxRecommendations: 3,
          includePopularConfigurations: true,
          region: 'US-CA',
        },
        expect.objectContaining({
          enabled: true,
          staleTime: 5 * 60 * 1000,
          retry: 2,
        }),
      );
    });

    it('should disable query when vehicleId is not provided', () => {
      mockUsePackageRecommendations.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} vehicleId="" />);

      expect(mockUsePackageRecommendations).toHaveBeenCalledWith(
        expect.any(Object),
        expect.objectContaining({
          enabled: false,
        }),
      );
    });
  });

  // ==========================================================================
  // 📊 Analytics Error Handling
  // ==========================================================================

  describe('Analytics Error Handling', () => {
    it('should log error when tracking fails', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const trackError = new Error('Tracking failed');

      mockUseTrackRecommendation.mockReturnValue({
        mutate: (_data, options) => {
          options?.onError?.(trackError);
        },
        isPending: false,
      });

      const recommendation = createMockRecommendation();

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const user = userEvent.setup();
      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const card = screen.getByRole('button', { pressed: false });
      await user.click(card);

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to track recommendation event:',
        trackError,
      );

      consoleErrorSpy.mockRestore();
    });

    it('should log error when acceptance fails', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const acceptError = new Error('Acceptance failed');

      mockUseAcceptRecommendation.mockReturnValue({
        mutate: (_data, options) => {
          options?.onError?.(acceptError);
        },
        isPending: false,
      });

      const recommendation = createMockRecommendation();

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const user = userEvent.setup();
      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add package/i });
      await user.click(addButton);

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to accept recommendation:',
        acceptError,
      );

      consoleErrorSpy.mockRestore();
    });
  });

  // ==========================================================================
  // 🎭 Edge Cases
  // ==========================================================================

  describe('Edge Cases', () => {
    it('should handle recommendations with zero savings', () => {
      const recommendation = createMockRecommendation({
        basePrice: 5000,
        discountedPrice: 5000,
        savingsAmount: 0,
        savingsPercentage: 0,
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.queryByText(/You save/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Save \d+%/i)).not.toBeInTheDocument();
    });

    it('should handle recommendations with no image', () => {
      const recommendation = createMockRecommendation({
        name: 'Basic Package',
        imageUrl: undefined,
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.queryByAltText('Basic Package')).not.toBeInTheDocument();
      expect(screen.getByText('Basic Package')).toBeInTheDocument();
    });

    it('should handle recommendations with empty reasons array', () => {
      const recommendation = createMockRecommendation({
        reasons: [],
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.queryByText('Why we recommend this:')).not.toBeInTheDocument();
    });

    it('should handle single included option correctly', () => {
      const recommendation = createMockRecommendation({
        includedOptions: ['opt-1'],
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByText('Includes 1 option')).toBeInTheDocument();
    });

    it('should handle popular configurations without trim name', () => {
      const recommendation = createMockRecommendation();
      const popularConfig = createMockPopularConfiguration({
        vehicleName: 'Model X',
        trimName: undefined,
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: {
          recommendations: [recommendation],
          popularConfigurations: [popularConfig],
          metadata: { processingTimeMs: 50 },
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(
        <PackageRecommendations {...defaultProps} showPopularConfigurations={true} />,
      );

      expect(screen.getByText('Model X')).toBeInTheDocument();
    });

    it('should handle popular configurations without rating', () => {
      const recommendation = createMockRecommendation();
      const popularConfig = createMockPopularConfiguration({
        averageRating: undefined,
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: {
          recommendations: [recommendation],
          popularConfigurations: [popularConfig],
          metadata: { processingTimeMs: 50 },
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(
        <PackageRecommendations {...defaultProps} showPopularConfigurations={true} />,
      );

      expect(screen.queryByText(/rating/i)).not.toBeInTheDocument();
    });

    it('should handle missing metadata gracefully', () => {
      const recommendation = createMockRecommendation();

      mockUsePackageRecommendations.mockReturnValue({
        data: {
          recommendations: [recommendation],
          metadata: undefined,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.queryByText(/Generated in/i)).not.toBeInTheDocument();
      expect(screen.getByText('Premium Package')).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // ⚡ Performance
  // ==========================================================================

  describe('Performance', () => {
    it('should memoize component to prevent unnecessary re-renders', () => {
      const recommendation = createMockRecommendation();

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const { rerender } = renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const firstRender = screen.getByText('Premium Package');

      rerender(<PackageRecommendations {...defaultProps} />);

      const secondRender = screen.getByText('Premium Package');

      expect(firstRender).toBe(secondRender);
    });

    it('should use lazy loading for images', () => {
      const recommendation = createMockRecommendation({
        imageUrl: 'https://example.com/image.jpg',
      });

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations: [recommendation], metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      const image = screen.getByRole('img');
      expect(image).toHaveAttribute('loading', 'lazy');
    });

    it('should efficiently calculate total savings with useMemo', () => {
      const recommendations = Array.from({ length: 100 }, () =>
        createMockRecommendation({ savingsAmount: 100 }),
      );

      mockUsePackageRecommendations.mockReturnValue({
        data: { recommendations, metadata: { processingTimeMs: 50 } },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithProviders(<PackageRecommendations {...defaultProps} />);

      expect(screen.getByText(/Save up to \$10,000/i)).toBeInTheDocument();
    });
  });
});