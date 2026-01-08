/**
 * Vehicle type definitions for AutoSelect frontend application
 * Provides comprehensive type-safe interfaces for vehicle data, API responses, and filtering
 */

/**
 * Vehicle availability status
 */
export type VehicleAvailability = 'available' | 'reserved' | 'sold' | 'unavailable';

/**
 * Vehicle body style types
 */
export type BodyStyle =
  | 'sedan'
  | 'suv'
  | 'truck'
  | 'coupe'
  | 'convertible'
  | 'wagon'
  | 'van'
  | 'hatchback';

/**
 * Vehicle fuel type
 */
export type FuelType = 'gasoline' | 'diesel' | 'electric' | 'hybrid' | 'plug-in-hybrid';

/**
 * Vehicle transmission type
 */
export type TransmissionType = 'automatic' | 'manual' | 'cvt' | 'dual-clutch';

/**
 * Vehicle drivetrain type
 */
export type DrivetrainType = 'fwd' | 'rwd' | 'awd' | '4wd';

/**
 * Sort field options for vehicle search
 */
export type VehicleSortField =
  | 'price'
  | 'year'
  | 'make'
  | 'model'
  | 'created_at'
  | 'updated_at'
  | 'relevance';

/**
 * Sort direction
 */
export type SortDirection = 'asc' | 'desc';

/**
 * Vehicle dimensions
 */
export interface VehicleDimensions {
  readonly length: number;
  readonly width: number;
  readonly height: number;
  readonly wheelbase: number;
  readonly groundClearance?: number;
  readonly cargoVolume?: number;
}

/**
 * Vehicle fuel economy
 */
export interface VehicleFuelEconomy {
  readonly city: number;
  readonly highway: number;
  readonly combined: number;
}

/**
 * Vehicle specifications
 */
export interface VehicleSpecifications {
  readonly engine: string;
  readonly horsepower: number;
  readonly torque: number;
  readonly transmission: TransmissionType;
  readonly drivetrain: DrivetrainType;
  readonly fuelType: FuelType;
  readonly fuelEconomy: VehicleFuelEconomy;
  readonly seatingCapacity: number;
  readonly dimensions: VehicleDimensions;
  readonly curbWeight?: number;
  readonly towingCapacity?: number;
  readonly customAttributes?: Record<string, string | number | boolean>;
}

/**
 * Vehicle features
 */
export interface VehicleFeatures {
  readonly safety: readonly string[];
  readonly comfort: readonly string[];
  readonly technology: readonly string[];
  readonly entertainment: readonly string[];
  readonly exterior: readonly string[];
  readonly interior: readonly string[];
}

/**
 * Vehicle inventory information
 */
export interface VehicleInventory {
  readonly id: string;
  readonly vin: string;
  readonly status: VehicleAvailability;
  readonly location: string;
  readonly dealershipId: string;
  readonly quantity: number;
  readonly reservedQuantity: number;
  readonly availableQuantity: number;
}

/**
 * Core vehicle data structure
 */
export interface Vehicle {
  readonly id: string;
  readonly make: string;
  readonly model: string;
  readonly year: number;
  readonly trim?: string;
  readonly bodyStyle: BodyStyle;
  readonly msrp: number;
  readonly price: number;
  readonly description: string;
  readonly imageUrl: string;
  readonly images: readonly string[];
  readonly specifications: VehicleSpecifications;
  readonly features: VehicleFeatures;
  readonly availability: VehicleAvailability;
  readonly inventory?: VehicleInventory;
  readonly createdAt: string;
  readonly updatedAt: string;
  readonly isDeleted: boolean;
}

/**
 * Price range filter
 */
export interface PriceRange {
  readonly min: number;
  readonly max: number;
}

/**
 * Year range filter
 */
export interface YearRange {
  readonly min: number;
  readonly max: number;
}

/**
 * Seating capacity range filter
 */
export interface SeatingRange {
  readonly min: number;
  readonly max: number;
}

/**
 * Vehicle search and filter parameters
 */
export interface VehicleFilters {
  readonly query?: string;
  readonly make?: readonly string[];
  readonly model?: readonly string[];
  readonly year?: YearRange;
  readonly bodyStyle?: readonly BodyStyle[];
  readonly fuelType?: readonly FuelType[];
  readonly transmission?: readonly TransmissionType[];
  readonly drivetrain?: readonly DrivetrainType[];
  readonly price?: PriceRange;
  readonly seatingCapacity?: SeatingRange;
  readonly availability?: readonly VehicleAvailability[];
  readonly features?: readonly string[];
  readonly customAttributes?: Record<string, string | number | boolean>;
}

/**
 * Search parameters including pagination and sorting
 */
export interface SearchParams {
  readonly filters?: VehicleFilters;
  readonly sortBy?: VehicleSortField;
  readonly sortDirection?: SortDirection;
  readonly page?: number;
  readonly pageSize?: number;
  readonly includeInventory?: boolean;
}

/**
 * Facet bucket for aggregation results
 */
export interface FacetBucket {
  readonly value: string;
  readonly count: number;
}

/**
 * Range facet bucket for numeric aggregations
 */
export interface RangeFacetBucket {
  readonly from: number;
  readonly to: number;
  readonly count: number;
}

/**
 * Search facets for filtering
 */
export interface SearchFacets {
  readonly makes: readonly FacetBucket[];
  readonly models: readonly FacetBucket[];
  readonly years: readonly RangeFacetBucket[];
  readonly bodyStyles: readonly FacetBucket[];
  readonly fuelTypes: readonly FacetBucket[];
  readonly transmissions: readonly FacetBucket[];
  readonly drivetrains: readonly FacetBucket[];
  readonly priceRanges: readonly RangeFacetBucket[];
  readonly seatingCapacities: readonly FacetBucket[];
  readonly availabilityStatuses: readonly FacetBucket[];
}

/**
 * Search metadata
 */
export interface SearchMetadata {
  readonly query?: string;
  readonly totalResults: number;
  readonly page: number;
  readonly pageSize: number;
  readonly totalPages: number;
  readonly hasNextPage: boolean;
  readonly hasPreviousPage: boolean;
  readonly sortBy: VehicleSortField;
  readonly sortDirection: SortDirection;
  readonly executionTimeMs: number;
}

/**
 * Vehicle list response with pagination
 */
export interface VehicleListResponse {
  readonly vehicles: readonly Vehicle[];
  readonly metadata: SearchMetadata;
  readonly facets?: SearchFacets;
}

/**
 * Vehicle detail response
 */
export interface VehicleDetailResponse {
  readonly vehicle: Vehicle;
  readonly relatedVehicles?: readonly Vehicle[];
}

/**
 * Price range response
 */
export interface PriceRangeResponse {
  readonly min: number;
  readonly max: number;
  readonly average: number;
  readonly count: number;
}

/**
 * Search suggestion
 */
export interface SearchSuggestion {
  readonly text: string;
  readonly type: 'make' | 'model' | 'body_style' | 'feature';
  readonly count: number;
}

/**
 * Search suggestions response
 */
export interface SearchSuggestionsResponse {
  readonly suggestions: readonly SearchSuggestion[];
  readonly query: string;
}

/**
 * Vehicle creation request
 */
export interface VehicleCreateRequest {
  readonly make: string;
  readonly model: string;
  readonly year: number;
  readonly trim?: string;
  readonly bodyStyle: BodyStyle;
  readonly msrp: number;
  readonly price: number;
  readonly description: string;
  readonly imageUrl: string;
  readonly images?: readonly string[];
  readonly specifications: VehicleSpecifications;
  readonly features: VehicleFeatures;
}

/**
 * Vehicle update request
 */
export interface VehicleUpdateRequest {
  readonly make?: string;
  readonly model?: string;
  readonly year?: number;
  readonly trim?: string;
  readonly bodyStyle?: BodyStyle;
  readonly msrp?: number;
  readonly price?: number;
  readonly description?: string;
  readonly imageUrl?: string;
  readonly images?: readonly string[];
  readonly specifications?: Partial<VehicleSpecifications>;
  readonly features?: Partial<VehicleFeatures>;
}

/**
 * API error response
 */
export interface ApiErrorResponse {
  readonly error: string;
  readonly message: string;
  readonly statusCode: number;
  readonly timestamp: string;
  readonly path?: string;
  readonly details?: Record<string, unknown>;
}

/**
 * Type guard to check if response is an error
 */
export function isApiError(response: unknown): response is ApiErrorResponse {
  return (
    typeof response === 'object' &&
    response !== null &&
    'error' in response &&
    'message' in response &&
    'statusCode' in response
  );
}

/**
 * Type guard to check if vehicle has inventory
 */
export function hasInventory(vehicle: Vehicle): vehicle is Vehicle & {
  readonly inventory: VehicleInventory;
} {
  return vehicle.inventory !== undefined;
}

/**
 * Type guard to check if vehicle is available
 */
export function isVehicleAvailable(vehicle: Vehicle): boolean {
  return vehicle.availability === 'available' && !vehicle.isDeleted;
}

/**
 * Helper type for partial vehicle updates
 */
export type PartialVehicle = Partial<Omit<Vehicle, 'id' | 'createdAt' | 'updatedAt'>>;

/**
 * Helper type for vehicle with required inventory
 */
export type VehicleWithInventory = Vehicle & {
  readonly inventory: VehicleInventory;
};

/**
 * Helper type for search result item
 */
export interface VehicleSearchResult extends Vehicle {
  readonly score?: number;
  readonly highlights?: Record<string, readonly string[]>;
}