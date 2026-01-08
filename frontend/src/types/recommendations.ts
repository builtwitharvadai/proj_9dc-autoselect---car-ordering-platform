/**
 * Package recommendation and analytics type definitions for AutoSelect frontend
 * Provides comprehensive type-safe interfaces for recommendation engine responses
 */

/**
 * Recommendation confidence level
 */
export type RecommendationConfidence = 'high' | 'medium' | 'low';

/**
 * Recommendation reason type
 */
export type RecommendationReason =
  | 'popular_combination'
  | 'cost_savings'
  | 'frequently_bought_together'
  | 'complements_selection'
  | 'dealer_recommended'
  | 'similar_vehicles';

/**
 * Analytics event type for tracking recommendation interactions
 */
export type RecommendationEventType =
  | 'recommendation_viewed'
  | 'recommendation_clicked'
  | 'recommendation_accepted'
  | 'recommendation_dismissed'
  | 'comparison_viewed';

/**
 * Package recommendation with savings and value proposition
 */
export interface PackageRecommendation {
  readonly id: string;
  readonly packageId: string;
  readonly name: string;
  readonly description: string;
  readonly basePrice: number;
  readonly discountedPrice: number;
  readonly savingsAmount: number;
  readonly savingsPercentage: number;
  readonly confidence: RecommendationConfidence;
  readonly reasons: readonly RecommendationReason[];
  readonly includedOptions: readonly string[];
  readonly compatibleWithSelection: boolean;
  readonly popularityScore: number;
  readonly estimatedDeliveryImpact?: number;
  readonly imageUrl?: string;
  readonly metadata?: Record<string, string | number | boolean>;
}

/**
 * Popular configuration for similar vehicles
 */
export interface PopularConfiguration {
  readonly id: string;
  readonly vehicleId: string;
  readonly vehicleName: string;
  readonly trimId?: string;
  readonly trimName?: string;
  readonly colorId?: string;
  readonly colorName?: string;
  readonly packageIds: readonly string[];
  readonly optionIds: readonly string[];
  readonly totalPrice: number;
  readonly popularityCount: number;
  readonly averageRating?: number;
  readonly configurationAge: number;
  readonly imageUrl?: string;
  readonly description?: string;
}

/**
 * Recommendation analytics data
 */
export interface RecommendationAnalytics {
  readonly recommendationId: string;
  readonly eventType: RecommendationEventType;
  readonly timestamp: string;
  readonly userId?: string;
  readonly sessionId?: string;
  readonly vehicleId: string;
  readonly packageId?: string;
  readonly position: number;
  readonly confidence: RecommendationConfidence;
  readonly metadata?: Record<string, string | number | boolean>;
}

/**
 * Recommendation request parameters
 */
export interface RecommendationRequest {
  readonly vehicleId: string;
  readonly trimId?: string;
  readonly selectedPackageIds?: readonly string[];
  readonly selectedOptionIds?: readonly string[];
  readonly budget?: number;
  readonly maxRecommendations?: number;
  readonly includePopularConfigurations?: boolean;
  readonly region?: string;
}

/**
 * Recommendation response with packages and configurations
 */
export interface RecommendationResponse {
  readonly vehicleId: string;
  readonly recommendations: readonly PackageRecommendation[];
  readonly popularConfigurations: readonly PopularConfiguration[];
  readonly totalSavingsOpportunity: number;
  readonly averageConfigurationPrice: number;
  readonly generatedAt: string;
  readonly metadata?: {
    readonly processingTimeMs: number;
    readonly algorithmVersion: string;
    readonly dataFreshness: string;
  };
}

/**
 * Recommendation comparison data
 */
export interface RecommendationComparison {
  readonly baseConfiguration: {
    readonly packageIds: readonly string[];
    readonly optionIds: readonly string[];
    readonly totalPrice: number;
  };
  readonly recommendedConfiguration: {
    readonly packageIds: readonly string[];
    readonly optionIds: readonly string[];
    readonly totalPrice: number;
  };
  readonly priceDifference: number;
  readonly priceDifferencePercentage: number;
  readonly additionalFeatures: readonly string[];
  readonly removedFeatures: readonly string[];
  readonly valueScore: number;
}

/**
 * Recommendation acceptance tracking
 */
export interface RecommendationAcceptance {
  readonly recommendationId: string;
  readonly packageId: string;
  readonly acceptedAt: string;
  readonly userId?: string;
  readonly sessionId?: string;
  readonly vehicleId: string;
  readonly finalPrice: number;
  readonly savingsRealized: number;
}

/**
 * Recommendation performance metrics
 */
export interface RecommendationMetrics {
  readonly totalRecommendations: number;
  readonly acceptanceRate: number;
  readonly averageSavings: number;
  readonly topPerformingPackages: readonly {
    readonly packageId: string;
    readonly packageName: string;
    readonly acceptanceRate: number;
    readonly averageSavings: number;
  }[];
  readonly conversionRate: number;
  readonly averageResponseTime: number;
}

/**
 * Type guard to check if recommendation has high confidence
 */
export function hasHighConfidence(
  recommendation: PackageRecommendation,
): recommendation is PackageRecommendation & { readonly confidence: 'high' } {
  return recommendation.confidence === 'high';
}

/**
 * Type guard to check if recommendation has significant savings
 */
export function hasSignificantSavings(
  recommendation: PackageRecommendation,
  threshold: number = 10,
): boolean {
  return recommendation.savingsPercentage >= threshold;
}

/**
 * Type guard to check if configuration is popular
 */
export function isPopularConfiguration(
  config: PopularConfiguration,
  threshold: number = 100,
): boolean {
  return config.popularityCount >= threshold;
}

/**
 * Helper type for partial recommendation updates
 */
export type PartialRecommendationRequest = Partial<
  Omit<RecommendationRequest, 'vehicleId'>
> & {
  readonly vehicleId: string;
};

/**
 * Helper type for recommendation with required metadata
 */
export type RecommendationWithMetadata = RecommendationResponse & {
  readonly metadata: NonNullable<RecommendationResponse['metadata']>;
};

/**
 * Recommendation confidence score mapping
 */
export const CONFIDENCE_SCORES: Record<RecommendationConfidence, number> = {
  high: 0.8,
  medium: 0.5,
  low: 0.3,
} as const;

/**
 * Recommendation reason display names
 */
export const RECOMMENDATION_REASON_NAMES: Record<RecommendationReason, string> = {
  popular_combination: 'Popular Combination',
  cost_savings: 'Cost Savings',
  frequently_bought_together: 'Frequently Bought Together',
  complements_selection: 'Complements Your Selection',
  dealer_recommended: 'Dealer Recommended',
  similar_vehicles: 'Popular with Similar Vehicles',
} as const;

/**
 * Recommendation event type display names
 */
export const RECOMMENDATION_EVENT_NAMES: Record<RecommendationEventType, string> = {
  recommendation_viewed: 'Viewed',
  recommendation_clicked: 'Clicked',
  recommendation_accepted: 'Accepted',
  recommendation_dismissed: 'Dismissed',
  comparison_viewed: 'Comparison Viewed',
} as const;

/**
 * Default recommendation constraints
 */
export const RECOMMENDATION_CONSTRAINTS = {
  MAX_RECOMMENDATIONS: 5,
  MIN_CONFIDENCE_THRESHOLD: 0.3,
  MIN_SAVINGS_PERCENTAGE: 5,
  MAX_POPULAR_CONFIGURATIONS: 3,
  DEFAULT_REGION: 'US',
} as const;

/**
 * Format savings amount as currency
 */
export function formatSavings(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Format savings percentage
 */
export function formatSavingsPercentage(percentage: number): string {
  return `${percentage.toFixed(1)}%`;
}

/**
 * Calculate value score for recommendation comparison
 */
export function calculateValueScore(
  savingsPercentage: number,
  confidence: RecommendationConfidence,
  popularityScore: number,
): number {
  const confidenceWeight = CONFIDENCE_SCORES[confidence];
  const normalizedPopularity = Math.min(popularityScore / 100, 1);
  const normalizedSavings = Math.min(savingsPercentage / 100, 1);

  return (
    normalizedSavings * 0.4 +
    confidenceWeight * 0.4 +
    normalizedPopularity * 0.2
  );
}

/**
 * Sort recommendations by value score
 */
export function sortByValueScore(
  recommendations: readonly PackageRecommendation[],
): readonly PackageRecommendation[] {
  return [...recommendations].sort((a, b) => {
    const scoreA = calculateValueScore(
      a.savingsPercentage,
      a.confidence,
      a.popularityScore,
    );
    const scoreB = calculateValueScore(
      b.savingsPercentage,
      b.confidence,
      b.popularityScore,
    );
    return scoreB - scoreA;
  });
}

/**
 * Filter recommendations by minimum confidence
 */
export function filterByConfidence(
  recommendations: readonly PackageRecommendation[],
  minConfidence: RecommendationConfidence = 'low',
): readonly PackageRecommendation[] {
  const minScore = CONFIDENCE_SCORES[minConfidence];
  return recommendations.filter(
    (rec) => CONFIDENCE_SCORES[rec.confidence] >= minScore,
  );
}

/**
 * Filter recommendations by minimum savings
 */
export function filterByMinimumSavings(
  recommendations: readonly PackageRecommendation[],
  minSavingsPercentage: number = RECOMMENDATION_CONSTRAINTS.MIN_SAVINGS_PERCENTAGE,
): readonly PackageRecommendation[] {
  return recommendations.filter(
    (rec) => rec.savingsPercentage >= minSavingsPercentage,
  );
}

/**
 * Get top N recommendations by value
 */
export function getTopRecommendations(
  recommendations: readonly PackageRecommendation[],
  count: number = RECOMMENDATION_CONSTRAINTS.MAX_RECOMMENDATIONS,
): readonly PackageRecommendation[] {
  return sortByValueScore(recommendations).slice(0, count);
}

/**
 * Check if recommendation is compatible with current selection
 */
export function isCompatibleWithSelection(
  recommendation: PackageRecommendation,
): recommendation is PackageRecommendation & { readonly compatibleWithSelection: true } {
  return recommendation.compatibleWithSelection;
}

/**
 * Calculate total potential savings from recommendations
 */
export function calculateTotalPotentialSavings(
  recommendations: readonly PackageRecommendation[],
): number {
  return recommendations.reduce((total, rec) => total + rec.savingsAmount, 0);
}

/**
 * Get recommendation reasons as display strings
 */
export function getReasonDisplayNames(
  reasons: readonly RecommendationReason[],
): readonly string[] {
  return reasons.map((reason) => RECOMMENDATION_REASON_NAMES[reason]);
}

/**
 * Create recommendation analytics event
 */
export function createAnalyticsEvent(
  eventType: RecommendationEventType,
  recommendation: PackageRecommendation,
  position: number,
  userId?: string,
  sessionId?: string,
): RecommendationAnalytics {
  return {
    recommendationId: recommendation.id,
    eventType,
    timestamp: new Date().toISOString(),
    userId,
    sessionId,
    vehicleId: '',
    packageId: recommendation.packageId,
    position,
    confidence: recommendation.confidence,
  };
}