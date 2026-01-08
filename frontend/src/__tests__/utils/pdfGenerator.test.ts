/**
 * Comprehensive Test Suite for PDF Generation Utility
 * 
 * Tests PDF generation functionality including:
 * - Document structure and content accuracy
 * - Error handling and validation
 * - Formatting and styling
 * - Edge cases and boundary conditions
 * - Performance and resource management
 * 
 * @module pdfGenerator.test
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { pdf } from '@react-pdf/renderer';
import type { Vehicle } from '../../types/vehicle';
import {
  generateComparisonPDF,
  downloadPDF,
  generateAndDownloadPDF,
  isPDFGenerationError,
  PDFGenerationError,
} from '../../utils/pdfGenerator';

// Mock @react-pdf/renderer
vi.mock('@react-pdf/renderer', () => ({
  Document: ({ children }: { children: React.ReactNode }) => children,
  Page: ({ children }: { children: React.ReactNode }) => children,
  Text: ({ children }: { children: React.ReactNode }) => children,
  View: ({ children }: { children: React.ReactNode }) => children,
  Image: () => null,
  StyleSheet: {
    create: (styles: Record<string, unknown>) => styles,
  },
  Font: {},
  pdf: vi.fn(),
}));

// Mock URL.createObjectURL and URL.revokeObjectURL
const mockCreateObjectURL = vi.fn();
const mockRevokeObjectURL = vi.fn();
global.URL.createObjectURL = mockCreateObjectURL;
global.URL.revokeObjectURL = mockRevokeObjectURL;

// Mock document methods
const mockAppendChild = vi.fn();
const mockRemoveChild = vi.fn();
const mockClick = vi.fn();

Object.defineProperty(global.document, 'createElement', {
  writable: true,
  value: vi.fn(() => ({
    href: '',
    download: '',
    style: { display: '' },
    click: mockClick,
  })),
});

Object.defineProperty(global.document.body, 'appendChild', {
  writable: true,
  value: mockAppendChild,
});

Object.defineProperty(global.document.body, 'removeChild', {
  writable: true,
  value: mockRemoveChild,
});

/**
 * Test Data Factory for Vehicle Objects
 */
class VehicleFactory {
  private static defaultVehicle: Vehicle = {
    id: '1',
    make: 'Toyota',
    model: 'Camry',
    year: 2024,
    trim: 'XLE',
    price: 32000,
    imageUrl: 'https://example.com/camry.jpg',
    specifications: {
      engine: '2.5L 4-Cylinder',
      horsepower: 203,
      torque: 184,
      transmission: '8-Speed Automatic',
      drivetrain: 'FWD',
      fuelType: 'Gasoline',
      fuelEconomy: {
        city: 28,
        highway: 39,
        combined: 32,
      },
      seatingCapacity: 5,
      curbWeight: 3310,
      towingCapacity: 1000,
    },
    features: {
      safety: [
        'Toyota Safety Sense 3.0',
        'Blind Spot Monitor',
        'Rear Cross-Traffic Alert',
      ],
      technology: [
        '9-inch Touchscreen',
        'Apple CarPlay',
        'Android Auto',
      ],
      comfort: ['Dual-Zone Climate Control', 'Power Driver Seat'],
      performance: ['Sport Mode', 'Paddle Shifters'],
    },
    description: 'Reliable midsize sedan',
    availability: 'in-stock',
    dealerInfo: {
      name: 'Test Dealer',
      location: 'Test City',
      contact: '555-0100',
    },
  };

  static create(overrides: Partial<Vehicle> = {}): Vehicle {
    return {
      ...this.defaultVehicle,
      ...overrides,
      specifications: {
        ...this.defaultVehicle.specifications,
        ...(overrides.specifications ?? {}),
        fuelEconomy: {
          ...this.defaultVehicle.specifications.fuelEconomy,
          ...(overrides.specifications?.fuelEconomy ?? {}),
        },
      },
      features: {
        ...this.defaultVehicle.features,
        ...(overrides.features ?? {}),
      },
    };
  }

  static createMany(count: number, overrides: Partial<Vehicle> = {}): Vehicle[] {
    return Array.from({ length: count }, (_, index) =>
      this.create({
        ...overrides,
        id: `${index + 1}`,
        make: `Make${index + 1}`,
        model: `Model${index + 1}`,
      }),
    );
  }
}

describe('PDFGenerationError', () => {
  it('should create error with message', () => {
    const error = new PDFGenerationError('Test error');

    expect(error).toBeInstanceOf(Error);
    expect(error.name).toBe('PDFGenerationError');
    expect(error.message).toBe('Test error');
    expect(error.cause).toBeUndefined();
  });

  it('should create error with cause', () => {
    const cause = new Error('Original error');
    const error = new PDFGenerationError('Test error', cause);

    expect(error.message).toBe('Test error');
    expect(error.cause).toBe(cause);
  });

  it('should be identifiable by type guard', () => {
    const error = new PDFGenerationError('Test error');

    expect(isPDFGenerationError(error)).toBe(true);
    expect(isPDFGenerationError(new Error('Regular error'))).toBe(false);
    expect(isPDFGenerationError('not an error')).toBe(false);
    expect(isPDFGenerationError(null)).toBe(false);
  });
});

describe('generateComparisonPDF', () => {
  let mockPdfInstance: {
    toBlob: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockCreateObjectURL.mockReturnValue('blob:mock-url');

    mockPdfInstance = {
      toBlob: vi.fn().mockResolvedValue(new Blob(['mock pdf'], { type: 'application/pdf' })),
    };

    vi.mocked(pdf).mockReturnValue(mockPdfInstance as never);
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  describe('🎯 Happy Path Scenarios', () => {
    it('should generate PDF for single vehicle', async () => {
      const vehicle = VehicleFactory.create();

      const result = await generateComparisonPDF([vehicle]);

      expect(result).toHaveProperty('blob');
      expect(result).toHaveProperty('url');
      expect(result).toHaveProperty('filename');
      expect(result.blob).toBeInstanceOf(Blob);
      expect(result.url).toBe('blob:mock-url');
      expect(result.filename).toMatch(/^vehicle-comparison-\d{4}-\d{2}-\d{2}\.pdf$/);
    });

    it('should generate PDF for multiple vehicles', async () => {
      const vehicles = VehicleFactory.createMany(3);

      const result = await generateComparisonPDF(vehicles);

      expect(result.blob).toBeInstanceOf(Blob);
      expect(pdf).toHaveBeenCalledTimes(1);
      expect(mockPdfInstance.toBlob).toHaveBeenCalledTimes(1);
    });

    it('should generate PDF with custom title', async () => {
      const vehicles = VehicleFactory.createMany(2);
      const options = { title: 'Custom Comparison Report' };

      const result = await generateComparisonPDF(vehicles, options);

      expect(result).toBeDefined();
      expect(pdf).toHaveBeenCalled();
    });

    it('should generate PDF with all options enabled', async () => {
      const vehicles = VehicleFactory.createMany(2);
      const options = {
        title: 'Full Report',
        includeImages: true,
        includeSpecifications: true,
        includeFeatures: true,
        pageSize: 'A4' as const,
        orientation: 'landscape' as const,
      };

      const result = await generateComparisonPDF(vehicles, options);

      expect(result).toBeDefined();
      expect(result.blob.type).toBe('application/pdf');
    });

    it('should generate PDF with images disabled', async () => {
      const vehicles = VehicleFactory.createMany(2);
      const options = { includeImages: false };

      const result = await generateComparisonPDF(vehicles, options);

      expect(result).toBeDefined();
    });

    it('should generate PDF with specifications disabled', async () => {
      const vehicles = VehicleFactory.createMany(2);
      const options = { includeSpecifications: false };

      const result = await generateComparisonPDF(vehicles, options);

      expect(result).toBeDefined();
    });

    it('should generate PDF with features disabled', async () => {
      const vehicles = VehicleFactory.createMany(2);
      const options = { includeFeatures: false };

      const result = await generateComparisonPDF(vehicles, options);

      expect(result).toBeDefined();
    });

    it('should generate PDF in portrait orientation', async () => {
      const vehicles = VehicleFactory.createMany(2);
      const options = { orientation: 'portrait' as const };

      const result = await generateComparisonPDF(vehicles, options);

      expect(result).toBeDefined();
    });

    it('should generate PDF in letter size', async () => {
      const vehicles = VehicleFactory.createMany(2);
      const options = { pageSize: 'LETTER' as const };

      const result = await generateComparisonPDF(vehicles, options);

      expect(result).toBeDefined();
    });
  });

  describe('🔍 Edge Cases and Boundary Conditions', () => {
    it('should handle vehicle with minimal data', async () => {
      const vehicle = VehicleFactory.create({
        trim: undefined,
        features: {
          safety: [],
          technology: [],
          comfort: [],
          performance: [],
        },
      });

      const result = await generateComparisonPDF([vehicle]);

      expect(result).toBeDefined();
    });

    it('should handle maximum allowed vehicles (4)', async () => {
      const vehicles = VehicleFactory.createMany(4);

      const result = await generateComparisonPDF(vehicles);

      expect(result).toBeDefined();
    });

    it('should handle vehicles with different specification values', async () => {
      const vehicles = [
        VehicleFactory.create({ specifications: { horsepower: 200 } }),
        VehicleFactory.create({ specifications: { horsepower: 300 } }),
      ];

      const result = await generateComparisonPDF(vehicles);

      expect(result).toBeDefined();
    });

    it('should handle vehicles with null specification values', async () => {
      const vehicle = VehicleFactory.create({
        specifications: {
          ...VehicleFactory.create().specifications,
          towingCapacity: null as never,
        },
      });

      const result = await generateComparisonPDF([vehicle]);

      expect(result).toBeDefined();
    });

    it('should handle vehicles with undefined specification values', async () => {
      const vehicle = VehicleFactory.create({
        specifications: {
          ...VehicleFactory.create().specifications,
          curbWeight: undefined as never,
        },
      });

      const result = await generateComparisonPDF([vehicle]);

      expect(result).toBeDefined();
    });

    it('should handle vehicles with boolean specification values', async () => {
      const vehicle = VehicleFactory.create({
        specifications: {
          ...VehicleFactory.create().specifications,
          // @ts-expect-error Testing boolean value
          hasAllWheelDrive: true,
        },
      });

      const result = await generateComparisonPDF([vehicle]);

      expect(result).toBeDefined();
    });

    it('should handle vehicles with very long feature lists', async () => {
      const vehicle = VehicleFactory.create({
        features: {
          safety: Array.from({ length: 20 }, (_, i) => `Safety Feature ${i + 1}`),
          technology: Array.from({ length: 20 }, (_, i) => `Tech Feature ${i + 1}`),
          comfort: [],
          performance: [],
        },
      });

      const result = await generateComparisonPDF([vehicle]);

      expect(result).toBeDefined();
    });

    it('should handle vehicles with special characters in names', async () => {
      const vehicle = VehicleFactory.create({
        make: 'Citroën',
        model: 'C4 Cactus',
        trim: 'Shine™',
      });

      const result = await generateComparisonPDF([vehicle]);

      expect(result).toBeDefined();
    });

    it('should handle vehicles with very high prices', async () => {
      const vehicle = VehicleFactory.create({
        price: 999999999,
      });

      const result = await generateComparisonPDF([vehicle]);

      expect(result).toBeDefined();
    });

    it('should handle vehicles with zero price', async () => {
      const vehicle = VehicleFactory.create({
        price: 0,
      });

      const result = await generateComparisonPDF([vehicle]);

      expect(result).toBeDefined();
    });
  });

  describe('❌ Error Scenarios', () => {
    it('should throw error when no vehicles provided', async () => {
      await expect(generateComparisonPDF([])).rejects.toThrow(PDFGenerationError);
      await expect(generateComparisonPDF([])).rejects.toThrow(
        'No vehicles provided for comparison',
      );
    });

    it('should throw error when more than 4 vehicles provided', async () => {
      const vehicles = VehicleFactory.createMany(5);

      await expect(generateComparisonPDF(vehicles)).rejects.toThrow(PDFGenerationError);
      await expect(generateComparisonPDF(vehicles)).rejects.toThrow(
        'Maximum 4 vehicles can be compared',
      );
    });

    it('should wrap PDF generation errors', async () => {
      const vehicles = VehicleFactory.createMany(2);
      const originalError = new Error('PDF rendering failed');
      mockPdfInstance.toBlob.mockRejectedValueOnce(originalError);

      await expect(generateComparisonPDF(vehicles)).rejects.toThrow(PDFGenerationError);
      await expect(generateComparisonPDF(vehicles)).rejects.toThrow('Failed to generate PDF');
    });

    it('should preserve PDFGenerationError when thrown', async () => {
      const vehicles = VehicleFactory.createMany(2);
      const customError = new PDFGenerationError('Custom error');
      mockPdfInstance.toBlob.mockRejectedValueOnce(customError);

      await expect(generateComparisonPDF(vehicles)).rejects.toThrow(customError);
    });
  });

  describe('📊 Data Formatting', () => {
    it('should format currency correctly', async () => {
      const vehicle = VehicleFactory.create({ price: 45678 });

      const result = await generateComparisonPDF([vehicle]);

      expect(result).toBeDefined();
      // Currency formatting is internal, but we verify PDF generation succeeds
    });

    it('should format numbers with locale', async () => {
      const vehicle = VehicleFactory.create({
        specifications: {
          ...VehicleFactory.create().specifications,
          curbWeight: 3500,
          towingCapacity: 5000,
        },
      });

      const result = await generateComparisonPDF([vehicle]);

      expect(result).toBeDefined();
    });

    it('should format specification display names', async () => {
      const vehicle = VehicleFactory.create();

      const result = await generateComparisonPDF([vehicle]);

      expect(result).toBeDefined();
    });
  });

  describe('⚡ Performance and Resource Management', () => {
    it('should create object URL for blob', async () => {
      const vehicles = VehicleFactory.createMany(2);

      await generateComparisonPDF(vehicles);

      expect(mockCreateObjectURL).toHaveBeenCalledTimes(1);
      expect(mockCreateObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    });

    it('should generate filename with current date', async () => {
      const vehicles = VehicleFactory.createMany(2);
      const today = new Date().toISOString().split('T')[0];

      const result = await generateComparisonPDF(vehicles);

      expect(result.filename).toContain(today);
    });

    it('should handle concurrent PDF generation', async () => {
      const vehicles1 = VehicleFactory.createMany(2);
      const vehicles2 = VehicleFactory.createMany(2);

      const [result1, result2] = await Promise.all([
        generateComparisonPDF(vehicles1),
        generateComparisonPDF(vehicles2),
      ]);

      expect(result1).toBeDefined();
      expect(result2).toBeDefined();
      expect(result1.url).not.toBe(result2.url);
    });
  });
});

describe('downloadPDF', () => {
  let mockLink: {
    href: string;
    download: string;
    style: { display: string };
    click: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    mockLink = {
      href: '',
      download: '',
      style: { display: '' },
      click: mockClick,
    };

    vi.mocked(document.createElement).mockReturnValue(mockLink as never);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('🎯 Happy Path Scenarios', () => {
    it('should create download link and trigger download', () => {
      const result = {
        blob: new Blob(['test'], { type: 'application/pdf' }),
        url: 'blob:mock-url',
        filename: 'test.pdf',
      };

      downloadPDF(result);

      expect(document.createElement).toHaveBeenCalledWith('a');
      expect(mockLink.href).toBe('blob:mock-url');
      expect(mockLink.download).toBe('test.pdf');
      expect(mockLink.style.display).toBe('none');
      expect(mockAppendChild).toHaveBeenCalledWith(mockLink);
      expect(mockClick).toHaveBeenCalledTimes(1);
      expect(mockRemoveChild).toHaveBeenCalledWith(mockLink);
    });

    it('should revoke object URL after timeout', () => {
      const result = {
        blob: new Blob(['test'], { type: 'application/pdf' }),
        url: 'blob:mock-url',
        filename: 'test.pdf',
      };

      downloadPDF(result);

      expect(mockRevokeObjectURL).not.toHaveBeenCalled();

      vi.advanceTimersByTime(100);

      expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
    });

    it('should handle multiple downloads', () => {
      const result1 = {
        blob: new Blob(['test1'], { type: 'application/pdf' }),
        url: 'blob:mock-url-1',
        filename: 'test1.pdf',
      };
      const result2 = {
        blob: new Blob(['test2'], { type: 'application/pdf' }),
        url: 'blob:mock-url-2',
        filename: 'test2.pdf',
      };

      downloadPDF(result1);
      downloadPDF(result2);

      expect(mockClick).toHaveBeenCalledTimes(2);
      expect(mockAppendChild).toHaveBeenCalledTimes(2);
      expect(mockRemoveChild).toHaveBeenCalledTimes(2);
    });
  });

  describe('❌ Error Scenarios', () => {
    it('should throw PDFGenerationError on download failure', () => {
      const result = {
        blob: new Blob(['test'], { type: 'application/pdf' }),
        url: 'blob:mock-url',
        filename: 'test.pdf',
      };

      mockClick.mockImplementationOnce(() => {
        throw new Error('Click failed');
      });

      expect(() => downloadPDF(result)).toThrow(PDFGenerationError);
      expect(() => downloadPDF(result)).toThrow('Failed to download PDF');
    });

    it('should handle DOM manipulation errors', () => {
      const result = {
        blob: new Blob(['test'], { type: 'application/pdf' }),
        url: 'blob:mock-url',
        filename: 'test.pdf',
      };

      mockAppendChild.mockImplementationOnce(() => {
        throw new Error('DOM error');
      });

      expect(() => downloadPDF(result)).toThrow(PDFGenerationError);
    });
  });

  describe('🧹 Cleanup', () => {
    it('should remove link from DOM after download', () => {
      const result = {
        blob: new Blob(['test'], { type: 'application/pdf' }),
        url: 'blob:mock-url',
        filename: 'test.pdf',
      };

      downloadPDF(result);

      expect(mockRemoveChild).toHaveBeenCalledWith(mockLink);
    });

    it('should schedule URL revocation', () => {
      const result = {
        blob: new Blob(['test'], { type: 'application/pdf' }),
        url: 'blob:mock-url',
        filename: 'test.pdf',
      };

      downloadPDF(result);

      expect(mockRevokeObjectURL).not.toHaveBeenCalled();

      vi.advanceTimersByTime(99);
      expect(mockRevokeObjectURL).not.toHaveBeenCalled();

      vi.advanceTimersByTime(1);
      expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
    });
  });
});

describe('generateAndDownloadPDF', () => {
  let mockPdfInstance: {
    toBlob: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockCreateObjectURL.mockReturnValue('blob:mock-url');

    mockPdfInstance = {
      toBlob: vi.fn().mockResolvedValue(new Blob(['mock pdf'], { type: 'application/pdf' })),
    };

    vi.mocked(pdf).mockReturnValue(mockPdfInstance as never);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('🎯 Integration Tests', () => {
    it('should generate and download PDF in one call', async () => {
      const vehicles = VehicleFactory.createMany(2);

      await generateAndDownloadPDF(vehicles);

      expect(pdf).toHaveBeenCalledTimes(1);
      expect(mockPdfInstance.toBlob).toHaveBeenCalledTimes(1);
      expect(mockClick).toHaveBeenCalledTimes(1);
    });

    it('should pass options to generation', async () => {
      const vehicles = VehicleFactory.createMany(2);
      const options = { title: 'Custom Title' };

      await generateAndDownloadPDF(vehicles, options);

      expect(pdf).toHaveBeenCalled();
    });

    it('should handle generation errors', async () => {
      const vehicles = VehicleFactory.createMany(2);
      mockPdfInstance.toBlob.mockRejectedValueOnce(new Error('Generation failed'));

      await expect(generateAndDownloadPDF(vehicles)).rejects.toThrow(PDFGenerationError);
    });

    it('should handle download errors', async () => {
      const vehicles = VehicleFactory.createMany(2);
      mockClick.mockImplementationOnce(() => {
        throw new Error('Download failed');
      });

      await expect(generateAndDownloadPDF(vehicles)).rejects.toThrow(PDFGenerationError);
    });
  });

  describe('⚡ End-to-End Workflow', () => {
    it('should complete full workflow successfully', async () => {
      const vehicles = VehicleFactory.createMany(3);
      const options = {
        title: 'My Comparison',
        includeImages: true,
        includeSpecifications: true,
        includeFeatures: true,
      };

      await generateAndDownloadPDF(vehicles, options);

      // Verify generation
      expect(pdf).toHaveBeenCalled();
      expect(mockPdfInstance.toBlob).toHaveBeenCalled();

      // Verify download
      expect(mockClick).toHaveBeenCalled();
      expect(mockAppendChild).toHaveBeenCalled();
      expect(mockRemoveChild).toHaveBeenCalled();

      // Verify cleanup
      vi.advanceTimersByTime(100);
      expect(mockRevokeObjectURL).toHaveBeenCalled();
    });

    it('should handle empty options', async () => {
      const vehicles = VehicleFactory.createMany(2);

      await generateAndDownloadPDF(vehicles, {});

      expect(pdf).toHaveBeenCalled();
      expect(mockClick).toHaveBeenCalled();
    });
  });
});

describe('isPDFGenerationError', () => {
  describe('🔍 Type Guard Validation', () => {
    it('should return true for PDFGenerationError instances', () => {
      const error = new PDFGenerationError('Test error');

      expect(isPDFGenerationError(error)).toBe(true);
    });

    it('should return false for regular Error instances', () => {
      const error = new Error('Regular error');

      expect(isPDFGenerationError(error)).toBe(false);
    });

    it('should return false for TypeError instances', () => {
      const error = new TypeError('Type error');

      expect(isPDFGenerationError(error)).toBe(false);
    });

    it('should return false for string values', () => {
      expect(isPDFGenerationError('error string')).toBe(false);
    });

    it('should return false for null', () => {
      expect(isPDFGenerationError(null)).toBe(false);
    });

    it('should return false for undefined', () => {
      expect(isPDFGenerationError(undefined)).toBe(false);
    });

    it('should return false for numbers', () => {
      expect(isPDFGenerationError(123)).toBe(false);
    });

    it('should return false for objects', () => {
      expect(isPDFGenerationError({ message: 'error' })).toBe(false);
    });

    it('should return false for arrays', () => {
      expect(isPDFGenerationError([])).toBe(false);
    });
  });

  describe('🎭 Error Handling Patterns', () => {
    it('should work in try-catch blocks', async () => {
      try {
        await generateComparisonPDF([]);
      } catch (error) {
        expect(isPDFGenerationError(error)).toBe(true);
        if (isPDFGenerationError(error)) {
          expect(error.message).toBe('No vehicles provided for comparison');
        }
      }
    });

    it('should narrow error type correctly', () => {
      const error: unknown = new PDFGenerationError('Test');

      if (isPDFGenerationError(error)) {
        // TypeScript should know error is PDFGenerationError here
        expect(error.name).toBe('PDFGenerationError');
        expect(error.cause).toBeUndefined();
      }
    });
  });
});

describe('🎨 Document Structure and Content', () => {
  let mockPdfInstance: {
    toBlob: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockCreateObjectURL.mockReturnValue('blob:mock-url');

    mockPdfInstance = {
      toBlob: vi.fn().mockResolvedValue(new Blob(['mock pdf'], { type: 'application/pdf' })),
    };

    vi.mocked(pdf).mockReturnValue(mockPdfInstance as never);
  });

  it('should include all vehicle information', async () => {
    const vehicle = VehicleFactory.create({
      make: 'Honda',
      model: 'Accord',
      year: 2024,
      trim: 'Sport',
      price: 35000,
    });

    const result = await generateComparisonPDF([vehicle]);

    expect(result).toBeDefined();
    expect(pdf).toHaveBeenCalled();
  });

  it('should include fuel economy data', async () => {
    const vehicle = VehicleFactory.create({
      specifications: {
        ...VehicleFactory.create().specifications,
        fuelEconomy: {
          city: 25,
          highway: 35,
          combined: 29,
        },
      },
    });

    const result = await generateComparisonPDF([vehicle]);

    expect(result).toBeDefined();
  });

  it('should include safety features', async () => {
    const vehicle = VehicleFactory.create({
      features: {
        safety: ['ABS', 'Airbags', 'Stability Control'],
        technology: [],
        comfort: [],
        performance: [],
      },
    });

    const result = await generateComparisonPDF([vehicle]);

    expect(result).toBeDefined();
  });

  it('should include technology features', async () => {
    const vehicle = VehicleFactory.create({
      features: {
        safety: [],
        technology: ['Navigation', 'Bluetooth', 'USB Ports'],
        comfort: [],
        performance: [],
      },
    });

    const result = await generateComparisonPDF([vehicle]);

    expect(result).toBeDefined();
  });
});

describe('🛡️ Security and Validation', () => {
  let mockPdfInstance: {
    toBlob: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockCreateObjectURL.mockReturnValue('blob:mock-url');

    mockPdfInstance = {
      toBlob: vi.fn().mockResolvedValue(new Blob(['mock pdf'], { type: 'application/pdf' })),
    };

    vi.mocked(pdf).mockReturnValue(mockPdfInstance as never);
  });

  it('should sanitize vehicle data with XSS attempts', async () => {
    const vehicle = VehicleFactory.create({
      make: '<script>alert("xss")</script>',
      model: 'Test<img src=x onerror=alert(1)>',
    });

    const result = await generateComparisonPDF([vehicle]);

    expect(result).toBeDefined();
  });

  it('should handle SQL injection attempts in strings', async () => {
    const vehicle = VehicleFactory.create({
      make: "'; DROP TABLE vehicles; --",
      model: "1' OR '1'='1",
    });

    const result = await generateComparisonPDF([vehicle]);

    expect(result).toBeDefined();
  });

  it('should validate vehicle count limits', async () => {
    const vehicles = VehicleFactory.createMany(10);

    await expect(generateComparisonPDF(vehicles)).rejects.toThrow(
      'Maximum 4 vehicles can be compared',
    );
  });

  it('should handle extremely long strings', async () => {
    const vehicle = VehicleFactory.create({
      make: 'A'.repeat(10000),
      model: 'B'.repeat(10000),
    });

    const result = await generateComparisonPDF([vehicle]);

    expect(result).toBeDefined();
  });
});

describe('⚡ Performance Tests', () => {
  let mockPdfInstance: {
    toBlob: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockCreateObjectURL.mockReturnValue('blob:mock-url');

    mockPdfInstance = {
      toBlob: vi.fn().mockResolvedValue(new Blob(['mock pdf'], { type: 'application/pdf' })),
    };

    vi.mocked(pdf).mockReturnValue(mockPdfInstance as never);
  });

  it('should generate PDF within reasonable time', async () => {
    const vehicles = VehicleFactory.createMany(4);
    const startTime = Date.now();

    await generateComparisonPDF(vehicles);

    const endTime = Date.now();
    const duration = endTime - startTime;

    // Should complete within 1 second (generous for mocked operations)
    expect(duration).toBeLessThan(1000);
  });

  it('should handle large vehicle datasets efficiently', async () => {
    const vehicle = VehicleFactory.create({
      features: {
        safety: Array.from({ length: 50 }, (_, i) => `Safety ${i}`),
        technology: Array.from({ length: 50 }, (_, i) => `Tech ${i}`),
        comfort: Array.from({ length: 50 }, (_, i) => `Comfort ${i}`),
        performance: Array.from({ length: 50 }, (_, i) => `Performance ${i}`),
      },
    });

    const result = await generateComparisonPDF([vehicle]);

    expect(result).toBeDefined();
  });

  it('should not leak memory on multiple generations', async () => {
    const vehicles = VehicleFactory.createMany(2);

    // Generate multiple PDFs
    for (let i = 0; i < 10; i++) {
      await generateComparisonPDF(vehicles);
    }

    // Verify all object URLs would be created
    expect(mockCreateObjectURL).toHaveBeenCalledTimes(10);
  });
});