/**
 * Package Recommendations Component
 * Displays intelligent package recommendations with savings calculations,
 * value propositions, and analytics tracking for recommendation interactions
 */

import { memo, useCallback, useMemo, useState } from 'react';
import {
  usePackageRecommendations,
  useTrackRecommendation,
  useAcceptRecommendation,
} from '../../hooks/useRecommendations';
import type {
  PackageRecommendation,
  RecommendationConfidence,
  RecommendationEventType,
} from '../../types/recommendations';
import {
  formatSavings,
  formatSavingsPercentage,
  RECOMMENDATION_REASON_NAMES,
  hasHighConfidence,
  hasSignificantSavings,
} from '../../types/recommendations';

/**
 * Component props interface
 */
export interface PackageRecommendationsProps {
  readonly vehicleId: string;
  readonly trimId?: string;
  readonly selectedPackageIds?: readonly string[];
  readonly selectedOptionIds?: readonly string[];
  readonly budget?: number;
  readonly maxRecommendations?: number;
  readonly onPackageSelect?: (packageId: string) => void;
  readonly onPackageDeselect?: (packageId: string) => void;
  readonly className?: string;
  readonly showPopularConfigurations?: boolean;
  readonly region?: string;
  readonly userId?: string;
  readonly sessionId?: string;
}

/**
 * Confidence badge color mapping
 */
const CONFIDENCE_COLORS: Record<RecommendationConfidence, string> = {
  high: 'bg-green-100 text-green-800 border-green-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-gray-100 text-gray-800 border-gray-200',
} as const;

/**
 * Confidence badge labels
 */
const CONFIDENCE_LABELS: Record<RecommendationConfidence, string> = {
  high: 'Highly Recommended',
  medium: 'Recommended',
  low: 'Consider',
} as const;

/**
 * Package Recommendations Component
 * Displays intelligent package suggestions with savings and value propositions
 */
export default memo(function PackageRecommendations({
  vehicleId,
  trimId,
  selectedPackageIds = [],
  selectedOptionIds = [],
  budget,
  maxRecommendations = 5,
  onPackageSelect,
  onPackageDeselect,
  className = '',
  showPopularConfigurations = true,
  region,
  userId,
  sessionId,
}: PackageRecommendationsProps): JSX.Element {
  // State for tracking selected recommendations
  const [selectedRecommendations, setSelectedRecommendations] = useState<Set<string>>(
    new Set(selectedPackageIds),
  );

  // Fetch recommendations
  const {
    data: recommendationsData,
    isLoading,
    error,
    refetch,
  } = usePackageRecommendations(
    {
      vehicleId,
      trimId,
      selectedPackageIds,
      selectedOptionIds,
      budget,
      maxRecommendations,
      includePopularConfigurations: showPopularConfigurations,
      region,
    },
    {
      enabled: Boolean(vehicleId),
      staleTime: 5 * 60 * 1000,
      retry: 2,
    },
  );

  // Analytics tracking mutations
  const trackRecommendation = useTrackRecommendation({
    onError: (error) => {
      console.error('Failed to track recommendation event:', error);
    },
  });

  const acceptRecommendation = useAcceptRecommendation({
    onSuccess: () => {
      void refetch();
    },
    onError: (error) => {
      console.error('Failed to accept recommendation:', error);
    },
  });

  /**
   * Track recommendation event
   */
  const trackEvent = useCallback(
    (
      eventType: RecommendationEventType,
      recommendation: PackageRecommendation,
      position: number,
    ) => {
      trackRecommendation.mutate({
        recommendationId: recommendation.id,
        eventType,
        timestamp: new Date().toISOString(),
        userId,
        sessionId,
        vehicleId,
        packageId: recommendation.packageId,
        position,
        confidence: recommendation.confidence,
        metadata: {
          savingsAmount: recommendation.savingsAmount,
          savingsPercentage: recommendation.savingsPercentage,
          popularityScore: recommendation.popularityScore,
        },
      });
    },
    [trackRecommendation, userId, sessionId, vehicleId],
  );

  /**
   * Handle recommendation card click
   */
  const handleRecommendationClick = useCallback(
    (recommendation: PackageRecommendation, position: number) => {
      trackEvent('recommendation_clicked', recommendation, position);
    },
    [trackEvent],
  );

  /**
   * Handle package selection
   */
  const handlePackageSelect = useCallback(
    (recommendation: PackageRecommendation, position: number) => {
      const isSelected = selectedRecommendations.has(recommendation.packageId);

      if (isSelected) {
        setSelectedRecommendations((prev) => {
          const next = new Set(prev);
          next.delete(recommendation.packageId);
          return next;
        });
        onPackageDeselect?.(recommendation.packageId);
        trackEvent('recommendation_dismissed', recommendation, position);
      } else {
        setSelectedRecommendations((prev) => new Set(prev).add(recommendation.packageId));
        onPackageSelect?.(recommendation.packageId);
        trackEvent('recommendation_accepted', recommendation, position);

        // Track acceptance in backend
        acceptRecommendation.mutate({
          recommendationId: recommendation.id,
          packageId: recommendation.packageId,
          acceptedAt: new Date().toISOString(),
          userId,
          sessionId,
          vehicleId,
          finalPrice: recommendation.discountedPrice,
          savingsRealized: recommendation.savingsAmount,
        });
      }
    },
    [
      selectedRecommendations,
      onPackageSelect,
      onPackageDeselect,
      trackEvent,
      acceptRecommendation,
      userId,
      sessionId,
      vehicleId,
    ],
  );

  /**
   * Calculate total potential savings
   */
  const totalPotentialSavings = useMemo(() => {
    if (!recommendationsData?.recommendations) return 0;
    return recommendationsData.recommendations.reduce(
      (total, rec) => total + rec.savingsAmount,
      0,
    );
  }, [recommendationsData]);

  /**
   * Filter and sort recommendations
   */
  const displayRecommendations = useMemo(() => {
    if (!recommendationsData?.recommendations) return [];
    return recommendationsData.recommendations
      .filter((rec) => rec.compatibleWithSelection)
      .slice(0, maxRecommendations);
  }, [recommendationsData, maxRecommendations]);

  // Loading state
  if (isLoading) {
    return (
      <div className={`space-y-4 ${className}`}>
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-4" />
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`rounded-lg border border-red-200 bg-red-50 p-4 ${className}`}>
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg
              className="h-5 w-5 text-red-400"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">
              Failed to load recommendations
            </h3>
            <p className="mt-1 text-sm text-red-700">
              {error instanceof Error ? error.message : 'An unexpected error occurred'}
            </p>
            <button
              type="button"
              onClick={() => void refetch()}
              className="mt-2 text-sm font-medium text-red-800 hover:text-red-900 underline"
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (!displayRecommendations.length) {
    return (
      <div className={`rounded-lg border border-gray-200 bg-gray-50 p-8 text-center ${className}`}>
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No recommendations available</h3>
        <p className="mt-1 text-sm text-gray-500">
          We couldn't find any package recommendations for your current selection.
        </p>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Recommended Packages</h2>
          <p className="mt-1 text-sm text-gray-600">
            Save up to {formatSavings(totalPotentialSavings)} with these package deals
          </p>
        </div>
        {recommendationsData?.metadata && (
          <div className="text-xs text-gray-500">
            Generated in {recommendationsData.metadata.processingTimeMs}ms
          </div>
        )}
      </div>

      {/* Recommendations Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {displayRecommendations.map((recommendation, index) => {
          const isSelected = selectedRecommendations.has(recommendation.packageId);
          const isHighConfidence = hasHighConfidence(recommendation);
          const hasSignificantSaving = hasSignificantSavings(recommendation);

          return (
            <div
              key={recommendation.id}
              className={`relative rounded-lg border-2 transition-all duration-200 ${
                isSelected
                  ? 'border-blue-500 bg-blue-50 shadow-md'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
              }`}
              onClick={() => handleRecommendationClick(recommendation, index)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleRecommendationClick(recommendation, index);
                }
              }}
              role="button"
              tabIndex={0}
              aria-pressed={isSelected}
            >
              {/* Confidence Badge */}
              <div className="absolute -top-2 -right-2 z-10">
                <span
                  className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${CONFIDENCE_COLORS[recommendation.confidence]}`}
                >
                  {CONFIDENCE_LABELS[recommendation.confidence]}
                </span>
              </div>

              {/* Package Image */}
              {recommendation.imageUrl && (
                <div className="aspect-video w-full overflow-hidden rounded-t-lg">
                  <img
                    src={recommendation.imageUrl}
                    alt={recommendation.name}
                    className="h-full w-full object-cover"
                    loading="lazy"
                  />
                </div>
              )}

              {/* Package Content */}
              <div className="p-4">
                <h3 className="text-lg font-semibold text-gray-900">{recommendation.name}</h3>
                <p className="mt-1 text-sm text-gray-600 line-clamp-2">
                  {recommendation.description}
                </p>

                {/* Pricing */}
                <div className="mt-4 space-y-2">
                  <div className="flex items-baseline justify-between">
                    <div>
                      <span className="text-2xl font-bold text-gray-900">
                        {formatSavings(recommendation.discountedPrice)}
                      </span>
                      {recommendation.savingsAmount > 0 && (
                        <span className="ml-2 text-sm text-gray-500 line-through">
                          {formatSavings(recommendation.basePrice)}
                        </span>
                      )}
                    </div>
                    {hasSignificantSaving && (
                      <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                        Save {formatSavingsPercentage(recommendation.savingsPercentage)}
                      </span>
                    )}
                  </div>

                  {recommendation.savingsAmount > 0 && (
                    <p className="text-sm font-medium text-green-600">
                      You save {formatSavings(recommendation.savingsAmount)}
                    </p>
                  )}
                </div>

                {/* Reasons */}
                {recommendation.reasons.length > 0 && (
                  <div className="mt-4">
                    <p className="text-xs font-medium text-gray-700 mb-2">Why we recommend this:</p>
                    <div className="flex flex-wrap gap-1">
                      {recommendation.reasons.slice(0, 2).map((reason) => (
                        <span
                          key={reason}
                          className="inline-flex items-center rounded-md bg-gray-100 px-2 py-1 text-xs text-gray-700"
                        >
                          {RECOMMENDATION_REASON_NAMES[reason]}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Included Options Count */}
                {recommendation.includedOptions.length > 0 && (
                  <div className="mt-3 text-xs text-gray-600">
                    Includes {recommendation.includedOptions.length} option
                    {recommendation.includedOptions.length !== 1 ? 's' : ''}
                  </div>
                )}

                {/* Popularity Score */}
                {isHighConfidence && recommendation.popularityScore > 50 && (
                  <div className="mt-2 flex items-center text-xs text-gray-600">
                    <svg
                      className="mr-1 h-4 w-4 text-yellow-400"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                      aria-hidden="true"
                    >
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                    Popular choice
                  </div>
                )}

                {/* Action Button */}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handlePackageSelect(recommendation, index);
                  }}
                  className={`mt-4 w-full rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                    isSelected
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-gray-900 text-white hover:bg-gray-800'
                  }`}
                  disabled={acceptRecommendation.isPending}
                >
                  {isSelected ? 'Selected' : 'Add Package'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Popular Configurations */}
      {showPopularConfigurations &&
        recommendationsData?.popularConfigurations &&
        recommendationsData.popularConfigurations.length > 0 && (
          <div className="mt-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Popular Configurations for Similar Vehicles
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {recommendationsData.popularConfigurations.slice(0, 3).map((config) => (
                <div
                  key={config.id}
                  className="rounded-lg border border-gray-200 bg-white p-4 hover:border-gray-300 hover:shadow-sm transition-all"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900">{config.vehicleName}</h4>
                      {config.trimName && (
                        <p className="text-sm text-gray-600">{config.trimName}</p>
                      )}
                    </div>
                    <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
                      {config.popularityCount} buyers
                    </span>
                  </div>
                  <div className="mt-3">
                    <p className="text-lg font-semibold text-gray-900">
                      {formatSavings(config.totalPrice)}
                    </p>
                    {config.averageRating && (
                      <div className="mt-1 flex items-center text-sm text-gray-600">
                        <svg
                          className="mr-1 h-4 w-4 text-yellow-400"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                          aria-hidden="true"
                        >
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                        {config.averageRating.toFixed(1)} rating
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
    </div>
  );
});