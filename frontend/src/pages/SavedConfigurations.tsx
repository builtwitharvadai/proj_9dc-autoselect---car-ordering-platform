/**
 * Saved Configurations Page
 * 
 * Displays and manages user's saved vehicle configurations with authentication check.
 * Provides list view, comparison selection, and management actions for saved configurations.
 * 
 * @module pages/SavedConfigurations
 */

import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import SavedConfigurationsList from '../components/SavedConfigurations/SavedConfigurationsList';
import ConfigurationComparison from '../components/SavedConfigurations/ConfigurationComparison';
import {
  useSavedConfigurations,
  useCompareConfigurations,
  type SavedConfigurationWithVehicle,
} from '../hooks/useSavedConfigurations';

/**
 * Page props
 */
export interface SavedConfigurationsProps {
  readonly className?: string;
}

/**
 * View mode for the page
 */
type ViewMode = 'list' | 'comparison';

/**
 * Authentication state
 */
interface AuthState {
  readonly isAuthenticated: boolean;
  readonly isLoading: boolean;
  readonly userId: string | null;
}

/**
 * Saved Configurations Page Component
 * 
 * Main page for managing saved vehicle configurations. Features:
 * - Authentication check and redirect
 * - List view of saved configurations
 * - Configuration comparison mode
 * - Management actions (edit, delete, share)
 * 
 * @example
 * ```tsx
 * <SavedConfigurations />
 * ```
 */
export default function SavedConfigurations({
  className = '',
}: SavedConfigurationsProps): JSX.Element {
  const navigate = useNavigate();

  // State management
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [selectedForCompare, setSelectedForCompare] = useState<readonly string[]>([]);
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
    userId: null,
  });

  // Check authentication status
  useEffect(() => {
    const checkAuth = async (): Promise<void> => {
      try {
        // Check for authentication token or session
        const token = localStorage.getItem('authToken');
        const userId = localStorage.getItem('userId');

        if (!token || !userId) {
          // Redirect to login if not authenticated
          navigate('/login', {
            state: { from: '/saved-configurations' },
            replace: true,
          });
          return;
        }

        // Verify token is still valid
        const response = await fetch(`${import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000'}/api/v1/auth/verify`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          // Token invalid, redirect to login
          localStorage.removeItem('authToken');
          localStorage.removeItem('userId');
          navigate('/login', {
            state: { from: '/saved-configurations' },
            replace: true,
          });
          return;
        }

        // Authentication successful
        setAuthState({
          isAuthenticated: true,
          isLoading: false,
          userId,
        });
      } catch (error) {
        // Error checking auth, redirect to login
        console.error('Authentication check failed:', error);
        navigate('/login', {
          state: { from: '/saved-configurations' },
          replace: true,
        });
      }
    };

    void checkAuth();
  }, [navigate]);

  // Fetch saved configurations
  const {
    data: configurationsData,
    isLoading: isLoadingConfigurations,
    isError: isConfigurationsError,
    error: configurationsError,
  } = useSavedConfigurations(
    {
      page: 1,
      pageSize: 100,
      status: 'active',
    },
    {
      enabled: authState.isAuthenticated,
      staleTime: 30000,
      retry: 2,
    },
  );

  // Fetch comparison data when in comparison mode
  const {
    data: comparisonData,
    isLoading: isLoadingComparison,
    isError: isComparisonError,
    error: comparisonError,
  } = useCompareConfigurations(
    { configurationIds: selectedForCompare },
    {
      enabled: viewMode === 'comparison' && selectedForCompare.length >= 2,
      staleTime: 60000,
    },
  );

  // Handle configuration edit
  const handleEdit = useCallback(
    (configId: string) => {
      const config = configurationsData?.configurations.find((c) => c.id === configId);
      if (config) {
        navigate(`/configure/${config.vehicleId}?config=${configId}`);
      }
    },
    [configurationsData, navigate],
  );

  // Handle comparison mode
  const handleCompare = useCallback((configIds: readonly string[]) => {
    setSelectedForCompare(configIds);
    setViewMode('comparison');
  }, []);

  // Handle back to list
  const handleBackToList = useCallback(() => {
    setViewMode('list');
    setSelectedForCompare([]);
  }, []);

  // Handle remove from comparison
  const handleRemoveFromComparison = useCallback((configId: string) => {
    setSelectedForCompare((prev) => prev.filter((id) => id !== configId));
  }, []);

  // Handle save configuration from comparison
  const handleSaveFromComparison = useCallback(
    (configId: string) => {
      const config = comparisonData?.configurations.find((c) => c.configurationId === configId);
      if (config) {
        navigate(`/configure/${config.vehicle.id}?config=${configId}`);
      }
    },
    [comparisonData, navigate],
  );

  // Render loading state during auth check
  if (authState.isLoading) {
    return (
      <div className={`saved-configurations-page min-h-screen bg-gray-50 ${className}`}>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
          <span className="ml-3 text-gray-600">Checking authentication...</span>
        </div>
      </div>
    );
  }

  // Don't render if not authenticated (will redirect)
  if (!authState.isAuthenticated) {
    return (
      <div className={`saved-configurations-page min-h-screen bg-gray-50 ${className}`}>
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <p className="text-gray-600">Redirecting to login...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`saved-configurations-page min-h-screen bg-gray-50 ${className}`}>
      {/* Page Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {viewMode === 'list' ? 'Saved Configurations' : 'Compare Configurations'}
              </h1>
              <p className="mt-2 text-sm text-gray-600">
                {viewMode === 'list'
                  ? 'Manage and compare your saved vehicle configurations'
                  : `Comparing ${selectedForCompare.length} configurations`}
              </p>
            </div>

            {viewMode === 'comparison' && (
              <button
                onClick={handleBackToList}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
              >
                <svg
                  className="mr-2 h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 19l-7-7m0 0l7-7m-7 7h18"
                  />
                </svg>
                Back to List
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Page Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {viewMode === 'list' ? (
          <SavedConfigurationsList
            onEdit={handleEdit}
            onCompare={handleCompare}
            enableCompare={true}
            pageSize={20}
          />
        ) : (
          <ConfigurationComparison
            configurations={comparisonData?.configurations ?? []}
            onRemoveConfiguration={handleRemoveFromComparison}
            onSaveConfiguration={handleSaveFromComparison}
            highlightDifferences={true}
            enableMobileView={true}
            isLoading={isLoadingComparison}
            error={
              isComparisonError
                ? comparisonError instanceof Error
                  ? comparisonError.message
                  : 'Failed to load comparison data'
                : null
            }
          />
        )}
      </div>

      {/* Error Toast */}
      {isConfigurationsError && viewMode === 'list' && (
        <div className="fixed bottom-4 right-4 max-w-md">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg">
            <div className="flex items-start">
              <svg
                className="h-5 w-5 text-red-600 mt-0.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error Loading Configurations</h3>
                <p className="mt-1 text-sm text-red-700">
                  {configurationsError instanceof Error
                    ? configurationsError.message
                    : 'Failed to load saved configurations'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}