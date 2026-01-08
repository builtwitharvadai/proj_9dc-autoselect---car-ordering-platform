/**
 * VehicleCard Component
 * 
 * Reusable vehicle card component displaying vehicle information with image,
 * specifications, pricing, and call-to-action buttons. Implements responsive
 * design and accessibility features.
 */

import { memo } from 'react';
import type { Vehicle } from '../../types/vehicle';
import { useComparison } from '../../hooks/useComparison';

/**
 * Props for VehicleCard component
 */
interface VehicleCardProps {
  readonly vehicle: Vehicle;
  readonly onViewDetails?: (vehicleId: string) => void;
  readonly onAddToCart?: (vehicleId: string) => void;
  readonly className?: string;
  readonly showInventory?: boolean;
  readonly priority?: boolean;
}

/**
 * Formats price as USD currency
 */
function formatPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(price);
}

/**
 * Generates Unsplash image URL for vehicle
 */
function getVehicleImageUrl(vehicle: Vehicle): string {
  if (vehicle.imageUrl && vehicle.imageUrl.startsWith('http')) {
    return vehicle.imageUrl;
  }

  const query = encodeURIComponent(`${vehicle.year} ${vehicle.make} ${vehicle.model}`);
  return `https://source.unsplash.com/800x600/?${query},car,automobile`;
}

/**
 * Gets availability badge styling
 */
function getAvailabilityBadgeClass(availability: Vehicle['availability']): string {
  const baseClasses = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium';
  
  switch (availability) {
    case 'available':
      return `${baseClasses} bg-green-100 text-green-800`;
    case 'reserved':
      return `${baseClasses} bg-yellow-100 text-yellow-800`;
    case 'sold':
      return `${baseClasses} bg-red-100 text-red-800`;
    case 'unavailable':
      return `${baseClasses} bg-gray-100 text-gray-800`;
    default:
      return `${baseClasses} bg-gray-100 text-gray-800`;
  }
}

/**
 * Gets availability badge text
 */
function getAvailabilityText(availability: Vehicle['availability']): string {
  switch (availability) {
    case 'available':
      return 'Available';
    case 'reserved':
      return 'Reserved';
    case 'sold':
      return 'Sold';
    case 'unavailable':
      return 'Unavailable';
    default:
      return 'Unknown';
  }
}

/**
 * VehicleCard component displaying vehicle information
 */
function VehicleCard({
  vehicle,
  onViewDetails,
  onAddToCart,
  className = '',
  showInventory = false,
  priority = false,
}: VehicleCardProps): JSX.Element {
  const imageUrl = getVehicleImageUrl(vehicle);
  const isAvailable = vehicle.availability === 'available' && !vehicle.isDeleted;
  const hasDiscount = vehicle.price < vehicle.msrp;
  const discountPercentage = hasDiscount
    ? Math.round(((vehicle.msrp - vehicle.price) / vehicle.msrp) * 100)
    : 0;

  const {
    toggleVehicle,
    isVehicleInComparison,
    canAddMore,
    count,
    maxVehicles,
  } = useComparison();

  const isInComparison = isVehicleInComparison(vehicle.id);
  const canToggleComparison = isInComparison || canAddMore;

  const handleViewDetails = (): void => {
    if (onViewDetails) {
      onViewDetails(vehicle.id);
    }
  };

  const handleAddToCart = (): void => {
    if (onAddToCart && isAvailable) {
      onAddToCart(vehicle.id);
    }
  };

  const handleToggleComparison = (): void => {
    if (canToggleComparison) {
      toggleVehicle(vehicle);
    }
  };

  const handleKeyDownViewDetails = (event: React.KeyboardEvent<HTMLButtonElement>): void => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleViewDetails();
    }
  };

  const handleKeyDownAddToCart = (event: React.KeyboardEvent<HTMLButtonElement>): void => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleAddToCart();
    }
  };

  const handleKeyDownToggleComparison = (event: React.KeyboardEvent<HTMLButtonElement>): void => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleToggleComparison();
    }
  };

  return (
    <article
      className={`bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-shadow duration-300 flex flex-col h-full ${className}`}
      aria-label={`${vehicle.year} ${vehicle.make} ${vehicle.model}`}
    >
      {/* Vehicle Image */}
      <div className="relative aspect-[4/3] overflow-hidden bg-gray-200">
        <img
          src={imageUrl}
          alt={`${vehicle.year} ${vehicle.make} ${vehicle.model}`}
          className="w-full h-full object-cover"
          loading={priority ? 'eager' : 'lazy'}
          onError={(e): void => {
            const target = e.target as HTMLImageElement;
            target.src = `https://via.placeholder.com/800x600/e5e7eb/6b7280?text=${encodeURIComponent(`${vehicle.make} ${vehicle.model}`)}`;
          }}
        />
        
        {/* Availability Badge */}
        <div className="absolute top-3 right-3">
          <span className={getAvailabilityBadgeClass(vehicle.availability)}>
            {getAvailabilityText(vehicle.availability)}
          </span>
        </div>

        {/* Discount Badge */}
        {hasDiscount && (
          <div className="absolute top-3 left-3">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-600 text-white">
              {discountPercentage}% OFF
            </span>
          </div>
        )}

        {/* Comparison Badge */}
        {isInComparison && (
          <div className="absolute bottom-3 left-3">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-600 text-white">
              <svg
                className="w-3 h-3 mr-1"
                fill="currentColor"
                viewBox="0 0 20 20"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
              In Comparison
            </span>
          </div>
        )}
      </div>

      {/* Vehicle Information */}
      <div className="flex-1 flex flex-col p-4 sm:p-5">
        {/* Title */}
        <div className="mb-3">
          <h3 className="text-lg sm:text-xl font-bold text-gray-900 mb-1">
            {vehicle.year} {vehicle.make} {vehicle.model}
          </h3>
          {vehicle.trim && (
            <p className="text-sm text-gray-600">{vehicle.trim}</p>
          )}
        </div>

        {/* Key Specifications */}
        <div className="mb-4 space-y-2">
          <div className="flex items-center text-sm text-gray-700">
            <svg
              className="w-4 h-4 mr-2 text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
            <span>{vehicle.specifications.horsepower} HP</span>
            <span className="mx-2 text-gray-400">•</span>
            <span className="capitalize">{vehicle.specifications.transmission}</span>
          </div>

          <div className="flex items-center text-sm text-gray-700">
            <svg
              className="w-4 h-4 mr-2 text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="capitalize">{vehicle.specifications.fuelType}</span>
            <span className="mx-2 text-gray-400">•</span>
            <span>{vehicle.specifications.fuelEconomy.combined} MPG</span>
          </div>

          <div className="flex items-center text-sm text-gray-700">
            <svg
              className="w-4 h-4 mr-2 text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
            <span>{vehicle.specifications.seatingCapacity} Seats</span>
            <span className="mx-2 text-gray-400">•</span>
            <span className="capitalize">{vehicle.bodyStyle}</span>
          </div>
        </div>

        {/* Inventory Information */}
        {showInventory && vehicle.inventory && (
          <div className="mb-4 p-3 bg-gray-50 rounded-md">
            <p className="text-xs text-gray-600 mb-1">Inventory</p>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-700">
                Available: {vehicle.inventory.availableQuantity} / {vehicle.inventory.quantity}
              </span>
              <span className="text-gray-600">{vehicle.inventory.location}</span>
            </div>
          </div>
        )}

        {/* Comparison Count Indicator */}
        {count > 0 && (
          <div className="mb-4 p-2 bg-blue-50 rounded-md border border-blue-200">
            <p className="text-xs text-blue-800 text-center">
              {count} of {maxVehicles} vehicles selected for comparison
            </p>
          </div>
        )}

        {/* Pricing */}
        <div className="mt-auto pt-4 border-t border-gray-200">
          <div className="flex items-baseline justify-between mb-3">
            <div>
              {hasDiscount && (
                <p className="text-sm text-gray-500 line-through">
                  MSRP: {formatPrice(vehicle.msrp)}
                </p>
              )}
              <p className="text-2xl font-bold text-gray-900">
                {formatPrice(vehicle.price)}
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col gap-2">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleViewDetails}
                onKeyDown={handleKeyDownViewDetails}
                className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
                aria-label={`View details for ${vehicle.year} ${vehicle.make} ${vehicle.model}`}
              >
                View Details
              </button>
              
              <button
                type="button"
                onClick={handleAddToCart}
                onKeyDown={handleKeyDownAddToCart}
                disabled={!isAvailable}
                className={`flex-1 px-4 py-2 text-sm font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors duration-200 ${
                  isAvailable
                    ? 'text-white bg-blue-600 hover:bg-blue-700 focus:ring-blue-500'
                    : 'text-gray-400 bg-gray-200 cursor-not-allowed'
                }`}
                aria-label={
                  isAvailable
                    ? `Add ${vehicle.year} ${vehicle.make} ${vehicle.model} to cart`
                    : `${vehicle.year} ${vehicle.make} ${vehicle.model} is not available`
                }
                aria-disabled={!isAvailable}
              >
                {isAvailable ? 'Add to Cart' : 'Unavailable'}
              </button>
            </div>

            {/* Add to Compare Button */}
            <button
              type="button"
              onClick={handleToggleComparison}
              onKeyDown={handleKeyDownToggleComparison}
              disabled={!canToggleComparison}
              className={`w-full px-4 py-2 text-sm font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors duration-200 ${
                isInComparison
                  ? 'text-blue-700 bg-blue-50 border border-blue-300 hover:bg-blue-100 focus:ring-blue-500'
                  : canAddMore
                    ? 'text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 focus:ring-blue-500'
                    : 'text-gray-400 bg-gray-100 border border-gray-200 cursor-not-allowed'
              }`}
              aria-label={
                isInComparison
                  ? `Remove ${vehicle.year} ${vehicle.make} ${vehicle.model} from comparison`
                  : canAddMore
                    ? `Add ${vehicle.year} ${vehicle.make} ${vehicle.model} to comparison`
                    : 'Maximum vehicles selected for comparison'
              }
              aria-disabled={!canToggleComparison}
            >
              <span className="flex items-center justify-center">
                {isInComparison ? (
                  <>
                    <svg
                      className="w-4 h-4 mr-1.5"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                    In Comparison
                  </>
                ) : (
                  <>
                    <svg
                      className="w-4 h-4 mr-1.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 4v16m8-8H4"
                      />
                    </svg>
                    Add to Compare
                  </>
                )}
              </span>
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}

/**
 * Memoized VehicleCard component for performance optimization
 */
export default memo(VehicleCard);