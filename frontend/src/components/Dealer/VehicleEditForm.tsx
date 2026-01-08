import React, { useState, useCallback, useEffect } from 'react';
import type {
  DealerInventoryWithVehicle,
  InventoryUpdateRequest,
  DealerInventoryStatus,
} from '../../types/dealer';

/**
 * Props for VehicleEditForm component
 */
interface VehicleEditFormProps {
  readonly inventory: DealerInventoryWithVehicle;
  readonly onSave: (
    inventoryId: string,
    updates: InventoryUpdateRequest,
  ) => Promise<void>;
  readonly onCancel: () => void;
  readonly isSubmitting?: boolean;
  readonly className?: string;
}

/**
 * Form state interface
 */
interface FormState {
  readonly stockLevel: string;
  readonly location: string;
  readonly status: DealerInventoryStatus;
  readonly notes: string;
}

/**
 * Form validation errors
 */
interface FormErrors {
  readonly stockLevel?: string;
  readonly location?: string;
  readonly status?: string;
  readonly notes?: string;
}

/**
 * Status options for dropdown
 */
const STATUS_OPTIONS: ReadonlyArray<{
  readonly value: DealerInventoryStatus;
  readonly label: string;
  readonly description: string;
}> = [
  {
    value: 'active',
    label: 'Active',
    description: 'Vehicle is available for sale',
  },
  {
    value: 'inactive',
    label: 'Inactive',
    description: 'Vehicle is temporarily unavailable',
  },
  {
    value: 'sold',
    label: 'Sold',
    description: 'Vehicle has been sold',
  },
  {
    value: 'reserved',
    label: 'Reserved',
    description: 'Vehicle is reserved for a customer',
  },
] as const;

/**
 * VehicleEditForm Component
 * 
 * Comprehensive form for editing individual vehicle inventory records.
 * Includes validation, real-time updates, and proper error handling.
 */
export default function VehicleEditForm({
  inventory,
  onSave,
  onCancel,
  isSubmitting = false,
  className = '',
}: VehicleEditFormProps): JSX.Element {
  // Form state
  const [formState, setFormState] = useState<FormState>({
    stockLevel: inventory.stockLevel.toString(),
    location: inventory.location,
    status: inventory.status,
    notes: inventory.notes ?? '',
  });

  // Validation errors
  const [errors, setErrors] = useState<FormErrors>({});

  // Track if form has been modified
  const [isDirty, setIsDirty] = useState(false);

  // Track if form has been touched
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  /**
   * Validate form field
   */
  const validateField = useCallback(
    (name: keyof FormState, value: string): string | undefined => {
      switch (name) {
        case 'stockLevel': {
          const numValue = parseInt(value, 10);
          if (value.trim() === '') {
            return 'Stock level is required';
          }
          if (isNaN(numValue)) {
            return 'Stock level must be a valid number';
          }
          if (numValue < 0) {
            return 'Stock level cannot be negative';
          }
          if (numValue > 10000) {
            return 'Stock level cannot exceed 10,000';
          }
          if (!Number.isInteger(numValue)) {
            return 'Stock level must be a whole number';
          }
          return undefined;
        }

        case 'location': {
          const trimmed = value.trim();
          if (trimmed === '') {
            return 'Location is required';
          }
          if (trimmed.length < 2) {
            return 'Location must be at least 2 characters';
          }
          if (trimmed.length > 200) {
            return 'Location cannot exceed 200 characters';
          }
          return undefined;
        }

        case 'status': {
          const validStatuses: readonly DealerInventoryStatus[] = [
            'active',
            'inactive',
            'sold',
            'reserved',
          ];
          if (!validStatuses.includes(value as DealerInventoryStatus)) {
            return 'Invalid status selected';
          }
          return undefined;
        }

        case 'notes': {
          if (value.length > 1000) {
            return 'Notes cannot exceed 1,000 characters';
          }
          return undefined;
        }

        default:
          return undefined;
      }
    },
    [],
  );

  /**
   * Validate entire form
   */
  const validateForm = useCallback((): FormErrors => {
    const newErrors: FormErrors = {};

    const stockLevelError = validateField('stockLevel', formState.stockLevel);
    if (stockLevelError) {
      newErrors.stockLevel = stockLevelError;
    }

    const locationError = validateField('location', formState.location);
    if (locationError) {
      newErrors.location = locationError;
    }

    const statusError = validateField('status', formState.status);
    if (statusError) {
      newErrors.status = statusError;
    }

    const notesError = validateField('notes', formState.notes);
    if (notesError) {
      newErrors.notes = notesError;
    }

    return newErrors;
  }, [formState, validateField]);

  /**
   * Handle field change
   */
  const handleFieldChange = useCallback(
    (name: keyof FormState, value: string) => {
      setFormState((prev) => ({
        ...prev,
        [name]: value,
      }));

      setIsDirty(true);

      // Validate field if it has been touched
      if (touched[name]) {
        const error = validateField(name, value);
        setErrors((prev) => ({
          ...prev,
          [name]: error,
        }));
      }
    },
    [touched, validateField],
  );

  /**
   * Handle field blur
   */
  const handleFieldBlur = useCallback(
    (name: keyof FormState) => {
      setTouched((prev) => ({
        ...prev,
        [name]: true,
      }));

      // Validate field on blur
      const error = validateField(name, formState[name]);
      setErrors((prev) => ({
        ...prev,
        [name]: error,
      }));
    },
    [formState, validateField],
  );

  /**
   * Handle form submission
   */
  const handleSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();

      // Mark all fields as touched
      setTouched({
        stockLevel: true,
        location: true,
        status: true,
        notes: true,
      });

      // Validate form
      const validationErrors = validateForm();
      setErrors(validationErrors);

      // Check if there are any errors
      if (Object.keys(validationErrors).length > 0) {
        return;
      }

      try {
        // Prepare update request
        const updates: InventoryUpdateRequest = {
          stockLevel: parseInt(formState.stockLevel, 10),
          location: formState.location.trim(),
          status: formState.status,
          notes: formState.notes.trim() || undefined,
        };

        // Call onSave callback
        await onSave(inventory.id, updates);

        // Reset dirty state on successful save
        setIsDirty(false);
      } catch (error) {
        // Error handling is done by parent component
        console.error('Failed to save vehicle inventory:', error);
      }
    },
    [formState, inventory.id, onSave, validateForm],
  );

  /**
   * Handle cancel with confirmation if form is dirty
   */
  const handleCancel = useCallback(() => {
    if (isDirty) {
      const confirmed = window.confirm(
        'You have unsaved changes. Are you sure you want to cancel?',
      );
      if (!confirmed) {
        return;
      }
    }
    onCancel();
  }, [isDirty, onCancel]);

  /**
   * Reset form to initial values
   */
  const handleReset = useCallback(() => {
    setFormState({
      stockLevel: inventory.stockLevel.toString(),
      location: inventory.location,
      status: inventory.status,
      notes: inventory.notes ?? '',
    });
    setErrors({});
    setTouched({});
    setIsDirty(false);
  }, [inventory]);

  /**
   * Warn user before leaving with unsaved changes
   */
  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      if (isDirty) {
        event.preventDefault();
        event.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [isDirty]);

  return (
    <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>
      {/* Vehicle Information Header */}
      <div className="mb-6 pb-4 border-b border-gray-200">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Edit Vehicle Inventory
        </h2>
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <div>
            <span className="font-medium">VIN:</span> {inventory.vin}
          </div>
          <div>
            <span className="font-medium">Vehicle:</span>{' '}
            {inventory.vehicle.year} {inventory.vehicle.make}{' '}
            {inventory.vehicle.model}
          </div>
        </div>
      </div>

      {/* Edit Form */}
      <form onSubmit={handleSubmit} noValidate>
        <div className="space-y-6">
          {/* Stock Level */}
          <div>
            <label
              htmlFor="stockLevel"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Stock Level <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              id="stockLevel"
              name="stockLevel"
              value={formState.stockLevel}
              onChange={(e) => handleFieldChange('stockLevel', e.target.value)}
              onBlur={() => handleFieldBlur('stockLevel')}
              disabled={isSubmitting}
              min="0"
              max="10000"
              step="1"
              className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed ${
                errors.stockLevel && touched.stockLevel
                  ? 'border-red-500'
                  : 'border-gray-300'
              }`}
              aria-invalid={
                errors.stockLevel && touched.stockLevel ? 'true' : 'false'
              }
              aria-describedby={
                errors.stockLevel && touched.stockLevel
                  ? 'stockLevel-error'
                  : undefined
              }
            />
            {errors.stockLevel && touched.stockLevel && (
              <p
                id="stockLevel-error"
                className="mt-1 text-sm text-red-600"
                role="alert"
              >
                {errors.stockLevel}
              </p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              Current: {inventory.stockLevel} | Available:{' '}
              {inventory.availableQuantity} | Reserved:{' '}
              {inventory.reservedQuantity}
            </p>
          </div>

          {/* Location */}
          <div>
            <label
              htmlFor="location"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Location <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="location"
              name="location"
              value={formState.location}
              onChange={(e) => handleFieldChange('location', e.target.value)}
              onBlur={() => handleFieldBlur('location')}
              disabled={isSubmitting}
              maxLength={200}
              className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed ${
                errors.location && touched.location
                  ? 'border-red-500'
                  : 'border-gray-300'
              }`}
              aria-invalid={
                errors.location && touched.location ? 'true' : 'false'
              }
              aria-describedby={
                errors.location && touched.location
                  ? 'location-error'
                  : undefined
              }
            />
            {errors.location && touched.location && (
              <p
                id="location-error"
                className="mt-1 text-sm text-red-600"
                role="alert"
              >
                {errors.location}
              </p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              Warehouse, lot, or storage location
            </p>
          </div>

          {/* Status */}
          <div>
            <label
              htmlFor="status"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Status <span className="text-red-500">*</span>
            </label>
            <select
              id="status"
              name="status"
              value={formState.status}
              onChange={(e) =>
                handleFieldChange(
                  'status',
                  e.target.value as DealerInventoryStatus,
                )
              }
              onBlur={() => handleFieldBlur('status')}
              disabled={isSubmitting}
              className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed ${
                errors.status && touched.status
                  ? 'border-red-500'
                  : 'border-gray-300'
              }`}
              aria-invalid={errors.status && touched.status ? 'true' : 'false'}
              aria-describedby={
                errors.status && touched.status ? 'status-error' : undefined
              }
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            {errors.status && touched.status && (
              <p
                id="status-error"
                className="mt-1 text-sm text-red-600"
                role="alert"
              >
                {errors.status}
              </p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              {
                STATUS_OPTIONS.find((opt) => opt.value === formState.status)
                  ?.description
              }
            </p>
          </div>

          {/* Notes */}
          <div>
            <label
              htmlFor="notes"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Notes
            </label>
            <textarea
              id="notes"
              name="notes"
              value={formState.notes}
              onChange={(e) => handleFieldChange('notes', e.target.value)}
              onBlur={() => handleFieldBlur('notes')}
              disabled={isSubmitting}
              maxLength={1000}
              rows={4}
              className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed resize-vertical ${
                errors.notes && touched.notes
                  ? 'border-red-500'
                  : 'border-gray-300'
              }`}
              aria-invalid={errors.notes && touched.notes ? 'true' : 'false'}
              aria-describedby={
                errors.notes && touched.notes ? 'notes-error' : undefined
              }
            />
            {errors.notes && touched.notes && (
              <p
                id="notes-error"
                className="mt-1 text-sm text-red-600"
                role="alert"
              >
                {errors.notes}
              </p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              {formState.notes.length}/1000 characters
            </p>
          </div>
        </div>

        {/* Form Actions */}
        <div className="mt-8 flex items-center justify-between gap-4 pt-6 border-t border-gray-200">
          <button
            type="button"
            onClick={handleReset}
            disabled={isSubmitting || !isDirty}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Reset
          </button>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleCancel}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={isSubmitting || !isDirty}
              className="px-6 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>

        {/* Dirty State Indicator */}
        {isDirty && !isSubmitting && (
          <p className="mt-4 text-sm text-amber-600 text-center">
            You have unsaved changes
          </p>
        )}
      </form>
    </div>
  );
}