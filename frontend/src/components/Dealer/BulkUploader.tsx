import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Upload, FileText, AlertCircle, CheckCircle, X, Download } from 'lucide-react';

/**
 * File upload validation result
 */
interface UploadValidation {
  readonly valid: boolean;
  readonly errors: readonly string[];
}

/**
 * Upload progress state
 */
interface UploadProgress {
  readonly loaded: number;
  readonly total: number;
  readonly percentage: number;
}

/**
 * BulkUploader component props
 */
interface BulkUploaderProps {
  readonly dealerId: string;
  readonly onUploadComplete?: (response: {
    readonly uploadId: string;
    readonly successCount: number;
    readonly errorCount: number;
  }) => void;
  readonly onUploadError?: (error: Error) => void;
  readonly className?: string;
  readonly maxFileSize?: number;
  readonly acceptedFormats?: readonly string[];
}

/**
 * CSV validation error display
 */
interface ValidationError {
  readonly row: number;
  readonly field: string;
  readonly message: string;
  readonly value?: string;
}

/**
 * Upload state type
 */
type UploadState = 'idle' | 'validating' | 'uploading' | 'processing' | 'success' | 'error';

const DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ACCEPTED_FORMATS = ['.csv', '.xlsx', '.xls'] as const;
const API_BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

/**
 * Bulk inventory uploader component with drag-and-drop support
 * Handles CSV/Excel file uploads with validation and progress tracking
 */
export default function BulkUploader({
  dealerId,
  onUploadComplete,
  onUploadError,
  className = '',
  maxFileSize = DEFAULT_MAX_FILE_SIZE,
  acceptedFormats = ACCEPTED_FORMATS,
}: BulkUploaderProps): JSX.Element {
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [validationErrors, setValidationErrors] = useState<readonly ValidationError[]>([]);
  const [uploadResult, setUploadResult] = useState<{
    readonly uploadId: string;
    readonly successCount: number;
    readonly errorCount: number;
    readonly totalRows: number;
  } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);

  /**
   * Validate file before upload
   */
  const validateFile = useCallback(
    (file: File): UploadValidation => {
      const errors: string[] = [];

      // Check file size
      if (file.size > maxFileSize) {
        errors.push(
          `File size exceeds maximum allowed size of ${(maxFileSize / (1024 * 1024)).toFixed(0)}MB`,
        );
      }

      // Check file format
      const fileExtension = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`;
      if (!acceptedFormats.includes(fileExtension as (typeof acceptedFormats)[number])) {
        errors.push(
          `Invalid file format. Accepted formats: ${acceptedFormats.join(', ')}`,
        );
      }

      // Check file name
      if (file.name.length > 255) {
        errors.push('File name is too long (maximum 255 characters)');
      }

      return {
        valid: errors.length === 0,
        errors,
      };
    },
    [maxFileSize, acceptedFormats],
  );

  /**
   * Handle file selection
   */
  const handleFileSelect = useCallback(
    (file: File) => {
      setErrorMessage(null);
      setValidationErrors([]);
      setUploadResult(null);

      const validation = validateFile(file);

      if (!validation.valid) {
        setErrorMessage(validation.errors[0] ?? 'Invalid file');
        setUploadState('error');
        return;
      }

      setSelectedFile(file);
      setUploadState('idle');
    },
    [validateFile],
  );

  /**
   * Handle file input change
   */
  const handleFileInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (file) {
        handleFileSelect(file);
      }
    },
    [handleFileSelect],
  );

  /**
   * Handle drag enter
   */
  const handleDragEnter = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    dragCounterRef.current += 1;
    if (event.dataTransfer.items && event.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  }, []);

  /**
   * Handle drag leave
   */
  const handleDragLeave = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    dragCounterRef.current -= 1;
    if (dragCounterRef.current === 0) {
      setIsDragging(false);
    }
  }, []);

  /**
   * Handle drag over
   */
  const handleDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
  }, []);

  /**
   * Handle drop
   */
  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setIsDragging(false);
      dragCounterRef.current = 0;

      const file = event.dataTransfer.files[0];
      if (file) {
        handleFileSelect(file);
      }
    },
    [handleFileSelect],
  );

  /**
   * Handle file upload
   */
  const handleUpload = useCallback(async () => {
    if (!selectedFile) {
      setErrorMessage('Please select a file to upload');
      return;
    }

    setUploadState('uploading');
    setErrorMessage(null);
    setValidationErrors([]);
    setUploadProgress({ loaded: 0, total: selectedFile.size, percentage: 0 });

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('dealerId', dealerId);

      const xhr = new XMLHttpRequest();

      // Track upload progress
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const percentage = Math.round((event.loaded / event.total) * 100);
          setUploadProgress({
            loaded: event.loaded,
            total: event.total,
            percentage,
          });
        }
      });

      // Handle upload completion
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          setUploadState('processing');
          try {
            const response = JSON.parse(xhr.responseText) as {
              readonly uploadId: string;
              readonly status: string;
              readonly totalRows: number;
              readonly successCount: number;
              readonly errorCount: number;
              readonly errors: readonly ValidationError[];
              readonly message: string;
            };

            if (response.errorCount > 0) {
              setValidationErrors(response.errors);
              setUploadState('error');
            } else {
              setUploadState('success');
            }

            setUploadResult({
              uploadId: response.uploadId,
              successCount: response.successCount,
              errorCount: response.errorCount,
              totalRows: response.totalRows,
            });

            if (onUploadComplete) {
              onUploadComplete({
                uploadId: response.uploadId,
                successCount: response.successCount,
                errorCount: response.errorCount,
              });
            }
          } catch (parseError) {
            setErrorMessage('Failed to parse server response');
            setUploadState('error');
            if (onUploadError) {
              onUploadError(
                parseError instanceof Error ? parseError : new Error('Parse error'),
              );
            }
          }
        } else {
          try {
            const errorResponse = JSON.parse(xhr.responseText) as {
              readonly message?: string;
              readonly detail?: string;
            };
            setErrorMessage(
              errorResponse.message ?? errorResponse.detail ?? 'Upload failed',
            );
          } catch {
            setErrorMessage(`Upload failed with status ${xhr.status}`);
          }
          setUploadState('error');
          if (onUploadError) {
            onUploadError(new Error(`Upload failed with status ${xhr.status}`));
          }
        }
      });

      // Handle upload error
      xhr.addEventListener('error', () => {
        setErrorMessage('Network error occurred during upload');
        setUploadState('error');
        if (onUploadError) {
          onUploadError(new Error('Network error'));
        }
      });

      // Handle upload abort
      xhr.addEventListener('abort', () => {
        setErrorMessage('Upload was cancelled');
        setUploadState('error');
      });

      xhr.open('POST', `${API_BASE_URL}/api/v1/dealer/inventory/bulk-upload`);
      xhr.send(formData);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : 'An unexpected error occurred',
      );
      setUploadState('error');
      if (onUploadError) {
        onUploadError(error instanceof Error ? error : new Error('Unknown error'));
      }
    }
  }, [selectedFile, dealerId, onUploadComplete, onUploadError]);

  /**
   * Handle template download
   */
  const handleDownloadTemplate = useCallback(() => {
    const link = document.createElement('a');
    link.href = `${API_BASE_URL}/api/v1/dealer/inventory/template`;
    link.download = 'inventory_upload_template.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, []);

  /**
   * Reset upload state
   */
  const handleReset = useCallback(() => {
    setSelectedFile(null);
    setUploadState('idle');
    setUploadProgress(null);
    setValidationErrors([]);
    setUploadResult(null);
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  /**
   * Format file size for display
   */
  const formatFileSize = useCallback((bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i] ?? 'Bytes'}`;
  }, []);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      dragCounterRef.current = 0;
    };
  }, []);

  return (
    <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Bulk Inventory Upload</h2>
        <p className="text-gray-600">
          Upload a CSV or Excel file to update multiple inventory items at once
        </p>
      </div>

      {/* Template Download */}
      <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-blue-900 mb-1">
              Download Template
            </h3>
            <p className="text-sm text-blue-700">
              Use our template to ensure your data is formatted correctly
            </p>
          </div>
          <button
            type="button"
            onClick={handleDownloadTemplate}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            aria-label="Download CSV template"
          >
            <Download className="w-4 h-4" aria-hidden="true" />
            <span>Download Template</span>
          </button>
        </div>
      </div>

      {/* File Upload Area */}
      <div
        className={`relative border-2 border-dashed rounded-lg p-8 transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : uploadState === 'error'
              ? 'border-red-300 bg-red-50'
              : 'border-gray-300 bg-gray-50 hover:border-gray-400'
        }`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={acceptedFormats.join(',')}
          onChange={handleFileInputChange}
          className="hidden"
          id="file-upload"
          aria-label="Choose file to upload"
          disabled={uploadState === 'uploading' || uploadState === 'processing'}
        />

        <div className="flex flex-col items-center justify-center text-center">
          <Upload
            className={`w-12 h-12 mb-4 ${
              isDragging ? 'text-blue-500' : 'text-gray-400'
            }`}
            aria-hidden="true"
          />

          {selectedFile ? (
            <div className="w-full">
              <div className="flex items-center justify-center gap-3 mb-4">
                <FileText className="w-6 h-6 text-blue-600" aria-hidden="true" />
                <div className="text-left">
                  <p className="text-sm font-medium text-gray-900">
                    {selectedFile.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatFileSize(selectedFile.size)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleReset}
                  className="p-1 text-gray-400 hover:text-gray-600 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 rounded"
                  aria-label="Remove selected file"
                  disabled={uploadState === 'uploading' || uploadState === 'processing'}
                >
                  <X className="w-5 h-5" aria-hidden="true" />
                </button>
              </div>

              {uploadState === 'idle' && (
                <button
                  type="button"
                  onClick={handleUpload}
                  className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                  Upload File
                </button>
              )}
            </div>
          ) : (
            <>
              <p className="text-base font-medium text-gray-900 mb-2">
                {isDragging ? 'Drop file here' : 'Drag and drop your file here'}
              </p>
              <p className="text-sm text-gray-500 mb-4">or</p>
              <label
                htmlFor="file-upload"
                className="px-6 py-2 bg-white border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors cursor-pointer focus-within:outline-none focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-2"
              >
                Browse Files
              </label>
              <p className="text-xs text-gray-500 mt-4">
                Accepted formats: {acceptedFormats.join(', ')} (Max{' '}
                {formatFileSize(maxFileSize)})
              </p>
            </>
          )}
        </div>
      </div>

      {/* Upload Progress */}
      {uploadProgress && (uploadState === 'uploading' || uploadState === 'processing') && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              {uploadState === 'uploading' ? 'Uploading...' : 'Processing...'}
            </span>
            <span className="text-sm font-medium text-gray-700">
              {uploadProgress.percentage}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
            <div
              className="bg-blue-600 h-2 transition-all duration-300 ease-out"
              style={{ width: `${uploadProgress.percentage}%` }}
              role="progressbar"
              aria-valuenow={uploadProgress.percentage}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Upload progress"
            />
          </div>
        </div>
      )}

      {/* Success Message */}
      {uploadState === 'success' && uploadResult && (
        <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-green-900 mb-1">
                Upload Successful
              </h3>
              <p className="text-sm text-green-700">
                Successfully processed {uploadResult.successCount} of{' '}
                {uploadResult.totalRows} rows
              </p>
              <button
                type="button"
                onClick={handleReset}
                className="mt-3 text-sm font-medium text-green-700 hover:text-green-800 focus:outline-none focus:underline"
              >
                Upload Another File
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Error Message */}
      {errorMessage && uploadState === 'error' && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-red-900 mb-1">Upload Failed</h3>
              <p className="text-sm text-red-700">{errorMessage}</p>
              <button
                type="button"
                onClick={handleReset}
                className="mt-3 text-sm font-medium text-red-700 hover:text-red-800 focus:outline-none focus:underline"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <div className="mt-6">
          <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start gap-3 mb-3">
              <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-yellow-900 mb-1">
                  Validation Errors Found
                </h3>
                <p className="text-sm text-yellow-700 mb-3">
                  {validationErrors.length} error{validationErrors.length !== 1 ? 's' : ''}{' '}
                  found in your file. Please fix these issues and try again.
                </p>
              </div>
            </div>

            <div className="max-h-64 overflow-y-auto">
              <table className="min-w-full divide-y divide-yellow-200">
                <thead className="bg-yellow-100">
                  <tr>
                    <th
                      scope="col"
                      className="px-3 py-2 text-left text-xs font-medium text-yellow-900 uppercase tracking-wider"
                    >
                      Row
                    </th>
                    <th
                      scope="col"
                      className="px-3 py-2 text-left text-xs font-medium text-yellow-900 uppercase tracking-wider"
                    >
                      Field
                    </th>
                    <th
                      scope="col"
                      className="px-3 py-2 text-left text-xs font-medium text-yellow-900 uppercase tracking-wider"
                    >
                      Error
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-yellow-200">
                  {validationErrors.map((error, index) => (
                    <tr key={index} className="hover:bg-yellow-50">
                      <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">
                        {error.row}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">
                        {error.field}
                      </td>
                      <td className="px-3 py-2 text-sm text-gray-700">
                        {error.message}
                        {error.value && (
                          <span className="block text-xs text-gray-500 mt-1">
                            Value: {error.value}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <button
              type="button"
              onClick={handleReset}
              className="mt-4 text-sm font-medium text-yellow-700 hover:text-yellow-800 focus:outline-none focus:underline"
            >
              Upload Corrected File
            </button>
          </div>
        </div>
      )}
    </div>
  );
}