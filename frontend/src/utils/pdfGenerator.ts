/**
 * PDF Generation Utility for Vehicle Comparison Reports
 * 
 * Generates professional PDF comparison reports using @react-pdf/renderer
 * with vehicle images, specifications table, and branding.
 * 
 * @module pdfGenerator
 */

import {
  Document,
  Page,
  Text,
  View,
  Image,
  StyleSheet,
  Font,
  pdf,
} from '@react-pdf/renderer';
import type { Vehicle } from '../types/vehicle';

/**
 * PDF generation options
 */
interface PDFGenerationOptions {
  readonly title?: string;
  readonly includeImages?: boolean;
  readonly includeSpecifications?: boolean;
  readonly includeFeatures?: boolean;
  readonly pageSize?: 'A4' | 'LETTER';
  readonly orientation?: 'portrait' | 'landscape';
}

/**
 * PDF generation result
 */
interface PDFGenerationResult {
  readonly blob: Blob;
  readonly url: string;
  readonly filename: string;
}

/**
 * Error thrown during PDF generation
 */
export class PDFGenerationError extends Error {
  constructor(
    message: string,
    public readonly cause?: unknown,
  ) {
    super(message);
    this.name = 'PDFGenerationError';
  }
}

/**
 * PDF styles configuration
 */
const styles = StyleSheet.create({
  page: {
    padding: 30,
    backgroundColor: '#ffffff',
    fontFamily: 'Helvetica',
  },
  header: {
    marginBottom: 20,
    borderBottom: '2 solid #2563eb',
    paddingBottom: 10,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1e40af',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 12,
    color: '#64748b',
  },
  vehicleSection: {
    marginBottom: 20,
  },
  vehicleHeader: {
    flexDirection: 'row',
    marginBottom: 10,
    alignItems: 'center',
  },
  vehicleImage: {
    width: 120,
    height: 80,
    objectFit: 'cover',
    borderRadius: 4,
    marginRight: 15,
  },
  vehicleInfo: {
    flex: 1,
  },
  vehicleName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 4,
  },
  vehiclePrice: {
    fontSize: 14,
    color: '#2563eb',
    fontWeight: 'bold',
  },
  table: {
    marginTop: 10,
  },
  tableRow: {
    flexDirection: 'row',
    borderBottom: '1 solid #e2e8f0',
    paddingVertical: 8,
  },
  tableHeader: {
    backgroundColor: '#f1f5f9',
    fontWeight: 'bold',
  },
  tableCell: {
    flex: 1,
    fontSize: 10,
    color: '#334155',
    paddingHorizontal: 5,
  },
  tableCellHeader: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#1e293b',
    paddingHorizontal: 5,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#1e293b',
    marginTop: 15,
    marginBottom: 8,
  },
  featuresList: {
    marginLeft: 10,
  },
  featureItem: {
    fontSize: 9,
    color: '#475569',
    marginBottom: 3,
  },
  footer: {
    position: 'absolute',
    bottom: 30,
    left: 30,
    right: 30,
    textAlign: 'center',
    fontSize: 8,
    color: '#94a3b8',
    borderTop: '1 solid #e2e8f0',
    paddingTop: 10,
  },
  comparisonGrid: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 20,
  },
  comparisonColumn: {
    flex: 1,
  },
  specRow: {
    flexDirection: 'row',
    paddingVertical: 6,
    borderBottom: '1 solid #f1f5f9',
  },
  specLabel: {
    flex: 1,
    fontSize: 9,
    color: '#64748b',
    fontWeight: 'bold',
  },
  specValue: {
    flex: 1,
    fontSize: 9,
    color: '#1e293b',
  },
  highlightedValue: {
    backgroundColor: '#fef3c7',
    padding: 2,
    borderRadius: 2,
  },
});

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
 * Format specification value
 */
function formatSpecValue(value: unknown): string {
  if (typeof value === 'number') {
    return value.toLocaleString('en-US');
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  if (value === null || value === undefined) {
    return 'N/A';
  }
  return String(value);
}

/**
 * Get specification display name
 */
function getSpecDisplayName(key: string): string {
  const displayNames: Record<string, string> = {
    engine: 'Engine',
    horsepower: 'Horsepower',
    torque: 'Torque (lb-ft)',
    transmission: 'Transmission',
    drivetrain: 'Drivetrain',
    fuelType: 'Fuel Type',
    seatingCapacity: 'Seating',
    curbWeight: 'Curb Weight (lbs)',
    towingCapacity: 'Towing Capacity (lbs)',
  };
  return displayNames[key] ?? key;
}

/**
 * Check if values are different for highlighting
 */
function shouldHighlight(values: readonly unknown[]): boolean {
  if (values.length <= 1) {
    return false;
  }
  const first = values[0];
  return values.some((v) => v !== first);
}

/**
 * Generate comparison table rows
 */
function generateComparisonRows(vehicles: readonly Vehicle[]): readonly {
  readonly label: string;
  readonly values: readonly string[];
  readonly highlight: boolean;
}[] {
  const specs = [
    'engine',
    'horsepower',
    'torque',
    'transmission',
    'drivetrain',
    'fuelType',
    'seatingCapacity',
    'curbWeight',
    'towingCapacity',
  ] as const;

  return specs.map((spec) => {
    const values = vehicles.map((v) => {
      const value = v.specifications[spec];
      return formatSpecValue(value);
    });

    return {
      label: getSpecDisplayName(spec),
      values,
      highlight: shouldHighlight(
        vehicles.map((v) => v.specifications[spec]),
      ),
    };
  });
}

/**
 * PDF Document Component
 */
function ComparisonDocument({
  vehicles,
  options,
}: {
  readonly vehicles: readonly Vehicle[];
  readonly options: PDFGenerationOptions;
}): JSX.Element {
  const title = options.title ?? 'Vehicle Comparison Report';
  const currentDate = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  const comparisonRows = generateComparisonRows(vehicles);

  return (
    <Document>
      <Page size={options.pageSize ?? 'A4'} orientation={options.orientation ?? 'landscape'} style={styles.page}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.subtitle}>Generated on {currentDate}</Text>
        </View>

        {/* Vehicle Images and Basic Info */}
        {options.includeImages !== false && (
          <View style={styles.comparisonGrid}>
            {vehicles.map((vehicle) => (
              <View key={vehicle.id} style={styles.comparisonColumn}>
                <Image
                  src={vehicle.imageUrl}
                  style={styles.vehicleImage}
                  cache={false}
                />
                <Text style={styles.vehicleName}>
                  {vehicle.year} {vehicle.make} {vehicle.model}
                </Text>
                {vehicle.trim && (
                  <Text style={{ fontSize: 10, color: '#64748b', marginBottom: 4 }}>
                    {vehicle.trim}
                  </Text>
                )}
                <Text style={styles.vehiclePrice}>
                  {formatCurrency(vehicle.price)}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* Specifications Comparison Table */}
        {options.includeSpecifications !== false && (
          <View style={styles.table}>
            <Text style={styles.sectionTitle}>Specifications Comparison</Text>
            
            {/* Table Header */}
            <View style={[styles.tableRow, styles.tableHeader]}>
              <Text style={[styles.tableCellHeader, { flex: 1.5 }]}>Specification</Text>
              {vehicles.map((vehicle) => (
                <Text key={vehicle.id} style={styles.tableCellHeader}>
                  {vehicle.make} {vehicle.model}
                </Text>
              ))}
            </View>

            {/* Table Rows */}
            {comparisonRows.map((row, index) => (
              <View key={index} style={styles.tableRow}>
                <Text style={[styles.tableCell, { flex: 1.5, fontWeight: 'bold' }]}>
                  {row.label}
                </Text>
                {row.values.map((value, vIndex) => (
                  <Text
                    key={vIndex}
                    style={[
                      styles.tableCell,
                      row.highlight && styles.highlightedValue,
                    ]}
                  >
                    {value}
                  </Text>
                ))}
              </View>
            ))}
          </View>
        )}

        {/* Fuel Economy Comparison */}
        <View style={styles.table}>
          <Text style={styles.sectionTitle}>Fuel Economy (MPG)</Text>
          <View style={[styles.tableRow, styles.tableHeader]}>
            <Text style={[styles.tableCellHeader, { flex: 1.5 }]}>Type</Text>
            {vehicles.map((vehicle) => (
              <Text key={vehicle.id} style={styles.tableCellHeader}>
                {vehicle.make} {vehicle.model}
              </Text>
            ))}
          </View>
          {(['city', 'highway', 'combined'] as const).map((type) => (
            <View key={type} style={styles.tableRow}>
              <Text style={[styles.tableCell, { flex: 1.5, fontWeight: 'bold' }]}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </Text>
              {vehicles.map((vehicle) => (
                <Text key={vehicle.id} style={styles.tableCell}>
                  {vehicle.specifications.fuelEconomy[type]} MPG
                </Text>
              ))}
            </View>
          ))}
        </View>

        {/* Features Comparison */}
        {options.includeFeatures !== false && (
          <View style={styles.vehicleSection}>
            <Text style={styles.sectionTitle}>Key Features</Text>
            <View style={styles.comparisonGrid}>
              {vehicles.map((vehicle) => (
                <View key={vehicle.id} style={styles.comparisonColumn}>
                  <Text style={{ fontSize: 11, fontWeight: 'bold', marginBottom: 5 }}>
                    {vehicle.make} {vehicle.model}
                  </Text>
                  <View style={styles.featuresList}>
                    {vehicle.features.safety.slice(0, 3).map((feature, idx) => (
                      <Text key={idx} style={styles.featureItem}>
                        • {feature}
                      </Text>
                    ))}
                    {vehicle.features.technology.slice(0, 3).map((feature, idx) => (
                      <Text key={idx} style={styles.featureItem}>
                        • {feature}
                      </Text>
                    ))}
                  </View>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Footer */}
        <Text style={styles.footer}>
          AutoSelect - Vehicle Comparison Report | Generated {currentDate}
        </Text>
      </Page>
    </Document>
  );
}

/**
 * Generate PDF blob from vehicles comparison
 */
export async function generateComparisonPDF(
  vehicles: readonly Vehicle[],
  options: PDFGenerationOptions = {},
): Promise<PDFGenerationResult> {
  try {
    if (vehicles.length === 0) {
      throw new PDFGenerationError('No vehicles provided for comparison');
    }

    if (vehicles.length > 4) {
      throw new PDFGenerationError('Maximum 4 vehicles can be compared');
    }

    const doc = <ComparisonDocument vehicles={vehicles} options={options} />;
    const asPdf = pdf(doc);
    const blob = await asPdf.toBlob();

    const url = URL.createObjectURL(blob);
    const timestamp = new Date().toISOString().split('T')[0];
    const filename = `vehicle-comparison-${timestamp}.pdf`;

    return {
      blob,
      url,
      filename,
    };
  } catch (error) {
    if (error instanceof PDFGenerationError) {
      throw error;
    }
    throw new PDFGenerationError(
      'Failed to generate PDF',
      error,
    );
  }
}

/**
 * Download PDF file
 */
export function downloadPDF(result: PDFGenerationResult): void {
  try {
    const link = document.createElement('a');
    link.href = result.url;
    link.download = result.filename;
    link.style.display = 'none';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Cleanup object URL after download
    setTimeout(() => {
      URL.revokeObjectURL(result.url);
    }, 100);
  } catch (error) {
    throw new PDFGenerationError(
      'Failed to download PDF',
      error,
    );
  }
}

/**
 * Generate and download comparison PDF
 */
export async function generateAndDownloadPDF(
  vehicles: readonly Vehicle[],
  options: PDFGenerationOptions = {},
): Promise<void> {
  const result = await generateComparisonPDF(vehicles, options);
  downloadPDF(result);
}

/**
 * Type guard for PDF generation error
 */
export function isPDFGenerationError(error: unknown): error is PDFGenerationError {
  return error instanceof PDFGenerationError;
}