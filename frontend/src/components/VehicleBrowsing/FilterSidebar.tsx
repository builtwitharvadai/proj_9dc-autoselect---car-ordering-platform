/**
 * Advanced Filter Sidebar Component for Vehicle Browsing
 * Provides collapsible filter sections with multi-select options, real-time counts, and mobile-responsive drawer
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import type {
  VehicleFilters,
  BodyStyle,
  FuelType,
  TransmissionType,
  DrivetrainType,
  PriceRange,
  YearRange,
} from '../../types/vehicle';
import { useVehicleFacets, usePriceRange } from '../../hooks/useVehicles';

interface FilterSidebarProps {
  readonly filters: VehicleFilters;
  readonly onFiltersChange: (filters: VehicleFilters) => void;
  readonly isOpen?: boolean;
  readonly onClose?: () => void;
  readonly className?: string;
}

interface FilterSection {
  readonly id: string;
  readonly label: string;
  readonly isExpanded: boolean;
}

interface FilterOption {
  readonly value: string;
  readonly label: string;
  readonly count: number;
}

const BODY_STYLE_LABELS: Record<BodyStyle, string> = {
  sedan: 'Sedan',
  suv: 'SUV',
  truck: 'Truck',
  coupe: 'Coupe',
  convertible: 'Convertible',
  wagon: 'Wagon',
  van: 'Van',
  hatchback: 'Hatchback',
} as const;

const FUEL_TYPE_LABELS: Record<FuelType, string> = {
  gasoline: 'Gasoline',
  diesel: 'Diesel',
  electric: 'Electric',
  hybrid: 'Hybrid',
  'plug-in-hybrid': 'Plug-in Hybrid',
} as const;

const TRANSMISSION_LABELS: Record<TransmissionType, string> = {
  automatic: 'Automatic',
  manual: 'Manual',
  cvt: 'CVT',
  'dual-clutch': 'Dual-Clutch',
} as const;

const DRIVETRAIN_LABELS: Record<DrivetrainType, string> = {
  fwd: 'Front-Wheel Drive',
  rwd: 'Rear-Wheel Drive',
  awd: 'All-Wheel Drive',
  '4wd': '4-Wheel Drive',
} as const;

const CURRENT_YEAR = new Date().getFullYear();
const MIN_YEAR = 2000;

export default function FilterSidebar({
  filters,
  onFiltersChange,
  isOpen = true,
  onClose,
  className = '',
}: FilterSidebarProps): JSX.Element {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    make: true,
    model: true,
    year: true,
    price: true,
    bodyStyle: false,
    fuelType: false,
    transmission: false,
    drivetrain: false,
  });

  const { data: facetsData, isLoading: facetsLoading } = useVehicleFacets(filters);
  const { data: priceRangeData, isLoading: priceRangeLoading } = usePriceRange(filters);

  const [localPriceRange, setLocalPriceRange] = useState<PriceRange>({
    min: 0,
    max: 100000,
  });

  const [localYearRange, setLocalYearRange] = useState<YearRange>({
    min: MIN_YEAR,
    max: CURRENT_YEAR,
  });

  useEffect(() => {
    if (priceRangeData) {
      setLocalPriceRange({
        min: filters.price?.min ?? priceRangeData.min,
        max: filters.price?.max ?? priceRangeData.max,
      });
    }
  }, [priceRangeData, filters.price]);

  useEffect(() => {
    setLocalYearRange({
      min: filters.year?.min ?? MIN_YEAR,
      max: filters.year?.max ?? CURRENT_YEAR,
    });
  }, [filters.year]);

  const toggleSection = useCallback((sectionId: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [sectionId]: !prev[sectionId],
    }));
  }, []);

  const handleMakeChange = useCallback(
    (make: string) => {
      const currentMakes = filters.make ?? [];
      const newMakes = currentMakes.includes(make)
        ? currentMakes.filter((m) => m !== make)
        : [...currentMakes, make];

      onFiltersChange({
        ...filters,
        make: newMakes.length > 0 ? newMakes : undefined,
        model: undefined,
      });
    },
    [filters, onFiltersChange],
  );

  const handleModelChange = useCallback(
    (model: string) => {
      const currentModels = filters.model ?? [];
      const newModels = currentModels.includes(model)
        ? currentModels.filter((m) => m !== model)
        : [...currentModels, model];

      onFiltersChange({
        ...filters,
        model: newModels.length > 0 ? newModels : undefined,
      });
    },
    [filters, onFiltersChange],
  );

  const handleBodyStyleChange = useCallback(
    (bodyStyle: BodyStyle) => {
      const currentStyles = filters.bodyStyle ?? [];
      const newStyles = currentStyles.includes(bodyStyle)
        ? currentStyles.filter((s) => s !== bodyStyle)
        : [...currentStyles, bodyStyle];

      onFiltersChange({
        ...filters,
        bodyStyle: newStyles.length > 0 ? newStyles : undefined,
      });
    },
    [filters, onFiltersChange],
  );

  const handleFuelTypeChange = useCallback(
    (fuelType: FuelType) => {
      const currentTypes = filters.fuelType ?? [];
      const newTypes = currentTypes.includes(fuelType)
        ? currentTypes.filter((t) => t !== fuelType)
        : [...currentTypes, fuelType];

      onFiltersChange({
        ...filters,
        fuelType: newTypes.length > 0 ? newTypes : undefined,
      });
    },
    [filters, onFiltersChange],
  );

  const handleTransmissionChange = useCallback(
    (transmission: TransmissionType) => {
      const currentTransmissions = filters.transmission ?? [];
      const newTransmissions = currentTransmissions.includes(transmission)
        ? currentTransmissions.filter((t) => t !== transmission)
        : [...currentTransmissions, transmission];

      onFiltersChange({
        ...filters,
        transmission: newTransmissions.length > 0 ? newTransmissions : undefined,
      });
    },
    [filters, onFiltersChange],
  );

  const handleDrivetrainChange = useCallback(
    (drivetrain: DrivetrainType) => {
      const currentDrivetrains = filters.drivetrain ?? [];
      const newDrivetrains = currentDrivetrains.includes(drivetrain)
        ? currentDrivetrains.filter((d) => d !== drivetrain)
        : [...currentDrivetrains, drivetrain];

      onFiltersChange({
        ...filters,
        drivetrain: newDrivetrains.length > 0 ? newDrivetrains : undefined,
      });
    },
    [filters, onFiltersChange],
  );

  const handlePriceRangeChange = useCallback(
    (min: number, max: number) => {
      setLocalPriceRange({ min, max });
    },
    [],
  );

  const handlePriceRangeCommit = useCallback(() => {
    onFiltersChange({
      ...filters,
      price:
        localPriceRange.min > 0 || localPriceRange.max < (priceRangeData?.max ?? 100000)
          ? localPriceRange
          : undefined,
    });
  }, [filters, localPriceRange, onFiltersChange, priceRangeData]);

  const handleYearRangeChange = useCallback(
    (min: number, max: number) => {
      setLocalYearRange({ min, max });
    },
    [],
  );

  const handleYearRangeCommit = useCallback(() => {
    onFiltersChange({
      ...filters,
      year: localYearRange.min > MIN_YEAR || localYearRange.max < CURRENT_YEAR ? localYearRange : undefined,
    });
  }, [filters, localYearRange, onFiltersChange]);

  const handleClearAll = useCallback(() => {
    onFiltersChange({});
    setLocalPriceRange({
      min: priceRangeData?.min ?? 0,
      max: priceRangeData?.max ?? 100000,
    });
    setLocalYearRange({
      min: MIN_YEAR,
      max: CURRENT_YEAR,
    });
  }, [onFiltersChange, priceRangeData]);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.make && filters.make.length > 0) count += filters.make.length;
    if (filters.model && filters.model.length > 0) count += filters.model.length;
    if (filters.bodyStyle && filters.bodyStyle.length > 0) count += filters.bodyStyle.length;
    if (filters.fuelType && filters.fuelType.length > 0) count += filters.fuelType.length;
    if (filters.transmission && filters.transmission.length > 0) count += filters.transmission.length;
    if (filters.drivetrain && filters.drivetrain.length > 0) count += filters.drivetrain.length;
    if (filters.price) count += 1;
    if (filters.year) count += 1;
    return count;
  }, [filters]);

  const makeOptions = useMemo<readonly FilterOption[]>(() => {
    if (!facetsData?.makes) return [];
    return facetsData.makes.map((bucket) => ({
      value: bucket.value,
      label: bucket.value,
      count: bucket.count,
    }));
  }, [facetsData]);

  const modelOptions = useMemo<readonly FilterOption[]>(() => {
    if (!facetsData?.models) return [];
    return facetsData.models.map((bucket) => ({
      value: bucket.value,
      label: bucket.value,
      count: bucket.count,
    }));
  }, [facetsData]);

  const bodyStyleOptions = useMemo<readonly FilterOption[]>(() => {
    if (!facetsData?.bodyStyles) return [];
    return facetsData.bodyStyles.map((bucket) => ({
      value: bucket.value,
      label: BODY_STYLE_LABELS[bucket.value as BodyStyle] ?? bucket.value,
      count: bucket.count,
    }));
  }, [facetsData]);

  const fuelTypeOptions = useMemo<readonly FilterOption[]>(() => {
    if (!facetsData?.fuelTypes) return [];
    return facetsData.fuelTypes.map((bucket) => ({
      value: bucket.value,
      label: FUEL_TYPE_LABELS[bucket.value as FuelType] ?? bucket.value,
      count: bucket.count,
    }));
  }, [facetsData]);

  const transmissionOptions = useMemo<readonly FilterOption[]>(() => {
    if (!facetsData?.transmissions) return [];
    return facetsData.transmissions.map((bucket) => ({
      value: bucket.value,
      label: TRANSMISSION_LABELS[bucket.value as TransmissionType] ?? bucket.value,
      count: bucket.count,
    }));
  }, [facetsData]);

  const drivetrainOptions = useMemo<readonly FilterOption[]>(() => {
    if (!facetsData?.drivetrains) return [];
    return facetsData.drivetrains.map((bucket) => ({
      value: bucket.value,
      label: DRIVETRAIN_LABELS[bucket.value as DrivetrainType] ?? bucket.value,
      count: bucket.count,
    }));
  }, [facetsData]);

  const sidebarContent = (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-gray-200 p-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-gray-900">Filters</h2>
          {activeFilterCount > 0 && (
            <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
              {activeFilterCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {activeFilterCount > 0 && (
            <button
              type="button"
              onClick={handleClearAll}
              className="text-sm font-medium text-blue-600 hover:text-blue-700"
              aria-label="Clear all filters"
            >
              Clear All
            </button>
          )}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-500 lg:hidden"
              aria-label="Close filters"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="divide-y divide-gray-200">
          <FilterSection
            id="make"
            label="Make"
            isExpanded={expandedSections['make'] ?? false}
            onToggle={toggleSection}
            isLoading={facetsLoading}
          >
            <CheckboxGroup
              options={makeOptions}
              selectedValues={filters.make ?? []}
              onChange={handleMakeChange}
              emptyMessage="No makes available"
            />
          </FilterSection>

          <FilterSection
            id="model"
            label="Model"
            isExpanded={expandedSections['model'] ?? false}
            onToggle={toggleSection}
            isLoading={facetsLoading}
            disabled={!filters.make || filters.make.length === 0}
          >
            <CheckboxGroup
              options={modelOptions}
              selectedValues={filters.model ?? []}
              onChange={handleModelChange}
              emptyMessage="Select a make first"
            />
          </FilterSection>

          <FilterSection
            id="year"
            label="Year"
            isExpanded={expandedSections['year'] ?? false}
            onToggle={toggleSection}
          >
            <RangeSlider
              min={MIN_YEAR}
              max={CURRENT_YEAR}
              value={localYearRange}
              onChange={handleYearRangeChange}
              onCommit={handleYearRangeCommit}
              formatValue={(value) => value.toString()}
            />
          </FilterSection>

          <FilterSection
            id="price"
            label="Price"
            isExpanded={expandedSections['price'] ?? false}
            onToggle={toggleSection}
            isLoading={priceRangeLoading}
          >
            <RangeSlider
              min={priceRangeData?.min ?? 0}
              max={priceRangeData?.max ?? 100000}
              value={localPriceRange}
              onChange={handlePriceRangeChange}
              onCommit={handlePriceRangeCommit}
              formatValue={(value) => `$${value.toLocaleString()}`}
              step={1000}
            />
          </FilterSection>

          <FilterSection
            id="bodyStyle"
            label="Body Style"
            isExpanded={expandedSections['bodyStyle'] ?? false}
            onToggle={toggleSection}
            isLoading={facetsLoading}
          >
            <CheckboxGroup
              options={bodyStyleOptions}
              selectedValues={filters.bodyStyle ?? []}
              onChange={handleBodyStyleChange}
              emptyMessage="No body styles available"
            />
          </FilterSection>

          <FilterSection
            id="fuelType"
            label="Fuel Type"
            isExpanded={expandedSections['fuelType'] ?? false}
            onToggle={toggleSection}
            isLoading={facetsLoading}
          >
            <CheckboxGroup
              options={fuelTypeOptions}
              selectedValues={filters.fuelType ?? []}
              onChange={handleFuelTypeChange}
              emptyMessage="No fuel types available"
            />
          </FilterSection>

          <FilterSection
            id="transmission"
            label="Transmission"
            isExpanded={expandedSections['transmission'] ?? false}
            onToggle={toggleSection}
            isLoading={facetsLoading}
          >
            <CheckboxGroup
              options={transmissionOptions}
              selectedValues={filters.transmission ?? []}
              onChange={handleTransmissionChange}
              emptyMessage="No transmissions available"
            />
          </FilterSection>

          <FilterSection
            id="drivetrain"
            label="Drivetrain"
            isExpanded={expandedSections['drivetrain'] ?? false}
            onToggle={toggleSection}
            isLoading={facetsLoading}
          >
            <CheckboxGroup
              options={drivetrainOptions}
              selectedValues={filters.drivetrain ?? []}
              onChange={handleDrivetrainChange}
              emptyMessage="No drivetrains available"
            />
          </FilterSection>
        </div>
      </div>
    </div>
  );

  if (!isOpen) {
    return <></>;
  }

  return (
    <>
      <div className={`hidden lg:block ${className}`}>
        <div className="sticky top-4 h-[calc(100vh-2rem)] overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          {sidebarContent}
        </div>
      </div>

      <div className="lg:hidden">
        <div
          className={`fixed inset-0 z-40 bg-gray-900 bg-opacity-50 transition-opacity ${
            isOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
          }`}
          onClick={onClose}
          aria-hidden="true"
        />
        <div
          className={`fixed inset-y-0 left-0 z-50 w-full max-w-sm transform bg-white shadow-xl transition-transform ${
            isOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          {sidebarContent}
        </div>
      </div>
    </>
  );
}

interface FilterSectionProps {
  readonly id: string;
  readonly label: string;
  readonly isExpanded: boolean;
  readonly onToggle: (id: string) => void;
  readonly children: React.ReactNode;
  readonly isLoading?: boolean;
  readonly disabled?: boolean;
}

function FilterSection({
  id,
  label,
  isExpanded,
  onToggle,
  children,
  isLoading = false,
  disabled = false,
}: FilterSectionProps): JSX.Element {
  return (
    <div className="border-b border-gray-200 last:border-b-0">
      <button
        type="button"
        onClick={() => onToggle(id)}
        disabled={disabled}
        className="flex w-full items-center justify-between p-4 text-left hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
        aria-expanded={isExpanded}
        aria-controls={`filter-section-${id}`}
      >
        <span className="text-sm font-medium text-gray-900">{label}</span>
        <svg
          className={`h-5 w-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isExpanded && (
        <div id={`filter-section-${id}`} className="px-4 pb-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
            </div>
          ) : (
            children
          )}
        </div>
      )}
    </div>
  );
}

interface CheckboxGroupProps {
  readonly options: readonly FilterOption[];
  readonly selectedValues: readonly string[];
  readonly onChange: (value: string) => void;
  readonly emptyMessage?: string;
}

function CheckboxGroup({
  options,
  selectedValues,
  onChange,
  emptyMessage = 'No options available',
}: CheckboxGroupProps): JSX.Element {
  if (options.length === 0) {
    return <p className="text-sm text-gray-500">{emptyMessage}</p>;
  }

  return (
    <div className="space-y-2">
      {options.map((option) => (
        <label key={option.value} className="flex cursor-pointer items-center gap-2 hover:bg-gray-50 rounded p-1">
          <input
            type="checkbox"
            checked={selectedValues.includes(option.value)}
            onChange={() => onChange(option.value)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
          />
          <span className="flex-1 text-sm text-gray-700">{option.label}</span>
          <span className="text-xs text-gray-500">({option.count})</span>
        </label>
      ))}
    </div>
  );
}

interface RangeSliderProps {
  readonly min: number;
  readonly max: number;
  readonly value: { readonly min: number; readonly max: number };
  readonly onChange: (min: number, max: number) => void;
  readonly onCommit: () => void;
  readonly formatValue: (value: number) => string;
  readonly step?: number;
}

function RangeSlider({
  min,
  max,
  value,
  onChange,
  onCommit,
  formatValue,
  step = 1,
}: RangeSliderProps): JSX.Element {
  const handleMinChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newMin = Number(e.target.value);
      onChange(Math.min(newMin, value.max), value.max);
    },
    [onChange, value.max],
  );

  const handleMaxChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newMax = Number(e.target.value);
      onChange(value.min, Math.max(newMax, value.min));
    },
    [onChange, value.min],
  );

  const minPercent = ((value.min - min) / (max - min)) * 100;
  const maxPercent = ((value.max - min) / (max - min)) * 100;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-gray-700">{formatValue(value.min)}</span>
        <span className="text-gray-400">-</span>
        <span className="font-medium text-gray-700">{formatValue(value.max)}</span>
      </div>

      <div className="relative h-2">
        <div className="absolute h-2 w-full rounded-full bg-gray-200" />
        <div
          className="absolute h-2 rounded-full bg-blue-600"
          style={{
            left: `${minPercent}%`,
            right: `${100 - maxPercent}%`,
          }}
        />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value.min}
          onChange={handleMinChange}
          onMouseUp={onCommit}
          onTouchEnd={onCommit}
          className="pointer-events-none absolute h-2 w-full appearance-none bg-transparent [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-blue-600 [&::-webkit-slider-thumb]:shadow [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:appearance-none [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:bg-blue-600 [&::-moz-range-thumb]:shadow"
          aria-label="Minimum value"
        />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value.max}
          onChange={handleMaxChange}
          onMouseUp={onCommit}
          onTouchEnd={onCommit}
          className="pointer-events-none absolute h-2 w-full appearance-none bg-transparent [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-blue-600 [&::-webkit-slider-thumb]:shadow [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:appearance-none [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:bg-blue-600 [&::-moz-range-thumb]:shadow"
          aria-label="Maximum value"
        />
      </div>
    </div>
  );
}