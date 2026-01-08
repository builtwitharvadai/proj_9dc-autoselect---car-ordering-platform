/**
 * Vehicle Comparison Table Component
 * 
 * Displays side-by-side comparison of up to 4 vehicles with specification details,
 * highlighting differences between vehicles. Features sticky headers, responsive design,
 * and mobile-optimized view.
 * 
 * @module components/VehicleComparison/ComparisonTable
 */

import { useMemo, useRef, useEffect, useState, useCallback } from 'react';
import type { Vehicle, VehicleSpecifications, VehicleFeatures } from '../../types/vehicle';

/**
 * Component props interface
 */
interface ComparisonTableProps {
  readonly vehicles: readonly Vehicle[];
  readonly className?: string;
  readonly onRemoveVehicle?: (vehicleId: string) => void;
  readonly highlightDifferences?: boolean;
  readonly compactMode?: boolean;
}

/**
 * Specification row data structure
 */
interface SpecificationRow {
  readonly label: string;
  readonly category: string;
  readonly values: readonly (string | number | null)[];
  readonly hasDifference: boolean;
  readonly unit?: string;
}

/**
 * Feature row data structure
 */
interface FeatureRow {
  readonly label: string;
  readonly category: string;
  readonly values: readonly boolean[];
  readonly hasDifference: boolean;
}

/**
 * Specification categories for organization
 */
const SPEC_CATEGORIES = {
  BASIC: 'Basic Information',
  ENGINE: 'Engine & Performance',
  FUEL: 'Fuel Economy',
  DIMENSIONS: 'Dimensions',
  CAPACITY: 'Capacity',
} as const;

/**
 * Feature categories for organization
 */
const FEATURE_CATEGORIES = {
  SAFETY: 'Safety Features',
  COMFORT: 'Comfort Features',
  TECHNOLOGY: 'Technology Features',
  ENTERTAINMENT: 'Entertainment',
  EXTERIOR: 'Exterior Features',
  INTERIOR: 'Interior Features',
} as const;

/**
 * Format currency value
 */
function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format number with commas
 */
function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(value);
}

/**
 * Check if values in array are different
 */
function hasDifferentValues<T>(values: readonly T[]): boolean {
  if (values.length <= 1) return false;
  const first = values[0];
  return values.some((value) => value !== first);
}

/**
 * Extract specification rows from vehicles
 */
function extractSpecificationRows(vehicles: readonly Vehicle[]): readonly SpecificationRow[] {
  const rows: SpecificationRow[] = [];

  // Basic Information
  rows.push({
    label: 'Year',
    category: SPEC_CATEGORIES.BASIC,
    values: vehicles.map((v) => v.year),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.year)),
  });

  rows.push({
    label: 'Make',
    category: SPEC_CATEGORIES.BASIC,
    values: vehicles.map((v) => v.make),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.make)),
  });

  rows.push({
    label: 'Model',
    category: SPEC_CATEGORIES.BASIC,
    values: vehicles.map((v) => v.model),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.model)),
  });

  rows.push({
    label: 'Trim',
    category: SPEC_CATEGORIES.BASIC,
    values: vehicles.map((v) => v.trim ?? null),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.trim ?? null)),
  });

  rows.push({
    label: 'Body Style',
    category: SPEC_CATEGORIES.BASIC,
    values: vehicles.map((v) => v.bodyStyle),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.bodyStyle)),
  });

  rows.push({
    label: 'Price',
    category: SPEC_CATEGORIES.BASIC,
    values: vehicles.map((v) => formatCurrency(v.price)),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.price)),
  });

  rows.push({
    label: 'MSRP',
    category: SPEC_CATEGORIES.BASIC,
    values: vehicles.map((v) => formatCurrency(v.msrp)),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.msrp)),
  });

  // Engine & Performance
  rows.push({
    label: 'Engine',
    category: SPEC_CATEGORIES.ENGINE,
    values: vehicles.map((v) => v.specifications.engine),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.specifications.engine)),
  });

  rows.push({
    label: 'Horsepower',
    category: SPEC_CATEGORIES.ENGINE,
    values: vehicles.map((v) => v.specifications.horsepower),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.specifications.horsepower)),
    unit: 'hp',
  });

  rows.push({
    label: 'Torque',
    category: SPEC_CATEGORIES.ENGINE,
    values: vehicles.map((v) => v.specifications.torque),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.specifications.torque)),
    unit: 'lb-ft',
  });

  rows.push({
    label: 'Transmission',
    category: SPEC_CATEGORIES.ENGINE,
    values: vehicles.map((v) => v.specifications.transmission),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.specifications.transmission)),
  });

  rows.push({
    label: 'Drivetrain',
    category: SPEC_CATEGORIES.ENGINE,
    values: vehicles.map((v) => v.specifications.drivetrain.toUpperCase()),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.specifications.drivetrain)),
  });

  rows.push({
    label: 'Fuel Type',
    category: SPEC_CATEGORIES.ENGINE,
    values: vehicles.map((v) => v.specifications.fuelType),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.specifications.fuelType)),
  });

  // Fuel Economy
  rows.push({
    label: 'City MPG',
    category: SPEC_CATEGORIES.FUEL,
    values: vehicles.map((v) => v.specifications.fuelEconomy.city),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.specifications.fuelEconomy.city)),
    unit: 'mpg',
  });

  rows.push({
    label: 'Highway MPG',
    category: SPEC_CATEGORIES.FUEL,
    values: vehicles.map((v) => v.specifications.fuelEconomy.highway),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.specifications.fuelEconomy.highway)),
    unit: 'mpg',
  });

  rows.push({
    label: 'Combined MPG',
    category: SPEC_CATEGORIES.FUEL,
    values: vehicles.map((v) => v.specifications.fuelEconomy.combined),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.specifications.fuelEconomy.combined)),
    unit: 'mpg',
  });

  // Dimensions
  rows.push({
    label: 'Length',
    category: SPEC_CATEGORIES.DIMENSIONS,
    values: vehicles.map((v) => v.specifications.dimensions.length),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.specifications.dimensions.length)),
    unit: 'in',
  });

  rows.push({
    label: 'Width',
    category: SPEC_CATEGORIES.DIMENSIONS,
    values: vehicles.map((v) => v.specifications.dimensions.width),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.specifications.dimensions.width)),
    unit: 'in',
  });

  rows.push({
    label: 'Height',
    category: SPEC_CATEGORIES.DIMENSIONS,
    values: vehicles.map((v) => v.specifications.dimensions.height),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.specifications.dimensions.height)),
    unit: 'in',
  });

  rows.push({
    label: 'Wheelbase',
    category: SPEC_CATEGORIES.DIMENSIONS,
    values: vehicles.map((v) => v.specifications.dimensions.wheelbase),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.specifications.dimensions.wheelbase)),
    unit: 'in',
  });

  if (vehicles.some((v) => v.specifications.dimensions.groundClearance !== undefined)) {
    rows.push({
      label: 'Ground Clearance',
      category: SPEC_CATEGORIES.DIMENSIONS,
      values: vehicles.map((v) => v.specifications.dimensions.groundClearance ?? null),
      hasDifference: hasDifferentValues(
        vehicles.map((v) => v.specifications.dimensions.groundClearance ?? null)
      ),
      unit: 'in',
    });
  }

  if (vehicles.some((v) => v.specifications.dimensions.cargoVolume !== undefined)) {
    rows.push({
      label: 'Cargo Volume',
      category: SPEC_CATEGORIES.DIMENSIONS,
      values: vehicles.map((v) => v.specifications.dimensions.cargoVolume ?? null),
      hasDifference: hasDifferentValues(
        vehicles.map((v) => v.specifications.dimensions.cargoVolume ?? null)
      ),
      unit: 'cu ft',
    });
  }

  // Capacity
  rows.push({
    label: 'Seating Capacity',
    category: SPEC_CATEGORIES.CAPACITY,
    values: vehicles.map((v) => v.specifications.seatingCapacity),
    hasDifference: hasDifferentValues(vehicles.map((v) => v.specifications.seatingCapacity)),
    unit: 'seats',
  });

  if (vehicles.some((v) => v.specifications.curbWeight !== undefined)) {
    rows.push({
      label: 'Curb Weight',
      category: SPEC_CATEGORIES.CAPACITY,
      values: vehicles.map((v) => v.specifications.curbWeight ?? null),
      hasDifference: hasDifferentValues(vehicles.map((v) => v.specifications.curbWeight ?? null)),
      unit: 'lbs',
    });
  }

  if (vehicles.some((v) => v.specifications.towingCapacity !== undefined)) {
    rows.push({
      label: 'Towing Capacity',
      category: SPEC_CATEGORIES.CAPACITY,
      values: vehicles.map((v) => v.specifications.towingCapacity ?? null),
      hasDifference: hasDifferentValues(
        vehicles.map((v) => v.specifications.towingCapacity ?? null)
      ),
      unit: 'lbs',
    });
  }

  return rows;
}

/**
 * Extract feature rows from vehicles
 */
function extractFeatureRows(vehicles: readonly Vehicle[]): readonly FeatureRow[] {
  const rows: FeatureRow[] = [];
  const allFeatures = new Set<string>();

  // Collect all unique features
  vehicles.forEach((vehicle) => {
    Object.values(vehicle.features).forEach((featureList) => {
      featureList.forEach((feature) => allFeatures.add(feature));
    });
  });

  // Create rows for each feature category
  const featuresByCategory: Record<string, string[]> = {
    [FEATURE_CATEGORIES.SAFETY]: [],
    [FEATURE_CATEGORIES.COMFORT]: [],
    [FEATURE_CATEGORIES.TECHNOLOGY]: [],
    [FEATURE_CATEGORIES.ENTERTAINMENT]: [],
    [FEATURE_CATEGORIES.EXTERIOR]: [],
    [FEATURE_CATEGORIES.INTERIOR]: [],
  };

  vehicles.forEach((vehicle) => {
    featuresByCategory[FEATURE_CATEGORIES.SAFETY].push(...vehicle.features.safety);
    featuresByCategory[FEATURE_CATEGORIES.COMFORT].push(...vehicle.features.comfort);
    featuresByCategory[FEATURE_CATEGORIES.TECHNOLOGY].push(...vehicle.features.technology);
    featuresByCategory[FEATURE_CATEGORIES.ENTERTAINMENT].push(...vehicle.features.entertainment);
    featuresByCategory[FEATURE_CATEGORIES.EXTERIOR].push(...vehicle.features.exterior);
    featuresByCategory[FEATURE_CATEGORIES.INTERIOR].push(...vehicle.features.interior);
  });

  // Create rows for each unique feature
  allFeatures.forEach((feature) => {
    let category = FEATURE_CATEGORIES.SAFETY;

    // Determine category
    for (const [cat, features] of Object.entries(featuresByCategory)) {
      if (features.includes(feature)) {
        category = cat as keyof typeof FEATURE_CATEGORIES;
        break;
      }
    }

    const values = vehicles.map((vehicle) => {
      return Object.values(vehicle.features).some((featureList) => featureList.includes(feature));
    });

    rows.push({
      label: feature,
      category,
      values,
      hasDifference: hasDifferentValues(values),
    });
  });

  return rows.sort((a, b) => {
    if (a.category !== b.category) {
      return a.category.localeCompare(b.category);
    }
    return a.label.localeCompare(b.label);
  });
}

/**
 * Format specification value for display
 */
function formatSpecValue(value: string | number | null, unit?: string): string {
  if (value === null) return '—';
  if (typeof value === 'number') {
    const formatted = formatNumber(value);
    return unit ? `${formatted} ${unit}` : formatted;
  }
  return value;
}

/**
 * Main comparison table component
 */
export default function ComparisonTable({
  vehicles,
  className = '',
  onRemoveVehicle,
  highlightDifferences = true,
  compactMode = false,
}: ComparisonTableProps): JSX.Element {
  const tableRef = useRef<HTMLDivElement>(null);
  const [isSticky, setIsSticky] = useState(false);

  // Extract specification and feature rows
  const specificationRows = useMemo(() => extractSpecificationRows(vehicles), [vehicles]);
  const featureRows = useMemo(() => extractFeatureRows(vehicles), [vehicles]);

  // Group rows by category
  const groupedSpecs = useMemo(() => {
    const groups: Record<string, SpecificationRow[]> = {};
    specificationRows.forEach((row) => {
      if (!groups[row.category]) {
        groups[row.category] = [];
      }
      groups[row.category].push(row);
    });
    return groups;
  }, [specificationRows]);

  const groupedFeatures = useMemo(() => {
    const groups: Record<string, FeatureRow[]> = {};
    featureRows.forEach((row) => {
      if (!groups[row.category]) {
        groups[row.category] = [];
      }
      groups[row.category].push(row);
    });
    return groups;
  }, [featureRows]);

  // Handle sticky header on scroll
  useEffect(() => {
    const handleScroll = () => {
      if (tableRef.current) {
        const rect = tableRef.current.getBoundingClientRect();
        setIsSticky(rect.top <= 0);
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Handle remove vehicle
  const handleRemove = useCallback(
    (vehicleId: string) => {
      onRemoveVehicle?.(vehicleId);
    },
    [onRemoveVehicle]
  );

  if (vehicles.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 text-lg">No vehicles to compare</p>
      </div>
    );
  }

  return (
    <div ref={tableRef} className={`comparison-table ${className}`}>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          {/* Vehicle Headers */}
          <thead className={`bg-white ${isSticky ? 'sticky top-0 shadow-md z-10' : ''}`}>
            <tr>
              <th className="p-4 text-left font-semibold text-gray-700 border-b-2 border-gray-200 min-w-[200px]">
                Specification
              </th>
              {vehicles.map((vehicle) => (
                <th
                  key={vehicle.id}
                  className="p-4 text-center border-b-2 border-gray-200 min-w-[200px]"
                >
                  <div className="space-y-2">
                    <img
                      src={vehicle.imageUrl}
                      alt={`${vehicle.year} ${vehicle.make} ${vehicle.model}`}
                      className="w-full h-32 object-cover rounded-lg"
                      loading="lazy"
                    />
                    <div className="font-semibold text-gray-900">
                      {vehicle.year} {vehicle.make}
                    </div>
                    <div className="text-sm text-gray-600">{vehicle.model}</div>
                    {vehicle.trim && <div className="text-xs text-gray-500">{vehicle.trim}</div>}
                    {onRemoveVehicle && (
                      <button
                        onClick={() => handleRemove(vehicle.id)}
                        className="text-xs text-red-600 hover:text-red-800 underline"
                        aria-label={`Remove ${vehicle.year} ${vehicle.make} ${vehicle.model} from comparison`}
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>

          {/* Specifications */}
          <tbody>
            {Object.entries(groupedSpecs).map(([category, rows]) => (
              <React.Fragment key={category}>
                <tr className="bg-gray-50">
                  <td
                    colSpan={vehicles.length + 1}
                    className="p-3 font-semibold text-gray-700 border-b border-gray-200"
                  >
                    {category}
                  </td>
                </tr>
                {rows.map((row, index) => (
                  <tr
                    key={`${category}-${index}`}
                    className={`${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-blue-50 transition-colors`}
                  >
                    <td className="p-3 text-sm text-gray-700 border-b border-gray-100">
                      {row.label}
                    </td>
                    {row.values.map((value, vIndex) => (
                      <td
                        key={vIndex}
                        className={`p-3 text-sm text-center border-b border-gray-100 ${
                          highlightDifferences && row.hasDifference
                            ? 'bg-yellow-50 font-medium'
                            : ''
                        }`}
                      >
                        {formatSpecValue(value, row.unit)}
                      </td>
                    ))}
                  </tr>
                ))}
              </React.Fragment>
            ))}

            {/* Features */}
            {Object.entries(groupedFeatures).map(([category, rows]) => (
              <React.Fragment key={category}>
                <tr className="bg-gray-50">
                  <td
                    colSpan={vehicles.length + 1}
                    className="p-3 font-semibold text-gray-700 border-b border-gray-200"
                  >
                    {category}
                  </td>
                </tr>
                {rows.map((row, index) => (
                  <tr
                    key={`${category}-${index}`}
                    className={`${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-blue-50 transition-colors`}
                  >
                    <td className="p-3 text-sm text-gray-700 border-b border-gray-100">
                      {row.label}
                    </td>
                    {row.values.map((value, vIndex) => (
                      <td
                        key={vIndex}
                        className={`p-3 text-sm text-center border-b border-gray-100 ${
                          highlightDifferences && row.hasDifference
                            ? 'bg-yellow-50 font-medium'
                            : ''
                        }`}
                      >
                        {value ? (
                          <span className="text-green-600 font-semibold">✓</span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      {highlightDifferences && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <div className="w-4 h-4 bg-yellow-50 border border-yellow-200 rounded"></div>
            <span>Highlighted rows indicate differences between vehicles</span>
          </div>
        </div>
      )}
    </div>
  );
}

// Add React import for Fragment
import React from 'react';