/**
 * Vehicle configuration type definitions for AutoSelect frontend application
 * Provides comprehensive type-safe interfaces for configuration wizard, pricing, and validation
 */

/**
 * Configuration step identifiers for wizard navigation
 */
export type ConfigurationStep =
  | 'select-trim'
  | 'choose-color'
  | 'select-packages'
  | 'add-features'
  | 'review';

/**
 * Option category types for feature organization
 */
export type OptionCategory =
  | 'exterior'
  | 'interior'
  | 'technology'
  | 'safety'
  | 'performance'
  | 'comfort'
  | 'entertainment';

/**
 * Configuration validation status
 */
export type ValidationStatus = 'valid' | 'invalid' | 'warning';

/**
 * Vehicle option definition
 */
export interface VehicleOption {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly category: OptionCategory;
  readonly price: number;
  readonly imageUrl?: string;
  readonly isRequired: boolean;
  readonly isAvailable: boolean;
  readonly compatibleTrims?: readonly string[];
  readonly compatibleYears?: readonly number[];
  readonly requiredOptions?: readonly string[];
  readonly mutuallyExclusiveWith?: readonly string[];
  readonly metadata?: Record<string, string | number | boolean>;
}

/**
 * Package definition with bundled options
 */
export interface Package {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly price: number;
  readonly discountPercentage: number;
  readonly imageUrl?: string;
  readonly includedOptions: readonly string[];
  readonly compatibleTrims?: readonly string[];
  readonly compatibleYears?: readonly number[];
  readonly isPopular: boolean;
  readonly savings: number;
}

/**
 * Configuration step metadata
 */
export interface ConfigurationStepMetadata {
  readonly step: ConfigurationStep;
  readonly title: string;
  readonly description: string;
  readonly isComplete: boolean;
  readonly isAccessible: boolean;
  readonly order: number;
}

/**
 * Pricing breakdown with itemized costs
 */
export interface PricingBreakdown {
  readonly basePrice: number;
  readonly optionsPrice: number;
  readonly packagesPrice: number;
  readonly packagesDiscount: number;
  readonly subtotal: number;
  readonly taxRate: number;
  readonly taxAmount: number;
  readonly destinationCharge: number;
  readonly total: number;
  readonly itemizedOptions: readonly {
    readonly id: string;
    readonly name: string;
    readonly price: number;
  }[];
  readonly itemizedPackages: readonly {
    readonly id: string;
    readonly name: string;
    readonly price: number;
    readonly discount: number;
  }[];
}

/**
 * Configuration validation error
 */
export interface ConfigurationValidationError {
  readonly field: string;
  readonly message: string;
  readonly severity: 'error' | 'warning';
  readonly relatedOptionIds?: readonly string[];
}

/**
 * Configuration validation result
 */
export interface ConfigurationValidationResult {
  readonly isValid: boolean;
  readonly errors: readonly ConfigurationValidationError[];
  readonly warnings: readonly ConfigurationValidationError[];
  readonly missingRequiredOptions: readonly string[];
  readonly incompatibleSelections: readonly string[];
}

/**
 * Color selection option
 */
export interface ColorOption {
  readonly id: string;
  readonly name: string;
  readonly hexCode: string;
  readonly category: 'standard' | 'metallic' | 'premium';
  readonly price: number;
  readonly imageUrl: string;
  readonly isAvailable: boolean;
}

/**
 * Trim level selection
 */
export interface TrimLevel {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly basePrice: number;
  readonly imageUrl: string;
  readonly features: readonly string[];
  readonly isAvailable: boolean;
}

/**
 * Complete configuration state
 */
export interface ConfigurationState {
  readonly vehicleId: string;
  readonly trimId?: string;
  readonly colorId?: string;
  readonly selectedPackageIds: readonly string[];
  readonly selectedOptionIds: readonly string[];
  readonly currentStep: ConfigurationStep;
  readonly completedSteps: readonly ConfigurationStep[];
  readonly pricing?: PricingBreakdown;
  readonly validation?: ConfigurationValidationResult;
  readonly notes?: string;
  readonly createdAt: string;
  readonly updatedAt: string;
}

/**
 * Configuration save request
 */
export interface ConfigurationSaveRequest {
  readonly vehicleId: string;
  readonly trimId?: string;
  readonly colorId?: string;
  readonly packageIds: readonly string[];
  readonly optionIds: readonly string[];
  readonly notes?: string;
}

/**
 * Configuration save response
 */
export interface ConfigurationSaveResponse {
  readonly id: string;
  readonly vehicleId: string;
  readonly trimId?: string;
  readonly colorId?: string;
  readonly packageIds: readonly string[];
  readonly optionIds: readonly string[];
  readonly pricing: PricingBreakdown;
  readonly validation: ConfigurationValidationResult;
  readonly notes?: string;
  readonly createdAt: string;
  readonly updatedAt: string;
}

/**
 * Configuration pricing request
 */
export interface ConfigurationPricingRequest {
  readonly vehicleId: string;
  readonly trimId?: string;
  readonly packageIds: readonly string[];
  readonly optionIds: readonly string[];
  readonly region?: string;
  readonly includeDestination?: boolean;
  readonly includeTax?: boolean;
}

/**
 * Configuration validation request
 */
export interface ConfigurationValidationRequest {
  readonly vehicleId: string;
  readonly trimId?: string;
  readonly year?: number;
  readonly packageIds: readonly string[];
  readonly optionIds: readonly string[];
}

/**
 * Vehicle options response
 */
export interface VehicleOptionsResponse {
  readonly vehicleId: string;
  readonly options: readonly VehicleOption[];
  readonly packages: readonly Package[];
  readonly colors: readonly ColorOption[];
  readonly trims: readonly TrimLevel[];
}

/**
 * Configuration wizard progress
 */
export interface ConfigurationProgress {
  readonly currentStep: ConfigurationStep;
  readonly completedSteps: readonly ConfigurationStep[];
  readonly totalSteps: number;
  readonly percentComplete: number;
  readonly canProceed: boolean;
  readonly canGoBack: boolean;
}

/**
 * Configuration summary for review
 */
export interface ConfigurationSummary {
  readonly vehicle: {
    readonly id: string;
    readonly make: string;
    readonly model: string;
    readonly year: number;
  };
  readonly trim?: TrimLevel;
  readonly color?: ColorOption;
  readonly packages: readonly Package[];
  readonly options: readonly VehicleOption[];
  readonly pricing: PricingBreakdown;
  readonly validation: ConfigurationValidationResult;
}

/**
 * Type guard to check if configuration has pricing
 */
export function hasPricing(
  config: ConfigurationState,
): config is ConfigurationState & { readonly pricing: PricingBreakdown } {
  return config.pricing !== undefined;
}

/**
 * Type guard to check if configuration has validation
 */
export function hasValidation(
  config: ConfigurationState,
): config is ConfigurationState & { readonly validation: ConfigurationValidationResult } {
  return config.validation !== undefined;
}

/**
 * Type guard to check if configuration is valid
 */
export function isConfigurationValid(config: ConfigurationState): boolean {
  return config.validation?.isValid ?? false;
}

/**
 * Type guard to check if step is complete
 */
export function isStepComplete(
  config: ConfigurationState,
  step: ConfigurationStep,
): boolean {
  return config.completedSteps.includes(step);
}

/**
 * Helper type for partial configuration updates
 */
export type PartialConfigurationState = Partial<
  Omit<ConfigurationState, 'vehicleId' | 'createdAt' | 'updatedAt'>
>;

/**
 * Helper type for configuration with required pricing
 */
export type ConfigurationWithPricing = ConfigurationState & {
  readonly pricing: PricingBreakdown;
};

/**
 * Helper type for configuration with required validation
 */
export type ConfigurationWithValidation = ConfigurationState & {
  readonly validation: ConfigurationValidationResult;
};

/**
 * Helper type for complete configuration
 */
export type CompleteConfiguration = ConfigurationState & {
  readonly trimId: string;
  readonly colorId: string;
  readonly pricing: PricingBreakdown;
  readonly validation: ConfigurationValidationResult;
};

/**
 * Configuration step order mapping
 */
export const CONFIGURATION_STEP_ORDER: Record<ConfigurationStep, number> = {
  'select-trim': 1,
  'choose-color': 2,
  'select-packages': 3,
  'add-features': 4,
  'review': 5,
} as const;

/**
 * Configuration step titles
 */
export const CONFIGURATION_STEP_TITLES: Record<ConfigurationStep, string> = {
  'select-trim': 'Select Trim Level',
  'choose-color': 'Choose Color',
  'select-packages': 'Select Packages',
  'add-features': 'Add Features',
  'review': 'Review Configuration',
} as const;

/**
 * Option category display names
 */
export const OPTION_CATEGORY_NAMES: Record<OptionCategory, string> = {
  exterior: 'Exterior',
  interior: 'Interior',
  technology: 'Technology',
  safety: 'Safety',
  performance: 'Performance',
  comfort: 'Comfort',
  entertainment: 'Entertainment',
} as const;