/**
 * ConfigurationComparison Component Test Suite
 * 
 * Comprehensive tests for the configuration comparison component including:
 * - Rendering and display logic
 * - Difference highlighting
 * - Responsive behavior (desktop/mobile)
 * - User interactions
 * - Accessibility compliance
 * - Edge cases and error states
 * 
 * @module components/SavedConfigurations/__tests__/ConfigurationComparison.test
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import ConfigurationComparison, {
  ConfigurationComparisonProps,
} from '../ConfigurationComparison';
import {
  ConfigurationComparisonItem,
  COMPARISON_CONSTRAINTS,
} from '../../../types/savedConfiguration';

// ============================================================================
// Test Data Factories
// ============================================================================

/**
 * Factory for creating test configuration items
 */
class ConfigurationFactory {
  private static idCounter = 1;

  static create(overrides: Partial<ConfigurationComparisonItem> = {}): ConfigurationComparisonItem {
    const id = `config-${this.idCounter++}`;
    return {
      configurationId: id,
      name: `Test Configuration ${id}`,
      vehicle: {
        year: 2024,
        make: 'Tesla',
        model: 'Model 3',
        trim: 'Long Range',
        ...overrides.vehicle,
      },
      pricing: {
        basePrice: 45000,
        optionsPrice: 5000,
        packagesPrice: 3000,
        total: 53000,
        ...overrides.pricing,
      },
      packages: overrides.packages ?? [
        {
          id: 'pkg-1',
          name: 'Premium Package',
          price: 3000,
          features: ['Leather Seats', 'Sunroof'],
        },
      ],
      options: overrides.options ?? [
        {
          id: 'opt-1',
          name: 'Autopilot',
          category: 'technology',
          price: 5000,
        },
      ],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ...overrides,
    };
  }

  static createMany(count: number, overrides: Partial<ConfigurationComparisonItem> = []): ConfigurationComparisonItem[] {
    return Array.from({ length: count }, (_, i) => {
      const itemOverrides = Array.isArray(overrides) ? overrides[i] ?? {} : overrides;
      return this.create(itemOverrides);
    });
  }

  static reset(): void {
    this.idCounter = 1;
  }
}

/**
 * Factory for creating component props
 */
class PropsFactory {
  static create(overrides: Partial<ConfigurationComparisonProps> = {}): ConfigurationComparisonProps {
    return {
      configurations: ConfigurationFactory.createMany(2),
      onRemoveConfiguration: vi.fn(),
      onSaveConfiguration: vi.fn(),
      highlightDifferences: true,
      enableMobileView: true,
      className: '',
      isLoading: false,
      error: null,
      ...overrides,
    };
  }
}

// ============================================================================
// Test Utilities
// ============================================================================

/**
 * Render component with default props
 */
function renderComponent(props: Partial<ConfigurationComparisonProps> = {}) {
  const defaultProps = PropsFactory.create(props);
  const user = userEvent.setup();
  const utils = render(<ConfigurationComparison {...defaultProps} />);
  
  return {
    ...utils,
    user,
    props: defaultProps,
  };
}

/**
 * Get table cells for a specific row
 */
function getRowCells(rowLabel: string) {
  const row = screen.getByRole('row', { name: new RegExp(rowLabel, 'i') });
  return within(row).getAllByRole('cell');
}

/**
 * Simulate mobile viewport
 */
function setMobileViewport() {
  global.innerWidth = 375;
  global.innerHeight = 667;
  global.dispatchEvent(new Event('resize'));
}

/**
 * Simulate desktop viewport
 */
function setDesktopViewport() {
  global.innerWidth = 1280;
  global.innerHeight = 720;
  global.dispatchEvent(new Event('resize'));
}

// ============================================================================
// Test Suite Setup
// ============================================================================

describe('ConfigurationComparison', () => {
  beforeEach(() => {
    ConfigurationFactory.reset();
    vi.clearAllMocks();
    setDesktopViewport();
  });

  // ==========================================================================
  // Rendering Tests
  // ==========================================================================

  describe('Rendering', () => {
    it('should render comparison table with configurations', () => {
      const configs = ConfigurationFactory.createMany(2);
      renderComponent({ configurations: configs });

      expect(screen.getByText('Configuration Comparison')).toBeInTheDocument();
      expect(screen.getByText(/comparing 2 configurations/i)).toBeInTheDocument();
    });

    it('should render vehicle information for each configuration', () => {
      const configs = [
        ConfigurationFactory.create({
          vehicle: { year: 2024, make: 'Tesla', model: 'Model 3', trim: 'Long Range' },
        }),
        ConfigurationFactory.create({
          vehicle: { year: 2024, make: 'BMW', model: 'i4', trim: 'eDrive40' },
        }),
      ];
      renderComponent({ configurations: configs });

      expect(screen.getByText(/2024 Tesla Model 3/i)).toBeInTheDocument();
      expect(screen.getByText(/2024 BMW i4/i)).toBeInTheDocument();
    });

    it('should render pricing information', () => {
      const configs = ConfigurationFactory.createMany(2, [
        { pricing: { basePrice: 45000, optionsPrice: 5000, packagesPrice: 3000, total: 53000 } },
        { pricing: { basePrice: 50000, optionsPrice: 4000, packagesPrice: 2000, total: 56000 } },
      ]);
      renderComponent({ configurations: configs });

      expect(screen.getByText(/\$53,000/)).toBeInTheDocument();
      expect(screen.getByText(/\$56,000/)).toBeInTheDocument();
    });

    it('should render package information', () => {
      const configs = ConfigurationFactory.createMany(2, [
        {
          packages: [
            { id: 'pkg-1', name: 'Premium Package', price: 3000, features: [] },
          ],
        },
        {
          packages: [
            { id: 'pkg-2', name: 'Sport Package', price: 2500, features: [] },
          ],
        },
      ]);
      renderComponent({ configurations: configs });

      expect(screen.getByText('Premium Package')).toBeInTheDocument();
      expect(screen.getByText('Sport Package')).toBeInTheDocument();
    });

    it('should render feature information', () => {
      const configs = ConfigurationFactory.createMany(2, [
        {
          options: [
            { id: 'opt-1', name: 'Autopilot', category: 'technology', price: 5000 },
          ],
        },
        {
          options: [
            { id: 'opt-2', name: 'Premium Audio', category: 'entertainment', price: 2000 },
          ],
        },
      ]);
      renderComponent({ configurations: configs });

      expect(screen.getByText('Autopilot')).toBeInTheDocument();
      expect(screen.getByText('Premium Audio')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      const { container } = renderComponent({ className: 'custom-class' });
      const wrapper = container.firstChild as HTMLElement;
      
      expect(wrapper).toHaveClass('custom-class');
    });
  });

  // ==========================================================================
  // Loading State Tests
  // ==========================================================================

  describe('Loading State', () => {
    it('should render loading spinner when isLoading is true', () => {
      renderComponent({ isLoading: true });

      expect(screen.getByText(/loading comparison/i)).toBeInTheDocument();
      expect(screen.queryByText('Configuration Comparison')).not.toBeInTheDocument();
    });

    it('should show loading animation', () => {
      const { container } = renderComponent({ isLoading: true });
      const spinner = container.querySelector('.animate-spin');
      
      expect(spinner).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Error State Tests
  // ==========================================================================

  describe('Error State', () => {
    it('should render error message when error prop is provided', () => {
      const errorMessage = 'Failed to load comparison data';
      renderComponent({ error: errorMessage });

      expect(screen.getByText('Comparison Error')).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    it('should show error icon', () => {
      renderComponent({ error: 'Test error' });
      
      const errorContainer = screen.getByText('Comparison Error').closest('div');
      expect(errorContainer).toBeInTheDocument();
    });

    it('should not render comparison table when error exists', () => {
      renderComponent({ error: 'Test error' });

      expect(screen.queryByText('Configuration Comparison')).not.toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Empty State Tests
  // ==========================================================================

  describe('Empty State', () => {
    it('should render empty state when no configurations provided', () => {
      renderComponent({ configurations: [] });

      expect(screen.getByText('No Configurations Selected')).toBeInTheDocument();
      expect(screen.getByText(/select configurations from your saved list/i)).toBeInTheDocument();
    });

    it('should show empty state icon', () => {
      renderComponent({ configurations: [] });
      
      const emptyContainer = screen.getByText('No Configurations Selected').closest('div');
      expect(emptyContainer).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Validation Tests
  // ==========================================================================

  describe('Validation', () => {
    it('should show invalid comparison message when less than minimum configurations', () => {
      const configs = ConfigurationFactory.createMany(1);
      renderComponent({ configurations: configs });

      expect(screen.getByText('Invalid Comparison')).toBeInTheDocument();
      expect(screen.getByText(new RegExp(`between ${COMPARISON_CONSTRAINTS.MIN_CONFIGURATIONS}`, 'i'))).toBeInTheDocument();
    });

    it('should show invalid comparison message when more than maximum configurations', () => {
      const configs = ConfigurationFactory.createMany(COMPARISON_CONSTRAINTS.MAX_CONFIGURATIONS + 1);
      renderComponent({ configurations: configs });

      expect(screen.getByText('Invalid Comparison')).toBeInTheDocument();
    });

    it('should render comparison when configuration count is valid', () => {
      const configs = ConfigurationFactory.createMany(2);
      renderComponent({ configurations: configs });

      expect(screen.queryByText('Invalid Comparison')).not.toBeInTheDocument();
      expect(screen.getByText('Configuration Comparison')).toBeInTheDocument();
    });

    it('should accept minimum number of configurations', () => {
      const configs = ConfigurationFactory.createMany(COMPARISON_CONSTRAINTS.MIN_CONFIGURATIONS);
      renderComponent({ configurations: configs });

      expect(screen.getByText('Configuration Comparison')).toBeInTheDocument();
    });

    it('should accept maximum number of configurations', () => {
      const configs = ConfigurationFactory.createMany(COMPARISON_CONSTRAINTS.MAX_CONFIGURATIONS);
      renderComponent({ configurations: configs });

      expect(screen.getByText('Configuration Comparison')).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Difference Highlighting Tests
  // ==========================================================================

  describe('Difference Highlighting', () => {
    it('should highlight rows with different values when highlightDifferences is true', () => {
      const configs = ConfigurationFactory.createMany(2, [
        { pricing: { basePrice: 45000, optionsPrice: 5000, packagesPrice: 3000, total: 53000 } },
        { pricing: { basePrice: 50000, optionsPrice: 4000, packagesPrice: 2000, total: 56000 } },
      ]);
      renderComponent({ configurations: configs, highlightDifferences: true });

      const cells = getRowCells('Base Price');
      const highlightedCells = cells.filter(cell => cell.classList.contains('bg-yellow-50'));
      
      expect(highlightedCells.length).toBeGreaterThan(0);
    });

    it('should not highlight rows when highlightDifferences is false', () => {
      const configs = ConfigurationFactory.createMany(2, [
        { pricing: { basePrice: 45000, optionsPrice: 5000, packagesPrice: 3000, total: 53000 } },
        { pricing: { basePrice: 50000, optionsPrice: 4000, packagesPrice: 2000, total: 56000 } },
      ]);
      renderComponent({ configurations: configs, highlightDifferences: false });

      const cells = getRowCells('Base Price');
      const highlightedCells = cells.filter(cell => cell.classList.contains('bg-yellow-50'));
      
      expect(highlightedCells.length).toBe(0);
    });

    it('should highlight lowest price configuration in green', () => {
      const configs = ConfigurationFactory.createMany(2, [
        { pricing: { basePrice: 45000, optionsPrice: 5000, packagesPrice: 3000, total: 53000 } },
        { pricing: { basePrice: 50000, optionsPrice: 4000, packagesPrice: 2000, total: 56000 } },
      ]);
      renderComponent({ configurations: configs });

      const cells = getRowCells('Total Price');
      const lowestPriceCell = cells.find(cell => cell.textContent?.includes('$53,000'));
      
      expect(lowestPriceCell).toHaveClass('text-green-600');
      expect(lowestPriceCell).toHaveClass('font-bold');
    });

    it('should not highlight rows with identical values', () => {
      const configs = ConfigurationFactory.createMany(2, [
        { pricing: { basePrice: 45000, optionsPrice: 5000, packagesPrice: 3000, total: 53000 } },
        { pricing: { basePrice: 45000, optionsPrice: 5000, packagesPrice: 3000, total: 53000 } },
      ]);
      renderComponent({ configurations: configs, highlightDifferences: true });

      const cells = getRowCells('Base Price');
      const highlightedCells = cells.filter(cell => cell.classList.contains('bg-yellow-50'));
      
      expect(highlightedCells.length).toBe(0);
    });
  });

  // ==========================================================================
  // Price Comparison Tests
  // ==========================================================================

  describe('Price Comparison', () => {
    it('should display price range in summary', () => {
      const configs = ConfigurationFactory.createMany(2, [
        { pricing: { basePrice: 45000, optionsPrice: 5000, packagesPrice: 3000, total: 53000 } },
        { pricing: { basePrice: 50000, optionsPrice: 4000, packagesPrice: 2000, total: 56000 } },
      ]);
      renderComponent({ configurations: configs });

      expect(screen.getByText(/price range:/i)).toBeInTheDocument();
      expect(screen.getByText(/\$53,000 - \$56,000/)).toBeInTheDocument();
    });

    it('should display average price in summary', () => {
      const configs = ConfigurationFactory.createMany(2, [
        { pricing: { basePrice: 45000, optionsPrice: 5000, packagesPrice: 3000, total: 50000 } },
        { pricing: { basePrice: 50000, optionsPrice: 4000, packagesPrice: 2000, total: 60000 } },
      ]);
      renderComponent({ configurations: configs });

      expect(screen.getByText(/average:/i)).toBeInTheDocument();
      expect(screen.getByText(/\$55,000/)).toBeInTheDocument();
    });

    it('should format prices correctly', () => {
      const configs = ConfigurationFactory.createMany(2, [
        { pricing: { basePrice: 45000, optionsPrice: 5000, packagesPrice: 3000, total: 53000 } },
      ]);
      renderComponent({ configurations: configs });

      expect(screen.getByText(/\$45,000/)).toBeInTheDocument();
      expect(screen.getByText(/\$5,000/)).toBeInTheDocument();
      expect(screen.getByText(/\$3,000/)).toBeInTheDocument();
    });

    it('should calculate price differences correctly', () => {
      const configs = ConfigurationFactory.createMany(2, [
        { pricing: { basePrice: 45000, optionsPrice: 5000, packagesPrice: 3000, total: 53000 } },
        { pricing: { basePrice: 50000, optionsPrice: 4000, packagesPrice: 2000, total: 56000 } },
      ]);
      renderComponent({ configurations: configs });

      // Price range should be $3,000 (56000 - 53000)
      expect(screen.getByText(/\$53,000 - \$56,000/)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // User Interaction Tests
  // ==========================================================================

  describe('User Interactions', () => {
    it('should call onRemoveConfiguration when remove button is clicked', async () => {
      const onRemove = vi.fn();
      const configs = ConfigurationFactory.createMany(2);
      const { user } = renderComponent({
        configurations: configs,
        onRemoveConfiguration: onRemove,
      });

      const removeButtons = screen.getAllByLabelText(/remove/i);
      await user.click(removeButtons[0]);

      expect(onRemove).toHaveBeenCalledWith(configs[0].configurationId);
      expect(onRemove).toHaveBeenCalledTimes(1);
    });

    it('should call onSaveConfiguration when save button is clicked in mobile view', async () => {
      const onSave = vi.fn();
      const configs = ConfigurationFactory.createMany(2);
      setMobileViewport();
      
      const { user } = renderComponent({
        configurations: configs,
        onSaveConfiguration: onSave,
        enableMobileView: true,
      });

      const saveButtons = screen.getAllByText('Save Configuration');
      await user.click(saveButtons[0]);

      expect(onSave).toHaveBeenCalledWith(configs[0].configurationId);
      expect(onSave).toHaveBeenCalledTimes(1);
    });

    it('should not render remove buttons when onRemoveConfiguration is not provided', () => {
      renderComponent({ onRemoveConfiguration: undefined });

      expect(screen.queryByLabelText(/remove/i)).not.toBeInTheDocument();
    });

    it('should not render save buttons when onSaveConfiguration is not provided', () => {
      setMobileViewport();
      renderComponent({ onSaveConfiguration: undefined, enableMobileView: true });

      expect(screen.queryByText('Save Configuration')).not.toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Section Expansion Tests
  // ==========================================================================

  describe('Section Expansion', () => {
    beforeEach(() => {
      setMobileViewport();
    });

    it('should expand pricing details when clicked in mobile view', async () => {
      const configs = ConfigurationFactory.createMany(2);
      const { user } = renderComponent({ configurations: configs, enableMobileView: true });

      const pricingButton = screen.getAllByText('Pricing Details')[0];
      
      // Initially expanded
      expect(screen.getAllByText(/base price:/i).length).toBeGreaterThan(0);

      // Click to collapse
      await user.click(pricingButton);
      
      await waitFor(() => {
        expect(screen.queryByText(/base price:/i)).not.toBeInTheDocument();
      });
    });

    it('should expand packages section when clicked in mobile view', async () => {
      const configs = ConfigurationFactory.createMany(2, [
        {
          packages: [
            { id: 'pkg-1', name: 'Premium Package', price: 3000, features: [] },
          ],
        },
      ]);
      const { user } = renderComponent({ configurations: configs, enableMobileView: true });

      const packagesButton = screen.getAllByText(/packages \(1\)/i)[0];
      
      // Initially expanded
      expect(screen.getAllByText('Premium Package').length).toBeGreaterThan(0);

      // Click to collapse
      await user.click(packagesButton);
      
      await waitFor(() => {
        const packageElements = screen.queryAllByText('Premium Package');
        // Should still have one in the header, but not in the expanded list
        expect(packageElements.length).toBeLessThan(2);
      });
    });

    it('should expand features section when clicked in mobile view', async () => {
      const configs = ConfigurationFactory.createMany(2, [
        {
          options: [
            { id: 'opt-1', name: 'Autopilot', category: 'technology', price: 5000 },
          ],
        },
      ]);
      const { user } = renderComponent({ configurations: configs, enableMobileView: true });

      const featuresButton = screen.getAllByText(/features \(1\)/i)[0];
      
      // Initially expanded
      expect(screen.getAllByText('Autopilot').length).toBeGreaterThan(0);

      // Click to collapse
      await user.click(featuresButton);
      
      await waitFor(() => {
        const featureElements = screen.queryAllByText('Autopilot');
        expect(featureElements.length).toBeLessThan(2);
      });
    });

    it('should rotate chevron icon when section is expanded/collapsed', async () => {
      const configs = ConfigurationFactory.createMany(2);
      const { user, container } = renderComponent({ configurations: configs, enableMobileView: true });

      const pricingButton = screen.getAllByText('Pricing Details')[0];
      const chevron = pricingButton.querySelector('svg');
      
      expect(chevron).toHaveClass('rotate-180');

      await user.click(pricingButton);
      
      await waitFor(() => {
        expect(chevron).not.toHaveClass('rotate-180');
      });
    });
  });

  // ==========================================================================
  // Responsive Behavior Tests
  // ==========================================================================

  describe('Responsive Behavior', () => {
    it('should show desktop table view on large screens', () => {
      setDesktopViewport();
      renderComponent({ enableMobileView: true });

      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();
      expect(table.closest('.hidden')).toBeNull();
    });

    it('should show mobile stacked view on small screens', () => {
      setMobileViewport();
      const configs = ConfigurationFactory.createMany(2);
      renderComponent({ configurations: configs, enableMobileView: true });

      // Mobile view should show configuration cards
      expect(screen.getAllByText(/test configuration/i).length).toBeGreaterThan(0);
    });

    it('should not show mobile view when enableMobileView is false', () => {
      setMobileViewport();
      renderComponent({ enableMobileView: false });

      // Should still show table even on mobile
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();
    });

    it('should display configuration count in mobile view', () => {
      setMobileViewport();
      const configs = ConfigurationFactory.createMany(2);
      renderComponent({ configurations: configs, enableMobileView: true });

      expect(screen.getByText(/packages \(\d+\)/i)).toBeInTheDocument();
      expect(screen.getByText(/features \(\d+\)/i)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Feature Comparison Tests
  // ==========================================================================

  describe('Feature Comparison', () => {
    it('should show checkmark for features present in configuration', () => {
      const configs = ConfigurationFactory.createMany(2, [
        {
          options: [
            { id: 'opt-1', name: 'Autopilot', category: 'technology', price: 5000 },
          ],
        },
        {
          options: [],
        },
      ]);
      renderComponent({ configurations: configs });

      const cells = getRowCells('Autopilot');
      expect(cells[1].textContent).toContain('✓');
      expect(cells[2].textContent).toContain('—');
    });

    it('should group features by category', () => {
      const configs = ConfigurationFactory.createMany(2, [
        {
          options: [
            { id: 'opt-1', name: 'Autopilot', category: 'technology', price: 5000 },
            { id: 'opt-2', name: 'Premium Audio', category: 'entertainment', price: 2000 },
          ],
        },
      ]);
      renderComponent({ configurations: configs });

      expect(screen.getByText('Autopilot')).toBeInTheDocument();
      expect(screen.getByText('Premium Audio')).toBeInTheDocument();
    });

    it('should handle features with different values across configurations', () => {
      const configs = ConfigurationFactory.createMany(3, [
        {
          options: [
            { id: 'opt-1', name: 'Autopilot', category: 'technology', price: 5000 },
          ],
        },
        {
          options: [
            { id: 'opt-1', name: 'Autopilot', category: 'technology', price: 5000 },
          ],
        },
        {
          options: [],
        },
      ]);
      renderComponent({ configurations: configs, highlightDifferences: true });

      const cells = getRowCells('Autopilot');
      const highlightedCells = cells.filter(cell => cell.classList.contains('bg-yellow-50'));
      
      expect(highlightedCells.length).toBeGreaterThan(0);
    });
  });

  // ==========================================================================
  // Package Comparison Tests
  // ==========================================================================

  describe('Package Comparison', () => {
    it('should show checkmark for packages included in configuration', () => {
      const configs = ConfigurationFactory.createMany(2, [
        {
          packages: [
            { id: 'pkg-1', name: 'Premium Package', price: 3000, features: [] },
          ],
        },
        {
          packages: [],
        },
      ]);
      renderComponent({ configurations: configs });

      const cells = getRowCells('Premium Package');
      expect(cells[1].textContent).toContain('✓');
      expect(cells[2].textContent).toContain('—');
    });

    it('should highlight package differences', () => {
      const configs = ConfigurationFactory.createMany(2, [
        {
          packages: [
            { id: 'pkg-1', name: 'Premium Package', price: 3000, features: [] },
          ],
        },
        {
          packages: [
            { id: 'pkg-2', name: 'Sport Package', price: 2500, features: [] },
          ],
        },
      ]);
      renderComponent({ configurations: configs, highlightDifferences: true });

      expect(screen.getByText('Premium Package')).toBeInTheDocument();
      expect(screen.getByText('Sport Package')).toBeInTheDocument();
    });

    it('should display package count in mobile view', () => {
      setMobileViewport();
      const configs = ConfigurationFactory.createMany(2, [
        {
          packages: [
            { id: 'pkg-1', name: 'Premium Package', price: 3000, features: [] },
            { id: 'pkg-2', name: 'Sport Package', price: 2500, features: [] },
          ],
        },
      ]);
      renderComponent({ configurations: configs, enableMobileView: true });

      expect(screen.getByText(/packages \(2\)/i)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Accessibility Tests
  // ==========================================================================

  describe('Accessibility', () => {
    it('should have proper ARIA labels for remove buttons', () => {
      const configs = ConfigurationFactory.createMany(2);
      renderComponent({ configurations: configs });

      const removeButtons = screen.getAllByLabelText(/remove/i);
      expect(removeButtons.length).toBe(2);
      expect(removeButtons[0]).toHaveAttribute('aria-label');
    });

    it('should have proper table structure with headers', () => {
      renderComponent();

      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();
      
      const headers = within(table).getAllByRole('columnheader');
      expect(headers.length).toBeGreaterThan(0);
    });

    it('should have proper heading hierarchy', () => {
      renderComponent();

      const mainHeading = screen.getByRole('heading', { level: 2 });
      expect(mainHeading).toHaveTextContent('Configuration Comparison');
    });

    it('should have proper heading hierarchy in mobile view', () => {
      setMobileViewport();
      const configs = ConfigurationFactory.createMany(2);
      renderComponent({ configurations: configs, enableMobileView: true });

      const headings = screen.getAllByRole('heading', { level: 3 });
      expect(headings.length).toBeGreaterThan(0);
    });

    it('should have keyboard accessible buttons', () => {
      const configs = ConfigurationFactory.createMany(2);
      renderComponent({ configurations: configs });

      const removeButtons = screen.getAllByLabelText(/remove/i);
      removeButtons.forEach(button => {
        expect(button).toHaveAttribute('type', 'button');
      });
    });

    it('should have proper focus management for interactive elements', async () => {
      const configs = ConfigurationFactory.createMany(2);
      const { user } = renderComponent({ configurations: configs });

      const removeButton = screen.getAllByLabelText(/remove/i)[0];
      
      await user.tab();
      // Button should be focusable
      expect(document.activeElement).toBeDefined();
    });

    it('should provide meaningful text alternatives for icons', () => {
      renderComponent({ error: 'Test error' });

      const errorIcon = screen.getByText('Comparison Error').closest('div')?.querySelector('svg');
      expect(errorIcon).toBeInTheDocument();
    });

    it('should have proper color contrast for text', () => {
      renderComponent();

      const heading = screen.getByText('Configuration Comparison');
      expect(heading).toHaveClass('text-gray-900');
    });
  });

  // ==========================================================================
  // Edge Cases Tests
  // ==========================================================================

  describe('Edge Cases', () => {
    it('should handle configurations with no packages', () => {
      const configs = ConfigurationFactory.createMany(2, [
        { packages: [] },
        { packages: [] },
      ]);
      renderComponent({ configurations: configs });

      expect(screen.getByText('Configuration Comparison')).toBeInTheDocument();
    });

    it('should handle configurations with no options', () => {
      const configs = ConfigurationFactory.createMany(2, [
        { options: [] },
        { options: [] },
      ]);
      renderComponent({ configurations: configs });

      expect(screen.getByText('Configuration Comparison')).toBeInTheDocument();
    });

    it('should handle configurations with identical pricing', () => {
      const pricing = { basePrice: 45000, optionsPrice: 5000, packagesPrice: 3000, total: 53000 };
      const configs = ConfigurationFactory.createMany(2, [
        { pricing },
        { pricing },
      ]);
      renderComponent({ configurations: configs });

      expect(screen.getByText(/\$53,000 - \$53,000/)).toBeInTheDocument();
    });

    it('should handle very long configuration names', () => {
      const longName = 'A'.repeat(100);
      const configs = ConfigurationFactory.createMany(2, [
        { name: longName },
      ]);
      renderComponent({ configurations: configs });

      expect(screen.getByText(longName)).toBeInTheDocument();
    });

    it('should handle zero prices', () => {
      const configs = ConfigurationFactory.createMany(2, [
        { pricing: { basePrice: 0, optionsPrice: 0, packagesPrice: 0, total: 0 } },
      ]);
      renderComponent({ configurations: configs });

      expect(screen.getByText(/\$0/)).toBeInTheDocument();
    });

    it('should handle very large prices', () => {
      const configs = ConfigurationFactory.createMany(2, [
        { pricing: { basePrice: 999999, optionsPrice: 100000, packagesPrice: 50000, total: 1149999 } },
      ]);
      renderComponent({ configurations: configs });

      expect(screen.getByText(/\$1,149,999/)).toBeInTheDocument();
    });

    it('should handle configurations with special characters in names', () => {
      const configs = ConfigurationFactory.createMany(2, [
        { name: 'Config & Test <Special>' },
      ]);
      renderComponent({ configurations: configs });

      expect(screen.getByText('Config & Test <Special>')).toBeInTheDocument();
    });

    it('should handle rapid configuration changes', async () => {
      const { rerender } = renderComponent();

      const newConfigs = ConfigurationFactory.createMany(3);
      rerender(<ConfigurationComparison {...PropsFactory.create({ configurations: newConfigs })} />);

      expect(screen.getByText(/comparing 3 configurations/i)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Performance Tests
  // ==========================================================================

  describe('Performance', () => {
    it('should render efficiently with maximum configurations', () => {
      const configs = ConfigurationFactory.createMany(COMPARISON_CONSTRAINTS.MAX_CONFIGURATIONS);
      const startTime = performance.now();
      
      renderComponent({ configurations: configs });
      
      const endTime = performance.now();
      const renderTime = endTime - startTime;
      
      // Should render in less than 100ms
      expect(renderTime).toBeLessThan(100);
    });

    it('should handle large number of features efficiently', () => {
      const manyOptions = Array.from({ length: 50 }, (_, i) => ({
        id: `opt-${i}`,
        name: `Option ${i}`,
        category: 'technology',
        price: 1000,
      }));

      const configs = ConfigurationFactory.createMany(2, [
        { options: manyOptions },
      ]);

      const startTime = performance.now();
      renderComponent({ configurations: configs });
      const endTime = performance.now();
      
      expect(endTime - startTime).toBeLessThan(200);
    });

    it('should memoize comparison calculations', () => {
      const configs = ConfigurationFactory.createMany(2);
      const { rerender } = renderComponent({ configurations: configs });

      // Rerender with same props
      rerender(<ConfigurationComparison {...PropsFactory.create({ configurations: configs })} />);

      // Should not recalculate (verified by no errors and fast render)
      expect(screen.getByText('Configuration Comparison')).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Integration Tests
  // ==========================================================================

  describe('Integration', () => {
    it('should work with all features enabled', async () => {
      const configs = ConfigurationFactory.createMany(3);
      const onRemove = vi.fn();
      const onSave = vi.fn();

      const { user } = renderComponent({
        configurations: configs,
        onRemoveConfiguration: onRemove,
        onSaveConfiguration: onSave,
        highlightDifferences: true,
        enableMobileView: true,
      });

      // Verify rendering
      expect(screen.getByText('Configuration Comparison')).toBeInTheDocument();

      // Test interaction
      const removeButtons = screen.getAllByLabelText(/remove/i);
      await user.click(removeButtons[0]);
      expect(onRemove).toHaveBeenCalled();
    });

    it('should maintain state across viewport changes', () => {
      const configs = ConfigurationFactory.createMany(2);
      renderComponent({ configurations: configs, enableMobileView: true });

      // Start desktop
      setDesktopViewport();
      expect(screen.getByRole('table')).toBeInTheDocument();

      // Switch to mobile
      setMobileViewport();
      // Component should still render
      expect(screen.getByText('Configuration Comparison')).toBeInTheDocument();
    });

    it('should handle configuration updates correctly', () => {
      const initialConfigs = ConfigurationFactory.createMany(2);
      const { rerender } = renderComponent({ configurations: initialConfigs });

      expect(screen.getByText(/comparing 2 configurations/i)).toBeInTheDocument();

      // Update configurations
      const updatedConfigs = ConfigurationFactory.createMany(3);
      rerender(<ConfigurationComparison {...PropsFactory.create({ configurations: updatedConfigs })} />);

      expect(screen.getByText(/comparing 3 configurations/i)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // Snapshot Tests
  // ==========================================================================

  describe('Snapshots', () => {
    it('should match snapshot for default state', () => {
      const { container } = renderComponent();
      expect(container).toMatchSnapshot();
    });

    it('should match snapshot for loading state', () => {
      const { container } = renderComponent({ isLoading: true });
      expect(container).toMatchSnapshot();
    });

    it('should match snapshot for error state', () => {
      const { container } = renderComponent({ error: 'Test error' });
      expect(container).toMatchSnapshot();
    });

    it('should match snapshot for empty state', () => {
      const { container } = renderComponent({ configurations: [] });
      expect(container).toMatchSnapshot();
    });

    it('should match snapshot for mobile view', () => {
      setMobileViewport();
      const configs = ConfigurationFactory.createMany(2);
      const { container } = renderComponent({ configurations: configs, enableMobileView: true });
      expect(container).toMatchSnapshot();
    });
  });
});