/**
 * VehicleGrid Component
 * 
 * Responsive grid view component for displaying vehicles with lazy-loaded images,
 * hover animations, skeleton loading states, and empty state handling.
 * 
 * Features:
 * - Responsive grid layout (1-4 columns based on viewport)
 * - Lazy-loaded images with blur-up effect
 * - Smooth hover animations and transitions
 * - Skeleton loading states during data fetch
 * - Empty state with helpful messaging
 * - Accessibility-compliant with ARIA labels
 * - Performance-optimized with React.memo
 */

import { memo, useState, useCallback, type JSX } from 'react';
import type { Vehicle } from '../../types/vehicle';

/**
 * Props for VehicleGrid component
 */
interface VehicleGridProps {
  readonly vehicles: readonly Vehicle[];
  readonly isLoading?: boolean;
  readonly onVehicleClick?: (vehicle: Vehicle) => void;
  readonly onVehicleHover?: (vehicleId: string | null) => void;
  readonly className?: string;
  readonly skeletonCount?: number;
}

/**
 * Props for VehicleCard component
 */
interface VehicleCardProps {
  readonly vehicle: Vehicle;
  readonly onClick?: (vehicle: Vehicle) => void;
  readonly onHover?: (vehicleId: string | null) => void;
}

/**
 * Format price as USD currency
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
  const baseClasses = 'px-2 py-1 text-xs font-semibold rounded-full';
  
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
 * VehicleCard Component
 * 
 * Individual vehicle card with image, details, and interactive states
 */
const VehicleCard = memo(function VehicleCard({
  vehicle,
  onClick,
  onHover,
}: VehicleCardProps): JSX.Element {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);

  const handleClick = useCallback(() => {
    if (onClick) {
      onClick(vehicle);
    }
  }, [onClick, vehicle]);

  const handleMouseEnter = useCallback(() => {
    if (onHover) {
      onHover(vehicle.id);
    }
  }, [onHover, vehicle.id]);

  const handleMouseLeave = useCallback(() => {
    if (onHover) {
      onHover(null);
    }
  }, [onHover]);

  const handleImageLoad = useCallback(() => {
    setImageLoaded(true);
  }, []);

  const handleImageError = useCallback(() => {
    setImageError(true);
    setImageLoaded(true);
  }, []);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        handleClick();
      }
    },
    [handleClick],
  );

  const vehicleTitle = `${vehicle.year} ${vehicle.make} ${vehicle.model}${vehicle.trim ? ` ${vehicle.trim}` : ''}`;
  const isAvailable = vehicle.availability === 'available' && !vehicle.isDeleted;

  return (
    <div
      className="group relative bg-white rounded-lg shadow-md overflow-hidden transition-all duration-300 hover:shadow-xl hover:-translate-y-1 cursor-pointer focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-2"
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-label={`View details for ${vehicleTitle}`}
    >
      {/* Image Container */}
      <div className="relative aspect-[4/3] bg-gray-200 overflow-hidden">
        {!imageLoaded && !imageError && (
          <div className="absolute inset-0 bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 animate-pulse" />
        )}
        
        {!imageError ? (
          <img
            src={vehicle.imageUrl}
            alt={vehicleTitle}
            loading="lazy"
            onLoad={handleImageLoad}
            onError={handleImageError}
            className={`w-full h-full object-cover transition-all duration-500 group-hover:scale-110 ${
              imageLoaded ? 'opacity-100' : 'opacity-0'
            }`}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
            <svg
              className="w-16 h-16 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
        )}

        {/* Availability Badge */}
        <div className="absolute top-3 right-3">
          <span className={getAvailabilityBadgeClass(vehicle.availability)}>
            {getAvailabilityLabel(vehicle.availability)}
          </span>
        </div>

        {/* Hover Overlay */}
        <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all duration-300" />
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Title */}
        <h3 className="text-lg font-semibold text-gray-900 mb-1 line-clamp-1 group-hover:text-blue-600 transition-colors">
          {vehicleTitle}
        </h3>

        {/* Body Style */}
        <p className="text-sm text-gray-600 mb-3 capitalize">{vehicle.bodyStyle}</p>

        {/* Specifications */}
        <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
          <div className="flex items-center gap-1">
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
            <span>{vehicle.specifications.horsepower} HP</span>
          </div>
          <div className="flex items-center gap-1">
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
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
            <span>{vehicle.specifications.seatingCapacity} Seats</span>
          </div>
        </div>

        {/* Fuel Economy */}
        <div className="text-sm text-gray-600 mb-4">
          <span className="font-medium">MPG:</span>{' '}
          {vehicle.specifications.fuelEconomy.city}/{vehicle.specifications.fuelEconomy.highway}{' '}
          (City/Hwy)
        </div>

        {/* Price */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-200">
          <div>
            <p className="text-2xl font-bold text-gray-900">{formatPrice(vehicle.price)}</p>
            {vehicle.msrp !== vehicle.price && (
              <p className="text-sm text-gray-500 line-through">{formatPrice(vehicle.msrp)}</p>
            )}
          </div>
          {isAvailable && (
            <button
              className="px-4 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              onClick={(e) => {
                e.stopPropagation();
                handleClick();
              }}
              aria-label={`View details for ${vehicleTitle}`}
            >
              View Details
            </button>
          )}
        </div>
      </div>
    </div>
  );
});

/**
 * SkeletonCard Component
 * 
 * Loading skeleton for vehicle cards
 */
const SkeletonCard = memo(function SkeletonCard(): JSX.Element {
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden animate-pulse">
      {/* Image Skeleton */}
      <div className="aspect-[4/3] bg-gray-300" />

      {/* Content Skeleton */}
      <div className="p-4">
        <div className="h-6 bg-gray-300 rounded mb-2 w-3/4" />
        <div className="h-4 bg-gray-300 rounded mb-3 w-1/2" />
        <div className="flex gap-4 mb-3">
          <div className="h-4 bg-gray-300 rounded w-16" />
          <div className="h-4 bg-gray-300 rounded w-16" />
        </div>
        <div className="h-4 bg-gray-300 rounded mb-4 w-2/3" />
        <div className="flex items-center justify-between pt-3 border-t border-gray-200">
          <div className="h-8 bg-gray-300 rounded w-24" />
          <div className="h-10 bg-gray-300 rounded w-28" />
        </div>
      </div>
    </div>
  );
});

/**
 * EmptyState Component
 * 
 * Displayed when no vehicles are available
 */
const EmptyState = memo(function EmptyState(): JSX.Element {
  return (
    <div className="col-span-full flex flex-col items-center justify-center py-16 px-4">
      <svg
        className="w-24 h-24 text-gray-400 mb-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0"
        />
      </svg>
      <h3 className="text-xl font-semibold text-gray-900 mb-2">No vehicles found</h3>
      <p className="text-gray-600 text-center max-w-md">
        We couldn't find any vehicles matching your criteria. Try adjusting your filters or search
        terms.
      </p>
    </div>
  );
});

/**
 * VehicleGrid Component
 * 
 * Main grid component for displaying vehicles
 */
export default function VehicleGrid({
  vehicles,
  isLoading = false,
  onVehicleClick,
  onVehicleHover,
  className = '',
  skeletonCount = 12,
}: VehicleGridProps): JSX.Element {
  // Show skeleton loading state
  if (isLoading) {
    return (
      <div
        className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 ${className}`}
        role="status"
        aria-label="Loading vehicles"
      >
        {Array.from({ length: skeletonCount }, (_, index) => (
          <SkeletonCard key={`skeleton-${index}`} />
        ))}
      </div>
    );
  }

  // Show empty state if no vehicles
  if (vehicles.length === 0) {
    return (
      <div className={className} role="status" aria-label="No vehicles available">
        <EmptyState />
      </div>
    );
  }

  // Render vehicle grid
  return (
    <div
      className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 ${className}`}
      role="list"
      aria-label={`${vehicles.length} vehicles available`}
    >
      {vehicles.map((vehicle) => (
        <div key={vehicle.id} role="listitem">
          <VehicleCard vehicle={vehicle} onClick={onVehicleClick} onHover={onVehicleHover} />
        </div>
      ))}
    </div>
  );
}