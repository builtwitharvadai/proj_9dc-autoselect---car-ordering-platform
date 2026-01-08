/**
 * Dealer-specific React Query hooks for inventory management
 * Provides type-safe hooks for dealer operations with proper error handling and caching
 */

import { useMutation, useQuery, useQueryClient, type UseQueryOptions } from '@tanstack/react-query';
import type {
  DealerInventory,
  DealerInventoryWithVehicle,
  DealerInventoryListRequest,
  DealerInventoryListResponse,
  DealerDashboardStats,
  BulkUploadRequest,
  BulkUploadResponse,
  StockAdjustmentRequest,
  StockAdjustmentResponse,
  InventoryStatusChangeRequest,
  InventoryStatusChangeResponse,
  InventoryCreateRequest,
  InventoryUpdateRequest,
  InventoryAuditLog,
  AuditLogListRequest,
  AuditLogListResponse,
  CSVUploadTemplate,
} from '../types/dealer';

const API_BASE_URL = import.meta.env['VITE_API_BASE_URL'] ?? 'http://localhost:8000';
const API_VERSION = 'v1';

/**
 * Query keys for dealer operations
 */
export const dealerKeys = {
  all: ['dealer'] as const,
  inventory: () => [...dealerKeys.all, 'inventory'] as const,
  inventoryList: (params: DealerInventoryListRequest) =>
    [...dealerKeys.inventory(), 'list', params] as const,
  inventoryDetail: (id: string) => [...dealerKeys.inventory(), 'detail', id] as const,
  stats: (dealerId: string) => [...dealerKeys.all, 'stats', dealerId] as const,
  auditLogs: (params: AuditLogListRequest) => [...dealerKeys.all, 'audit', params] as const,
  uploadTemplate: () => [...dealerKeys.all, 'template'] as const,
} as const;

/**
 * Custom error class for dealer API errors
 */
export class DealerApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'DealerApiError';
  }
}

/**
 * Type guard for API error responses
 */
function isDealerApiError(error: unknown): error is DealerApiError {
  return error instanceof DealerApiError;
}

/**
 * Generic fetch wrapper with error handling
 */
async function fetchWithAuth<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem('authToken');
  
  const headers = new Headers(options.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  headers.set('Content-Type', 'application/json');

  const response = await fetch(`${API_BASE_URL}/api/${API_VERSION}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new DealerApiError(
      errorData.message ?? `Request failed with status ${response.status}`,
      response.status,
      errorData,
    );
  }

  return response.json() as Promise<T>;
}

/**
 * Hook to fetch dealer inventory list with filters and pagination
 */
export function useDealerInventory(
  request: DealerInventoryListRequest,
  options?: Omit<
    UseQueryOptions<DealerInventoryListResponse, DealerApiError>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery<DealerInventoryListResponse, DealerApiError>({
    queryKey: dealerKeys.inventoryList(request),
    queryFn: async () => {
      const params = new URLSearchParams();
      
      if (request.filters?.dealerId) {
        params.append('dealer_id', request.filters.dealerId);
      }
      if (request.filters?.status) {
        request.filters.status.forEach((status) => params.append('status', status));
      }
      if (request.filters?.vehicleId) {
        params.append('vehicle_id', request.filters.vehicleId);
      }
      if (request.filters?.vin) {
        params.append('vin', request.filters.vin);
      }
      if (request.filters?.location) {
        params.append('location', request.filters.location);
      }
      if (request.filters?.lowStock !== undefined) {
        params.append('low_stock', String(request.filters.lowStock));
      }
      if (request.filters?.outOfStock !== undefined) {
        params.append('out_of_stock', String(request.filters.outOfStock));
      }
      if (request.filters?.searchQuery) {
        params.append('search', request.filters.searchQuery);
      }
      if (request.sortBy) {
        params.append('sort_by', request.sortBy);
      }
      if (request.sortDirection) {
        params.append('sort_direction', request.sortDirection);
      }
      if (request.page !== undefined) {
        params.append('page', String(request.page));
      }
      if (request.pageSize !== undefined) {
        params.append('page_size', String(request.pageSize));
      }
      if (request.includeVehicleDetails !== undefined) {
        params.append('include_vehicle_details', String(request.includeVehicleDetails));
      }

      return fetchWithAuth<DealerInventoryListResponse>(
        `/dealer/inventory?${params.toString()}`,
      );
    },
    staleTime: 30000,
    gcTime: 300000,
    ...options,
  });
}

/**
 * Hook to fetch single inventory item details
 */
export function useDealerInventoryDetail(
  inventoryId: string,
  options?: Omit<
    UseQueryOptions<DealerInventoryWithVehicle, DealerApiError>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery<DealerInventoryWithVehicle, DealerApiError>({
    queryKey: dealerKeys.inventoryDetail(inventoryId),
    queryFn: () =>
      fetchWithAuth<DealerInventoryWithVehicle>(`/dealer/inventory/${inventoryId}`),
    staleTime: 60000,
    gcTime: 300000,
    enabled: Boolean(inventoryId),
    ...options,
  });
}

/**
 * Hook to fetch dealer dashboard statistics
 */
export function useDealerStats(
  dealerId: string,
  options?: Omit<UseQueryOptions<DealerDashboardStats, DealerApiError>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<DealerDashboardStats, DealerApiError>({
    queryKey: dealerKeys.stats(dealerId),
    queryFn: () => fetchWithAuth<DealerDashboardStats>(`/dealer/${dealerId}/stats`),
    staleTime: 60000,
    gcTime: 300000,
    enabled: Boolean(dealerId),
    refetchInterval: 300000,
    ...options,
  });
}

/**
 * Hook to fetch audit logs
 */
export function useDealerAuditLogs(
  request: AuditLogListRequest,
  options?: Omit<UseQueryOptions<AuditLogListResponse, DealerApiError>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<AuditLogListResponse, DealerApiError>({
    queryKey: dealerKeys.auditLogs(request),
    queryFn: async () => {
      const params = new URLSearchParams();
      
      if (request.filters?.dealerId) {
        params.append('dealer_id', request.filters.dealerId);
      }
      if (request.filters?.inventoryId) {
        params.append('inventory_id', request.filters.inventoryId);
      }
      if (request.filters?.userId) {
        params.append('user_id', request.filters.userId);
      }
      if (request.filters?.action) {
        request.filters.action.forEach((action) => params.append('action', action));
      }
      if (request.filters?.startDate) {
        params.append('start_date', request.filters.startDate);
      }
      if (request.filters?.endDate) {
        params.append('end_date', request.filters.endDate);
      }
      if (request.sortBy) {
        params.append('sort_by', request.sortBy);
      }
      if (request.sortDirection) {
        params.append('sort_direction', request.sortDirection);
      }
      if (request.page !== undefined) {
        params.append('page', String(request.page));
      }
      if (request.pageSize !== undefined) {
        params.append('page_size', String(request.pageSize));
      }

      return fetchWithAuth<AuditLogListResponse>(`/dealer/audit-logs?${params.toString()}`);
    },
    staleTime: 60000,
    gcTime: 300000,
    ...options,
  });
}

/**
 * Hook to fetch CSV upload template
 */
export function useUploadTemplate(
  options?: Omit<UseQueryOptions<CSVUploadTemplate, DealerApiError>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<CSVUploadTemplate, DealerApiError>({
    queryKey: dealerKeys.uploadTemplate(),
    queryFn: () => fetchWithAuth<CSVUploadTemplate>('/dealer/upload-template'),
    staleTime: Infinity,
    gcTime: Infinity,
    ...options,
  });
}

/**
 * Hook to create new inventory item
 */
export function useCreateInventory() {
  const queryClient = useQueryClient();

  return useMutation<DealerInventory, DealerApiError, InventoryCreateRequest>({
    mutationFn: (data) =>
      fetchWithAuth<DealerInventory>('/dealer/inventory', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: dealerKeys.inventory() });
      void queryClient.invalidateQueries({ queryKey: dealerKeys.stats(data.dealerId) });
    },
  });
}

/**
 * Hook to update inventory item
 */
export function useUpdateInventory() {
  const queryClient = useQueryClient();

  return useMutation<
    DealerInventory,
    DealerApiError,
    { inventoryId: string; data: InventoryUpdateRequest }
  >({
    mutationFn: ({ inventoryId, data }) =>
      fetchWithAuth<DealerInventory>(`/dealer/inventory/${inventoryId}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: (data, variables) => {
      void queryClient.invalidateQueries({ queryKey: dealerKeys.inventory() });
      void queryClient.invalidateQueries({
        queryKey: dealerKeys.inventoryDetail(variables.inventoryId),
      });
      void queryClient.invalidateQueries({ queryKey: dealerKeys.stats(data.dealerId) });
    },
  });
}

/**
 * Hook to delete inventory item
 */
export function useDeleteInventory() {
  const queryClient = useQueryClient();

  return useMutation<void, DealerApiError, { inventoryId: string; dealerId: string }>({
    mutationFn: ({ inventoryId }) =>
      fetchWithAuth<void>(`/dealer/inventory/${inventoryId}`, {
        method: 'DELETE',
      }),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: dealerKeys.inventory() });
      void queryClient.removeQueries({
        queryKey: dealerKeys.inventoryDetail(variables.inventoryId),
      });
      void queryClient.invalidateQueries({ queryKey: dealerKeys.stats(variables.dealerId) });
    },
  });
}

/**
 * Hook to adjust stock levels
 */
export function useAdjustStock() {
  const queryClient = useQueryClient();

  return useMutation<StockAdjustmentResponse, DealerApiError, StockAdjustmentRequest>({
    mutationFn: (data) =>
      fetchWithAuth<StockAdjustmentResponse>('/dealer/inventory/adjust-stock', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: dealerKeys.inventory() });
      void queryClient.invalidateQueries({
        queryKey: dealerKeys.inventoryDetail(data.inventoryId),
      });
    },
  });
}

/**
 * Hook to change inventory status
 */
export function useChangeInventoryStatus() {
  const queryClient = useQueryClient();

  return useMutation<InventoryStatusChangeResponse, DealerApiError, InventoryStatusChangeRequest>({
    mutationFn: (data) =>
      fetchWithAuth<InventoryStatusChangeResponse>('/dealer/inventory/change-status', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: dealerKeys.inventory() });
      void queryClient.invalidateQueries({
        queryKey: dealerKeys.inventoryDetail(data.inventoryId),
      });
    },
  });
}

/**
 * Hook to upload CSV file for bulk inventory update
 */
export function useBulkUpload() {
  const queryClient = useQueryClient();

  return useMutation<BulkUploadResponse, DealerApiError, BulkUploadRequest>({
    mutationFn: async (data) => {
      const formData = new FormData();
      formData.append('file', data.file);
      formData.append('dealer_id', data.dealerId);
      if (data.overwriteExisting !== undefined) {
        formData.append('overwrite_existing', String(data.overwriteExisting));
      }

      const token = localStorage.getItem('authToken');
      const headers = new Headers();
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }

      const response = await fetch(`${API_BASE_URL}/api/${API_VERSION}/dealer/bulk-upload`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new DealerApiError(
          errorData.message ?? `Upload failed with status ${response.status}`,
          response.status,
          errorData,
        );
      }

      return response.json() as Promise<BulkUploadResponse>;
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: dealerKeys.inventory() });
      void queryClient.invalidateQueries({ queryKey: dealerKeys.stats(variables.dealerId) });
    },
  });
}

/**
 * Hook to check bulk upload status
 */
export function useBulkUploadStatus(
  uploadId: string,
  options?: Omit<UseQueryOptions<BulkUploadResponse, DealerApiError>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<BulkUploadResponse, DealerApiError>({
    queryKey: [...dealerKeys.all, 'upload-status', uploadId] as const,
    queryFn: () => fetchWithAuth<BulkUploadResponse>(`/dealer/bulk-upload/${uploadId}/status`),
    enabled: Boolean(uploadId),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) {
        return false;
      }
      return data.status === 'processing' ? 2000 : false;
    },
    ...options,
  });
}

/**
 * Hook to prefetch inventory list
 */
export function usePrefetchInventory() {
  const queryClient = useQueryClient();

  return (request: DealerInventoryListRequest) => {
    void queryClient.prefetchQuery({
      queryKey: dealerKeys.inventoryList(request),
      queryFn: async () => {
        const params = new URLSearchParams();
        
        if (request.filters?.dealerId) {
          params.append('dealer_id', request.filters.dealerId);
        }
        if (request.page !== undefined) {
          params.append('page', String(request.page));
        }
        if (request.pageSize !== undefined) {
          params.append('page_size', String(request.pageSize));
        }

        return fetchWithAuth<DealerInventoryListResponse>(
          `/dealer/inventory?${params.toString()}`,
        );
      },
      staleTime: 30000,
    });
  };
}

/**
 * Hook to invalidate all dealer queries
 */
export function useInvalidateDealerQueries() {
  const queryClient = useQueryClient();

  return () => {
    void queryClient.invalidateQueries({ queryKey: dealerKeys.all });
  };
}

/**
 * Export error type guard
 */
export { isDealerApiError };

/**
 * Export types for convenience
 */
export type {
  DealerInventory,
  DealerInventoryWithVehicle,
  DealerInventoryListRequest,
  DealerInventoryListResponse,
  DealerDashboardStats,
  BulkUploadRequest,
  BulkUploadResponse,
  StockAdjustmentRequest,
  StockAdjustmentResponse,
  InventoryStatusChangeRequest,
  InventoryStatusChangeResponse,
  InventoryCreateRequest,
  InventoryUpdateRequest,
  InventoryAuditLog,
  AuditLogListRequest,
  AuditLogListResponse,
  CSVUploadTemplate,
};