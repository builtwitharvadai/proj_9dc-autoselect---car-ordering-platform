import type { Vehicle, VehicleSpecifications } from '../../types/vehicle';

/**
 * Vehicle overview component props
 */
interface VehicleOverviewProps {
  readonly vehicle: Vehicle;
  readonly onConfigure?: () => void;
  readonly onContactDealer?: () => void;
  readonly className?: string;
  readonly showActions?: boolean;
}

/**
 * Format currency value
 */
function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format fuel economy value
 */
function formatFuelEconomy(city: number, highway: number, combined: number): string {
  return `${city}/${highway}/${combined} MPG (City/Hwy/Combined)`;
}

/**
 * Format transmission type for display
 */
function formatTransmission(transmission: string): string {
  const transmissionMap: Record<string, string> = {
    automatic: 'Automatic',
    manual: 'Manual',
    cvt: 'CVT',
    'dual-clutch': 'Dual-Clutch',
  };
  return transmissionMap[transmission] ?? transmission;
}

/**
 * Format drivetrain type for display
 */
function formatDrivetrain(drivetrain: string): string {
  const drivetrainMap: Record<string, string> = {
    fwd: 'Front-Wheel Drive',
    rwd: 'Rear-Wheel Drive',
    awd: 'All-Wheel Drive',
    '4wd': '4-Wheel Drive',
  };
  return drivetrainMap[drivetrain] ?? drivetrain;
}

/**
 * Format fuel type for display
 */
function formatFuelType(fuelType: string): string {
  const fuelTypeMap: Record<string, string> = {
    gasoline: 'Gasoline',
    diesel: 'Diesel',
    electric: 'Electric',
    hybrid: 'Hybrid',
    'plug-in-hybrid': 'Plug-in Hybrid',
  };
  return fuelTypeMap[fuelType] ?? fuelType;
}

/**
 * Calculate savings if MSRP differs from price
 */
function calculateSavings(msrp: number, price: number): number | null {
  if (msrp <= price) {
    return null;
  }
  return msrp - price;
}

/**
 * Key specification item component
 */
interface SpecItemProps {
  readonly label: string;
  readonly value: string;
  readonly icon?: string;
}

function SpecItem({ label, value, icon }: SpecItemProps): JSX.Element {
  return (
    <div className="flex items-start gap-3">
      {icon && (
        <span className="text-2xl text-blue-600" aria-hidden="true">
          {icon}
        </span>
      )}
      <div className="flex-1">
        <dt className="text-sm font-medium text-gray-500">{label}</dt>
        <dd className="mt-1 text-base font-semibold text-gray-900">{value}</dd>
      </div>
    </div>
  );
}

/**
 * VehicleOverview Component
 * 
 * Displays vehicle name, key specifications, pricing, and primary call-to-action buttons.
 * 
 * Features:
 * - Vehicle name with year, make, model, and trim
 * - Key specifications (engine, transmission, fuel economy)
 * - Pricing with MSRP and savings calculation
 * - Configure and contact dealer action buttons
 * - Responsive design
 * - Accessibility compliant
 */
export default function VehicleOverview({
  vehicle,
  onConfigure,
  onContactDealer,
  className = '',
  showActions = true,
}: VehicleOverviewProps): JSX.Element {
  const { year, make, model, trim, msrp, price, specifications } = vehicle;
  const savings = calculateSavings(msrp, price);

  const vehicleName = trim
    ? `${year} ${make} ${model} ${trim}`
    : `${year} ${make} ${model}`;

  const keySpecs: SpecItemProps[] = [
    {
      label: 'Engine',
      value: specifications.engine,
      icon: '⚙️',
    },
    {
      label: 'Transmission',
      value: formatTransmission(specifications.transmission),
      icon: '🔧',
    },
    {
      label: 'Drivetrain',
      value: formatDrivetrain(specifications.drivetrain),
      icon: '🚗',
    },
    {
      label: 'Fuel Type',
      value: formatFuelType(specifications.fuelType),
      icon: '⛽',
    },
    {
      label: 'Fuel Economy',
      value: formatFuelEconomy(
        specifications.fuelEconomy.city,
        specifications.fuelEconomy.highway,
        specifications.fuelEconomy.combined
      ),
      icon: '📊',
    },
    {
      label: 'Horsepower',
      value: `${specifications.horsepower} HP`,
      icon: '💪',
    },
  ];

  return (
    <div
      className={`rounded-lg bg-white shadow-md ${className}`}
      role="region"
      aria-label="Vehicle overview"
    >
      <div className="p-6 space-y-6">
        {/* Vehicle Name */}
        <div className="border-b border-gray-200 pb-4">
          <h1 className="text-3xl font-bold text-gray-900 sm:text-4xl">
            {vehicleName}
          </h1>
          {vehicle.description && (
            <p className="mt-2 text-base text-gray-600">
              {vehicle.description}
            </p>
          )}
        </div>

        {/* Key Specifications */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Key Specifications
          </h2>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {keySpecs.map((spec) => (
              <SpecItem
                key={spec.label}
                label={spec.label}
                value={spec.value}
                icon={spec.icon}
              />
            ))}
          </dl>
        </div>

        {/* Pricing */}
        <div className="border-t border-gray-200 pt-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Pricing
          </h2>
          <div className="space-y-3">
            {msrp !== price && (
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-500">MSRP</span>
                <span className="text-lg font-medium text-gray-500 line-through">
                  {formatCurrency(msrp)}
                </span>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-base font-semibold text-gray-900">
                Your Price
              </span>
              <span className="text-3xl font-bold text-blue-600">
                {formatCurrency(price)}
              </span>
            </div>
            {savings && (
              <div className="flex items-center justify-between rounded-md bg-green-50 px-4 py-2">
                <span className="text-sm font-medium text-green-800">
                  You Save
                </span>
                <span className="text-lg font-bold text-green-800">
                  {formatCurrency(savings)}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        {showActions && (
          <div className="border-t border-gray-200 pt-6">
            <div className="flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={onConfigure}
                className="flex-1 inline-flex items-center justify-center rounded-md bg-blue-600 px-6 py-3 text-base font-semibold text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors duration-200"
                aria-label="Configure this vehicle"
              >
                <svg
                  className="mr-2 h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
                Configure Vehicle
              </button>
              <button
                type="button"
                onClick={onContactDealer}
                className="flex-1 inline-flex items-center justify-center rounded-md bg-white px-6 py-3 text-base font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors duration-200"
                aria-label="Contact dealer about this vehicle"
              >
                <svg
                  className="mr-2 h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
                Contact Dealer
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}