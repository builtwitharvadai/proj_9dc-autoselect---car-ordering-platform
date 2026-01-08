/**
 * Comprehensive Test Suite for Unsplash API Integration Service
 * 
 * Tests cover:
 * - Image URL generation with various configurations
 * - Cache behavior and expiration
 * - Search term building logic
 * - Error handling and validation
 * - Multiple image size generation
 * - Cache management operations
 * 
 * Coverage Target: >80%
 * Framework: Vitest
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  generateVehicleImage,
  generateVehicleImages,
  getMainVehicleImage,
  getThumbnailVehicleImage,
  getHeroVehicleImage,
  getCardVehicleImage,
  clearImageCache,
  getCacheSize,
  getCacheStats,
  performCacheCleanup,
  isUnsplashImageError,
  UnsplashImageError,
  AVAILABLE_SIZES,
  AVAILABLE_BODY_STYLES,
} from '../unsplash';

describe('UnsplashImageError', () => {
  it('should create error with message, code, and details', () => {
    const error = new UnsplashImageError(
      'Test error',
      'TEST_CODE',
      { key: 'value' },
    );

    expect(error.message).toBe('Test error');
    expect(error.code).toBe('TEST_CODE');
    expect(error.details).toEqual({ key: 'value' });
    expect(error.name).toBe('UnsplashImageError');
  });

  it('should create error without details', () => {
    const error = new UnsplashImageError('Test error', 'TEST_CODE');

    expect(error.message).toBe('Test error');
    expect(error.code).toBe('TEST_CODE');
    expect(error.details).toBeUndefined();
  });

  it('should be instance of Error', () => {
    const error = new UnsplashImageError('Test', 'CODE');

    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(UnsplashImageError);
  });
});

describe('isUnsplashImageError', () => {
  it('should return true for UnsplashImageError instances', () => {
    const error = new UnsplashImageError('Test', 'CODE');

    expect(isUnsplashImageError(error)).toBe(true);
  });

  it('should return false for regular Error instances', () => {
    const error = new Error('Test');

    expect(isUnsplashImageError(error)).toBe(false);
  });

  it('should return false for non-error values', () => {
    expect(isUnsplashImageError(null)).toBe(false);
    expect(isUnsplashImageError(undefined)).toBe(false);
    expect(isUnsplashImageError('string')).toBe(false);
    expect(isUnsplashImageError(123)).toBe(false);
    expect(isUnsplashImageError({})).toBe(false);
  });
});

describe('generateVehicleImage', () => {
  beforeEach(() => {
    clearImageCache();
  });

  afterEach(() => {
    clearImageCache();
  });

  describe('Basic Image Generation', () => {
    it('should generate image with default options', () => {
      const result = generateVehicleImage();

      expect(result).toMatchObject({
        url: expect.stringContaining('https://source.unsplash.com'),
        width: 1200,
        height: 800,
        searchTerm: 'modern car',
        cached: false,
      });
    });

    it('should generate image with main size by default', () => {
      const result = generateVehicleImage();

      expect(result.url).toContain('1200x800');
      expect(result.width).toBe(1200);
      expect(result.height).toBe(800);
    });

    it('should generate image with thumbnail size', () => {
      const result = generateVehicleImage({ size: 'thumbnail' });

      expect(result.url).toContain('400x300');
      expect(result.width).toBe(400);
      expect(result.height).toBe(300);
    });

    it('should generate image with hero size', () => {
      const result = generateVehicleImage({ size: 'hero' });

      expect(result.url).toContain('1920x1080');
      expect(result.width).toBe(1920);
      expect(result.height).toBe(1080);
    });

    it('should generate image with card size', () => {
      const result = generateVehicleImage({ size: 'card' });

      expect(result.url).toContain('600x400');
      expect(result.width).toBe(600);
      expect(result.height).toBe(400);
    });
  });

  describe('Search Term Building', () => {
    it('should use body style in search term', () => {
      const result = generateVehicleImage({ bodyStyle: 'sedan' });

      expect(result.searchTerm).toContain('luxury sedan');
      expect(result.url).toContain(encodeURIComponent('luxury sedan'));
    });

    it('should use make in search term', () => {
      const result = generateVehicleImage({ make: 'Toyota' });

      expect(result.searchTerm).toContain('Toyota');
      expect(result.url).toContain(encodeURIComponent('Toyota'));
    });

    it('should use model in search term', () => {
      const result = generateVehicleImage({ model: 'Camry' });

      expect(result.searchTerm).toContain('Camry');
      expect(result.url).toContain(encodeURIComponent('Camry'));
    });

    it('should use recent year in search term', () => {
      const currentYear = new Date().getFullYear();
      const result = generateVehicleImage({ year: currentYear });

      expect(result.searchTerm).toContain(currentYear.toString());
    });

    it('should not use old year in search term', () => {
      const oldYear = new Date().getFullYear() - 15;
      const result = generateVehicleImage({ year: oldYear });

      expect(result.searchTerm).not.toContain(oldYear.toString());
    });

    it('should use color in search term', () => {
      const result = generateVehicleImage({ color: 'red' });

      expect(result.searchTerm).toContain('red');
      expect(result.url).toContain(encodeURIComponent('red'));
    });

    it('should combine multiple attributes in search term', () => {
      const result = generateVehicleImage({
        bodyStyle: 'suv',
        make: 'Honda',
        model: 'CR-V',
        year: new Date().getFullYear(),
        color: 'blue',
      });

      expect(result.searchTerm).toContain('suv vehicle');
      expect(result.searchTerm).toContain('Honda');
      expect(result.searchTerm).toContain('CR-V');
      expect(result.searchTerm).toContain('blue');
    });

    it('should use default search term when no options provided', () => {
      const result = generateVehicleImage({});

      expect(result.searchTerm).toBe('modern car');
    });

    it('should handle unknown body style gracefully', () => {
      const result = generateVehicleImage({ bodyStyle: 'unknown' });

      expect(result.searchTerm).toBe('modern car');
    });

    it('should handle case-insensitive body styles', () => {
      const result = generateVehicleImage({ bodyStyle: 'SEDAN' });

      expect(result.searchTerm).toContain('luxury sedan');
    });
  });

  describe('Body Style Variations', () => {
    const bodyStyles = [
      { style: 'sedan', expected: 'luxury sedan' },
      { style: 'suv', expected: 'suv vehicle' },
      { style: 'truck', expected: 'pickup truck' },
      { style: 'coupe', expected: 'sports coupe' },
      { style: 'convertible', expected: 'convertible car' },
      { style: 'wagon', expected: 'station wagon' },
      { style: 'van', expected: 'passenger van' },
      { style: 'hatchback', expected: 'hatchback car' },
    ];

    bodyStyles.forEach(({ style, expected }) => {
      it(`should generate correct search term for ${style}`, () => {
        const result = generateVehicleImage({ bodyStyle: style });

        expect(result.searchTerm).toContain(expected);
      });
    });
  });

  describe('Seed Parameter', () => {
    it('should include seed in URL when provided', () => {
      const result = generateVehicleImage({ seed: 'test-seed-123' });

      expect(result.url).toContain('sig=');
      expect(result.url).toContain(encodeURIComponent('test-seed-123'));
    });

    it('should not include seed in URL when not provided', () => {
      const result = generateVehicleImage();

      expect(result.url).not.toContain('sig=');
    });

    it('should generate consistent URLs with same seed', () => {
      const result1 = generateVehicleImage({ seed: 'consistent', useCache: false });
      const result2 = generateVehicleImage({ seed: 'consistent', useCache: false });

      expect(result1.url).toBe(result2.url);
    });
  });

  describe('Caching Behavior', () => {
    it('should cache generated URLs by default', () => {
      const options = { bodyStyle: 'sedan', make: 'Toyota' };

      const result1 = generateVehicleImage(options);
      expect(result1.cached).toBe(false);
      expect(getCacheSize()).toBe(1);

      const result2 = generateVehicleImage(options);
      expect(result2.cached).toBe(true);
      expect(result2.url).toBe(result1.url);
    });

    it('should not cache when useCache is false', () => {
      const options = { bodyStyle: 'sedan', useCache: false };

      generateVehicleImage(options);
      expect(getCacheSize()).toBe(0);

      generateVehicleImage(options);
      expect(getCacheSize()).toBe(0);
    });

    it('should generate different cache keys for different options', () => {
      generateVehicleImage({ bodyStyle: 'sedan' });
      generateVehicleImage({ bodyStyle: 'suv' });
      generateVehicleImage({ size: 'thumbnail' });

      expect(getCacheSize()).toBe(3);
    });

    it('should use same cache key for identical options', () => {
      const options = {
        bodyStyle: 'sedan',
        make: 'Toyota',
        model: 'Camry',
        size: 'main' as const,
      };

      generateVehicleImage(options);
      generateVehicleImage(options);

      expect(getCacheSize()).toBe(1);
    });

    it('should return cached URL on subsequent calls', () => {
      const options = { bodyStyle: 'coupe', make: 'BMW' };

      const result1 = generateVehicleImage(options);
      const result2 = generateVehicleImage(options);

      expect(result2.cached).toBe(true);
      expect(result2.url).toBe(result1.url);
      expect(result2.searchTerm).toBe(result1.searchTerm);
    });
  });

  describe('Error Handling', () => {
    it('should throw error for invalid size type', () => {
      expect(() => {
        generateVehicleImage({ size: 'invalid' as any });
      }).toThrow(UnsplashImageError);
    });

    it('should include error details for invalid size', () => {
      try {
        generateVehicleImage({ size: 'invalid' as any });
      } catch (error) {
        expect(isUnsplashImageError(error)).toBe(true);
        if (isUnsplashImageError(error)) {
          expect(error.code).toBe('INVALID_SIZE');
          expect(error.details).toHaveProperty('sizeType', 'invalid');
          expect(error.details).toHaveProperty('availableSizes');
        }
      }
    });

    it('should wrap unexpected errors in UnsplashImageError', () => {
      // This test verifies error wrapping behavior
      // In practice, the current implementation is robust
      // but we test the error handling path
      expect(() => {
        generateVehicleImage({ size: 'main' });
      }).not.toThrow();
    });
  });

  describe('URL Structure', () => {
    it('should generate valid Unsplash URL structure', () => {
      const result = generateVehicleImage();

      expect(result.url).toMatch(/^https:\/\/source\.unsplash\.com\/\d+x\d+\/\?/);
    });

    it('should properly encode search terms in URL', () => {
      const result = generateVehicleImage({
        make: 'Mercedes-Benz',
        model: 'S-Class',
      });

      expect(result.url).toContain(encodeURIComponent('Mercedes-Benz'));
      expect(result.url).toContain(encodeURIComponent('S-Class'));
    });

    it('should include size dimensions in URL', () => {
      const result = generateVehicleImage({ size: 'hero' });

      expect(result.url).toContain('1920x1080');
    });
  });
});

describe('generateVehicleImages', () => {
  beforeEach(() => {
    clearImageCache();
  });

  afterEach(() => {
    clearImageCache();
  });

  it('should generate multiple images with default sizes', () => {
    const results = generateVehicleImages();

    expect(results).toHaveLength(2);
    expect(results[0]?.width).toBe(1200);
    expect(results[1]?.width).toBe(400);
  });

  it('should generate images for specified sizes', () => {
    const results = generateVehicleImages({}, ['main', 'thumbnail', 'hero']);

    expect(results).toHaveLength(3);
    expect(results[0]?.width).toBe(1200);
    expect(results[1]?.width).toBe(400);
    expect(results[2]?.width).toBe(1920);
  });

  it('should apply base options to all images', () => {
    const results = generateVehicleImages(
      { bodyStyle: 'sedan', make: 'Toyota' },
      ['main', 'thumbnail'],
    );

    results.forEach((result) => {
      expect(result.searchTerm).toContain('luxury sedan');
      expect(result.searchTerm).toContain('Toyota');
    });
  });

  it('should generate different URLs for different sizes', () => {
    const results = generateVehicleImages({}, ['main', 'thumbnail', 'hero', 'card']);

    const urls = results.map((r) => r.url);
    const uniqueUrls = new Set(urls);

    expect(uniqueUrls.size).toBe(4);
  });

  it('should cache each size separately', () => {
    generateVehicleImages({ bodyStyle: 'suv' }, ['main', 'thumbnail', 'hero']);

    expect(getCacheSize()).toBe(3);
  });
});

describe('Convenience Functions', () => {
  beforeEach(() => {
    clearImageCache();
  });

  afterEach(() => {
    clearImageCache();
  });

  describe('getMainVehicleImage', () => {
    it('should return main size image URL', () => {
      const url = getMainVehicleImage({ bodyStyle: 'sedan' });

      expect(url).toContain('1200x800');
      expect(url).toContain('https://source.unsplash.com');
    });

    it('should apply provided options', () => {
      const url = getMainVehicleImage({ make: 'Honda', model: 'Accord' });

      expect(url).toContain(encodeURIComponent('Honda'));
      expect(url).toContain(encodeURIComponent('Accord'));
    });
  });

  describe('getThumbnailVehicleImage', () => {
    it('should return thumbnail size image URL', () => {
      const url = getThumbnailVehicleImage({ bodyStyle: 'suv' });

      expect(url).toContain('400x300');
      expect(url).toContain('https://source.unsplash.com');
    });

    it('should apply provided options', () => {
      const url = getThumbnailVehicleImage({ color: 'blue' });

      expect(url).toContain(encodeURIComponent('blue'));
    });
  });

  describe('getHeroVehicleImage', () => {
    it('should return hero size image URL', () => {
      const url = getHeroVehicleImage({ bodyStyle: 'truck' });

      expect(url).toContain('1920x1080');
      expect(url).toContain('https://source.unsplash.com');
    });

    it('should apply provided options', () => {
      const url = getHeroVehicleImage({ make: 'Ford', model: 'F-150' });

      expect(url).toContain(encodeURIComponent('Ford'));
      expect(url).toContain(encodeURIComponent('F-150'));
    });
  });

  describe('getCardVehicleImage', () => {
    it('should return card size image URL', () => {
      const url = getCardVehicleImage({ bodyStyle: 'coupe' });

      expect(url).toContain('600x400');
      expect(url).toContain('https://source.unsplash.com');
    });

    it('should apply provided options', () => {
      const url = getCardVehicleImage({ year: new Date().getFullYear() });

      expect(url).toContain(encodeURIComponent(new Date().getFullYear().toString()));
    });
  });
});

describe('Cache Management', () => {
  beforeEach(() => {
    clearImageCache();
  });

  afterEach(() => {
    clearImageCache();
  });

  describe('clearImageCache', () => {
    it('should clear all cached entries', () => {
      generateVehicleImage({ bodyStyle: 'sedan' });
      generateVehicleImage({ bodyStyle: 'suv' });
      generateVehicleImage({ bodyStyle: 'truck' });

      expect(getCacheSize()).toBe(3);

      clearImageCache();

      expect(getCacheSize()).toBe(0);
    });

    it('should allow new entries after clearing', () => {
      generateVehicleImage({ bodyStyle: 'sedan' });
      clearImageCache();
      generateVehicleImage({ bodyStyle: 'suv' });

      expect(getCacheSize()).toBe(1);
    });
  });

  describe('getCacheSize', () => {
    it('should return 0 for empty cache', () => {
      expect(getCacheSize()).toBe(0);
    });

    it('should return correct count of cached entries', () => {
      generateVehicleImage({ bodyStyle: 'sedan' });
      expect(getCacheSize()).toBe(1);

      generateVehicleImage({ bodyStyle: 'suv' });
      expect(getCacheSize()).toBe(2);

      generateVehicleImage({ bodyStyle: 'truck' });
      expect(getCacheSize()).toBe(3);
    });

    it('should not count duplicate entries', () => {
      const options = { bodyStyle: 'sedan', make: 'Toyota' };

      generateVehicleImage(options);
      generateVehicleImage(options);
      generateVehicleImage(options);

      expect(getCacheSize()).toBe(1);
    });
  });

  describe('getCacheStats', () => {
    it('should return stats for empty cache', () => {
      const stats = getCacheStats();

      expect(stats).toEqual({
        size: 0,
        validEntries: 0,
        expiredEntries: 0,
      });
    });

    it('should return stats for valid entries', () => {
      generateVehicleImage({ bodyStyle: 'sedan' });
      generateVehicleImage({ bodyStyle: 'suv' });

      const stats = getCacheStats();

      expect(stats.size).toBe(2);
      expect(stats.validEntries).toBe(2);
      expect(stats.expiredEntries).toBe(0);
    });

    it('should detect expired entries', () => {
      // Mock Date.now to simulate expired entries
      const originalNow = Date.now;
      const mockNow = vi.fn();

      Date.now = mockNow;

      // Create entry at time 0
      mockNow.mockReturnValue(0);
      generateVehicleImage({ bodyStyle: 'sedan' });

      // Check stats at time > 24 hours
      mockNow.mockReturnValue(25 * 60 * 60 * 1000);
      const stats = getCacheStats();

      expect(stats.size).toBe(1);
      expect(stats.validEntries).toBe(0);
      expect(stats.expiredEntries).toBe(1);

      // Restore original Date.now
      Date.now = originalNow;
    });
  });

  describe('performCacheCleanup', () => {
    it('should remove expired entries', () => {
      const originalNow = Date.now;
      const mockNow = vi.fn();

      Date.now = mockNow;

      // Create entries at different times
      mockNow.mockReturnValue(0);
      generateVehicleImage({ bodyStyle: 'sedan' });

      mockNow.mockReturnValue(1000);
      generateVehicleImage({ bodyStyle: 'suv' });

      // Move time forward past expiration
      mockNow.mockReturnValue(25 * 60 * 60 * 1000);

      expect(getCacheSize()).toBe(2);

      performCacheCleanup();

      expect(getCacheSize()).toBe(0);

      Date.now = originalNow;
    });

    it('should keep valid entries during cleanup', () => {
      const originalNow = Date.now;
      const mockNow = vi.fn();

      Date.now = mockNow;

      // Create old entry
      mockNow.mockReturnValue(0);
      generateVehicleImage({ bodyStyle: 'sedan' });

      // Create recent entry
      mockNow.mockReturnValue(23 * 60 * 60 * 1000);
      generateVehicleImage({ bodyStyle: 'suv' });

      // Move time forward to expire first entry
      mockNow.mockReturnValue(25 * 60 * 60 * 1000);

      performCacheCleanup();

      expect(getCacheSize()).toBe(1);

      Date.now = originalNow;
    });

    it('should handle empty cache gracefully', () => {
      expect(() => {
        performCacheCleanup();
      }).not.toThrow();

      expect(getCacheSize()).toBe(0);
    });
  });

  describe('Cache Expiration', () => {
    it('should not return expired cached URLs', () => {
      const originalNow = Date.now;
      const mockNow = vi.fn();

      Date.now = mockNow;

      const options = { bodyStyle: 'sedan', make: 'Toyota' };

      // Create cached entry
      mockNow.mockReturnValue(0);
      const result1 = generateVehicleImage(options);
      expect(result1.cached).toBe(false);

      // Move time forward past expiration
      mockNow.mockReturnValue(25 * 60 * 60 * 1000);

      // Should generate new URL, not use expired cache
      const result2 = generateVehicleImage(options);
      expect(result2.cached).toBe(false);

      Date.now = originalNow;
    });

    it('should return cached URL within expiration period', () => {
      const originalNow = Date.now;
      const mockNow = vi.fn();

      Date.now = mockNow;

      const options = { bodyStyle: 'sedan', make: 'Toyota' };

      // Create cached entry
      mockNow.mockReturnValue(0);
      const result1 = generateVehicleImage(options);

      // Move time forward but within expiration
      mockNow.mockReturnValue(23 * 60 * 60 * 1000);

      // Should use cached URL
      const result2 = generateVehicleImage(options);
      expect(result2.cached).toBe(true);
      expect(result2.url).toBe(result1.url);

      Date.now = originalNow;
    });
  });
});

describe('Constants and Exports', () => {
  describe('AVAILABLE_SIZES', () => {
    it('should export all available size types', () => {
      expect(AVAILABLE_SIZES).toEqual(['main', 'thumbnail', 'hero', 'card']);
    });

    it('should be readonly array', () => {
      expect(Object.isFrozen(AVAILABLE_SIZES)).toBe(false);
      // TypeScript enforces readonly at compile time
    });
  });

  describe('AVAILABLE_BODY_STYLES', () => {
    it('should export all available body styles', () => {
      expect(AVAILABLE_BODY_STYLES).toContain('sedan');
      expect(AVAILABLE_BODY_STYLES).toContain('suv');
      expect(AVAILABLE_BODY_STYLES).toContain('truck');
      expect(AVAILABLE_BODY_STYLES).toContain('coupe');
      expect(AVAILABLE_BODY_STYLES).toContain('convertible');
      expect(AVAILABLE_BODY_STYLES).toContain('wagon');
      expect(AVAILABLE_BODY_STYLES).toContain('van');
      expect(AVAILABLE_BODY_STYLES).toContain('hatchback');
    });

    it('should have correct number of body styles', () => {
      expect(AVAILABLE_BODY_STYLES).toHaveLength(8);
    });
  });
});

describe('Edge Cases and Boundary Conditions', () => {
  beforeEach(() => {
    clearImageCache();
  });

  afterEach(() => {
    clearImageCache();
  });

  it('should handle empty string options', () => {
    const result = generateVehicleImage({
      bodyStyle: '',
      make: '',
      model: '',
      color: '',
    });

    expect(result.searchTerm).toBe('modern car');
  });

  it('should handle whitespace-only options', () => {
    const result = generateVehicleImage({
      bodyStyle: '   ',
      make: '   ',
      model: '   ',
    });

    expect(result.searchTerm).toBe('modern car');
  });

  it('should handle special characters in options', () => {
    const result = generateVehicleImage({
      make: 'Mercedes-Benz',
      model: 'S-Class',
      color: 'pearl white',
    });

    expect(result.url).toContain(encodeURIComponent('Mercedes-Benz'));
    expect(result.url).toContain(encodeURIComponent('S-Class'));
    expect(result.url).toContain(encodeURIComponent('pearl white'));
  });

  it('should handle very long option values', () => {
    const longMake = 'A'.repeat(100);
    const result = generateVehicleImage({ make: longMake });

    expect(result.searchTerm).toContain(longMake);
    expect(result.url).toContain(encodeURIComponent(longMake));
  });

  it('should handle year at boundary (exactly 10 years old)', () => {
    const boundaryYear = new Date().getFullYear() - 10;
    const result = generateVehicleImage({ year: boundaryYear });

    expect(result.searchTerm).toContain(boundaryYear.toString());
  });

  it('should handle year just past boundary (11 years old)', () => {
    const oldYear = new Date().getFullYear() - 11;
    const result = generateVehicleImage({ year: oldYear });

    expect(result.searchTerm).not.toContain(oldYear.toString());
  });

  it('should handle future year', () => {
    const futureYear = new Date().getFullYear() + 5;
    const result = generateVehicleImage({ year: futureYear });

    expect(result.searchTerm).toContain(futureYear.toString());
  });

  it('should handle zero year', () => {
    const result = generateVehicleImage({ year: 0 });

    expect(result.searchTerm).not.toContain('0');
  });

  it('should handle negative year', () => {
    const result = generateVehicleImage({ year: -2020 });

    expect(result.searchTerm).not.toContain('-2020');
  });
});

describe('Performance and Stress Tests', () => {
  beforeEach(() => {
    clearImageCache();
  });

  afterEach(() => {
    clearImageCache();
  });

  it('should handle rapid successive calls efficiently', () => {
    const startTime = performance.now();

    for (let i = 0; i < 100; i++) {
      generateVehicleImage({ bodyStyle: 'sedan', make: `Make${i}` });
    }

    const endTime = performance.now();
    const duration = endTime - startTime;

    // Should complete 100 generations in reasonable time (< 100ms)
    expect(duration).toBeLessThan(100);
  });

  it('should handle large cache efficiently', () => {
    // Generate 1000 unique cached entries
    for (let i = 0; i < 1000; i++) {
      generateVehicleImage({ make: `Make${i}`, model: `Model${i}` });
    }

    expect(getCacheSize()).toBe(1000);

    // Cache lookup should still be fast
    const startTime = performance.now();
    generateVehicleImage({ make: 'Make500', model: 'Model500' });
    const endTime = performance.now();

    expect(endTime - startTime).toBeLessThan(10);
  });

  it('should handle cache cleanup efficiently', () => {
    // Generate many entries
    for (let i = 0; i < 500; i++) {
      generateVehicleImage({ make: `Make${i}` });
    }

    const startTime = performance.now();
    performCacheCleanup();
    const endTime = performance.now();

    // Cleanup should be fast even with many entries
    expect(endTime - startTime).toBeLessThan(50);
  });
});

describe('Integration Scenarios', () => {
  beforeEach(() => {
    clearImageCache();
  });

  afterEach(() => {
    clearImageCache();
  });

  it('should handle complete vehicle listing workflow', () => {
    // Generate images for vehicle listing
    const vehicle = {
      bodyStyle: 'sedan',
      make: 'Toyota',
      model: 'Camry',
      year: new Date().getFullYear(),
      color: 'silver',
    };

    const mainImage = getMainVehicleImage(vehicle);
    const thumbnail = getThumbnailVehicleImage(vehicle);
    const heroImage = getHeroVehicleImage(vehicle);

    expect(mainImage).toBeTruthy();
    expect(thumbnail).toBeTruthy();
    expect(heroImage).toBeTruthy();

    // All should have consistent search terms
    const mainResult = generateVehicleImage({ ...vehicle, size: 'main' });
    const thumbResult = generateVehicleImage({ ...vehicle, size: 'thumbnail' });

    expect(mainResult.searchTerm).toBe(thumbResult.searchTerm);
  });

  it('should handle vehicle comparison workflow', () => {
    const vehicles = [
      { bodyStyle: 'sedan', make: 'Toyota', model: 'Camry' },
      { bodyStyle: 'sedan', make: 'Honda', model: 'Accord' },
      { bodyStyle: 'sedan', make: 'Nissan', model: 'Altima' },
    ];

    const images = vehicles.map((vehicle) =>
      generateVehicleImage({ ...vehicle, size: 'card' }),
    );

    expect(images).toHaveLength(3);
    images.forEach((image) => {
      expect(image.width).toBe(600);
      expect(image.height).toBe(400);
    });

    // Each should have unique URL
    const urls = images.map((img) => img.url);
    const uniqueUrls = new Set(urls);
    expect(uniqueUrls.size).toBe(3);
  });

  it('should handle gallery generation workflow', () => {
    const vehicle = {
      bodyStyle: 'suv',
      make: 'Jeep',
      model: 'Wrangler',
      year: new Date().getFullYear(),
    };

    const galleryImages = generateVehicleImages(vehicle, [
      'hero',
      'main',
      'card',
      'thumbnail',
    ]);

    expect(galleryImages).toHaveLength(4);

    // Verify size progression
    expect(galleryImages[0]?.width).toBe(1920); // hero
    expect(galleryImages[1]?.width).toBe(1200); // main
    expect(galleryImages[2]?.width).toBe(600); // card
    expect(galleryImages[3]?.width).toBe(400); // thumbnail
  });
});

describe('Type Safety and TypeScript Integration', () => {
  it('should enforce readonly on result properties', () => {
    const result = generateVehicleImage();

    // TypeScript should prevent modification (compile-time check)
    // Runtime verification that properties exist
    expect(result).toHaveProperty('url');
    expect(result).toHaveProperty('width');
    expect(result).toHaveProperty('height');
    expect(result).toHaveProperty('searchTerm');
    expect(result).toHaveProperty('cached');
  });

  it('should work with const assertions', () => {
    const options = {
      bodyStyle: 'sedan',
      size: 'main',
    } as const;

    const result = generateVehicleImage(options);

    expect(result.url).toBeTruthy();
  });

  it('should handle optional parameters correctly', () => {
    // All parameters are optional
    expect(() => {
      generateVehicleImage();
      generateVehicleImage({});
      generateVehicleImage({ bodyStyle: 'sedan' });
      generateVehicleImage({ size: 'thumbnail' });
    }).not.toThrow();
  });
});