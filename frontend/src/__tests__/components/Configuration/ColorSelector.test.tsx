/**
 * ColorSelector Component Test Suite
 * 
 * Comprehensive tests for color selection, image preview, overlay effects,
 * and Unsplash integration with error handling.
 * 
 * Coverage Areas:
 * - Component rendering and initialization
 * - Color selection interactions
 * - Image loading states (idle, loading, loaded, error)
 * - Unsplash API integration and error handling
 * - Color overlay effects
 * - Category grouping and display
 * - Accessibility features
 * - Edge cases and error scenarios
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ColorSelector from '../../../components/Configuration/ColorSelector';
import * as unsplashService from '../../../services/unsplash';
import type { ColorOption } from '../../../types/configuration';

// ============================================================================
// 🎭 Test Data Factories
// ============================================================================

/**
 * Factory for creating test color options
 */
class ColorOptionFactory {
  private static idCounter = 0;

  static create(overrides: Partial<ColorOption> = {}): ColorOption {
    const id = `color-${++this.idCounter}`;
    return {
      id,
      name: `Test Color ${this.idCounter}`,
      hexCode: '#000000',
      category: 'standard',
      price: 0,
      isAvailable: true,
      ...overrides,
    };
  }

  static createMany(count: number, overrides: Partial<ColorOption> = {}): ColorOption[] {
    return Array.from({ length: count }, () => this.create(overrides));
  }

  static createByCategory(): ColorOption[] {
    return [
      this.create({ name: 'Arctic White', hexCode: '#FFFFFF', category: 'standard', price: 0 }),
      this.create({ name: 'Midnight Black', hexCode: '#000000', category: 'standard', price: 0 }),
      this.create({
        name: 'Silver Metallic',
        hexCode: '#C0C0C0',
        category: 'metallic',
        price: 500,
      }),
      this.create({
        name: 'Gold Metallic',
        hexCode: '#FFD700',
        category: 'metallic',
        price: 750,
      }),
      this.create({
        name: 'Ruby Red Premium',
        hexCode: '#E0115F',
        category: 'premium',
        price: 1500,
      }),
    ];
  }

  static reset(): void {
    this.idCounter = 0;
  }
}

/**
 * Factory for creating mock Unsplash responses
 */
class UnsplashResponseFactory {
  static createSuccess(overrides: Partial<{ url: string; seed: string }> = {}) {
    return {
      url: overrides.url ?? 'https://images.unsplash.com/photo-test?w=400',
      seed: overrides.seed ?? 'test-seed',
    };
  }

  static createError(message = 'Failed to fetch image') {
    const error = new Error(message);
    error.name = 'UnsplashImageError';
    return error;
  }
}

// ============================================================================
// 🎪 Mock Setup
// ============================================================================

vi.mock('../../../services/unsplash', () => ({
  generateVehicleImage: vi.fn(),
  isUnsplashImageError: vi.fn((error: unknown) => {
    return error instanceof Error && error.name === 'UnsplashImageError';
  }),
}));

// ============================================================================
// 🧪 Test Suite
// ============================================================================

describe('ColorSelector Component', () => {
  // Test props
  const defaultProps = {
    vehicleId: 'vehicle-123',
    colors: ColorOptionFactory.createByCategory(),
    selectedColorId: undefined,
    onColorSelect: vi.fn(),
    make: 'Tesla',
    model: 'Model 3',
    year: 2024,
    bodyStyle: 'sedan',
  };

  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
    ColorOptionFactory.reset();

    // Default mock implementation
    vi.mocked(unsplashService.generateVehicleImage).mockReturnValue(
      UnsplashResponseFactory.createSuccess(),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 🎯 Unit Tests - Component Rendering
  // ==========================================================================

  describe('Component Rendering', () => {
    it('should render loading skeleton when no colors provided', () => {
      render(<ColorSelector {...defaultProps} colors={[]} />);

      const skeletons = screen.getAllByRole('generic').filter((el) =>
        el.className.includes('animate-pulse'),
      );
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it('should render main preview placeholder when no color selected', () => {
      render(<ColorSelector {...defaultProps} />);

      expect(screen.getByText('Select a color to preview')).toBeInTheDocument();
    });

    it('should render all color thumbnails', () => {
      render(<ColorSelector {...defaultProps} />);

      defaultProps.colors.forEach((color) => {
        expect(screen.getByLabelText(`Select ${color.name} color`)).toBeInTheDocument();
      });
    });

    it('should group colors by category', () => {
      render(<ColorSelector {...defaultProps} />);

      expect(screen.getByText('Standard')).toBeInTheDocument();
      expect(screen.getByText('Metallic')).toBeInTheDocument();
      expect(screen.getByText('Premium')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      const { container } = render(
        <ColorSelector {...defaultProps} className="custom-class" />,
      );

      expect(container.firstChild).toHaveClass('custom-class');
    });

    it('should render "No colors available" when colors array is empty after initialization', () => {
      const { rerender } = render(<ColorSelector {...defaultProps} />);

      rerender(<ColorSelector {...defaultProps} colors={[]} />);

      expect(screen.getByText('No colors available')).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 🎯 Unit Tests - Color Selection
  // ==========================================================================

  describe('Color Selection', () => {
    it('should call onColorSelect when available color is clicked', async () => {
      const onColorSelect = vi.fn();
      render(<ColorSelector {...defaultProps} onColorSelect={onColorSelect} />);

      const firstColor = defaultProps.colors[0];
      const colorButton = screen.getByLabelText(`Select ${firstColor?.name} color`);

      await user.click(colorButton);

      expect(onColorSelect).toHaveBeenCalledWith(firstColor?.id);
      expect(onColorSelect).toHaveBeenCalledTimes(1);
    });

    it('should not call onColorSelect when unavailable color is clicked', async () => {
      const onColorSelect = vi.fn();
      const unavailableColor = ColorOptionFactory.create({
        name: 'Unavailable Color',
        isAvailable: false,
      });
      const colors = [...defaultProps.colors, unavailableColor];

      render(<ColorSelector {...defaultProps} colors={colors} onColorSelect={onColorSelect} />);

      const colorButton = screen.getByLabelText(`Select ${unavailableColor.name} color`);
      await user.click(colorButton);

      expect(onColorSelect).not.toHaveBeenCalled();
    });

    it('should highlight selected color with ring and scale', () => {
      const selectedColor = defaultProps.colors[0];
      render(<ColorSelector {...defaultProps} selectedColorId={selectedColor?.id} />);

      const colorButton = screen.getByLabelText(`Select ${selectedColor?.name} color`);

      expect(colorButton).toHaveClass('ring-4', 'ring-blue-500', 'scale-105');
    });

    it('should show checkmark icon on selected color', () => {
      const selectedColor = defaultProps.colors[0];
      render(<ColorSelector {...defaultProps} selectedColorId={selectedColor?.id} />);

      const colorButton = screen.getByLabelText(`Select ${selectedColor?.name} color`);
      const checkmark = within(colorButton).getByRole('generic', { hidden: true });

      expect(checkmark.querySelector('svg')).toBeInTheDocument();
    });

    it('should update aria-pressed attribute on selection', () => {
      const selectedColor = defaultProps.colors[0];
      render(<ColorSelector {...defaultProps} selectedColorId={selectedColor?.id} />);

      const colorButton = screen.getByLabelText(`Select ${selectedColor?.name} color`);

      expect(colorButton).toHaveAttribute('aria-pressed', 'true');
    });
  });

  // ==========================================================================
  // 🎯 Unit Tests - Image Loading States
  // ==========================================================================

  describe('Image Loading States', () => {
    it('should show loading state for thumbnails initially', () => {
      render(<ColorSelector {...defaultProps} />);

      const loadingElements = screen
        .getAllByRole('button')
        .filter((btn) => btn.querySelector('.animate-pulse'));

      expect(loadingElements.length).toBeGreaterThan(0);
    });

    it('should show loading state for main preview when color selected', async () => {
      const { rerender } = render(<ColorSelector {...defaultProps} />);

      const selectedColor = defaultProps.colors[0];
      rerender(<ColorSelector {...defaultProps} selectedColorId={selectedColor?.id} />);

      await waitFor(() => {
        expect(screen.getByText('Loading preview...')).toBeInTheDocument();
      });
    });

    it('should display image after successful load', async () => {
      render(<ColorSelector {...defaultProps} />);

      await waitFor(() => {
        const images = screen.getAllByRole('img');
        expect(images.length).toBeGreaterThan(0);
      });
    });

    it('should handle thumbnail image load event', async () => {
      render(<ColorSelector {...defaultProps} />);

      await waitFor(() => {
        const images = screen.getAllByRole('img');
        expect(images.length).toBeGreaterThan(0);
      });

      // Simulate image load
      const firstImage = screen.getAllByRole('img')[0];
      if (firstImage) {
        firstImage.dispatchEvent(new Event('load'));
      }

      // Image should be visible (not in loading state)
      expect(firstImage).toBeVisible();
    });

    it('should handle thumbnail image error event', async () => {
      render(<ColorSelector {...defaultProps} />);

      await waitFor(() => {
        const images = screen.getAllByRole('img');
        expect(images.length).toBeGreaterThan(0);
      });

      // Simulate image error
      const firstImage = screen.getAllByRole('img')[0];
      if (firstImage) {
        firstImage.dispatchEvent(new Event('error'));
      }

      await waitFor(() => {
        expect(screen.getByText('Preview unavailable')).toBeInTheDocument();
      });
    });

    it('should show error state for main preview on load failure', async () => {
      vi.mocked(unsplashService.generateVehicleImage).mockImplementation(() => {
        throw UnsplashResponseFactory.createError();
      });

      const selectedColor = defaultProps.colors[0];
      render(<ColorSelector {...defaultProps} selectedColorId={selectedColor?.id} />);

      await waitFor(() => {
        expect(screen.getByText('Failed to load preview image')).toBeInTheDocument();
      });
    });
  });

  // ==========================================================================
  // 🔗 Integration Tests - Unsplash Service
  // ==========================================================================

  describe('Unsplash Service Integration', () => {
    it('should call generateVehicleImage with correct parameters for thumbnails', async () => {
      render(<ColorSelector {...defaultProps} />);

      await waitFor(() => {
        expect(unsplashService.generateVehicleImage).toHaveBeenCalled();
      });

      const firstColor = defaultProps.colors[0];
      expect(unsplashService.generateVehicleImage).toHaveBeenCalledWith(
        expect.objectContaining({
          bodyStyle: 'sedan',
          make: 'Tesla',
          model: 'Model 3',
          year: 2024,
          color: firstColor?.name,
          size: 'thumbnail',
          seed: expect.stringContaining('vehicle-123'),
        }),
      );
    });

    it('should call generateVehicleImage with main size for preview', async () => {
      const selectedColor = defaultProps.colors[0];
      render(<ColorSelector {...defaultProps} selectedColorId={selectedColor?.id} />);

      await waitFor(() => {
        expect(unsplashService.generateVehicleImage).toHaveBeenCalledWith(
          expect.objectContaining({
            size: 'main',
            color: selectedColor?.name,
          }),
        );
      });
    });

    it('should generate unique seeds for each color', async () => {
      render(<ColorSelector {...defaultProps} />);

      await waitFor(() => {
        expect(unsplashService.generateVehicleImage).toHaveBeenCalled();
      });

      const calls = vi.mocked(unsplashService.generateVehicleImage).mock.calls;
      const seeds = calls.map((call) => call[0]?.seed);
      const uniqueSeeds = new Set(seeds);

      expect(uniqueSeeds.size).toBe(seeds.length);
    });

    it('should apply color overlay to image URLs', async () => {
      const mockUrl = 'https://images.unsplash.com/photo-test';
      vi.mocked(unsplashService.generateVehicleImage).mockReturnValue({
        url: mockUrl,
        seed: 'test-seed',
      });

      render(<ColorSelector {...defaultProps} />);

      await waitFor(() => {
        const images = screen.getAllByRole('img');
        expect(images.length).toBeGreaterThan(0);
      });

      const firstImage = screen.getAllByRole('img')[0];
      const firstColor = defaultProps.colors[0];
      const expectedOverlay = firstColor?.hexCode.replace('#', '');

      expect(firstImage?.getAttribute('src')).toContain('blend=');
      expect(firstImage?.getAttribute('src')).toContain(expectedOverlay);
    });

    it('should handle Unsplash API errors gracefully', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      vi.mocked(unsplashService.generateVehicleImage).mockImplementation(() => {
        throw UnsplashResponseFactory.createError('API rate limit exceeded');
      });

      render(<ColorSelector {...defaultProps} />);

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalled();
      });

      consoleErrorSpy.mockRestore();
    });

    it('should regenerate images when vehicle details change', async () => {
      const { rerender } = render(<ColorSelector {...defaultProps} />);

      await waitFor(() => {
        expect(unsplashService.generateVehicleImage).toHaveBeenCalled();
      });

      const initialCallCount = vi.mocked(unsplashService.generateVehicleImage).mock.calls.length;

      rerender(<ColorSelector {...defaultProps} model="Model S" />);

      await waitFor(() => {
        expect(vi.mocked(unsplashService.generateVehicleImage).mock.calls.length).toBeGreaterThan(
          initialCallCount,
        );
      });
    });
  });

  // ==========================================================================
  // 🎯 Unit Tests - Color Display and Formatting
  // ==========================================================================

  describe('Color Display and Formatting', () => {
    it('should display color name and category', () => {
      const selectedColor = defaultProps.colors[0];
      render(<ColorSelector {...defaultProps} selectedColorId={selectedColor?.id} />);

      expect(screen.getAllByText(selectedColor?.name ?? '').length).toBeGreaterThan(0);
    });

    it('should display color price when greater than zero', () => {
      const colorWithPrice = defaultProps.colors.find((c) => c.price > 0);
      render(<ColorSelector {...defaultProps} selectedColorId={colorWithPrice?.id} />);

      if (colorWithPrice) {
        expect(screen.getByText(`+$${colorWithPrice.price.toLocaleString()}`)).toBeInTheDocument();
      }
    });

    it('should not display price for free colors', () => {
      const freeColor = defaultProps.colors.find((c) => c.price === 0);
      render(<ColorSelector {...defaultProps} selectedColorId={freeColor?.id} />);

      const priceElements = screen.queryAllByText(/^\+\$/);
      expect(priceElements.length).toBe(0);
    });

    it('should display color swatch with correct hex code', () => {
      render(<ColorSelector {...defaultProps} />);

      defaultProps.colors.forEach((color) => {
        const colorButton = screen.getByLabelText(`Select ${color.name} color`);
        const swatch = within(colorButton).getByRole('generic', { hidden: true });

        expect(swatch).toHaveStyle({ backgroundColor: color.hexCode });
      });
    });

    it('should show unavailable overlay for unavailable colors', () => {
      const unavailableColor = ColorOptionFactory.create({
        name: 'Unavailable Color',
        isAvailable: false,
      });
      const colors = [...defaultProps.colors, unavailableColor];

      render(<ColorSelector {...defaultProps} colors={colors} />);

      const colorButton = screen.getByLabelText(`Select ${unavailableColor.name} color`);
      expect(within(colorButton).getByText('Unavailable')).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 🎯 Unit Tests - Main Preview Display
  // ==========================================================================

  describe('Main Preview Display', () => {
    it('should display selected color details in preview overlay', async () => {
      const selectedColor = defaultProps.colors[2]; // Metallic color with price
      render(<ColorSelector {...defaultProps} selectedColorId={selectedColor?.id} />);

      await waitFor(() => {
        expect(screen.getByText(selectedColor?.name ?? '')).toBeInTheDocument();
      });

      expect(screen.getByText('Metallic')).toBeInTheDocument();
      if (selectedColor && selectedColor.price > 0) {
        expect(screen.getByText(`+$${selectedColor.price.toLocaleString()}`)).toBeInTheDocument();
      }
    });

    it('should update preview when different color selected', async () => {
      const { rerender } = render(
        <ColorSelector {...defaultProps} selectedColorId={defaultProps.colors[0]?.id} />,
      );

      await waitFor(() => {
        expect(screen.getByText(defaultProps.colors[0]?.name ?? '')).toBeInTheDocument();
      });

      const newSelectedColor = defaultProps.colors[1];
      rerender(<ColorSelector {...defaultProps} selectedColorId={newSelectedColor?.id} />);

      await waitFor(() => {
        expect(screen.getByText(newSelectedColor?.name ?? '')).toBeInTheDocument();
      });
    });

    it('should clear preview when color deselected', async () => {
      const { rerender } = render(
        <ColorSelector {...defaultProps} selectedColorId={defaultProps.colors[0]?.id} />,
      );

      await waitFor(() => {
        expect(screen.queryByText('Select a color to preview')).not.toBeInTheDocument();
      });

      rerender(<ColorSelector {...defaultProps} selectedColorId={undefined} />);

      await waitFor(() => {
        expect(screen.getByText('Select a color to preview')).toBeInTheDocument();
      });
    });
  });

  // ==========================================================================
  // 🎯 Unit Tests - Selected Color Info Panel
  // ==========================================================================

  describe('Selected Color Info Panel', () => {
    it('should display selected color info panel', () => {
      const selectedColor = defaultProps.colors[0];
      render(<ColorSelector {...defaultProps} selectedColorId={selectedColor?.id} />);

      const infoPanel = screen.getByRole('generic', { hidden: true });
      expect(within(infoPanel).getByText(selectedColor?.name ?? '')).toBeInTheDocument();
    });

    it('should show color swatch in info panel', () => {
      const selectedColor = defaultProps.colors[0];
      render(<ColorSelector {...defaultProps} selectedColorId={selectedColor?.id} />);

      const swatches = screen.getAllByRole('generic', { hidden: true });
      const colorSwatch = swatches.find((el) =>
        el.style.backgroundColor.includes(selectedColor?.hexCode.replace('#', '')),
      );

      expect(colorSwatch).toBeDefined();
    });

    it('should display additional cost in info panel', () => {
      const colorWithPrice = defaultProps.colors.find((c) => c.price > 0);
      render(<ColorSelector {...defaultProps} selectedColorId={colorWithPrice?.id} />);

      expect(screen.getByText('Additional Cost')).toBeInTheDocument();
      if (colorWithPrice) {
        expect(screen.getByText(`+$${colorWithPrice.price.toLocaleString()}`)).toBeInTheDocument();
      }
    });

    it('should not show info panel when no color selected', () => {
      render(<ColorSelector {...defaultProps} />);

      expect(screen.queryByText('Additional Cost')).not.toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 🛡️ Edge Cases and Error Scenarios
  // ==========================================================================

  describe('Edge Cases and Error Scenarios', () => {
    it('should handle empty colors array', () => {
      render(<ColorSelector {...defaultProps} colors={[]} />);

      expect(screen.queryByText('No colors available')).not.toBeInTheDocument();
      expect(screen.getByRole('generic').className).toContain('animate-pulse');
    });

    it('should handle missing vehicle details', () => {
      render(
        <ColorSelector
          {...defaultProps}
          make={undefined}
          model={undefined}
          year={undefined}
          bodyStyle={undefined}
        />,
      );

      expect(unsplashService.generateVehicleImage).toHaveBeenCalledWith(
        expect.objectContaining({
          make: undefined,
          model: undefined,
          year: undefined,
          bodyStyle: undefined,
        }),
      );
    });

    it('should handle invalid color hex codes gracefully', () => {
      const invalidColor = ColorOptionFactory.create({
        name: 'Invalid Color',
        hexCode: 'invalid',
      });
      const colors = [...defaultProps.colors, invalidColor];

      render(<ColorSelector {...defaultProps} colors={colors} />);

      const colorButton = screen.getByLabelText(`Select ${invalidColor.name} color`);
      expect(colorButton).toBeInTheDocument();
    });

    it('should handle rapid color selection changes', async () => {
      const onColorSelect = vi.fn();
      render(<ColorSelector {...defaultProps} onColorSelect={onColorSelect} />);

      // Rapidly click multiple colors
      for (const color of defaultProps.colors.slice(0, 3)) {
        const colorButton = screen.getByLabelText(`Select ${color.name} color`);
        await user.click(colorButton);
      }

      expect(onColorSelect).toHaveBeenCalledTimes(3);
    });

    it('should handle very long color names', () => {
      const longNameColor = ColorOptionFactory.create({
        name: 'This is a very long color name that should be truncated properly in the UI',
      });
      const colors = [...defaultProps.colors, longNameColor];

      render(<ColorSelector {...defaultProps} colors={colors} />);

      const colorButton = screen.getByLabelText(`Select ${longNameColor.name} color`);
      expect(colorButton).toBeInTheDocument();
    });

    it('should handle colors with zero price', () => {
      const freeColor = ColorOptionFactory.create({ price: 0 });
      render(<ColorSelector {...defaultProps} selectedColorId={freeColor.id} colors={[freeColor]} />);

      expect(screen.queryByText(/^\+\$/)).not.toBeInTheDocument();
    });

    it('should handle colors with very high prices', () => {
      const expensiveColor = ColorOptionFactory.create({
        name: 'Diamond Platinum',
        price: 999999,
      });
      render(
        <ColorSelector
          {...defaultProps}
          selectedColorId={expensiveColor.id}
          colors={[expensiveColor]}
        />,
      );

      expect(screen.getByText('+$999,999')).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // ♿ Accessibility Tests
  // ==========================================================================

  describe('Accessibility', () => {
    it('should have proper ARIA labels for color buttons', () => {
      render(<ColorSelector {...defaultProps} />);

      defaultProps.colors.forEach((color) => {
        const button = screen.getByLabelText(`Select ${color.name} color`);
        expect(button).toHaveAttribute('aria-label');
      });
    });

    it('should have proper ARIA pressed state', () => {
      const selectedColor = defaultProps.colors[0];
      render(<ColorSelector {...defaultProps} selectedColorId={selectedColor?.id} />);

      const selectedButton = screen.getByLabelText(`Select ${selectedColor?.name} color`);
      expect(selectedButton).toHaveAttribute('aria-pressed', 'true');

      const unselectedButton = screen.getByLabelText(
        `Select ${defaultProps.colors[1]?.name} color`,
      );
      expect(unselectedButton).toHaveAttribute('aria-pressed', 'false');
    });

    it('should disable unavailable color buttons', () => {
      const unavailableColor = ColorOptionFactory.create({
        name: 'Unavailable Color',
        isAvailable: false,
      });
      const colors = [...defaultProps.colors, unavailableColor];

      render(<ColorSelector {...defaultProps} colors={colors} />);

      const button = screen.getByLabelText(`Select ${unavailableColor.name} color`);
      expect(button).toBeDisabled();
    });

    it('should have proper button type attributes', () => {
      render(<ColorSelector {...defaultProps} />);

      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        expect(button).toHaveAttribute('type', 'button');
      });
    });

    it('should have descriptive alt text for images', async () => {
      const selectedColor = defaultProps.colors[0];
      render(<ColorSelector {...defaultProps} selectedColorId={selectedColor?.id} />);

      await waitFor(() => {
        const previewImage = screen.getByAltText(`${selectedColor?.name} preview`);
        expect(previewImage).toBeInTheDocument();
      });
    });

    it('should use aria-hidden for decorative elements', () => {
      render(<ColorSelector {...defaultProps} />);

      const decorativeElements = screen.getAllByRole('generic', { hidden: true });
      decorativeElements.forEach((element) => {
        expect(element).toHaveAttribute('aria-hidden', 'true');
      });
    });
  });

  // ==========================================================================
  // ⚡ Performance Tests
  // ==========================================================================

  describe('Performance', () => {
    it('should render large number of colors efficiently', () => {
      const manyColors = ColorOptionFactory.createMany(50);
      const startTime = performance.now();

      render(<ColorSelector {...defaultProps} colors={manyColors} />);

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      // Should render in less than 1 second
      expect(renderTime).toBeLessThan(1000);
    });

    it('should use lazy loading for thumbnail images', async () => {
      render(<ColorSelector {...defaultProps} />);

      await waitFor(() => {
        const images = screen.getAllByRole('img');
        expect(images.length).toBeGreaterThan(0);
      });

      const thumbnailImages = screen
        .getAllByRole('img')
        .filter((img) => img.getAttribute('loading') === 'lazy');

      expect(thumbnailImages.length).toBeGreaterThan(0);
    });

    it('should use eager loading for main preview image', async () => {
      const selectedColor = defaultProps.colors[0];
      render(<ColorSelector {...defaultProps} selectedColorId={selectedColor?.id} />);

      await waitFor(() => {
        const previewImage = screen.getByAltText(`${selectedColor?.name} preview`);
        expect(previewImage).toHaveAttribute('loading', 'eager');
      });
    });

    it('should not regenerate images unnecessarily', async () => {
      const { rerender } = render(<ColorSelector {...defaultProps} />);

      await waitFor(() => {
        expect(unsplashService.generateVehicleImage).toHaveBeenCalled();
      });

      const initialCallCount = vi.mocked(unsplashService.generateVehicleImage).mock.calls.length;

      // Rerender with same props
      rerender(<ColorSelector {...defaultProps} />);

      await waitFor(() => {
        expect(vi.mocked(unsplashService.generateVehicleImage).mock.calls.length).toBe(
          initialCallCount,
        );
      });
    });
  });

  // ==========================================================================
  // 🔄 State Management Tests
  // ==========================================================================

  describe('State Management', () => {
    it('should maintain image load states independently', async () => {
      render(<ColorSelector {...defaultProps} />);

      await waitFor(() => {
        const images = screen.getAllByRole('img');
        expect(images.length).toBeGreaterThan(0);
      });

      // Simulate one image loading successfully
      const firstImage = screen.getAllByRole('img')[0];
      if (firstImage) {
        firstImage.dispatchEvent(new Event('load'));
      }

      // Simulate another image failing
      const secondImage = screen.getAllByRole('img')[1];
      if (secondImage) {
        secondImage.dispatchEvent(new Event('error'));
      }

      // Both states should coexist
      expect(firstImage).toBeVisible();
      await waitFor(() => {
        expect(screen.getByText('Preview unavailable')).toBeInTheDocument();
      });
    });

    it('should clear main image when selection is removed', async () => {
      const { rerender } = render(
        <ColorSelector {...defaultProps} selectedColorId={defaultProps.colors[0]?.id} />,
      );

      await waitFor(() => {
        expect(screen.queryByText('Select a color to preview')).not.toBeInTheDocument();
      });

      rerender(<ColorSelector {...defaultProps} selectedColorId={undefined} />);

      await waitFor(() => {
        expect(screen.getByText('Select a color to preview')).toBeInTheDocument();
      });
    });

    it('should update color images when colors prop changes', async () => {
      const { rerender } = render(<ColorSelector {...defaultProps} />);

      await waitFor(() => {
        expect(unsplashService.generateVehicleImage).toHaveBeenCalled();
      });

      const newColors = ColorOptionFactory.createMany(3);
      rerender(<ColorSelector {...defaultProps} colors={newColors} />);

      await waitFor(() => {
        newColors.forEach((color) => {
          expect(screen.getByLabelText(`Select ${color.name} color`)).toBeInTheDocument();
        });
      });
    });
  });

  // ==========================================================================
  // 🎨 Visual Regression Tests
  // ==========================================================================

  describe('Visual Styling', () => {
    it('should apply hover effects to available colors', async () => {
      render(<ColorSelector {...defaultProps} />);

      const firstColor = defaultProps.colors[0];
      const colorButton = screen.getByLabelText(`Select ${firstColor?.name} color`);

      expect(colorButton).toHaveClass('hover:ring-blue-300');
      expect(colorButton).toHaveClass('hover:scale-105');
    });

    it('should not apply hover effects to unavailable colors', () => {
      const unavailableColor = ColorOptionFactory.create({
        name: 'Unavailable Color',
        isAvailable: false,
      });
      const colors = [...defaultProps.colors, unavailableColor];

      render(<ColorSelector {...defaultProps} colors={colors} />);

      const colorButton = screen.getByLabelText(`Select ${unavailableColor.name} color`);

      expect(colorButton).toHaveClass('cursor-not-allowed', 'opacity-50');
    });

    it('should apply gradient overlay to preview image', async () => {
      const selectedColor = defaultProps.colors[0];
      render(<ColorSelector {...defaultProps} selectedColorId={selectedColor?.id} />);

      await waitFor(() => {
        const gradient = screen.getByText(selectedColor?.name ?? '').closest('div');
        expect(gradient?.className).toContain('bg-gradient-to-t');
      });
    });

    it('should display color category badges correctly', () => {
      render(<ColorSelector {...defaultProps} />);

      expect(screen.getByText('Standard')).toBeInTheDocument();
      expect(screen.getByText('Metallic')).toBeInTheDocument();
      expect(screen.getByText('Premium')).toBeInTheDocument();
    });
  });
});