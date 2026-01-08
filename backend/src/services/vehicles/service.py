"""
Vehicle service for business logic operations.

This module implements the VehicleService class providing comprehensive
business logic for vehicle catalog operations including CRUD operations,
search functionality, filtering, caching, validation, and inventory integration.
Implements production-ready patterns with proper error handling and logging.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any, Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from src.core.logging import get_logger
from src.cache.redis_client import RedisClient, CacheKeyManager
from src.database.models.vehicle import Vehicle
from src.database.models.inventory import InventoryItem, InventoryStatus
from src.services.vehicles.repository import VehicleRepository
from src.schemas.vehicles import (
    VehicleCreate,
    VehicleUpdate,
    VehicleResponse,
    VehicleListResponse,
    VehicleSearchRequest,
)

logger = get_logger(__name__)


class VehicleServiceError(Exception):
    """Base exception for vehicle service errors."""

    def __init__(self, message: str, code: str, **context):
        super().__init__(message)
        self.code = code
        self.context = context


class VehicleNotFoundError(VehicleServiceError):
    """Exception raised when vehicle is not found."""

    def __init__(self, vehicle_id: uuid.UUID, **context):
        super().__init__(
            f"Vehicle not found: {vehicle_id}",
            code="VEHICLE_NOT_FOUND",
            vehicle_id=str(vehicle_id),
            **context,
        )


class VehicleValidationError(VehicleServiceError):
    """Exception raised when vehicle validation fails."""

    def __init__(self, message: str, **context):
        super().__init__(
            message,
            code="VEHICLE_VALIDATION_ERROR",
            **context,
        )


class VehicleService:
    """
    Business logic service for vehicle catalog operations.

    Provides comprehensive vehicle management functionality including
    CRUD operations, search, filtering, caching, and inventory integration.
    Implements proper error handling, validation, and logging.
    """

    def __init__(
        self,
        session: AsyncSession,
        cache_client: Optional[RedisClient] = None,
        cache_ttl: int = 3600,
        search_service: Optional[Any] = None,
    ):
        """
        Initialize vehicle service.

        Args:
            session: Async database session
            cache_client: Optional Redis cache client
            cache_ttl: Cache TTL in seconds (default: 1 hour)
            search_service: Optional Elasticsearch search service
        """
        self.repository = VehicleRepository(session)
        self.session = session
        self.cache_client = cache_client
        self.cache_ttl = cache_ttl
        self.cache_key_manager = CacheKeyManager()
        self.search_service = search_service

        logger.info(
            "Vehicle service initialized",
            cache_enabled=cache_client is not None,
            cache_ttl=cache_ttl,
            search_enabled=search_service is not None,
        )

    async def create_vehicle(self, vehicle_data: VehicleCreate) -> VehicleResponse:
        """
        Create new vehicle with validation and caching.

        Args:
            vehicle_data: Vehicle creation data

        Returns:
            Created vehicle response

        Raises:
            VehicleValidationError: If validation fails
            VehicleServiceError: If creation fails
        """
        try:
            await self._validate_vehicle_uniqueness(
                make=vehicle_data.make,
                model=vehicle_data.model,
                year=vehicle_data.year,
                trim=vehicle_data.trim,
            )

            vehicle = Vehicle(
                make=vehicle_data.make,
                model=vehicle_data.model,
                year=vehicle_data.year,
                trim=vehicle_data.trim,
                body_style=vehicle_data.body_style,
                exterior_color=vehicle_data.exterior_color,
                interior_color=vehicle_data.interior_color,
                base_price=vehicle_data.base_price,
                specifications=vehicle_data.specifications.model_dump(),
                dimensions=vehicle_data.dimensions.model_dump(),
                features=vehicle_data.features.model_dump(),
                custom_attributes=vehicle_data.custom_attributes,
                is_active=True,
            )

            created_vehicle = await self.repository.create(vehicle)
            await self.session.commit()

            if self.cache_client:
                await self._invalidate_list_cache()

            response = self._to_response(created_vehicle)

            if self.search_service:
                await self._sync_to_search_index(response)

            logger.info(
                "Vehicle created successfully",
                vehicle_id=str(created_vehicle.id),
                make=created_vehicle.make,
                model=created_vehicle.model,
                year=created_vehicle.year,
            )

            return response

        except IntegrityError as e:
            await self.session.rollback()
            logger.error(
                "Vehicle creation failed - integrity error",
                error=str(e),
                vehicle_data=vehicle_data.model_dump(),
            )
            raise VehicleValidationError(
                "Vehicle with similar attributes already exists",
                vehicle_data=vehicle_data.model_dump(),
            ) from e

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Vehicle creation failed - database error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleServiceError(
                "Failed to create vehicle",
                code="VEHICLE_CREATE_ERROR",
                error=str(e),
            ) from e

        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Vehicle creation failed - unexpected error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_vehicle(
        self,
        vehicle_id: uuid.UUID,
        include_inventory: bool = False,
    ) -> VehicleResponse:
        """
        Get vehicle by ID with caching support.

        Args:
            vehicle_id: Vehicle identifier
            include_inventory: Whether to include inventory data

        Returns:
            Vehicle response

        Raises:
            VehicleNotFoundError: If vehicle not found
            VehicleServiceError: If retrieval fails
        """
        try:
            cache_key = self.cache_key_manager.vehicle_key(str(vehicle_id))

            if self.cache_client and not include_inventory:
                cached_data = await self.cache_client.get(cache_key)
                if cached_data:
                    logger.debug(
                        "Vehicle retrieved from cache",
                        vehicle_id=str(vehicle_id),
                    )
                    return VehicleResponse.model_validate_json(cached_data)

            vehicle = await self.repository.get_by_id(
                vehicle_id,
                include_inventory=include_inventory,
            )

            if not vehicle:
                raise VehicleNotFoundError(vehicle_id)

            response = self._to_response(vehicle)

            if self.cache_client and not include_inventory:
                await self.cache_client.set(
                    cache_key,
                    response.model_dump_json(),
                    ex=self.cache_ttl,
                )

            logger.debug(
                "Vehicle retrieved successfully",
                vehicle_id=str(vehicle_id),
                include_inventory=include_inventory,
            )

            return response

        except VehicleNotFoundError:
            raise

        except SQLAlchemyError as e:
            logger.error(
                "Vehicle retrieval failed",
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleServiceError(
                "Failed to retrieve vehicle",
                code="VEHICLE_GET_ERROR",
                vehicle_id=str(vehicle_id),
                error=str(e),
            ) from e

        except Exception as e:
            logger.error(
                "Vehicle retrieval failed - unexpected error",
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def update_vehicle(
        self,
        vehicle_id: uuid.UUID,
        vehicle_data: VehicleUpdate,
    ) -> VehicleResponse:
        """
        Update existing vehicle with validation and cache invalidation.

        Args:
            vehicle_id: Vehicle identifier
            vehicle_data: Vehicle update data

        Returns:
            Updated vehicle response

        Raises:
            VehicleNotFoundError: If vehicle not found
            VehicleValidationError: If validation fails
            VehicleServiceError: If update fails
        """
        try:
            vehicle = await self.repository.get_by_id(vehicle_id)
            if not vehicle:
                raise VehicleNotFoundError(vehicle_id)

            update_data = vehicle_data.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                if field == "specifications" and value:
                    vehicle.specifications = value.model_dump()
                elif field == "dimensions" and value:
                    vehicle.dimensions = value.model_dump()
                elif field == "features" and value:
                    vehicle.features = value.model_dump()
                elif value is not None:
                    setattr(vehicle, field, value)

            updated_vehicle = await self.repository.update(vehicle)
            await self.session.commit()

            if self.cache_client:
                await self._invalidate_vehicle_cache(vehicle_id)
                await self._invalidate_list_cache()

            response = self._to_response(updated_vehicle)

            if self.search_service:
                await self._sync_to_search_index(response)

            logger.info(
                "Vehicle updated successfully",
                vehicle_id=str(vehicle_id),
                updated_fields=list(update_data.keys()),
            )

            return response

        except VehicleNotFoundError:
            raise

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Vehicle update failed",
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleServiceError(
                "Failed to update vehicle",
                code="VEHICLE_UPDATE_ERROR",
                vehicle_id=str(vehicle_id),
                error=str(e),
            ) from e

        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Vehicle update failed - unexpected error",
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def delete_vehicle(
        self,
        vehicle_id: uuid.UUID,
        soft: bool = True,
    ) -> bool:
        """
        Delete vehicle with cache invalidation.

        Args:
            vehicle_id: Vehicle identifier
            soft: If True, perform soft delete; otherwise hard delete

        Returns:
            True if deleted successfully

        Raises:
            VehicleNotFoundError: If vehicle not found
            VehicleServiceError: If deletion fails
        """
        try:
            deleted = await self.repository.delete(vehicle_id, soft=soft)

            if not deleted:
                raise VehicleNotFoundError(vehicle_id)

            await self.session.commit()

            if self.cache_client:
                await self._invalidate_vehicle_cache(vehicle_id)
                await self._invalidate_list_cache()

            if self.search_service:
                await self._remove_from_search_index(vehicle_id)

            logger.info(
                "Vehicle deleted successfully",
                vehicle_id=str(vehicle_id),
                soft_delete=soft,
            )

            return True

        except VehicleNotFoundError:
            raise

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Vehicle deletion failed",
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleServiceError(
                "Failed to delete vehicle",
                code="VEHICLE_DELETE_ERROR",
                vehicle_id=str(vehicle_id),
                error=str(e),
            ) from e

        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Vehicle deletion failed - unexpected error",
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def search_vehicles(
        self,
        search_request: VehicleSearchRequest,
    ) -> VehicleListResponse:
        """
        Search vehicles with comprehensive filtering and caching.

        Args:
            search_request: Search parameters

        Returns:
            Paginated vehicle list response

        Raises:
            VehicleServiceError: If search fails
        """
        try:
            cache_key = self._generate_search_cache_key(search_request)

            if self.cache_client:
                cached_data = await self.cache_client.get(cache_key)
                if cached_data:
                    logger.debug(
                        "Search results retrieved from cache",
                        cache_key=cache_key,
                    )
                    return VehicleListResponse.model_validate_json(cached_data)

            skip = (search_request.page - 1) * search_request.page_size

            vehicles, total = await self.repository.search(
                make=search_request.make,
                model=search_request.model,
                year=None,
                min_year=search_request.year_min,
                max_year=search_request.year_max,
                body_style=search_request.body_style,
                fuel_type=search_request.fuel_type,
                min_price=search_request.price_min,
                max_price=search_request.price_max,
                specifications=search_request.custom_attributes,
                available_only=False,
                skip=skip,
                limit=search_request.page_size,
                sort_by=search_request.sort_by or "year",
                sort_order=search_request.sort_order,
            )

            total_pages = (
                (total + search_request.page_size - 1) // search_request.page_size
                if total > 0
                else 0
            )

            response = VehicleListResponse(
                items=[self._to_response(v) for v in vehicles],
                total=total,
                page=search_request.page,
                page_size=search_request.page_size,
                total_pages=total_pages,
            )

            if self.cache_client:
                await self.cache_client.set(
                    cache_key,
                    response.model_dump_json(),
                    ex=self.cache_ttl,
                )

            logger.info(
                "Vehicle search completed",
                total=total,
                returned=len(vehicles),
                page=search_request.page,
                filters=search_request.model_dump(exclude_unset=True),
            )

            return response

        except SQLAlchemyError as e:
            logger.error(
                "Vehicle search failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleServiceError(
                "Failed to search vehicles",
                code="VEHICLE_SEARCH_ERROR",
                error=str(e),
            ) from e

        except Exception as e:
            logger.error(
                "Vehicle search failed - unexpected error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_available_vehicles(
        self,
        dealership_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> VehicleListResponse:
        """
        Get available vehicles with inventory.

        Args:
            dealership_id: Optional dealership filter
            page: Page number
            page_size: Items per page

        Returns:
            Paginated list of available vehicles

        Raises:
            VehicleServiceError: If retrieval fails
        """
        try:
            skip = (page - 1) * page_size

            vehicles, total = await self.repository.get_available_vehicles(
                dealership_id=dealership_id,
                skip=skip,
                limit=page_size,
            )

            total_pages = (
                (total + page_size - 1) // page_size if total > 0 else 0
            )

            response = VehicleListResponse(
                items=[self._to_response(v) for v in vehicles],
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )

            logger.info(
                "Available vehicles retrieved",
                total=total,
                returned=len(vehicles),
                dealership_id=str(dealership_id) if dealership_id else None,
            )

            return response

        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve available vehicles",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleServiceError(
                "Failed to retrieve available vehicles",
                code="VEHICLE_AVAILABLE_ERROR",
                error=str(e),
            ) from e

        except Exception as e:
            logger.error(
                "Failed to retrieve available vehicles - unexpected error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_price_range(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
    ) -> tuple[Optional[Decimal], Optional[Decimal]]:
        """
        Get price range for vehicles matching criteria.

        Args:
            make: Optional manufacturer filter
            model: Optional model filter
            year: Optional year filter

        Returns:
            Tuple of (min_price, max_price)

        Raises:
            VehicleServiceError: If retrieval fails
        """
        try:
            min_price, max_price = await self.repository.get_price_range(
                make=make,
                model=model,
                year=year,
            )

            logger.debug(
                "Price range retrieved",
                min_price=float(min_price) if min_price else None,
                max_price=float(max_price) if max_price else None,
                filters={"make": make, "model": model, "year": year},
            )

            return min_price, max_price

        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve price range",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleServiceError(
                "Failed to retrieve price range",
                code="VEHICLE_PRICE_RANGE_ERROR",
                error=str(e),
            ) from e

        except Exception as e:
            logger.error(
                "Failed to retrieve price range - unexpected error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def bulk_index_vehicles(
        self,
        batch_size: int = 100,
    ) -> dict[str, int]:
        """
        Bulk index all active vehicles to Elasticsearch.

        Args:
            batch_size: Number of vehicles to process per batch

        Returns:
            Dictionary with indexing statistics

        Raises:
            VehicleServiceError: If bulk indexing fails
        """
        if not self.search_service:
            logger.warning("Search service not configured, skipping bulk indexing")
            return {"indexed": 0, "failed": 0, "skipped": 0}

        try:
            indexed_count = 0
            failed_count = 0
            offset = 0

            logger.info("Starting bulk vehicle indexing", batch_size=batch_size)

            while True:
                vehicles, total = await self.repository.search(
                    available_only=False,
                    skip=offset,
                    limit=batch_size,
                )

                if not vehicles:
                    break

                batch_responses = []
                for vehicle in vehicles:
                    try:
                        response = self._to_response(vehicle)
                        batch_responses.append(response)
                    except Exception as e:
                        logger.error(
                            "Failed to convert vehicle to response",
                            vehicle_id=str(vehicle.id),
                            error=str(e),
                        )
                        failed_count += 1

                if batch_responses:
                    try:
                        await self._bulk_sync_to_search_index(batch_responses)
                        indexed_count += len(batch_responses)
                        logger.info(
                            "Indexed vehicle batch",
                            batch_size=len(batch_responses),
                            total_indexed=indexed_count,
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to index vehicle batch",
                            batch_size=len(batch_responses),
                            error=str(e),
                        )
                        failed_count += len(batch_responses)

                offset += batch_size

                if offset >= total:
                    break

            logger.info(
                "Bulk vehicle indexing completed",
                indexed=indexed_count,
                failed=failed_count,
                total=total,
            )

            return {
                "indexed": indexed_count,
                "failed": failed_count,
                "skipped": 0,
            }

        except Exception as e:
            logger.error(
                "Bulk vehicle indexing failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleServiceError(
                "Failed to bulk index vehicles",
                code="VEHICLE_BULK_INDEX_ERROR",
                error=str(e),
            ) from e

    async def _sync_to_search_index(self, vehicle: VehicleResponse) -> None:
        """
        Sync single vehicle to Elasticsearch index.

        Args:
            vehicle: Vehicle response to index
        """
        if not self.search_service:
            return

        try:
            from src.services.search.vehicle_index import VehicleIndex

            vehicle_index = VehicleIndex()
            document = vehicle_index.prepare_document(vehicle)

            await self.search_service._index.index_vehicle(
                vehicle_id=str(vehicle.id),
                document=document,
            )

            logger.debug(
                "Vehicle synced to search index",
                vehicle_id=str(vehicle.id),
            )

        except Exception as e:
            logger.error(
                "Failed to sync vehicle to search index",
                vehicle_id=str(vehicle.id),
                error=str(e),
                error_type=type(e).__name__,
            )

    async def _bulk_sync_to_search_index(
        self,
        vehicles: list[VehicleResponse],
    ) -> None:
        """
        Bulk sync vehicles to Elasticsearch index.

        Args:
            vehicles: List of vehicle responses to index
        """
        if not self.search_service:
            return

        try:
            from src.services.search.vehicle_index import VehicleIndex

            vehicle_index = VehicleIndex()
            documents = []

            for vehicle in vehicles:
                document = vehicle_index.prepare_document(vehicle)
                documents.append({
                    "id": str(vehicle.id),
                    "document": document,
                })

            await self.search_service._index.bulk_index_vehicles(documents)

            logger.debug(
                "Vehicles bulk synced to search index",
                count=len(vehicles),
            )

        except Exception as e:
            logger.error(
                "Failed to bulk sync vehicles to search index",
                count=len(vehicles),
                error=str(e),
                error_type=type(e).__name__,
            )

    async def _remove_from_search_index(self, vehicle_id: uuid.UUID) -> None:
        """
        Remove vehicle from Elasticsearch index.

        Args:
            vehicle_id: Vehicle identifier to remove
        """
        if not self.search_service:
            return

        try:
            await self.search_service._index.delete_vehicle(str(vehicle_id))

            logger.debug(
                "Vehicle removed from search index",
                vehicle_id=str(vehicle_id),
            )

        except Exception as e:
            logger.error(
                "Failed to remove vehicle from search index",
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )

    async def _validate_vehicle_uniqueness(
        self,
        make: str,
        model: str,
        year: int,
        trim: Optional[str] = None,
    ) -> None:
        """
        Validate vehicle uniqueness.

        Args:
            make: Vehicle manufacturer
            model: Vehicle model
            year: Manufacturing year
            trim: Optional trim level

        Raises:
            VehicleValidationError: If similar vehicle exists
        """
        existing_vehicles = await self.repository.get_by_make_model_year(
            make=make,
            model=model,
            year=year,
        )

        if trim:
            for vehicle in existing_vehicles:
                if vehicle.trim and vehicle.trim.lower() == trim.lower():
                    raise VehicleValidationError(
                        f"Vehicle already exists: {make} {model} {year} {trim}",
                        make=make,
                        model=model,
                        year=year,
                        trim=trim,
                    )

    def _to_response(self, vehicle: Vehicle) -> VehicleResponse:
        """
        Convert vehicle model to response schema.

        Args:
            vehicle: Vehicle model instance

        Returns:
            Vehicle response schema
        """
        from src.schemas.vehicles import (
            VehicleSpecifications,
            VehicleDimensions,
            VehicleFeatures,
        )

        return VehicleResponse(
            id=vehicle.id,
            make=vehicle.make,
            model=vehicle.model,
            year=vehicle.year,
            trim=vehicle.trim,
            body_style=vehicle.body_style,
            exterior_color=vehicle.exterior_color,
            interior_color=vehicle.interior_color,
            base_price=vehicle.base_price,
            specifications=VehicleSpecifications(**vehicle.specifications),
            dimensions=VehicleDimensions(**vehicle.dimensions),
            features=VehicleFeatures(**vehicle.features),
            custom_attributes=vehicle.custom_attributes or {},
            is_active=vehicle.is_active,
            created_at=vehicle.created_at,
            updated_at=vehicle.updated_at,
        )

    def _generate_search_cache_key(
        self,
        search_request: VehicleSearchRequest,
    ) -> str:
        """
        Generate cache key for search request.

        Args:
            search_request: Search parameters

        Returns:
            Cache key string
        """
        filters = search_request.model_dump(exclude_unset=True)
        return self.cache_key_manager.list_key("vehicles", filters)

    async def _invalidate_vehicle_cache(self, vehicle_id: uuid.UUID) -> None:
        """
        Invalidate vehicle cache.

        Args:
            vehicle_id: Vehicle identifier
        """
        if not self.cache_client:
            return

        try:
            cache_key = self.cache_key_manager.vehicle_key(str(vehicle_id))
            await self.cache_client.delete(cache_key)
            logger.debug("Vehicle cache invalidated", vehicle_id=str(vehicle_id))

        except Exception as e:
            logger.warning(
                "Failed to invalidate vehicle cache",
                vehicle_id=str(vehicle_id),
                error=str(e),
            )

    async def _invalidate_list_cache(self) -> None:
        """Invalidate all list caches."""
        if not self.cache_client:
            return

        try:
            pattern = self.cache_key_manager.make_key("list", "vehicles", "*")
            logger.debug("List cache invalidation requested", pattern=pattern)

        except Exception as e:
            logger.warning(
                "Failed to invalidate list cache",
                error=str(e),
            )