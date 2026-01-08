/**
 * Unsplash API Integration Service
 * 
 * Provides vehicle image generation using Unsplash's source API with proper
 * sizing, caching, and error handling. Implements vehicle-specific search terms
 * for relevant imagery.
 */

/**
 * Image size configuration for different use cases
 */
interface ImageSize {
  readonly width: number;
  readonly height: number;
}

/**
 * Supported image sizes for vehicle images
 */
const IMAGE_SIZES = {
  main: { width: 1200, height: 800 } as const,
  thumbnail: { width: 400, height: 300 } as const,
  hero: { width: 1920, height: 1080 } as const,
  card: { width: 600, height: 400 } as const,
} as const;

type ImageSizeType = keyof typeof IMAGE_SIZES;

/**
 * Vehicle-specific search terms for Unsplash queries
 */
const VEHICLE_SEARCH_TERMS: Record<string, readonly string[]> = {
  sedan: ['luxury sedan', 'modern sedan', 'executive car'],
  suv: ['suv vehicle', 'sport utility vehicle', 'crossover suv'],
  truck: ['pickup truck', 'modern truck', 'commercial truck'],
  coupe: ['sports coupe', 'luxury coupe', 'performance car'],
  convertible: ['convertible car', 'cabriolet', 'roadster'],
  wagon: ['station wagon', 'estate car', 'family wagon'],
  van: ['passenger van', 'minivan', 'commercial van'],
  hatchback: ['hatchback car', 'compact hatchback', 'city car'],
} as const;

/**
 * Default search term when body style is not recognized
 */
const DEFAULT_SEARCH_TERM = 'modern car';

/**
 * Unsplash API base URL
 */
const UNSPLASH_BASE_URL = 'https://source.unsplash.com';

/**
 * Cache duration for image URLs (24 hours in milliseconds)
 */
const CACHE_DURATION_MS = 24 * 60 * 60 * 1000;

/**
 * In-memory cache for generated image URLs
 */
interface CacheEntry {
  readonly url: string;
  readonly timestamp: number;
}

const imageCache = new Map<string, CacheEntry>();

/**
 * Error thrown when image generation fails
 */
export class UnsplashImageError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'UnsplashImageError';
  }
}

/**
 * Options for generating vehicle images
 */
interface GenerateImageOptions {
  readonly bodyStyle?: string;
  readonly make?: string;
  readonly model?: string;
  readonly year?: number;
  readonly color?: string;
  readonly size?: ImageSizeType;
  readonly seed?: string;
  readonly useCache?: boolean;
}

/**
 * Result of image generation
 */
interface ImageResult {
  readonly url: string;
  readonly width: number;
  readonly height: number;
  readonly searchTerm: string;
  readonly cached: boolean;
}

/**
 * Generates a cache key for image URL caching
 */
function generateCacheKey(options: GenerateImageOptions, size: ImageSize): string {
  const parts = [
    options.bodyStyle ?? 'default',
    options.make ?? '',
    options.model ?? '',
    options.year?.toString() ?? '',
    options.color ?? '',
    `${size.width}x${size.height}`,
    options.seed ?? '',
  ];

  return parts.filter(Boolean).join('_').toLowerCase();
}

/**
 * Checks if a cache entry is still valid
 */
function isCacheValid(entry: CacheEntry): boolean {
  return Date.now() - entry.timestamp < CACHE_DURATION_MS;
}

/**
 * Retrieves an image URL from cache if valid
 */
function getFromCache(cacheKey: string): string | null {
  const entry = imageCache.get(cacheKey);

  if (!entry) {
    return null;
  }

  if (!isCacheValid(entry)) {
    imageCache.delete(cacheKey);
    return null;
  }

  return entry.url;
}

/**
 * Stores an image URL in cache
 */
function storeInCache(cacheKey: string, url: string): void {
  imageCache.set(cacheKey, {
    url,
    timestamp: Date.now(),
  });
}

/**
 * Builds a search term based on vehicle attributes
 */
function buildSearchTerm(options: GenerateImageOptions): string {
  const terms: string[] = [];

  // Add body style specific term
  if (options.bodyStyle) {
    const bodyStyleTerms = VEHICLE_SEARCH_TERMS[options.bodyStyle.toLowerCase()];
    if (bodyStyleTerms && bodyStyleTerms.length > 0) {
      terms.push(bodyStyleTerms[0]);
    }
  }

  // Add make and model if available
  if (options.make) {
    terms.push(options.make);
  }

  if (options.model) {
    terms.push(options.model);
  }

  // Add year if recent (last 10 years)
  if (options.year && options.year >= new Date().getFullYear() - 10) {
    terms.push(options.year.toString());
  }

  // Add color if specified
  if (options.color) {
    terms.push(options.color);
  }

  // Return combined terms or default
  return terms.length > 0 ? terms.join(' ') : DEFAULT_SEARCH_TERM;
}

/**
 * Constructs the Unsplash image URL with proper parameters
 */
function constructImageUrl(searchTerm: string, size: ImageSize, seed?: string): string {
  const encodedTerm = encodeURIComponent(searchTerm);
  let url = `${UNSPLASH_BASE_URL}/${size.width}x${size.height}/?${encodedTerm}`;

  // Add seed for consistent images across requests
  if (seed) {
    url += `&sig=${encodeURIComponent(seed)}`;
  }

  return url;
}

/**
 * Clears expired entries from the cache
 */
function cleanupCache(): void {
  const now = Date.now();
  const keysToDelete: string[] = [];

  imageCache.forEach((entry, key) => {
    if (now - entry.timestamp >= CACHE_DURATION_MS) {
      keysToDelete.push(key);
    }
  });

  keysToDelete.forEach((key) => {
    imageCache.delete(key);
  });
}

/**
 * Generates a vehicle image URL from Unsplash
 * 
 * @param options - Configuration options for image generation
 * @returns Image result with URL and metadata
 * @throws {UnsplashImageError} If image generation fails
 */
export function generateVehicleImage(options: GenerateImageOptions = {}): ImageResult {
  try {
    // Get image size configuration
    const sizeType = options.size ?? 'main';
    const size = IMAGE_SIZES[sizeType];

    if (!size) {
      throw new UnsplashImageError(
        `Invalid image size type: ${sizeType}`,
        'INVALID_SIZE',
        { sizeType, availableSizes: Object.keys(IMAGE_SIZES) },
      );
    }

    // Check cache if enabled
    const useCache = options.useCache ?? true;
    let cached = false;

    if (useCache) {
      const cacheKey = generateCacheKey(options, size);
      const cachedUrl = getFromCache(cacheKey);

      if (cachedUrl) {
        const searchTerm = buildSearchTerm(options);
        return {
          url: cachedUrl,
          width: size.width,
          height: size.height,
          searchTerm,
          cached: true,
        };
      }
    }

    // Build search term and construct URL
    const searchTerm = buildSearchTerm(options);
    const url = constructImageUrl(searchTerm, size, options.seed);

    // Store in cache if enabled
    if (useCache) {
      const cacheKey = generateCacheKey(options, size);
      storeInCache(cacheKey, url);
    }

    return {
      url,
      width: size.width,
      height: size.height,
      searchTerm,
      cached,
    };
  } catch (error) {
    if (error instanceof UnsplashImageError) {
      throw error;
    }

    throw new UnsplashImageError(
      'Failed to generate vehicle image',
      'GENERATION_ERROR',
      {
        originalError: error instanceof Error ? error.message : String(error),
        options,
      },
    );
  }
}

/**
 * Generates multiple vehicle images with different sizes
 * 
 * @param options - Base configuration options
 * @param sizes - Array of size types to generate
 * @returns Array of image results
 */
export function generateVehicleImages(
  options: GenerateImageOptions = {},
  sizes: readonly ImageSizeType[] = ['main', 'thumbnail'],
): readonly ImageResult[] {
  return sizes.map((size) =>
    generateVehicleImage({
      ...options,
      size,
    }),
  );
}

/**
 * Generates a main vehicle image URL (1200x800)
 * 
 * @param options - Configuration options
 * @returns Image URL
 */
export function getMainVehicleImage(options: GenerateImageOptions = {}): string {
  return generateVehicleImage({ ...options, size: 'main' }).url;
}

/**
 * Generates a thumbnail vehicle image URL (400x300)
 * 
 * @param options - Configuration options
 * @returns Image URL
 */
export function getThumbnailVehicleImage(options: GenerateImageOptions = {}): string {
  return generateVehicleImage({ ...options, size: 'thumbnail' }).url;
}

/**
 * Generates a hero vehicle image URL (1920x1080)
 * 
 * @param options - Configuration options
 * @returns Image URL
 */
export function getHeroVehicleImage(options: GenerateImageOptions = {}): string {
  return generateVehicleImage({ ...options, size: 'hero' }).url;
}

/**
 * Generates a card vehicle image URL (600x400)
 * 
 * @param options - Configuration options
 * @returns Image URL
 */
export function getCardVehicleImage(options: GenerateImageOptions = {}): string {
  return generateVehicleImage({ ...options, size: 'card' }).url;
}

/**
 * Clears the entire image cache
 */
export function clearImageCache(): void {
  imageCache.clear();
}

/**
 * Gets the current cache size
 * 
 * @returns Number of cached entries
 */
export function getCacheSize(): number {
  return imageCache.size;
}

/**
 * Gets cache statistics
 * 
 * @returns Cache statistics object
 */
export function getCacheStats(): {
  readonly size: number;
  readonly validEntries: number;
  readonly expiredEntries: number;
} {
  let validEntries = 0;
  let expiredEntries = 0;

  imageCache.forEach((entry) => {
    if (isCacheValid(entry)) {
      validEntries++;
    } else {
      expiredEntries++;
    }
  });

  return {
    size: imageCache.size,
    validEntries,
    expiredEntries,
  };
}

/**
 * Performs cache cleanup by removing expired entries
 * Should be called periodically to prevent memory leaks
 */
export function performCacheCleanup(): void {
  cleanupCache();
}

// Periodic cache cleanup (every hour)
if (typeof window !== 'undefined') {
  setInterval(() => {
    performCacheCleanup();
  }, 60 * 60 * 1000);
}

/**
 * Type guard to check if an error is an UnsplashImageError
 */
export function isUnsplashImageError(error: unknown): error is UnsplashImageError {
  return error instanceof UnsplashImageError;
}

/**
 * Available image sizes
 */
export const AVAILABLE_SIZES = Object.keys(IMAGE_SIZES) as readonly ImageSizeType[];

/**
 * Available body styles
 */
export const AVAILABLE_BODY_STYLES = Object.keys(
  VEHICLE_SEARCH_TERMS,
) as readonly string[];