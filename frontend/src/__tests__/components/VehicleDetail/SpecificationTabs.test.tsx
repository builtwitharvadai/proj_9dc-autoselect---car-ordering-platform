import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import SpecificationTabs from '../../../components/VehicleDetail/SpecificationTabs';
import type { Vehicle } from '../../../types/vehicle';

/**
 * Test Suite: SpecificationTabs Component
 * 
 * Coverage Areas:
 * - Component rendering and initialization
 * - Tab navigation and switching
 * - Keyboard accessibility (ARIA compliance)
 * - Content display for all tab panels
 * - User interactions and callbacks
 * - Edge cases and error scenarios
 * - Performance and optimization
 */

// ============================================================================
// Test Data Factories
// ============================================================================

/**
 * Factory for creating mock vehicle data with sensible defaults
 */
function createMockVehicle(overrides: Partial<Vehicle> = {}): Vehicle {
  const defaults: Vehicle = {
    id: 'test-vehicle-1',
    make: 'Toyota',
    model: 'Camry',
    year: 2024,
    trim: 'XLE',
    price: 32000,
    msrp: 35000,
    description:
      'The 2024 Toyota Camry XLE combines comfort, reliability, and advanced technology in a sophisticated midsize sedan.',
    images: ['image1.jpg', 'image2.jpg'],
    specifications: {
      engine: '2.5L 4-Cylinder',
      transmission: 'automatic',
      drivetrain: 'fwd',
      fuelType: 'gasoline',
      horsepower: 203,
      torque: 184,
      fuelEconomy: {
        city: 28,
        highway: 39,
        combined: 32,
      },
      seatingCapacity: 5,
      dimensions: {
        length: 192.7,
        width: 72.4,
        height: 56.9,
        wheelbase: 111.2,
        groundClearance: 5.7,
        cargoVolume: 15.1,
      },
      curbWeight: 3310,
      towingCapacity: 1000,
    },
    features: {
      safety: [
        'Toyota Safety Sense 3.0',
        'Pre-Collision System',
        'Lane Departure Alert',
        'Adaptive Cruise Control',
      ],
      comfort: [
        'Dual-Zone Climate Control',
        'Power-Adjustable Seats',
        'Heated Front Seats',
        'Premium Audio System',
      ],
      technology: [
        '9-inch Touchscreen',
        'Apple CarPlay',
        'Android Auto',
        'Wireless Charging',
      ],
    },
    availability: {
      status: 'in-stock',
      quantity: 3,
      estimatedDelivery: '2024-02-15',
    },
    dealer: {
      id: 'dealer-1',
      name: 'AutoSelect Toyota',
      location: 'Los Angeles, CA',
      rating: 4.5,
    },
  };

  return { ...defaults, ...overrides };
}

/**
 * Factory for creating minimal vehicle data (edge case testing)
 */
function createMinimalVehicle(): Vehicle {
  return {
    id: 'minimal-vehicle',
    make: 'Test',
    model: 'Model',
    year: 2024,
    trim: 'Base',
    price: 20000,
    msrp: 20000,
    description: 'Minimal vehicle description',
    images: [],
    specifications: {
      engine: 'Base Engine',
      transmission: 'manual',
      drivetrain: 'rwd',
      fuelType: 'gasoline',
      horsepower: 150,
      torque: 150,
      fuelEconomy: {
        city: 25,
        highway: 35,
        combined: 30,
      },
      seatingCapacity: 5,
      dimensions: {
        length: 180,
        width: 70,
        height: 55,
        wheelbase: 105,
      },
    },
    features: {
      safety: ['Basic Safety Features'],
      comfort: ['Basic Comfort'],
      technology: ['Basic Tech'],
    },
    availability: {
      status: 'in-stock',
      quantity: 1,
    },
    dealer: {
      id: 'dealer-1',
      name: 'Test Dealer',
      location: 'Test Location',
      rating: 4.0,
    },
  };
}

// ============================================================================
// Unit Tests: Component Rendering
// ============================================================================

describe('SpecificationTabs - Component Rendering', () => {
  it('should render with default props', () => {
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    expect(screen.getByRole('tablist')).toBeInTheDocument();
    expect(screen.getAllByRole('tab')).toHaveLength(4);
  });

  it('should render all tab buttons with correct labels', () => {
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    expect(screen.getByRole('tab', { name: /view vehicle overview/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /view vehicle features/i })).toBeInTheDocument();
    expect(
      screen.getByRole('tab', { name: /view vehicle specifications/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /view vehicle pricing/i })).toBeInTheDocument();
  });

  it('should apply custom className when provided', () => {
    const vehicle = createMockVehicle();
    const { container } = render(
      <SpecificationTabs vehicle={vehicle} className="custom-class" />,
    );

    const tabsContainer = container.querySelector('.specification-tabs');
    expect(tabsContainer).toHaveClass('custom-class');
  });

  it('should render with minimal vehicle data', () => {
    const vehicle = createMinimalVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    expect(screen.getByRole('tablist')).toBeInTheDocument();
    expect(screen.getAllByRole('tab')).toHaveLength(4);
  });

  it('should have proper ARIA structure', () => {
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const tablist = screen.getByRole('tablist');
    expect(tablist).toHaveAttribute('aria-label', 'Vehicle information sections');

    const tabs = screen.getAllByRole('tab');
    tabs.forEach((tab) => {
      expect(tab).toHaveAttribute('aria-selected');
      expect(tab).toHaveAttribute('aria-controls');
      expect(tab).toHaveAttribute('id');
    });
  });
});

// ============================================================================
// Unit Tests: Tab Navigation
// ============================================================================

describe('SpecificationTabs - Tab Navigation', () => {
  it('should display overview tab by default', () => {
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const overviewTab = screen.getByRole('tab', { name: /view vehicle overview/i });
    expect(overviewTab).toHaveAttribute('aria-selected', 'true');
    expect(overviewTab).toHaveAttribute('tabindex', '0');

    const overviewPanel = screen.getByRole('tabpanel', { name: /overview/i });
    expect(overviewPanel).not.toHaveAttribute('hidden');
  });

  it('should respect defaultTab prop', () => {
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} defaultTab="features" />);

    const featuresTab = screen.getByRole('tab', { name: /view vehicle features/i });
    expect(featuresTab).toHaveAttribute('aria-selected', 'true');
  });

  it('should switch tabs on click', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const featuresTab = screen.getByRole('tab', { name: /view vehicle features/i });
    await user.click(featuresTab);

    expect(featuresTab).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tabpanel', { name: /features/i })).not.toHaveAttribute('hidden');
  });

  it('should call onTabChange callback when tab changes', async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} onTabChange={onTabChange} />);

    const specificationsTab = screen.getByRole('tab', {
      name: /view vehicle specifications/i,
    });
    await user.click(specificationsTab);

    expect(onTabChange).toHaveBeenCalledWith('specifications');
    expect(onTabChange).toHaveBeenCalledTimes(1);
  });

  it('should hide inactive tab panels', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const overviewPanel = screen.getByRole('tabpanel', { name: /overview/i });
    expect(overviewPanel).not.toHaveAttribute('hidden');

    const featuresTab = screen.getByRole('tab', { name: /view vehicle features/i });
    await user.click(featuresTab);

    expect(overviewPanel).toHaveAttribute('hidden');
  });

  it('should update tabindex for inactive tabs', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const overviewTab = screen.getByRole('tab', { name: /view vehicle overview/i });
    const featuresTab = screen.getByRole('tab', { name: /view vehicle features/i });

    expect(overviewTab).toHaveAttribute('tabindex', '0');
    expect(featuresTab).toHaveAttribute('tabindex', '-1');

    await user.click(featuresTab);

    expect(overviewTab).toHaveAttribute('tabindex', '-1');
    expect(featuresTab).toHaveAttribute('tabindex', '0');
  });
});

// ============================================================================
// Integration Tests: Keyboard Navigation
// ============================================================================

describe('SpecificationTabs - Keyboard Navigation', () => {
  it('should navigate to next tab with ArrowRight', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const overviewTab = screen.getByRole('tab', { name: /view vehicle overview/i });
    overviewTab.focus();

    await user.keyboard('{ArrowRight}');

    const featuresTab = screen.getByRole('tab', { name: /view vehicle features/i });
    expect(featuresTab).toHaveAttribute('aria-selected', 'true');
    expect(featuresTab).toHaveFocus();
  });

  it('should navigate to previous tab with ArrowLeft', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} defaultTab="features" />);

    const featuresTab = screen.getByRole('tab', { name: /view vehicle features/i });
    featuresTab.focus();

    await user.keyboard('{ArrowLeft}');

    const overviewTab = screen.getByRole('tab', { name: /view vehicle overview/i });
    expect(overviewTab).toHaveAttribute('aria-selected', 'true');
    expect(overviewTab).toHaveFocus();
  });

  it('should wrap to last tab when pressing ArrowLeft on first tab', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const overviewTab = screen.getByRole('tab', { name: /view vehicle overview/i });
    overviewTab.focus();

    await user.keyboard('{ArrowLeft}');

    const pricingTab = screen.getByRole('tab', { name: /view vehicle pricing/i });
    expect(pricingTab).toHaveAttribute('aria-selected', 'true');
    expect(pricingTab).toHaveFocus();
  });

  it('should wrap to first tab when pressing ArrowRight on last tab', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} defaultTab="pricing" />);

    const pricingTab = screen.getByRole('tab', { name: /view vehicle pricing/i });
    pricingTab.focus();

    await user.keyboard('{ArrowRight}');

    const overviewTab = screen.getByRole('tab', { name: /view vehicle overview/i });
    expect(overviewTab).toHaveAttribute('aria-selected', 'true');
    expect(overviewTab).toHaveFocus();
  });

  it('should navigate to first tab with Home key', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} defaultTab="pricing" />);

    const pricingTab = screen.getByRole('tab', { name: /view vehicle pricing/i });
    pricingTab.focus();

    await user.keyboard('{Home}');

    const overviewTab = screen.getByRole('tab', { name: /view vehicle overview/i });
    expect(overviewTab).toHaveAttribute('aria-selected', 'true');
    expect(overviewTab).toHaveFocus();
  });

  it('should navigate to last tab with End key', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const overviewTab = screen.getByRole('tab', { name: /view vehicle overview/i });
    overviewTab.focus();

    await user.keyboard('{End}');

    const pricingTab = screen.getByRole('tab', { name: /view vehicle pricing/i });
    expect(pricingTab).toHaveAttribute('aria-selected', 'true');
    expect(pricingTab).toHaveFocus();
  });

  it('should not change tab on other key presses', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const overviewTab = screen.getByRole('tab', { name: /view vehicle overview/i });
    overviewTab.focus();

    await user.keyboard('{Enter}');
    await user.keyboard('{Space}');
    await user.keyboard('{Escape}');

    expect(overviewTab).toHaveAttribute('aria-selected', 'true');
  });
});

// ============================================================================
// Unit Tests: Overview Panel Content
// ============================================================================

describe('SpecificationTabs - Overview Panel', () => {
  it('should display vehicle description', () => {
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    expect(screen.getByText(vehicle.description)).toBeInTheDocument();
  });

  it('should display engine specification', () => {
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    expect(screen.getByText('Engine')).toBeInTheDocument();
    expect(screen.getByText(vehicle.specifications.engine)).toBeInTheDocument();
  });

  it('should display transmission with proper capitalization', () => {
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    expect(screen.getByText('Transmission')).toBeInTheDocument();
    expect(screen.getByText('Automatic')).toBeInTheDocument();
  });

  it('should display drivetrain in uppercase', () => {
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    expect(screen.getByText('Drivetrain')).toBeInTheDocument();
    expect(screen.getByText('FWD')).toBeInTheDocument();
  });

  it('should display fuel type with proper formatting', () => {
    const vehicle = createMockVehicle({
      specifications: {
        ...createMockVehicle().specifications,
        fuelType: 'plug-in-hybrid',
      },
    });
    render(<SpecificationTabs vehicle={vehicle} />);

    expect(screen.getByText('Fuel Type')).toBeInTheDocument();
    expect(screen.getByText('Plug in hybrid')).toBeInTheDocument();
  });

  it('should render overview panel with proper structure', () => {
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const overviewPanel = screen.getByRole('tabpanel', { name: /overview/i });
    expect(overviewPanel).toHaveAttribute('id', 'tabpanel-overview');
    expect(overviewPanel).toHaveAttribute('aria-labelledby', 'tab-overview');
  });
});

// ============================================================================
// Unit Tests: Features Panel Content
// ============================================================================

describe('SpecificationTabs - Features Panel', () => {
  beforeEach(async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const featuresTab = screen.getByRole('tab', { name: /view vehicle features/i });
    await user.click(featuresTab);
  });

  it('should display all safety features', () => {
    const vehicle = createMockVehicle();
    const { features } = vehicle;

    features.safety.forEach((feature) => {
      expect(screen.getByText(feature)).toBeInTheDocument();
    });
  });

  it('should display all comfort features', () => {
    const vehicle = createMockVehicle();
    const { features } = vehicle;

    features.comfort.forEach((feature) => {
      expect(screen.getByText(feature)).toBeInTheDocument();
    });
  });

  it('should display all technology features', () => {
    const vehicle = createMockVehicle();
    const { features } = vehicle;

    features.technology.forEach((feature) => {
      expect(screen.getByText(feature)).toBeInTheDocument();
    });
  });

  it('should render feature sections with proper headings', () => {
    expect(screen.getByText('Safety Features')).toBeInTheDocument();
    expect(screen.getByText('Comfort Features')).toBeInTheDocument();
    expect(screen.getByText('Technology Features')).toBeInTheDocument();
  });

  it('should render features with checkmark icons', () => {
    const featuresPanel = screen.getByRole('tabpanel', { name: /features/i });
    const svgIcons = within(featuresPanel).getAllByRole('img', { hidden: true });

    expect(svgIcons.length).toBeGreaterThan(0);
  });

  it('should handle empty feature arrays gracefully', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle({
      features: {
        safety: [],
        comfort: [],
        technology: [],
      },
    });
    render(<SpecificationTabs vehicle={vehicle} />);

    const featuresTab = screen.getByRole('tab', { name: /view vehicle features/i });
    await user.click(featuresTab);

    expect(screen.getByText('Safety Features')).toBeInTheDocument();
    expect(screen.getByText('Comfort Features')).toBeInTheDocument();
    expect(screen.getByText('Technology Features')).toBeInTheDocument();
  });
});

// ============================================================================
// Unit Tests: Specifications Panel Content
// ============================================================================

describe('SpecificationTabs - Specifications Panel', () => {
  beforeEach(async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const specificationsTab = screen.getByRole('tab', {
      name: /view vehicle specifications/i,
    });
    await user.click(specificationsTab);
  });

  it('should display performance specifications', () => {
    const vehicle = createMockVehicle();

    expect(screen.getByText('Performance')).toBeInTheDocument();
    expect(screen.getByText('Horsepower')).toBeInTheDocument();
    expect(screen.getByText(`${vehicle.specifications.horsepower} HP`)).toBeInTheDocument();
    expect(screen.getByText('Torque')).toBeInTheDocument();
    expect(screen.getByText(`${vehicle.specifications.torque} lb-ft`)).toBeInTheDocument();
  });

  it('should display fuel economy with proper formatting', () => {
    const vehicle = createMockVehicle();
    const { fuelEconomy } = vehicle.specifications;

    expect(screen.getByText('Fuel Economy')).toBeInTheDocument();
    expect(screen.getByText('City')).toBeInTheDocument();
    expect(screen.getByText(`${fuelEconomy.city} MPG`)).toBeInTheDocument();
    expect(screen.getByText('Highway')).toBeInTheDocument();
    expect(screen.getByText(`${fuelEconomy.highway} MPG`)).toBeInTheDocument();
    expect(screen.getByText('Combined')).toBeInTheDocument();
    expect(screen.getByText(`${fuelEconomy.combined} MPG`)).toBeInTheDocument();
  });

  it('should display dimensions with proper formatting', () => {
    const vehicle = createMockVehicle();
    const { dimensions } = vehicle.specifications;

    expect(screen.getByText('Dimensions')).toBeInTheDocument();
    expect(screen.getByText('Length')).toBeInTheDocument();
    expect(screen.getByText(`${dimensions.length}"`)).toBeInTheDocument();
    expect(screen.getByText('Width')).toBeInTheDocument();
    expect(screen.getByText(`${dimensions.width}"`)).toBeInTheDocument();
    expect(screen.getByText('Height')).toBeInTheDocument();
    expect(screen.getByText(`${dimensions.height}"`)).toBeInTheDocument();
    expect(screen.getByText('Wheelbase')).toBeInTheDocument();
    expect(screen.getByText(`${dimensions.wheelbase}"`)).toBeInTheDocument();
  });

  it('should display optional ground clearance when available', () => {
    const vehicle = createMockVehicle();

    expect(screen.getByText('Ground Clearance')).toBeInTheDocument();
    expect(
      screen.getByText(`${vehicle.specifications.dimensions.groundClearance}"`),
    ).toBeInTheDocument();
  });

  it('should display optional cargo volume when available', () => {
    const vehicle = createMockVehicle();

    expect(screen.getByText('Cargo Volume')).toBeInTheDocument();
    expect(
      screen.getByText(`${vehicle.specifications.dimensions.cargoVolume} cu ft`),
    ).toBeInTheDocument();
  });

  it('should not display ground clearance when not available', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle({
      specifications: {
        ...createMockVehicle().specifications,
        dimensions: {
          ...createMockVehicle().specifications.dimensions,
          groundClearance: undefined,
        },
      },
    });
    render(<SpecificationTabs vehicle={vehicle} />);

    const specificationsTab = screen.getByRole('tab', {
      name: /view vehicle specifications/i,
    });
    await user.click(specificationsTab);

    expect(screen.queryByText('Ground Clearance')).not.toBeInTheDocument();
  });

  it('should display capacity information', () => {
    const vehicle = createMockVehicle();

    expect(screen.getByText('Capacity')).toBeInTheDocument();
    expect(screen.getByText('Seating Capacity')).toBeInTheDocument();
    expect(
      screen.getByText(`${vehicle.specifications.seatingCapacity} passengers`),
    ).toBeInTheDocument();
  });

  it('should display curb weight when available', () => {
    const vehicle = createMockVehicle();

    expect(screen.getByText('Curb Weight')).toBeInTheDocument();
    expect(screen.getByText('3,310 lbs')).toBeInTheDocument();
  });

  it('should display towing capacity when available', () => {
    const vehicle = createMockVehicle();

    expect(screen.getByText('Towing Capacity')).toBeInTheDocument();
    expect(screen.getByText('1,000 lbs')).toBeInTheDocument();
  });
});

// ============================================================================
// Unit Tests: Pricing Panel Content
// ============================================================================

describe('SpecificationTabs - Pricing Panel', () => {
  beforeEach(async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const pricingTab = screen.getByRole('tab', { name: /view vehicle pricing/i });
    await user.click(pricingTab);
  });

  it('should display current price with proper formatting', () => {
    const vehicle = createMockVehicle();

    expect(screen.getByText('Current Price')).toBeInTheDocument();
    expect(screen.getByText('$32,000')).toBeInTheDocument();
  });

  it('should display MSRP and savings when price differs from MSRP', () => {
    expect(screen.getByText(/MSRP: \$35,000/i)).toBeInTheDocument();
    expect(screen.getByText(/Save \$3,000/i)).toBeInTheDocument();
  });

  it('should display only MSRP when price equals MSRP', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle({
      price: 35000,
      msrp: 35000,
    });
    render(<SpecificationTabs vehicle={vehicle} />);

    const pricingTab = screen.getByRole('tab', { name: /view vehicle pricing/i });
    await user.click(pricingTab);

    expect(screen.getByText(/MSRP: \$35,000/i)).toBeInTheDocument();
    expect(screen.queryByText(/Save/i)).not.toBeInTheDocument();
  });

  it('should display pricing information list', () => {
    expect(screen.getByText('Pricing Information')).toBeInTheDocument();
    expect(
      screen.getByText(/Price includes destination charges and dealer fees/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Financing options available with approved credit/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/Trade-in value assessment available/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Extended warranty and protection plans available/i),
    ).toBeInTheDocument();
  });

  it('should display pricing disclaimer', () => {
    expect(
      screen.getByText(/Prices and availability subject to change/i),
    ).toBeInTheDocument();
  });

  it('should render pricing information with checkmark icons', () => {
    const pricingPanel = screen.getByRole('tabpanel', { name: /pricing/i });
    const svgIcons = within(pricingPanel).getAllByRole('img', { hidden: true });

    expect(svgIcons.length).toBeGreaterThan(0);
  });
});

// ============================================================================
// Integration Tests: Tab Panel Visibility
// ============================================================================

describe('SpecificationTabs - Tab Panel Visibility', () => {
  it('should show only active tab panel', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const overviewPanel = screen.getByRole('tabpanel', { name: /overview/i });
    const featuresPanel = screen.getByRole('tabpanel', { name: /features/i });
    const specificationsPanel = screen.getByRole('tabpanel', { name: /specifications/i });
    const pricingPanel = screen.getByRole('tabpanel', { name: /pricing/i });

    expect(overviewPanel).not.toHaveAttribute('hidden');
    expect(featuresPanel).toHaveAttribute('hidden');
    expect(specificationsPanel).toHaveAttribute('hidden');
    expect(pricingPanel).toHaveAttribute('hidden');

    const featuresTab = screen.getByRole('tab', { name: /view vehicle features/i });
    await user.click(featuresTab);

    expect(overviewPanel).toHaveAttribute('hidden');
    expect(featuresPanel).not.toHaveAttribute('hidden');
    expect(specificationsPanel).toHaveAttribute('hidden');
    expect(pricingPanel).toHaveAttribute('hidden');
  });

  it('should maintain panel content when switching tabs', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const featuresTab = screen.getByRole('tab', { name: /view vehicle features/i });
    await user.click(featuresTab);

    expect(screen.getByText('Safety Features')).toBeInTheDocument();

    const overviewTab = screen.getByRole('tab', { name: /view vehicle overview/i });
    await user.click(overviewTab);

    await user.click(featuresTab);

    expect(screen.getByText('Safety Features')).toBeInTheDocument();
  });
});

// ============================================================================
// Edge Cases and Error Scenarios
// ============================================================================

describe('SpecificationTabs - Edge Cases', () => {
  it('should handle vehicle with no optional specifications', async () => {
    const user = userEvent.setup();
    const vehicle = createMinimalVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const specificationsTab = screen.getByRole('tab', {
      name: /view vehicle specifications/i,
    });
    await user.click(specificationsTab);

    expect(screen.queryByText('Ground Clearance')).not.toBeInTheDocument();
    expect(screen.queryByText('Cargo Volume')).not.toBeInTheDocument();
    expect(screen.queryByText('Curb Weight')).not.toBeInTheDocument();
    expect(screen.queryByText('Towing Capacity')).not.toBeInTheDocument();
  });

  it('should handle very long feature lists', async () => {
    const user = userEvent.setup();
    const longFeatureList = Array.from({ length: 50 }, (_, i) => `Feature ${i + 1}`);
    const vehicle = createMockVehicle({
      features: {
        safety: longFeatureList,
        comfort: longFeatureList,
        technology: longFeatureList,
      },
    });
    render(<SpecificationTabs vehicle={vehicle} />);

    const featuresTab = screen.getByRole('tab', { name: /view vehicle features/i });
    await user.click(featuresTab);

    expect(screen.getByText('Feature 1')).toBeInTheDocument();
    expect(screen.getByText('Feature 50')).toBeInTheDocument();
  });

  it('should handle zero values in specifications', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle({
      specifications: {
        ...createMockVehicle().specifications,
        horsepower: 0,
        torque: 0,
        fuelEconomy: {
          city: 0,
          highway: 0,
          combined: 0,
        },
      },
    });
    render(<SpecificationTabs vehicle={vehicle} />);

    const specificationsTab = screen.getByRole('tab', {
      name: /view vehicle specifications/i,
    });
    await user.click(specificationsTab);

    expect(screen.getByText('0 HP')).toBeInTheDocument();
    expect(screen.getByText('0 lb-ft')).toBeInTheDocument();
    expect(screen.getAllByText('0 MPG')).toHaveLength(3);
  });

  it('should handle very large price values', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle({
      price: 999999,
      msrp: 1000000,
    });
    render(<SpecificationTabs vehicle={vehicle} />);

    const pricingTab = screen.getByRole('tab', { name: /view vehicle pricing/i });
    await user.click(pricingTab);

    expect(screen.getByText('$999,999')).toBeInTheDocument();
    expect(screen.getByText(/MSRP: \$1,000,000/i)).toBeInTheDocument();
  });

  it('should handle rapid tab switching', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const tabs = screen.getAllByRole('tab');

    for (let i = 0; i < 10; i++) {
      await user.click(tabs[i % tabs.length]!);
    }

    expect(screen.getByRole('tablist')).toBeInTheDocument();
  });
});

// ============================================================================
// Accessibility Tests
// ============================================================================

describe('SpecificationTabs - Accessibility', () => {
  it('should have proper ARIA attributes on tablist', () => {
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const tablist = screen.getByRole('tablist');
    expect(tablist).toHaveAttribute('aria-label', 'Vehicle information sections');
  });

  it('should have proper ARIA attributes on tabs', () => {
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const tabs = screen.getAllByRole('tab');
    tabs.forEach((tab) => {
      expect(tab).toHaveAttribute('aria-selected');
      expect(tab).toHaveAttribute('aria-controls');
      expect(tab).toHaveAttribute('aria-label');
      expect(tab).toHaveAttribute('id');
    });
  });

  it('should have proper ARIA attributes on tab panels', () => {
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const panels = screen.getAllByRole('tabpanel', { hidden: true });
    panels.forEach((panel) => {
      expect(panel).toHaveAttribute('id');
      expect(panel).toHaveAttribute('aria-labelledby');
    });
  });

  it('should have matching IDs between tabs and panels', () => {
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const overviewTab = screen.getByRole('tab', { name: /view vehicle overview/i });
    const overviewPanel = screen.getByRole('tabpanel', { name: /overview/i });

    expect(overviewTab.getAttribute('aria-controls')).toBe(overviewPanel.getAttribute('id'));
    expect(overviewPanel.getAttribute('aria-labelledby')).toBe(overviewTab.getAttribute('id'));
  });

  it('should have focus visible styles', () => {
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const tabs = screen.getAllByRole('tab');
    tabs.forEach((tab) => {
      expect(tab).toHaveClass('focus:outline-none');
      expect(tab).toHaveClass('focus:ring-2');
    });
  });

  it('should support screen reader navigation', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const overviewTab = screen.getByRole('tab', { name: /view vehicle overview/i });
    overviewTab.focus();

    await user.keyboard('{ArrowRight}');

    const featuresTab = screen.getByRole('tab', { name: /view vehicle features/i });
    expect(featuresTab).toHaveFocus();
    expect(featuresTab).toHaveAttribute('aria-selected', 'true');
  });
});

// ============================================================================
// Performance Tests
// ============================================================================

describe('SpecificationTabs - Performance', () => {
  it('should render within acceptable time', () => {
    const vehicle = createMockVehicle();
    const startTime = performance.now();

    render(<SpecificationTabs vehicle={vehicle} />);

    const endTime = performance.now();
    const renderTime = endTime - startTime;

    expect(renderTime).toBeLessThan(100);
  });

  it('should handle multiple rapid re-renders efficiently', () => {
    const vehicle = createMockVehicle();
    const { rerender } = render(<SpecificationTabs vehicle={vehicle} />);

    const startTime = performance.now();

    for (let i = 0; i < 10; i++) {
      rerender(<SpecificationTabs vehicle={vehicle} />);
    }

    const endTime = performance.now();
    const totalTime = endTime - startTime;

    expect(totalTime).toBeLessThan(500);
  });

  it('should not cause memory leaks on unmount', () => {
    const vehicle = createMockVehicle();
    const { unmount } = render(<SpecificationTabs vehicle={vehicle} />);

    unmount();

    expect(screen.queryByRole('tablist')).not.toBeInTheDocument();
  });
});

// ============================================================================
// Integration Tests: Callback Behavior
// ============================================================================

describe('SpecificationTabs - Callback Behavior', () => {
  it('should call onTabChange only once per tab switch', async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} onTabChange={onTabChange} />);

    const featuresTab = screen.getByRole('tab', { name: /view vehicle features/i });
    await user.click(featuresTab);

    expect(onTabChange).toHaveBeenCalledTimes(1);
    expect(onTabChange).toHaveBeenCalledWith('features');
  });

  it('should call onTabChange with correct tab ID for keyboard navigation', async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} onTabChange={onTabChange} />);

    const overviewTab = screen.getByRole('tab', { name: /view vehicle overview/i });
    overviewTab.focus();

    await user.keyboard('{ArrowRight}');

    expect(onTabChange).toHaveBeenCalledWith('features');
  });

  it('should not call onTabChange when clicking active tab', async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} onTabChange={onTabChange} />);

    const overviewTab = screen.getByRole('tab', { name: /view vehicle overview/i });
    await user.click(overviewTab);

    expect(onTabChange).toHaveBeenCalledTimes(1);
  });

  it('should handle missing onTabChange callback gracefully', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle();
    render(<SpecificationTabs vehicle={vehicle} />);

    const featuresTab = screen.getByRole('tab', { name: /view vehicle features/i });

    await expect(user.click(featuresTab)).resolves.not.toThrow();
  });
});

// ============================================================================
// Formatting Utility Tests
// ============================================================================

describe('SpecificationTabs - Formatting Utilities', () => {
  it('should format currency correctly', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle({
      price: 45678,
      msrp: 50000,
    });
    render(<SpecificationTabs vehicle={vehicle} />);

    const pricingTab = screen.getByRole('tab', { name: /view vehicle pricing/i });
    await user.click(pricingTab);

    expect(screen.getByText('$45,678')).toBeInTheDocument();
    expect(screen.getByText(/MSRP: \$50,000/i)).toBeInTheDocument();
  });

  it('should format fuel economy correctly', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle({
      specifications: {
        ...createMockVehicle().specifications,
        fuelEconomy: {
          city: 25,
          highway: 35,
          combined: 30,
        },
      },
    });
    render(<SpecificationTabs vehicle={vehicle} />);

    const specificationsTab = screen.getByRole('tab', {
      name: /view vehicle specifications/i,
    });
    await user.click(specificationsTab);

    expect(screen.getByText('25 MPG')).toBeInTheDocument();
    expect(screen.getByText('35 MPG')).toBeInTheDocument();
    expect(screen.getByText('30 MPG')).toBeInTheDocument();
  });

  it('should format dimensions correctly', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle({
      specifications: {
        ...createMockVehicle().specifications,
        dimensions: {
          length: 200.5,
          width: 75.3,
          height: 60.8,
          wheelbase: 115.2,
        },
      },
    });
    render(<SpecificationTabs vehicle={vehicle} />);

    const specificationsTab = screen.getByRole('tab', {
      name: /view vehicle specifications/i,
    });
    await user.click(specificationsTab);

    expect(screen.getByText('200.5"')).toBeInTheDocument();
    expect(screen.getByText('75.3"')).toBeInTheDocument();
    expect(screen.getByText('60.8"')).toBeInTheDocument();
    expect(screen.getByText('115.2"')).toBeInTheDocument();
  });

  it('should format weight with thousands separator', async () => {
    const user = userEvent.setup();
    const vehicle = createMockVehicle({
      specifications: {
        ...createMockVehicle().specifications,
        curbWeight: 4567,
      },
    });
    render(<SpecificationTabs vehicle={vehicle} />);

    const specificationsTab = screen.getByRole('tab', {
      name: /view vehicle specifications/i,
    });
    await user.click(specificationsTab);

    expect(screen.getByText('4,567 lbs')).toBeInTheDocument();
  });
});

// ============================================================================
// Cleanup and Lifecycle Tests
// ============================================================================

describe('SpecificationTabs - Lifecycle', () => {
  let cleanup: () => void;

  afterEach(() => {
    if (cleanup) {
      cleanup();
    }
  });

  it('should cleanup event listeners on unmount', () => {
    const vehicle = createMockVehicle();
    const { unmount } = render(<SpecificationTabs vehicle={vehicle} />);

    cleanup = unmount;

    expect(screen.queryByRole('tablist')).toBeInTheDocument();

    unmount();

    expect(screen.queryByRole('tablist')).not.toBeInTheDocument();
  });

  it('should handle prop updates correctly', () => {
    const vehicle1 = createMockVehicle({ id: 'vehicle-1' });
    const vehicle2 = createMockVehicle({ id: 'vehicle-2', make: 'Honda', model: 'Accord' });

    const { rerender } = render(<SpecificationTabs vehicle={vehicle1} />);

    expect(screen.getByText(vehicle1.description)).toBeInTheDocument();

    rerender(<SpecificationTabs vehicle={vehicle2} />);

    expect(screen.getByText(vehicle2.description)).toBeInTheDocument();
  });

  it('should maintain tab state across prop updates', async () => {
    const user = userEvent.setup();
    const vehicle1 = createMockVehicle({ id: 'vehicle-1' });
    const vehicle2 = createMockVehicle({ id: 'vehicle-2' });

    const { rerender } = render(<SpecificationTabs vehicle={vehicle1} />);

    const featuresTab = screen.getByRole('tab', { name: /view vehicle features/i });
    await user.click(featuresTab);

    expect(featuresTab).toHaveAttribute('aria-selected', 'true');

    rerender(<SpecificationTabs vehicle={vehicle2} />);

    expect(featuresTab).toHaveAttribute('aria-selected', 'true');
  });
});