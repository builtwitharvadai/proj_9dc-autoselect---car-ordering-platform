/**
 * ColorSelector Component
 * 
 * Interactive color selector with visual preview using Unsplash images.
 * Provides thumbnail grid, selected color highlighting, and main image preview
 * with color overlay effects.
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import { generateVehicleImage, isUnsplashImageError } from '../../services/unsplash';
import type { ColorOption } from '../../types/configuration';

/**
 * Props for ColorSelector component
 */
interface ColorSelectorProps {
  readonly vehicleId: string;
  readonly colors: readonly ColorOption[];
  readonly selectedColorId?: string;
  readonly onColorSelect: (colorId: string) => void;
  readonly className?: string;
  readonly make?: string;
  readonly model?: string;
  readonly year?: number;
  readonly bodyStyle?: string;
}

/**
 * Image loading state
 */
type ImageLoadState = 'idle' | 'loading' | 'loaded' | 'error';

/**
 * Color with image URL
 */
interface ColorWithImage extends ColorOption {
  readonly imageUrl: string;
  readonly loadState: ImageLoadState;
}

/**
 * Generates a unique seed for consistent image generation
 */
function generateImageSeed(vehicleId: string, colorId: string): string {
  return `${vehicleId}-${colorId}`;
}

/**
 * Applies color overlay filter to image URL
 */
function applyColorOverlay(imageUrl: string, hexCode: string): string {
  // Remove # from hex code
  const cleanHex = hexCode.replace('#', '');
  
  // Add color overlay parameter to Unsplash URL
  return `${imageUrl}&blend=${cleanHex}&blend-mode=multiply&blend-alpha=30`;
}

/**
 * Gets color category display name
 */
function getColorCategoryLabel(category: ColorOption['category']): string {
  const labels: Record<ColorOption['category'], string> = {
    standard: 'Standard',
    metallic: 'Metallic',
    premium: 'Premium',
  };
  return labels[category];
}

/**
 * ColorSelector Component
 */
export default function ColorSelector({
  vehicleId,
  colors,
  selectedColorId,
  onColorSelect,
  className = '',
  make,
  model,
  year,
  bodyStyle,
}: ColorSelectorProps): JSX.Element {
  // State for colors with images
  const [colorsWithImages, setColorsWithImages] = useState<readonly ColorWithImage[]>([]);
  
  // State for main preview image
  const [mainImageUrl, setMainImageUrl] = useState<string>('');
  const [mainImageLoadState, setMainImageLoadState] = useState<ImageLoadState>('idle');

  // Get selected color
  const selectedColor = useMemo(
    () => colorsWithImages.find((c) => c.id === selectedColorId),
    [colorsWithImages, selectedColorId],
  );

  /**
   * Generate images for all colors
   */
  useEffect(() => {
    const generateImages = async (): Promise<void> => {
      try {
        const colorsWithUrls = colors.map((color): ColorWithImage => {
          try {
            const seed = generateImageSeed(vehicleId, color.id);
            const result = generateVehicleImage({
              bodyStyle,
              make,
              model,
              year,
              color: color.name,
              size: 'thumbnail',
              seed,
            });

            const overlayUrl = applyColorOverlay(result.url, color.hexCode);

            return {
              ...color,
              imageUrl: overlayUrl,
              loadState: 'idle',
            };
          } catch (error) {
            console.error(`Failed to generate image for color ${color.id}:`, error);
            return {
              ...color,
              imageUrl: '',
              loadState: 'error',
            };
          }
        });

        setColorsWithImages(colorsWithUrls);
      } catch (error) {
        console.error('Failed to generate color images:', error);
      }
    };

    if (colors.length > 0) {
      void generateImages();
    }
  }, [colors, vehicleId, bodyStyle, make, model, year]);

  /**
   * Generate main preview image when color is selected
   */
  useEffect(() => {
    const generateMainImage = async (): Promise<void> => {
      if (!selectedColor) {
        setMainImageUrl('');
        setMainImageLoadState('idle');
        return;
      }

      setMainImageLoadState('loading');

      try {
        const seed = generateImageSeed(vehicleId, selectedColor.id);
        const result = generateVehicleImage({
          bodyStyle,
          make,
          model,
          year,
          color: selectedColor.name,
          size: 'main',
          seed,
        });

        const overlayUrl = applyColorOverlay(result.url, selectedColor.hexCode);
        setMainImageUrl(overlayUrl);
        setMainImageLoadState('loaded');
      } catch (error) {
        console.error('Failed to generate main preview image:', error);
        setMainImageLoadState('error');
      }
    };

    void generateMainImage();
  }, [selectedColor, vehicleId, bodyStyle, make, model, year]);

  /**
   * Handle color selection
   */
  const handleColorSelect = useCallback(
    (colorId: string) => {
      const color = colors.find((c) => c.id === colorId);
      if (color?.isAvailable) {
        onColorSelect(colorId);
      }
    },
    [colors, onColorSelect],
  );

  /**
   * Handle thumbnail image load
   */
  const handleThumbnailLoad = useCallback((colorId: string) => {
    setColorsWithImages((prev) =>
      prev.map((c) =>
        c.id === colorId ? { ...c, loadState: 'loaded' as const } : c,
      ),
    );
  }, []);

  /**
   * Handle thumbnail image error
   */
  const handleThumbnailError = useCallback((colorId: string) => {
    setColorsWithImages((prev) =>
      prev.map((c) =>
        c.id === colorId ? { ...c, loadState: 'error' as const } : c,
      ),
    );
  }, []);

  /**
   * Group colors by category
   */
  const colorsByCategory = useMemo(() => {
    const grouped = new Map<ColorOption['category'], ColorWithImage[]>();

    colorsWithImages.forEach((color) => {
      const existing = grouped.get(color.category) ?? [];
      grouped.set(color.category, [...existing, color]);
    });

    return grouped;
  }, [colorsWithImages]);

  /**
   * Render loading skeleton
   */
  const renderLoadingSkeleton = (): JSX.Element => (
    <div className="animate-pulse">
      <div className="aspect-video bg-gray-200 rounded-lg mb-6" />
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="aspect-square bg-gray-200 rounded-lg" />
        ))}
      </div>
    </div>
  );

  /**
   * Render main preview
   */
  const renderMainPreview = (): JSX.Element => {
    if (!selectedColor) {
      return (
        <div className="aspect-video bg-gray-100 rounded-lg flex items-center justify-center">
          <p className="text-gray-500 text-lg">Select a color to preview</p>
        </div>
      );
    }

    if (mainImageLoadState === 'loading') {
      return (
        <div className="aspect-video bg-gray-200 rounded-lg animate-pulse flex items-center justify-center">
          <div className="text-gray-400">Loading preview...</div>
        </div>
      );
    }

    if (mainImageLoadState === 'error') {
      return (
        <div className="aspect-video bg-gray-100 rounded-lg flex items-center justify-center">
          <p className="text-red-500">Failed to load preview image</p>
        </div>
      );
    }

    return (
      <div className="relative aspect-video bg-gray-100 rounded-lg overflow-hidden">
        <img
          src={mainImageUrl}
          alt={`${selectedColor.name} preview`}
          className="w-full h-full object-cover"
          loading="eager"
        />
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-white text-2xl font-bold">{selectedColor.name}</h3>
              <p className="text-white/80 text-sm">
                {getColorCategoryLabel(selectedColor.category)}
              </p>
            </div>
            {selectedColor.price > 0 && (
              <div className="text-white text-xl font-semibold">
                +${selectedColor.price.toLocaleString()}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  /**
   * Render color thumbnail
   */
  const renderColorThumbnail = (color: ColorWithImage): JSX.Element => {
    const isSelected = color.id === selectedColorId;
    const isAvailable = color.isAvailable;

    return (
      <button
        key={color.id}
        type="button"
        onClick={() => handleColorSelect(color.id)}
        disabled={!isAvailable}
        className={`
          relative aspect-square rounded-lg overflow-hidden transition-all
          ${isSelected ? 'ring-4 ring-blue-500 scale-105' : 'ring-2 ring-gray-200'}
          ${isAvailable ? 'cursor-pointer hover:ring-blue-300' : 'cursor-not-allowed opacity-50'}
          ${!isSelected && isAvailable ? 'hover:scale-105' : ''}
        `}
        aria-label={`Select ${color.name} color`}
        aria-pressed={isSelected}
      >
        {color.loadState === 'loading' || color.loadState === 'idle' ? (
          <div className="w-full h-full bg-gray-200 animate-pulse" />
        ) : color.loadState === 'error' ? (
          <div
            className="w-full h-full flex items-center justify-center"
            style={{ backgroundColor: color.hexCode }}
          >
            <span className="text-xs text-white/80">Preview unavailable</span>
          </div>
        ) : (
          <img
            src={color.imageUrl}
            alt={color.name}
            className="w-full h-full object-cover"
            loading="lazy"
            onLoad={() => handleThumbnailLoad(color.id)}
            onError={() => handleThumbnailError(color.id)}
          />
        )}

        {/* Color swatch indicator */}
        <div className="absolute bottom-2 right-2">
          <div
            className="w-6 h-6 rounded-full border-2 border-white shadow-lg"
            style={{ backgroundColor: color.hexCode }}
            aria-hidden="true"
          />
        </div>

        {/* Selected indicator */}
        {isSelected && (
          <div className="absolute top-2 left-2">
            <div className="bg-blue-500 text-white rounded-full p-1">
              <svg
                className="w-4 h-4"
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
            </div>
          </div>
        )}

        {/* Unavailable overlay */}
        {!isAvailable && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
            <span className="text-white text-xs font-semibold">Unavailable</span>
          </div>
        )}

        {/* Color name and price */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2">
          <p className="text-white text-xs font-medium truncate">{color.name}</p>
          {color.price > 0 && (
            <p className="text-white/80 text-xs">+${color.price.toLocaleString()}</p>
          )}
        </div>
      </button>
    );
  };

  /**
   * Render color grid by category
   */
  const renderColorGrid = (): JSX.Element => {
    if (colorsByCategory.size === 0) {
      return (
        <div className="text-center py-8">
          <p className="text-gray-500">No colors available</p>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        {Array.from(colorsByCategory.entries()).map(([category, categoryColors]) => (
          <div key={category}>
            <h4 className="text-lg font-semibold text-gray-900 mb-3">
              {getColorCategoryLabel(category)}
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {categoryColors.map((color) => renderColorThumbnail(color))}
            </div>
          </div>
        ))}
      </div>
    );
  };

  if (colors.length === 0) {
    return renderLoadingSkeleton();
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Main preview */}
      <div>{renderMainPreview()}</div>

      {/* Color selection grid */}
      <div>
        <h3 className="text-xl font-bold text-gray-900 mb-4">Available Colors</h3>
        {renderColorGrid()}
      </div>

      {/* Selected color info */}
      {selectedColor && (
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div
                className="w-12 h-12 rounded-lg border-2 border-gray-300"
                style={{ backgroundColor: selectedColor.hexCode }}
                aria-hidden="true"
              />
              <div>
                <p className="font-semibold text-gray-900">{selectedColor.name}</p>
                <p className="text-sm text-gray-600">
                  {getColorCategoryLabel(selectedColor.category)}
                </p>
              </div>
            </div>
            {selectedColor.price > 0 && (
              <div className="text-right">
                <p className="text-sm text-gray-600">Additional Cost</p>
                <p className="text-lg font-bold text-gray-900">
                  +${selectedColor.price.toLocaleString()}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}