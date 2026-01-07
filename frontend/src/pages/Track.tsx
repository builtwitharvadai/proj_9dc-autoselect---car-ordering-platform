import { useState } from 'react';

interface OrderStatus {
  readonly id: string;
  readonly status: 'processing' | 'in-transit' | 'delivered' | 'cancelled';
  readonly statusLabel: string;
  readonly timestamp: Date;
  readonly location?: string;
  readonly description: string;
}

interface TrackingInfo {
  readonly orderId: string;
  readonly orderDate: Date;
  readonly estimatedDelivery: Date;
  readonly currentStatus: OrderStatus['status'];
  readonly vehicleName: string;
  readonly vehicleImage: string;
  readonly trackingNumber: string;
  readonly statusHistory: readonly OrderStatus[];
}

const MOCK_TRACKING_DATA: TrackingInfo = {
  orderId: 'ORD-2024-001',
  orderDate: new Date('2024-01-01'),
  estimatedDelivery: new Date('2024-02-15'),
  currentStatus: 'in-transit',
  vehicleName: '2024 Luxury Sedan',
  vehicleImage: 'https://via.placeholder.com/400x250?text=2024+Luxury+Sedan',
  trackingNumber: 'TRK-2024-001-ABC',
  statusHistory: [
    {
      id: '1',
      status: 'processing',
      statusLabel: 'Order Confirmed',
      timestamp: new Date('2024-01-01T10:00:00'),
      description: 'Your order has been confirmed and is being prepared',
    },
    {
      id: '2',
      status: 'processing',
      statusLabel: 'In Production',
      timestamp: new Date('2024-01-05T14:30:00'),
      description: 'Vehicle is being manufactured at our facility',
    },
    {
      id: '3',
      status: 'in-transit',
      statusLabel: 'Quality Check Complete',
      timestamp: new Date('2024-01-20T09:15:00'),
      description: 'Vehicle passed all quality inspections',
    },
    {
      id: '4',
      status: 'in-transit',
      statusLabel: 'In Transit',
      timestamp: new Date('2024-01-25T16:45:00'),
      location: 'Distribution Center, Chicago, IL',
      description: 'Vehicle is on its way to your delivery location',
    },
  ] as const,
};

export default function Track(): JSX.Element {
  const [trackingNumber, setTrackingNumber] = useState<string>('');
  const [trackingInfo, setTrackingInfo] = useState<TrackingInfo | null>(null);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    setError(null);

    if (!trackingNumber.trim()) {
      setError('Please enter a tracking number');
      return;
    }

    setIsSearching(true);

    setTimeout(() => {
      if (trackingNumber.toUpperCase() === MOCK_TRACKING_DATA.trackingNumber) {
        setTrackingInfo(MOCK_TRACKING_DATA);
        setError(null);
      } else {
        setTrackingInfo(null);
        setError('Tracking number not found. Please check and try again.');
      }
      setIsSearching(false);
    }, 1000);
  };

  const formatDate = (date: Date): string => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    }).format(date);
  };

  const formatDateTime = (date: Date): string => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  const getStatusColor = (status: OrderStatus['status']): string => {
    switch (status) {
      case 'processing':
        return 'text-[rgb(var(--color-primary-600))] bg-[rgb(var(--color-primary-50))]';
      case 'in-transit':
        return 'text-[rgb(var(--color-primary-700))] bg-[rgb(var(--color-primary-100))]';
      case 'delivered':
        return 'text-green-700 bg-green-50';
      case 'cancelled':
        return 'text-red-700 bg-red-50';
      default:
        return 'text-[rgb(var(--color-gray-700))] bg-[rgb(var(--color-gray-100))]';
    }
  };

  const getStatusIcon = (status: OrderStatus['status']): JSX.Element => {
    switch (status) {
      case 'processing':
        return (
          <svg
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        );
      case 'in-transit':
        return (
          <svg
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0"
            />
          </svg>
        );
      case 'delivered':
        return (
          <svg
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        );
      case 'cancelled':
        return (
          <svg
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        );
      default:
        return (
          <svg
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        );
    }
  };

  return (
    <div className="min-h-screen bg-[rgb(var(--color-gray-50))] pt-16">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[rgb(var(--color-gray-900))] sm:text-4xl">
            Track Your Order
          </h1>
          <p className="mt-2 text-base text-[rgb(var(--color-gray-600))] sm:text-lg">
            Enter your tracking number to see the status of your vehicle delivery
          </p>
        </div>

        <div className="mb-8 rounded-[var(--radius-lg)] bg-white p-6 shadow-[var(--shadow-sm)]">
          <form onSubmit={handleSearch} className="flex flex-col gap-4 sm:flex-row">
            <div className="flex-1">
              <label htmlFor="tracking-number" className="sr-only">
                Tracking Number
              </label>
              <input
                type="text"
                id="tracking-number"
                value={trackingNumber}
                onChange={(e) => setTrackingNumber(e.target.value)}
                placeholder="Enter tracking number (e.g., TRK-2024-001-ABC)"
                className="w-full rounded-[var(--radius-md)] border border-[rgb(var(--color-gray-300))] px-4 py-3 text-base text-[rgb(var(--color-gray-900))] placeholder-[rgb(var(--color-gray-400))] focus:border-[rgb(var(--color-primary-500))] focus:outline-none focus:ring-2 focus:ring-[rgb(var(--color-primary-500))] focus:ring-opacity-20"
                aria-label="Tracking number input"
                aria-describedby={error ? 'tracking-error' : undefined}
                aria-invalid={error ? 'true' : 'false'}
              />
            </div>
            <button
              type="submit"
              disabled={isSearching}
              className="rounded-[var(--radius-md)] bg-[rgb(var(--color-primary-600))] px-8 py-3 text-base font-medium text-white transition-colors duration-[var(--transition-fast)] hover:bg-[rgb(var(--color-primary-700))] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-primary-600))] disabled:cursor-not-allowed disabled:opacity-50"
              aria-label={isSearching ? 'Searching...' : 'Track order'}
            >
              {isSearching ? 'Searching...' : 'Track Order'}
            </button>
          </form>

          {error && (
            <div
              id="tracking-error"
              className="mt-4 flex items-center gap-2 rounded-[var(--radius-md)] bg-red-50 p-4 text-sm text-red-700"
              role="alert"
              aria-live="polite"
            >
              <svg
                className="h-5 w-5 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <div className="mt-4 rounded-[var(--radius-md)] bg-[rgb(var(--color-primary-50))] p-4">
            <p className="text-sm text-[rgb(var(--color-primary-700))]">
              <strong>Demo:</strong> Try tracking number{' '}
              <code className="rounded bg-[rgb(var(--color-primary-100))] px-2 py-1 font-mono text-xs">
                TRK-2024-001-ABC
              </code>
            </p>
          </div>
        </div>

        {trackingInfo && (
          <div className="space-y-6">
            <div className="overflow-hidden rounded-[var(--radius-lg)] bg-white shadow-[var(--shadow-sm)]">
              <div className="flex flex-col gap-6 p-6 sm:flex-row">
                <div className="flex-shrink-0">
                  <img
                    src={trackingInfo.vehicleImage}
                    alt={trackingInfo.vehicleName}
                    className="h-48 w-full rounded-[var(--radius-md)] object-cover sm:w-64"
                    loading="lazy"
                  />
                </div>

                <div className="flex-1">
                  <div className="mb-4">
                    <h2 className="text-2xl font-bold text-[rgb(var(--color-gray-900))]">
                      {trackingInfo.vehicleName}
                    </h2>
                    <p className="mt-1 text-sm text-[rgb(var(--color-gray-600))]">
                      Order ID: {trackingInfo.orderId}
                    </p>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <p className="text-sm font-medium text-[rgb(var(--color-gray-700))]">
                        Order Date
                      </p>
                      <p className="mt-1 text-base text-[rgb(var(--color-gray-900))]">
                        {formatDate(trackingInfo.orderDate)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[rgb(var(--color-gray-700))]">
                        Estimated Delivery
                      </p>
                      <p className="mt-1 text-base text-[rgb(var(--color-gray-900))]">
                        {formatDate(trackingInfo.estimatedDelivery)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[rgb(var(--color-gray-700))]">
                        Tracking Number
                      </p>
                      <p className="mt-1 font-mono text-sm text-[rgb(var(--color-gray-900))]">
                        {trackingInfo.trackingNumber}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[rgb(var(--color-gray-700))]">
                        Current Status
                      </p>
                      <span
                        className={`mt-1 inline-flex items-center gap-2 rounded-[var(--radius-full)] px-3 py-1 text-sm font-medium ${getStatusColor(trackingInfo.currentStatus)}`}
                      >
                        {getStatusIcon(trackingInfo.currentStatus)}
                        {trackingInfo.currentStatus
                          .split('-')
                          .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
                          .join(' ')}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-[var(--radius-lg)] bg-white p-6 shadow-[var(--shadow-sm)]">
              <h3 className="mb-6 text-xl font-semibold text-[rgb(var(--color-gray-900))]">
                Tracking History
              </h3>

              <div className="relative">
                <div
                  className="absolute left-4 top-0 h-full w-0.5 bg-[rgb(var(--color-gray-200))]"
                  aria-hidden="true"
                />

                <ol className="space-y-6" role="list">
                  {trackingInfo.statusHistory.map((status, index) => (
                    <li key={status.id} className="relative flex gap-4">
                      <div
                        className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-[var(--radius-full)] ${getStatusColor(status.status)}`}
                        aria-hidden="true"
                      >
                        {getStatusIcon(status.status)}
                      </div>

                      <div className="flex-1 pb-6">
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="text-base font-semibold text-[rgb(var(--color-gray-900))]">
                              {status.statusLabel}
                            </h4>
                            <p className="mt-1 text-sm text-[rgb(var(--color-gray-600))]">
                              {status.description}
                            </p>
                            {status.location && (
                              <p className="mt-1 flex items-center gap-1 text-sm text-[rgb(var(--color-gray-600))]">
                                <svg
                                  className="h-4 w-4"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
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
                                {status.location}
                              </p>
                            )}
                          </div>
                          <time
                            className="text-sm text-[rgb(var(--color-gray-500))]"
                            dateTime={status.timestamp.toISOString()}
                          >
                            {formatDateTime(status.timestamp)}
                          </time>
                        </div>

                        {index === trackingInfo.statusHistory.length - 1 && (
                          <div className="mt-4 rounded-[var(--radius-md)] bg-[rgb(var(--color-primary-50))] p-4">
                            <p className="text-sm font-medium text-[rgb(var(--color-primary-700))]">
                              This is the most recent update for your order
                            </p>
                          </div>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              </div>
            </div>

            <div className="rounded-[var(--radius-lg)] bg-white p-6 shadow-[var(--shadow-sm)]">
              <h3 className="mb-4 text-lg font-semibold text-[rgb(var(--color-gray-900))]">
                Need Help?
              </h3>
              <div className="space-y-3">
                <div className="flex items-center gap-3 text-sm text-[rgb(var(--color-gray-600))]">
                  <svg
                    className="h-5 w-5 text-[rgb(var(--color-primary-600))]"
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
                  <span>
                    Email us at{' '}
                    <a
                      href="mailto:support@autoselect.com"
                      className="font-medium text-[rgb(var(--color-primary-600))] hover:text-[rgb(var(--color-primary-700))]"
                    >
                      support@autoselect.com
                    </a>
                  </span>
                </div>
                <div className="flex items-center gap-3 text-sm text-[rgb(var(--color-gray-600))]">
                  <svg
                    className="h-5 w-5 text-[rgb(var(--color-primary-600))]"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
                    />
                  </svg>
                  <span>
                    Call us at{' '}
                    <a
                      href="tel:+18005551234"
                      className="font-medium text-[rgb(var(--color-primary-600))] hover:text-[rgb(var(--color-primary-700))]"
                    >
                      1-800-555-1234
                    </a>
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}