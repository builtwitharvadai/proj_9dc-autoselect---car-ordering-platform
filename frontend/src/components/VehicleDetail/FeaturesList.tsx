import React from 'react';
import type { VehicleFeatures } from '../../types/vehicle';

/**
 * Props for the FeaturesList component
 */
interface FeaturesListProps {
  /**
   * Vehicle features organized by category
   */
  readonly features: VehicleFeatures;
  
  /**
   * Optional CSS class name for styling
   */
  readonly className?: string;
  
  /**
   * Whether to show standard/optional indicators
   * @default true
   */
  readonly showIndicators?: boolean;
  
  /**
   * Optional features that are not standard
   * Used to determine which features should be marked as optional
   */
  readonly optionalFeatures?: readonly string[];
  
  /**
   * Callback when a feature is clicked (for additional details)
   */
  readonly onFeatureClick?: (feature: string, category: string) => void;
  
  /**
   * Whether to show empty categories
   * @default false
   */
  readonly showEmptyCategories?: boolean;
  
  /**
   * Maximum number of features to show per category before collapsing
   * @default undefined (show all)
   */
  readonly maxFeaturesPerCategory?: number;
}

/**
 * Feature category configuration
 */
interface FeatureCategoryConfig {
  readonly key: keyof VehicleFeatures;
  readonly label: string;
  readonly icon: string;
  readonly description: string;
}

/**
 * Feature categories with their display configuration
 */
const FEATURE_CATEGORIES: readonly FeatureCategoryConfig[] = [
  {
    key: 'safety',
    label: 'Safety Features',
    icon: '🛡️',
    description: 'Advanced safety systems and driver assistance',
  },
  {
    key: 'technology',
    label: 'Technology',
    icon: '💻',
    description: 'Infotainment and connectivity features',
  },
  {
    key: 'comfort',
    label: 'Comfort & Convenience',
    icon: '🪑',
    description: 'Interior comfort and convenience features',
  },
  {
    key: 'entertainment',
    label: 'Entertainment',
    icon: '🎵',
    description: 'Audio and entertainment systems',
  },
  {
    key: 'exterior',
    label: 'Exterior Features',
    icon: '🚗',
    description: 'Exterior styling and functional features',
  },
  {
    key: 'interior',
    label: 'Interior Features',
    icon: '🎨',
    description: 'Interior design and materials',
  },
] as const;

/**
 * FeaturesList Component
 * 
 * Displays vehicle features organized by category with visual indicators
 * for standard vs optional features. Supports collapsible categories and
 * interactive feature selection.
 * 
 * @example
 * ```tsx
 * <FeaturesList
 *   features={vehicle.features}
 *   optionalFeatures={['Premium Audio', 'Sunroof']}
 *   showIndicators={true}
 *   onFeatureClick={(feature, category) => console.log(feature, category)}
 * />
 * ```
 */
export default function FeaturesList({
  features,
  className = '',
  showIndicators = true,
  optionalFeatures = [],
  onFeatureClick,
  showEmptyCategories = false,
  maxFeaturesPerCategory,
}: FeaturesListProps): JSX.Element {
  const [expandedCategories, setExpandedCategories] = React.useState<Set<string>>(
    new Set(FEATURE_CATEGORIES.map((cat) => cat.key))
  );

  /**
   * Check if a feature is optional
   */
  const isOptionalFeature = React.useCallback(
    (feature: string): boolean => {
      return optionalFeatures.includes(feature);
    },
    [optionalFeatures]
  );

  /**
   * Toggle category expansion
   */
  const toggleCategory = React.useCallback((categoryKey: string): void => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryKey)) {
        next.delete(categoryKey);
      } else {
        next.add(categoryKey);
      }
      return next;
    });
  }, []);

  /**
   * Handle feature click
   */
  const handleFeatureClick = React.useCallback(
    (feature: string, category: string): void => {
      if (onFeatureClick) {
        onFeatureClick(feature, category);
      }
    },
    [onFeatureClick]
  );

  /**
   * Get features for a category with optional truncation
   */
  const getCategoryFeatures = React.useCallback(
    (categoryKey: keyof VehicleFeatures): readonly string[] => {
      const categoryFeatures = features[categoryKey];
      
      if (!maxFeaturesPerCategory || expandedCategories.has(categoryKey)) {
        return categoryFeatures;
      }
      
      return categoryFeatures.slice(0, maxFeaturesPerCategory);
    },
    [features, maxFeaturesPerCategory, expandedCategories]
  );

  /**
   * Check if category should show "Show more" button
   */
  const shouldShowMoreButton = React.useCallback(
    (categoryKey: keyof VehicleFeatures): boolean => {
      if (!maxFeaturesPerCategory) {
        return false;
      }
      
      const categoryFeatures = features[categoryKey];
      return categoryFeatures.length > maxFeaturesPerCategory && !expandedCategories.has(categoryKey);
    },
    [features, maxFeaturesPerCategory, expandedCategories]
  );

  /**
   * Render feature item with indicator
   */
  const renderFeatureItem = React.useCallback(
    (feature: string, category: string): JSX.Element => {
      const isOptional = isOptionalFeature(feature);
      const isClickable = Boolean(onFeatureClick);

      return (
        <li
          key={feature}
          className={`flex items-start gap-3 py-2 ${isClickable ? 'cursor-pointer hover:bg-gray-50 rounded-md px-2 -mx-2 transition-colors' : ''}`}
          onClick={() => isClickable && handleFeatureClick(feature, category)}
          role={isClickable ? 'button' : undefined}
          tabIndex={isClickable ? 0 : undefined}
          onKeyDown={(e) => {
            if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
              e.preventDefault();
              handleFeatureClick(feature, category);
            }
          }}
          aria-label={`${feature}${showIndicators ? ` - ${isOptional ? 'Optional' : 'Standard'}` : ''}`}
        >
          {showIndicators && (
            <span
              className={`flex-shrink-0 mt-1 w-2 h-2 rounded-full ${
                isOptional ? 'bg-blue-500' : 'bg-green-500'
              }`}
              aria-hidden="true"
              title={isOptional ? 'Optional' : 'Standard'}
            />
          )}
          <span className="flex-1 text-gray-700 text-sm leading-relaxed">
            {feature}
          </span>
          {showIndicators && (
            <span
              className={`flex-shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${
                isOptional
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-green-100 text-green-700'
              }`}
            >
              {isOptional ? 'Optional' : 'Standard'}
            </span>
          )}
        </li>
      );
    },
    [isOptionalFeature, showIndicators, onFeatureClick, handleFeatureClick]
  );

  /**
   * Render category section
   */
  const renderCategory = React.useCallback(
    (config: FeatureCategoryConfig): JSX.Element | null => {
      const categoryFeatures = features[config.key];
      const isExpanded = expandedCategories.has(config.key);
      const displayFeatures = getCategoryFeatures(config.key);
      const showMore = shouldShowMoreButton(config.key);

      // Skip empty categories if configured
      if (!showEmptyCategories && categoryFeatures.length === 0) {
        return null;
      }

      return (
        <div
          key={config.key}
          className="border border-gray-200 rounded-lg overflow-hidden bg-white"
        >
          {/* Category Header */}
          <button
            type="button"
            onClick={() => toggleCategory(config.key)}
            className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset"
            aria-expanded={isExpanded}
            aria-controls={`category-${config.key}`}
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl" aria-hidden="true">
                {config.icon}
              </span>
              <div className="text-left">
                <h3 className="text-lg font-semibold text-gray-900">
                  {config.label}
                </h3>
                <p className="text-sm text-gray-600 mt-0.5">
                  {config.description}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-500">
                {categoryFeatures.length} {categoryFeatures.length === 1 ? 'feature' : 'features'}
              </span>
              <svg
                className={`w-5 h-5 text-gray-400 transition-transform ${
                  isExpanded ? 'transform rotate-180' : ''
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
            </div>
          </button>

          {/* Category Content */}
          {isExpanded && (
            <div
              id={`category-${config.key}`}
              className="px-4 pb-4"
              role="region"
              aria-label={`${config.label} features`}
            >
              {categoryFeatures.length === 0 ? (
                <p className="text-sm text-gray-500 italic py-2">
                  No features in this category
                </p>
              ) : (
                <>
                  <ul className="space-y-1" role="list">
                    {displayFeatures.map((feature) =>
                      renderFeatureItem(feature, config.key)
                    )}
                  </ul>
                  
                  {showMore && (
                    <button
                      type="button"
                      onClick={() => toggleCategory(config.key)}
                      className="mt-3 text-sm font-medium text-blue-600 hover:text-blue-700 focus:outline-none focus:underline"
                    >
                      Show {categoryFeatures.length - maxFeaturesPerCategory!} more features
                    </button>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      );
    },
    [
      features,
      expandedCategories,
      showEmptyCategories,
      getCategoryFeatures,
      shouldShowMoreButton,
      toggleCategory,
      renderFeatureItem,
      maxFeaturesPerCategory,
    ]
  );

  /**
   * Calculate total feature count
   */
  const totalFeatures = React.useMemo(() => {
    return FEATURE_CATEGORIES.reduce(
      (sum, config) => sum + features[config.key].length,
      0
    );
  }, [features]);

  /**
   * Calculate optional feature count
   */
  const optionalCount = React.useMemo(() => {
    return FEATURE_CATEGORIES.reduce((sum, config) => {
      return (
        sum +
        features[config.key].filter((feature) => isOptionalFeature(feature)).length
      );
    }, 0);
  }, [features, isOptionalFeature]);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Summary Header */}
      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              Vehicle Features
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              {totalFeatures} total features across {FEATURE_CATEGORIES.length} categories
            </p>
          </div>
          {showIndicators && optionalFeatures.length > 0 && (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-green-500" aria-hidden="true" />
                <span className="text-sm text-gray-700">
                  {totalFeatures - optionalCount} Standard
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-blue-500" aria-hidden="true" />
                <span className="text-sm text-gray-700">
                  {optionalCount} Optional
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Feature Categories */}
      <div className="space-y-3">
        {FEATURE_CATEGORIES.map((config) => renderCategory(config))}
      </div>

      {/* Empty State */}
      {totalFeatures === 0 && (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
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
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">
            No features available
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            Feature information is not available for this vehicle.
          </p>
        </div>
      )}
    </div>
  );
}