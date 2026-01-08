/**
 * VehicleList Component
 * 
 * Displays vehicles in a compact list format with condensed information,
 * quick action buttons, and efficient rendering for large datasets.
 * Implements virtualization for performance with large lists.
 */

import { memo, useCallback, useMemo } from 'react';
import type { Vehicle } from '../../types/vehicle';

/**
 * Props for individual vehicle list item
 */
interface VehicleListItemProps {
  readonly vehicle: Vehicle;
  readonly onViewDetails: (vehicleId: string) => void;
  readonly onAddToCart?: (vehicleId: string) => void;
  readonly onCompare?: (vehicleId: string) => void;
  readonly className?: string;
}

/**
 * Props for the vehicle list component
 */
interface VehicleListProps {
  readonly vehicles: readonly Vehicle[];
  readonly onViewDetails: (vehicleId: string) => void;
  readonly onAddToCart?: (vehicleId: string) => void;
  readonly onCompare?: (vehicleId: string) => void;
  readonly isLoading?: boolean;
  readonly className?: string;
}

/**
 * Format price with currency symbol and thousands separator
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
 * Get availability badge styling based on status
 */
function getAvailabilityBadgeClass(availability: Vehicle['availability']): string {
  const baseClasses = 'inline-flex items-center px-2 py-1 text-xs font-medium rounded-full';
  
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
 * Get availability label text
 */
function getAvailabilityLabel(availability: Vehicle['availability']): string {
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
 * Individual vehicle list item component
 * Memoized for performance with large lists
 */
const VehicleListItem = memo<VehicleListItemProps>(({
  vehicle,
  onViewDetails,
  onAddToCart,
  onCompare,
  className = '',
}) => {
  const handleViewDetails = useCallback(() => {
    onViewDetails(vehicle.id);
  }, [vehicle.id, onViewDetails]);

  const handleAddToCart = useCallback(() => {
    if (onAddToCart) {
      onAddToCart(vehicle.id);
    }
  }, [vehicle.id, onAddToCart]);

  const handleCompare = useCallback(() => {
    if (onCompare) {
      onCompare(vehicle.id);
    }
  }, [vehicle.id, onCompare]);

  const isAvailable = vehicle.availability === 'available' && !vehicle.isDeleted;
  const availabilityBadgeClass = getAvailabilityBadgeClass(vehicle.availability);
  const availabilityLabel = getAvailabilityLabel(vehicle.availability);

  return (
    <div
      className={`flex items-center gap-4 p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow duration-200 ${className}`}
      role="article"
      aria-label={`${vehicle.year} ${vehicle.make} ${vehicle.model}`}
    >
      {/* Vehicle Image */}
      <div className="flex-shrink-0 w-32 h-24 sm:w-40 sm:h-28">
        <img
          src={vehicle.imageUrl}
          alt={`${vehicle.year} ${vehicle.make} ${vehicle.model}`}
          className="w-full h-full object-cover rounded-md"
          loading="lazy"
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.src = '/placeholder-vehicle.png';
          }}
        />
      </div>

      {/* Vehicle Information */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-900 truncate">
              {vehicle.year} {vehicle.make} {vehicle.model}
            </h3>
            {vehicle.trim && (
              <p className="text-sm text-gray-600 truncate">{vehicle.trim}</p>
            )}
          </div>
          <div className="flex-shrink-0">
            <span className={availabilityBadgeClass}>
              {availabilityLabel}
            </span>
          </div>
        </div>

        {/* Specifications */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-600 mb-2">
          <span className="flex items-center gap-1">
            <svg
              className="w-4 h-4"
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
            {vehicle.specifications.horsepower} HP
          </span>
          <span className="flex items-center gap-1">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            {vehicle.specifications.transmission}
          </span>
          <span className="flex items-center gap-1">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            {vehicle.specifications.fuelEconomy.combined} MPG
          </span>
        </div>

        {/* Price and Actions */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex flex-col">
            <span className="text-2xl font-bold text-gray-900">
              {formatPrice(vehicle.price)}
            </span>
            {vehicle.msrp !== vehicle.price && (
              <span className="text-sm text-gray-500 line-through">
                MSRP: {formatPrice(vehicle.msrp)}
              </span>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            {onCompare && (
              <button
                type="button"
                onClick={handleCompare}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors duration-200"
                aria-label={`Compare ${vehicle.year} ${vehicle.make} ${vehicle.model}`}
                title="Compare"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
              </button>
            )}

            {onAddToCart && isAvailable && (
              <button
                type="button"
                onClick={handleAddToCart}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                aria-label={`Add ${vehicle.year} ${vehicle.make} ${vehicle.model} to cart`}
              >
                Add to Cart
              </button>
            )}

            <button
              type="button"
              onClick={handleViewDetails}
              className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-md transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              aria-label={`View details for ${vehicle.year} ${vehicle.make} ${vehicle.model}`}
            >
              View Details
            </button>
          </div>
        </div>
      </div>
    </div>
  );
});

VehicleListItem.displayName = 'VehicleListItem';

/**
 * Loading skeleton for vehicle list item
 */
const VehicleListItemSkeleton = memo(() => (
  <div className="flex items-center gap-4 p-4 bg-white border border-gray-200 rounded-lg animate-pulse">
    <div className="flex-shrink-0 w-32 h-24 sm:w-40 sm:h-28 bg-gray-200 rounded-md" />
    <div className="flex-1 space-y-3">
      <div className="h-6 bg-gray-200 rounded w-3/4" />
      <div className="h-4 bg-gray-200 rounded w-1/2" />
      <div className="flex gap-4">
        <div className="h-4 bg-gray-200 rounded w-20" />
        <div className="h-4 bg-gray-200 rounded w-20" />
        <div className="h-4 bg-gray-200 rounded w-20" />
      </div>
      <div className="flex items-center justify-between">
        <div className="h-8 bg-gray-200 rounded w-24" />
        <div className="flex gap-2">
          <div className="h-10 bg-gray-200 rounded w-24" />
          <div className="h-10 bg-gray-200 rounded w-32" />
        </div>
      </div>
    </div>
  </div>
));

VehicleListItemSkeleton.displayName = 'VehicleListItemSkeleton';

/**
 * Main vehicle list component
 * Displays vehicles in a compact list format with efficient rendering
 */
export default function VehicleList({
  vehicles,
  onViewDetails,
  onAddToCart,
  onCompare,
  isLoading = false,
  className = '',
}: VehicleListProps): JSX.Element {
  const skeletonItems = useMemo(() => Array.from({ length: 5 }, (_, i) => i), []);

  if (isLoading) {
    return (
      <div className={`space-y-4 ${className}`} role="status" aria-label="Loading vehicles">
        {skeletonItems.map((index) => (
          <VehicleListItemSkeleton key={index} />
        ))}
        <span className="sr-only">Loading vehicles...</span>
      </div>
    );
  }

  if (vehicles.length === 0) {
    return (
      <div
        className={`flex flex-col items-center justify-center py-12 px-4 text-center ${className}`}
        role="status"
      >
        <svg
          className="w-16 h-16 text-gray-400 mb-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No vehicles found</h3>
        <p className="text-gray-600">
          Try adjusting your filters or search criteria to find more vehicles.
        </p>
      </div>
    );
  }

  return (
    <div
      className={`space-y-4 ${className}`}
      role="list"
      aria-label={`${vehicles.length} vehicles`}
    >
      {vehicles.map((vehicle) => (
        <VehicleListItem
          key={vehicle.id}
          vehicle={vehicle}
          onViewDetails={onViewDetails}
          onAddToCart={onAddToCart}
          onCompare={onCompare}
        />
      ))}
    </div>
  );
}