/**
 * Quantity Selector Component
 * Provides increment/decrement controls with direct input, validation,
 * debounced updates, and loading states during API calls
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Minus, Plus } from 'lucide-react';

/**
 * Quantity selector props
 */
export interface QuantitySelectorProps {
  /** Current quantity value */
  readonly quantity: number;
  /** Callback when quantity changes */
  readonly onQuantityChange: (quantity: number) => void;
  /** Minimum allowed quantity */
  readonly min?: number;
  /** Maximum allowed quantity */
  readonly max?: number;
  /** Whether the selector is disabled */
  readonly disabled?: boolean;
  /** Whether an update is in progress */
  readonly isLoading?: boolean;
  /** Debounce delay in milliseconds */
  readonly debounceMs?: number;
  /** Additional CSS classes */
  readonly className?: string;
  /** Size variant */
  readonly size?: 'sm' | 'md' | 'lg';
  /** Show validation errors */
  readonly showError?: boolean;
  /** Custom error message */
  readonly errorMessage?: string;
  /** Aria label for accessibility */
  readonly ariaLabel?: string;
}

/**
 * Default configuration values
 */
const DEFAULT_MIN = 1;
const DEFAULT_MAX = 99;
const DEFAULT_DEBOUNCE_MS = 500;
const DEFAULT_SIZE = 'md';

/**
 * Size-specific styling configurations
 */
const SIZE_STYLES = {
  sm: {
    container: 'h-8',
    button: 'w-8 h-8 text-sm',
    input: 'w-12 h-8 text-sm',
  },
  md: {
    container: 'h-10',
    button: 'w-10 h-10 text-base',
    input: 'w-16 h-10 text-base',
  },
  lg: {
    container: 'h-12',
    button: 'w-12 h-12 text-lg',
    input: 'w-20 h-12 text-lg',
  },
} as const;

/**
 * Quantity Selector Component
 * Handles quantity input with increment/decrement buttons, validation,
 * debouncing, and loading states
 */
export default function QuantitySelector({
  quantity,
  onQuantityChange,
  min = DEFAULT_MIN,
  max = DEFAULT_MAX,
  disabled = false,
  isLoading = false,
  debounceMs = DEFAULT_DEBOUNCE_MS,
  className = '',
  size = DEFAULT_SIZE,
  showError = false,
  errorMessage,
  ariaLabel = 'Quantity selector',
}: QuantitySelectorProps): JSX.Element {
  // Local state for input value to allow typing
  const [inputValue, setInputValue] = useState<string>(quantity.toString());
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isFocused, setIsFocused] = useState(false);

  // Refs for debouncing and cleanup
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Sync input value when quantity prop changes externally
  useEffect(() => {
    if (!isFocused) {
      setInputValue(quantity.toString());
      setValidationError(null);
    }
  }, [quantity, isFocused]);

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  /**
   * Validate quantity value
   */
  const validateQuantity = useCallback(
    (value: number): { valid: boolean; error: string | null } => {
      if (!Number.isInteger(value)) {
        return { valid: false, error: 'Quantity must be a whole number' };
      }

      if (value < min) {
        return { valid: false, error: `Minimum quantity is ${min}` };
      }

      if (value > max) {
        return { valid: false, error: `Maximum quantity is ${max}` };
      }

      return { valid: true, error: null };
    },
    [min, max],
  );

  /**
   * Debounced quantity change handler
   */
  const debouncedQuantityChange = useCallback(
    (newQuantity: number) => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      debounceTimerRef.current = setTimeout(() => {
        const validation = validateQuantity(newQuantity);

        if (validation.valid) {
          setValidationError(null);
          onQuantityChange(newQuantity);
        } else {
          setValidationError(validation.error);
        }
      }, debounceMs);
    },
    [debounceMs, onQuantityChange, validateQuantity],
  );

  /**
   * Handle increment button click
   */
  const handleIncrement = useCallback(() => {
    if (disabled || isLoading) return;

    const newQuantity = quantity + 1;
    if (newQuantity <= max) {
      setInputValue(newQuantity.toString());
      setValidationError(null);
      onQuantityChange(newQuantity);
    }
  }, [disabled, isLoading, quantity, max, onQuantityChange]);

  /**
   * Handle decrement button click
   */
  const handleDecrement = useCallback(() => {
    if (disabled || isLoading) return;

    const newQuantity = quantity - 1;
    if (newQuantity >= min) {
      setInputValue(newQuantity.toString());
      setValidationError(null);
      onQuantityChange(newQuantity);
    }
  }, [disabled, isLoading, quantity, min, onQuantityChange]);

  /**
   * Handle direct input change
   */
  const handleInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const value = event.target.value;

      // Allow empty string for clearing
      if (value === '') {
        setInputValue('');
        return;
      }

      // Only allow numeric input
      if (!/^\d+$/.test(value)) {
        return;
      }

      setInputValue(value);

      const numericValue = parseInt(value, 10);
      if (!isNaN(numericValue)) {
        debouncedQuantityChange(numericValue);
      }
    },
    [debouncedQuantityChange],
  );

  /**
   * Handle input blur - validate and correct value
   */
  const handleInputBlur = useCallback(() => {
    setIsFocused(false);

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    const numericValue = parseInt(inputValue, 10);

    if (isNaN(numericValue) || inputValue === '') {
      // Reset to current quantity if invalid
      setInputValue(quantity.toString());
      setValidationError(null);
      return;
    }

    const validation = validateQuantity(numericValue);

    if (validation.valid) {
      setValidationError(null);
      if (numericValue !== quantity) {
        onQuantityChange(numericValue);
      }
    } else {
      // Reset to valid value
      setInputValue(quantity.toString());
      setValidationError(validation.error);

      // Clear error after delay
      setTimeout(() => {
        setValidationError(null);
      }, 3000);
    }
  }, [inputValue, quantity, onQuantityChange, validateQuantity]);

  /**
   * Handle input focus
   */
  const handleInputFocus = useCallback(() => {
    setIsFocused(true);
    inputRef.current?.select();
  }, []);

  /**
   * Handle keyboard navigation
   */
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLInputElement>) => {
      if (disabled || isLoading) return;

      if (event.key === 'ArrowUp') {
        event.preventDefault();
        handleIncrement();
      } else if (event.key === 'ArrowDown') {
        event.preventDefault();
        handleDecrement();
      } else if (event.key === 'Enter') {
        event.preventDefault();
        inputRef.current?.blur();
      }
    },
    [disabled, isLoading, handleIncrement, handleDecrement],
  );

  // Get size-specific styles
  const sizeStyles = SIZE_STYLES[size];

  // Determine if buttons should be disabled
  const isDecrementDisabled = disabled || isLoading || quantity <= min;
  const isIncrementDisabled = disabled || isLoading || quantity >= max;

  // Determine error to display
  const displayError = showError && (validationError ?? errorMessage);

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <div
        className={`flex items-center gap-2 ${sizeStyles.container}`}
        role="group"
        aria-label={ariaLabel}
      >
        {/* Decrement Button */}
        <button
          type="button"
          onClick={handleDecrement}
          disabled={isDecrementDisabled}
          className={`
            ${sizeStyles.button}
            flex items-center justify-center
            rounded-md border border-gray-300
            bg-white hover:bg-gray-50
            disabled:opacity-50 disabled:cursor-not-allowed
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
            transition-colors duration-150
            ${isLoading ? 'cursor-wait' : ''}
          `}
          aria-label="Decrease quantity"
          aria-disabled={isDecrementDisabled}
        >
          <Minus className="w-4 h-4 text-gray-600" aria-hidden="true" />
        </button>

        {/* Quantity Input */}
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            inputMode="numeric"
            value={inputValue}
            onChange={handleInputChange}
            onBlur={handleInputBlur}
            onFocus={handleInputFocus}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            className={`
              ${sizeStyles.input}
              text-center font-medium
              rounded-md border
              ${validationError ? 'border-red-500' : 'border-gray-300'}
              bg-white
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
              disabled:bg-gray-100 disabled:cursor-not-allowed
              transition-colors duration-150
              ${isLoading ? 'cursor-wait' : ''}
            `}
            aria-label="Quantity"
            aria-valuemin={min}
            aria-valuemax={max}
            aria-valuenow={quantity}
            aria-invalid={!!validationError}
            aria-describedby={displayError ? 'quantity-error' : undefined}
          />

          {/* Loading Spinner Overlay */}
          {isLoading && (
            <div
              className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75 rounded-md"
              aria-hidden="true"
            >
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>

        {/* Increment Button */}
        <button
          type="button"
          onClick={handleIncrement}
          disabled={isIncrementDisabled}
          className={`
            ${sizeStyles.button}
            flex items-center justify-center
            rounded-md border border-gray-300
            bg-white hover:bg-gray-50
            disabled:opacity-50 disabled:cursor-not-allowed
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
            transition-colors duration-150
            ${isLoading ? 'cursor-wait' : ''}
          `}
          aria-label="Increase quantity"
          aria-disabled={isIncrementDisabled}
        >
          <Plus className="w-4 h-4 text-gray-600" aria-hidden="true" />
        </button>
      </div>

      {/* Error Message */}
      {displayError && (
        <p
          id="quantity-error"
          className="text-sm text-red-600"
          role="alert"
          aria-live="polite"
        >
          {displayError}
        </p>
      )}

      {/* Screen Reader Status */}
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {isLoading ? 'Updating quantity...' : `Quantity: ${quantity}`}
      </div>
    </div>
  );
}