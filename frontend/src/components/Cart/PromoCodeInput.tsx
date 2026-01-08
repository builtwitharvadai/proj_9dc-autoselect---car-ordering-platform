/**
 * Promotional Code Input Component
 * Provides input field for promotional code entry with validation,
 * application, and removal functionality with real-time feedback
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { useApplyPromoCode } from '../../hooks/useCart';
import { isCartApiError } from '../../hooks/useCart';
import type { Cart } from '../../types/cart';

/**
 * Component props interface
 */
export interface PromoCodeInputProps {
  readonly cart: Cart | undefined;
  readonly disabled?: boolean;
  readonly className?: string;
  readonly onSuccess?: (cart: Cart) => void;
  readonly onError?: (error: Error) => void;
}

/**
 * Input state type
 */
type InputState = 'idle' | 'validating' | 'success' | 'error';

/**
 * Promotional code input and application component
 */
export default function PromoCodeInput({
  cart,
  disabled = false,
  className = '',
  onSuccess,
  onError,
}: PromoCodeInputProps): JSX.Element {
  const [code, setCode] = useState('');
  const [inputState, setInputState] = useState<InputState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const applyPromoCodeMutation = useApplyPromoCode();

  const appliedCode = cart?.promotionalCode;
  const hasAppliedCode = appliedCode !== undefined && appliedCode.length > 0;

  /**
   * Reset input state
   */
  const resetState = useCallback(() => {
    setInputState('idle');
    setErrorMessage(null);
  }, []);

  /**
   * Handle input change
   */
  const handleInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const value = event.target.value.trim().toUpperCase();
      setCode(value);
      if (inputState !== 'idle') {
        resetState();
      }
    },
    [inputState, resetState],
  );

  /**
   * Handle promotional code application
   */
  const handleApply = useCallback(async () => {
    if (!code || code.length === 0) {
      setInputState('error');
      setErrorMessage('Please enter a promotional code');
      return;
    }

    if (hasAppliedCode && appliedCode === code) {
      setInputState('error');
      setErrorMessage('This code is already applied');
      return;
    }

    setInputState('validating');
    setErrorMessage(null);

    try {
      const response = await applyPromoCodeMutation.mutateAsync({ code });

      setInputState('success');
      setCode('');

      if (onSuccess) {
        onSuccess(response.cart);
      }

      setTimeout(() => {
        resetState();
      }, 3000);
    } catch (error) {
      setInputState('error');

      let message = 'Failed to apply promotional code';

      if (isCartApiError(error)) {
        if (error.cartError) {
          switch (error.cartError.type) {
            case 'INVALID_PROMOTIONAL_CODE':
              message = 'Invalid promotional code';
              break;
            case 'PROMOTIONAL_CODE_EXPIRED':
              message = 'This promotional code has expired';
              break;
            case 'PROMOTIONAL_CODE_USAGE_LIMIT':
              message = 'This promotional code has reached its usage limit';
              break;
            case 'MIN_PURCHASE_NOT_MET':
              message = error.cartError.message || 'Minimum purchase amount not met';
              break;
            default:
              message = error.cartError.message || message;
          }
        } else {
          message = error.message;
        }
      } else if (error instanceof Error) {
        message = error.message;
      }

      setErrorMessage(message);

      if (onError) {
        onError(error instanceof Error ? error : new Error(message));
      }
    }
  }, [
    code,
    hasAppliedCode,
    appliedCode,
    applyPromoCodeMutation,
    onSuccess,
    onError,
    resetState,
  ]);

  /**
   * Handle promotional code removal
   */
  const handleRemove = useCallback(async () => {
    if (!hasAppliedCode) {
      return;
    }

    setInputState('validating');
    setErrorMessage(null);

    try {
      const response = await applyPromoCodeMutation.mutateAsync({ code: '' });

      setInputState('idle');
      setCode('');

      if (onSuccess) {
        onSuccess(response.cart);
      }
    } catch (error) {
      setInputState('error');

      const message =
        error instanceof Error ? error.message : 'Failed to remove promotional code';

      setErrorMessage(message);

      if (onError) {
        onError(error instanceof Error ? error : new Error(message));
      }
    }
  }, [hasAppliedCode, applyPromoCodeMutation, onSuccess, onError]);

  /**
   * Handle form submission
   */
  const handleSubmit = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      void handleApply();
    },
    [handleApply],
  );

  /**
   * Handle key press
   */
  const handleKeyPress = useCallback(
    (event: React.KeyboardEvent<HTMLInputElement>) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        void handleApply();
      }
    },
    [handleApply],
  );

  /**
   * Focus input on mount
   */
  useEffect(() => {
    if (!hasAppliedCode && inputRef.current) {
      inputRef.current.focus();
    }
  }, [hasAppliedCode]);

  const isDisabled = disabled || inputState === 'validating';
  const showAppliedCode = hasAppliedCode && inputState !== 'validating';
  const showInput = !showAppliedCode;

  return (
    <div className={`promo-code-input ${className}`}>
      {showInput && (
        <form onSubmit={handleSubmit} className="space-y-2">
          <div className="flex gap-2">
            <div className="flex-1">
              <label htmlFor="promo-code" className="sr-only">
                Promotional Code
              </label>
              <input
                ref={inputRef}
                id="promo-code"
                type="text"
                value={code}
                onChange={handleInputChange}
                onKeyPress={handleKeyPress}
                placeholder="Enter promo code"
                disabled={isDisabled}
                className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 transition-colors ${
                  inputState === 'error'
                    ? 'border-red-500 focus:ring-red-500'
                    : inputState === 'success'
                      ? 'border-green-500 focus:ring-green-500'
                      : 'border-gray-300 focus:ring-blue-500'
                } ${isDisabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'}`}
                aria-invalid={inputState === 'error'}
                aria-describedby={
                  inputState === 'error' ? 'promo-code-error' : undefined
                }
              />
            </div>
            <button
              type="submit"
              disabled={isDisabled || code.length === 0}
              className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                isDisabled || code.length === 0
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800'
              }`}
              aria-label="Apply promotional code"
            >
              {inputState === 'validating' ? (
                <span className="flex items-center gap-2">
                  <svg
                    className="animate-spin h-5 w-5"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
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
                  <span>Applying...</span>
                </span>
              ) : (
                'Apply'
              )}
            </button>
          </div>

          {inputState === 'error' && errorMessage && (
            <div
              id="promo-code-error"
              className="flex items-start gap-2 text-sm text-red-600"
              role="alert"
            >
              <svg
                className="w-5 h-5 flex-shrink-0 mt-0.5"
                fill="currentColor"
                viewBox="0 0 20 20"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
              <span>{errorMessage}</span>
            </div>
          )}

          {inputState === 'success' && (
            <div
              className="flex items-start gap-2 text-sm text-green-600"
              role="status"
            >
              <svg
                className="w-5 h-5 flex-shrink-0 mt-0.5"
                fill="currentColor"
                viewBox="0 0 20 20"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
              <span>Promotional code applied successfully!</span>
            </div>
          )}
        </form>
      )}

      {showAppliedCode && (
        <div className="flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center gap-3">
            <svg
              className="w-5 h-5 text-green-600 flex-shrink-0"
              fill="currentColor"
              viewBox="0 0 20 20"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            <div>
              <p className="text-sm font-medium text-green-900">
                Promotional code applied
              </p>
              <p className="text-sm text-green-700 font-mono">{appliedCode}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void handleRemove()}
            disabled={isDisabled}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              isDisabled
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-white text-red-600 hover:bg-red-50 active:bg-red-100 border border-red-200'
            }`}
            aria-label="Remove promotional code"
          >
            {inputState === 'validating' ? 'Removing...' : 'Remove'}
          </button>
        </div>
      )}
    </div>
  );
}