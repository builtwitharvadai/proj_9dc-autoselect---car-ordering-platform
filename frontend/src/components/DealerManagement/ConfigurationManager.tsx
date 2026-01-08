/**
 * Configuration Manager Component
 * Comprehensive interface for managing vehicle options, packages, pricing rules, and regional settings
 * with validation, bulk operations, and real-time updates
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
  PlusCircle,
  Edit2,
  Trash2,
  Save,
  X,
  AlertCircle,
  CheckCircle,
  Upload,
  Download,
  Filter,
  Search,
  RefreshCw,
  Settings,
  Globe,
  DollarSign,
  Package,
  Calendar,
  Eye,
  EyeOff,
} from 'lucide-react';
import type {
  PricingRule,
  RegionSettings,
  DealerConfiguration,
  ConfigurationRuleType,
  RuleScope,
  RuleStatus,
  BulkUpdateRequest,
  BulkUpdateResponse,
  ConfigurationValidationResult,
  ConfigurationExportRequest,
  ConfigurationImportRequest,
  RuleCondition,
  RuleAction,
  PricingAdjustment,
  CustomPricing,
  InventorySettings,
  DisplaySettings,
  NotificationSettings,
  DealerPermissions,
} from '../../types/dealerManagement';

/**
 * Component props interface
 */
export interface ConfigurationManagerProps {
  readonly dealerId: string;
  readonly onConfigurationChange?: (type: 'pricing' | 'region' | 'dealer', id: string) => void;
  readonly onError?: (error: Error) => void;
  readonly className?: string;
  readonly enableBulkOperations?: boolean;
  readonly enableExportImport?: boolean;
  readonly readOnly?: boolean;
}

/**
 * Configuration type for tab management
 */
type ConfigurationType = 'pricing' | 'regions' | 'dealer' | 'options' | 'packages';

/**
 * Edit mode state
 */
interface EditState {
  readonly type: ConfigurationType;
  readonly id: string | null;
  readonly isNew: boolean;
}

/**
 * Filter state for configuration lists
 */
interface FilterState {
  readonly searchQuery: string;
  readonly status: readonly RuleStatus[];
  readonly scope: readonly RuleScope[];
  readonly ruleType: readonly ConfigurationRuleType[];
  readonly effectiveDateRange: {
    readonly from?: string;
    readonly to?: string;
  };
}

/**
 * Validation state
 */
interface ValidationState {
  readonly isValidating: boolean;
  readonly result: ConfigurationValidationResult | null;
  readonly errors: readonly string[];
}

/**
 * Configuration Manager Component
 */
export default function ConfigurationManager({
  dealerId,
  onConfigurationChange,
  onError,
  className = '',
  enableBulkOperations = true,
  enableExportImport = true,
  readOnly = false,
}: ConfigurationManagerProps): JSX.Element {
  // State management
  const [activeTab, setActiveTab] = useState<ConfigurationType>('pricing');
  const [editState, setEditState] = useState<EditState | null>(null);
  const [filters, setFilters] = useState<FilterState>({
    searchQuery: '',
    status: [],
    scope: [],
    ruleType: [],
    effectiveDateRange: {},
  });
  const [validation, setValidation] = useState<ValidationState>({
    isValidating: false,
    result: null,
    errors: [],
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [bulkOperation, setBulkOperation] = useState<'activate' | 'deactivate' | 'delete' | null>(
    null,
  );

  // Mock data - replace with actual API calls
  const [pricingRules, setPricingRules] = useState<readonly PricingRule[]>([]);
  const [regionSettings, setRegionSettings] = useState<readonly RegionSettings[]>([]);
  const [dealerConfig, setDealerConfig] = useState<DealerConfiguration | null>(null);

  /**
   * Load configurations on mount and when dealer changes
   */
  useEffect(() => {
    void loadConfigurations();
  }, [dealerId]);

  /**
   * Load all configurations
   */
  const loadConfigurations = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    try {
      // TODO: Replace with actual API calls
      // const [rules, regions, config] = await Promise.all([
      //   fetchPricingRules(dealerId),
      //   fetchRegionSettings(dealerId),
      //   fetchDealerConfiguration(dealerId),
      // ]);
      // setPricingRules(rules);
      // setRegionSettings(regions);
      // setDealerConfig(config);
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to load configurations');
      onError?.(err);
    } finally {
      setIsLoading(false);
    }
  }, [dealerId, onError]);

  /**
   * Handle tab change
   */
  const handleTabChange = useCallback((tab: ConfigurationType): void => {
    setActiveTab(tab);
    setEditState(null);
    setSelectedItems(new Set());
  }, []);

  /**
   * Handle create new configuration
   */
  const handleCreate = useCallback((): void => {
    setEditState({
      type: activeTab,
      id: null,
      isNew: true,
    });
  }, [activeTab]);

  /**
   * Handle edit configuration
   */
  const handleEdit = useCallback((id: string): void => {
    setEditState({
      type: activeTab,
      id,
      isNew: false,
    });
  }, [activeTab]);

  /**
   * Handle delete configuration
   */
  const handleDelete = useCallback(
    async (id: string): Promise<void> => {
      if (!confirm('Are you sure you want to delete this configuration?')) {
        return;
      }

      setIsLoading(true);
      try {
        // TODO: Replace with actual API call
        // await deleteConfiguration(activeTab, id);
        await loadConfigurations();
        onConfigurationChange?.(activeTab as 'pricing' | 'region' | 'dealer', id);
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Failed to delete configuration');
        onError?.(err);
      } finally {
        setIsLoading(false);
      }
    },
    [activeTab, loadConfigurations, onConfigurationChange, onError],
  );

  /**
   * Handle save configuration
   */
  const handleSave = useCallback(
    async (data: unknown): Promise<void> => {
      if (!editState) return;

      setIsSaving(true);
      setValidation({ isValidating: true, result: null, errors: [] });

      try {
        // Validate configuration
        // TODO: Replace with actual API call
        // const validationResult = await validateConfiguration(editState.type, data);
        // if (!validationResult.isValid) {
        //   setValidation({
        //     isValidating: false,
        //     result: validationResult,
        //     errors: validationResult.errors.map(e => e.errorMessage),
        //   });
        //   return;
        // }

        // Save configuration
        // TODO: Replace with actual API call
        // if (editState.isNew) {
        //   await createConfiguration(editState.type, data);
        // } else {
        //   await updateConfiguration(editState.type, editState.id!, data);
        // }

        await loadConfigurations();
        setEditState(null);
        setValidation({ isValidating: false, result: null, errors: [] });
        onConfigurationChange?.(
          editState.type as 'pricing' | 'region' | 'dealer',
          editState.id ?? 'new',
        );
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Failed to save configuration');
        setValidation({
          isValidating: false,
          result: null,
          errors: [err.message],
        });
        onError?.(err);
      } finally {
        setIsSaving(false);
      }
    },
    [editState, loadConfigurations, onConfigurationChange, onError],
  );

  /**
   * Handle cancel edit
   */
  const handleCancel = useCallback((): void => {
    setEditState(null);
    setValidation({ isValidating: false, result: null, errors: [] });
  }, []);

  /**
   * Handle bulk operation
   */
  const handleBulkOperation = useCallback(
    async (operation: 'activate' | 'deactivate' | 'delete'): Promise<void> => {
      if (selectedItems.size === 0) return;

      if (
        operation === 'delete' &&
        !confirm(`Are you sure you want to delete ${selectedItems.size} items?`)
      ) {
        return;
      }

      setBulkOperation(operation);
      setIsLoading(true);

      try {
        const request: BulkUpdateRequest = {
          operationType: operation,
          targetType:
            activeTab === 'pricing'
              ? 'pricing_rule'
              : activeTab === 'regions'
                ? 'region_settings'
                : 'dealer_configuration',
          items: Array.from(selectedItems).map((id) => ({
            id,
            data: {},
          })),
        };

        // TODO: Replace with actual API call
        // const response: BulkUpdateResponse = await performBulkOperation(request);
        // if (response.failureCount > 0) {
        //   console.warn(`Bulk operation completed with ${response.failureCount} failures`);
        // }

        await loadConfigurations();
        setSelectedItems(new Set());
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Bulk operation failed');
        onError?.(err);
      } finally {
        setIsLoading(false);
        setBulkOperation(null);
      }
    },
    [selectedItems, activeTab, loadConfigurations, onError],
  );

  /**
   * Handle export configurations
   */
  const handleExport = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    try {
      const request: ConfigurationExportRequest = {
        exportType: activeTab === 'pricing' ? 'pricing_rules' : 'region_settings',
        format: 'json',
        filters: {
          searchQuery: filters.searchQuery || undefined,
          status: filters.status.length > 0 ? filters.status : undefined,
        },
      };

      // TODO: Replace with actual API call
      // const blob = await exportConfigurations(request);
      // const url = URL.createObjectURL(blob);
      // const a = document.createElement('a');
      // a.href = url;
      // a.download = `${activeTab}-export-${new Date().toISOString()}.json`;
      // a.click();
      // URL.revokeObjectURL(url);
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Export failed');
      onError?.(err);
    } finally {
      setIsLoading(false);
    }
  }, [activeTab, filters, onError]);

  /**
   * Handle import configurations
   */
  const handleImport = useCallback(
    async (file: File): Promise<void> => {
      setIsLoading(true);
      try {
        const data = await file.text();
        const request: ConfigurationImportRequest = {
          importType: activeTab === 'pricing' ? 'pricing_rules' : 'region_settings',
          format: 'json',
          data,
          validateOnly: false,
          mergeStrategy: 'merge',
        };

        // TODO: Replace with actual API call
        // await importConfigurations(request);
        await loadConfigurations();
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Import failed');
        onError?.(err);
      } finally {
        setIsLoading(false);
      }
    },
    [activeTab, loadConfigurations, onError],
  );

  /**
   * Handle filter change
   */
  const handleFilterChange = useCallback(
    (key: keyof FilterState, value: FilterState[keyof FilterState]): void => {
      setFilters((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  /**
   * Handle item selection
   */
  const handleItemSelect = useCallback((id: string, selected: boolean): void => {
    setSelectedItems((prev) => {
      const next = new Set(prev);
      if (selected) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  }, []);

  /**
   * Handle select all
   */
  const handleSelectAll = useCallback((selected: boolean): void => {
    if (selected) {
      const allIds =
        activeTab === 'pricing'
          ? pricingRules.map((r) => r.id)
          : activeTab === 'regions'
            ? regionSettings.map((r) => r.id)
            : [];
      setSelectedItems(new Set(allIds));
    } else {
      setSelectedItems(new Set());
    }
  }, [activeTab, pricingRules, regionSettings]);

  /**
   * Filter configurations based on current filters
   */
  const filteredConfigurations = useMemo(() => {
    const items =
      activeTab === 'pricing'
        ? pricingRules
        : activeTab === 'regions'
          ? regionSettings
          : [];

    return items.filter((item) => {
      // Search query filter
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase();
        const name = 'name' in item ? item.name.toLowerCase() : '';
        const description = 'description' in item ? item.description?.toLowerCase() ?? '' : '';
        if (!name.includes(query) && !description.includes(query)) {
          return false;
        }
      }

      // Status filter
      if (filters.status.length > 0 && 'status' in item) {
        if (!filters.status.includes(item.status)) {
          return false;
        }
      }

      // Scope filter
      if (filters.scope.length > 0 && 'scope' in item) {
        if (!filters.scope.includes(item.scope)) {
          return false;
        }
      }

      // Rule type filter
      if (filters.ruleType.length > 0 && 'ruleType' in item) {
        if (!filters.ruleType.includes(item.ruleType)) {
          return false;
        }
      }

      // Date range filter
      if (filters.effectiveDateRange.from || filters.effectiveDateRange.to) {
        const effectiveFrom = 'effectiveFrom' in item ? new Date(item.effectiveFrom) : null;
        if (effectiveFrom) {
          if (
            filters.effectiveDateRange.from &&
            effectiveFrom < new Date(filters.effectiveDateRange.from)
          ) {
            return false;
          }
          if (
            filters.effectiveDateRange.to &&
            effectiveFrom > new Date(filters.effectiveDateRange.to)
          ) {
            return false;
          }
        }
      }

      return true;
    });
  }, [activeTab, pricingRules, regionSettings, filters]);

  /**
   * Render tab navigation
   */
  const renderTabs = (): JSX.Element => (
    <div className="border-b border-gray-200">
      <nav className="-mb-px flex space-x-8" aria-label="Configuration tabs">
        {[
          { id: 'pricing' as const, label: 'Pricing Rules', icon: DollarSign },
          { id: 'regions' as const, label: 'Regional Settings', icon: Globe },
          { id: 'dealer' as const, label: 'Dealer Config', icon: Settings },
          { id: 'options' as const, label: 'Options', icon: Package },
          { id: 'packages' as const, label: 'Packages', icon: Package },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => handleTabChange(id)}
            className={`
              flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm
              ${
                activeTab === id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
            aria-current={activeTab === id ? 'page' : undefined}
          >
            <Icon className="h-5 w-5" />
            {label}
          </button>
        ))}
      </nav>
    </div>
  );

  /**
   * Render toolbar
   */
  const renderToolbar = (): JSX.Element => (
    <div className="flex items-center justify-between gap-4 p-4 bg-gray-50 border-b border-gray-200">
      <div className="flex items-center gap-2">
        {!readOnly && (
          <button
            onClick={handleCreate}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <PlusCircle className="h-4 w-4" />
            Create New
          </button>
        )}

        {enableBulkOperations && selectedItems.size > 0 && !readOnly && (
          <>
            <button
              onClick={() => void handleBulkOperation('activate')}
              disabled={isLoading || bulkOperation !== null}
              className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <CheckCircle className="h-4 w-4" />
              Activate ({selectedItems.size})
            </button>
            <button
              onClick={() => void handleBulkOperation('deactivate')}
              disabled={isLoading || bulkOperation !== null}
              className="inline-flex items-center gap-2 px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <EyeOff className="h-4 w-4" />
              Deactivate ({selectedItems.size})
            </button>
            <button
              onClick={() => void handleBulkOperation('delete')}
              disabled={isLoading || bulkOperation !== null}
              className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Trash2 className="h-4 w-4" />
              Delete ({selectedItems.size})
            </button>
          </>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`inline-flex items-center gap-2 px-4 py-2 border rounded-md ${
            showFilters
              ? 'bg-blue-50 border-blue-300 text-blue-700'
              : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
          }`}
        >
          <Filter className="h-4 w-4" />
          Filters
        </button>

        {enableExportImport && (
          <>
            <button
              onClick={() => void handleExport()}
              disabled={isLoading}
              className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download className="h-4 w-4" />
              Export
            </button>
            <label className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 cursor-pointer">
              <Upload className="h-4 w-4" />
              Import
              <input
                type="file"
                accept=".json,.csv"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void handleImport(file);
                }}
                className="hidden"
                disabled={isLoading || readOnly}
              />
            </label>
          </>
        )}

        <button
          onClick={() => void loadConfigurations()}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>
    </div>
  );

  /**
   * Render filters panel
   */
  const renderFilters = (): JSX.Element | null => {
    if (!showFilters) return null;

    return (
      <div className="p-4 bg-gray-50 border-b border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={filters.searchQuery}
                onChange={(e) => handleFilterChange('searchQuery', e.target.value)}
                placeholder="Search configurations..."
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {activeTab === 'pricing' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                <select
                  multiple
                  value={filters.status as string[]}
                  onChange={(e) =>
                    handleFilterChange(
                      'status',
                      Array.from(e.target.selectedOptions, (option) => option.value) as RuleStatus[],
                    )
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                  <option value="scheduled">Scheduled</option>
                  <option value="expired">Expired</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Scope</label>
                <select
                  multiple
                  value={filters.scope as string[]}
                  onChange={(e) =>
                    handleFilterChange(
                      'scope',
                      Array.from(e.target.selectedOptions, (option) => option.value) as RuleScope[],
                    )
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="global">Global</option>
                  <option value="regional">Regional</option>
                  <option value="dealer-specific">Dealer Specific</option>
                </select>
              </div>
            </>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Effective Date Range
            </label>
            <div className="flex gap-2">
              <input
                type="date"
                value={filters.effectiveDateRange.from ?? ''}
                onChange={(e) =>
                  handleFilterChange('effectiveDateRange', {
                    ...filters.effectiveDateRange,
                    from: e.target.value,
                  })
                }
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <input
                type="date"
                value={filters.effectiveDateRange.to ?? ''}
                onChange={(e) =>
                  handleFilterChange('effectiveDateRange', {
                    ...filters.effectiveDateRange,
                    to: e.target.value,
                  })
                }
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <button
            onClick={() =>
              setFilters({
                searchQuery: '',
                status: [],
                scope: [],
                ruleType: [],
                effectiveDateRange: {},
              })
            }
            className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900"
          >
            Clear Filters
          </button>
        </div>
      </div>
    );
  };

  /**
   * Render configuration list
   */
  const renderConfigurationList = (): JSX.Element => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      );
    }

    if (filteredConfigurations.length === 0) {
      return (
        <div className="text-center py-12">
          <p className="text-gray-500">No configurations found</p>
          {!readOnly && (
            <button
              onClick={handleCreate}
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              <PlusCircle className="h-4 w-4" />
              Create First Configuration
            </button>
          )}
        </div>
      );
    }

    return (
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {enableBulkOperations && !readOnly && (
                <th className="px-6 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={selectedItems.size === filteredConfigurations.length}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                </th>
              )}
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Effective Date
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredConfigurations.map((config) => {
              const id = config.id;
              const name = 'name' in config ? config.name : 'regionName' in config ? config.regionName : '';
              const status = 'status' in config ? config.status : 'isActive' in config && config.isActive ? 'active' : 'inactive';
              const effectiveFrom = 'effectiveFrom' in config ? config.effectiveFrom : '';

              return (
                <tr key={id} className="hover:bg-gray-50">
                  {enableBulkOperations && !readOnly && (
                    <td className="px-6 py-4">
                      <input
                        type="checkbox"
                        checked={selectedItems.has(id)}
                        onChange={(e) => handleItemSelect(id, e.target.checked)}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                    </td>
                  )}
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{name}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        status === 'active'
                          ? 'bg-green-100 text-green-800'
                          : status === 'scheduled'
                            ? 'bg-blue-100 text-blue-800'
                            : status === 'expired'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {effectiveFrom ? new Date(effectiveFrom).toLocaleDateString() : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleEdit(id)}
                        className="text-blue-600 hover:text-blue-900"
                        title="Edit"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      {!readOnly && (
                        <button
                          onClick={() => void handleDelete(id)}
                          className="text-red-600 hover:text-red-900"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  /**
   * Render validation errors
   */
  const renderValidationErrors = (): JSX.Element | null => {
    if (validation.errors.length === 0) return null;

    return (
      <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
        <div className="flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-medium text-red-800">Validation Errors</h3>
            <ul className="mt-2 text-sm text-red-700 list-disc list-inside">
              {validation.errors.map((error, index) => (
                <li key={index}>{error}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className={`bg-white rounded-lg shadow ${className}`}>
      {renderTabs()}
      {renderToolbar()}
      {renderFilters()}
      {renderValidationErrors()}
      <div className="p-6">{renderConfigurationList()}</div>
    </div>
  );
}