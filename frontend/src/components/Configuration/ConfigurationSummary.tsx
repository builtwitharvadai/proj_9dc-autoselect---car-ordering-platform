/**
 * Configuration Summary Component
 * Displays complete configuration review with itemized selections and pricing
 * Provides edit capabilities and save/continue actions
 */

import { useCallback, useMemo } from 'react';
import type {
  ColorOption,
  ConfigurationSummary as ConfigurationSummaryType,
  Package,
  TrimLevel,
  VehicleOption,
} from '../../types/configuration';

/**
 * Component props interface
 */
interface ConfigurationSummaryProps {
  readonly summary: ConfigurationSummaryType;
  readonly onEdit: (step: 'select-trim' | 'choose-color' | 'select-packages' | 'add-features') => void;
  readonly onSave: () => void;
  readonly onContinue: () => void;
  readonly isSaving?: boolean;
  readonly className?: string;
}

/**
 * Format currency with proper locale and precision
 */
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Configuration Summary Component
 */
export default function ConfigurationSummary({
  summary,
  onEdit,
  onSave,
  onContinue,
  isSaving = false,
  className = '',
}: ConfigurationSummaryProps): JSX.Element {
  /**
   * Handle edit button click with step navigation
   */
  const handleEdit = useCallback(
    (step: 'select-trim' | 'choose-color' | 'select-packages' | 'add-features') => {
      onEdit(step);
    },
    [onEdit],
  );

  /**
   * Handle save button click
   */
  const handleSave = useCallback(() => {
    if (!isSaving) {
      onSave();
    }
  }, [isSaving, onSave]);

  /**
   * Handle continue button click
   */
  const handleContinue = useCallback(() => {
    if (!isSaving) {
      onContinue();
    }
  }, [isSaving, onContinue]);

  /**
   * Check if configuration is valid
   */
  const isValid = useMemo(() => {
    return summary.validation.isValid;
  }, [summary.validation.isValid]);

  /**
   * Get validation error messages
   */
  const errorMessages = useMemo(() => {
    return summary.validation.errors.map((error) => error.message);
  }, [summary.validation.errors]);

  /**
   * Get validation warning messages
   */
  const warningMessages = useMemo(() => {
    return summary.validation.warnings.map((warning) => warning.message);
  }, [summary.validation.warnings]);

  /**
   * Render trim section
   */
  const renderTrimSection = useCallback(
    (trim: TrimLevel | undefined) => {
      if (!trim) {
        return (
          <div className="text-gray-500 italic">
            No trim selected
          </div>
        );
      }

      return (
        <div className="space-y-2">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h4 className="font-semibold text-gray-900">{trim.name}</h4>
              <p className="text-sm text-gray-600 mt-1">{trim.description}</p>
            </div>
            <div className="text-right ml-4">
              <p className="font-semibold text-gray-900">{formatCurrency(trim.basePrice)}</p>
            </div>
          </div>
          {trim.features.length > 0 && (
            <div className="mt-3">
              <p className="text-sm font-medium text-gray-700 mb-2">Included Features:</p>
              <ul className="text-sm text-gray-600 space-y-1">
                {trim.features.map((feature, index) => (
                  <li key={index} className="flex items-start">
                    <span className="text-blue-600 mr-2">✓</span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      );
    },
    [],
  );

  /**
   * Render color section
   */
  const renderColorSection = useCallback(
    (color: ColorOption | undefined) => {
      if (!color) {
        return (
          <div className="text-gray-500 italic">
            No color selected
          </div>
        );
      }

      return (
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div
              className="w-12 h-12 rounded-lg border-2 border-gray-300 shadow-sm"
              style={{ backgroundColor: color.hexCode }}
              aria-label={`${color.name} color swatch`}
            />
            <div>
              <h4 className="font-semibold text-gray-900">{color.name}</h4>
              <p className="text-sm text-gray-600 capitalize">{color.category}</p>
            </div>
          </div>
          <div className="text-right">
            <p className="font-semibold text-gray-900">
              {color.price > 0 ? formatCurrency(color.price) : 'Included'}
            </p>
          </div>
        </div>
      );
    },
    [],
  );

  /**
   * Render packages section
   */
  const renderPackagesSection = useCallback(
    (packages: readonly Package[]) => {
      if (packages.length === 0) {
        return (
          <div className="text-gray-500 italic">
            No packages selected
          </div>
        );
      }

      return (
        <div className="space-y-4">
          {packages.map((pkg) => (
            <div key={pkg.id} className="border-b border-gray-200 pb-4 last:border-0 last:pb-0">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <h4 className="font-semibold text-gray-900">{pkg.name}</h4>
                  <p className="text-sm text-gray-600 mt-1">{pkg.description}</p>
                </div>
                <div className="text-right ml-4">
                  <p className="font-semibold text-gray-900">{formatCurrency(pkg.price)}</p>
                  {pkg.discountPercentage > 0 && (
                    <p className="text-sm text-green-600">
                      Save {pkg.discountPercentage}%
                    </p>
                  )}
                </div>
              </div>
              {pkg.includedOptions.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs font-medium text-gray-700 mb-1">Includes:</p>
                  <ul className="text-xs text-gray-600 space-y-1">
                    {pkg.includedOptions.map((optionId, index) => (
                      <li key={index} className="flex items-start">
                        <span className="text-blue-600 mr-1">•</span>
                        <span>{optionId}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      );
    },
    [],
  );

  /**
   * Render options section
   */
  const renderOptionsSection = useCallback(
    (options: readonly VehicleOption[]) => {
      if (options.length === 0) {
        return (
          <div className="text-gray-500 italic">
            No individual options selected
          </div>
        );
      }

      return (
        <div className="space-y-3">
          {options.map((option) => (
            <div key={option.id} className="flex items-start justify-between">
              <div className="flex-1">
                <h4 className="font-medium text-gray-900">{option.name}</h4>
                <p className="text-sm text-gray-600 mt-1">{option.description}</p>
                <p className="text-xs text-gray-500 mt-1 capitalize">{option.category}</p>
              </div>
              <div className="text-right ml-4">
                <p className="font-semibold text-gray-900">{formatCurrency(option.price)}</p>
              </div>
            </div>
          ))}
        </div>
      );
    },
    [],
  );

  /**
   * Render pricing breakdown
   */
  const renderPricingBreakdown = useCallback(() => {
    const { pricing } = summary;

    return (
      <div className="space-y-3">
        <div className="flex justify-between text-gray-700">
          <span>Base Price</span>
          <span>{formatCurrency(pricing.basePrice)}</span>
        </div>

        {pricing.optionsPrice > 0 && (
          <div className="flex justify-between text-gray-700">
            <span>Options</span>
            <span>{formatCurrency(pricing.optionsPrice)}</span>
          </div>
        )}

        {pricing.packagesPrice > 0 && (
          <div className="flex justify-between text-gray-700">
            <span>Packages</span>
            <span>{formatCurrency(pricing.packagesPrice)}</span>
          </div>
        )}

        {pricing.packagesDiscount > 0 && (
          <div className="flex justify-between text-green-600">
            <span>Package Savings</span>
            <span>-{formatCurrency(pricing.packagesDiscount)}</span>
          </div>
        )}

        <div className="border-t border-gray-300 pt-3">
          <div className="flex justify-between text-gray-700">
            <span>Subtotal</span>
            <span>{formatCurrency(pricing.subtotal)}</span>
          </div>
        </div>

        {pricing.destinationCharge > 0 && (
          <div className="flex justify-between text-gray-700">
            <span>Destination Charge</span>
            <span>{formatCurrency(pricing.destinationCharge)}</span>
          </div>
        )}

        {pricing.taxAmount > 0 && (
          <div className="flex justify-between text-gray-700">
            <span>Tax ({(pricing.taxRate * 100).toFixed(2)}%)</span>
            <span>{formatCurrency(pricing.taxAmount)}</span>
          </div>
        )}

        <div className="border-t-2 border-gray-900 pt-3">
          <div className="flex justify-between text-xl font-bold text-gray-900">
            <span>Total Price</span>
            <span>{formatCurrency(pricing.total)}</span>
          </div>
        </div>
      </div>
    );
  }, [summary]);

  return (
    <div className={`bg-white rounded-lg shadow-lg ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-2xl font-bold text-gray-900">Configuration Summary</h2>
        <p className="text-sm text-gray-600 mt-1">
          Review your selections before continuing
        </p>
      </div>

      {/* Vehicle Info */}
      <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">
          {summary.vehicle.year} {summary.vehicle.make} {summary.vehicle.model}
        </h3>
      </div>

      {/* Validation Messages */}
      {(!isValid || warningMessages.length > 0) && (
        <div className="px-6 py-4 border-b border-gray-200">
          {errorMessages.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-3">
              <h4 className="text-sm font-semibold text-red-800 mb-2">Configuration Errors:</h4>
              <ul className="text-sm text-red-700 space-y-1">
                {errorMessages.map((message, index) => (
                  <li key={index} className="flex items-start">
                    <span className="mr-2">•</span>
                    <span>{message}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {warningMessages.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-yellow-800 mb-2">Warnings:</h4>
              <ul className="text-sm text-yellow-700 space-y-1">
                {warningMessages.map((message, index) => (
                  <li key={index} className="flex items-start">
                    <span className="mr-2">•</span>
                    <span>{message}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Configuration Sections */}
      <div className="px-6 py-4 space-y-6">
        {/* Trim Section */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-gray-900">Trim Level</h3>
            <button
              type="button"
              onClick={() => handleEdit('select-trim')}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              aria-label="Edit trim selection"
            >
              Edit
            </button>
          </div>
          {renderTrimSection(summary.trim)}
        </div>

        {/* Color Section */}
        <div className="border-t border-gray-200 pt-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-gray-900">Exterior Color</h3>
            <button
              type="button"
              onClick={() => handleEdit('choose-color')}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              aria-label="Edit color selection"
            >
              Edit
            </button>
          </div>
          {renderColorSection(summary.color)}
        </div>

        {/* Packages Section */}
        <div className="border-t border-gray-200 pt-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-gray-900">
              Packages ({summary.packages.length})
            </h3>
            <button
              type="button"
              onClick={() => handleEdit('select-packages')}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              aria-label="Edit package selections"
            >
              Edit
            </button>
          </div>
          {renderPackagesSection(summary.packages)}
        </div>

        {/* Options Section */}
        <div className="border-t border-gray-200 pt-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-gray-900">
              Individual Options ({summary.options.length})
            </h3>
            <button
              type="button"
              onClick={() => handleEdit('add-features')}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              aria-label="Edit option selections"
            >
              Edit
            </button>
          </div>
          {renderOptionsSection(summary.options)}
        </div>
      </div>

      {/* Pricing Summary */}
      <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Pricing Summary</h3>
        {renderPricingBreakdown()}
      </div>

      {/* Action Buttons */}
      <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
        <button
          type="button"
          onClick={handleSave}
          disabled={isSaving}
          className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Save configuration"
        >
          {isSaving ? 'Saving...' : 'Save Configuration'}
        </button>

        <button
          type="button"
          onClick={handleContinue}
          disabled={!isValid || isSaving}
          className="px-8 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Continue to next step"
        >
          Continue
        </button>
      </div>
    </div>
  );
}