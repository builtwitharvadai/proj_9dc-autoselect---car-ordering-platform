/**
 * VehicleGrid Component Test Suite
 * 
 * Comprehensive tests for VehicleGrid component including:
 * - Component rendering and structure
 * - Loading states and skeleton UI
 * - Empty state handling
 * - Vehicle card interactions
 * - Image loading and error states
 * - Accessibility compliance
 * - Responsive behavior
 * - User interactions (click, hover, keyboard)
 * - Price formatting and display
 * - Availability badge rendering
 * 
 * Coverage Target: >80%
 * Test Framework: Vitest + React Testing Library
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import VehicleGrid from '../../../components/VehicleBrowsing/VehicleGrid';
import type { Vehicle } from '../../../types/vehicle';

// ============================================================================
// 🏭 Test Data Factories
// ============================================================================

/**
 * Create a mock vehicle with default values
 */
function createMockVehicle(overrides: Partial<Vehicle> = {}): Vehicle {
  return {
    id: 'vehicle-1',
    make: 'Tesla',
    model: 'Model 3',
    year: 2024,
    trim: 'Long Range',
    bodyStyle: 'sedan',
    price: 45000,
    msrp: 50000,
    availability: 'available',
    isDeleted: false,
    imageUrl: 'https://example.com/tesla-model-3.jpg',
    specifications: {
      horsepower: 346,
      seatingCapacity: 5,
      fuelEconomy: {
        city: 132,
        highway: 126,
      },
      transmission: 'automatic',
      drivetrain: 'awd',
      engine: 'electric',
    },
    features: [],
    createdAt: new Date('2024-01-01'),
    updatedAt: new Date('2024-01-01'),
    ...overrides,
  };
}

/**
 * Create multiple mock vehicles
 */
function createMockVehicles(count: number): Vehicle[] {
  return Array.from({ length: count }, (_, index) => createMockVehicle({
    id: `vehicle-${index + 1}`,
    make: ['Tesla', 'BMW', 'Audi', 'Mercedes'][index % 4],
    model: ['Model 3', 'X5', 'A4', 'C-Class'][index % 4],
    price: 40000 + (index * 5000),
    msrp: 45000 + (index * 5000),
  }));
}

// ============================================================================
// 🎭 Test Setup and Utilities
// ============================================================================

/**
 * Setup user event for interactions
 */
function setupUser() {
  return userEvent.setup();
}

/**
 * Mock IntersectionObserver for lazy loading tests
 */
function mockIntersectionObserver() {
  const mockIntersectionObserver = vi.fn();
  mockIntersectionObserver.mockReturnValue({
    observe: () => null,
    unobserve: () => null,
    disconnect: () => null,
  });
  window.IntersectionObserver = mockIntersectionObserver as any;
}

// ============================================================================
// 🧪 Test Suite: Component Rendering
// ============================================================================

describe('VehicleGrid - Component Rendering', () => {
  beforeEach(() => {
    mockIntersectionObserver();
  });

  it('should render vehicle grid with vehicles', () => {
    const vehicles = createMockVehicles(3);
    render(<VehicleGrid vehicles={vehicles} />);

    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.getByLabelText('3 vehicles available')).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(3);
  });

  it('should render vehicle cards with correct information', () => {
    const vehicle = createMockVehicle({
      make: 'Tesla',
      model: 'Model 3',
      year: 2024,
      trim: 'Long Range',
      price: 45000,
      msrp: 50000,
    });
    render(<VehicleGrid vehicles={[vehicle]} />);

    expect(screen.getByText('2024 Tesla Model 3 Long Range')).toBeInTheDocument();
    expect(screen.getByText('$45,000')).toBeInTheDocument();
    expect(screen.getByText('$50,000')).toBeInTheDocument();
    expect(screen.getByText('346 HP')).toBeInTheDocument();
    expect(screen.getByText('5 Seats')).toBeInTheDocument();
    expect(screen.getByText(/132\/126/)).toBeInTheDocument();
  });

  it('should render vehicle without trim', () => {
    const vehicle = createMockVehicle({
      make: 'BMW',
      model: 'X5',
      year: 2024,
      trim: undefined,
    });
    render(<VehicleGrid vehicles={[vehicle]} />);

    expect(screen.getByText('2024 BMW X5')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const vehicles = createMockVehicles(1);
    const { container } = render(
      <VehicleGrid vehicles={vehicles} className="custom-class" />
    );

    const gridElement = container.querySelector('.custom-class');
    expect(gridElement).toBeInTheDocument();
  });

  it('should render responsive grid classes', () => {
    const vehicles = createMockVehicles(1);
    const { container } = render(<VehicleGrid vehicles={vehicles} />);

    const gridElement = container.querySelector(
      '.grid.grid-cols-1.sm\\:grid-cols-2.lg\\:grid-cols-3.xl\\:grid-cols-4'
    );
    expect(gridElement).toBeInTheDocument();
  });
});

// ============================================================================
// 🧪 Test Suite: Loading States
// ============================================================================

describe('VehicleGrid - Loading States', () => {
  it('should render skeleton cards when loading', () => {
    render(<VehicleGrid vehicles={[]} isLoading={true} />);

    expect(screen.getByRole('status', { name: 'Loading vehicles' })).toBeInTheDocument();
    
    const skeletons = screen.getAllByRole('status').filter(
      (el) => el.classList.contains('animate-pulse')
    );
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('should render custom number of skeleton cards', () => {
    const { container } = render(
      <VehicleGrid vehicles={[]} isLoading={true} skeletonCount={6} />
    );

    const skeletonCards = container.querySelectorAll('.animate-pulse');
    expect(skeletonCards).toHaveLength(6);
  });

  it('should render default 12 skeleton cards', () => {
    const { container } = render(
      <VehicleGrid vehicles={[]} isLoading={true} />
    );

    const skeletonCards = container.querySelectorAll('.animate-pulse');
    expect(skeletonCards).toHaveLength(12);
  });

  it('should not render vehicles when loading', () => {
    const vehicles = createMockVehicles(3);
    render(<VehicleGrid vehicles={vehicles} isLoading={true} />);

    expect(screen.queryByRole('list')).not.toBeInTheDocument();
    expect(screen.queryByText('Tesla')).not.toBeInTheDocument();
  });
});

// ============================================================================
// 🧪 Test Suite: Empty State
// ============================================================================

describe('VehicleGrid - Empty State', () => {
  it('should render empty state when no vehicles', () => {
    render(<VehicleGrid vehicles={[]} />);

    expect(screen.getByRole('status', { name: 'No vehicles available' })).toBeInTheDocument();
    expect(screen.getByText('No vehicles found')).toBeInTheDocument();
    expect(
      screen.getByText(/We couldn't find any vehicles matching your criteria/)
    ).toBeInTheDocument();
  });

  it('should render empty state icon', () => {
    const { container } = render(<VehicleGrid vehicles={[]} />);

    const icon = container.querySelector('svg.w-24.h-24.text-gray-400');
    expect(icon).toBeInTheDocument();
  });

  it('should not render empty state when loading', () => {
    render(<VehicleGrid vehicles={[]} isLoading={true} />);

    expect(screen.queryByText('No vehicles found')).not.toBeInTheDocument();
  });

  it('should not render empty state when vehicles exist', () => {
    const vehicles = createMockVehicles(1);
    render(<VehicleGrid vehicles={vehicles} />);

    expect(screen.queryByText('No vehicles found')).not.toBeInTheDocument();
  });
});

// ============================================================================
// 🧪 Test Suite: Vehicle Card Interactions
// ============================================================================

describe('VehicleGrid - Vehicle Card Interactions', () => {
  it('should call onVehicleClick when card is clicked', async () => {
    const user = setupUser();
    const onVehicleClick = vi.fn();
    const vehicle = createMockVehicle();
    render(<VehicleGrid vehicles={[vehicle]} onVehicleClick={onVehicleClick} />);

    const card = screen.getByRole('button', { name: /View details for 2024 Tesla Model 3/ });
    await user.click(card);

    expect(onVehicleClick).toHaveBeenCalledTimes(1);
    expect(onVehicleClick).toHaveBeenCalledWith(vehicle);
  });

  it('should call onVehicleClick when View Details button is clicked', async () => {
    const user = setupUser();
    const onVehicleClick = vi.fn();
    const vehicle = createMockVehicle();
    render(<VehicleGrid vehicles={[vehicle]} onVehicleClick={onVehicleClick} />);

    const button = screen.getByRole('button', { name: /View details for 2024 Tesla Model 3 Long Range/ });
    await user.click(button);

    expect(onVehicleClick).toHaveBeenCalledTimes(1);
  });

  it('should call onVehicleHover on mouse enter', async () => {
    const user = setupUser();
    const onVehicleHover = vi.fn();
    const vehicle = createMockVehicle();
    render(<VehicleGrid vehicles={[vehicle]} onVehicleHover={onVehicleHover} />);

    const card = screen.getByRole('button', { name: /View details for 2024 Tesla Model 3/ });
    await user.hover(card);

    expect(onVehicleHover).toHaveBeenCalledWith(vehicle.id);
  });

  it('should call onVehicleHover with null on mouse leave', async () => {
    const user = setupUser();
    const onVehicleHover = vi.fn();
    const vehicle = createMockVehicle();
    render(<VehicleGrid vehicles={[vehicle]} onVehicleHover={onVehicleHover} />);

    const card = screen.getByRole('button', { name: /View details for 2024 Tesla Model 3/ });
    await user.hover(card);
    await user.unhover(card);

    expect(onVehicleHover).toHaveBeenCalledWith(null);
  });

  it('should handle keyboard navigation with Enter key', async () => {
    const user = setupUser();
    const onVehicleClick = vi.fn();
    const vehicle = createMockVehicle();
    render(<VehicleGrid vehicles={[vehicle]} onVehicleClick={onVehicleClick} />);

    const card = screen.getByRole('button', { name: /View details for 2024 Tesla Model 3/ });
    card.focus();
    await user.keyboard('{Enter}');

    expect(onVehicleClick).toHaveBeenCalledTimes(1);
  });

  it('should handle keyboard navigation with Space key', async () => {
    const user = setupUser();
    const onVehicleClick = vi.fn();
    const vehicle = createMockVehicle();
    render(<VehicleGrid vehicles={[vehicle]} onVehicleClick={onVehicleClick} />);

    const card = screen.getByRole('button', { name: /View details for 2024 Tesla Model 3/ });
    card.focus();
    await user.keyboard(' ');

    expect(onVehicleClick).toHaveBeenCalledTimes(1);
  });

  it('should not trigger click on other keys', async () => {
    const user = setupUser();
    const onVehicleClick = vi.fn();
    const vehicle = createMockVehicle();
    render(<VehicleGrid vehicles={[vehicle]} onVehicleClick={onVehicleClick} />);

    const card = screen.getByRole('button', { name: /View details for 2024 Tesla Model 3/ });
    card.focus();
    await user.keyboard('{Tab}');

    expect(onVehicleClick).not.toHaveBeenCalled();
  });
});

// ============================================================================
// 🧪 Test Suite: Image Loading
// ============================================================================

describe('VehicleGrid - Image Loading', () => {
  it('should show loading state before image loads', () => {
    const vehicle = createMockVehicle();
    const { container } = render(<VehicleGrid vehicles={[vehicle]} />);

    const loadingState = container.querySelector('.animate-pulse');
    expect(loadingState).toBeInTheDocument();
  });

  it('should show image after successful load', async () => {
    const vehicle = createMockVehicle();
    render(<VehicleGrid vehicles={[vehicle]} />);

    const image = screen.getByAltText('2024 Tesla Model 3 Long Range') as HTMLImageElement;
    
    // Simulate image load
    await waitFor(() => {
      image.dispatchEvent(new Event('load'));
    });

    expect(image).toHaveClass('opacity-100');
  });

  it('should show error state when image fails to load', async () => {
    const vehicle = createMockVehicle();
    const { container } = render(<VehicleGrid vehicles={[vehicle]} />);

    const image = screen.getByAltText('2024 Tesla Model 3 Long Range') as HTMLImageElement;
    
    // Simulate image error
    await waitFor(() => {
      image.dispatchEvent(new Event('error'));
    });

    const errorIcon = container.querySelector('svg.w-16.h-16.text-gray-400');
    expect(errorIcon).toBeInTheDocument();
  });

  it('should have lazy loading attribute', () => {
    const vehicle = createMockVehicle();
    render(<VehicleGrid vehicles={[vehicle]} />);

    const image = screen.getByAltText('2024 Tesla Model 3 Long Range') as HTMLImageElement;
    expect(image).toHaveAttribute('loading', 'lazy');
  });
});

// ============================================================================
// 🧪 Test Suite: Availability Badge
// ============================================================================

describe('VehicleGrid - Availability Badge', () => {
  it('should render available badge with correct styling', () => {
    const vehicle = createMockVehicle({ availability: 'available' });
    render(<VehicleGrid vehicles={[vehicle]} />);

    const badge = screen.getByText('Available');
    expect(badge).toHaveClass('bg-green-100', 'text-green-800');
  });

  it('should render reserved badge with correct styling', () => {
    const vehicle = createMockVehicle({ availability: 'reserved' });
    render(<VehicleGrid vehicles={[vehicle]} />);

    const badge = screen.getByText('Reserved');
    expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });

  it('should render sold badge with correct styling', () => {
    const vehicle = createMockVehicle({ availability: 'sold' });
    render(<VehicleGrid vehicles={[vehicle]} />);

    const badge = screen.getByText('Sold');
    expect(badge).toHaveClass('bg-red-100', 'text-red-800');
  });

  it('should render unavailable badge with correct styling', () => {
    const vehicle = createMockVehicle({ availability: 'unavailable' });
    render(<VehicleGrid vehicles={[vehicle]} />);

    const badge = screen.getByText('Unavailable');
    expect(badge).toHaveClass('bg-gray-100', 'text-gray-800');
  });

  it('should hide View Details button for unavailable vehicles', () => {
    const vehicle = createMockVehicle({ availability: 'sold' });
    render(<VehicleGrid vehicles={[vehicle]} />);

    expect(screen.queryByText('View Details')).not.toBeInTheDocument();
  });

  it('should hide View Details button for deleted vehicles', () => {
    const vehicle = createMockVehicle({ isDeleted: true });
    render(<VehicleGrid vehicles={[vehicle]} />);

    expect(screen.queryByText('View Details')).not.toBeInTheDocument();
  });

  it('should show View Details button for available vehicles', () => {
    const vehicle = createMockVehicle({ availability: 'available', isDeleted: false });
    render(<VehicleGrid vehicles={[vehicle]} />);

    expect(screen.getByText('View Details')).toBeInTheDocument();
  });
});

// ============================================================================
// 🧪 Test Suite: Price Formatting
// ============================================================================

describe('VehicleGrid - Price Formatting', () => {
  it('should format price as USD currency', () => {
    const vehicle = createMockVehicle({ price: 45000 });
    render(<VehicleGrid vehicles={[vehicle]} />);

    expect(screen.getByText('$45,000')).toBeInTheDocument();
  });

  it('should show MSRP when different from price', () => {
    const vehicle = createMockVehicle({ price: 45000, msrp: 50000 });
    render(<VehicleGrid vehicles={[vehicle]} />);

    expect(screen.getByText('$45,000')).toBeInTheDocument();
    expect(screen.getByText('$50,000')).toBeInTheDocument();
    
    const msrpElement = screen.getByText('$50,000');
    expect(msrpElement).toHaveClass('line-through');
  });

  it('should not show MSRP when same as price', () => {
    const vehicle = createMockVehicle({ price: 45000, msrp: 45000 });
    render(<VehicleGrid vehicles={[vehicle]} />);

    const prices = screen.getAllByText('$45,000');
    expect(prices).toHaveLength(1);
  });

  it('should format large prices correctly', () => {
    const vehicle = createMockVehicle({ price: 125000 });
    render(<VehicleGrid vehicles={[vehicle]} />);

    expect(screen.getByText('$125,000')).toBeInTheDocument();
  });

  it('should format prices without decimals', () => {
    const vehicle = createMockVehicle({ price: 45999 });
    render(<VehicleGrid vehicles={[vehicle]} />);

    expect(screen.getByText('$45,999')).toBeInTheDocument();
    expect(screen.queryByText(/\.\d{2}/)).not.toBeInTheDocument();
  });
});

// ============================================================================
// 🧪 Test Suite: Accessibility
// ============================================================================

describe('VehicleGrid - Accessibility', () => {
  it('should have proper ARIA labels on grid', () => {
    const vehicles = createMockVehicles(3);
    render(<VehicleGrid vehicles={vehicles} />);

    expect(screen.getByRole('list')).toHaveAttribute('aria-label', '3 vehicles available');
  });

  it('should have proper ARIA labels on cards', () => {
    const vehicle = createMockVehicle();
    render(<VehicleGrid vehicles={[vehicle]} />);

    const card = screen.getByRole('button', { 
      name: 'View details for 2024 Tesla Model 3 Long Range' 
    });
    expect(card).toBeInTheDocument();
  });

  it('should be keyboard navigable', () => {
    const vehicle = createMockVehicle();
    render(<VehicleGrid vehicles={[vehicle]} />);

    const card = screen.getByRole('button', { name: /View details for 2024 Tesla Model 3/ });
    expect(card).toHaveAttribute('tabIndex', '0');
  });

  it('should have focus visible styles', () => {
    const vehicle = createMockVehicle();
    render(<VehicleGrid vehicles={[vehicle]} />);

    const card = screen.getByRole('button', { name: /View details for 2024 Tesla Model 3/ });
    expect(card).toHaveClass('focus-within:ring-2', 'focus-within:ring-blue-500');
  });

  it('should have proper alt text for images', () => {
    const vehicle = createMockVehicle();
    render(<VehicleGrid vehicles={[vehicle]} />);

    const image = screen.getByAltText('2024 Tesla Model 3 Long Range');
    expect(image).toBeInTheDocument();
  });

  it('should hide decorative icons from screen readers', () => {
    const vehicle = createMockVehicle();
    const { container } = render(<VehicleGrid vehicles={[vehicle]} />);

    const icons = container.querySelectorAll('svg[aria-hidden="true"]');
    expect(icons.length).toBeGreaterThan(0);
  });

  it('should have proper loading state announcement', () => {
    render(<VehicleGrid vehicles={[]} isLoading={true} />);

    expect(screen.getByRole('status', { name: 'Loading vehicles' })).toBeInTheDocument();
  });

  it('should have proper empty state announcement', () => {
    render(<VehicleGrid vehicles={[]} />);

    expect(screen.getByRole('status', { name: 'No vehicles available' })).toBeInTheDocument();
  });
});

// ============================================================================
// 🧪 Test Suite: Multiple Vehicles
// ============================================================================

describe('VehicleGrid - Multiple Vehicles', () => {
  it('should render multiple vehicles correctly', () => {
    const vehicles = createMockVehicles(6);
    render(<VehicleGrid vehicles={vehicles} />);

    expect(screen.getAllByRole('listitem')).toHaveLength(6);
    expect(screen.getByLabelText('6 vehicles available')).toBeInTheDocument();
  });

  it('should render each vehicle with unique key', () => {
    const vehicles = createMockVehicles(3);
    const { container } = render(<VehicleGrid vehicles={vehicles} />);

    const listItems = container.querySelectorAll('[role="listitem"]');
    const keys = Array.from(listItems).map((item) => item.getAttribute('key'));
    const uniqueKeys = new Set(keys);
    
    expect(uniqueKeys.size).toBe(keys.length);
  });

  it('should handle large number of vehicles', () => {
    const vehicles = createMockVehicles(50);
    render(<VehicleGrid vehicles={vehicles} />);

    expect(screen.getAllByRole('listitem')).toHaveLength(50);
  });

  it('should maintain performance with many vehicles', () => {
    const vehicles = createMockVehicles(100);
    const startTime = performance.now();
    
    render(<VehicleGrid vehicles={vehicles} />);
    
    const endTime = performance.now();
    const renderTime = endTime - startTime;
    
    // Render should complete in less than 1 second
    expect(renderTime).toBeLessThan(1000);
  });
});

// ============================================================================
// 🧪 Test Suite: Edge Cases
// ============================================================================

describe('VehicleGrid - Edge Cases', () => {
  it('should handle vehicle with missing optional fields', () => {
    const vehicle = createMockVehicle({
      trim: undefined,
      msrp: 45000,
      price: 45000,
    });
    render(<VehicleGrid vehicles={[vehicle]} />);

    expect(screen.getByText('2024 Tesla Model 3')).toBeInTheDocument();
  });

  it('should handle very long vehicle names', () => {
    const vehicle = createMockVehicle({
      make: 'Mercedes-Benz',
      model: 'S-Class Maybach',
      trim: 'S 680 4MATIC Sedan',
    });
    render(<VehicleGrid vehicles={[vehicle]} />);

    const title = screen.getByText(/2024 Mercedes-Benz S-Class Maybach/);
    expect(title).toHaveClass('line-clamp-1');
  });

  it('should handle zero price', () => {
    const vehicle = createMockVehicle({ price: 0 });
    render(<VehicleGrid vehicles={[vehicle]} />);

    expect(screen.getByText('$0')).toBeInTheDocument();
  });

  it('should handle very high prices', () => {
    const vehicle = createMockVehicle({ price: 999999 });
    render(<VehicleGrid vehicles={[vehicle]} />);

    expect(screen.getByText('$999,999')).toBeInTheDocument();
  });

  it('should handle missing image URL gracefully', () => {
    const vehicle = createMockVehicle({ imageUrl: '' });
    const { container } = render(<VehicleGrid vehicles={[vehicle]} />);

    const image = container.querySelector('img');
    expect(image).toHaveAttribute('src', '');
  });

  it('should handle special characters in vehicle data', () => {
    const vehicle = createMockVehicle({
      make: "O'Brien's",
      model: 'Test & Demo',
    });
    render(<VehicleGrid vehicles={[vehicle]} />);

    expect(screen.getByText(/O'Brien's Test & Demo/)).toBeInTheDocument();
  });
});

// ============================================================================
// 🧪 Test Suite: Component Memoization
// ============================================================================

describe('VehicleGrid - Component Memoization', () => {
  it('should not re-render vehicle cards when props unchanged', () => {
    const vehicles = createMockVehicles(3);
    const { rerender } = render(<VehicleGrid vehicles={vehicles} />);

    const initialCards = screen.getAllByRole('button');
    
    rerender(<VehicleGrid vehicles={vehicles} />);
    
    const afterCards = screen.getAllByRole('button');
    expect(initialCards).toEqual(afterCards);
  });

  it('should re-render when vehicles change', () => {
    const vehicles1 = createMockVehicles(2);
    const vehicles2 = createMockVehicles(3);
    
    const { rerender } = render(<VehicleGrid vehicles={vehicles1} />);
    expect(screen.getAllByRole('listitem')).toHaveLength(2);

    rerender(<VehicleGrid vehicles={vehicles2} />);
    expect(screen.getAllByRole('listitem')).toHaveLength(3);
  });
});

// ============================================================================
// 🧪 Test Suite: Responsive Behavior
// ============================================================================

describe('VehicleGrid - Responsive Behavior', () => {
  it('should have responsive grid classes', () => {
    const vehicles = createMockVehicles(4);
    const { container } = render(<VehicleGrid vehicles={vehicles} />);

    const grid = container.querySelector('.grid');
    expect(grid).toHaveClass(
      'grid-cols-1',
      'sm:grid-cols-2',
      'lg:grid-cols-3',
      'xl:grid-cols-4'
    );
  });

  it('should maintain aspect ratio for images', () => {
    const vehicle = createMockVehicle();
    const { container } = render(<VehicleGrid vehicles={[vehicle]} />);

    const imageContainer = container.querySelector('.aspect-\\[4\\/3\\]');
    expect(imageContainer).toBeInTheDocument();
  });
});

// ============================================================================
// 🧪 Test Suite: Hover Effects
// ============================================================================

describe('VehicleGrid - Hover Effects', () => {
  it('should apply hover classes to card', () => {
    const vehicle = createMockVehicle();
    const { container } = render(<VehicleGrid vehicles={[vehicle]} />);

    const card = container.querySelector('.group');
    expect(card).toHaveClass('hover:shadow-xl', 'hover:-translate-y-1');
  });

  it('should apply hover classes to image', () => {
    const vehicle = createMockVehicle();
    const { container } = render(<VehicleGrid vehicles={[vehicle]} />);

    const image = screen.getByAltText('2024 Tesla Model 3 Long Range');
    expect(image).toHaveClass('group-hover:scale-110');
  });

  it('should apply hover classes to title', () => {
    const vehicle = createMockVehicle();
    render(<VehicleGrid vehicles={[vehicle]} />);

    const title = screen.getByText('2024 Tesla Model 3 Long Range');
    expect(title).toHaveClass('group-hover:text-blue-600');
  });
});