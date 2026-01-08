/**
 * VehicleDetailPage Component
 * 
 * Comprehensive vehicle detail page displaying complete specifications, image gallery,
 * tabbed sections, availability indicator, and configuration call-to-action.
 * 
 * Features:
 * - SEO-optimized with meta tags and structured data
 * - Responsive design across all device sizes
 * - Breadcrumb navigation
 * - Social sharing capabilities
 * - Accessibility compliant (WCAG 2.1 AA)
 * - Performance optimized with lazy loading
 * - Real-time availability indicator
 */

import { useEffect, useMemo, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useVehicle } from '@/hooks/useVehicles';
import ImageGallery from '@/components/VehicleDetail/ImageGallery';
import SpecificationTabs from '@/components/VehicleDetail/SpecificationTabs';
import VehicleOverview from '@/components/VehicleDetail/VehicleOverview';
import type { Vehicle } from '@/types/vehicle';

/**
 * Props for VehicleDetailPage component
 */
interface VehicleDetailPageProps {
  readonly className?: string;
}

/**
 * Breadcrumb item interface
 */
interface BreadcrumbItem {
  readonly label: string;
  readonly path: string;
  readonly current?: boolean;
}

/**
 * Social sharing platform type
 */
type SocialPlatform = 'facebook' | 'twitter' | 'linkedin' | 'email';

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
 * Generate structured data for SEO
 */
function generateStructuredData(vehicle: Vehicle): string {
  const structuredData = {
    '@context': 'https://schema.org',
    '@type': 'Car',
    name: `${vehicle.year} ${vehicle.make} ${vehicle.model}${vehicle.trim ? ` ${vehicle.trim}` : ''}`,
    brand: {
      '@type': 'Brand',
      name: vehicle.make,
    },
    model: vehicle.model,
    vehicleModelDate: vehicle.year.toString(),
    bodyType: vehicle.bodyStyle,
    fuelType: vehicle.specifications.fuelType,
    vehicleTransmission: vehicle.specifications.transmission,
    driveWheelConfiguration: vehicle.specifications.drivetrain,
    vehicleEngine: {
      '@type': 'EngineSpecification',
      name: vehicle.specifications.engine,
    },
    vehicleSeatingCapacity: vehicle.specifications.seatingCapacity,
    offers: {
      '@type': 'Offer',
      price: vehicle.price,
      priceCurrency: 'USD',
      availability: vehicle.availability === 'available' 
        ? 'https://schema.org/InStock' 
        : 'https://schema.org/OutOfStock',
      seller: {
        '@type': 'Organization',
        name: 'AutoSelect',
      },
    },
    description: vehicle.description,
  };

  return JSON.stringify(structuredData);
}

/**
 * Generate breadcrumb items
 */
function generateBreadcrumbs(vehicle: Vehicle): readonly BreadcrumbItem[] {
  return [
    { label: 'Home', path: '/' },
    { label: 'Browse', path: '/browse' },
    { label: vehicle.make, path: `/browse?make=${encodeURIComponent(vehicle.make)}` },
    { 
      label: vehicle.model, 
      path: `/browse?make=${encodeURIComponent(vehicle.make)}&model=${encodeURIComponent(vehicle.model)}` 
    },
    { 
      label: `${vehicle.year} ${vehicle.trim ?? ''}`.trim(), 
      path: `/vehicles/${vehicle.id}`,
      current: true,
    },
  ];
}

/**
 * Generate social sharing URL
 */
function generateShareUrl(platform: SocialPlatform, vehicle: Vehicle, currentUrl: string): string {
  const title = `${vehicle.year} ${vehicle.make} ${vehicle.model}${vehicle.trim ? ` ${vehicle.trim}` : ''}`;
  const description = vehicle.description;
  const encodedUrl = encodeURIComponent(currentUrl);
  const encodedTitle = encodeURIComponent(title);
  const encodedDescription = encodeURIComponent(description);

  const shareUrls: Record<SocialPlatform, string> = {
    facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`,
    twitter: `https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}`,
    linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`,
    email: `mailto:?subject=${encodedTitle}&body=${encodedDescription}%0A%0A${encodedUrl}`,
  };

  return shareUrls[platform];
}

/**
 * Breadcrumb navigation component
 */
function Breadcrumbs({ items }: { readonly items: readonly BreadcrumbItem[] }): JSX.Element {
  return (
    <nav aria-label="Breadcrumb" className="mb-6">
      <ol className="flex items-center space-x-2 text-sm">
        {items.map((item, index) => (
          <li key={item.path} className="flex items-center">
            {index > 0 && (
              <svg
                className="h-4 w-4 text-gray-400 mx-2"
                fill="currentColor"
                viewBox="0 0 20 20"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            )}
            {item.current ? (
              <span
                className="font-medium text-gray-900"
                aria-current="page"
              >
                {item.label}
              </span>
            ) : (
              <Link
                to={item.path}
                className="text-gray-500 hover:text-gray-700 transition-colors"
              >
                {item.label}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

/**
 * Social sharing component
 */
function SocialSharing({ vehicle }: { readonly vehicle: Vehicle }): JSX.Element {
  const currentUrl = typeof window !== 'undefined' ? window.location.href : '';

  const handleShare = useCallback((platform: SocialPlatform) => {
    const shareUrl = generateShareUrl(platform, vehicle, currentUrl);
    
    if (platform === 'email') {
      window.location.href = shareUrl;
    } else {
      window.open(shareUrl, '_blank', 'width=600,height=400,noopener,noreferrer');
    }
  }, [vehicle, currentUrl]);

  const socialButtons: Array<{ platform: SocialPlatform; label: string; icon: string }> = [
    { platform: 'facebook', label: 'Share on Facebook', icon: 'facebook' },
    { platform: 'twitter', label: 'Share on Twitter', icon: 'twitter' },
    { platform: 'linkedin', label: 'Share on LinkedIn', icon: 'linkedin' },
    { platform: 'email', label: 'Share via Email', icon: 'email' },
  ];

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium text-gray-700">Share:</span>
      <div className="flex gap-2">
        {socialButtons.map(({ platform, label, icon }) => (
          <button
            key={platform}
            type="button"
            onClick={() => handleShare(platform)}
            className="p-2 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            aria-label={label}
            title={label}
          >
            <span className="sr-only">{label}</span>
            <svg
              className="h-5 w-5 text-gray-600"
              fill="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              {icon === 'facebook' && (
                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
              )}
              {icon === 'twitter' && (
                <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z" />
              )}
              {icon === 'linkedin' && (
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
              )}
              {icon === 'email' && (
                <path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z" />
              )}
            </svg>
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * Loading skeleton component
 */
function LoadingSkeleton(): JSX.Element {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-8 bg-gray-200 rounded w-3/4" />
      <div className="aspect-[3/2] bg-gray-200 rounded-lg" />
      <div className="space-y-3">
        <div className="h-4 bg-gray-200 rounded w-full" />
        <div className="h-4 bg-gray-200 rounded w-5/6" />
        <div className="h-4 bg-gray-200 rounded w-4/6" />
      </div>
    </div>
  );
}

/**
 * Error display component
 */
function ErrorDisplay({ message }: { readonly message: string }): JSX.Element {
  const navigate = useNavigate();

  return (
    <div className="text-center py-12">
      <svg
        className="mx-auto h-12 w-12 text-red-500"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
      <h2 className="mt-4 text-lg font-semibold text-gray-900">
        Unable to Load Vehicle
      </h2>
      <p className="mt-2 text-sm text-gray-600">{message}</p>
      <div className="mt-6 flex gap-3 justify-center">
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Try Again
        </button>
        <button
          type="button"
          onClick={() => navigate('/browse')}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Browse Vehicles
        </button>
      </div>
    </div>
  );
}

/**
 * VehicleDetailPage Component
 */
export default function VehicleDetailPage({ className = '' }: VehicleDetailPageProps): JSX.Element {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Fetch vehicle data
  const { data, isLoading, error } = useVehicle(id ?? '', {
    enabled: Boolean(id),
    retry: 3,
    staleTime: 5 * 60 * 1000,
  });

  const vehicle = data?.vehicle;

  // Generate breadcrumbs
  const breadcrumbs = useMemo(
    () => (vehicle ? generateBreadcrumbs(vehicle) : []),
    [vehicle]
  );

  // Generate structured data
  const structuredData = useMemo(
    () => (vehicle ? generateStructuredData(vehicle) : ''),
    [vehicle]
  );

  // Handle configure button click
  const handleConfigure = useCallback(() => {
    if (vehicle) {
      navigate(`/configure/${vehicle.id}`);
    }
  }, [vehicle, navigate]);

  // Handle contact dealer button click
  const handleContactDealer = useCallback(() => {
    // Scroll to contact form or open modal
    console.log('Contact dealer clicked');
  }, []);

  // Scroll to top on mount
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [id]);

  // Handle loading state
  if (isLoading) {
    return (
      <div className={`container mx-auto px-4 py-8 ${className}`}>
        <LoadingSkeleton />
      </div>
    );
  }

  // Handle error state
  if (error ?? !vehicle) {
    return (
      <div className={`container mx-auto px-4 py-8 ${className}`}>
        <ErrorDisplay
          message={error?.message ?? 'Vehicle not found'}
        />
      </div>
    );
  }

  // Generate page title and description
  const pageTitle = `${vehicle.year} ${vehicle.make} ${vehicle.model}${vehicle.trim ? ` ${vehicle.trim}` : ''} - AutoSelect`;
  const pageDescription = vehicle.description ?? `View detailed specifications, features, and pricing for the ${vehicle.year} ${vehicle.make} ${vehicle.model}. Configure and order your vehicle today.`;

  return (
    <>
      {/* SEO Meta Tags */}
      <Helmet>
        <title>{pageTitle}</title>
        <meta name="description" content={pageDescription} />
        <meta property="og:title" content={pageTitle} />
        <meta property="og:description" content={pageDescription} />
        <meta property="og:type" content="product" />
        <meta property="og:url" content={typeof window !== 'undefined' ? window.location.href : ''} />
        <meta property="product:price:amount" content={vehicle.price.toString()} />
        <meta property="product:price:currency" content="USD" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={pageTitle} />
        <meta name="twitter:description" content={pageDescription} />
        <link rel="canonical" href={typeof window !== 'undefined' ? window.location.href : ''} />
        <script type="application/ld+json">{structuredData}</script>
      </Helmet>

      {/* Main Content */}
      <div className={`container mx-auto px-4 py-8 ${className}`}>
        {/* Breadcrumb Navigation */}
        <Breadcrumbs items={breadcrumbs} />

        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 sm:text-4xl">
              {vehicle.year} {vehicle.make} {vehicle.model}
              {vehicle.trim && <span className="text-gray-600"> {vehicle.trim}</span>}
            </h1>
            <p className="mt-2 text-lg text-gray-600">
              Starting at {formatCurrency(vehicle.price)}
            </p>
          </div>
          <div className="mt-4 md:mt-0">
            <SocialSharing vehicle={vehicle} />
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Image Gallery and Tabs */}
          <div className="lg:col-span-2 space-y-8">
            {/* Image Gallery */}
            <ImageGallery
              vehicle={vehicle}
              enableZoom={true}
              thumbnailCount={5}
              lazyLoadThreshold={100}
            />

            {/* Specification Tabs */}
            <SpecificationTabs
              vehicle={vehicle}
              defaultTab="overview"
            />
          </div>

          {/* Right Column - Overview and Actions */}
          <div className="lg:col-span-1">
            <div className="sticky top-4 space-y-6">
              {/* Vehicle Overview */}
              <VehicleOverview
                vehicle={vehicle}
                onConfigure={handleConfigure}
                onContactDealer={handleContactDealer}
                showActions={true}
              />

              {/* Additional Information */}
              <div className="bg-gray-50 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Need Help?
                </h3>
                <ul className="space-y-3 text-sm text-gray-700">
                  <li className="flex items-start">
                    <svg
                      className="h-5 w-5 text-blue-500 mr-2 mt-0.5 flex-shrink-0"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span>Schedule a test drive</span>
                  </li>
                  <li className="flex items-start">
                    <svg
                      className="h-5 w-5 text-blue-500 mr-2 mt-0.5 flex-shrink-0"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span>Get financing pre-approval</span>
                  </li>
                  <li className="flex items-start">
                    <svg
                      className="h-5 w-5 text-blue-500 mr-2 mt-0.5 flex-shrink-0"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span>Trade-in value estimate</span>
                  </li>
                  <li className="flex items-start">
                    <svg
                      className="h-5 w-5 text-blue-500 mr-2 mt-0.5 flex-shrink-0"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span>Contact our sales team</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}