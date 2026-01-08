/**
 * Saved configuration type definitions for AutoSelect frontend application
 * Provides comprehensive type-safe interfaces for saved configurations and comparison features
 */

/**
 * Saved configuration status
 */
export type SavedConfigurationStatus = 'active' | 'archived' | 'shared';

/**
 * Configuration visibility level
 */
export type ConfigurationVisibility = 'private' | 'public' | 'shared';

/**
 * Comparison highlight type
 */
export type ComparisonHighlightType = 'price' | 'feature' | 'specification' | 'package';

/**
 * Saved configuration entity
 */
export interface SavedConfiguration {
  readonly id: string;
  readonly userId: string;
  readonly name: string;
  readonly description?: string;
  readonly vehicleId: string;
  readonly trimId?: string;
  readonly colorId?: string;
  readonly selectedPackageIds: readonly string[];
  readonly selectedOptionIds: readonly string[];
  readonly pricing: {
    readonly basePrice: number;
    readonly optionsPrice: number;
    readonly packagesPrice: number;
    readonly packagesDiscount: number;
    readonly subtotal: number;
    readonly taxAmount: number;
    readonly destinationCharge: number;
    readonly total: number;
  };
  readonly status: SavedConfigurationStatus;
  readonly visibility: ConfigurationVisibility;
  readonly shareToken?: string;
  readonly shareUrl?: string;
  readonly sharedAt?: string;
  readonly viewCount: number;
  readonly lastViewedAt?: string;
  readonly createdAt: string;
  readonly updatedAt: string;
  readonly metadata?: Record<string, string | number | boolean>;
}

/**
 * Saved configuration with vehicle details
 */
export interface SavedConfigurationWithVehicle extends SavedConfiguration {
  readonly vehicle: {
    readonly id: string;
    readonly make: string;
    readonly model: string;
    readonly year: number;
    readonly trim?: string;
    readonly imageUrl?: string;
  };
}

/**
 * Request to save a configuration
 */
export interface SaveConfigurationRequest {
  readonly name: string;
  readonly description?: string;
  readonly vehicleId: string;
  readonly trimId?: string;
  readonly colorId?: string;
  readonly packageIds: readonly string[];
  readonly optionIds: readonly string[];
  readonly visibility?: ConfigurationVisibility;
  readonly notes?: string;
}

/**
 * Response after saving a configuration
 */
export interface SaveConfigurationResponse {
  readonly id: string;
  readonly name: string;
  readonly description?: string;
  readonly vehicleId: string;
  readonly trimId?: string;
  readonly colorId?: string;
  readonly packageIds: readonly string[];
  readonly optionIds: readonly string[];
  readonly pricing: {
    readonly basePrice: number;
    readonly optionsPrice: number;
    readonly packagesPrice: number;
    readonly packagesDiscount: number;
    readonly subtotal: number;
    readonly taxAmount: number;
    readonly destinationCharge: number;
    readonly total: number;
  };
  readonly status: SavedConfigurationStatus;
  readonly visibility: ConfigurationVisibility;
  readonly shareToken?: string;
  readonly shareUrl?: string;
  readonly createdAt: string;
  readonly updatedAt: string;
}

/**
 * Request to update a saved configuration
 */
export interface UpdateSavedConfigurationRequest {
  readonly name?: string;
  readonly description?: string;
  readonly visibility?: ConfigurationVisibility;
  readonly status?: SavedConfigurationStatus;
  readonly notes?: string;
}

/**
 * Request to share a configuration
 */
export interface ShareConfigurationRequest {
  readonly configurationId: string;
  readonly visibility: ConfigurationVisibility;
  readonly expiresInDays?: number;
}

/**
 * Response after sharing a configuration
 */
export interface ShareConfigurationResponse {
  readonly shareToken: string;
  readonly shareUrl: string;
  readonly expiresAt?: string;
  readonly visibility: ConfigurationVisibility;
}

/**
 * List of saved configurations request
 */
export interface SavedConfigurationListRequest {
  readonly page?: number;
  readonly pageSize?: number;
  readonly status?: SavedConfigurationStatus;
  readonly visibility?: ConfigurationVisibility;
  readonly sortBy?: 'name' | 'createdAt' | 'updatedAt' | 'viewCount';
  readonly sortDirection?: 'asc' | 'desc';
  readonly search?: string;
}

/**
 * List of saved configurations response
 */
export interface SavedConfigurationListResponse {
  readonly configurations: readonly SavedConfigurationWithVehicle[];
  readonly total: number;
  readonly page: number;
  readonly pageSize: number;
  readonly totalPages: number;
}

/**
 * Configuration comparison item
 */
export interface ConfigurationComparisonItem {
  readonly configurationId: string;
  readonly name: string;
  readonly vehicleId: string;
  readonly vehicle: {
    readonly make: string;
    readonly model: string;
    readonly year: number;
    readonly trim?: string;
    readonly imageUrl?: string;
  };
  readonly trimId?: string;
  readonly colorId?: string;
  readonly color?: {
    readonly name: string;
    readonly hexCode: string;
  };
  readonly packages: readonly {
    readonly id: string;
    readonly name: string;
    readonly price: number;
  }[];
  readonly options: readonly {
    readonly id: string;
    readonly name: string;
    readonly category: string;
    readonly price: number;
  }[];
  readonly pricing: {
    readonly basePrice: number;
    readonly optionsPrice: number;
    readonly packagesPrice: number;
    readonly packagesDiscount: number;
    readonly subtotal: number;
    readonly taxAmount: number;
    readonly destinationCharge: number;
    readonly total: number;
  };
}

/**
 * Configuration comparison request
 */
export interface ConfigurationComparisonRequest {
  readonly configurationIds: readonly string[];
  readonly highlightDifferences?: boolean;
}

/**
 * Price difference in comparison
 */
export interface PriceDifference {
  readonly configurationId: string;
  readonly basePrice: number;
  readonly optionsPrice: number;
  readonly packagesPrice: number;
  readonly total: number;
  readonly differenceFromLowest: number;
  readonly differencePercentage: number;
}

/**
 * Feature difference in comparison
 */
export interface FeatureDifference {
  readonly category: string;
  readonly featureName: string;
  readonly configurations: Record<string, boolean | string | number>;
  readonly isDifferent: boolean;
}

/**
 * Package difference in comparison
 */
export interface PackageDifference {
  readonly packageId: string;
  readonly packageName: string;
  readonly configurations: Record<string, boolean>;
  readonly price: number;
}

/**
 * Configuration comparison result
 */
export interface ConfigurationComparisonResult {
  readonly configurations: readonly ConfigurationComparisonItem[];
  readonly priceDifferences: readonly PriceDifference[];
  readonly featureDifferences: readonly FeatureDifference[];
  readonly packageDifferences: readonly PackageDifference[];
  readonly lowestPriceConfigurationId: string;
  readonly highestPriceConfigurationId: string;
  readonly averagePrice: number;
  readonly priceRange: {
    readonly min: number;
    readonly max: number;
  };
  readonly comparedAt: string;
}

/**
 * Comparison highlight
 */
export interface ComparisonHighlight {
  readonly type: ComparisonHighlightType;
  readonly configurationId: string;
  readonly field: string;
  readonly value: string | number | boolean;
  readonly isDifferent: boolean;
  readonly isAdvantage?: boolean;
}

/**
 * Configuration comparison summary
 */
export interface ConfigurationComparisonSummary {
  readonly totalConfigurations: number;
  readonly priceSpread: number;
  readonly uniqueFeatures: number;
  readonly commonFeatures: number;
  readonly uniquePackages: number;
  readonly commonPackages: number;
  readonly highlights: readonly ComparisonHighlight[];
}

/**
 * Type guard to check if configuration has share token
 */
export function hasShareToken(
  config: SavedConfiguration,
): config is SavedConfiguration & { readonly shareToken: string; readonly shareUrl: string } {
  return config.shareToken !== undefined && config.shareUrl !== undefined;
}

/**
 * Type guard to check if configuration is shared
 */
export function isSharedConfiguration(config: SavedConfiguration): boolean {
  return config.visibility === 'shared' || config.visibility === 'public';
}

/**
 * Type guard to check if configuration is active
 */
export function isActiveConfiguration(config: SavedConfiguration): boolean {
  return config.status === 'active';
}

/**
 * Type guard to check if configuration has been viewed
 */
export function hasBeenViewed(
  config: SavedConfiguration,
): config is SavedConfiguration & { readonly lastViewedAt: string } {
  return config.lastViewedAt !== undefined && config.viewCount > 0;
}

/**
 * Helper type for partial configuration updates
 */
export type PartialSavedConfigurationUpdate = Partial<
  Omit<SavedConfiguration, 'id' | 'userId' | 'vehicleId' | 'createdAt' | 'updatedAt'>
>;

/**
 * Helper type for configuration with vehicle
 */
export type ConfigurationWithVehicle = SavedConfiguration & {
  readonly vehicle: NonNullable<SavedConfigurationWithVehicle['vehicle']>;
};

/**
 * Helper type for shared configuration
 */
export type SharedConfiguration = SavedConfiguration & {
  readonly shareToken: string;
  readonly shareUrl: string;
  readonly visibility: 'shared' | 'public';
};

/**
 * Configuration comparison constraints
 */
export const COMPARISON_CONSTRAINTS = {
  MIN_CONFIGURATIONS: 2,
  MAX_CONFIGURATIONS: 3,
  DEFAULT_CONFIGURATIONS: 2,
} as const;

/**
 * Saved configuration constraints
 */
export const SAVED_CONFIGURATION_CONSTRAINTS = {
  MIN_NAME_LENGTH: 3,
  MAX_NAME_LENGTH: 100,
  MAX_DESCRIPTION_LENGTH: 500,
  MAX_CONFIGURATIONS_PER_USER: 50,
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
} as const;

/**
 * Configuration status display names
 */
export const CONFIGURATION_STATUS_NAMES: Record<SavedConfigurationStatus, string> = {
  active: 'Active',
  archived: 'Archived',
  shared: 'Shared',
} as const;

/**
 * Configuration visibility display names
 */
export const CONFIGURATION_VISIBILITY_NAMES: Record<ConfigurationVisibility, string> = {
  private: 'Private',
  public: 'Public',
  shared: 'Shared',
} as const;

/**
 * Comparison highlight type display names
 */
export const COMPARISON_HIGHLIGHT_TYPE_NAMES: Record<ComparisonHighlightType, string> = {
  price: 'Price',
  feature: 'Feature',
  specification: 'Specification',
  package: 'Package',
} as const;

/**
 * Format currency for display
 */
export function formatConfigurationPrice(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Calculate price difference percentage
 */
export function calculatePriceDifferencePercentage(price: number, basePrice: number): number {
  if (basePrice === 0) {
    return 0;
  }
  return ((price - basePrice) / basePrice) * 100;
}

/**
 * Format price difference for display
 */
export function formatPriceDifference(difference: number): string {
  const sign = difference >= 0 ? '+' : '';
  return `${sign}${formatConfigurationPrice(Math.abs(difference))}`;
}

/**
 * Format price difference percentage for display
 */
export function formatPriceDifferencePercentage(percentage: number): string {
  const sign = percentage >= 0 ? '+' : '';
  return `${sign}${percentage.toFixed(1)}%`;
}

/**
 * Check if configurations can be compared
 */
export function canCompareConfigurations(count: number): boolean {
  return (
    count >= COMPARISON_CONSTRAINTS.MIN_CONFIGURATIONS &&
    count <= COMPARISON_CONSTRAINTS.MAX_CONFIGURATIONS
  );
}

/**
 * Validate configuration name
 */
export function isValidConfigurationName(name: string): boolean {
  const trimmed = name.trim();
  return (
    trimmed.length >= SAVED_CONFIGURATION_CONSTRAINTS.MIN_NAME_LENGTH &&
    trimmed.length <= SAVED_CONFIGURATION_CONSTRAINTS.MAX_NAME_LENGTH
  );
}

/**
 * Validate configuration description
 */
export function isValidConfigurationDescription(description: string | undefined): boolean {
  if (!description) {
    return true;
  }
  return description.trim().length <= SAVED_CONFIGURATION_CONSTRAINTS.MAX_DESCRIPTION_LENGTH;
}