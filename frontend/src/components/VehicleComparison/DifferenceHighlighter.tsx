/**
 * DifferenceHighlighter Component
 * 
 * Utility component that compares vehicle specifications and highlights differences
 * with appropriate styling and indicators. Provides visual feedback for side-by-side
 * vehicle comparison with accessibility support.
 */

import React, { useMemo } from 'react';
import type { Vehicle, VehicleSpecifications } from '../../types/vehicle';

/**
 * Difference type enumeration
 */
type DifferenceType = 'higher' | 'lower' | 'different' | 'same';

/**
 * Comparison result for a single specification field
 */
interface ComparisonResult {
  readonly value: string | number | boolean;
  readonly differenceType: DifferenceType;
  readonly isHighlighted: boolean;
  readonly comparisonValue?: string | number;
}

/**
 * Props for DifferenceHighlighter component
 */
interface DifferenceHighlighterProps {
  readonly value: string | number | boolean;
  readonly vehicles: readonly Vehicle[];
  readonly currentVehicleIndex: number;
  readonly fieldPath: string;
  readonly className?: string;
  readonly showIndicator?: boolean;
  readonly highlightBest?: boolean;
  readonly formatValue?: (value: string | number | boolean) => string;
}

/**
 * Props for DifferenceIndicator component
 */
interface DifferenceIndicatorProps {
  readonly type: DifferenceType;
  readonly className?: string;
}

/**
 * Get nested property value from object using dot notation path
 */
function getNestedValue(
  obj: Record<string, unknown>,
  path: string,
): string | number | boolean | undefined {
  const keys = path.split('.');
  let current: unknown = obj;

  for (const key of keys) {
    if (current === null || current === undefined) {
      return undefined;
    }
    if (typeof current === 'object' && key in current) {
      current = (current as Record<string, unknown>)[key];
    } else {
      return undefined;
    }
  }

  if (
    typeof current === 'string' ||
    typeof current === 'number' ||
    typeof current === 'boolean'
  ) {
    return current;
  }

  return undefined;
}

/**
 * Compare numeric values and determine difference type
 */
function compareNumericValues(
  currentValue: number,
  otherValues: readonly number[],
  higherIsBetter: boolean = true,
): DifferenceType {
  if (otherValues.length === 0) {
    return 'same';
  }

  const allValues = [currentValue, ...otherValues];
  const max = Math.max(...allValues);
  const min = Math.min(...allValues);

  if (max === min) {
    return 'same';
  }

  if (higherIsBetter) {
    if (currentValue === max) return 'higher';
    if (currentValue === min) return 'lower';
  } else {
    if (currentValue === min) return 'higher';
    if (currentValue === max) return 'lower';
  }

  return 'different';
}

/**
 * Determine if higher values are better for a given field
 */
function isHigherBetter(fieldPath: string): boolean {
  const lowerIsBetterFields = [
    'price',
    'msrp',
    'specifications.fuelEconomy.city',
    'specifications.fuelEconomy.highway',
    'specifications.fuelEconomy.combined',
    'specifications.curbWeight',
  ];

  return !lowerIsBetterFields.some((field) => fieldPath.includes(field));
}

/**
 * Compare values across vehicles and determine difference type
 */
function compareValues(
  currentValue: string | number | boolean,
  vehicles: readonly Vehicle[],
  currentIndex: number,
  fieldPath: string,
  highlightBest: boolean,
): ComparisonResult {
  const otherValues = vehicles
    .map((vehicle, index) => {
      if (index === currentIndex) return undefined;
      const vehicleObj = vehicle as unknown as Record<string, unknown>;
      return getNestedValue(vehicleObj, fieldPath);
    })
    .filter(
      (v): v is string | number | boolean => v !== undefined,
    );

  if (otherValues.length === 0) {
    return {
      value: currentValue,
      differenceType: 'same',
      isHighlighted: false,
    };
  }

  // Numeric comparison
  if (typeof currentValue === 'number') {
    const numericOthers = otherValues.filter(
      (v): v is number => typeof v === 'number',
    );

    if (numericOthers.length === 0) {
      return {
        value: currentValue,
        differenceType: 'same',
        isHighlighted: false,
      };
    }

    const higherIsBetter = isHigherBetter(fieldPath);
    const differenceType = compareNumericValues(
      currentValue,
      numericOthers,
      higherIsBetter,
    );

    return {
      value: currentValue,
      differenceType,
      isHighlighted: highlightBest && differenceType === 'higher',
      comparisonValue:
        differenceType !== 'same'
          ? higherIsBetter
            ? Math.max(...numericOthers)
            : Math.min(...numericOthers)
          : undefined,
    };
  }

  // String/Boolean comparison
  const allSame = otherValues.every((v) => v === currentValue);

  return {
    value: currentValue,
    differenceType: allSame ? 'same' : 'different',
    isHighlighted: false,
  };
}

/**
 * Format value for display
 */
function defaultFormatValue(value: string | number | boolean): string {
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  if (typeof value === 'number') {
    return value.toLocaleString();
  }
  return String(value);
}

/**
 * Get CSS classes for difference type
 */
function getDifferenceClasses(
  type: DifferenceType,
  isHighlighted: boolean,
): string {
  const baseClasses = 'transition-colors duration-200';

  if (isHighlighted) {
    return `${baseClasses} bg-green-50 text-green-900 font-semibold border-l-4 border-green-500 pl-2`;
  }

  switch (type) {
    case 'higher':
      return `${baseClasses} text-green-700 font-medium`;
    case 'lower':
      return `${baseClasses} text-red-700 font-medium`;
    case 'different':
      return `${baseClasses} text-amber-700 font-medium`;
    case 'same':
    default:
      return `${baseClasses} text-gray-700`;
  }
}

/**
 * Difference indicator icon component
 */
function DifferenceIndicator({
  type,
  className = '',
}: DifferenceIndicatorProps): JSX.Element | null {
  if (type === 'same') {
    return null;
  }

  const icons = {
    higher: (
      <svg
        className="w-4 h-4 text-green-600"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M5 10l7-7m0 0l7 7m-7-7v18"
        />
      </svg>
    ),
    lower: (
      <svg
        className="w-4 h-4 text-red-600"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M19 14l-7 7m0 0l-7-7m7 7V3"
        />
      </svg>
    ),
    different: (
      <svg
        className="w-4 h-4 text-amber-600"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"
        />
      </svg>
    ),
  };

  const labels = {
    higher: 'Better value',
    lower: 'Lower value',
    different: 'Different value',
  };

  return (
    <span
      className={`inline-flex items-center ml-1 ${className}`}
      aria-label={labels[type]}
      title={labels[type]}
    >
      {icons[type]}
    </span>
  );
}

/**
 * DifferenceHighlighter Component
 * 
 * Highlights differences between vehicle specifications with visual indicators
 * and appropriate styling based on comparison results.
 */
export default function DifferenceHighlighter({
  value,
  vehicles,
  currentVehicleIndex,
  fieldPath,
  className = '',
  showIndicator = true,
  highlightBest = true,
  formatValue = defaultFormatValue,
}: DifferenceHighlighterProps): JSX.Element {
  // Memoize comparison result to avoid recalculation
  const comparisonResult = useMemo(
    () =>
      compareValues(
        value,
        vehicles,
        currentVehicleIndex,
        fieldPath,
        highlightBest,
      ),
    [value, vehicles, currentVehicleIndex, fieldPath, highlightBest],
  );

  const { differenceType, isHighlighted } = comparisonResult;
  const formattedValue = formatValue(value);

  const differenceClasses = getDifferenceClasses(differenceType, isHighlighted);

  // Accessibility label for screen readers
  const ariaLabel = useMemo(() => {
    if (differenceType === 'same') {
      return `${formattedValue} - same across all vehicles`;
    }
    if (isHighlighted) {
      return `${formattedValue} - best value`;
    }
    const labels = {
      higher: 'higher than others',
      lower: 'lower than others',
      different: 'different from others',
    };
    return `${formattedValue} - ${labels[differenceType] ?? 'different'}`;
  }, [formattedValue, differenceType, isHighlighted]);

  return (
    <span
      className={`inline-flex items-center ${differenceClasses} ${className}`}
      aria-label={ariaLabel}
      role="text"
    >
      <span>{formattedValue}</span>
      {showIndicator && (
        <DifferenceIndicator type={differenceType} className="ml-1" />
      )}
    </span>
  );
}

/**
 * Export utility functions for external use
 */
export { compareValues, getNestedValue, isHigherBetter, defaultFormatValue };
export type { ComparisonResult, DifferenceType };