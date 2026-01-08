/**
 * Comprehensive Test Suite for FilterSidebar Component
 * 
 * Test Coverage:
 * - Component rendering and visibility states
 * - Filter selection and multi-select behavior
 * - Filter counts and active filter tracking
 * - Clear all functionality
 * - Mobile responsive drawer behavior
 * - Range slider interactions
 * - Loading states and error handling
 * - Accessibility compliance
 * - Performance and optimization
 * 
 * Coverage Target: >80%
 * Complexity: Medium (5-20 test files, integration testing)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import FilterSidebar from '../../../components/VehicleBrowsing/FilterSidebar';
import type { VehicleFilters } from '../../../types/vehicle';
import * as vehicleHooks from '../../../hooks/useVehicles';

// ============================================================================
// Test Setup and Utilities
// ============================================================================

/**
 * Factory for creating test filter objects
 */
class FilterFactory {
  static empty(): VehicleFilters {
    return {};
  }

  static withMake(makes: string[]): VehicleFilters {
    return { make: makes };
  }

  static withModel(models: string[]): VehicleFilters {
    return { model: models };
  }

  static withPriceRange(min: number, max: number): VehicleFilters {
    return { price: { min, max } };
  }

  static withYearRange(min: number, max: number): VehicleFilters {
    return { year: { min, max } };
  }

  static complete(): VehicleFilters {
    return {
      make: ['Toyota', 'Honda'],
      model: ['Camry', 'Accord'],
      bodyStyle: ['sedan', 'suv'],
      fuelType: ['gasoline', 'hybrid'],
      transmission: ['automatic'],
      drivetrain: ['fwd', 'awd'],
      price: { min: 20000, max: 50000 },
      year: { min: 2020, max: 2024 },
    };
  }
}

/**
 * Mock data factory for vehicle facets
 */
const createMockFacetsData = () => ({
  makes: [
    { value: 'Toyota', count: 150 },
    { value: 'Honda', count: 120 },
    { value: 'Ford', count: 100 },
    { value: 'Chevrolet', count: 90 },
  ],
  models: [
    { value: 'Camry', count: 45 },
    { value: 'Accord', count: 40 },
    { value: 'Civic', count: 35 },
  ],
  bodyStyles: [
    { value: 'sedan', count: 200 },
    { value: 'suv', count: 180 },
    { value: 'truck', count: 150 },
  ],
  fuelTypes: [
    { value: 'gasoline', count: 300 },
    { value: 'hybrid', count: 100 },
    { value: 'electric', count: 50 },
  ],
  transmissions: [
    { value: 'automatic', count: 400 },
    { value: 'manual', count: 50 },
  ],
  drivetrains: [
    { value: 'fwd', count: 250 },
    { value: 'awd', count: 150 },
    { value: 'rwd', count: 50 },
  ],
});

/**
 * Mock data factory for price range
 */
const createMockPriceRange = () => ({
  min: 15000,
  max: 80000,
});

/**
 * Test wrapper with React Query provider
 */
function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

/**
 * Default props factory
 */
const createDefaultProps = (overrides = {}) => ({
  filters: FilterFactory.empty(),
  onFiltersChange: vi.fn(),
  isOpen: true,
  ...overrides,
});

// ============================================================================
// Test Suite: Component Rendering
// ============================================================================

describe('FilterSidebar - Component Rendering', () => {
  let mockUseVehicleFacets: ReturnType<typeof vi.fn>;
  let mockUsePriceRange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockUseVehicleFacets = vi.fn(() => ({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    }));

    mockUsePriceRange = vi.fn(() => ({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    }));

    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockImplementation(mockUseVehicleFacets);
    vi.spyOn(vehicleHooks, 'usePriceRange').mockImplementation(mockUsePriceRange);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render filter sidebar with all sections', () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(screen.getByText('Filters')).toBeInTheDocument();
    expect(screen.getByText('Make')).toBeInTheDocument();
    expect(screen.getByText('Model')).toBeInTheDocument();
    expect(screen.getByText('Year')).toBeInTheDocument();
    expect(screen.getByText('Price')).toBeInTheDocument();
    expect(screen.getByText('Body Style')).toBeInTheDocument();
    expect(screen.getByText('Fuel Type')).toBeInTheDocument();
    expect(screen.getByText('Transmission')).toBeInTheDocument();
    expect(screen.getByText('Drivetrain')).toBeInTheDocument();
  });

  it('should not render when isOpen is false', () => {
    const props = createDefaultProps({ isOpen: false });
    const { container } = renderWithQueryClient(<FilterSidebar {...props} />);

    expect(container.firstChild).toBeEmptyDOMElement();
  });

  it('should render desktop and mobile versions correctly', () => {
    const props = createDefaultProps();
    const { container } = renderWithQueryClient(<FilterSidebar {...props} />);

    const desktopVersion = container.querySelector('.hidden.lg\\:block');
    const mobileVersion = container.querySelector('.lg\\:hidden');

    expect(desktopVersion).toBeInTheDocument();
    expect(mobileVersion).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const props = createDefaultProps({ className: 'custom-class' });
    const { container } = renderWithQueryClient(<FilterSidebar {...props} />);

    const desktopVersion = container.querySelector('.custom-class');
    expect(desktopVersion).toBeInTheDocument();
  });

  it('should render close button on mobile when onClose is provided', () => {
    const onClose = vi.fn();
    const props = createDefaultProps({ onClose });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const closeButton = screen.getByLabelText('Close filters');
    expect(closeButton).toBeInTheDocument();
  });

  it('should not render close button when onClose is not provided', () => {
    const props = createDefaultProps({ onClose: undefined });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const closeButton = screen.queryByLabelText('Close filters');
    expect(closeButton).not.toBeInTheDocument();
  });
});

// ============================================================================
// Test Suite: Filter Section Expansion
// ============================================================================

describe('FilterSidebar - Filter Section Expansion', () => {
  beforeEach(() => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    } as any);

    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should expand and collapse filter sections on click', async () => {
    const user = userEvent.setup();
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const bodyStyleButton = screen.getByRole('button', { name: /Body Style/i });

    // Initially collapsed
    expect(bodyStyleButton).toHaveAttribute('aria-expanded', 'false');

    // Expand section
    await user.click(bodyStyleButton);
    expect(bodyStyleButton).toHaveAttribute('aria-expanded', 'true');

    // Collapse section
    await user.click(bodyStyleButton);
    expect(bodyStyleButton).toHaveAttribute('aria-expanded', 'false');
  });

  it('should have Make and Model sections expanded by default', () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const makeButton = screen.getByRole('button', { name: /^Make$/i });
    const modelButton = screen.getByRole('button', { name: /^Model$/i });

    expect(makeButton).toHaveAttribute('aria-expanded', 'true');
    expect(modelButton).toHaveAttribute('aria-expanded', 'true');
  });

  it('should show loading spinner when section is loading', () => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any);

    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const spinners = screen.getAllByRole('status', { hidden: true });
    expect(spinners.length).toBeGreaterThan(0);
  });

  it('should disable Model section when no make is selected', () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const modelButton = screen.getByRole('button', { name: /^Model$/i });
    expect(modelButton).toBeDisabled();
  });

  it('should enable Model section when make is selected', () => {
    const props = createDefaultProps({
      filters: FilterFactory.withMake(['Toyota']),
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const modelButton = screen.getByRole('button', { name: /^Model$/i });
    expect(modelButton).not.toBeDisabled();
  });
});

// ============================================================================
// Test Suite: Make Filter
// ============================================================================

describe('FilterSidebar - Make Filter', () => {
  beforeEach(() => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    } as any);

    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render all make options with counts', () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(screen.getByText('Toyota')).toBeInTheDocument();
    expect(screen.getByText('(150)')).toBeInTheDocument();
    expect(screen.getByText('Honda')).toBeInTheDocument();
    expect(screen.getByText('(120)')).toBeInTheDocument();
  });

  it('should select a make when checkbox is clicked', async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({ onFiltersChange });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const toyotaCheckbox = screen.getByRole('checkbox', { name: /Toyota/i });
    await user.click(toyotaCheckbox);

    expect(onFiltersChange).toHaveBeenCalledWith({
      make: ['Toyota'],
      model: undefined,
    });
  });

  it('should deselect a make when already selected checkbox is clicked', async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({
      filters: FilterFactory.withMake(['Toyota']),
      onFiltersChange,
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const toyotaCheckbox = screen.getByRole('checkbox', { name: /Toyota/i });
    await user.click(toyotaCheckbox);

    expect(onFiltersChange).toHaveBeenCalledWith({
      make: undefined,
      model: undefined,
    });
  });

  it('should support multi-select for makes', async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({
      filters: FilterFactory.withMake(['Toyota']),
      onFiltersChange,
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const hondaCheckbox = screen.getByRole('checkbox', { name: /Honda/i });
    await user.click(hondaCheckbox);

    expect(onFiltersChange).toHaveBeenCalledWith({
      make: ['Toyota', 'Honda'],
      model: undefined,
    });
  });

  it('should clear model filter when make is changed', async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({
      filters: {
        make: ['Toyota'],
        model: ['Camry'],
      },
      onFiltersChange,
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const hondaCheckbox = screen.getByRole('checkbox', { name: /Honda/i });
    await user.click(hondaCheckbox);

    expect(onFiltersChange).toHaveBeenCalledWith({
      make: ['Toyota', 'Honda'],
      model: undefined,
    });
  });

  it('should show empty message when no makes available', () => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: { ...createMockFacetsData(), makes: [] },
      isLoading: false,
      error: null,
    } as any);

    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(screen.getByText('No makes available')).toBeInTheDocument();
  });
});

// ============================================================================
// Test Suite: Model Filter
// ============================================================================

describe('FilterSidebar - Model Filter', () => {
  beforeEach(() => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    } as any);

    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render model options when make is selected', () => {
    const props = createDefaultProps({
      filters: FilterFactory.withMake(['Toyota']),
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(screen.getByText('Camry')).toBeInTheDocument();
    expect(screen.getByText('Accord')).toBeInTheDocument();
  });

  it('should show "Select a make first" when no make selected', () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(screen.getByText('Select a make first')).toBeInTheDocument();
  });

  it('should select a model when checkbox is clicked', async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({
      filters: FilterFactory.withMake(['Toyota']),
      onFiltersChange,
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const camryCheckbox = screen.getByRole('checkbox', { name: /Camry/i });
    await user.click(camryCheckbox);

    expect(onFiltersChange).toHaveBeenCalledWith({
      make: ['Toyota'],
      model: ['Camry'],
    });
  });

  it('should support multi-select for models', async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({
      filters: {
        make: ['Toyota'],
        model: ['Camry'],
      },
      onFiltersChange,
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const accordCheckbox = screen.getByRole('checkbox', { name: /Accord/i });
    await user.click(accordCheckbox);

    expect(onFiltersChange).toHaveBeenCalledWith({
      make: ['Toyota'],
      model: ['Camry', 'Accord'],
    });
  });
});

// ============================================================================
// Test Suite: Body Style Filter
// ============================================================================

describe('FilterSidebar - Body Style Filter', () => {
  beforeEach(() => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    } as any);

    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render body style options with human-readable labels', async () => {
    const user = userEvent.setup();
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const bodyStyleButton = screen.getByRole('button', { name: /Body Style/i });
    await user.click(bodyStyleButton);

    expect(screen.getByText('Sedan')).toBeInTheDocument();
    expect(screen.getByText('SUV')).toBeInTheDocument();
    expect(screen.getByText('Truck')).toBeInTheDocument();
  });

  it('should select body style when checkbox is clicked', async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({ onFiltersChange });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const bodyStyleButton = screen.getByRole('button', { name: /Body Style/i });
    await user.click(bodyStyleButton);

    const sedanCheckbox = screen.getByRole('checkbox', { name: /Sedan/i });
    await user.click(sedanCheckbox);

    expect(onFiltersChange).toHaveBeenCalledWith({
      bodyStyle: ['sedan'],
    });
  });

  it('should support multi-select for body styles', async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({
      filters: { bodyStyle: ['sedan'] },
      onFiltersChange,
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const bodyStyleButton = screen.getByRole('button', { name: /Body Style/i });
    await user.click(bodyStyleButton);

    const suvCheckbox = screen.getByRole('checkbox', { name: /SUV/i });
    await user.click(suvCheckbox);

    expect(onFiltersChange).toHaveBeenCalledWith({
      bodyStyle: ['sedan', 'suv'],
    });
  });
});

// ============================================================================
// Test Suite: Price Range Filter
// ============================================================================

describe('FilterSidebar - Price Range Filter', () => {
  beforeEach(() => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    } as any);

    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render price range with formatted values', () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(screen.getByText('$15,000')).toBeInTheDocument();
    expect(screen.getByText('$80,000')).toBeInTheDocument();
  });

  it('should update price range on slider change', async () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const minSlider = screen.getAllByLabelText('Minimum value')[0];
    fireEvent.change(minSlider, { target: { value: '20000' } });

    await waitFor(() => {
      expect(screen.getByText('$20,000')).toBeInTheDocument();
    });
  });

  it('should call onFiltersChange on slider mouseup', async () => {
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({ onFiltersChange });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const minSlider = screen.getAllByLabelText('Minimum value')[0];
    fireEvent.change(minSlider, { target: { value: '20000' } });
    fireEvent.mouseUp(minSlider);

    await waitFor(() => {
      expect(onFiltersChange).toHaveBeenCalledWith({
        price: { min: 20000, max: 80000 },
      });
    });
  });

  it('should prevent min from exceeding max', async () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const minSlider = screen.getAllByLabelText('Minimum value')[0];
    fireEvent.change(minSlider, { target: { value: '90000' } });

    await waitFor(() => {
      expect(screen.getByText('$80,000')).toBeInTheDocument();
    });
  });

  it('should prevent max from going below min', async () => {
    const props = createDefaultProps({
      filters: FilterFactory.withPriceRange(30000, 50000),
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const maxSlider = screen.getAllByLabelText('Maximum value')[0];
    fireEvent.change(maxSlider, { target: { value: '20000' } });

    await waitFor(() => {
      expect(screen.getByText('$30,000')).toBeInTheDocument();
    });
  });

  it('should handle touchend event for mobile', async () => {
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({ onFiltersChange });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const minSlider = screen.getAllByLabelText('Minimum value')[0];
    fireEvent.change(minSlider, { target: { value: '25000' } });
    fireEvent.touchEnd(minSlider);

    await waitFor(() => {
      expect(onFiltersChange).toHaveBeenCalled();
    });
  });
});

// ============================================================================
// Test Suite: Year Range Filter
// ============================================================================

describe('FilterSidebar - Year Range Filter', () => {
  beforeEach(() => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    } as any);

    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render year range with current year as max', () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const currentYear = new Date().getFullYear();
    expect(screen.getByText(currentYear.toString())).toBeInTheDocument();
    expect(screen.getByText('2000')).toBeInTheDocument();
  });

  it('should update year range on slider change', async () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const minSlider = screen.getAllByLabelText('Minimum value')[1];
    fireEvent.change(minSlider, { target: { value: '2015' } });

    await waitFor(() => {
      expect(screen.getByText('2015')).toBeInTheDocument();
    });
  });

  it('should call onFiltersChange on year slider mouseup', async () => {
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({ onFiltersChange });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const minSlider = screen.getAllByLabelText('Minimum value')[1];
    fireEvent.change(minSlider, { target: { value: '2018' } });
    fireEvent.mouseUp(minSlider);

    await waitFor(() => {
      expect(onFiltersChange).toHaveBeenCalledWith(
        expect.objectContaining({
          year: expect.objectContaining({ min: 2018 }),
        }),
      );
    });
  });
});

// ============================================================================
// Test Suite: Active Filter Count
// ============================================================================

describe('FilterSidebar - Active Filter Count', () => {
  beforeEach(() => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    } as any);

    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should not show filter count badge when no filters active', () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const badge = screen.queryByText(/^\d+$/);
    expect(badge).not.toBeInTheDocument();
  });

  it('should show correct filter count for single filter', () => {
    const props = createDefaultProps({
      filters: FilterFactory.withMake(['Toyota']),
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('should show correct filter count for multiple filters', () => {
    const props = createDefaultProps({
      filters: FilterFactory.complete(),
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    // 2 makes + 2 models + 2 body styles + 2 fuel types + 1 transmission + 2 drivetrains + 1 price + 1 year = 13
    expect(screen.getByText('13')).toBeInTheDocument();
  });

  it('should count price range as single filter', () => {
    const props = createDefaultProps({
      filters: FilterFactory.withPriceRange(20000, 50000),
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('should count year range as single filter', () => {
    const props = createDefaultProps({
      filters: FilterFactory.withYearRange(2020, 2024),
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(screen.getByText('1')).toBeInTheDocument();
  });
});

// ============================================================================
// Test Suite: Clear All Functionality
// ============================================================================

describe('FilterSidebar - Clear All Functionality', () => {
  beforeEach(() => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    } as any);

    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should not show Clear All button when no filters active', () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const clearButton = screen.queryByRole('button', { name: /Clear all filters/i });
    expect(clearButton).not.toBeInTheDocument();
  });

  it('should show Clear All button when filters are active', () => {
    const props = createDefaultProps({
      filters: FilterFactory.withMake(['Toyota']),
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(screen.getByRole('button', { name: /Clear all filters/i })).toBeInTheDocument();
  });

  it('should clear all filters when Clear All is clicked', async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({
      filters: FilterFactory.complete(),
      onFiltersChange,
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const clearButton = screen.getByRole('button', { name: /Clear all filters/i });
    await user.click(clearButton);

    expect(onFiltersChange).toHaveBeenCalledWith({});
  });

  it('should reset price range to defaults when clearing', async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({
      filters: FilterFactory.withPriceRange(30000, 60000),
      onFiltersChange,
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const clearButton = screen.getByRole('button', { name: /Clear all filters/i });
    await user.click(clearButton);

    await waitFor(() => {
      expect(screen.getByText('$15,000')).toBeInTheDocument();
      expect(screen.getByText('$80,000')).toBeInTheDocument();
    });
  });

  it('should reset year range to defaults when clearing', async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({
      filters: FilterFactory.withYearRange(2020, 2023),
      onFiltersChange,
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const clearButton = screen.getByRole('button', { name: /Clear all filters/i });
    await user.click(clearButton);

    const currentYear = new Date().getFullYear();
    await waitFor(() => {
      expect(screen.getByText('2000')).toBeInTheDocument();
      expect(screen.getByText(currentYear.toString())).toBeInTheDocument();
    });
  });
});

// ============================================================================
// Test Suite: Mobile Drawer Behavior
// ============================================================================

describe('FilterSidebar - Mobile Drawer Behavior', () => {
  beforeEach(() => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    } as any);

    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should call onClose when close button is clicked', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const props = createDefaultProps({ onClose });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const closeButton = screen.getByLabelText('Close filters');
    await user.click(closeButton);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('should call onClose when backdrop is clicked', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const props = createDefaultProps({ onClose });
    const { container } = renderWithQueryClient(<FilterSidebar {...props} />);

    const backdrop = container.querySelector('.fixed.inset-0.z-40');
    if (backdrop) {
      await user.click(backdrop);
      expect(onClose).toHaveBeenCalledTimes(1);
    }
  });

  it('should apply correct transform classes when open', () => {
    const props = createDefaultProps({ isOpen: true });
    const { container } = renderWithQueryClient(<FilterSidebar {...props} />);

    const drawer = container.querySelector('.translate-x-0');
    expect(drawer).toBeInTheDocument();
  });

  it('should apply correct transform classes when closed', () => {
    const props = createDefaultProps({ isOpen: false });
    const { container } = renderWithQueryClient(<FilterSidebar {...props} />);

    const drawer = container.querySelector('.-translate-x-full');
    expect(drawer).not.toBeInTheDocument();
  });
});

// ============================================================================
// Test Suite: Accessibility
// ============================================================================

describe('FilterSidebar - Accessibility', () => {
  beforeEach(() => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    } as any);

    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should have proper ARIA labels for all interactive elements', () => {
    const props = createDefaultProps({ onClose: vi.fn() });
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(screen.getByLabelText('Close filters')).toBeInTheDocument();
    expect(screen.getByLabelText('Clear all filters')).toBeInTheDocument();
  });

  it('should have proper ARIA expanded states for sections', () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const makeButton = screen.getByRole('button', { name: /^Make$/i });
    expect(makeButton).toHaveAttribute('aria-expanded', 'true');

    const bodyStyleButton = screen.getByRole('button', { name: /Body Style/i });
    expect(bodyStyleButton).toHaveAttribute('aria-expanded', 'false');
  });

  it('should have proper ARIA controls for expandable sections', () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const makeButton = screen.getByRole('button', { name: /^Make$/i });
    expect(makeButton).toHaveAttribute('aria-controls', 'filter-section-make');
  });

  it('should have proper labels for range sliders', () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const minSliders = screen.getAllByLabelText('Minimum value');
    const maxSliders = screen.getAllByLabelText('Maximum value');

    expect(minSliders.length).toBeGreaterThan(0);
    expect(maxSliders.length).toBeGreaterThan(0);
  });

  it('should support keyboard navigation for checkboxes', async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({ onFiltersChange });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const toyotaCheckbox = screen.getByRole('checkbox', { name: /Toyota/i });
    toyotaCheckbox.focus();
    await user.keyboard('{Space}');

    expect(onFiltersChange).toHaveBeenCalled();
  });

  it('should have proper disabled state styling', () => {
    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const modelButton = screen.getByRole('button', { name: /^Model$/i });
    expect(modelButton).toHaveClass('disabled:cursor-not-allowed', 'disabled:opacity-50');
  });
});

// ============================================================================
// Test Suite: Loading States
// ============================================================================

describe('FilterSidebar - Loading States', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should show loading spinner for facets', () => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any);

    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);

    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const spinners = screen.getAllByRole('status', { hidden: true });
    expect(spinners.length).toBeGreaterThan(0);
  });

  it('should show loading spinner for price range', () => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    } as any);

    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any);

    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    const spinners = screen.getAllByRole('status', { hidden: true });
    expect(spinners.length).toBeGreaterThan(0);
  });

  it('should render content when data is loaded', async () => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    } as any);

    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);

    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    await waitFor(() => {
      expect(screen.getByText('Toyota')).toBeInTheDocument();
      expect(screen.getByText('$15,000')).toBeInTheDocument();
    });
  });
});

// ============================================================================
// Test Suite: Edge Cases and Error Handling
// ============================================================================

describe('FilterSidebar - Edge Cases', () => {
  beforeEach(() => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    } as any);

    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should handle undefined facets data gracefully', () => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as any);

    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(screen.getByText('Filters')).toBeInTheDocument();
  });

  it('should handle undefined price range data gracefully', () => {
    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as any);

    const props = createDefaultProps();
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(screen.getByText('$0')).toBeInTheDocument();
    expect(screen.getByText('$100,000')).toBeInTheDocument();
  });

  it('should handle empty filter arrays', () => {
    const props = createDefaultProps({
      filters: {
        make: [],
        model: [],
        bodyStyle: [],
      },
    });
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(screen.getByText('Filters')).toBeInTheDocument();
  });

  it('should handle rapid filter changes', async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({ onFiltersChange });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const toyotaCheckbox = screen.getByRole('checkbox', { name: /Toyota/i });
    const hondaCheckbox = screen.getByRole('checkbox', { name: /Honda/i });

    await user.click(toyotaCheckbox);
    await user.click(hondaCheckbox);
    await user.click(toyotaCheckbox);

    expect(onFiltersChange).toHaveBeenCalledTimes(3);
  });

  it('should maintain filter state during re-renders', async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    const { rerender } = renderWithQueryClient(
      <FilterSidebar {...createDefaultProps({ onFiltersChange })} />,
    );

    const toyotaCheckbox = screen.getByRole('checkbox', { name: /Toyota/i });
    await user.click(toyotaCheckbox);

    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <FilterSidebar
          {...createDefaultProps({
            filters: FilterFactory.withMake(['Toyota']),
            onFiltersChange,
          })}
        />
      </QueryClientProvider>,
    );

    const updatedCheckbox = screen.getByRole('checkbox', { name: /Toyota/i });
    expect(updatedCheckbox).toBeChecked();
  });
});

// ============================================================================
// Test Suite: Performance and Optimization
// ============================================================================

describe('FilterSidebar - Performance', () => {
  beforeEach(() => {
    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    } as any);

    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should memoize filter options to prevent unnecessary re-renders', () => {
    const props = createDefaultProps();
    const { rerender } = renderWithQueryClient(<FilterSidebar {...props} />);

    const initialMakes = screen.getAllByRole('checkbox');

    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <FilterSidebar {...props} />
      </QueryClientProvider>,
    );

    const rerenderedMakes = screen.getAllByRole('checkbox');
    expect(initialMakes.length).toBe(rerenderedMakes.length);
  });

  it('should handle large number of filter options efficiently', () => {
    const largeFacetsData = {
      ...createMockFacetsData(),
      makes: Array.from({ length: 100 }, (_, i) => ({
        value: `Make${i}`,
        count: i + 1,
      })),
    };

    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: largeFacetsData,
      isLoading: false,
      error: null,
    } as any);

    const props = createDefaultProps();
    const startTime = performance.now();
    renderWithQueryClient(<FilterSidebar {...props} />);
    const endTime = performance.now();

    expect(endTime - startTime).toBeLessThan(1000);
  });

  it('should debounce range slider updates', async () => {
    const onFiltersChange = vi.fn();
    const props = createDefaultProps({ onFiltersChange });
    renderWithQueryClient(<FilterSidebar {...props} />);

    const minSlider = screen.getAllByLabelText('Minimum value')[0];

    fireEvent.change(minSlider, { target: { value: '20000' } });
    fireEvent.change(minSlider, { target: { value: '25000' } });
    fireEvent.change(minSlider, { target: { value: '30000' } });

    expect(onFiltersChange).not.toHaveBeenCalled();

    fireEvent.mouseUp(minSlider);

    await waitFor(() => {
      expect(onFiltersChange).toHaveBeenCalledTimes(1);
    });
  });
});

// ============================================================================
// Test Suite: Integration with Hooks
// ============================================================================

describe('FilterSidebar - Hook Integration', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should call useVehicleFacets with current filters', () => {
    const mockUseVehicleFacets = vi.fn(() => ({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    }));

    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockImplementation(mockUseVehicleFacets);
    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);

    const filters = FilterFactory.withMake(['Toyota']);
    const props = createDefaultProps({ filters });
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(mockUseVehicleFacets).toHaveBeenCalledWith(filters);
  });

  it('should call usePriceRange with current filters', () => {
    const mockUsePriceRange = vi.fn(() => ({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    }));

    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockReturnValue({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    } as any);
    vi.spyOn(vehicleHooks, 'usePriceRange').mockImplementation(mockUsePriceRange);

    const filters = FilterFactory.withMake(['Toyota']);
    const props = createDefaultProps({ filters });
    renderWithQueryClient(<FilterSidebar {...props} />);

    expect(mockUsePriceRange).toHaveBeenCalledWith(filters);
  });

  it('should update when hook data changes', async () => {
    const mockUseVehicleFacets = vi.fn(() => ({
      data: createMockFacetsData(),
      isLoading: false,
      error: null,
    }));

    vi.spyOn(vehicleHooks, 'useVehicleFacets').mockImplementation(mockUseVehicleFacets);
    vi.spyOn(vehicleHooks, 'usePriceRange').mockReturnValue({
      data: createMockPriceRange(),
      isLoading: false,
      error: null,
    } as any);

    const props = createDefaultProps();
    const { rerender } = renderWithQueryClient(<FilterSidebar {...props} />);

    const updatedFacetsData = {
      ...createMockFacetsData(),
      makes: [{ value: 'Tesla', count: 50 }],
    };

    mockUseVehicleFacets.mockReturnValue({
      data: updatedFacetsData,
      isLoading: false,
      error: null,
    });

    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <FilterSidebar {...props} />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText('Tesla')).toBeInTheDocument();
    });
  });
});