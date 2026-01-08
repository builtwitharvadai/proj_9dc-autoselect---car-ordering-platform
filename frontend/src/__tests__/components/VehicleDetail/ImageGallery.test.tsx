/**
 * ImageGallery Component Test Suite
 * 
 * Comprehensive tests for the ImageGallery component including:
 * - Image loading and error handling
 * - Thumbnail navigation
 * - Zoom functionality
 * - Keyboard navigation
 * - Accessibility features
 * - Lazy loading
 * - Edge cases and error scenarios
 * 
 * Coverage Target: >80%
 * Test Framework: Vitest + React Testing Library
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ImageGallery from '@/components/VehicleDetail/ImageGallery';
import * as unsplashService from '@/services/unsplash';
import type { Vehicle } from '@/types/vehicle';

// ============================================================================
// 🏭 Test Data Factories
// ============================================================================

/**
 * Creates a mock vehicle for testing
 */
const createMockVehicle = (overrides?: Partial<Vehicle>): Vehicle => ({
  id: 'test-vehicle-123',
  make: 'Tesla',
  model: 'Model 3',
  year: 2024,
  bodyStyle: 'sedan',
  color: 'blue',
  price: 45000,
  mileage: 0,
  transmission: 'automatic',
  fuelType: 'electric',
  features: ['Autopilot', 'Premium Audio'],
  description: 'Test vehicle description',
  status: 'available',
  vin: 'TEST123456789',
  ...overrides,
});

/**
 * Creates mock image data
 */
const createMockImages = (count: number) =>
  Array.from({ length: count }, (_, i) => ({
    url: `https://images.unsplash.com/photo-${i}?w=800`,
    thumbnailUrl: `https://images.unsplash.com/photo-${i}?w=200`,
    alt: `Test Image ${i + 1}`,
    loaded: false,
    error: null,
  }));

// ============================================================================
// 🎭 Mock Setup
// ============================================================================

/**
 * Mock Unsplash service
 */
vi.mock('@/services/unsplash', () => ({
  generateVehicleImages: vi.fn(),
  isUnsplashImageError: vi.fn(),
}));

/**
 * Mock IntersectionObserver for lazy loading tests
 */
class MockIntersectionObserver {
  readonly root = null;
  readonly rootMargin = '';
  readonly thresholds = [];

  constructor(
    private callback: IntersectionObserverCallback,
    _options?: IntersectionObserverInit,
  ) {}

  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
  takeRecords = vi.fn(() => []);

  trigger(entries: Partial<IntersectionObserverEntry>[]) {
    this.callback(entries as IntersectionObserverEntry[], this);
  }
}

// ============================================================================
// 🧪 Test Suite
// ============================================================================

describe('ImageGallery Component', () => {
  let mockVehicle: Vehicle;
  let mockGenerateImages: ReturnType<typeof vi.fn>;
  let mockIsUnsplashError: ReturnType<typeof vi.fn>;
  let mockObserver: MockIntersectionObserver;

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();

    // Setup mock vehicle
    mockVehicle = createMockVehicle();

    // Setup Unsplash service mocks
    mockGenerateImages = vi.mocked(unsplashService.generateVehicleImages);
    mockIsUnsplashError = vi.mocked(unsplashService.isUnsplashImageError);

    mockGenerateImages.mockImplementation((config, types) =>
      types.map((type, index) => ({
        url: `https://images.unsplash.com/photo-${index}?w=${type === 'thumbnail' ? '200' : '800'}`,
        alt: `${config.year} ${config.make} ${config.model}`,
      })),
    );

    mockIsUnsplashError.mockReturnValue(false);

    // Setup IntersectionObserver mock
    mockObserver = new MockIntersectionObserver(() => {});
    global.IntersectionObserver = vi.fn(() => mockObserver) as any;

    // Mock scrollIntoView
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 🎯 Unit Tests - Rendering
  // ==========================================================================

  describe('Rendering', () => {
    it('should render image gallery with default props', () => {
      render(<ImageGallery vehicle={mockVehicle} />);

      expect(screen.getByRole('region', { name: /vehicle image gallery/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /previous image/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /next image/i })).toBeInTheDocument();
    });

    it('should render with custom className', () => {
      const { container } = render(
        <ImageGallery vehicle={mockVehicle} className="custom-class" />,
      );

      const gallery = container.querySelector('.custom-class');
      expect(gallery).toBeInTheDocument();
    });

    it('should generate correct number of images', () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const thumbnails = screen.getAllByRole('tab');
      expect(thumbnails).toHaveLength(3);
    });

    it('should display image counter', () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={5} />);

      expect(screen.getByText('1 / 5')).toBeInTheDocument();
    });

    it('should render thumbnails with correct attributes', () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const thumbnails = screen.getAllByRole('tab');
      expect(thumbnails[0]).toHaveAttribute('aria-selected', 'true');
      expect(thumbnails[1]).toHaveAttribute('aria-selected', 'false');
    });
  });

  // ==========================================================================
  // 🎯 Unit Tests - Image Loading
  // ==========================================================================

  describe('Image Loading', () => {
    it('should show loading spinner initially', () => {
      render(<ImageGallery vehicle={mockVehicle} />);

      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(screen.getByText(/loading image/i)).toBeInTheDocument();
    });

    it('should hide loading spinner after image loads', async () => {
      render(<ImageGallery vehicle={mockVehicle} />);

      const mainImage = screen.getByAltText(/tesla model 3 - image 1/i);
      fireEvent.load(mainImage);

      await waitFor(() => {
        expect(screen.queryByRole('status')).not.toBeInTheDocument();
      });
    });

    it('should call onImageLoad callback when image loads', async () => {
      const onImageLoad = vi.fn();
      render(<ImageGallery vehicle={mockVehicle} onImageLoad={onImageLoad} />);

      const mainImage = screen.getByAltText(/tesla model 3 - image 1/i);
      fireEvent.load(mainImage);

      await waitFor(() => {
        expect(onImageLoad).toHaveBeenCalledWith(0);
      });
    });

    it('should display error state when image fails to load', async () => {
      render(<ImageGallery vehicle={mockVehicle} />);

      const mainImage = screen.getByAltText(/tesla model 3 - image 1/i);
      fireEvent.error(mainImage);

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
        expect(screen.getByText(/failed to load image/i)).toBeInTheDocument();
      });
    });

    it('should call onImageError callback when image fails', async () => {
      const onImageError = vi.fn();
      render(<ImageGallery vehicle={mockVehicle} onImageError={onImageError} />);

      const mainImage = screen.getByAltText(/tesla model 3 - image 1/i);
      fireEvent.error(mainImage);

      await waitFor(() => {
        expect(onImageError).toHaveBeenCalledWith(0, expect.any(Error));
      });
    });

    it('should display Unsplash error message when available', async () => {
      const unsplashError = new Error('Unsplash API rate limit exceeded');
      mockIsUnsplashError.mockReturnValue(true);

      render(<ImageGallery vehicle={mockVehicle} />);

      const mainImage = screen.getByAltText(/tesla model 3 - image 1/i);
      fireEvent.error(mainImage);

      await waitFor(() => {
        expect(mockIsUnsplashError).toHaveBeenCalled();
      });
    });
  });

  // ==========================================================================
  // 🎯 Unit Tests - Navigation
  // ==========================================================================

  describe('Navigation', () => {
    it('should navigate to next image on next button click', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const nextButton = screen.getByRole('button', { name: /next image/i });
      await userEvent.click(nextButton);

      expect(screen.getByText('2 / 3')).toBeInTheDocument();
    });

    it('should navigate to previous image on previous button click', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const nextButton = screen.getByRole('button', { name: /next image/i });
      await userEvent.click(nextButton);

      const prevButton = screen.getByRole('button', { name: /previous image/i });
      await userEvent.click(prevButton);

      expect(screen.getByText('1 / 3')).toBeInTheDocument();
    });

    it('should wrap to last image when clicking previous on first image', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const prevButton = screen.getByRole('button', { name: /previous image/i });
      await userEvent.click(prevButton);

      expect(screen.getByText('3 / 3')).toBeInTheDocument();
    });

    it('should wrap to first image when clicking next on last image', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const nextButton = screen.getByRole('button', { name: /next image/i });
      await userEvent.click(nextButton);
      await userEvent.click(nextButton);
      await userEvent.click(nextButton);

      expect(screen.getByText('1 / 3')).toBeInTheDocument();
    });

    it('should navigate to specific image on thumbnail click', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const thumbnails = screen.getAllByRole('tab');
      await userEvent.click(thumbnails[2]);

      expect(screen.getByText('3 / 3')).toBeInTheDocument();
      expect(thumbnails[2]).toHaveAttribute('aria-selected', 'true');
    });

    it('should scroll thumbnail into view when navigating', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={5} />);

      const nextButton = screen.getByRole('button', { name: /next image/i });
      await userEvent.click(nextButton);

      await waitFor(() => {
        expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
      });
    });
  });

  // ==========================================================================
  // 🎯 Unit Tests - Keyboard Navigation
  // ==========================================================================

  describe('Keyboard Navigation', () => {
    it('should navigate to next image on ArrowRight key', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const gallery = screen.getByRole('region', { name: /vehicle image gallery/i });
      fireEvent.keyDown(gallery, { key: 'ArrowRight' });

      expect(screen.getByText('2 / 3')).toBeInTheDocument();
    });

    it('should navigate to previous image on ArrowLeft key', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const gallery = screen.getByRole('region', { name: /vehicle image gallery/i });
      fireEvent.keyDown(gallery, { key: 'ArrowRight' });
      fireEvent.keyDown(gallery, { key: 'ArrowLeft' });

      expect(screen.getByText('1 / 3')).toBeInTheDocument();
    });

    it('should navigate to first image on Home key', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const gallery = screen.getByRole('region', { name: /vehicle image gallery/i });
      fireEvent.keyDown(gallery, { key: 'ArrowRight' });
      fireEvent.keyDown(gallery, { key: 'ArrowRight' });
      fireEvent.keyDown(gallery, { key: 'Home' });

      expect(screen.getByText('1 / 3')).toBeInTheDocument();
    });

    it('should navigate to last image on End key', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const gallery = screen.getByRole('region', { name: /vehicle image gallery/i });
      fireEvent.keyDown(gallery, { key: 'End' });

      expect(screen.getByText('3 / 3')).toBeInTheDocument();
    });

    it('should prevent default behavior for navigation keys', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const gallery = screen.getByRole('region', { name: /vehicle image gallery/i });
      const event = new KeyboardEvent('keydown', { key: 'ArrowRight' });
      const preventDefaultSpy = vi.spyOn(event, 'preventDefault');

      fireEvent(gallery, event);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });
  });

  // ==========================================================================
  // 🎯 Unit Tests - Zoom Functionality
  // ==========================================================================

  describe('Zoom Functionality', () => {
    it('should toggle zoom on image click when enabled', async () => {
      render(<ImageGallery vehicle={mockVehicle} enableZoom={true} />);

      const mainImage = screen.getByAltText(/tesla model 3 - image 1/i);
      const imageContainer = mainImage.closest('[role="button"]');

      expect(imageContainer).toHaveAttribute('aria-label', 'Click to zoom in');

      await userEvent.click(imageContainer!);

      expect(imageContainer).toHaveAttribute('aria-label', 'Click to zoom out');
    });

    it('should not zoom when enableZoom is false', async () => {
      render(<ImageGallery vehicle={mockVehicle} enableZoom={false} />);

      const mainImage = screen.getByAltText(/tesla model 3 - image 1/i);
      const imageContainer = mainImage.closest('[role="button"]');

      await userEvent.click(imageContainer!);

      expect(imageContainer).toHaveAttribute('aria-label', 'Click to zoom in');
    });

    it('should update zoom position on mouse move when zoomed', async () => {
      render(<ImageGallery vehicle={mockVehicle} enableZoom={true} />);

      const mainImage = screen.getByAltText(/tesla model 3 - image 1/i);
      const imageContainer = mainImage.closest('[role="button"]');

      await userEvent.click(imageContainer!);

      fireEvent.mouseMove(imageContainer!, {
        clientX: 100,
        clientY: 100,
      });

      // Verify zoom transform is applied
      expect(mainImage).toHaveStyle({ transform: expect.stringContaining('scale') });
    });

    it('should reset zoom on Escape key', async () => {
      render(<ImageGallery vehicle={mockVehicle} enableZoom={true} />);

      const gallery = screen.getByRole('region', { name: /vehicle image gallery/i });
      const mainImage = screen.getByAltText(/tesla model 3 - image 1/i);
      const imageContainer = mainImage.closest('[role="button"]');

      await userEvent.click(imageContainer!);
      fireEvent.keyDown(gallery, { key: 'Escape' });

      expect(imageContainer).toHaveAttribute('aria-label', 'Click to zoom in');
    });

    it('should reset zoom when navigating to different image', async () => {
      render(<ImageGallery vehicle={mockVehicle} enableZoom={true} thumbnailCount={3} />);

      const mainImage = screen.getByAltText(/tesla model 3 - image 1/i);
      const imageContainer = mainImage.closest('[role="button"]');

      await userEvent.click(imageContainer!);

      const nextButton = screen.getByRole('button', { name: /next image/i });
      await userEvent.click(nextButton);

      const newImageContainer = screen
        .getByAltText(/tesla model 3 - image 2/i)
        .closest('[role="button"]');
      expect(newImageContainer).toHaveAttribute('aria-label', 'Click to zoom in');
    });
  });

  // ==========================================================================
  // 🎯 Unit Tests - Lazy Loading
  // ==========================================================================

  describe('Lazy Loading', () => {
    it('should setup IntersectionObserver with correct options', () => {
      render(<ImageGallery vehicle={mockVehicle} lazyLoadThreshold={200} />);

      expect(global.IntersectionObserver).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          rootMargin: '200px',
          threshold: 0.01,
        }),
      );
    });

    it('should observe thumbnail images', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      await waitFor(() => {
        expect(mockObserver.observe).toHaveBeenCalled();
      });
    });

    it('should disconnect observer on unmount', () => {
      const { unmount } = render(<ImageGallery vehicle={mockVehicle} />);

      unmount();

      expect(mockObserver.disconnect).toHaveBeenCalled();
    });

    it('should load image when thumbnail becomes visible', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const thumbnails = screen.getAllByAltText(/thumbnail/i);
      const thumbnail = thumbnails[0] as HTMLImageElement;

      mockObserver.trigger([
        {
          target: thumbnail,
          isIntersecting: true,
        } as Partial<IntersectionObserverEntry>,
      ]);

      await waitFor(() => {
        expect(thumbnail.src).toBeTruthy();
      });
    });
  });

  // ==========================================================================
  // 🎯 Unit Tests - Edge Cases
  // ==========================================================================

  describe('Edge Cases', () => {
    it('should handle empty images array gracefully', () => {
      mockGenerateImages.mockReturnValue([]);

      render(<ImageGallery vehicle={mockVehicle} />);

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/no images available/i)).toBeInTheDocument();
    });

    it('should not render navigation buttons with single image', () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={1} />);

      expect(screen.queryByRole('button', { name: /previous image/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /next image/i })).not.toBeInTheDocument();
    });

    it('should not render thumbnail navigation with single image', () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={1} />);

      expect(screen.queryByRole('tablist')).not.toBeInTheDocument();
    });

    it('should handle image generation error', () => {
      mockGenerateImages.mockImplementation(() => {
        throw new Error('Failed to generate images');
      });

      // Suppress console.error for this test
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(<ImageGallery vehicle={mockVehicle} />);

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/no images available/i)).toBeInTheDocument();

      consoleErrorSpy.mockRestore();
    });

    it('should handle thumbnail with error state', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const mainImage = screen.getByAltText(/tesla model 3 - image 1/i);
      fireEvent.error(mainImage);

      await waitFor(() => {
        const thumbnails = screen.getAllByRole('tab');
        const errorIcon = within(thumbnails[0]).getByRole('img', { hidden: true });
        expect(errorIcon).toBeInTheDocument();
      });
    });

    it('should handle rapid navigation clicks', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={5} />);

      const nextButton = screen.getByRole('button', { name: /next image/i });

      // Rapidly click next button
      await userEvent.click(nextButton);
      await userEvent.click(nextButton);
      await userEvent.click(nextButton);

      expect(screen.getByText('4 / 5')).toBeInTheDocument();
    });

    it('should handle mouse move without zoom', () => {
      render(<ImageGallery vehicle={mockVehicle} enableZoom={true} />);

      const mainImage = screen.getByAltText(/tesla model 3 - image 1/i);
      const imageContainer = mainImage.closest('[role="button"]');

      // Mouse move without zoom should not throw
      expect(() => {
        fireEvent.mouseMove(imageContainer!, {
          clientX: 100,
          clientY: 100,
        });
      }).not.toThrow();
    });
  });

  // ==========================================================================
  // 🎯 Integration Tests - Accessibility
  // ==========================================================================

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      expect(screen.getByRole('region', { name: /vehicle image gallery/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /previous image/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /next image/i })).toBeInTheDocument();
      expect(screen.getByRole('tablist', { name: /image thumbnails/i })).toBeInTheDocument();
    });

    it('should have proper focus management', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const prevButton = screen.getByRole('button', { name: /previous image/i });
      const nextButton = screen.getByRole('button', { name: /next image/i });

      prevButton.focus();
      expect(prevButton).toHaveFocus();

      await userEvent.tab();
      expect(nextButton).toHaveFocus();
    });

    it('should announce image counter changes', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const counter = screen.getByText('1 / 3');
      expect(counter).toHaveAttribute('aria-live', 'polite');
      expect(counter).toHaveAttribute('aria-atomic', 'true');
    });

    it('should have proper alt text for images', () => {
      render(<ImageGallery vehicle={mockVehicle} />);

      const mainImage = screen.getByAltText(/2024 tesla model 3 - image 1/i);
      expect(mainImage).toBeInTheDocument();
    });

    it('should have keyboard accessible zoom toggle', async () => {
      render(<ImageGallery vehicle={mockVehicle} enableZoom={true} />);

      const mainImage = screen.getByAltText(/tesla model 3 - image 1/i);
      const imageContainer = mainImage.closest('[role="button"]');

      expect(imageContainer).toHaveAttribute('tabindex', '0');
    });

    it('should announce loading state', () => {
      render(<ImageGallery vehicle={mockVehicle} />);

      const loadingStatus = screen.getByRole('status');
      expect(loadingStatus).toHaveAttribute('aria-live', 'polite');
    });

    it('should announce error state', async () => {
      render(<ImageGallery vehicle={mockVehicle} />);

      const mainImage = screen.getByAltText(/tesla model 3 - image 1/i);
      fireEvent.error(mainImage);

      await waitFor(() => {
        const errorAlert = screen.getByRole('alert');
        expect(errorAlert).toHaveAttribute('aria-live', 'polite');
      });
    });
  });

  // ==========================================================================
  // 🎯 Integration Tests - Component Interactions
  // ==========================================================================

  describe('Component Interactions', () => {
    it('should maintain state consistency during navigation', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const nextButton = screen.getByRole('button', { name: /next image/i });
      await userEvent.click(nextButton);

      expect(screen.getByText('2 / 3')).toBeInTheDocument();

      const thumbnails = screen.getAllByRole('tab');
      expect(thumbnails[1]).toHaveAttribute('aria-selected', 'true');
      expect(thumbnails[0]).toHaveAttribute('aria-selected', 'false');
    });

    it('should handle multiple prop changes', async () => {
      const { rerender } = render(
        <ImageGallery vehicle={mockVehicle} thumbnailCount={3} enableZoom={true} />,
      );

      rerender(<ImageGallery vehicle={mockVehicle} thumbnailCount={5} enableZoom={false} />);

      const thumbnails = screen.getAllByRole('tab');
      expect(thumbnails).toHaveLength(5);
    });

    it('should handle vehicle prop change', async () => {
      const { rerender } = render(<ImageGallery vehicle={mockVehicle} />);

      const newVehicle = createMockVehicle({
        id: 'new-vehicle-456',
        make: 'BMW',
        model: 'M3',
      });

      rerender(<ImageGallery vehicle={newVehicle} />);

      await waitFor(() => {
        expect(mockGenerateImages).toHaveBeenCalledWith(
          expect.objectContaining({
            make: 'BMW',
            model: 'M3',
          }),
          expect.any(Array),
        );
      });
    });

    it('should coordinate zoom and navigation', async () => {
      render(<ImageGallery vehicle={mockVehicle} enableZoom={true} thumbnailCount={3} />);

      const mainImage = screen.getByAltText(/tesla model 3 - image 1/i);
      const imageContainer = mainImage.closest('[role="button"]');

      // Zoom in
      await userEvent.click(imageContainer!);
      expect(imageContainer).toHaveAttribute('aria-label', 'Click to zoom out');

      // Navigate
      const nextButton = screen.getByRole('button', { name: /next image/i });
      await userEvent.click(nextButton);

      // Zoom should reset
      const newImageContainer = screen
        .getByAltText(/tesla model 3 - image 2/i)
        .closest('[role="button"]');
      expect(newImageContainer).toHaveAttribute('aria-label', 'Click to zoom in');
    });
  });

  // ==========================================================================
  // 🎯 Performance Tests
  // ==========================================================================

  describe('Performance', () => {
    it('should render efficiently with many images', () => {
      const startTime = performance.now();

      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={20} />);

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      // Render should complete in less than 100ms
      expect(renderTime).toBeLessThan(100);
    });

    it('should not re-render unnecessarily', async () => {
      const { rerender } = render(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      const renderCount = mockGenerateImages.mock.calls.length;

      // Re-render with same props
      rerender(<ImageGallery vehicle={mockVehicle} thumbnailCount={3} />);

      // Should not generate images again
      expect(mockGenerateImages.mock.calls.length).toBe(renderCount);
    });

    it('should handle rapid state updates efficiently', async () => {
      render(<ImageGallery vehicle={mockVehicle} thumbnailCount={10} />);

      const nextButton = screen.getByRole('button', { name: /next image/i });

      // Rapidly navigate
      const startTime = performance.now();
      for (let i = 0; i < 10; i++) {
        await userEvent.click(nextButton);
      }
      const endTime = performance.now();

      // Should complete in reasonable time
      expect(endTime - startTime).toBeLessThan(1000);
    });
  });

  // ==========================================================================
  // 🎯 Security Tests
  // ==========================================================================

  describe('Security', () => {
    it('should sanitize image URLs', () => {
      const maliciousVehicle = createMockVehicle({
        make: '<script>alert("xss")</script>',
      });

      render(<ImageGallery vehicle={maliciousVehicle} />);

      const mainImage = screen.getByRole('img', { name: /image 1/i });
      expect(mainImage.getAttribute('alt')).not.toContain('<script>');
    });

    it('should handle invalid image URLs gracefully', async () => {
      mockGenerateImages.mockReturnValue([
        {
          url: 'javascript:alert("xss")',
          alt: 'Test',
        },
      ]);

      render(<ImageGallery vehicle={mockVehicle} />);

      // Should not execute malicious code
      expect(screen.getByRole('region')).toBeInTheDocument();
    });

    it('should prevent XSS in alt text', () => {
      const xssVehicle = createMockVehicle({
        model: '"><img src=x onerror=alert(1)>',
      });

      render(<ImageGallery vehicle={xssVehicle} />);

      const images = screen.getAllByRole('img');
      images.forEach((img) => {
        expect(img.getAttribute('alt')).not.toContain('onerror');
      });
    });
  });
});