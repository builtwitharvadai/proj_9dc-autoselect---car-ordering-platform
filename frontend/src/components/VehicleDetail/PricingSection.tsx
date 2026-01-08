import React from 'react';
import type { Vehicle } from '../../types/vehicle';

/**
 * Props for the PricingSection component
 */
interface PricingSectionProps {
  readonly vehicle: Vehicle;
  readonly className?: string;
}

/**
 * Incentive information structure
 */
interface Incentive {
  readonly id: string;
  readonly name: string;
  readonly amount: number;
  readonly description: string;
  readonly expiresAt?: string;
}

/**
 * Financing option structure
 */
interface FinancingOption {
  readonly id: string;
  readonly name: string;
  readonly apr: number;
  readonly termMonths: number;
  readonly monthlyPayment: number;
  readonly downPayment: number;
}

/**
 * PricingSection Component
 * 
 * Displays comprehensive pricing information including MSRP, available incentives,
 * financing options, and total pricing breakdown with disclaimer text.
 * 
 * Features:
 * - MSRP and current price display
 * - Available incentives with expiration dates
 * - Multiple financing options
 * - Total pricing breakdown
 * - Legal disclaimers
 * - Responsive design
 * - Accessibility compliant
 */
export default function PricingSection({
  vehicle,
  className = '',
}: PricingSectionProps): JSX.Element {
  // Mock incentives data - in production, this would come from API
  const incentives: readonly Incentive[] = React.useMemo(() => {
    const baseIncentives: Incentive[] = [];

    // Add manufacturer rebate if price is less than MSRP
    if (vehicle.price < vehicle.msrp) {
      const discount = vehicle.msrp - vehicle.price;
      baseIncentives.push({
        id: 'manufacturer-rebate',
        name: 'Manufacturer Rebate',
        amount: discount,
        description: 'Limited time manufacturer incentive',
        expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      });
    }

    // Add loyalty bonus for returning customers
    baseIncentives.push({
      id: 'loyalty-bonus',
      name: 'Loyalty Bonus',
      amount: 500,
      description: 'For returning customers',
    });

    // Add financing incentive
    baseIncentives.push({
      id: 'financing-incentive',
      name: 'Financing Incentive',
      amount: 1000,
      description: 'When financing through our preferred lenders',
      expiresAt: new Date(Date.now() + 60 * 24 * 60 * 60 * 1000).toISOString(),
    });

    return baseIncentives;
  }, [vehicle.msrp, vehicle.price]);

  // Calculate total available incentives
  const totalIncentives = React.useMemo(
    () => incentives.reduce((sum, incentive) => sum + incentive.amount, 0),
    [incentives]
  );

  // Mock financing options - in production, this would come from API
  const financingOptions: readonly FinancingOption[] = React.useMemo(() => {
    const price = vehicle.price;
    const downPayment = price * 0.2; // 20% down payment

    return [
      {
        id: 'option-36',
        name: '36 Month Financing',
        apr: 3.99,
        termMonths: 36,
        monthlyPayment: calculateMonthlyPayment(price - downPayment, 3.99, 36),
        downPayment,
      },
      {
        id: 'option-48',
        name: '48 Month Financing',
        apr: 4.49,
        termMonths: 48,
        monthlyPayment: calculateMonthlyPayment(price - downPayment, 4.49, 48),
        downPayment,
      },
      {
        id: 'option-60',
        name: '60 Month Financing',
        apr: 4.99,
        termMonths: 60,
        monthlyPayment: calculateMonthlyPayment(price - downPayment, 4.99, 60),
        downPayment,
      },
      {
        id: 'option-72',
        name: '72 Month Financing',
        apr: 5.49,
        termMonths: 72,
        monthlyPayment: calculateMonthlyPayment(price - downPayment, 5.49, 72),
        downPayment,
      },
    ];
  }, [vehicle.price]);

  // Calculate final price after incentives
  const finalPrice = React.useMemo(
    () => Math.max(0, vehicle.price - totalIncentives),
    [vehicle.price, totalIncentives]
  );

  // Format currency
  const formatCurrency = React.useCallback((amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  }, []);

  // Format date
  const formatDate = React.useCallback((dateString: string): string => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    }).format(new Date(dateString));
  }, []);

  return (
    <section
      className={`pricing-section bg-white rounded-lg shadow-md p-6 ${className}`}
      aria-labelledby="pricing-heading"
    >
      <h2 id="pricing-heading" className="text-2xl font-bold text-gray-900 mb-6">
        Pricing & Financing
      </h2>

      {/* MSRP and Current Price */}
      <div className="pricing-overview mb-8 pb-6 border-b border-gray-200">
        <div className="flex justify-between items-center mb-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">MSRP</p>
            <p className="text-2xl font-semibold text-gray-900">
              {formatCurrency(vehicle.msrp)}
            </p>
          </div>
          {vehicle.price < vehicle.msrp && (
            <div className="text-right">
              <p className="text-sm text-gray-600 mb-1">Current Price</p>
              <p className="text-2xl font-bold text-green-600">
                {formatCurrency(vehicle.price)}
              </p>
            </div>
          )}
        </div>
        {vehicle.price < vehicle.msrp && (
          <div className="bg-green-50 border border-green-200 rounded-md p-3">
            <p className="text-sm font-medium text-green-800">
              Save {formatCurrency(vehicle.msrp - vehicle.price)} off MSRP
            </p>
          </div>
        )}
      </div>

      {/* Available Incentives */}
      {incentives.length > 0 && (
        <div className="incentives-section mb-8 pb-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Available Incentives
          </h3>
          <div className="space-y-3">
            {incentives.map((incentive) => (
              <div
                key={incentive.id}
                className="flex justify-between items-start p-4 bg-blue-50 border border-blue-200 rounded-md"
              >
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{incentive.name}</p>
                  <p className="text-sm text-gray-600 mt-1">{incentive.description}</p>
                  {incentive.expiresAt && (
                    <p className="text-xs text-gray-500 mt-1">
                      Expires: {formatDate(incentive.expiresAt)}
                    </p>
                  )}
                </div>
                <p className="font-bold text-blue-600 ml-4">
                  -{formatCurrency(incentive.amount)}
                </p>
              </div>
            ))}
          </div>
          <div className="mt-4 flex justify-between items-center p-3 bg-blue-100 rounded-md">
            <p className="font-semibold text-gray-900">Total Incentives</p>
            <p className="font-bold text-blue-700">
              -{formatCurrency(totalIncentives)}
            </p>
          </div>
        </div>
      )}

      {/* Financing Options */}
      <div className="financing-section mb-8 pb-6 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Financing Options
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {financingOptions.map((option) => (
            <div
              key={option.id}
              className="p-4 border border-gray-300 rounded-md hover:border-blue-500 hover:shadow-md transition-all"
            >
              <p className="font-semibold text-gray-900 mb-2">{option.name}</p>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">APR:</span>
                  <span className="font-medium text-gray-900">{option.apr}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Down Payment:</span>
                  <span className="font-medium text-gray-900">
                    {formatCurrency(option.downPayment)}
                  </span>
                </div>
                <div className="flex justify-between pt-2 border-t border-gray-200">
                  <span className="text-gray-900 font-medium">Monthly Payment:</span>
                  <span className="font-bold text-blue-600">
                    {formatCurrency(option.monthlyPayment)}/mo
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-4">
          * Financing options are subject to credit approval. Rates and terms may vary.
        </p>
      </div>

      {/* Total Pricing Breakdown */}
      <div className="pricing-breakdown mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Total Pricing Breakdown
        </h3>
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-gray-700">Vehicle Price</span>
            <span className="font-medium text-gray-900">
              {formatCurrency(vehicle.price)}
            </span>
          </div>
          {totalIncentives > 0 && (
            <div className="flex justify-between items-center text-green-600">
              <span>Total Incentives</span>
              <span className="font-medium">-{formatCurrency(totalIncentives)}</span>
            </div>
          )}
          <div className="flex justify-between items-center pt-3 border-t-2 border-gray-300">
            <span className="text-lg font-bold text-gray-900">Final Price</span>
            <span className="text-2xl font-bold text-blue-600">
              {formatCurrency(finalPrice)}
            </span>
          </div>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="disclaimer bg-gray-50 border border-gray-200 rounded-md p-4">
        <h4 className="text-sm font-semibold text-gray-900 mb-2">
          Important Pricing Information
        </h4>
        <div className="text-xs text-gray-600 space-y-2">
          <p>
            * Prices shown are manufacturer's suggested retail price (MSRP) and do not
            include taxes, title, license, registration fees, destination charges, or
            optional equipment.
          </p>
          <p>
            * Incentives and rebates are subject to eligibility requirements and may
            vary by region. Not all customers will qualify for all incentives.
          </p>
          <p>
            * Financing options are estimates based on standard credit approval. Actual
            rates and terms may vary based on creditworthiness and lender requirements.
          </p>
          <p>
            * Final pricing may vary based on dealer location, market conditions, and
            vehicle availability. Contact your local dealer for exact pricing.
          </p>
          <p>
            * Incentive expiration dates are subject to change without notice. Please
            verify current offers with your dealer.
          </p>
          <p>
            * Monthly payment calculations assume 20% down payment and do not include
            taxes, fees, or insurance.
          </p>
        </div>
      </div>
    </section>
  );
}

/**
 * Calculate monthly payment for a loan
 * 
 * @param principal - Loan amount
 * @param annualRate - Annual interest rate (percentage)
 * @param months - Loan term in months
 * @returns Monthly payment amount
 */
function calculateMonthlyPayment(
  principal: number,
  annualRate: number,
  months: number
): number {
  const monthlyRate = annualRate / 100 / 12;
  const payment =
    (principal * monthlyRate * Math.pow(1 + monthlyRate, months)) /
    (Math.pow(1 + monthlyRate, months) - 1);
  return Math.round(payment * 100) / 100;
}