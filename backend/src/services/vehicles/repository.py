"""
Vehicle repository for data access operations.

This module implements the repository pattern for vehicle data access with async
SQLAlchemy operations, comprehensive search functionality, filtering, pagination,
and complex queries with inventory joins. Provides efficient database operations
with proper error handling and logging.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any, Sequence

from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from src.core.logging import get_logger
from src.database.models.vehicle import Vehicle, VehicleConfiguration
from src.database.models.inventory import InventoryItem, InventoryStatus

logger = get_logger(__name__)


class VehicleRepository:
    """
    Repository for vehicle data access operations.

    Implements async CRUD operations, search functionality, filtering,
    pagination, and complex queries with inventory data joins.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize vehicle repository.

        Args:
            session: Async database session
        """
        self.session = session

    async def get_by_id(
        self,
        vehicle_id: uuid.UUID,
        include_inventory: bool = False,
    ) -> Optional[Vehicle]:
        """
        Get vehicle by ID.

        Args:
            vehicle_id: Vehicle identifier
            include_inventory: Whether to load inventory relationships

        Returns:
            Vehicle if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = select(Vehicle).where(
                and_(
                    Vehicle.id == vehicle_id,
                    Vehicle.deleted_at.is_(None),
                )
            )

            if include_inventory:
                stmt = stmt.options(
                    selectinload(Vehicle.inventory_items),
                )

            result = await self.session.execute(stmt)
            vehicle = result.scalar_one_or_none()

            if vehicle:
                logger.debug(
                    "Vehicle retrieved",
                    vehicle_id=str(vehicle_id),
                    include_inventory=include_inventory,
                )
            else:
                logger.debug(
                    "Vehicle not found",
                    vehicle_id=str(vehicle_id),
                )

            return vehicle

        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve vehicle",
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_by_vin(self, vin: str) -> Optional[Vehicle]:
        """
        Get vehicle by VIN.

        Args:
            vin: Vehicle Identification Number

        Returns:
            Vehicle if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = select(Vehicle).where(
                and_(
                    Vehicle.vin == vin.upper(),
                    Vehicle.deleted_at.is_(None),
                )
            )

            result = await self.session.execute(stmt)
            vehicle = result.scalar_one_or_none()

            if vehicle:
                logger.debug("Vehicle retrieved by VIN", vin=vin)
            else:
                logger.debug("Vehicle not found by VIN", vin=vin)

            return vehicle

        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve vehicle by VIN",
                vin=vin,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def create(self, vehicle: Vehicle) -> Vehicle:
        """
        Create new vehicle.

        Args:
            vehicle: Vehicle instance to create

        Returns:
            Created vehicle with generated ID

        Raises:
            IntegrityError: If vehicle with VIN already exists
            SQLAlchemyError: If database operation fails
        """
        try:
            self.session.add(vehicle)
            await self.session.flush()
            await self.session.refresh(vehicle)

            logger.info(
                "Vehicle created",
                vehicle_id=str(vehicle.id),
                make=vehicle.make,
                model=vehicle.model,
                year=vehicle.year,
                vin=vehicle.vin,
            )

            return vehicle

        except IntegrityError as e:
            logger.error(
                "Vehicle creation failed - integrity error",
                vin=vehicle.vin,
                error=str(e),
            )
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Vehicle creation failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def update(self, vehicle: Vehicle) -> Vehicle:
        """
        Update existing vehicle.

        Args:
            vehicle: Vehicle instance with updated data

        Returns:
            Updated vehicle

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            vehicle.updated_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(vehicle)

            logger.info(
                "Vehicle updated",
                vehicle_id=str(vehicle.id),
                make=vehicle.make,
                model=vehicle.model,
                year=vehicle.year,
            )

            return vehicle

        except SQLAlchemyError as e:
            logger.error(
                "Vehicle update failed",
                vehicle_id=str(vehicle.id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def delete(self, vehicle_id: uuid.UUID, soft: bool = True) -> bool:
        """
        Delete vehicle (soft or hard delete).

        Args:
            vehicle_id: Vehicle identifier
            soft: If True, perform soft delete; otherwise hard delete

        Returns:
            True if vehicle was deleted, False if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            vehicle = await self.get_by_id(vehicle_id)
            if not vehicle:
                logger.warning(
                    "Vehicle not found for deletion",
                    vehicle_id=str(vehicle_id),
                )
                return False

            if soft:
                vehicle.deleted_at = datetime.utcnow()
                await self.session.flush()
                logger.info(
                    "Vehicle soft deleted",
                    vehicle_id=str(vehicle_id),
                )
            else:
                await self.session.delete(vehicle)
                await self.session.flush()
                logger.info(
                    "Vehicle hard deleted",
                    vehicle_id=str(vehicle_id),
                )

            return True

        except SQLAlchemyError as e:
            logger.error(
                "Vehicle deletion failed",
                vehicle_id=str(vehicle_id),
                soft=soft,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def search(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
        body_style: Optional[str] = None,
        fuel_type: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        specifications: Optional[dict[str, Any]] = None,
        available_only: bool = False,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "year",
        sort_order: str = "desc",
    ) -> tuple[Sequence[Vehicle], int]:
        """
        Search vehicles with filtering and pagination.

        Args:
            make: Filter by manufacturer
            model: Filter by model name
            year: Filter by exact year
            min_year: Filter by minimum year
            max_year: Filter by maximum year
            body_style: Filter by body style
            fuel_type: Filter by fuel type
            min_price: Filter by minimum price
            max_price: Filter by maximum price
            specifications: Filter by JSONB specifications
            available_only: Only return available vehicles
            skip: Number of records to skip
            limit: Maximum number of records to return
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (vehicles list, total count)

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            conditions = [Vehicle.deleted_at.is_(None)]

            if make:
                conditions.append(
                    Vehicle.make.ilike(f"%{make}%")
                )

            if model:
                conditions.append(
                    Vehicle.model.ilike(f"%{model}%")
                )

            if year:
                conditions.append(Vehicle.year == year)

            if min_year:
                conditions.append(Vehicle.year >= min_year)

            if max_year:
                conditions.append(Vehicle.year <= max_year)

            if body_style:
                conditions.append(
                    Vehicle.body_style.ilike(f"%{body_style}%")
                )

            if fuel_type:
                conditions.append(
                    Vehicle.fuel_type.ilike(f"%{fuel_type}%")
                )

            if min_price:
                conditions.append(Vehicle.base_price >= min_price)

            if max_price:
                conditions.append(Vehicle.base_price <= max_price)

            if specifications:
                for key, value in specifications.items():
                    conditions.append(
                        Vehicle.specifications[key].astext == str(value)
                    )

            if available_only:
                conditions.append(
                    Vehicle.inventory_items.any(
                        and_(
                            InventoryItem.status == InventoryStatus.AVAILABLE,
                            InventoryItem.deleted_at.is_(None),
                        )
                    )
                )

            count_stmt = select(func.count()).select_from(Vehicle).where(
                and_(*conditions)
            )
            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar_one()

            sort_column = getattr(Vehicle, sort_by, Vehicle.year)
            order_func = desc if sort_order.lower() == "desc" else asc

            stmt = (
                select(Vehicle)
                .where(and_(*conditions))
                .order_by(order_func(sort_column))
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)
            vehicles = result.scalars().all()

            logger.info(
                "Vehicle search completed",
                total=total,
                returned=len(vehicles),
                filters={
                    "make": make,
                    "model": model,
                    "year": year,
                    "body_style": body_style,
                    "fuel_type": fuel_type,
                    "available_only": available_only,
                },
            )

            return vehicles, total

        except SQLAlchemyError as e:
            logger.error(
                "Vehicle search failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_with_inventory(
        self,
        vehicle_id: uuid.UUID,
        dealership_id: Optional[uuid.UUID] = None,
    ) -> Optional[Vehicle]:
        """
        Get vehicle with inventory data.

        Args:
            vehicle_id: Vehicle identifier
            dealership_id: Optional dealership filter

        Returns:
            Vehicle with inventory items loaded

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = (
                select(Vehicle)
                .where(
                    and_(
                        Vehicle.id == vehicle_id,
                        Vehicle.deleted_at.is_(None),
                    )
                )
                .options(
                    selectinload(Vehicle.inventory_items),
                )
            )

            result = await self.session.execute(stmt)
            vehicle = result.scalar_one_or_none()

            if vehicle and dealership_id:
                vehicle.inventory_items = [
                    item
                    for item in vehicle.inventory_items
                    if item.dealership_id == dealership_id
                    and item.deleted_at is None
                ]

            if vehicle:
                logger.debug(
                    "Vehicle with inventory retrieved",
                    vehicle_id=str(vehicle_id),
                    inventory_count=len(vehicle.inventory_items),
                )

            return vehicle

        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve vehicle with inventory",
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_available_vehicles(
        self,
        dealership_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Vehicle], int]:
        """
        Get available vehicles with inventory.

        Args:
            dealership_id: Optional dealership filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (vehicles list, total count)

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            conditions = [
                Vehicle.deleted_at.is_(None),
                InventoryItem.deleted_at.is_(None),
                InventoryItem.status == InventoryStatus.AVAILABLE,
            ]

            if dealership_id:
                conditions.append(
                    InventoryItem.dealership_id == dealership_id
                )

            count_stmt = (
                select(func.count(func.distinct(Vehicle.id)))
                .select_from(Vehicle)
                .join(InventoryItem)
                .where(and_(*conditions))
            )
            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar_one()

            stmt = (
                select(Vehicle)
                .join(InventoryItem)
                .where(and_(*conditions))
                .options(selectinload(Vehicle.inventory_items))
                .distinct()
                .order_by(desc(Vehicle.year), Vehicle.make, Vehicle.model)
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)
            vehicles = result.scalars().all()

            logger.info(
                "Available vehicles retrieved",
                total=total,
                returned=len(vehicles),
                dealership_id=str(dealership_id) if dealership_id else None,
            )

            return vehicles, total

        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve available vehicles",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_by_make_model_year(
        self,
        make: str,
        model: str,
        year: int,
    ) -> Sequence[Vehicle]:
        """
        Get vehicles by make, model, and year.

        Args:
            make: Vehicle manufacturer
            model: Vehicle model
            year: Manufacturing year

        Returns:
            List of matching vehicles

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = select(Vehicle).where(
                and_(
                    Vehicle.make.ilike(make),
                    Vehicle.model.ilike(model),
                    Vehicle.year == year,
                    Vehicle.deleted_at.is_(None),
                )
            )

            result = await self.session.execute(stmt)
            vehicles = result.scalars().all()

            logger.debug(
                "Vehicles retrieved by make/model/year",
                make=make,
                model=model,
                year=year,
                count=len(vehicles),
            )

            return vehicles

        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve vehicles by make/model/year",
                make=make,
                model=model,
                year=year,
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
            SQLAlchemyError: If database operation fails
        """
        try:
            conditions = [Vehicle.deleted_at.is_(None)]

            if make:
                conditions.append(Vehicle.make.ilike(make))

            if model:
                conditions.append(Vehicle.model.ilike(model))

            if year:
                conditions.append(Vehicle.year == year)

            stmt = select(
                func.min(Vehicle.base_price),
                func.max(Vehicle.base_price),
            ).where(and_(*conditions))

            result = await self.session.execute(stmt)
            min_price, max_price = result.one()

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
            raise

    async def count_by_filters(
        self,
        make: Optional[str] = None,
        body_style: Optional[str] = None,
        fuel_type: Optional[str] = None,
    ) -> int:
        """
        Count vehicles matching filters.

        Args:
            make: Optional manufacturer filter
            body_style: Optional body style filter
            fuel_type: Optional fuel type filter

        Returns:
            Count of matching vehicles

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            conditions = [Vehicle.deleted_at.is_(None)]

            if make:
                conditions.append(Vehicle.make.ilike(make))

            if body_style:
                conditions.append(Vehicle.body_style.ilike(body_style))

            if fuel_type:
                conditions.append(Vehicle.fuel_type.ilike(fuel_type))

            stmt = select(func.count()).select_from(Vehicle).where(
                and_(*conditions)
            )

            result = await self.session.execute(stmt)
            count = result.scalar_one()

            logger.debug(
                "Vehicle count retrieved",
                count=count,
                filters={
                    "make": make,
                    "body_style": body_style,
                    "fuel_type": fuel_type,
                },
            )

            return count

        except SQLAlchemyError as e:
            logger.error(
                "Failed to count vehicles",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise