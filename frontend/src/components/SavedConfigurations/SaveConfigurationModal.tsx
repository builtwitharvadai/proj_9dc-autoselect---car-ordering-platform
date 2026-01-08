/**
 * Modal component for saving vehicle configurations
 * Provides form interface for naming and saving current configuration state
 */

import { useState, useCallback, useEffect, useRef, type FormEvent, type ChangeEvent } from 'react';
import {
  useSaveConfiguration,
  type SaveConfigurationRequest,
  type SaveConfigurationResponse,
  isSavedConfigurationApiError,
} from '../../hooks/useSavedConfigurations';
import { useConfiguration } from '../../contexts/ConfigurationContext';
import {
  isValidConfigurationName,
  isValidConfigurationDescription,
  SAVED_CONFIGURATION_CONSTRAINTS,
} from '../../types/savedConfiguration';

/**
 * Props for SaveConfigurationModal component
 */
export interface SaveConfigurationModalProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly onSuccess?: (savedConfig: SaveConfigurationResponse) => void;
  readonly onError?: (error: Error) => void;
  readonly className?: string;
  readonly vehicleId: string;
  readonly trimId?: string;
  readonly colorId?: string;
  readonly packageIds: readonly string[];
  readonly optionIds: readonly string[];
}

/**
 * Form validation state
 */
interface ValidationState {
  readonly name: string;
  readonly description: string;
}

/**
 * Form error state
 */
interface FormErrors {
  readonly name?: string;
  readonly description?: string;
  readonly general?: string;
}

/**
 * Modal for saving current vehicle configuration with custom name
 * Includes validation, error handling, and success feedback
 */
export default function SaveConfigurationModal({
  isOpen,
  onClose,
  onSuccess,
  onError,
  className = '',
  vehicleId,
  trimId,
  colorId,
  packageIds,
  optionIds,
}: SaveConfigurationModalProps): JSX.Element | null {
  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  // Refs
  const nameInputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  // Hooks
  const { state: configState } = useConfiguration();
  const saveConfigMutation = useSaveConfiguration({
    onSuccess: (data) => {
      setShowSuccess(true);
      setIsSubmitting(false);
      
      // Call success callback after brief delay to show success message
      setTimeout(() => {
        onSuccess?.(data);
        handleClose();
      }, 1500);
    },
    onError: (error) => {
      setIsSubmitting(false);
      
      if (isSavedConfigurationApiError(error)) {
        if (error.statusCode === 400) {
          setErrors({ general: error.message });
        } else if (error.statusCode === 401) {
          setErrors({ general: 'You must be logged in to save configurations' });
        } else {
          setErrors({ general: 'Failed to save configuration. Please try again.' });
        }
      } else {
        setErrors({ general: 'An unexpected error occurred. Please try again.' });
      }
      
      onError?.(error);
    },
  });

  /**
   * Reset form state
   */
  const resetForm = useCallback(() => {
    setName('');
    setDescription('');
    setErrors({});
    setIsSubmitting(false);
    setShowSuccess(false);
  }, []);

  /**
   * Handle modal close
   */
  const handleClose = useCallback(() => {
    if (!isSubmitting) {
      resetForm();
      onClose();
    }
  }, [isSubmitting, resetForm, onClose]);

  /**
   * Validate form fields
   */
  const validateForm = useCallback((): boolean => {
    const newErrors: FormErrors = {};

    // Validate name
    if (!name.trim()) {
      newErrors.name = 'Configuration name is required';
    } else if (!isValidConfigurationName(name)) {
      newErrors.name = `Name must be between ${SAVED_CONFIGURATION_CONSTRAINTS.MIN_NAME_LENGTH} and ${SAVED_CONFIGURATION_CONSTRAINTS.MAX_NAME_LENGTH} characters`;
    }

    // Validate description
    if (description && !isValidConfigurationDescription(description)) {
      newErrors.description = `Description must not exceed ${SAVED_CONFIGURATION_CONSTRAINTS.MAX_DESCRIPTION_LENGTH} characters`;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [name, description]);

  /**
   * Handle form submission
   */
  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();

      if (isSubmitting || showSuccess) {
        return;
      }

      // Validate form
      if (!validateForm()) {
        return;
      }

      setIsSubmitting(true);
      setErrors({});

      try {
        const request: SaveConfigurationRequest = {
          name: name.trim(),
          description: description.trim() || undefined,
          vehicleId,
          trimId,
          colorId,
          packageIds,
          optionIds,
          visibility: 'private',
        };

        saveConfigMutation.mutate(request);
      } catch (error) {
        setIsSubmitting(false);
        setErrors({
          general: error instanceof Error ? error.message : 'Failed to save configuration',
        });
      }
    },
    [
      isSubmitting,
      showSuccess,
      validateForm,
      name,
      description,
      vehicleId,
      trimId,
      colorId,
      packageIds,
      optionIds,
      saveConfigMutation,
    ],
  );

  /**
   * Handle name input change
   */
  const handleNameChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setName(value);
    
    // Clear name error when user starts typing
    if (errors.name) {
      setErrors((prev) => ({ ...prev, name: undefined }));
    }
  }, [errors.name]);

  /**
   * Handle description input change
   */
  const handleDescriptionChange = useCallback((event: ChangeEvent<HTMLTextAreaElement>) => {
    const value = event.target.value;
    setDescription(value);
    
    // Clear description error when user starts typing
    if (errors.description) {
      setErrors((prev) => ({ ...prev, description: undefined }));
    }
  }, [errors.description]);

  /**
   * Handle escape key press
   */
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isSubmitting) {
        handleClose();
      }
    },
    [isSubmitting, handleClose],
  );

  /**
   * Handle backdrop click
   */
  const handleBackdropClick = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      if (event.target === event.currentTarget && !isSubmitting) {
        handleClose();
      }
    },
    [isSubmitting, handleClose],
  );

  /**
   * Focus name input when modal opens
   */
  useEffect(() => {
    if (isOpen && nameInputRef.current) {
      nameInputRef.current.focus();
    }
  }, [isOpen]);

  /**
   * Add escape key listener
   */
  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => {
        document.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [isOpen, handleKeyDown]);

  /**
   * Prevent body scroll when modal is open
   */
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = '';
      };
    }
  }, [isOpen]);

  // Don't render if not open
  if (!isOpen) {
    return null;
  }

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4 ${className}`}
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="save-config-title"
    >
      <div
        ref={modalRef}
        className="w-full max-w-md rounded-lg bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 id="save-config-title" className="text-xl font-semibold text-gray-900">
            Save Configuration
          </h2>
          <button
            type="button"
            onClick={handleClose}
            disabled={isSubmitting}
            className="rounded-full p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Close modal"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="px-6 py-4">
          {/* Success message */}
          {showSuccess && (
            <div className="mb-4 rounded-md bg-green-50 p-4">
              <div className="flex">
                <svg
                  className="h-5 w-5 text-green-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
                <p className="ml-3 text-sm font-medium text-green-800">
                  Configuration saved successfully!
                </p>
              </div>
            </div>
          )}

          {/* General error */}
          {errors.general && (
            <div className="mb-4 rounded-md bg-red-50 p-4">
              <div className="flex">
                <svg
                  className="h-5 w-5 text-red-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
                <p className="ml-3 text-sm font-medium text-red-800">{errors.general}</p>
              </div>
            </div>
          )}

          {/* Name field */}
          <div className="mb-4">
            <label htmlFor="config-name" className="mb-2 block text-sm font-medium text-gray-700">
              Configuration Name <span className="text-red-500">*</span>
            </label>
            <input
              ref={nameInputRef}
              id="config-name"
              type="text"
              value={name}
              onChange={handleNameChange}
              disabled={isSubmitting || showSuccess}
              maxLength={SAVED_CONFIGURATION_CONSTRAINTS.MAX_NAME_LENGTH}
              className={`w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-500 ${
                errors.name
                  ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                  : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
              }`}
              placeholder="e.g., My Dream Car"
              aria-invalid={Boolean(errors.name)}
              aria-describedby={errors.name ? 'name-error' : undefined}
            />
            {errors.name && (
              <p id="name-error" className="mt-1 text-sm text-red-600">
                {errors.name}
              </p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              {name.length}/{SAVED_CONFIGURATION_CONSTRAINTS.MAX_NAME_LENGTH} characters
            </p>
          </div>

          {/* Description field */}
          <div className="mb-6">
            <label
              htmlFor="config-description"
              className="mb-2 block text-sm font-medium text-gray-700"
            >
              Description (Optional)
            </label>
            <textarea
              id="config-description"
              value={description}
              onChange={handleDescriptionChange}
              disabled={isSubmitting || showSuccess}
              maxLength={SAVED_CONFIGURATION_CONSTRAINTS.MAX_DESCRIPTION_LENGTH}
              rows={3}
              className={`w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-500 ${
                errors.description
                  ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                  : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
              }`}
              placeholder="Add notes about this configuration..."
              aria-invalid={Boolean(errors.description)}
              aria-describedby={errors.description ? 'description-error' : undefined}
            />
            {errors.description && (
              <p id="description-error" className="mt-1 text-sm text-red-600">
                {errors.description}
              </p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              {description.length}/{SAVED_CONFIGURATION_CONSTRAINTS.MAX_DESCRIPTION_LENGTH}{' '}
              characters
            </p>
          </div>

          {/* Actions */}
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting || showSuccess}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || showSuccess}
              className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <svg
                    className="-ml-1 mr-2 h-4 w-4 animate-spin text-white"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Saving...
                </>
              ) : showSuccess ? (
                <>
                  <svg className="-ml-1 mr-2 h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Saved
                </>
              ) : (
                'Save Configuration'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}