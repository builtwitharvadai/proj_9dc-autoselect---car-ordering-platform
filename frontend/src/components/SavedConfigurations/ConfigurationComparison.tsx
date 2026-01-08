/**
 * Configuration Comparison Component
 * 
 * Provides side-by-side comparison of up to 3 saved vehicle configurations.
 * Features responsive design with mobile-friendly stacked view and difference highlighting.
 * 
 * @module components/SavedConfigurations/ConfigurationComparison
 */

import { useState, useMemo, useCallback, useEffect } from 'react';
import {
  ConfigurationComparisonItem,
  ConfigurationComparisonResult,
  PriceDifference,
  FeatureDifference,
  PackageDifference,
  ComparisonHighlight,
  ComparisonHighlightType,
  COMPARISON_CONSTRAINTS,
  formatConfigurationPrice,
  formatPriceDifference,
  formatPriceDifferencePercentage,
  canCompareConfigurations,
} from '../../types/savedConfiguration';

/**
 * Props for ConfigurationComparison component
 */
export interface ConfigurationComparisonProps {
  /** Configurations to compare */
  readonly configurations: readonly ConfigurationComparisonItem[];
  /** Callback when configuration is removed from comparison */
  readonly onRemoveConfiguration?: (configurationId: string) => void;
  /** Callback when configuration is saved from comparison */
  readonly onSaveConfiguration?: (configurationId: string) => void;
  /** Whether to highlight differences */
  readonly highlightDifferences?: boolean;
  /** Whether to show mobile stacked view */
  readonly enableMobileView?: boolean;
  /** Additional CSS classes */
  readonly className?: string;
  /** Whether comparison is loading */
  readonly isLoading?: boolean;
  /** Error message if comparison failed */
  readonly error?: string | null;
}

/**
 * Comparison table row type
 */
type ComparisonRowType = 'header' | 'price' | 'feature' | 'package' | 'specification';

/**
 * Comparison table row
 */
interface ComparisonRow {
  readonly type: ComparisonRowType;
  readonly label: string;
  readonly values: readonly (string | number | boolean | null)[];
  readonly isDifferent: boolean;
  readonly highlightType?: ComparisonHighlightType;
}

/**
 * Mobile view mode
 */
type MobileViewMode = 'stacked' | 'swipe';

/**
 * ConfigurationComparison Component
 * 
 * Displays side-by-side comparison of vehicle configurations with:
 * - Responsive table layout
 * - Mobile-friendly stacked view
 * - Difference highlighting
 * - Price comparison
 * - Feature and package comparison
 * 
 * @example
 * ```tsx
 * <ConfigurationComparison
 *   configurations={savedConfigurations}
 *   onRemoveConfiguration={handleRemove}
 *   highlightDifferences={true}
 * />
 * ```
 */
export default function ConfigurationComparison({
  configurations,
  onRemoveConfiguration,
  onSaveConfiguration,
  highlightDifferences = true,
  enableMobileView = true,
  className = '',
  isLoading = false,
  error = null,
}: ConfigurationComparisonProps): JSX.Element {
  // State
  const [mobileViewMode, setMobileViewMode] = useState<MobileViewMode>('stacked');
  const [selectedMobileIndex, setSelectedMobileIndex] = useState(0);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['pricing', 'packages', 'features'])
  );

  // Validate configuration count
  const isValidComparison = canCompareConfigurations(configurations.length);

  // Calculate comparison result
  const comparisonResult = useMemo<ConfigurationComparisonResult | null>(() => {
    if (!isValidComparison || configurations.length === 0) {
      return null;
    }

    // Calculate price differences
    const prices = configurations.map(c => c.pricing.total);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const avgPrice = prices.reduce((sum, p) => sum + p, 0) / prices.length;

    const priceDifferences: PriceDifference[] = configurations.map(config => ({
      configurationId: config.configurationId,
      basePrice: config.pricing.basePrice,
      optionsPrice: config.pricing.optionsPrice,
      packagesPrice: config.pricing.packagesPrice,
      total: config.pricing.total,
      differenceFromLowest: config.pricing.total - minPrice,
      differencePercentage: minPrice > 0 ? ((config.pricing.total - minPrice) / minPrice) * 100 : 0,
    }));

    // Find lowest and highest price configurations
    const lowestPriceConfig = configurations.find(c => c.pricing.total === minPrice);
    const highestPriceConfig = configurations.find(c => c.pricing.total === maxPrice);

    // Calculate feature differences
    const allOptions = new Map<string, Map<string, boolean | string | number>>();
    configurations.forEach(config => {
      config.options.forEach(option => {
        if (!allOptions.has(option.id)) {
          allOptions.set(option.id, new Map());
        }
        allOptions.get(option.id)?.set(config.configurationId, true);
      });
    });

    const featureDifferences: FeatureDifference[] = Array.from(allOptions.entries()).map(
      ([optionId, configMap]) => {
        const option = configurations
          .flatMap(c => c.options)
          .find(o => o.id === optionId);
        
        const values: Record<string, boolean | string | number> = {};
        configurations.forEach(config => {
          values[config.configurationId] = configMap.get(config.configurationId) ?? false;
        });

        const uniqueValues = new Set(Object.values(values));
        
        return {
          category: option?.category ?? 'other',
          featureName: option?.name ?? 'Unknown',
          configurations: values,
          isDifferent: uniqueValues.size > 1,
        };
      }
    );

    // Calculate package differences
    const allPackages = new Map<string, Map<string, boolean>>();
    configurations.forEach(config => {
      config.packages.forEach(pkg => {
        if (!allPackages.has(pkg.id)) {
          allPackages.set(pkg.id, new Map());
        }
        allPackages.get(pkg.id)?.set(config.configurationId, true);
      });
    });

    const packageDifferences: PackageDifference[] = Array.from(allPackages.entries()).map(
      ([packageId, configMap]) => {
        const pkg = configurations
          .flatMap(c => c.packages)
          .find(p => p.id === packageId);
        
        const values: Record<string, boolean> = {};
        configurations.forEach(config => {
          values[config.configurationId] = configMap.get(config.configurationId) ?? false;
        });

        return {
          packageId,
          packageName: pkg?.name ?? 'Unknown',
          configurations: values,
          price: pkg?.price ?? 0,
        };
      }
    );

    return {
      configurations,
      priceDifferences,
      featureDifferences,
      packageDifferences,
      lowestPriceConfigurationId: lowestPriceConfig?.configurationId ?? '',
      highestPriceConfigurationId: highestPriceConfig?.configurationId ?? '',
      averagePrice: avgPrice,
      priceRange: {
        min: minPrice,
        max: maxPrice,
      },
      comparedAt: new Date().toISOString(),
    };
  }, [configurations, isValidComparison]);

  // Build comparison rows
  const comparisonRows = useMemo<readonly ComparisonRow[]>(() => {
    if (!comparisonResult) {
      return [];
    }

    const rows: ComparisonRow[] = [];

    // Vehicle information header
    rows.push({
      type: 'header',
      label: 'Vehicle',
      values: configurations.map(c => `${c.vehicle.year} ${c.vehicle.make} ${c.vehicle.model}`),
      isDifferent: false,
    });

    // Pricing section
    if (expandedSections.has('pricing')) {
      rows.push({
        type: 'price',
        label: 'Base Price',
        values: configurations.map(c => c.pricing.basePrice),
        isDifferent: new Set(configurations.map(c => c.pricing.basePrice)).size > 1,
        highlightType: 'price',
      });

      rows.push({
        type: 'price',
        label: 'Options Price',
        values: configurations.map(c => c.pricing.optionsPrice),
        isDifferent: new Set(configurations.map(c => c.pricing.optionsPrice)).size > 1,
        highlightType: 'price',
      });

      rows.push({
        type: 'price',
        label: 'Packages Price',
        values: configurations.map(c => c.pricing.packagesPrice),
        isDifferent: new Set(configurations.map(c => c.pricing.packagesPrice)).size > 1,
        highlightType: 'price',
      });

      rows.push({
        type: 'price',
        label: 'Total Price',
        values: configurations.map(c => c.pricing.total),
        isDifferent: new Set(configurations.map(c => c.pricing.total)).size > 1,
        highlightType: 'price',
      });
    }

    // Packages section
    if (expandedSections.has('packages')) {
      comparisonResult.packageDifferences.forEach(pkg => {
        rows.push({
          type: 'package',
          label: pkg.packageName,
          values: configurations.map(c => pkg.configurations[c.configurationId] ?? false),
          isDifferent: pkg.configurations && Object.values(pkg.configurations).some((v, i, arr) => v !== arr[0]),
          highlightType: 'package',
        });
      });
    }

    // Features section
    if (expandedSections.has('features')) {
      const featuresByCategory = new Map<string, FeatureDifference[]>();
      comparisonResult.featureDifferences.forEach(feature => {
        const category = feature.category;
        if (!featuresByCategory.has(category)) {
          featuresByCategory.set(category, []);
        }
        featuresByCategory.get(category)?.push(feature);
      });

      featuresByCategory.forEach((features, category) => {
        features.forEach(feature => {
          rows.push({
            type: 'feature',
            label: feature.featureName,
            values: configurations.map(c => feature.configurations[c.configurationId] ?? false),
            isDifferent: feature.isDifferent,
            highlightType: 'feature',
          });
        });
      });
    }

    return rows;
  }, [comparisonResult, configurations, expandedSections]);

  // Toggle section expansion
  const toggleSection = useCallback((section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  }, []);

  // Handle mobile swipe
  const handleMobileSwipe = useCallback((direction: 'left' | 'right') => {
    if (mobileViewMode !== 'swipe') return;

    setSelectedMobileIndex(prev => {
      if (direction === 'left') {
        return Math.min(prev + 1, configurations.length - 1);
      }
      return Math.max(prev - 1, 0);
    });
  }, [mobileViewMode, configurations.length]);

  // Reset mobile index when configurations change
  useEffect(() => {
    if (selectedMobileIndex >= configurations.length) {
      setSelectedMobileIndex(Math.max(0, configurations.length - 1));
    }
  }, [configurations.length, selectedMobileIndex]);

  // Render loading state
  if (isLoading) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-4 text-gray-600">Loading comparison...</p>
        </div>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className={`rounded-lg border border-red-200 bg-red-50 p-6 ${className}`}>
        <div className="flex items-start">
          <svg
            className="h-6 w-6 text-red-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Comparison Error</h3>
            <p className="mt-1 text-sm text-red-700">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  // Render invalid comparison state
  if (!isValidComparison) {
    return (
      <div className={`rounded-lg border border-yellow-200 bg-yellow-50 p-6 ${className}`}>
        <div className="flex items-start">
          <svg
            className="h-6 w-6 text-yellow-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800">Invalid Comparison</h3>
            <p className="mt-1 text-sm text-yellow-700">
              Please select between {COMPARISON_CONSTRAINTS.MIN_CONFIGURATIONS} and{' '}
              {COMPARISON_CONSTRAINTS.MAX_CONFIGURATIONS} configurations to compare.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Render empty state
  if (configurations.length === 0) {
    return (
      <div className={`rounded-lg border border-gray-200 bg-gray-50 p-8 text-center ${className}`}>
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
          />
        </svg>
        <h3 className="mt-4 text-lg font-medium text-gray-900">No Configurations Selected</h3>
        <p className="mt-2 text-sm text-gray-600">
          Select configurations from your saved list to compare them side-by-side.
        </p>
      </div>
    );
  }

  // Desktop view
  const desktopView = (
    <div className="hidden overflow-x-auto md:block">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th
              scope="col"
              className="sticky left-0 z-10 bg-gray-50 px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
            >
              Feature
            </th>
            {configurations.map((config, index) => (
              <th
                key={config.configurationId}
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                <div className="flex items-center justify-between">
                  <span>Configuration {index + 1}</span>
                  {onRemoveConfiguration && (
                    <button
                      onClick={() => onRemoveConfiguration(config.configurationId)}
                      className="ml-2 text-red-600 hover:text-red-800"
                      aria-label={`Remove ${config.name}`}
                    >
                      <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </button>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {comparisonRows.map((row, rowIndex) => (
            <tr
              key={`${row.type}-${row.label}-${rowIndex}`}
              className={row.type === 'header' ? 'bg-gray-50 font-medium' : ''}
            >
              <td className="sticky left-0 z-10 bg-white px-6 py-4 text-sm font-medium text-gray-900">
                {row.label}
              </td>
              {row.values.map((value, colIndex) => {
                const config = configurations[colIndex];
                const isDifferent = highlightDifferences && row.isDifferent;
                const isLowestPrice =
                  row.type === 'price' &&
                  row.label === 'Total Price' &&
                  comparisonResult?.lowestPriceConfigurationId === config?.configurationId;

                return (
                  <td
                    key={`${config?.configurationId ?? colIndex}-${rowIndex}`}
                    className={`px-6 py-4 text-sm ${
                      isDifferent ? 'bg-yellow-50' : ''
                    } ${isLowestPrice ? 'font-bold text-green-600' : 'text-gray-900'}`}
                  >
                    {typeof value === 'number'
                      ? formatConfigurationPrice(value)
                      : typeof value === 'boolean'
                        ? value
                          ? '✓'
                          : '—'
                        : value ?? '—'}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  // Mobile stacked view
  const mobileStackedView = (
    <div className="space-y-6 md:hidden">
      {configurations.map((config, index) => (
        <div key={config.configurationId} className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="mb-4 flex items-start justify-between">
            <div>
              <h3 className="text-lg font-medium text-gray-900">{config.name}</h3>
              <p className="text-sm text-gray-600">
                {config.vehicle.year} {config.vehicle.make} {config.vehicle.model}
              </p>
            </div>
            {onRemoveConfiguration && (
              <button
                onClick={() => onRemoveConfiguration(config.configurationId)}
                className="text-red-600 hover:text-red-800"
                aria-label={`Remove ${config.name}`}
              >
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            )}
          </div>

          <div className="space-y-3">
            <div className="flex justify-between border-b border-gray-200 pb-2">
              <span className="text-sm font-medium text-gray-700">Total Price</span>
              <span
                className={`text-sm font-bold ${
                  comparisonResult?.lowestPriceConfigurationId === config.configurationId
                    ? 'text-green-600'
                    : 'text-gray-900'
                }`}
              >
                {formatConfigurationPrice(config.pricing.total)}
              </span>
            </div>

            {comparisonResult && (
              <div className="text-sm text-gray-600">
                <div className="flex justify-between">
                  <span>Difference from lowest:</span>
                  <span>
                    {formatPriceDifference(
                      comparisonResult.priceDifferences[index]?.differenceFromLowest ?? 0
                    )}
                  </span>
                </div>
              </div>
            )}

            <div className="pt-2">
              <button
                onClick={() => toggleSection('pricing')}
                className="flex w-full items-center justify-between text-sm font-medium text-gray-700"
              >
                <span>Pricing Details</span>
                <svg
                  className={`h-5 w-5 transform transition-transform ${
                    expandedSections.has('pricing') ? 'rotate-180' : ''
                  }`}
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
              {expandedSections.has('pricing') && (
                <div className="mt-2 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Base Price:</span>
                    <span className="text-gray-900">
                      {formatConfigurationPrice(config.pricing.basePrice)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Options:</span>
                    <span className="text-gray-900">
                      {formatConfigurationPrice(config.pricing.optionsPrice)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Packages:</span>
                    <span className="text-gray-900">
                      {formatConfigurationPrice(config.pricing.packagesPrice)}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {config.packages.length > 0 && (
              <div className="pt-2">
                <button
                  onClick={() => toggleSection('packages')}
                  className="flex w-full items-center justify-between text-sm font-medium text-gray-700"
                >
                  <span>Packages ({config.packages.length})</span>
                  <svg
                    className={`h-5 w-5 transform transition-transform ${
                      expandedSections.has('packages') ? 'rotate-180' : ''
                    }`}
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
                {expandedSections.has('packages') && (
                  <ul className="mt-2 space-y-1 text-sm text-gray-600">
                    {config.packages.map(pkg => (
                      <li key={pkg.id} className="flex items-center">
                        <svg className="mr-2 h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                          <path
                            fillRule="evenodd"
                            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                        {pkg.name}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {config.options.length > 0 && (
              <div className="pt-2">
                <button
                  onClick={() => toggleSection('features')}
                  className="flex w-full items-center justify-between text-sm font-medium text-gray-700"
                >
                  <span>Features ({config.options.length})</span>
                  <svg
                    className={`h-5 w-5 transform transition-transform ${
                      expandedSections.has('features') ? 'rotate-180' : ''
                    }`}
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
                {expandedSections.has('features') && (
                  <ul className="mt-2 space-y-1 text-sm text-gray-600">
                    {config.options.map(option => (
                      <li key={option.id} className="flex items-center">
                        <svg className="mr-2 h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                          <path
                            fillRule="evenodd"
                            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                        {option.name}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          {onSaveConfiguration && (
            <button
              onClick={() => onSaveConfiguration(config.configurationId)}
              className="mt-4 w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Save Configuration
            </button>
          )}
        </div>
      ))}
    </div>
  );

  return (
    <div className={`rounded-lg bg-white shadow ${className}`}>
      {/* Comparison summary */}
      {comparisonResult && (
        <div className="border-b border-gray-200 bg-gray-50 px-6 py-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-medium text-gray-900">Configuration Comparison</h2>
              <p className="mt-1 text-sm text-gray-600">
                Comparing {configurations.length} configuration{configurations.length !== 1 ? 's' : ''}
              </p>
            </div>
            <div className="flex flex-wrap gap-4 text-sm">
              <div>
                <span className="text-gray-600">Price Range:</span>
                <span className="ml-2 font-medium text-gray-900">
                  {formatConfigurationPrice(comparisonResult.priceRange.min)} -{' '}
                  {formatConfigurationPrice(comparisonResult.priceRange.max)}
                </span>
              </div>
              <div>
                <span className="text-gray-600">Average:</span>
                <span className="ml-2 font-medium text-gray-900">
                  {formatConfigurationPrice(comparisonResult.averagePrice)}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Comparison content */}
      <div className="p-6">
        {enableMobileView ? (
          <>
            {desktopView}
            {mobileStackedView}
          </>
        ) : (
          desktopView
        )}
      </div>
    </div>
  );
}