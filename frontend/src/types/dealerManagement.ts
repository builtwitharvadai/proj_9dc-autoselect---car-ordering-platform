/**
 * Dealer Management Type Definitions
 * Comprehensive interfaces for dealer configuration, pricing rules, and regional settings
 */

/**
 * Dealer role types for access control
 */
export type DealerRole = 'admin' | 'manager' | 'sales' | 'viewer';

/**
 * Configuration rule types
 */
export type ConfigurationRuleType =
  | 'pricing'
  | 'availability'
  | 'compatibility'
  | 'discount'
  | 'bundle';

/**
 * Rule application scope
 */
export type RuleScope = 'global' | 'regional' | 'dealer-specific';

/**
 * Rule status
 */
export type RuleStatus = 'active' | 'inactive' | 'scheduled' | 'expired';

/**
 * Bulk operation status
 */
export type BulkOperationStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'partial';

/**
 * Configuration change type
 */
export type ConfigurationChangeType =
  | 'create'
  | 'update'
  | 'delete'
  | 'activate'
  | 'deactivate'
  | 'bulk_update';

/**
 * Pricing rule configuration
 */
export interface PricingRule {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly ruleType: ConfigurationRuleType;
  readonly scope: RuleScope;
  readonly status: RuleStatus;
  readonly priority: number;
  readonly effectiveFrom: string;
  readonly effectiveTo?: string;
  readonly conditions: readonly RuleCondition[];
  readonly actions: readonly RuleAction[];
  readonly metadata?: Record<string, string | number | boolean>;
  readonly createdAt: string;
  readonly updatedAt: string;
  readonly createdBy: string;
  readonly updatedBy?: string;
}

/**
 * Rule condition definition
 */
export interface RuleCondition {
  readonly field: string;
  readonly operator: ConditionOperator;
  readonly value: string | number | boolean | readonly (string | number)[];
  readonly logicalOperator?: 'AND' | 'OR';
}

/**
 * Condition operators
 */
export type ConditionOperator =
  | 'equals'
  | 'not_equals'
  | 'greater_than'
  | 'less_than'
  | 'greater_than_or_equal'
  | 'less_than_or_equal'
  | 'in'
  | 'not_in'
  | 'contains'
  | 'starts_with'
  | 'ends_with'
  | 'between';

/**
 * Rule action definition
 */
export interface RuleAction {
  readonly type: RuleActionType;
  readonly target: string;
  readonly value: string | number | boolean;
  readonly parameters?: Record<string, string | number | boolean>;
}

/**
 * Rule action types
 */
export type RuleActionType =
  | 'set_price'
  | 'apply_discount'
  | 'set_availability'
  | 'add_option'
  | 'remove_option'
  | 'set_attribute'
  | 'send_notification';

/**
 * Regional settings configuration
 */
export interface RegionSettings {
  readonly id: string;
  readonly regionCode: string;
  readonly regionName: string;
  readonly countryCode: string;
  readonly currency: string;
  readonly taxRate: number;
  readonly availableOptions: readonly string[];
  readonly availablePackages: readonly string[];
  readonly pricingAdjustments: readonly PricingAdjustment[];
  readonly shippingZones: readonly string[];
  readonly customAttributes?: Record<string, string | number | boolean>;
  readonly isActive: boolean;
  readonly effectiveFrom: string;
  readonly effectiveTo?: string;
  readonly createdAt: string;
  readonly updatedAt: string;
}

/**
 * Pricing adjustment for regional settings
 */
export interface PricingAdjustment {
  readonly itemType: 'vehicle' | 'option' | 'package';
  readonly itemId: string;
  readonly adjustmentType: 'percentage' | 'fixed_amount';
  readonly adjustmentValue: number;
  readonly reason?: string;
}

/**
 * Dealer configuration
 */
export interface DealerConfiguration {
  readonly id: string;
  readonly dealerId: string;
  readonly dealerName: string;
  readonly regionId: string;
  readonly availableVehicles: readonly string[];
  readonly availableOptions: readonly string[];
  readonly availablePackages: readonly string[];
  readonly pricingRules: readonly string[];
  readonly customPricing: readonly CustomPricing[];
  readonly inventorySettings: InventorySettings;
  readonly displaySettings: DisplaySettings;
  readonly notificationSettings: NotificationSettings;
  readonly permissions: DealerPermissions;
  readonly isActive: boolean;
  readonly metadata?: Record<string, string | number | boolean>;
  readonly createdAt: string;
  readonly updatedAt: string;
  readonly lastSyncedAt?: string;
}

/**
 * Custom pricing override
 */
export interface CustomPricing {
  readonly itemType: 'vehicle' | 'option' | 'package';
  readonly itemId: string;
  readonly basePrice: number;
  readonly dealerPrice: number;
  readonly msrp?: number;
  readonly effectiveFrom: string;
  readonly effectiveTo?: string;
  readonly notes?: string;
}

/**
 * Inventory settings
 */
export interface InventorySettings {
  readonly autoReserveInventory: boolean;
  readonly reservationDurationMinutes: number;
  readonly lowStockThreshold: number;
  readonly allowBackorders: boolean;
  readonly maxBackorderQuantity: number;
  readonly notifyOnLowStock: boolean;
  readonly notifyOnOutOfStock: boolean;
}

/**
 * Display settings
 */
export interface DisplaySettings {
  readonly showMSRP: boolean;
  readonly showDealerPrice: boolean;
  readonly showSavings: boolean;
  readonly showInventoryCount: boolean;
  readonly highlightPopularOptions: boolean;
  readonly defaultSortOrder: 'price' | 'popularity' | 'newest' | 'name';
  readonly itemsPerPage: number;
  readonly enableComparison: boolean;
  readonly maxComparisonItems: number;
}

/**
 * Notification settings
 */
export interface NotificationSettings {
  readonly emailNotifications: boolean;
  readonly smsNotifications: boolean;
  readonly notifyOnNewOrder: boolean;
  readonly notifyOnInventoryChange: boolean;
  readonly notifyOnPriceChange: boolean;
  readonly notifyOnConfigurationUpdate: boolean;
  readonly notificationRecipients: readonly string[];
}

/**
 * Dealer permissions
 */
export interface DealerPermissions {
  readonly canManageInventory: boolean;
  readonly canManagePricing: boolean;
  readonly canManageOptions: boolean;
  readonly canManagePackages: boolean;
  readonly canViewReports: boolean;
  readonly canExportData: boolean;
  readonly canImportData: boolean;
  readonly canManageUsers: boolean;
  readonly customPermissions?: readonly string[];
}

/**
 * Bulk update request
 */
export interface BulkUpdateRequest {
  readonly operationType: 'create' | 'update' | 'delete' | 'activate' | 'deactivate';
  readonly targetType: 'pricing_rule' | 'region_settings' | 'dealer_configuration';
  readonly items: readonly BulkUpdateItem[];
  readonly validateOnly?: boolean;
  readonly continueOnError?: boolean;
  readonly metadata?: Record<string, string | number | boolean>;
}

/**
 * Bulk update item
 */
export interface BulkUpdateItem {
  readonly id?: string;
  readonly data: Record<string, unknown>;
  readonly action?: 'skip' | 'merge' | 'replace';
}

/**
 * Bulk update response
 */
export interface BulkUpdateResponse {
  readonly operationId: string;
  readonly status: BulkOperationStatus;
  readonly totalItems: number;
  readonly successCount: number;
  readonly failureCount: number;
  readonly skippedCount: number;
  readonly results: readonly BulkUpdateResult[];
  readonly errors: readonly BulkUpdateError[];
  readonly startedAt: string;
  readonly completedAt?: string;
  readonly processingTimeMs?: number;
}

/**
 * Bulk update result
 */
export interface BulkUpdateResult {
  readonly itemIndex: number;
  readonly itemId?: string;
  readonly status: 'success' | 'failed' | 'skipped';
  readonly message?: string;
  readonly data?: Record<string, unknown>;
}

/**
 * Bulk update error
 */
export interface BulkUpdateError {
  readonly itemIndex: number;
  readonly itemId?: string;
  readonly errorCode: string;
  readonly errorMessage: string;
  readonly field?: string;
  readonly details?: Record<string, unknown>;
}

/**
 * Configuration rule request
 */
export interface ConfigurationRuleRequest {
  readonly name: string;
  readonly description: string;
  readonly ruleType: ConfigurationRuleType;
  readonly scope: RuleScope;
  readonly priority: number;
  readonly effectiveFrom: string;
  readonly effectiveTo?: string;
  readonly conditions: readonly RuleCondition[];
  readonly actions: readonly RuleAction[];
  readonly metadata?: Record<string, string | number | boolean>;
}

/**
 * Region settings request
 */
export interface RegionSettingsRequest {
  readonly regionCode: string;
  readonly regionName: string;
  readonly countryCode: string;
  readonly currency: string;
  readonly taxRate: number;
  readonly availableOptions: readonly string[];
  readonly availablePackages: readonly string[];
  readonly pricingAdjustments?: readonly PricingAdjustment[];
  readonly shippingZones?: readonly string[];
  readonly customAttributes?: Record<string, string | number | boolean>;
  readonly effectiveFrom: string;
  readonly effectiveTo?: string;
}

/**
 * Dealer configuration request
 */
export interface DealerConfigurationRequest {
  readonly dealerId: string;
  readonly regionId: string;
  readonly availableVehicles: readonly string[];
  readonly availableOptions: readonly string[];
  readonly availablePackages: readonly string[];
  readonly pricingRules?: readonly string[];
  readonly customPricing?: readonly CustomPricing[];
  readonly inventorySettings?: Partial<InventorySettings>;
  readonly displaySettings?: Partial<DisplaySettings>;
  readonly notificationSettings?: Partial<NotificationSettings>;
  readonly permissions?: Partial<DealerPermissions>;
  readonly metadata?: Record<string, string | number | boolean>;
}

/**
 * Configuration change log
 */
export interface ConfigurationChangeLog {
  readonly id: string;
  readonly changeType: ConfigurationChangeType;
  readonly targetType: 'pricing_rule' | 'region_settings' | 'dealer_configuration';
  readonly targetId: string;
  readonly changes: readonly FieldChange[];
  readonly reason?: string;
  readonly performedBy: string;
  readonly performedAt: string;
  readonly metadata?: Record<string, string | number | boolean>;
}

/**
 * Field change detail
 */
export interface FieldChange {
  readonly field: string;
  readonly oldValue: unknown;
  readonly newValue: unknown;
  readonly changeType: 'added' | 'modified' | 'removed';
}

/**
 * Configuration validation result
 */
export interface ConfigurationValidationResult {
  readonly isValid: boolean;
  readonly errors: readonly ValidationError[];
  readonly warnings: readonly ValidationWarning[];
  readonly suggestions?: readonly string[];
}

/**
 * Validation error
 */
export interface ValidationError {
  readonly field: string;
  readonly errorCode: string;
  readonly errorMessage: string;
  readonly severity: 'error' | 'critical';
  readonly details?: Record<string, unknown>;
}

/**
 * Validation warning
 */
export interface ValidationWarning {
  readonly field: string;
  readonly warningCode: string;
  readonly warningMessage: string;
  readonly suggestion?: string;
}

/**
 * Configuration export request
 */
export interface ConfigurationExportRequest {
  readonly exportType: 'pricing_rules' | 'region_settings' | 'dealer_configurations' | 'all';
  readonly format: 'json' | 'csv' | 'xlsx';
  readonly filters?: ConfigurationFilters;
  readonly includeInactive?: boolean;
  readonly includeMetadata?: boolean;
}

/**
 * Configuration filters
 */
export interface ConfigurationFilters {
  readonly dealerIds?: readonly string[];
  readonly regionIds?: readonly string[];
  readonly status?: readonly RuleStatus[];
  readonly effectiveFrom?: string;
  readonly effectiveTo?: string;
  readonly searchQuery?: string;
}

/**
 * Configuration import request
 */
export interface ConfigurationImportRequest {
  readonly importType: 'pricing_rules' | 'region_settings' | 'dealer_configurations';
  readonly format: 'json' | 'csv' | 'xlsx';
  readonly data: string | ArrayBuffer;
  readonly validateOnly?: boolean;
  readonly mergeStrategy?: 'replace' | 'merge' | 'skip_existing';
  readonly continueOnError?: boolean;
}

/**
 * Type guards
 */

export function isPricingRule(config: unknown): config is PricingRule {
  return (
    typeof config === 'object' &&
    config !== null &&
    'ruleType' in config &&
    'conditions' in config &&
    'actions' in config
  );
}

export function isRegionSettings(config: unknown): config is RegionSettings {
  return (
    typeof config === 'object' &&
    config !== null &&
    'regionCode' in config &&
    'currency' in config &&
    'taxRate' in config
  );
}

export function isDealerConfiguration(config: unknown): config is DealerConfiguration {
  return (
    typeof config === 'object' &&
    config !== null &&
    'dealerId' in config &&
    'regionId' in config &&
    'permissions' in config
  );
}

export function isActiveRule(rule: PricingRule): boolean {
  const now = new Date();
  const effectiveFrom = new Date(rule.effectiveFrom);
  const effectiveTo = rule.effectiveTo ? new Date(rule.effectiveTo) : null;

  return (
    rule.status === 'active' &&
    now >= effectiveFrom &&
    (!effectiveTo || now <= effectiveTo)
  );
}

export function isActiveRegion(region: RegionSettings): boolean {
  const now = new Date();
  const effectiveFrom = new Date(region.effectiveFrom);
  const effectiveTo = region.effectiveTo ? new Date(region.effectiveTo) : null;

  return (
    region.isActive &&
    now >= effectiveFrom &&
    (!effectiveTo || now <= effectiveTo)
  );
}

/**
 * Helper types
 */

export type PartialDealerConfiguration = Partial<
  Omit<DealerConfiguration, 'id' | 'dealerId' | 'createdAt' | 'updatedAt'>
>;

export type PartialPricingRule = Partial<
  Omit<PricingRule, 'id' | 'createdAt' | 'updatedAt' | 'createdBy'>
>;

export type PartialRegionSettings = Partial<
  Omit<RegionSettings, 'id' | 'createdAt' | 'updatedAt'>
>;

/**
 * Constants
 */

export const DEALER_ROLE_NAMES: Record<DealerRole, string> = {
  admin: 'Administrator',
  manager: 'Manager',
  sales: 'Sales Representative',
  viewer: 'Viewer',
} as const;

export const RULE_STATUS_NAMES: Record<RuleStatus, string> = {
  active: 'Active',
  inactive: 'Inactive',
  scheduled: 'Scheduled',
  expired: 'Expired',
} as const;

export const BULK_OPERATION_STATUS_NAMES: Record<BulkOperationStatus, string> = {
  pending: 'Pending',
  processing: 'Processing',
  completed: 'Completed',
  failed: 'Failed',
  partial: 'Partially Completed',
} as const;

export const DEFAULT_INVENTORY_SETTINGS: InventorySettings = {
  autoReserveInventory: true,
  reservationDurationMinutes: 15,
  lowStockThreshold: 5,
  allowBackorders: false,
  maxBackorderQuantity: 0,
  notifyOnLowStock: true,
  notifyOnOutOfStock: true,
} as const;

export const DEFAULT_DISPLAY_SETTINGS: DisplaySettings = {
  showMSRP: true,
  showDealerPrice: true,
  showSavings: true,
  showInventoryCount: true,
  highlightPopularOptions: true,
  defaultSortOrder: 'popularity',
  itemsPerPage: 20,
  enableComparison: true,
  maxComparisonItems: 3,
} as const;

export const DEFAULT_NOTIFICATION_SETTINGS: NotificationSettings = {
  emailNotifications: true,
  smsNotifications: false,
  notifyOnNewOrder: true,
  notifyOnInventoryChange: true,
  notifyOnPriceChange: true,
  notifyOnConfigurationUpdate: false,
  notificationRecipients: [],
} as const;