import { ShoppingCart } from 'lucide-react';
import { Link } from 'react-router-dom';

/**
 * EmptyCart Component
 * 
 * Displays an empty cart state with a call-to-action to browse vehicles.
 * Features responsive design with engaging visuals and clear messaging.
 * 
 * @component
 */

export interface EmptyCartProps {
  readonly className?: string;
  readonly onBrowseClick?: () => void;
}

export default function EmptyCart({
  className = '',
  onBrowseClick,
}: EmptyCartProps): JSX.Element {
  const handleBrowseClick = (): void => {
    if (onBrowseClick) {
      onBrowseClick();
    }
  };

  return (
    <div
      className={`flex flex-col items-center justify-center py-16 px-4 sm:px-6 lg:px-8 ${className}`}
      role="status"
      aria-live="polite"
      aria-label="Empty cart"
    >
      {/* Icon Container */}
      <div className="relative mb-8">
        {/* Background Circle */}
        <div className="absolute inset-0 bg-blue-50 rounded-full blur-2xl opacity-50" />
        
        {/* Icon */}
        <div className="relative bg-gradient-to-br from-blue-100 to-blue-50 rounded-full p-8 shadow-lg">
          <ShoppingCart
            className="w-24 h-24 text-blue-600"
            strokeWidth={1.5}
            aria-hidden="true"
          />
        </div>
      </div>

      {/* Content */}
      <div className="text-center max-w-md">
        {/* Heading */}
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-3">
          Your Cart is Empty
        </h2>

        {/* Description */}
        <p className="text-base sm:text-lg text-gray-600 mb-8 leading-relaxed">
          Start building your dream vehicle by exploring our extensive collection of cars, trucks, and SUVs.
        </p>

        {/* Call-to-Action Button */}
        <Link
          to="/browse"
          onClick={handleBrowseClick}
          className="inline-flex items-center justify-center gap-2 px-8 py-3 bg-blue-600 text-white font-semibold rounded-lg shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all duration-200 transform hover:scale-105 active:scale-95"
          aria-label="Browse vehicles"
        >
          <ShoppingCart className="w-5 h-5" aria-hidden="true" />
          <span>Browse Vehicles</span>
        </Link>

        {/* Additional Help Text */}
        <p className="mt-6 text-sm text-gray-500">
          Need help finding the perfect vehicle?{' '}
          <Link
            to="/contact"
            className="text-blue-600 hover:text-blue-700 font-medium underline focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded"
          >
            Contact our team
          </Link>
        </p>
      </div>

      {/* Feature Highlights */}
      <div className="mt-12 grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-3xl w-full">
        <div className="text-center p-4">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-100 rounded-full mb-3">
            <svg
              className="w-6 h-6 text-blue-600"
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
          </div>
          <h3 className="text-sm font-semibold text-gray-900 mb-1">
            Wide Selection
          </h3>
          <p className="text-xs text-gray-600">
            Choose from thousands of vehicles
          </p>
        </div>

        <div className="text-center p-4">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-100 rounded-full mb-3">
            <svg
              className="w-6 h-6 text-blue-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-gray-900 mb-1">
            Best Prices
          </h3>
          <p className="text-xs text-gray-600">
            Competitive pricing guaranteed
          </p>
        </div>

        <div className="text-center p-4">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-100 rounded-full mb-3">
            <svg
              className="w-6 h-6 text-blue-600"
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
          </div>
          <h3 className="text-sm font-semibold text-gray-900 mb-1">
            Fast Delivery
          </h3>
          <p className="text-xs text-gray-600">
            Quick and reliable shipping
          </p>
        </div>
      </div>
    </div>
  );
}