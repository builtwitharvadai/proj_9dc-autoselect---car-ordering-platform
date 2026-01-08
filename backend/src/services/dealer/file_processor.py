"""
Dealer inventory file processing service for CSV and Excel uploads.

This module provides comprehensive file processing capabilities for bulk inventory
updates including validation, error reporting, batch processing, and support for
multiple file formats with robust error handling and audit logging.
"""

import csv
import io
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import aiofiles
import pandas as pd
from pydantic import ValidationError

from src.core.logging import get_logger
from src.schemas.dealer import BulkInventoryItem

logger = get_logger(__name__)


class FileProcessingError(Exception):
    """Base exception for file processing errors."""

    def __init__(
        self,
        message: str,
        code: str,
        line_number: Optional[int] = None,
        **context: Any,
    ):
        super().__init__(message)
        self.code = code
        self.line_number = line_number
        self.context = context


class FileValidationError(FileProcessingError):
    """Exception raised for file validation errors."""

    pass


class FileParsingError(FileProcessingError):
    """Exception raised for file parsing errors."""

    pass


class FileProcessorConfig:
    """Configuration for file processor."""

    MAX_FILE_SIZE_MB: int = 50
    MAX_ROWS: int = 1000
    SUPPORTED_EXTENSIONS: set[str] = {".csv", ".xlsx", ".xls"}
    CHUNK_SIZE: int = 100
    REQUIRED_COLUMNS: set[str] = {"vehicle_id", "quantity", "status"}
    OPTIONAL_COLUMNS: set[str] = {"location", "vin", "notes"}
    CSV_ENCODING: str = "utf-8"
    CSV_DELIMITER: str = ","


class FileProcessor:
    """
    Service for processing CSV and Excel files for bulk inventory updates.

    Handles file validation, parsing, data transformation, and error reporting
    with support for batch processing and comprehensive error handling.
    """

    def __init__(self, config: Optional[FileProcessorConfig] = None):
        """
        Initialize file processor with configuration.

        Args:
            config: Optional configuration object, uses defaults if not provided
        """
        self.config = config or FileProcessorConfig()
        self.logger = get_logger(__name__)

    async def process_file(
        self,
        file_path: str,
        dealer_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        """
        Process uploaded file and extract inventory items.

        Args:
            file_path: Path to the uploaded file
            dealer_id: Dealer unique identifier
            user_id: User who uploaded the file

        Returns:
            Dictionary containing processing results with items, errors, and metadata

        Raises:
            FileValidationError: If file validation fails
            FileParsingError: If file parsing fails
        """
        start_time = datetime.now()
        self.logger.info(
            "Starting file processing",
            file_path=file_path,
            dealer_id=str(dealer_id),
            user_id=str(user_id),
        )

        try:
            # Validate file
            await self._validate_file(file_path)

            # Parse file based on extension
            file_extension = Path(file_path).suffix.lower()
            if file_extension == ".csv":
                items, errors = await self._process_csv(file_path)
            elif file_extension in {".xlsx", ".xls"}:
                items, errors = await self._process_excel(file_path)
            else:
                raise FileValidationError(
                    f"Unsupported file format: {file_extension}",
                    code="UNSUPPORTED_FORMAT",
                    file_path=file_path,
                )

            # Calculate processing metrics
            processing_time_ms = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )

            result = {
                "total_rows": len(items) + len(errors),
                "valid_items": len(items),
                "invalid_items": len(errors),
                "items": items,
                "errors": errors,
                "processing_time_ms": processing_time_ms,
                "file_path": file_path,
                "dealer_id": str(dealer_id),
                "user_id": str(user_id),
                "processed_at": datetime.now().isoformat(),
            }

            self.logger.info(
                "File processing completed",
                total_rows=result["total_rows"],
                valid_items=result["valid_items"],
                invalid_items=result["invalid_items"],
                processing_time_ms=processing_time_ms,
            )

            return result

        except Exception as e:
            self.logger.error(
                "File processing failed",
                error=str(e),
                error_type=type(e).__name__,
                file_path=file_path,
            )
            raise

    async def _validate_file(self, file_path: str) -> None:
        """
        Validate file before processing.

        Args:
            file_path: Path to the file to validate

        Raises:
            FileValidationError: If validation fails
        """
        path = Path(file_path)

        # Check file exists
        if not path.exists():
            raise FileValidationError(
                "File not found",
                code="FILE_NOT_FOUND",
                file_path=file_path,
            )

        # Check file extension
        if path.suffix.lower() not in self.config.SUPPORTED_EXTENSIONS:
            raise FileValidationError(
                f"Unsupported file extension: {path.suffix}",
                code="UNSUPPORTED_EXTENSION",
                file_path=file_path,
                extension=path.suffix,
            )

        # Check file size
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.config.MAX_FILE_SIZE_MB:
            raise FileValidationError(
                f"File size exceeds maximum allowed size of {self.config.MAX_FILE_SIZE_MB}MB",
                code="FILE_TOO_LARGE",
                file_path=file_path,
                file_size_mb=file_size_mb,
            )

        self.logger.debug(
            "File validation passed",
            file_path=file_path,
            file_size_mb=round(file_size_mb, 2),
        )

    async def _process_csv(
        self, file_path: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Process CSV file and extract inventory items.

        Args:
            file_path: Path to CSV file

        Returns:
            Tuple of (valid_items, errors)

        Raises:
            FileParsingError: If CSV parsing fails
        """
        valid_items: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        try:
            async with aiofiles.open(
                file_path, mode="r", encoding=self.config.CSV_ENCODING
            ) as file:
                content = await file.read()

            # Parse CSV
            csv_reader = csv.DictReader(
                io.StringIO(content),
                delimiter=self.config.CSV_DELIMITER,
            )

            # Validate headers
            if not csv_reader.fieldnames:
                raise FileParsingError(
                    "CSV file has no headers",
                    code="MISSING_HEADERS",
                    file_path=file_path,
                )

            headers = set(csv_reader.fieldnames)
            missing_columns = self.config.REQUIRED_COLUMNS - headers
            if missing_columns:
                raise FileParsingError(
                    f"Missing required columns: {', '.join(missing_columns)}",
                    code="MISSING_COLUMNS",
                    file_path=file_path,
                    missing_columns=list(missing_columns),
                )

            # Process rows
            for line_number, row in enumerate(csv_reader, start=2):
                try:
                    item = self._parse_row(row, line_number)
                    valid_items.append(item)
                except (ValidationError, ValueError) as e:
                    errors.append(
                        {
                            "line_number": line_number,
                            "row": row,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    )

                # Check row limit
                if len(valid_items) + len(errors) > self.config.MAX_ROWS:
                    raise FileParsingError(
                        f"File exceeds maximum allowed rows of {self.config.MAX_ROWS}",
                        code="TOO_MANY_ROWS",
                        file_path=file_path,
                        max_rows=self.config.MAX_ROWS,
                    )

            return valid_items, errors

        except csv.Error as e:
            raise FileParsingError(
                f"CSV parsing error: {str(e)}",
                code="CSV_PARSE_ERROR",
                file_path=file_path,
            ) from e
        except UnicodeDecodeError as e:
            raise FileParsingError(
                f"File encoding error: {str(e)}",
                code="ENCODING_ERROR",
                file_path=file_path,
            ) from e

    async def _process_excel(
        self, file_path: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Process Excel file and extract inventory items.

        Args:
            file_path: Path to Excel file

        Returns:
            Tuple of (valid_items, errors)

        Raises:
            FileParsingError: If Excel parsing fails
        """
        valid_items: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        try:
            # Read Excel file
            df = pd.read_excel(file_path, engine="openpyxl")

            # Validate headers
            headers = set(df.columns)
            missing_columns = self.config.REQUIRED_COLUMNS - headers
            if missing_columns:
                raise FileParsingError(
                    f"Missing required columns: {', '.join(missing_columns)}",
                    code="MISSING_COLUMNS",
                    file_path=file_path,
                    missing_columns=list(missing_columns),
                )

            # Check row limit
            if len(df) > self.config.MAX_ROWS:
                raise FileParsingError(
                    f"File exceeds maximum allowed rows of {self.config.MAX_ROWS}",
                    code="TOO_MANY_ROWS",
                    file_path=file_path,
                    max_rows=self.config.MAX_ROWS,
                )

            # Process rows
            for idx, row in df.iterrows():
                line_number = idx + 2  # Account for header row
                try:
                    row_dict = row.to_dict()
                    # Replace NaN with None
                    row_dict = {
                        k: (None if pd.isna(v) else v) for k, v in row_dict.items()
                    }
                    item = self._parse_row(row_dict, line_number)
                    valid_items.append(item)
                except (ValidationError, ValueError) as e:
                    errors.append(
                        {
                            "line_number": line_number,
                            "row": row_dict,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    )

            return valid_items, errors

        except Exception as e:
            raise FileParsingError(
                f"Excel parsing error: {str(e)}",
                code="EXCEL_PARSE_ERROR",
                file_path=file_path,
            ) from e

    def _parse_row(self, row: dict[str, Any], line_number: int) -> dict[str, Any]:
        """
        Parse and validate a single row.

        Args:
            row: Dictionary containing row data
            line_number: Line number in the file

        Returns:
            Validated inventory item dictionary

        Raises:
            ValidationError: If row validation fails
            ValueError: If data conversion fails
        """
        try:
            # Extract and validate required fields
            vehicle_id_str = str(row.get("vehicle_id", "")).strip()
            if not vehicle_id_str:
                raise ValueError("vehicle_id is required")

            try:
                vehicle_id = UUID(vehicle_id_str)
            except ValueError as e:
                raise ValueError(f"Invalid vehicle_id format: {vehicle_id_str}") from e

            # Parse quantity
            quantity_str = str(row.get("quantity", "")).strip()
            if not quantity_str:
                raise ValueError("quantity is required")

            try:
                quantity = int(quantity_str)
                if quantity < 0:
                    raise ValueError("quantity must be non-negative")
            except (ValueError, InvalidOperation) as e:
                raise ValueError(f"Invalid quantity: {quantity_str}") from e

            # Parse status
            status = str(row.get("status", "")).strip()
            if not status:
                raise ValueError("status is required")

            # Parse optional fields
            location = row.get("location")
            if location is not None:
                location = str(location).strip() or None

            vin = row.get("vin")
            if vin is not None:
                vin = str(vin).strip().upper() or None
                if vin and len(vin) != 17:
                    raise ValueError(f"VIN must be 17 characters: {vin}")

            notes = row.get("notes")
            if notes is not None:
                notes = str(notes).strip() or None

            # Create and validate item using Pydantic schema
            item_data = {
                "vehicle_id": vehicle_id,
                "quantity": quantity,
                "status": status,
                "location": location,
                "vin": vin,
                "notes": notes,
            }

            # Validate with Pydantic
            validated_item = BulkInventoryItem(**item_data)

            return validated_item.model_dump()

        except ValidationError as e:
            self.logger.warning(
                "Row validation failed",
                line_number=line_number,
                errors=e.errors(),
            )
            raise
        except ValueError as e:
            self.logger.warning(
                "Row parsing failed",
                line_number=line_number,
                error=str(e),
            )
            raise

    async def validate_file_content(
        self, file_path: str
    ) -> dict[str, Any]:
        """
        Validate file content without processing.

        Args:
            file_path: Path to the file to validate

        Returns:
            Dictionary containing validation results

        Raises:
            FileValidationError: If validation fails
        """
        self.logger.info("Validating file content", file_path=file_path)

        try:
            await self._validate_file(file_path)

            file_extension = Path(file_path).suffix.lower()
            if file_extension == ".csv":
                items, errors = await self._process_csv(file_path)
            elif file_extension in {".xlsx", ".xls"}:
                items, errors = await self._process_excel(file_path)
            else:
                raise FileValidationError(
                    f"Unsupported file format: {file_extension}",
                    code="UNSUPPORTED_FORMAT",
                    file_path=file_path,
                )

            return {
                "valid": len(errors) == 0,
                "total_rows": len(items) + len(errors),
                "valid_rows": len(items),
                "invalid_rows": len(errors),
                "errors": errors[:10],  # Return first 10 errors
                "has_more_errors": len(errors) > 10,
            }

        except Exception as e:
            self.logger.error(
                "File validation failed",
                error=str(e),
                file_path=file_path,
            )
            raise


def get_file_processor(
    config: Optional[FileProcessorConfig] = None,
) -> FileProcessor:
    """
    Get file processor instance.

    Args:
        config: Optional configuration object

    Returns:
        FileProcessor instance
    """
    return FileProcessor(config=config)