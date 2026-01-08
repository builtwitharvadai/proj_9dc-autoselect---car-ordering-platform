/**
 * Configuration sharing utilities for AutoSelect frontend application
 * Provides URL generation, parsing, and validation for shareable vehicle configurations
 */

/**
 * Configuration share data structure
 */
interface ConfigurationShareData {
  readonly vehicleId: string;
  readonly trimId?: string;
  readonly colorId?: string;
  readonly packageIds: readonly string[];
  readonly optionIds: readonly string[];
  readonly timestamp: number;
  readonly version: string;
}

/**
 * Share URL generation result
 */
interface ShareUrlResult {
  readonly url: string;
  readonly token: string;
  readonly expiresAt?: Date;
}

/**
 * Share URL parsing result
 */
interface ParsedShareUrl {
  readonly data: ConfigurationShareData;
  readonly isValid: boolean;
  readonly errors: readonly string[];
}

/**
 * Share token validation result
 */
interface TokenValidationResult {
  readonly isValid: boolean;
  readonly isExpired: boolean;
  readonly errors: readonly string[];
  readonly data?: ConfigurationShareData;
}

/**
 * Configuration sharing error types
 */
type ShareErrorType =
  | 'INVALID_TOKEN'
  | 'EXPIRED_TOKEN'
  | 'MALFORMED_DATA'
  | 'ENCODING_ERROR'
  | 'DECODING_ERROR'
  | 'VALIDATION_ERROR'
  | 'VERSION_MISMATCH';

/**
 * Configuration sharing error
 */
class ConfigurationSharingError extends Error {
  constructor(
    message: string,
    public readonly type: ShareErrorType,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'ConfigurationSharingError';
  }
}

/**
 * Current share data version
 */
const SHARE_DATA_VERSION = '1.0';

/**
 * URL parameter name for share token
 */
const SHARE_TOKEN_PARAM = 'share';

/**
 * Maximum token length for validation
 */
const MAX_TOKEN_LENGTH = 2048;

/**
 * Token expiration time in milliseconds (30 days)
 */
const TOKEN_EXPIRATION_MS = 30 * 24 * 60 * 60 * 1000;

/**
 * Generate a shareable URL for a vehicle configuration
 */
export function generateShareUrl(
  data: Omit<ConfigurationShareData, 'timestamp' | 'version'>,
  baseUrl?: string,
): ShareUrlResult {
  try {
    const shareData: ConfigurationShareData = {
      ...data,
      timestamp: Date.now(),
      version: SHARE_DATA_VERSION,
    };

    const token = encodeShareData(shareData);
    const url = buildShareUrl(token, baseUrl);
    const expiresAt = new Date(shareData.timestamp + TOKEN_EXPIRATION_MS);

    return {
      url,
      token,
      expiresAt,
    };
  } catch (error) {
    throw new ConfigurationSharingError(
      'Failed to generate share URL',
      'ENCODING_ERROR',
      { error: error instanceof Error ? error.message : String(error) },
    );
  }
}

/**
 * Parse a shared configuration URL
 */
export function parseShareUrl(url: string): ParsedShareUrl {
  const errors: string[] = [];

  try {
    const token = extractTokenFromUrl(url);

    if (!token) {
      errors.push('No share token found in URL');
      return {
        data: createEmptyShareData(),
        isValid: false,
        errors,
      };
    }

    const validationResult = validateShareToken(token);

    if (!validationResult.isValid) {
      return {
        data: validationResult.data ?? createEmptyShareData(),
        isValid: false,
        errors: [...validationResult.errors],
      };
    }

    return {
      data: validationResult.data!,
      isValid: true,
      errors: [],
    };
  } catch (error) {
    errors.push(
      error instanceof Error ? error.message : 'Unknown parsing error',
    );
    return {
      data: createEmptyShareData(),
      isValid: false,
      errors,
    };
  }
}

/**
 * Validate a share token
 */
export function validateShareToken(token: string): TokenValidationResult {
  const errors: string[] = [];

  if (!token || typeof token !== 'string') {
    errors.push('Token is required and must be a string');
    return { isValid: false, isExpired: false, errors };
  }

  if (token.length > MAX_TOKEN_LENGTH) {
    errors.push(`Token exceeds maximum length of ${MAX_TOKEN_LENGTH}`);
    return { isValid: false, isExpired: false, errors };
  }

  try {
    const data = decodeShareData(token);

    if (data.version !== SHARE_DATA_VERSION) {
      errors.push(
        `Version mismatch: expected ${SHARE_DATA_VERSION}, got ${data.version}`,
      );
      return { isValid: false, isExpired: false, errors, data };
    }

    const isExpired = isTokenExpired(data.timestamp);

    if (isExpired) {
      errors.push('Share token has expired');
      return { isValid: false, isExpired: true, errors, data };
    }

    const validationErrors = validateShareData(data);
    if (validationErrors.length > 0) {
      return {
        isValid: false,
        isExpired: false,
        errors: validationErrors,
        data,
      };
    }

    return {
      isValid: true,
      isExpired: false,
      errors: [],
      data,
    };
  } catch (error) {
    errors.push(
      error instanceof Error ? error.message : 'Token decoding failed',
    );
    return { isValid: false, isExpired: false, errors };
  }
}

/**
 * Encode share data to a URL-safe token
 */
function encodeShareData(data: ConfigurationShareData): string {
  try {
    const jsonString = JSON.stringify(data);
    const base64 = btoa(jsonString);
    return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
  } catch (error) {
    throw new ConfigurationSharingError(
      'Failed to encode share data',
      'ENCODING_ERROR',
      { error: error instanceof Error ? error.message : String(error) },
    );
  }
}

/**
 * Decode share data from a URL-safe token
 */
function decodeShareData(token: string): ConfigurationShareData {
  try {
    const base64 = token.replace(/-/g, '+').replace(/_/g, '/');
    const padding = '='.repeat((4 - (base64.length % 4)) % 4);
    const jsonString = atob(base64 + padding);
    const data = JSON.parse(jsonString) as ConfigurationShareData;

    return data;
  } catch (error) {
    throw new ConfigurationSharingError(
      'Failed to decode share token',
      'DECODING_ERROR',
      { error: error instanceof Error ? error.message : String(error) },
    );
  }
}

/**
 * Build a complete share URL with token
 */
function buildShareUrl(token: string, baseUrl?: string): string {
  const base = baseUrl ?? window.location.origin;
  const url = new URL('/configure', base);
  url.searchParams.set(SHARE_TOKEN_PARAM, token);
  return url.toString();
}

/**
 * Extract share token from URL
 */
function extractTokenFromUrl(url: string): string | null {
  try {
    const urlObj = new URL(url);
    return urlObj.searchParams.get(SHARE_TOKEN_PARAM);
  } catch {
    return null;
  }
}

/**
 * Check if token is expired
 */
function isTokenExpired(timestamp: number): boolean {
  const now = Date.now();
  const age = now - timestamp;
  return age > TOKEN_EXPIRATION_MS;
}

/**
 * Validate share data structure
 */
function validateShareData(data: ConfigurationShareData): readonly string[] {
  const errors: string[] = [];

  if (!data.vehicleId || typeof data.vehicleId !== 'string') {
    errors.push('Vehicle ID is required and must be a string');
  }

  if (data.trimId !== undefined && typeof data.trimId !== 'string') {
    errors.push('Trim ID must be a string');
  }

  if (data.colorId !== undefined && typeof data.colorId !== 'string') {
    errors.push('Color ID must be a string');
  }

  if (!Array.isArray(data.packageIds)) {
    errors.push('Package IDs must be an array');
  } else if (
    !data.packageIds.every((id) => typeof id === 'string')
  ) {
    errors.push('All package IDs must be strings');
  }

  if (!Array.isArray(data.optionIds)) {
    errors.push('Option IDs must be an array');
  } else if (
    !data.optionIds.every((id) => typeof id === 'string')
  ) {
    errors.push('All option IDs must be strings');
  }

  if (typeof data.timestamp !== 'number' || data.timestamp <= 0) {
    errors.push('Timestamp must be a positive number');
  }

  if (typeof data.version !== 'string' || !data.version) {
    errors.push('Version must be a non-empty string');
  }

  return errors;
}

/**
 * Create empty share data for error cases
 */
function createEmptyShareData(): ConfigurationShareData {
  return {
    vehicleId: '',
    packageIds: [],
    optionIds: [],
    timestamp: 0,
    version: SHARE_DATA_VERSION,
  };
}

/**
 * Check if URL contains a share token
 */
export function hasShareToken(url: string): boolean {
  try {
    const urlObj = new URL(url);
    return urlObj.searchParams.has(SHARE_TOKEN_PARAM);
  } catch {
    return false;
  }
}

/**
 * Get share token from current URL
 */
export function getShareTokenFromCurrentUrl(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  return extractTokenFromUrl(window.location.href);
}

/**
 * Copy share URL to clipboard
 */
export async function copyShareUrlToClipboard(url: string): Promise<boolean> {
  if (typeof navigator === 'undefined' || !navigator.clipboard) {
    return false;
  }

  try {
    await navigator.clipboard.writeText(url);
    return true;
  } catch {
    return false;
  }
}

/**
 * Format share URL for display
 */
export function formatShareUrlForDisplay(url: string): string {
  try {
    const urlObj = new URL(url);
    const token = urlObj.searchParams.get(SHARE_TOKEN_PARAM);

    if (!token) {
      return url;
    }

    const truncatedToken =
      token.length > 20 ? `${token.slice(0, 20)}...` : token;
    urlObj.searchParams.set(SHARE_TOKEN_PARAM, truncatedToken);

    return urlObj.toString();
  } catch {
    return url;
  }
}

/**
 * Calculate share token expiration date
 */
export function getTokenExpirationDate(token: string): Date | null {
  try {
    const data = decodeShareData(token);
    return new Date(data.timestamp + TOKEN_EXPIRATION_MS);
  } catch {
    return null;
  }
}

/**
 * Check if share token will expire soon (within 7 days)
 */
export function isTokenExpiringSoon(token: string): boolean {
  const expirationDate = getTokenExpirationDate(token);
  if (!expirationDate) {
    return false;
  }

  const now = Date.now();
  const sevenDaysMs = 7 * 24 * 60 * 60 * 1000;
  const timeUntilExpiration = expirationDate.getTime() - now;

  return timeUntilExpiration > 0 && timeUntilExpiration < sevenDaysMs;
}

/**
 * Type guard for ConfigurationSharingError
 */
export function isConfigurationSharingError(
  error: unknown,
): error is ConfigurationSharingError {
  return error instanceof ConfigurationSharingError;
}

/**
 * Export types
 */
export type {
  ConfigurationShareData,
  ShareUrlResult,
  ParsedShareUrl,
  TokenValidationResult,
  ShareErrorType,
};

/**
 * Export error class
 */
export { ConfigurationSharingError };

/**
 * Export constants
 */
export {
  SHARE_DATA_VERSION,
  SHARE_TOKEN_PARAM,
  MAX_TOKEN_LENGTH,
  TOKEN_EXPIRATION_MS,
};