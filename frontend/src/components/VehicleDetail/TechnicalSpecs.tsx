/**
 * TechnicalSpecs Component
 * 
 * Displays comprehensive vehicle technical specifications in a responsive table format.
 * Organizes specifications into logical categories with proper formatting and accessibility.
 * 
 * @module components/VehicleDetail/TechnicalSpecs
 */

import React from 'react';
import type { VehicleSpecifications } from '../../types/vehicle';

/**
 * Props for the TechnicalSpecs component
 */
interface TechnicalSpecsProps {
  readonly specifications: VehicleSpecifications;
  readonly className?: string;
}

/**
 * Specification row data structure
 */
interface SpecRow {
  readonly label: string;
  readonly value: string | number;
  readonly unit?: string;
}

/**
 * Specification category grouping
 */
interface SpecCategory {
  readonly title: string;
  readonly rows: readonly SpecRow[];
}

/**
 * Format fuel economy value with proper units
 */
function formatFuelEconomy(mpg: number): string {
  return `${mpg} mpg`;
}

/**
 * Format dimension value with proper units
 */
function formatDimension(value: number): string {
  return `${value.toFixed(1)} in`;
}

/**
 * Format weight value with proper units
 */
function formatWeight(value: number): string {
  return `${value.toLocaleString()} lbs`;
}

/**
 * Format capacity value with proper units
 */
function formatCapacity(value: number): string {
  return `${value.toLocaleString()} lbs`;
}

/**
 * Format volume value with proper units
 */
function formatVolume(value: number): string {
  return `${value.toFixed(1)} cu ft`;
}

/**
 * Format transmission type for display
 */
function formatTransmission(transmission: string): string {
  const transmissionMap: Record<string, string> = {
    automatic: 'Automatic',
    manual: 'Manual',
    cvt: 'CVT',
    'dual-clutch': 'Dual-Clutch',
  };
  return transmissionMap[transmission] ?? transmission;
}

/**
 * Format drivetrain type for display
 */
function formatDrivetrain(drivetrain: string): string {
  const drivetrainMap: Record<string, string> = {
    fwd: 'Front-Wheel Drive',
    rwd: 'Rear-Wheel Drive',
    awd: 'All-Wheel Drive',
    '4wd': 'Four-Wheel Drive',
  };
  return drivetrainMap[drivetrain] ?? drivetrain;
}

/**
 * Format fuel type for display
 */
function formatFuelType(fuelType: string): string {
  const fuelTypeMap: Record<string, string> = {
    gasoline: 'Gasoline',
    diesel: 'Diesel',
    electric: 'Electric',
    hybrid: 'Hybrid',
    'plug-in-hybrid': 'Plug-in Hybrid',
  };
  return fuelTypeMap[fuelType] ?? fuelType;
}

/**
 * Build specification categories from vehicle specifications
 */
function buildSpecCategories(specs: VehicleSpecifications): readonly SpecCategory[] {
  const categories: SpecCategory[] = [];

  // Engine & Performance
  const engineRows: SpecRow[] = [
    { label: 'Engine', value: specs.engine },
    { label: 'Horsepower', value: specs.horsepower, unit: 'hp' },
    { label: 'Torque', value: specs.torque, unit: 'lb-ft' },
    { label: 'Transmission', value: formatTransmission(specs.transmission) },
    { label: 'Drivetrain', value: formatDrivetrain(specs.drivetrain) },
  ];
  categories.push({ title: 'Engine & Performance', rows: engineRows });

  // Fuel Economy
  const fuelRows: SpecRow[] = [
    { label: 'Fuel Type', value: formatFuelType(specs.fuelType) },
    { label: 'City MPG', value: formatFuelEconomy(specs.fuelEconomy.city) },
    { label: 'Highway MPG', value: formatFuelEconomy(specs.fuelEconomy.highway) },
    { label: 'Combined MPG', value: formatFuelEconomy(specs.fuelEconomy.combined) },
  ];
  categories.push({ title: 'Fuel Economy', rows: fuelRows });

  // Dimensions
  const dimensionRows: SpecRow[] = [
    { label: 'Length', value: formatDimension(specs.dimensions.length) },
    { label: 'Width', value: formatDimension(specs.dimensions.width) },
    { label: 'Height', value: formatDimension(specs.dimensions.height) },
    { label: 'Wheelbase', value: formatDimension(specs.dimensions.wheelbase) },
  ];

  if (specs.dimensions.groundClearance !== undefined) {
    dimensionRows.push({
      label: 'Ground Clearance',
      value: formatDimension(specs.dimensions.groundClearance),
    });
  }

  if (specs.dimensions.cargoVolume !== undefined) {
    dimensionRows.push({
      label: 'Cargo Volume',
      value: formatVolume(specs.dimensions.cargoVolume),
    });
  }

  categories.push({ title: 'Dimensions', rows: dimensionRows });

  // Capacity & Weight
  const capacityRows: SpecRow[] = [
    { label: 'Seating Capacity', value: specs.seatingCapacity, unit: 'passengers' },
  ];

  if (specs.curbWeight !== undefined) {
    capacityRows.push({
      label: 'Curb Weight',
      value: formatWeight(specs.curbWeight),
    });
  }

  if (specs.towingCapacity !== undefined) {
    capacityRows.push({
      label: 'Towing Capacity',
      value: formatCapacity(specs.towingCapacity),
    });
  }

  categories.push({ title: 'Capacity & Weight', rows: capacityRows });

  // Custom Attributes
  if (specs.customAttributes !== undefined && Object.keys(specs.customAttributes).length > 0) {
    const customRows: SpecRow[] = Object.entries(specs.customAttributes).map(
      ([key, value]) => ({
        label: key
          .split('_')
          .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' '),
        value: String(value),
      })
    );
    categories.push({ title: 'Additional Specifications', rows: customRows });
  }

  return categories;
}

/**
 * TechnicalSpecs Component
 * 
 * Renders a comprehensive table of vehicle technical specifications organized by category.
 * Provides responsive design with proper accessibility attributes.
 */
export default function TechnicalSpecs({
  specifications,
  className = '',
}: TechnicalSpecsProps): JSX.Element {
  const categories = buildSpecCategories(specifications);

  return (
    <div className={`technical-specs ${className}`} role="region" aria-label="Technical Specifications">
      <div className="space-y-8">
        {categories.map((category) => (
          <div key={category.title} className="spec-category">
            <h3 className="text-xl font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              {category.title}
            </h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <tbody className="bg-white divide-y divide-gray-200">
                  {category.rows.map((row, index) => (
                    <tr
                      key={`${category.title}-${row.label}`}
                      className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 w-1/2">
                        {row.label}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 w-1/2">
                        {row.value}
                        {row.unit !== undefined && (
                          <span className="ml-1 text-gray-500">{row.unit}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>

      {/* Mobile-optimized view */}
      <style jsx>{`
        @media (max-width: 640px) {
          .technical-specs table {
            font-size: 0.875rem;
          }
          .technical-specs td {
            padding: 0.75rem 1rem;
          }
          .technical-specs .spec-category h3 {
            font-size: 1.125rem;
          }
        }

        @media (max-width: 480px) {
          .technical-specs table {
            display: block;
          }
          .technical-specs tbody {
            display: block;
          }
          .technical-specs tr {
            display: flex;
            flex-direction: column;
            margin-bottom: 1rem;
            border: 1px solid #e5e7eb;
            border-radius: 0.375rem;
            overflow: hidden;
          }
          .technical-specs td {
            display: block;
            width: 100% !important;
            border: none;
          }
          .technical-specs td:first-child {
            background-color: #f9fafb;
            font-weight: 600;
            padding-bottom: 0.5rem;
          }
          .technical-specs td:last-child {
            padding-top: 0.5rem;
          }
        }
      `}</style>
    </div>
  );
}