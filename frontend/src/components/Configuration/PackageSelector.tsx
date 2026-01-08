/**
 * Package Selector Component
 * Displays bundled package options with included features, pricing, and savings
 * Provides package compatibility validation and visual indicators
 */

import { memo, useCallback, useMemo, useState } from 'react';
import type { Package } from '../../types/configuration';

/**
 * Component props interface
 */
interface PackageSelectorProps {
  readonly packages: readonly Package[];
  readonly selectedPackageIds: readonly string[];
  readonly onPackageToggle: (packageId: string) => void;
  readonly trimId?: string;
  readonly year?: number;
  readonly isLoading?: boolean;
  readonly className?: string;
  readonly maxSelections?: number;
  readonly showSavings?: boolean;
  readonly compactMode?: boolean;
}

/**
 * Package card display state
 */
interface PackageCardState {
  readonly isExpanded: boolean;
  readonly isHovered: boolean;
}

/**
 * Format currency value
 */
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Format discount percentage
 */
function formatDiscount(percentage: number): string {
  return `${percentage.toFixed(0)}%`;
}

/**
 * Check if package is compatible with current configuration
 */
function isPackageCompatible(
  pkg: Package,
  trimId: string | undefined,
  year: number | undefined,
): boolean {
  const trimCompatible =
    !pkg.compatibleTrims || pkg.compatibleTrims.length === 0 || !trimId
      ? true
      : pkg.compatibleTrims.includes(trimId);

  const yearCompatible =
    !pkg.compatibleYears || pkg.compatibleYears.length === 0 || !year
      ? true
      : pkg.compatibleYears.includes(year);

  return trimCompatible && yearCompatible;
}

/**
 * Package card component
 */
const PackageCard = memo(function PackageCard({
  package: pkg,
  isSelected,
  isCompatible,
  onToggle,
  showSavings,
  compactMode,
}: {
  readonly package: Package;
  readonly isSelected: boolean;
  readonly isCompatible: boolean;
  readonly onToggle: () => void;
  readonly showSavings: boolean;
  readonly compactMode: boolean;
}): JSX.Element {
  const [cardState, setCardState] = useState<PackageCardState>({
    isExpanded: false,
    isHovered: false,
  });

  const handleMouseEnter = useCallback(() => {
    setCardState((prev) => ({ ...prev, isHovered: true }));
  }, []);

  const handleMouseLeave = useCallback(() => {
    setCardState((prev) => ({ ...prev, isHovered: false }));
  }, []);

  const handleExpandToggle = useCallback(() => {
    setCardState((prev) => ({ ...prev, isExpanded: !prev.isExpanded }));
  }, []);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        if (isCompatible) {
          onToggle();
        }
      }
    },
    [isCompatible, onToggle],
  );

  const cardClasses = useMemo(() => {
    const base = 'relative rounded-lg border-2 transition-all duration-200';
    const size = compactMode ? 'p-4' : 'p-6';
    const state = isSelected
      ? 'border-blue-500 bg-blue-50 shadow-md'
      : cardState.isHovered && isCompatible
        ? 'border-gray-300 bg-gray-50 shadow-sm'
        : 'border-gray-200 bg-white';
    const cursor = isCompatible ? 'cursor-pointer' : 'cursor-not-allowed opacity-60';

    return `${base} ${size} ${state} ${cursor}`;
  }, [compactMode, isSelected, cardState.isHovered, isCompatible]);

  return (
    <div
      className={cardClasses}
      onClick={isCompatible ? onToggle : undefined}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={isCompatible ? 0 : -1}
      aria-pressed={isSelected}
      aria-disabled={!isCompatible}
      aria-label={`${pkg.name} package, ${formatCurrency(pkg.price)}${!isCompatible ? ', not compatible' : ''}`}
    >
      {/* Popular badge */}
      {pkg.isPopular && (
        <div className="absolute -top-3 left-4 rounded-full bg-blue-600 px-3 py-1 text-xs font-semibold text-white shadow-sm">
          Popular
        </div>
      )}

      {/* Incompatible badge */}
      {!isCompatible && (
        <div className="absolute -top-3 right-4 rounded-full bg-red-600 px-3 py-1 text-xs font-semibold text-white shadow-sm">
          Not Compatible
        </div>
      )}

      {/* Header */}
      <div className="mb-4 flex items-start justify-between">
        <div className="flex-1">
          <h3 className={`font-semibold text-gray-900 ${compactMode ? 'text-lg' : 'text-xl'}`}>
            {pkg.name}
          </h3>
          {!compactMode && <p className="mt-1 text-sm text-gray-600">{pkg.description}</p>}
        </div>

        {/* Selection indicator */}
        <div
          className={`ml-4 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border-2 transition-colors ${
            isSelected
              ? 'border-blue-600 bg-blue-600'
              : isCompatible
                ? 'border-gray-300 bg-white'
                : 'border-gray-200 bg-gray-100'
          }`}
          aria-hidden="true"
        >
          {isSelected && (
            <svg className="h-4 w-4 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                clipRule="evenodd"
              />
            </svg>
          )}
        </div>
      </div>

      {/* Package image */}
      {pkg.imageUrl && !compactMode && (
        <div className="mb-4 overflow-hidden rounded-md">
          <img
            src={pkg.imageUrl}
            alt={`${pkg.name} package`}
            className="h-48 w-full object-cover"
            loading="lazy"
          />
        </div>
      )}

      {/* Pricing */}
      <div className="mb-4">
        <div className="flex items-baseline gap-2">
          <span className={`font-bold text-gray-900 ${compactMode ? 'text-xl' : 'text-2xl'}`}>
            {formatCurrency(pkg.price)}
          </span>
          {showSavings && pkg.savings > 0 && (
            <span className="text-sm text-green-600">
              Save {formatCurrency(pkg.savings)} ({formatDiscount(pkg.discountPercentage)})
            </span>
          )}
        </div>
      </div>

      {/* Included options */}
      <div className="mb-4">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            handleExpandToggle();
          }}
          className="flex w-full items-center justify-between text-sm font-medium text-gray-700 hover:text-gray-900"
          aria-expanded={cardState.isExpanded}
          aria-controls={`package-options-${pkg.id}`}
        >
          <span>Includes {pkg.includedOptions.length} options</span>
          <svg
            className={`h-5 w-5 transition-transform ${cardState.isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {cardState.isExpanded && (
          <ul
            id={`package-options-${pkg.id}`}
            className="mt-2 space-y-1 text-sm text-gray-600"
            role="list"
          >
            {pkg.includedOptions.map((optionId) => (
              <li key={optionId} className="flex items-start">
                <svg
                  className="mr-2 mt-0.5 h-4 w-4 flex-shrink-0 text-green-500"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
                <span>Option {optionId}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Compatibility info */}
      {!isCompatible && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">
          <p className="font-medium">Not compatible with current selection</p>
          {pkg.compatibleTrims && pkg.compatibleTrims.length > 0 && (
            <p className="mt-1 text-xs">
              Available for: {pkg.compatibleTrims.join(', ')} trims
            </p>
          )}
          {pkg.compatibleYears && pkg.compatibleYears.length > 0 && (
            <p className="mt-1 text-xs">Available for: {pkg.compatibleYears.join(', ')} years</p>
          )}
        </div>
      )}
    </div>
  );
});

/**
 * Package Selector Component
 */
export default function PackageSelector({
  packages,
  selectedPackageIds,
  onPackageToggle,
  trimId,
  year,
  isLoading = false,
  className = '',
  maxSelections,
  showSavings = true,
  compactMode = false,
}: PackageSelectorProps): JSX.Element {
  // Filter and sort packages
  const sortedPackages = useMemo(() => {
    return [...packages].sort((a, b) => {
      // Popular packages first
      if (a.isPopular && !b.isPopular) return -1;
      if (!a.isPopular && b.isPopular) return 1;

      // Then by compatibility
      const aCompatible = isPackageCompatible(a, trimId, year);
      const bCompatible = isPackageCompatible(b, trimId, year);
      if (aCompatible && !bCompatible) return -1;
      if (!aCompatible && bCompatible) return 1;

      // Then by price (ascending)
      return a.price - b.price;
    });
  }, [packages, trimId, year]);

  // Calculate statistics
  const stats = useMemo(() => {
    const compatible = sortedPackages.filter((pkg) => isPackageCompatible(pkg, trimId, year));
    const totalSavings = selectedPackageIds.reduce((sum, id) => {
      const pkg = packages.find((p) => p.id === id);
      return sum + (pkg?.savings ?? 0);
    }, 0);

    return {
      total: packages.length,
      compatible: compatible.length,
      selected: selectedPackageIds.length,
      totalSavings,
    };
  }, [sortedPackages, trimId, year, selectedPackageIds, packages]);

  // Handle package toggle
  const handlePackageToggle = useCallback(
    (packageId: string) => {
      const pkg = packages.find((p) => p.id === packageId);
      if (!pkg) return;

      const isCompatible = isPackageCompatible(pkg, trimId, year);
      if (!isCompatible) return;

      const isSelected = selectedPackageIds.includes(packageId);
      if (!isSelected && maxSelections && selectedPackageIds.length >= maxSelections) {
        return;
      }

      onPackageToggle(packageId);
    },
    [packages, trimId, year, selectedPackageIds, maxSelections, onPackageToggle],
  );

  if (isLoading) {
    return (
      <div className={`space-y-4 ${className}`}>
        <div className="h-8 w-48 animate-pulse rounded bg-gray-200" />
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-96 animate-pulse rounded-lg bg-gray-200" />
          ))}
        </div>
      </div>
    );
  }

  if (packages.length === 0) {
    return (
      <div className={`rounded-lg border-2 border-dashed border-gray-300 p-12 text-center ${className}`}>
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
          />
        </svg>
        <h3 className="mt-4 text-lg font-medium text-gray-900">No packages available</h3>
        <p className="mt-2 text-sm text-gray-500">
          There are no package options available for this vehicle configuration.
        </p>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Select Packages</h2>
          <p className="mt-1 text-sm text-gray-600">
            Choose bundled options to save money and enhance your vehicle
          </p>
        </div>

        {/* Statistics */}
        <div className="flex gap-4 text-sm">
          <div className="text-center">
            <div className="font-semibold text-gray-900">{stats.selected}</div>
            <div className="text-gray-500">Selected</div>
          </div>
          <div className="text-center">
            <div className="font-semibold text-gray-900">{stats.compatible}</div>
            <div className="text-gray-500">Compatible</div>
          </div>
          {showSavings && stats.totalSavings > 0 && (
            <div className="text-center">
              <div className="font-semibold text-green-600">{formatCurrency(stats.totalSavings)}</div>
              <div className="text-gray-500">Total Savings</div>
            </div>
          )}
        </div>
      </div>

      {/* Selection limit warning */}
      {maxSelections && selectedPackageIds.length >= maxSelections && (
        <div className="rounded-md bg-yellow-50 p-4">
          <div className="flex">
            <svg
              className="h-5 w-5 text-yellow-400"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            <div className="ml-3">
              <p className="text-sm font-medium text-yellow-800">
                Maximum packages selected ({maxSelections})
              </p>
              <p className="mt-1 text-sm text-yellow-700">
                Deselect a package to choose a different one.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Package grid */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {sortedPackages.map((pkg) => (
          <PackageCard
            key={pkg.id}
            package={pkg}
            isSelected={selectedPackageIds.includes(pkg.id)}
            isCompatible={isPackageCompatible(pkg, trimId, year)}
            onToggle={() => handlePackageToggle(pkg.id)}
            showSavings={showSavings}
            compactMode={compactMode}
          />
        ))}
      </div>

      {/* Compatibility info */}
      {stats.compatible < stats.total && (
        <div className="rounded-md bg-blue-50 p-4">
          <div className="flex">
            <svg
              className="h-5 w-5 text-blue-400"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
            <div className="ml-3">
              <p className="text-sm font-medium text-blue-800">
                {stats.total - stats.compatible} package{stats.total - stats.compatible !== 1 ? 's' : ''} not
                compatible
              </p>
              <p className="mt-1 text-sm text-blue-700">
                Some packages are only available for specific trims or model years.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}