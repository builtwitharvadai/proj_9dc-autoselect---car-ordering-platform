/**
 * Real-time pricing sidebar component for vehicle configuration
 * Displays itemized cost breakdown with base price, options, packages, discounts, taxes, and total
 * Implements sticky positioning on desktop and mobile-responsive drawer
 */

import { useEffect, useMemo, useState } from 'react';
import type { PricingBreakdown } from '../../types/configuration';

/**
 * Component props interface
 */
interface PricingSidebarProps {
  readonly pricing: PricingBreakdown | null;
  readonly isLoading?: boolean;
  readonly className?: string;
  readonly sticky?: boolean;
  readonly mobileDrawer?: boolean;
  readonly onCheckout?: () => void;
  readonly showCheckoutButton?: boolean;
}

/**
 * Format currency with proper locale and symbol
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
 * Calculate percentage for visual indicators
 */
function calculatePercentage(part: number, total: number): number {
  if (total === 0) return 0;
  return Math.round((part / total) * 100);
}

/**
 * PricingSidebar component
 */
export default function PricingSidebar({
  pricing,
  isLoading = false,
  className = '',
  sticky = true,
  mobileDrawer = true,
  onCheckout,
  showCheckoutButton = true,
}: PricingSidebarProps): JSX.Element {
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Detect mobile viewport
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);

    return () => {
      window.removeEventListener('resize', checkMobile);
    };
  }, []);

  // Calculate derived values
  const derivedValues = useMemo(() => {
    if (!pricing) {
      return {
        hasOptions: false,
        hasPackages: false,
        hasDiscount: false,
        totalBeforeTax: 0,
        savingsAmount: 0,
        taxPercentage: 0,
      };
    }

    const totalBeforeTax = pricing.subtotal;
    const savingsAmount = Math.abs(pricing.packagesDiscount);
    const taxPercentage = pricing.taxRate * 100;

    return {
      hasOptions: pricing.itemizedOptions.length > 0,
      hasPackages: pricing.itemizedPackages.length > 0,
      hasDiscount: pricing.packagesDiscount < 0,
      totalBeforeTax,
      savingsAmount,
      taxPercentage,
    };
  }, [pricing]);

  // Handle checkout action
  const handleCheckout = () => {
    if (onCheckout) {
      onCheckout();
    }
  };

  // Toggle mobile drawer
  const toggleMobileDrawer = () => {
    setIsMobileDrawerOpen((prev) => !prev);
  };

  // Render loading state
  if (isLoading) {
    return (
      <div
        className={`bg-white rounded-lg shadow-lg p-6 ${sticky ? 'sticky top-4' : ''} ${className}`}
        role="status"
        aria-live="polite"
        aria-label="Loading pricing information"
      >
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-3/4" />
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded" />
            <div className="h-4 bg-gray-200 rounded w-5/6" />
            <div className="h-4 bg-gray-200 rounded w-4/6" />
          </div>
          <div className="border-t border-gray-200 pt-4">
            <div className="h-8 bg-gray-200 rounded" />
          </div>
        </div>
      </div>
    );
  }

  // Render empty state
  if (!pricing) {
    return (
      <div
        className={`bg-white rounded-lg shadow-lg p-6 ${sticky ? 'sticky top-4' : ''} ${className}`}
        role="status"
        aria-live="polite"
      >
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Pricing Summary</h2>
        <p className="text-gray-500 text-center py-8">
          Select options to see pricing details
        </p>
      </div>
    );
  }

  // Main pricing content
  const pricingContent = (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900">Pricing Summary</h2>
        {isMobile && mobileDrawer && (
          <button
            type="button"
            onClick={toggleMobileDrawer}
            className="md:hidden text-gray-500 hover:text-gray-700"
            aria-label="Close pricing summary"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Base Price */}
      <div className="flex items-center justify-between py-2">
        <span className="text-gray-700 font-medium">Base Price</span>
        <span className="text-gray-900 font-semibold">
          {formatCurrency(pricing.basePrice)}
        </span>
      </div>

      {/* Options */}
      {derivedValues.hasOptions && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm font-medium text-gray-700">
            <span>Selected Options</span>
            <span>{formatCurrency(pricing.optionsPrice)}</span>
          </div>
          <div className="pl-4 space-y-1">
            {pricing.itemizedOptions.map((option) => (
              <div
                key={option.id}
                className="flex items-center justify-between text-sm text-gray-600"
              >
                <span className="truncate pr-2">{option.name}</span>
                <span className="whitespace-nowrap">
                  {formatCurrency(option.price)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Packages */}
      {derivedValues.hasPackages && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm font-medium text-gray-700">
            <span>Packages</span>
            <span>{formatCurrency(pricing.packagesPrice)}</span>
          </div>
          <div className="pl-4 space-y-1">
            {pricing.itemizedPackages.map((pkg) => (
              <div key={pkg.id} className="space-y-1">
                <div className="flex items-center justify-between text-sm text-gray-600">
                  <span className="truncate pr-2">{pkg.name}</span>
                  <span className="whitespace-nowrap">
                    {formatCurrency(pkg.price)}
                  </span>
                </div>
                {pkg.discount > 0 && (
                  <div className="flex items-center justify-between text-xs text-green-600">
                    <span className="pl-2">Package Discount</span>
                    <span>-{formatCurrency(pkg.discount)}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Package Discount Summary */}
      {derivedValues.hasDiscount && (
        <div className="flex items-center justify-between py-2 text-green-600">
          <span className="font-medium">Total Package Savings</span>
          <span className="font-semibold">
            -{formatCurrency(derivedValues.savingsAmount)}
          </span>
        </div>
      )}

      {/* Subtotal */}
      <div className="border-t border-gray-200 pt-3">
        <div className="flex items-center justify-between py-2">
          <span className="text-gray-700 font-medium">Subtotal</span>
          <span className="text-gray-900 font-semibold">
            {formatCurrency(pricing.subtotal)}
          </span>
        </div>
      </div>

      {/* Tax */}
      <div className="flex items-center justify-between py-2 text-sm">
        <span className="text-gray-600">
          Tax ({derivedValues.taxPercentage.toFixed(2)}%)
        </span>
        <span className="text-gray-900">{formatCurrency(pricing.taxAmount)}</span>
      </div>

      {/* Destination Charge */}
      <div className="flex items-center justify-between py-2 text-sm">
        <span className="text-gray-600">Destination Charge</span>
        <span className="text-gray-900">
          {formatCurrency(pricing.destinationCharge)}
        </span>
      </div>

      {/* Total */}
      <div className="border-t-2 border-gray-300 pt-4">
        <div className="flex items-center justify-between">
          <span className="text-lg font-bold text-gray-900">Total Price</span>
          <span className="text-2xl font-bold text-blue-600">
            {formatCurrency(pricing.total)}
          </span>
        </div>
      </div>

      {/* Visual Progress Bar */}
      <div className="pt-2">
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-600 transition-all duration-300"
            style={{
              width: `${calculatePercentage(pricing.subtotal, pricing.total)}%`,
            }}
            role="progressbar"
            aria-valuenow={calculatePercentage(pricing.subtotal, pricing.total)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Price breakdown visualization"
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>Base + Options</span>
          <span>Total with Tax & Fees</span>
        </div>
      </div>

      {/* Checkout Button */}
      {showCheckoutButton && onCheckout && (
        <button
          type="button"
          onClick={handleCheckout}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          aria-label="Proceed to checkout"
        >
          Continue to Checkout
        </button>
      )}

      {/* Disclaimer */}
      <p className="text-xs text-gray-500 text-center pt-2">
        * Prices are estimates and may vary based on location and availability
      </p>
    </div>
  );

  // Mobile drawer implementation
  if (isMobile && mobileDrawer) {
    return (
      <>
        {/* Mobile Trigger Button */}
        <button
          type="button"
          onClick={toggleMobileDrawer}
          className="md:hidden fixed bottom-4 right-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-full shadow-lg z-40 flex items-center space-x-2"
          aria-label="View pricing summary"
          aria-expanded={isMobileDrawerOpen}
        >
          <span>{formatCurrency(pricing.total)}</span>
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>

        {/* Mobile Drawer Overlay */}
        {isMobileDrawerOpen && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
            onClick={toggleMobileDrawer}
            role="button"
            tabIndex={0}
            aria-label="Close pricing summary"
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                toggleMobileDrawer();
              }
            }}
          />
        )}

        {/* Mobile Drawer */}
        <div
          className={`fixed bottom-0 left-0 right-0 bg-white rounded-t-2xl shadow-2xl z-50 transform transition-transform duration-300 md:hidden ${
            isMobileDrawerOpen ? 'translate-y-0' : 'translate-y-full'
          } ${className}`}
          role="dialog"
          aria-modal="true"
          aria-label="Pricing summary"
        >
          <div className="max-h-[80vh] overflow-y-auto p-6">{pricingContent}</div>
        </div>
      </>
    );
  }

  // Desktop sticky sidebar
  return (
    <div
      className={`bg-white rounded-lg shadow-lg p-6 ${sticky ? 'sticky top-4' : ''} ${className}`}
      role="complementary"
      aria-label="Pricing summary"
    >
      {pricingContent}
    </div>
  );
}