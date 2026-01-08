/**
 * ImageGallery Component
 * 
 * Responsive image gallery with main image display, thumbnail navigation,
 * zoom functionality, and lazy loading. Integrates with Unsplash API for
 * vehicle images with comprehensive error handling and loading states.
 */

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { generateVehicleImages, isUnsplashImageError } from '@/services/unsplash';
import type { Vehicle } from '@/types/vehicle';

/**
 * Props for the ImageGallery component
 */
interface ImageGalleryProps {
  readonly vehicle: Vehicle;
  readonly className?: string;
  readonly onImageLoad?: (index: number) => void;
  readonly onImageError?: (index: number, error: Error) => void;
  readonly enableZoom?: boolean;
  readonly thumbnailCount?: number;
  readonly lazyLoadThreshold?: number;
}

/**
 * Image data structure with loading and error states
 */
interface ImageData {
  readonly url: string;
  readonly thumbnailUrl: string;
  readonly alt: string;
  readonly loaded: boolean;
  readonly error: Error | null;
}

/**
 * Zoom state for image magnification
 */
interface ZoomState {
  readonly isZoomed: boolean;
  readonly x: number;
  readonly y: number;
}

/**
 * Default number of images to generate
 */
const DEFAULT_IMAGE_COUNT = 5;

/**
 * Default lazy load threshold in pixels
 */
const DEFAULT_LAZY_LOAD_THRESHOLD = 100;

/**
 * Zoom scale factor
 */
const ZOOM_SCALE = 2;

/**
 * Keyboard navigation keys
 */
const NAVIGATION_KEYS = {
  ARROW_LEFT: 'ArrowLeft',
  ARROW_RIGHT: 'ArrowRight',
  ESCAPE: 'Escape',
  HOME: 'Home',
  END: 'End',
} as const;

/**
 * Generates image data for the vehicle
 */
function generateImageData(vehicle: Vehicle, count: number): readonly ImageData[] {
  try {
    const images = generateVehicleImages(
      {
        bodyStyle: vehicle.bodyStyle,
        make: vehicle.make,
        model: vehicle.model,
        year: vehicle.year,
        color: vehicle.color,
        seed: vehicle.id,
      },
      Array.from({ length: count }, (_, i) => (i === 0 ? 'main' : 'card')),
    );

    return images.map((image, index) => ({
      url: image.url,
      thumbnailUrl: generateVehicleImages(
        {
          bodyStyle: vehicle.bodyStyle,
          make: vehicle.make,
          model: vehicle.model,
          year: vehicle.year,
          color: vehicle.color,
          seed: `${vehicle.id}-thumb-${index}`,
        },
        ['thumbnail'],
      )[0].url,
      alt: `${vehicle.year} ${vehicle.make} ${vehicle.model} - Image ${index + 1}`,
      loaded: false,
      error: null,
    }));
  } catch (error) {
    console.error('Failed to generate vehicle images:', error);
    return [];
  }
}

/**
 * ImageGallery component with Unsplash integration and lazy loading
 */
export default function ImageGallery({
  vehicle,
  className = '',
  onImageLoad,
  onImageError,
  enableZoom = true,
  thumbnailCount = DEFAULT_IMAGE_COUNT,
  lazyLoadThreshold = DEFAULT_LAZY_LOAD_THRESHOLD,
}: ImageGalleryProps): JSX.Element {
  // State management
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [images, setImages] = useState<readonly ImageData[]>(() =>
    generateImageData(vehicle, thumbnailCount),
  );
  const [zoomState, setZoomState] = useState<ZoomState>({
    isZoomed: false,
    x: 0,
    y: 0,
  });

  // Refs
  const mainImageRef = useRef<HTMLImageElement>(null);
  const thumbnailContainerRef = useRef<HTMLDivElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  // Current image data
  const currentImage = useMemo(() => images[currentIndex], [images, currentIndex]);

  /**
   * Handles image load success
   */
  const handleImageLoad = useCallback(
    (index: number) => {
      setImages((prev) =>
        prev.map((img, i) => (i === index ? { ...img, loaded: true, error: null } : img)),
      );

      if (onImageLoad) {
        onImageLoad(index);
      }
    },
    [onImageLoad],
  );

  /**
   * Handles image load error
   */
  const handleImageError = useCallback(
    (index: number, error: Error) => {
      console.error(`Failed to load image ${index}:`, error);

      setImages((prev) =>
        prev.map((img, i) => (i === index ? { ...img, loaded: false, error } : img)),
      );

      if (onImageError) {
        onImageError(index, error);
      }
    },
    [onImageError],
  );

  /**
   * Navigates to the previous image
   */
  const handlePrevious = useCallback(() => {
    setCurrentIndex((prev) => (prev === 0 ? images.length - 1 : prev - 1));
    setZoomState({ isZoomed: false, x: 0, y: 0 });
  }, [images.length]);

  /**
   * Navigates to the next image
   */
  const handleNext = useCallback(() => {
    setCurrentIndex((prev) => (prev === images.length - 1 ? 0 : prev + 1));
    setZoomState({ isZoomed: false, x: 0, y: 0 });
  }, [images.length]);

  /**
   * Navigates to a specific image
   */
  const handleThumbnailClick = useCallback((index: number) => {
    setCurrentIndex(index);
    setZoomState({ isZoomed: false, x: 0, y: 0 });
  }, []);

  /**
   * Toggles zoom state
   */
  const handleZoomToggle = useCallback(() => {
    if (!enableZoom) return;

    setZoomState((prev) => ({
      isZoomed: !prev.isZoomed,
      x: prev.isZoomed ? 0 : 50,
      y: prev.isZoomed ? 0 : 50,
    }));
  }, [enableZoom]);

  /**
   * Handles mouse move for zoom positioning
   */
  const handleMouseMove = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      if (!zoomState.isZoomed || !mainImageRef.current) return;

      const rect = mainImageRef.current.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width) * 100;
      const y = ((event.clientY - rect.top) / rect.height) * 100;

      setZoomState((prev) => ({ ...prev, x, y }));
    },
    [zoomState.isZoomed],
  );

  /**
   * Handles keyboard navigation
   */
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      switch (event.key) {
        case NAVIGATION_KEYS.ARROW_LEFT:
          event.preventDefault();
          handlePrevious();
          break;
        case NAVIGATION_KEYS.ARROW_RIGHT:
          event.preventDefault();
          handleNext();
          break;
        case NAVIGATION_KEYS.ESCAPE:
          event.preventDefault();
          setZoomState({ isZoomed: false, x: 0, y: 0 });
          break;
        case NAVIGATION_KEYS.HOME:
          event.preventDefault();
          handleThumbnailClick(0);
          break;
        case NAVIGATION_KEYS.END:
          event.preventDefault();
          handleThumbnailClick(images.length - 1);
          break;
      }
    },
    [handlePrevious, handleNext, handleThumbnailClick, images.length],
  );

  /**
   * Sets up intersection observer for lazy loading
   */
  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const img = entry.target as HTMLImageElement;
            const src = img.dataset['src'];
            if (src && !img.src) {
              img.src = src;
            }
          }
        });
      },
      {
        rootMargin: `${lazyLoadThreshold}px`,
        threshold: 0.01,
      },
    );

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [lazyLoadThreshold]);

  /**
   * Scrolls thumbnail into view when current index changes
   */
  useEffect(() => {
    if (thumbnailContainerRef.current) {
      const thumbnail = thumbnailContainerRef.current.children[
        currentIndex
      ] as HTMLElement | null;
      if (thumbnail) {
        thumbnail.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
          inline: 'center',
        });
      }
    }
  }, [currentIndex]);

  // Handle empty images
  if (images.length === 0) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-100 rounded-lg p-8 ${className}`}
        role="alert"
        aria-live="polite"
      >
        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <p className="mt-2 text-sm text-gray-600">No images available</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`space-y-4 ${className}`}
      onKeyDown={handleKeyDown}
      role="region"
      aria-label="Vehicle image gallery"
    >
      {/* Main Image Display */}
      <div className="relative aspect-[3/2] bg-gray-100 rounded-lg overflow-hidden">
        {currentImage.error ? (
          <div
            className="absolute inset-0 flex items-center justify-center"
            role="alert"
            aria-live="polite"
          >
            <div className="text-center p-4">
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
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
              <p className="mt-2 text-sm text-gray-600">Failed to load image</p>
              {isUnsplashImageError(currentImage.error) && (
                <p className="mt-1 text-xs text-gray-500">{currentImage.error.message}</p>
              )}
            </div>
          </div>
        ) : (
          <>
            {!currentImage.loaded && (
              <div
                className="absolute inset-0 flex items-center justify-center"
                role="status"
                aria-live="polite"
              >
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
                <span className="sr-only">Loading image...</span>
              </div>
            )}
            <div
              className={`relative w-full h-full cursor-${enableZoom ? 'zoom-in' : 'default'} ${
                zoomState.isZoomed ? 'cursor-zoom-out' : ''
              }`}
              onClick={handleZoomToggle}
              onMouseMove={handleMouseMove}
              role="button"
              tabIndex={0}
              aria-label={
                zoomState.isZoomed ? 'Click to zoom out' : 'Click to zoom in'
              }
            >
              <img
                ref={mainImageRef}
                src={currentImage.url}
                alt={currentImage.alt}
                className={`w-full h-full object-cover transition-all duration-300 ${
                  currentImage.loaded ? 'opacity-100' : 'opacity-0'
                }`}
                style={
                  zoomState.isZoomed
                    ? {
                        transform: `scale(${ZOOM_SCALE})`,
                        transformOrigin: `${zoomState.x}% ${zoomState.y}%`,
                      }
                    : undefined
                }
                onLoad={() => handleImageLoad(currentIndex)}
                onError={(e) => {
                  const error = new Error('Failed to load image');
                  handleImageError(currentIndex, error);
                }}
                loading="eager"
              />
            </div>
          </>
        )}

        {/* Navigation Buttons */}
        {images.length > 1 && (
          <>
            <button
              type="button"
              onClick={handlePrevious}
              className="absolute left-4 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white rounded-full p-2 shadow-lg transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              aria-label="Previous image"
            >
              <svg
                className="w-6 h-6 text-gray-800"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </button>
            <button
              type="button"
              onClick={handleNext}
              className="absolute right-4 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white rounded-full p-2 shadow-lg transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              aria-label="Next image"
            >
              <svg
                className="w-6 h-6 text-gray-800"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          </>
        )}

        {/* Image Counter */}
        <div
          className="absolute bottom-4 right-4 bg-black/70 text-white px-3 py-1 rounded-full text-sm"
          aria-live="polite"
          aria-atomic="true"
        >
          {currentIndex + 1} / {images.length}
        </div>
      </div>

      {/* Thumbnail Navigation */}
      {images.length > 1 && (
        <div
          ref={thumbnailContainerRef}
          className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100"
          role="tablist"
          aria-label="Image thumbnails"
        >
          {images.map((image, index) => (
            <button
              key={index}
              type="button"
              onClick={() => handleThumbnailClick(index)}
              className={`flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden border-2 transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                index === currentIndex
                  ? 'border-blue-600 ring-2 ring-blue-600'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
              role="tab"
              aria-selected={index === currentIndex}
              aria-label={`View image ${index + 1}`}
            >
              {image.error ? (
                <div className="w-full h-full bg-gray-200 flex items-center justify-center">
                  <svg
                    className="w-6 h-6 text-gray-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </div>
              ) : (
                <img
                  data-src={image.thumbnailUrl}
                  alt={`Thumbnail ${index + 1}`}
                  className="w-full h-full object-cover"
                  loading="lazy"
                  onLoad={() => {
                    if (observerRef.current) {
                      const imgElement = document.querySelector(
                        `[data-src="${image.thumbnailUrl}"]`,
                      );
                      if (imgElement) {
                        observerRef.current.observe(imgElement);
                      }
                    }
                  }}
                />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}