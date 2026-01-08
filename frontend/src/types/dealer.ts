/**
 * Dealer-specific TypeScript type definitions
 * Provides type-safe interfaces for dealer inventory management functionality
 */

/**
 * Dealer inventory item status
 */
export type DealerInventoryStatus = 'active' | 'inactive' | 'sold' | 'reserved';

/**
 * Bulk upload operation status
 */
export type BulkUploadStatus = 'pending' | 'processing' | 'completed' | 'failed';

/**
 * Audit log action types
 */
export type AuditAction =
  | 'create'
  | 'update'
  | 'delete'
  | 'status_change'
  | 'stock_adjustment'
  | 'bulk_upload';

/**
 * CSV upload validation error
 */
export interface CSVValidationError {
  readonly row: number;
  readonly field: string;
  readonly message: string;
  readonly value?: string;
}

/**
 * Dealer inventory item
 */
export interface DealerInventory {
  readonly id: string;
  readonly dealerId: string;
  readonly vehicleId: string;
  readonly vin: string;
  readonly status: DealerInventoryStatus;
  readonly stockLevel: number;
  readonly reservedQuantity: number;
  readonly availableQuantity: number;
  readonly location: string;
  readonly notes?: string;
  readonly createdAt: string;
  readonly updatedAt: string;
  readonly createdBy: string;
  readonly updatedBy: string;
}

/**
 * Dealer inventory with vehicle details
 */
export interface DealerInventoryWithVehicle extends DealerInventory {
  readonly vehicle: {
    readonly make: string;
    readonly model: string;
    readonly year: number;
    readonly trim?: string;
    readonly price: number;
    readonly imageUrl: string;
  };
}

/**
 * Bulk upload response
 */
export interface BulkUploadResponse {
  readonly uploadId: string;
  readonly status: BulkUploadStatus;
  readonly totalRows: number;
  readonly successCount: number;
  readonly errorCount: number;
  readonly errors: readonly CSVValidationError[];
  readonly processedAt?: string;
  readonly completedAt?: string;
  readonly message: string;
}

/**
 * Bulk upload request
 */
export interface BulkUploadRequest {
  readonly file: File;
  readonly dealerId: string;
  readonly overwriteExisting?: boolean;
}

/**
 * Dealer dashboard statistics
 */
export interface DealerDashboardStats {
  readonly totalVehicles: number;
  readonly activeVehicles: number;
  readonly inactiveVehicles: number;
  readonly soldVehicles: number;
  readonly reservedVehicles: number;
  readonly totalStockLevel: number;
  readonly availableStockLevel: number;
  readonly reservedStockLevel: number;
  readonly lowStockCount: number;
  readonly outOfStockCount: number;
  readonly recentUpdates: number;
  readonly lastUpdatedAt?: string;
}

/**
 * Inventory audit log entry
 */
export interface InventoryAuditLog {
  readonly id: string;
  readonly inventoryId: string;
  readonly dealerId: string;
  readonly action: AuditAction;
  readonly userId: string;
  readonly userName: string;
  readonly changes: Record<string, { readonly before: unknown; readonly after: unknown }>;
  readonly metadata?: Record<string, unknown>;
  readonly timestamp: string;
  readonly ipAddress?: string;
  readonly userAgent?: string;
}

/**
 * Stock adjustment request
 */
export interface StockAdjustmentRequest {
  readonly inventoryId: string;
  readonly adjustment: number;
  readonly reason: string;
  readonly notes?: string;
}

/**
 * Stock adjustment response
 */
export interface StockAdjustmentResponse {
  readonly inventoryId: string;
  readonly previousStockLevel: number;
  readonly newStockLevel: number;
  readonly adjustment: number;
  readonly adjustedAt: string;
  readonly adjustedBy: string;
  readonly auditLogId: string;
}

/**
 * Inventory status change request
 */
export interface InventoryStatusChangeRequest {
  readonly inventoryId: string;
  readonly newStatus: DealerInventoryStatus;
  readonly reason: string;
  readonly notes?: string;
}

/**
 * Inventory status change response
 */
export interface InventoryStatusChangeResponse {
  readonly inventoryId: string;
  readonly previousStatus: DealerInventoryStatus;
  readonly newStatus: DealerInventoryStatus;
  readonly changedAt: string;
  readonly changedBy: string;
  readonly auditLogId: string;
}

/**
 * Dealer inventory filters
 */
export interface DealerInventoryFilters {
  readonly dealerId?: string;
  readonly status?: readonly DealerInventoryStatus[];
  readonly vehicleId?: string;
  readonly vin?: string;
  readonly location?: string;
  readonly lowStock?: boolean;
  readonly outOfStock?: boolean;
  readonly searchQuery?: string;
  readonly make?: string;
  readonly model?: string;
  readonly year?: number;
  readonly minStockLevel?: number;
  readonly maxStockLevel?: number;
}

/**
 * Dealer inventory list request
 */
export interface DealerInventoryListRequest {
  readonly filters?: DealerInventoryFilters;
  readonly sortBy?: 'createdAt' | 'updatedAt' | 'stockLevel' | 'status' | 'vin';
  readonly sortDirection?: 'asc' | 'desc';
  readonly page?: number;
  readonly pageSize?: number;
  readonly includeVehicleDetails?: boolean;
}

/**
 * Dealer inventory list response
 */
export interface DealerInventoryListResponse {
  readonly items: readonly DealerInventoryWithVehicle[];
  readonly total: number;
  readonly page: number;
  readonly pageSize: number;
  readonly totalPages: number;
  readonly hasNextPage: boolean;
  readonly hasPreviousPage: boolean;
}

/**
 * Inventory create request
 */
export interface InventoryCreateRequest {
  readonly dealerId: string;
  readonly vehicleId: string;
  readonly vin: string;
  readonly stockLevel: number;
  readonly location: string;
  readonly status?: DealerInventoryStatus;
  readonly notes?: string;
}

/**
 * Inventory update request
 */
export interface InventoryUpdateRequest {
  readonly stockLevel?: number;
  readonly location?: string;
  readonly status?: DealerInventoryStatus;
  readonly notes?: string;
}

/**
 * Audit log filters
 */
export interface AuditLogFilters {
  readonly dealerId?: string;
  readonly inventoryId?: string;
  readonly userId?: string;
  readonly action?: readonly AuditAction[];
  readonly startDate?: string;
  readonly endDate?: string;
}

/**
 * Audit log list request
 */
export interface AuditLogListRequest {
  readonly filters?: AuditLogFilters;
  readonly sortBy?: 'timestamp';
  readonly sortDirection?: 'asc' | 'desc';
  readonly page?: number;
  readonly pageSize?: number;
}

/**
 * Audit log list response
 */
export interface AuditLogListResponse {
  readonly logs: readonly InventoryAuditLog[];
  readonly total: number;
  readonly page: number;
  readonly pageSize: number;
  readonly totalPages: number;
  readonly hasNextPage: boolean;
  readonly hasPreviousPage: boolean;
}

/**
 * CSV upload template column
 */
export interface CSVTemplateColumn {
  readonly name: string;
  readonly required: boolean;
  readonly type: 'string' | 'number' | 'enum';
  readonly description: string;
  readonly example: string;
  readonly enumValues?: readonly string[];
}

/**
 * CSV upload template
 */
export interface CSVUploadTemplate {
  readonly columns: readonly CSVTemplateColumn[];
  readonly sampleData: readonly Record<string, string>[];
  readonly instructions: string;
}

/**
 * Type guard to check if inventory has low stock
 */
export function isLowStock(
  inventory: DealerInventory,
  threshold: number = 5,
): boolean {
  return inventory.availableQuantity > 0 && inventory.availableQuantity <= threshold;
}

/**
 * Type guard to check if inventory is out of stock
 */
export function isOutOfStock(inventory: DealerInventory): boolean {
  return inventory.availableQuantity === 0;
}

/**
 * Type guard to check if inventory is available for sale
 */
export function isAvailableForSale(inventory: DealerInventory): boolean {
  return inventory.status === 'active' && inventory.availableQuantity > 0;
}

/**
 * Type guard to check if bulk upload is complete
 */
export function isBulkUploadComplete(
  response: BulkUploadResponse,
): response is BulkUploadResponse & { readonly completedAt: string } {
  return response.status === 'completed' && response.completedAt !== undefined;
}

/**
 * Type guard to check if bulk upload has errors
 */
export function hasBulkUploadErrors(response: BulkUploadResponse): boolean {
  return response.errorCount > 0 && response.errors.length > 0;
}

/**
 * Helper type for partial inventory updates
 */
export type PartialInventoryUpdate = Partial<
  Omit<DealerInventory, 'id' | 'dealerId' | 'vehicleId' | 'createdAt' | 'updatedAt'>
>;

/**
 * Helper type for inventory with required vehicle details
 */
export type InventoryWithVehicle = DealerInventory & {
  readonly vehicle: NonNullable<DealerInventoryWithVehicle['vehicle']>;
};