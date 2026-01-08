/**
 * Feature selection component for vehicle configuration
 * Provides categorized feature options with validation, compatibility checking,
 * and package indicators for the configuration wizard
 */

import { useMemo, useState, useCallback, useEffect } from 'react';
import type {
  VehicleOption,
  OptionCategory,
  OPTION_CATEGORY_NAMES,
} from '../../types/configuration';

/**
 * Props for the FeatureSelector component
 */
interface FeatureSelectorProps {
  readonly options: readonly VehicleOption[];
  readonly selectedOptionIds: readonly string[];
  readonly selectedPackageIds: readonly string[];
  readonly packageOptions: ReadonlyMap<string, readonly string[]>;
  readonly onOptionToggle: (optionId: string) => void;
  readonly className?: string;
  readonly disabled?: boolean;
}

/**
 * Categorized options structure
 */
interface CategorizedOptions {
  readonly [K in OptionCategory]?: readonly VehicleOption[];
}

/**
 * Option compatibility state
 */
interface OptionCompatibility {
  readonly isCompatible: boolean;
  readonly reason?: string;
  readonly conflictingOptions?: readonly string[];
}

/**
 * Category display configuration
 */
const CATEGORY_ORDER: readonly OptionCategory[] = [
  'exterior',
  'interior',
  'technology',
  'safety',
  'performance',
  'comfort',
  'entertainment',
] as const;

/**
 * Category icons mapping
 */
const CATEGORY_ICONS: Record<OptionCategory, string> = {
  exterior: '🚗',
  interior: '🪑',
  technology: '💻',
  safety: '🛡️',
  performance: '⚡',
  comfort: '✨',
  entertainment: '🎵',
} as const;

/**
 * Check if option is included in any selected package
 */
function isOptionInPackage(
  optionId: string,
  selectedPackageIds: readonly string[],
  packageOptions: ReadonlyMap<string, readonly string[]>,
): boolean {
  return selectedPackageIds.some((packageId) => {
    const options = packageOptions.get(packageId);
    return options?.includes(optionId) ?? false;
  });
}

/**
 * Check option compatibility with current selections
 */
function checkOptionCompatibility(
  option: VehicleOption,
  selectedOptionIds: readonly string[],
  allOptions: readonly VehicleOption[],
): OptionCompatibility {
  // Check if option is available
  if (!option.isAvailable) {
    return {
      isCompatible: false,
      reason: 'This option is currently unavailable',
    };
  }

  // Check mutually exclusive options
  if (option.mutuallyExclusiveWith && option.mutuallyExclusiveWith.length > 0) {
    const conflicts = option.mutuallyExclusiveWith.filter((exclusiveId) =>
      selectedOptionIds.includes(exclusiveId),
    );

    if (conflicts.length > 0) {
      const conflictNames = conflicts
        .map((id) => {
          const conflictOption = allOptions.find((opt) => opt.id === id);
          return conflictOption?.name ?? id;
        })
        .join(', ');

      return {
        isCompatible: false,
        reason: `Incompatible with: ${conflictNames}`,
        conflictingOptions: conflicts,
      };
    }
  }

  // Check required options
  if (option.requiredOptions && option.requiredOptions.length > 0) {
    const missingRequired = option.requiredOptions.filter(
      (requiredId) => !selectedOptionIds.includes(requiredId),
    );

    if (missingRequired.length > 0) {
      const requiredNames = missingRequired
        .map((id) => {
          const requiredOption = allOptions.find((opt) => opt.id === id);
          return requiredOption?.name ?? id;
        })
        .join(', ');

      return {
        isCompatible: false,
        reason: `Requires: ${requiredNames}`,
      };
    }
  }

  return { isCompatible: true };
}

/**
 * Categorize options by category
 */
function categorizeOptions(options: readonly VehicleOption[]): CategorizedOptions {
  const categorized: Record<string, VehicleOption[]> = {};

  for (const option of options) {
    const category = option.category;
    if (!categorized[category]) {
      categorized[category] = [];
    }
    categorized[category].push(option);
  }

  // Sort options within each category by name
  for (const category of Object.keys(categorized)) {
    categorized[category].sort((a, b) => a.name.localeCompare(b.name));
  }

  return categorized as CategorizedOptions;
}

/**
 * Format price for display
 */
function formatPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(price);
}

/**
 * FeatureSelector component
 */
export default function FeatureSelector({
  options,
  selectedOptionIds,
  selectedPackageIds,
  packageOptions,
  onOptionToggle,
  className = '',
  disabled = false,
}: FeatureSelectorProps): JSX.Element {
  const [expandedCategories, setExpandedCategories] = useState<Set<OptionCategory>>(
    new Set(CATEGORY_ORDER),
  );

  // Categorize options
  const categorizedOptions = useMemo(() => categorizeOptions(options), [options]);

  // Calculate compatibility for all options
  const optionCompatibility = useMemo(() => {
    const compatibility = new Map<string, OptionCompatibility>();

    for (const option of options) {
      compatibility.set(option.id, checkOptionCompatibility(option, selectedOptionIds, options));
    }

    return compatibility;
  }, [options, selectedOptionIds]);

  // Track which options are in packages
  const optionsInPackages = useMemo(() => {
    const inPackages = new Set<string>();

    for (const option of options) {
      if (isOptionInPackage(option.id, selectedPackageIds, packageOptions)) {
        inPackages.add(option.id);
      }
    }

    return inPackages;
  }, [options, selectedPackageIds, packageOptions]);

  // Toggle category expansion
  const toggleCategory = useCallback((category: OptionCategory) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  }, []);

  // Handle option selection
  const handleOptionToggle = useCallback(
    (optionId: string) => {
      if (disabled) return;

      const option = options.find((opt) => opt.id === optionId);
      if (!option) return;

      // Don't allow toggling options that are in packages
      if (optionsInPackages.has(optionId)) return;

      // Check compatibility before allowing selection
      const compatibility = optionCompatibility.get(optionId);
      if (!compatibility?.isCompatible && !selectedOptionIds.includes(optionId)) {
        return;
      }

      onOptionToggle(optionId);
    },
    [disabled, options, optionsInPackages, optionCompatibility, selectedOptionIds, onOptionToggle],
  );

  // Expand all categories on mount
  useEffect(() => {
    setExpandedCategories(new Set(CATEGORY_ORDER));
  }, []);

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-gray-900">Select Features</h2>
        <p className="text-gray-600">
          Choose additional features to customize your vehicle. Options included in packages are
          marked with a package indicator.
        </p>
      </div>

      <div className="space-y-4">
        {CATEGORY_ORDER.map((category) => {
          const categoryOptions = categorizedOptions[category];
          if (!categoryOptions || categoryOptions.length === 0) return null;

          const isExpanded = expandedCategories.has(category);
          const categoryName =
            OPTION_CATEGORY_NAMES[category as keyof typeof OPTION_CATEGORY_NAMES];
          const categoryIcon = CATEGORY_ICONS[category];

          return (
            <div key={category} className="border border-gray-200 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => toggleCategory(category)}
                className="w-full px-6 py-4 bg-gray-50 hover:bg-gray-100 transition-colors flex items-center justify-between"
                aria-expanded={isExpanded}
                aria-controls={`category-${category}`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl" aria-hidden="true">
                    {categoryIcon}
                  </span>
                  <span className="text-lg font-semibold text-gray-900">{categoryName}</span>
                  <span className="text-sm text-gray-500">({categoryOptions.length})</span>
                </div>
                <svg
                  className={`w-5 h-5 text-gray-500 transition-transform ${
                    isExpanded ? 'rotate-180' : ''
                  }`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>

              {isExpanded && (
                <div id={`category-${category}`} className="p-6 space-y-4">
                  {categoryOptions.map((option) => {
                    const isSelected = selectedOptionIds.includes(option.id);
                    const inPackage = optionsInPackages.has(option.id);
                    const compatibility = optionCompatibility.get(option.id);
                    const isDisabled =
                      disabled || inPackage || (!isSelected && !compatibility?.isCompatible);

                    return (
                      <div
                        key={option.id}
                        className={`border rounded-lg p-4 transition-all ${
                          isSelected
                            ? 'border-blue-500 bg-blue-50'
                            : isDisabled
                              ? 'border-gray-200 bg-gray-50 opacity-60'
                              : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <label
                          className={`flex items-start gap-4 ${
                            isDisabled ? 'cursor-not-allowed' : 'cursor-pointer'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleOptionToggle(option.id)}
                            disabled={isDisabled}
                            className="mt-1 h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                            aria-describedby={`option-${option.id}-description`}
                          />

                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-semibold text-gray-900">{option.name}</span>
                              {inPackage && (
                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                  Included in Package
                                </span>
                              )}
                              {option.isRequired && (
                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                  Required
                                </span>
                              )}
                            </div>

                            <p
                              id={`option-${option.id}-description`}
                              className="text-sm text-gray-600 mb-2"
                            >
                              {option.description}
                            </p>

                            {!compatibility?.isCompatible && compatibility?.reason && (
                              <div className="flex items-start gap-2 mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded">
                                <svg
                                  className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0"
                                  fill="currentColor"
                                  viewBox="0 0 20 20"
                                  aria-hidden="true"
                                >
                                  <path
                                    fillRule="evenodd"
                                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                                    clipRule="evenodd"
                                  />
                                </svg>
                                <span className="text-xs text-yellow-800">
                                  {compatibility.reason}
                                </span>
                              </div>
                            )}

                            <div className="flex items-center justify-between mt-2">
                              <span className="text-lg font-bold text-gray-900">
                                {option.price > 0 ? formatPrice(option.price) : 'Included'}
                              </span>
                            </div>
                          </div>
                        </label>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {options.length === 0 && (
        <div className="text-center py-12">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No features available</h3>
          <p className="mt-1 text-sm text-gray-500">
            There are no additional features available for this vehicle configuration.
          </p>
        </div>
      )}
    </div>
  );
}