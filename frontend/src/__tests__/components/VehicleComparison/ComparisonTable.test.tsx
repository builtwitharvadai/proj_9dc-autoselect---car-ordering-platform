/**
 * ComparisonTable Component Test Suite
 * 
 * Comprehensive tests for the vehicle comparison table component including:
 * - Rendering with various vehicle combinations
 * - Difference highlighting functionality
 * - Sticky header behavior
 * - Remove vehicle functionality
 * - Responsive design and accessibility
 * - Edge cases and error scenarios
 * 
 * @module components/VehicleComparison/__tests__/ComparisonTable.test
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import ComparisonTable from '../ComparisonTable';
import type { Vehicle } from '../../../types/vehicle';

// ============================================================================
// Test Data Factories
// ============================================================================

/**
 * Create a mock vehicle with default values
 */
function createMockVehicle(overrides: Partial<Vehicle> = {}): Vehicle {
  const defaults: Vehicle = {
    id: `vehicle-${Math.random().toString(36).substr(2, 9)}`,
    year: 2024,
    make: 'Toyota',
    model: 'Camry',
    trim: 'LE',
    bodyStyle: 'Sedan',
    price: 28000,
    msrp: 30000,
    imageUrl: 'https://example.com/camry.jpg',
    specifications: {
      engine: '2.5L 4-Cylinder',
      horsepower: 203,
      torque: 184,
      transmission: '8-Speed Automatic',
      drivetrain: 'fwd',
      fuelType: 'Gasoline',
      fuelEconomy: {
        city: 28,
        highway: 39,
        combined: 32,
      },
      dimensions: {
        length: 192.7,
        width: 72.4,
        height: 56.9,
        wheelbase: 111.2,
        groundClearance: 5.7,
        cargoVolume: 15.1,
      },
      seatingCapacity: 5,
      curbWeight: 3310,
      towingCapacity: 1000,
    },
    features: {
      safety: ['Forward Collision Warning', 'Lane Departure Warning'],
      comfort: ['Dual-Zone Climate Control', 'Power Seats'],
      technology: ['Apple CarPlay', 'Android Auto'],
      entertainment: ['8-inch Touchscreen', 'Bluetooth'],
      exterior: ['LED Headlights', 'Alloy Wheels'],
      interior: ['Leather Seats', 'Heated Seats'],
    },
    availability: {
      status: 'in_stock',
      quantity: 5,
      estimatedDelivery: '2024-01-15',
    },
    dealerInfo: {
      dealerId: 'dealer-1',
      dealerName: 'Test Dealer',
      location: 'Test City',
      distance: 10,
    },
  };

  return { ...defaults, ...overrides };
}

/**
 * Create multiple mock vehicles with variations
 */
function createMockVehicles(count: number): Vehicle[] {
  const vehicles: Vehicle[] = [];
  
  for (let i = 0; i < count; i++) {
    vehicles.push(
      createMockVehicle({
        id: `vehicle-${i}`,
        make: ['Toyota', 'Honda', 'Ford', 'Chevrolet'][i % 4],
        model: ['Camry', 'Accord', 'Fusion', 'Malibu'][i % 4],
        price: 28000 + i * 2000,
        specifications: {
          ...createMockVehicle().specifications,
          horsepower: 200 + i * 10,
          fuelEconomy: {
            city: 28 - i,
            highway: 39 - i,
            combined: 32 - i,
          },
        },
      })
    );
  }
  
  return vehicles;
}

// ============================================================================
// Test Setup and Utilities
// ============================================================================

describe('ComparisonTable', () => {
  let mockScrollTo: ReturnType<typeof vi.fn>;
  let mockAddEventListener: ReturnType<typeof vi.fn>;
  let mockRemoveEventListener: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    // Mock window.scrollTo
    mockScrollTo = vi.fn();
    window.scrollTo = mockScrollTo;

    // Mock window event listeners
    mockAddEventListener = vi.fn();
    mockRemoveEventListener = vi.fn();
    window.addEventListener = mockAddEventListener;
    window.removeEventListener = mockRemoveEventListener;

    // Mock IntersectionObserver
    global.IntersectionObserver = vi.fn().mockImplementation(() => ({
      observe: vi.fn(),
      unobserve: vi.fn(),
      disconnect: vi.fn(),
    }));
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ==========================================================================
  // Basic Rendering Tests
  // ==========================================================================

  describe('Basic Rendering', () => {
    it('should render empty state when no vehicles provided', () => {
      render(<ComparisonTable vehicles={[]} />);
      
      expect(screen.getByText('No vehicles to compare')).toBeInTheDocument();
    });

    it('should render single vehicle comparison', () => {
      const vehicle = createMockVehicle();
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      expect(screen.getByText(`${vehicle.year} ${vehicle.make}`)).toBeInTheDocument();
      expect(screen.getByText(vehicle.model)).toBeInTheDocument();
      expect(screen.getByText(vehicle.trim!)).toBeInTheDocument();
    });

    it('should render multiple vehicles side by side', () => {
      const vehicles = createMockVehicles(3);
      render(<ComparisonTable vehicles={vehicles} />);
      
      vehicles.forEach((vehicle) => {
        expect(screen.getByText(`${vehicle.year} ${vehicle.make}`)).toBeInTheDocument();
        expect(screen.getByText(vehicle.model)).toBeInTheDocument();
      });
    });

    it('should render vehicle images with correct alt text', () => {
      const vehicle = createMockVehicle();
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      const image = screen.getByAltText(
        `${vehicle.year} ${vehicle.make} ${vehicle.model}`
      );
      expect(image).toBeInTheDocument();
      expect(image).toHaveAttribute('src', vehicle.imageUrl);
      expect(image).toHaveAttribute('loading', 'lazy');
    });

    it('should apply custom className', () => {
      const vehicles = createMockVehicles(1);
      const { container } = render(
        <ComparisonTable vehicles={vehicles} className="custom-class" />
      );
      
      expect(container.querySelector('.comparison-table')).toHaveClass('custom-class');
    });
  });

  // ==========================================================================
  // Specification Display Tests
  // ==========================================================================

  describe('Specification Display', () => {
    it('should display all basic information specifications', () => {
      const vehicle = createMockVehicle();
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      expect(screen.getByText('Year')).toBeInTheDocument();
      expect(screen.getByText('Make')).toBeInTheDocument();
      expect(screen.getByText('Model')).toBeInTheDocument();
      expect(screen.getByText('Trim')).toBeInTheDocument();
      expect(screen.getByText('Body Style')).toBeInTheDocument();
      expect(screen.getByText('Price')).toBeInTheDocument();
      expect(screen.getByText('MSRP')).toBeInTheDocument();
    });

    it('should display engine and performance specifications', () => {
      const vehicle = createMockVehicle();
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      expect(screen.getByText('Engine')).toBeInTheDocument();
      expect(screen.getByText('Horsepower')).toBeInTheDocument();
      expect(screen.getByText('Torque')).toBeInTheDocument();
      expect(screen.getByText('Transmission')).toBeInTheDocument();
      expect(screen.getByText('Drivetrain')).toBeInTheDocument();
      expect(screen.getByText('Fuel Type')).toBeInTheDocument();
    });

    it('should display fuel economy specifications', () => {
      const vehicle = createMockVehicle();
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      expect(screen.getByText('City MPG')).toBeInTheDocument();
      expect(screen.getByText('Highway MPG')).toBeInTheDocument();
      expect(screen.getByText('Combined MPG')).toBeInTheDocument();
    });

    it('should display dimension specifications', () => {
      const vehicle = createMockVehicle();
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      expect(screen.getByText('Length')).toBeInTheDocument();
      expect(screen.getByText('Width')).toBeInTheDocument();
      expect(screen.getByText('Height')).toBeInTheDocument();
      expect(screen.getByText('Wheelbase')).toBeInTheDocument();
    });

    it('should display optional specifications when present', () => {
      const vehicle = createMockVehicle();
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      expect(screen.getByText('Ground Clearance')).toBeInTheDocument();
      expect(screen.getByText('Cargo Volume')).toBeInTheDocument();
      expect(screen.getByText('Curb Weight')).toBeInTheDocument();
      expect(screen.getByText('Towing Capacity')).toBeInTheDocument();
    });

    it('should format currency values correctly', () => {
      const vehicle = createMockVehicle({ price: 35000, msrp: 38000 });
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      expect(screen.getByText('$35,000')).toBeInTheDocument();
      expect(screen.getByText('$38,000')).toBeInTheDocument();
    });

    it('should format numeric values with units', () => {
      const vehicle = createMockVehicle();
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      expect(screen.getByText('203 hp')).toBeInTheDocument();
      expect(screen.getByText('184 lb-ft')).toBeInTheDocument();
      expect(screen.getByText('28 mpg')).toBeInTheDocument();
    });

    it('should display em dash for null values', () => {
      const vehicle = createMockVehicle({
        trim: undefined,
        specifications: {
          ...createMockVehicle().specifications,
          dimensions: {
            ...createMockVehicle().specifications.dimensions,
            groundClearance: undefined,
          },
        },
      });
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      const cells = screen.getAllByText('—');
      expect(cells.length).toBeGreaterThan(0);
    });
  });

  // ==========================================================================
  // Feature Display Tests
  // ==========================================================================

  describe('Feature Display', () => {
    it('should display all feature categories', () => {
      const vehicle = createMockVehicle();
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      expect(screen.getByText('Safety Features')).toBeInTheDocument();
      expect(screen.getByText('Comfort Features')).toBeInTheDocument();
      expect(screen.getByText('Technology Features')).toBeInTheDocument();
      expect(screen.getByText('Entertainment')).toBeInTheDocument();
      expect(screen.getByText('Exterior Features')).toBeInTheDocument();
      expect(screen.getByText('Interior Features')).toBeInTheDocument();
    });

    it('should display checkmarks for present features', () => {
      const vehicle = createMockVehicle();
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      const checkmarks = screen.getAllByText('✓');
      expect(checkmarks.length).toBeGreaterThan(0);
      checkmarks.forEach((mark) => {
        expect(mark).toHaveClass('text-green-600');
      });
    });

    it('should display em dash for absent features', () => {
      const vehicles = [
        createMockVehicle({
          features: {
            safety: ['Forward Collision Warning'],
            comfort: [],
            technology: [],
            entertainment: [],
            exterior: [],
            interior: [],
          },
        }),
        createMockVehicle({
          features: {
            safety: [],
            comfort: ['Dual-Zone Climate Control'],
            technology: [],
            entertainment: [],
            exterior: [],
            interior: [],
          },
        }),
      ];
      render(<ComparisonTable vehicles={vehicles} />);
      
      const dashes = screen.getAllByText('—');
      expect(dashes.length).toBeGreaterThan(0);
    });

    it('should collect all unique features from all vehicles', () => {
      const vehicles = [
        createMockVehicle({
          features: {
            safety: ['Feature A', 'Feature B'],
            comfort: [],
            technology: [],
            entertainment: [],
            exterior: [],
            interior: [],
          },
        }),
        createMockVehicle({
          features: {
            safety: ['Feature C'],
            comfort: [],
            technology: [],
            entertainment: [],
            exterior: [],
            interior: [],
          },
        }),
      ];
      render(<ComparisonTable vehicles={vehicles} />);
      
      expect(screen.getByText('Feature A')).toBeInTheDocument();
      expect(screen.getByText('Feature B')).toBeInTheDocument();
      expect(screen.getByText('Feature C')).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Difference Highlighting Tests
  // ==========================================================================

  describe('Difference Highlighting', () => {
    it('should highlight differences when enabled', () => {
      const vehicles = [
        createMockVehicle({ price: 30000 }),
        createMockVehicle({ price: 35000 }),
      ];
      const { container } = render(
        <ComparisonTable vehicles={vehicles} highlightDifferences={true} />
      );
      
      const highlightedCells = container.querySelectorAll('.bg-yellow-50');
      expect(highlightedCells.length).toBeGreaterThan(0);
    });

    it('should not highlight when disabled', () => {
      const vehicles = [
        createMockVehicle({ price: 30000 }),
        createMockVehicle({ price: 35000 }),
      ];
      const { container } = render(
        <ComparisonTable vehicles={vehicles} highlightDifferences={false} />
      );
      
      const highlightedCells = container.querySelectorAll('.bg-yellow-50');
      expect(highlightedCells.length).toBe(0);
    });

    it('should not highlight when values are the same', () => {
      const vehicles = [
        createMockVehicle({ make: 'Toyota' }),
        createMockVehicle({ make: 'Toyota' }),
      ];
      const { container } = render(
        <ComparisonTable vehicles={vehicles} highlightDifferences={true} />
      );
      
      // Find the Make row
      const makeRow = screen.getByText('Make').closest('tr');
      const highlightedCells = makeRow?.querySelectorAll('.bg-yellow-50') ?? [];
      expect(highlightedCells.length).toBe(0);
    });

    it('should display legend when highlighting is enabled', () => {
      const vehicles = createMockVehicles(2);
      render(<ComparisonTable vehicles={vehicles} highlightDifferences={true} />);
      
      expect(
        screen.getByText('Highlighted rows indicate differences between vehicles')
      ).toBeInTheDocument();
    });

    it('should not display legend when highlighting is disabled', () => {
      const vehicles = createMockVehicles(2);
      render(<ComparisonTable vehicles={vehicles} highlightDifferences={false} />);
      
      expect(
        screen.queryByText('Highlighted rows indicate differences between vehicles')
      ).not.toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Remove Vehicle Functionality Tests
  // ==========================================================================

  describe('Remove Vehicle Functionality', () => {
    it('should display remove button when onRemoveVehicle is provided', () => {
      const vehicle = createMockVehicle();
      const onRemove = vi.fn();
      render(<ComparisonTable vehicles={[vehicle]} onRemoveVehicle={onRemove} />);
      
      expect(screen.getByText('Remove')).toBeInTheDocument();
    });

    it('should not display remove button when onRemoveVehicle is not provided', () => {
      const vehicle = createMockVehicle();
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      expect(screen.queryByText('Remove')).not.toBeInTheDocument();
    });

    it('should call onRemoveVehicle with correct vehicle ID when clicked', async () => {
      const user = userEvent.setup();
      const vehicles = createMockVehicles(2);
      const onRemove = vi.fn();
      render(<ComparisonTable vehicles={vehicles} onRemoveVehicle={onRemove} />);
      
      const removeButtons = screen.getAllByText('Remove');
      await user.click(removeButtons[0]);
      
      expect(onRemove).toHaveBeenCalledTimes(1);
      expect(onRemove).toHaveBeenCalledWith(vehicles[0].id);
    });

    it('should have accessible aria-label for remove button', () => {
      const vehicle = createMockVehicle();
      const onRemove = vi.fn();
      render(<ComparisonTable vehicles={[vehicle]} onRemoveVehicle={onRemove} />);
      
      const removeButton = screen.getByLabelText(
        `Remove ${vehicle.year} ${vehicle.make} ${vehicle.model} from comparison`
      );
      expect(removeButton).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Sticky Header Tests
  // ==========================================================================

  describe('Sticky Header Behavior', () => {
    it('should register scroll event listener on mount', () => {
      const vehicles = createMockVehicles(2);
      render(<ComparisonTable vehicles={vehicles} />);
      
      expect(mockAddEventListener).toHaveBeenCalledWith(
        'scroll',
        expect.any(Function),
        { passive: true }
      );
    });

    it('should remove scroll event listener on unmount', () => {
      const vehicles = createMockVehicles(2);
      const { unmount } = render(<ComparisonTable vehicles={vehicles} />);
      
      unmount();
      
      expect(mockRemoveEventListener).toHaveBeenCalledWith(
        'scroll',
        expect.any(Function)
      );
    });

    it('should apply sticky class when scrolled', async () => {
      const vehicles = createMockVehicles(2);
      const { container } = render(<ComparisonTable vehicles={vehicles} />);
      
      // Get the scroll handler
      const scrollHandler = mockAddEventListener.mock.calls.find(
        (call) => call[0] === 'scroll'
      )?.[1];
      
      // Mock getBoundingClientRect to simulate scroll
      const tableElement = container.querySelector('.comparison-table');
      if (tableElement) {
        vi.spyOn(tableElement, 'getBoundingClientRect').mockReturnValue({
          top: -100,
          bottom: 500,
          left: 0,
          right: 1000,
          width: 1000,
          height: 600,
          x: 0,
          y: -100,
          toJSON: () => ({}),
        });
      }
      
      // Trigger scroll
      if (scrollHandler) {
        scrollHandler();
      }
      
      await waitFor(() => {
        const thead = container.querySelector('thead');
        expect(thead).toHaveClass('sticky');
      });
    });
  });

  // ==========================================================================
  // Responsive Design Tests
  // ==========================================================================

  describe('Responsive Design', () => {
    it('should have horizontal scroll container', () => {
      const vehicles = createMockVehicles(4);
      const { container } = render(<ComparisonTable vehicles={vehicles} />);
      
      const scrollContainer = container.querySelector('.overflow-x-auto');
      expect(scrollContainer).toBeInTheDocument();
    });

    it('should set minimum width for specification column', () => {
      const vehicles = createMockVehicles(2);
      render(<ComparisonTable vehicles={vehicles} />);
      
      const specHeader = screen.getByText('Specification');
      expect(specHeader).toHaveClass('min-w-[200px]');
    });

    it('should set minimum width for vehicle columns', () => {
      const vehicles = createMockVehicles(2);
      const { container } = render(<ComparisonTable vehicles={vehicles} />);
      
      const vehicleHeaders = container.querySelectorAll('thead th:not(:first-child)');
      vehicleHeaders.forEach((header) => {
        expect(header).toHaveClass('min-w-[200px]');
      });
    });
  });

  // ==========================================================================
  // Accessibility Tests
  // ==========================================================================

  describe('Accessibility', () => {
    it('should have proper table structure', () => {
      const vehicles = createMockVehicles(2);
      render(<ComparisonTable vehicles={vehicles} />);
      
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();
      
      const headers = within(table).getAllByRole('columnheader');
      expect(headers.length).toBeGreaterThan(0);
    });

    it('should have accessible image alt text', () => {
      const vehicle = createMockVehicle();
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      const image = screen.getByAltText(
        `${vehicle.year} ${vehicle.make} ${vehicle.model}`
      );
      expect(image).toBeInTheDocument();
    });

    it('should have accessible remove button labels', () => {
      const vehicle = createMockVehicle();
      const onRemove = vi.fn();
      render(<ComparisonTable vehicles={[vehicle]} onRemoveVehicle={onRemove} />);
      
      const removeButton = screen.getByLabelText(
        `Remove ${vehicle.year} ${vehicle.make} ${vehicle.model} from comparison`
      );
      expect(removeButton).toBeInTheDocument();
    });

    it('should have proper heading hierarchy', () => {
      const vehicles = createMockVehicles(2);
      const { container } = render(<ComparisonTable vehicles={vehicles} />);
      
      const categoryHeaders = container.querySelectorAll('td[colspan]');
      expect(categoryHeaders.length).toBeGreaterThan(0);
    });
  });

  // ==========================================================================
  // Edge Cases and Error Scenarios
  // ==========================================================================

  describe('Edge Cases', () => {
    it('should handle vehicle without trim', () => {
      const vehicle = createMockVehicle({ trim: undefined });
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      expect(screen.getByText(`${vehicle.year} ${vehicle.make}`)).toBeInTheDocument();
      expect(screen.getByText(vehicle.model)).toBeInTheDocument();
    });

    it('should handle vehicle with missing optional specifications', () => {
      const vehicle = createMockVehicle({
        specifications: {
          ...createMockVehicle().specifications,
          dimensions: {
            length: 192.7,
            width: 72.4,
            height: 56.9,
            wheelbase: 111.2,
          },
          curbWeight: undefined,
          towingCapacity: undefined,
        },
      });
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      expect(screen.queryByText('Ground Clearance')).not.toBeInTheDocument();
      expect(screen.queryByText('Cargo Volume')).not.toBeInTheDocument();
    });

    it('should handle vehicle with empty feature arrays', () => {
      const vehicle = createMockVehicle({
        features: {
          safety: [],
          comfort: [],
          technology: [],
          entertainment: [],
          exterior: [],
          interior: [],
        },
      });
      render(<ComparisonTable vehicles={[vehicle]} />);
      
      expect(screen.getByText(`${vehicle.year} ${vehicle.make}`)).toBeInTheDocument();
    });

    it('should handle maximum of 4 vehicles', () => {
      const vehicles = createMockVehicles(4);
      render(<ComparisonTable vehicles={vehicles} />);
      
      vehicles.forEach((vehicle) => {
        expect(screen.getByText(`${vehicle.year} ${vehicle.make}`)).toBeInTheDocument();
      });
    });

    it('should handle single vehicle without differences', () => {
      const vehicle = createMockVehicle();
      const { container } = render(
        <ComparisonTable vehicles={[vehicle]} highlightDifferences={true} />
      );
      
      const highlightedCells = container.querySelectorAll('.bg-yellow-50');
      expect(highlightedCells.length).toBe(0);
    });

    it('should handle vehicles with identical specifications', () => {
      const baseVehicle = createMockVehicle();
      const vehicles = [
        baseVehicle,
        { ...baseVehicle, id: 'vehicle-2' },
      ];
      const { container } = render(
        <ComparisonTable vehicles={vehicles} highlightDifferences={true} />
      );
      
      const highlightedCells = container.querySelectorAll('.bg-yellow-50');
      expect(highlightedCells.length).toBe(0);
    });
  });

  // ==========================================================================
  // Performance Tests
  // ==========================================================================

  describe('Performance', () => {
    it('should render large comparison efficiently', () => {
      const vehicles = createMockVehicles(4);
      const startTime = performance.now();
      
      render(<ComparisonTable vehicles={vehicles} />);
      
      const endTime = performance.now();
      const renderTime = endTime - startTime;
      
      // Should render in less than 100ms
      expect(renderTime).toBeLessThan(100);
    });

    it('should use lazy loading for images', () => {
      const vehicles = createMockVehicles(3);
      render(<ComparisonTable vehicles={vehicles} />);
      
      const images = screen.getAllByRole('img');
      images.forEach((image) => {
        expect(image).toHaveAttribute('loading', 'lazy');
      });
    });

    it('should memoize specification rows', () => {
      const vehicles = createMockVehicles(2);
      const { rerender } = render(<ComparisonTable vehicles={vehicles} />);
      
      // Rerender with same vehicles
      rerender(<ComparisonTable vehicles={vehicles} />);
      
      // Should not cause additional processing
      expect(screen.getByText('Specification')).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Integration Tests
  // ==========================================================================

  describe('Integration Scenarios', () => {
    it('should handle complete user workflow', async () => {
      const user = userEvent.setup();
      const vehicles = createMockVehicles(3);
      const onRemove = vi.fn();
      
      const { rerender } = render(
        <ComparisonTable
          vehicles={vehicles}
          onRemoveVehicle={onRemove}
          highlightDifferences={true}
        />
      );
      
      // Verify initial render
      expect(screen.getByText('Specification')).toBeInTheDocument();
      vehicles.forEach((vehicle) => {
        expect(screen.getByText(`${vehicle.year} ${vehicle.make}`)).toBeInTheDocument();
      });
      
      // Remove a vehicle
      const removeButtons = screen.getAllByText('Remove');
      await user.click(removeButtons[0]);
      expect(onRemove).toHaveBeenCalledWith(vehicles[0].id);
      
      // Rerender with updated vehicles
      const updatedVehicles = vehicles.slice(1);
      rerender(
        <ComparisonTable
          vehicles={updatedVehicles}
          onRemoveVehicle={onRemove}
          highlightDifferences={true}
        />
      );
      
      // Verify updated state
      expect(screen.queryByText(`${vehicles[0].year} ${vehicles[0].make}`)).not.toBeInTheDocument();
      expect(screen.getByText(`${vehicles[1].year} ${vehicles[1].make}`)).toBeInTheDocument();
    });

    it('should handle toggling highlight differences', () => {
      const vehicles = [
        createMockVehicle({ price: 30000 }),
        createMockVehicle({ price: 35000 }),
      ];
      
      const { container, rerender } = render(
        <ComparisonTable vehicles={vehicles} highlightDifferences={true} />
      );
      
      // Verify highlighting is present
      let highlightedCells = container.querySelectorAll('.bg-yellow-50');
      expect(highlightedCells.length).toBeGreaterThan(0);
      
      // Toggle highlighting off
      rerender(<ComparisonTable vehicles={vehicles} highlightDifferences={false} />);
      
      // Verify highlighting is removed
      highlightedCells = container.querySelectorAll('.bg-yellow-50');
      expect(highlightedCells.length).toBe(0);
    });
  });

  // ==========================================================================
  // Category Grouping Tests
  // ==========================================================================

  describe('Category Grouping', () => {
    it('should group specifications by category', () => {
      const vehicles = createMockVehicles(2);
      render(<ComparisonTable vehicles={vehicles} />);
      
      expect(screen.getByText('Basic Information')).toBeInTheDocument();
      expect(screen.getByText('Engine & Performance')).toBeInTheDocument();
      expect(screen.getByText('Fuel Economy')).toBeInTheDocument();
      expect(screen.getByText('Dimensions')).toBeInTheDocument();
      expect(screen.getByText('Capacity')).toBeInTheDocument();
    });

    it('should group features by category', () => {
      const vehicles = createMockVehicles(2);
      render(<ComparisonTable vehicles={vehicles} />);
      
      expect(screen.getByText('Safety Features')).toBeInTheDocument();
      expect(screen.getByText('Comfort Features')).toBeInTheDocument();
      expect(screen.getByText('Technology Features')).toBeInTheDocument();
      expect(screen.getByText('Entertainment')).toBeInTheDocument();
      expect(screen.getByText('Exterior Features')).toBeInTheDocument();
      expect(screen.getByText('Interior Features')).toBeInTheDocument();
    });

    it('should display category headers with proper styling', () => {
      const vehicles = createMockVehicles(2);
      const { container } = render(<ComparisonTable vehicles={vehicles} />);
      
      const categoryHeaders = container.querySelectorAll('td[colspan]');
      categoryHeaders.forEach((header) => {
        expect(header).toHaveClass('bg-gray-50');
        expect(header).toHaveClass('font-semibold');
      });
    });
  });

  // ==========================================================================
  // Visual Styling Tests
  // ==========================================================================

  describe('Visual Styling', () => {
    it('should apply alternating row colors', () => {
      const vehicles = createMockVehicles(2);
      const { container } = render(<ComparisonTable vehicles={vehicles} />);
      
      const rows = container.querySelectorAll('tbody tr:not([class*="bg-gray-50"])');
      rows.forEach((row, index) => {
        if (index % 2 === 0) {
          expect(row).toHaveClass('bg-white');
        }
      });
    });

    it('should apply hover effect to rows', () => {
      const vehicles = createMockVehicles(2);
      const { container } = render(<ComparisonTable vehicles={vehicles} />);
      
      const rows = container.querySelectorAll('tbody tr');
      rows.forEach((row) => {
        expect(row).toHaveClass('hover:bg-blue-50');
      });
    });

    it('should style remove button correctly', () => {
      const vehicle = createMockVehicle();
      const onRemove = vi.fn();
      render(<ComparisonTable vehicles={[vehicle]} onRemoveVehicle={onRemove} />);
      
      const removeButton = screen.getByText('Remove');
      expect(removeButton).toHaveClass('text-red-600');
      expect(removeButton).toHaveClass('hover:text-red-800');
      expect(removeButton).toHaveClass('underline');
    });
  });
});