/**
 * SEO utilities for vehicle detail pages
 * Generates SEO meta tags, structured data (JSON-LD), and Open Graph tags
 */

import type { Vehicle } from '../types/vehicle';

/**
 * Meta tag configuration
 */
interface MetaTag {
  readonly name?: string;
  readonly property?: string;
  readonly content: string;
}

/**
 * Structured data for vehicles (JSON-LD)
 */
interface VehicleStructuredData {
  readonly '@context': 'https://schema.org';
  readonly '@type': 'Car' | 'Product';
  readonly name: string;
  readonly description: string;
  readonly brand: {
    readonly '@type': 'Brand';
    readonly name: string;
  };
  readonly model: string;
  readonly vehicleModelDate?: string;
  readonly image: readonly string[];
  readonly offers: {
    readonly '@type': 'Offer';
    readonly price: string;
    readonly priceCurrency: 'USD';
    readonly availability: string;
    readonly url: string;
  };
  readonly vehicleConfiguration?: string;
  readonly vehicleTransmission?: string;
  readonly fuelType?: string;
  readonly driveWheelConfiguration?: string;
  readonly numberOfDoors?: number;
  readonly seatingCapacity?: number;
  readonly vehicleEngine?: {
    readonly '@type': 'EngineSpecification';
    readonly name: string;
  };
  readonly fuelEfficiency?: {
    readonly '@type': 'QuantitativeValue';
    readonly value: number;
    readonly unitText: string;
  };
}

/**
 * SEO configuration for vehicle pages
 */
interface VehicleSEOConfig {
  readonly title: string;
  readonly description: string;
  readonly canonical: string;
  readonly metaTags: readonly MetaTag[];
  readonly structuredData: VehicleStructuredData;
}

/**
 * Generate page title for vehicle
 */
export function generateVehicleTitle(vehicle: Vehicle): string {
  const parts = [vehicle.year.toString(), vehicle.make, vehicle.model];
  
  if (vehicle.trim) {
    parts.push(vehicle.trim);
  }
  
  parts.push('- AutoSelect');
  
  return parts.join(' ');
}

/**
 * Generate meta description for vehicle
 */
export function generateVehicleDescription(vehicle: Vehicle): string {
  const specs = vehicle.specifications;
  const features: string[] = [];
  
  // Add key specifications
  features.push(`${specs.horsepower}hp ${specs.engine}`);
  features.push(specs.transmission);
  features.push(specs.drivetrain.toUpperCase());
  
  // Add fuel economy if available
  if (specs.fuelEconomy.combined > 0) {
    features.push(`${specs.fuelEconomy.combined} MPG combined`);
  }
  
  const description = `${vehicle.year} ${vehicle.make} ${vehicle.model}${vehicle.trim ? ` ${vehicle.trim}` : ''} for sale. ${features.join(', ')}. Starting at $${vehicle.price.toLocaleString()}. View detailed specifications, features, and photos.`;
  
  // Limit to 160 characters for optimal SEO
  return description.length > 160 ? `${description.substring(0, 157)}...` : description;
}

/**
 * Generate canonical URL for vehicle
 */
export function generateCanonicalUrl(vehicleId: string): string {
  const baseUrl = import.meta.env['VITE_APP_URL'] ?? 'https://autoselect.com';
  return `${baseUrl}/vehicles/${vehicleId}`;
}

/**
 * Map vehicle availability to schema.org availability
 */
function mapAvailabilityToSchema(availability: Vehicle['availability']): string {
  const availabilityMap: Record<Vehicle['availability'], string> = {
    available: 'https://schema.org/InStock',
    reserved: 'https://schema.org/PreOrder',
    sold: 'https://schema.org/SoldOut',
    unavailable: 'https://schema.org/OutOfStock',
  };
  
  return availabilityMap[availability];
}

/**
 * Map drivetrain to schema.org format
 */
function mapDrivetrainToSchema(drivetrain: string): string {
  const drivetrainMap: Record<string, string> = {
    fwd: 'FrontWheelDriveConfiguration',
    rwd: 'RearWheelDriveConfiguration',
    awd: 'AllWheelDriveConfiguration',
    '4wd': 'FourWheelDriveConfiguration',
  };
  
  return drivetrainMap[drivetrain] ?? drivetrain;
}

/**
 * Generate structured data (JSON-LD) for vehicle
 */
export function generateStructuredData(vehicle: Vehicle, canonicalUrl: string): VehicleStructuredData {
  const specs = vehicle.specifications;
  
  const structuredData: VehicleStructuredData = {
    '@context': 'https://schema.org',
    '@type': 'Car',
    name: `${vehicle.year} ${vehicle.make} ${vehicle.model}${vehicle.trim ? ` ${vehicle.trim}` : ''}`,
    description: vehicle.description,
    brand: {
      '@type': 'Brand',
      name: vehicle.make,
    },
    model: vehicle.model,
    vehicleModelDate: vehicle.year.toString(),
    image: vehicle.images.length > 0 ? [...vehicle.images] : [vehicle.imageUrl],
    offers: {
      '@type': 'Offer',
      price: vehicle.price.toString(),
      priceCurrency: 'USD',
      availability: mapAvailabilityToSchema(vehicle.availability),
      url: canonicalUrl,
    },
  };
  
  // Add optional specifications
  if (vehicle.trim) {
    structuredData.vehicleConfiguration = vehicle.trim;
  }
  
  if (specs.transmission) {
    structuredData.vehicleTransmission = specs.transmission;
  }
  
  if (specs.fuelType) {
    structuredData.fuelType = specs.fuelType;
  }
  
  if (specs.drivetrain) {
    structuredData.driveWheelConfiguration = mapDrivetrainToSchema(specs.drivetrain);
  }
  
  if (specs.seatingCapacity > 0) {
    structuredData.seatingCapacity = specs.seatingCapacity;
  }
  
  if (specs.engine) {
    structuredData.vehicleEngine = {
      '@type': 'EngineSpecification',
      name: specs.engine,
    };
  }
  
  if (specs.fuelEconomy.combined > 0) {
    structuredData.fuelEfficiency = {
      '@type': 'QuantitativeValue',
      value: specs.fuelEconomy.combined,
      unitText: 'MPG',
    };
  }
  
  return structuredData;
}

/**
 * Generate Open Graph meta tags
 */
export function generateOpenGraphTags(
  vehicle: Vehicle,
  canonicalUrl: string,
  description: string,
): readonly MetaTag[] {
  const tags: MetaTag[] = [
    { property: 'og:type', content: 'product' },
    { property: 'og:title', content: generateVehicleTitle(vehicle) },
    { property: 'og:description', content: description },
    { property: 'og:url', content: canonicalUrl },
    { property: 'og:site_name', content: 'AutoSelect' },
    { property: 'og:locale', content: 'en_US' },
  ];
  
  // Add images
  if (vehicle.images.length > 0) {
    vehicle.images.forEach((image) => {
      tags.push({ property: 'og:image', content: image });
    });
  } else {
    tags.push({ property: 'og:image', content: vehicle.imageUrl });
  }
  
  // Add product-specific tags
  tags.push(
    { property: 'product:price:amount', content: vehicle.price.toString() },
    { property: 'product:price:currency', content: 'USD' },
    { property: 'product:availability', content: vehicle.availability },
    { property: 'product:condition', content: 'new' },
  );
  
  return tags;
}

/**
 * Generate Twitter Card meta tags
 */
export function generateTwitterCardTags(
  vehicle: Vehicle,
  description: string,
): readonly MetaTag[] {
  const tags: MetaTag[] = [
    { name: 'twitter:card', content: 'summary_large_image' },
    { name: 'twitter:title', content: generateVehicleTitle(vehicle) },
    { name: 'twitter:description', content: description },
  ];
  
  // Add image
  const imageUrl = vehicle.images.length > 0 ? vehicle.images[0] : vehicle.imageUrl;
  tags.push({ name: 'twitter:image', content: imageUrl });
  
  return tags;
}

/**
 * Generate standard meta tags
 */
export function generateStandardMetaTags(
  vehicle: Vehicle,
  description: string,
): readonly MetaTag[] {
  return [
    { name: 'description', content: description },
    { name: 'keywords', content: generateKeywords(vehicle) },
    { name: 'author', content: 'AutoSelect' },
    { name: 'robots', content: 'index, follow' },
  ];
}

/**
 * Generate keywords for vehicle
 */
function generateKeywords(vehicle: Vehicle): string {
  const keywords: string[] = [
    vehicle.make,
    vehicle.model,
    vehicle.year.toString(),
    vehicle.bodyStyle,
    vehicle.specifications.fuelType,
    vehicle.specifications.transmission,
    'car for sale',
    'new car',
    'vehicle',
  ];
  
  if (vehicle.trim) {
    keywords.push(vehicle.trim);
  }
  
  return keywords.join(', ');
}

/**
 * Generate complete SEO configuration for vehicle page
 */
export function generateVehicleSEO(vehicle: Vehicle): VehicleSEOConfig {
  const title = generateVehicleTitle(vehicle);
  const description = generateVehicleDescription(vehicle);
  const canonical = generateCanonicalUrl(vehicle.id);
  const structuredData = generateStructuredData(vehicle, canonical);
  
  const metaTags: MetaTag[] = [
    ...generateStandardMetaTags(vehicle, description),
    ...generateOpenGraphTags(vehicle, canonical, description),
    ...generateTwitterCardTags(vehicle, description),
  ];
  
  return {
    title,
    description,
    canonical,
    metaTags,
    structuredData,
  };
}

/**
 * Apply SEO configuration to document head
 */
export function applySEOToDocument(config: VehicleSEOConfig): void {
  // Set title
  document.title = config.title;
  
  // Remove existing meta tags
  const existingMetaTags = document.querySelectorAll('meta[name], meta[property]');
  existingMetaTags.forEach((tag) => {
    const name = tag.getAttribute('name');
    const property = tag.getAttribute('property');
    
    if (
      name &&
      (name.startsWith('twitter:') ||
        name === 'description' ||
        name === 'keywords' ||
        name === 'author' ||
        name === 'robots')
    ) {
      tag.remove();
    }
    
    if (property && (property.startsWith('og:') || property.startsWith('product:'))) {
      tag.remove();
    }
  });
  
  // Add new meta tags
  config.metaTags.forEach((tag) => {
    const metaElement = document.createElement('meta');
    
    if (tag.name) {
      metaElement.setAttribute('name', tag.name);
    }
    
    if (tag.property) {
      metaElement.setAttribute('property', tag.property);
    }
    
    metaElement.setAttribute('content', tag.content);
    document.head.appendChild(metaElement);
  });
  
  // Update or create canonical link
  let canonicalLink = document.querySelector('link[rel="canonical"]');
  
  if (!canonicalLink) {
    canonicalLink = document.createElement('link');
    canonicalLink.setAttribute('rel', 'canonical');
    document.head.appendChild(canonicalLink);
  }
  
  canonicalLink.setAttribute('href', config.canonical);
  
  // Update or create structured data script
  let structuredDataScript = document.querySelector('script[type="application/ld+json"]');
  
  if (!structuredDataScript) {
    structuredDataScript = document.createElement('script');
    structuredDataScript.setAttribute('type', 'application/ld+json');
    document.head.appendChild(structuredDataScript);
  }
  
  structuredDataScript.textContent = JSON.stringify(config.structuredData, null, 2);
}

/**
 * Remove SEO configuration from document head
 */
export function removeSEOFromDocument(): void {
  // Remove meta tags
  const metaTags = document.querySelectorAll('meta[name], meta[property]');
  metaTags.forEach((tag) => {
    const name = tag.getAttribute('name');
    const property = tag.getAttribute('property');
    
    if (
      name &&
      (name.startsWith('twitter:') ||
        name === 'description' ||
        name === 'keywords' ||
        name === 'author' ||
        name === 'robots')
    ) {
      tag.remove();
    }
    
    if (property && (property.startsWith('og:') || property.startsWith('product:'))) {
      tag.remove();
    }
  });
  
  // Remove canonical link
  const canonicalLink = document.querySelector('link[rel="canonical"]');
  if (canonicalLink) {
    canonicalLink.remove();
  }
  
  // Remove structured data
  const structuredDataScript = document.querySelector('script[type="application/ld+json"]');
  if (structuredDataScript) {
    structuredDataScript.remove();
  }
}