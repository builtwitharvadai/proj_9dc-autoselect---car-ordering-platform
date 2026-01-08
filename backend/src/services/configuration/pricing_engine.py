"""
Pricing calculation engine with support for complex pricing rules.

This module implements the PricingEngine class for calculating vehicle prices
with support for base price, option prices, package discounts, tax calculations,
destination charges, and total pricing. Includes caching for performance and
support for regional pricing variations.
"""

import uuid
from decimal import Decimal
from typing import Any, Optional
from datetime import datetime, timedelta

from src.core.logging import get_logger
from src.cache.redis_client import RedisClient, get_redis_client
from src.database.models.vehicle import Vehicle
from src.database.models.vehicle_option import VehicleOption
from src.database.models.package import Package

logger = get_logger(__name__)


class PricingError(Exception):
    """Base exception for pricing calculation errors."""

    def __init__(self, message: str, **context: Any):
        super().__init__(message)
        self.context = context


class PricingValidationError(PricingError):
    """Exception raised when pricing validation fails."""

    pass


class PricingCalculationError(PricingError):
    """Exception raised when pricing calculation fails."""

    pass


class PricingEngine:
    """
    Pricing calculation engine with caching and regional support.

    Implements comprehensive pricing calculations including base price,
    options, packages, discounts, taxes, and destination charges.
    Supports regional pricing variations and performance caching.
    """

    # Cache configuration
    CACHE_TTL_SECONDS = 3600  # 1 hour
    CACHE_KEY_PREFIX = "pricing"

    # Tax rates by region (can be moved to database/config)
    DEFAULT_TAX_RATE = Decimal("0.08")  # 8%
    REGIONAL_TAX_RATES = {
        "CA": Decimal("0.0725"),  # California
        "NY": Decimal("0.08875"),  # New York
        "TX": Decimal("0.0625"),  # Texas
        "FL": Decimal("0.06"),  # Florida
    }

    # Pricing limits for validation
    MIN_PRICE = Decimal("0.00")
    MAX_PRICE = Decimal("10000000.00")
    MAX_DISCOUNT_PERCENTAGE = Decimal("100.00")

    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        enable_caching: bool = True,
        default_region: str = "US",
    ):
        """
        Initialize pricing engine.

        Args:
            redis_client: Redis client for caching (optional)
            enable_caching: Enable price caching
            default_region: Default region for tax calculations
        """
        self._redis_client = redis_client
        self._enable_caching = enable_caching
        self._default_region = default_region

        logger.info(
            "Pricing engine initialized",
            enable_caching=enable_caching,
            default_region=default_region,
        )

    async def _get_redis_client(self) -> Optional[RedisClient]:
        """
        Get Redis client instance.

        Returns:
            Redis client or None if caching disabled
        """
        if not self._enable_caching:
            return None

        if self._redis_client is None:
            try:
                self._redis_client = await get_redis_client()
            except Exception as e:
                logger.warning(
                    "Failed to get Redis client, caching disabled",
                    error=str(e),
                )
                return None

        return self._redis_client

    def _make_cache_key(self, *parts: Any) -> str:
        """
        Generate cache key for pricing data.

        Args:
            *parts: Key components

        Returns:
            Formatted cache key
        """
        key_parts = [str(part) for part in parts if part is not None]
        return f"{self.CACHE_KEY_PREFIX}:{':'.join(key_parts)}"

    async def _get_cached_price(self, cache_key: str) -> Optional[dict[str, Any]]:
        """
        Get cached pricing data.

        Args:
            cache_key: Cache key

        Returns:
            Cached pricing data or None
        """
        redis = await self._get_redis_client()
        if redis is None:
            return None

        try:
            cached_data = await redis.get_json(cache_key)
            if cached_data:
                logger.debug("Cache hit for pricing", cache_key=cache_key)
                return cached_data
        except Exception as e:
            logger.warning(
                "Failed to get cached price",
                cache_key=cache_key,
                error=str(e),
            )

        return None

    async def _set_cached_price(
        self, cache_key: str, price_data: dict[str, Any]
    ) -> None:
        """
        Cache pricing data.

        Args:
            cache_key: Cache key
            price_data: Pricing data to cache
        """
        redis = await self._get_redis_client()
        if redis is None:
            return

        try:
            await redis.set_json(
                cache_key, price_data, ex=self.CACHE_TTL_SECONDS
            )
            logger.debug("Cached pricing data", cache_key=cache_key)
        except Exception as e:
            logger.warning(
                "Failed to cache price",
                cache_key=cache_key,
                error=str(e),
            )

    def _validate_price(self, price: Decimal, field_name: str) -> None:
        """
        Validate price value.

        Args:
            price: Price to validate
            field_name: Field name for error messages

        Raises:
            PricingValidationError: If price is invalid
        """
        if price < self.MIN_PRICE:
            raise PricingValidationError(
                f"{field_name} cannot be negative",
                field=field_name,
                value=float(price),
            )

        if price > self.MAX_PRICE:
            raise PricingValidationError(
                f"{field_name} exceeds maximum allowed value",
                field=field_name,
                value=float(price),
                max_value=float(self.MAX_PRICE),
            )

    def calculate_base_price(self, vehicle: Vehicle) -> Decimal:
        """
        Calculate vehicle base price.

        Args:
            vehicle: Vehicle instance

        Returns:
            Base price

        Raises:
            PricingValidationError: If base price is invalid
        """
        base_price = vehicle.base_price
        self._validate_price(base_price, "base_price")

        logger.debug(
            "Calculated base price",
            vehicle_id=str(vehicle.id),
            base_price=float(base_price),
        )

        return base_price

    def calculate_option_price(self, option: VehicleOption) -> Decimal:
        """
        Calculate single option price.

        Args:
            option: Vehicle option instance

        Returns:
            Option price

        Raises:
            PricingValidationError: If option price is invalid
        """
        option_price = option.price
        self._validate_price(option_price, "option_price")

        logger.debug(
            "Calculated option price",
            option_id=str(option.id),
            option_name=option.name,
            price=float(option_price),
        )

        return option_price

    def calculate_options_total(
        self, options: list[VehicleOption]
    ) -> Decimal:
        """
        Calculate total price for multiple options.

        Args:
            options: List of vehicle options

        Returns:
            Total options price

        Raises:
            PricingCalculationError: If calculation fails
        """
        try:
            total = sum(
                (self.calculate_option_price(opt) for opt in options),
                start=Decimal("0.00"),
            )

            self._validate_price(total, "options_total")

            logger.debug(
                "Calculated options total",
                option_count=len(options),
                total=float(total),
            )

            return total

        except Exception as e:
            logger.error(
                "Failed to calculate options total",
                option_count=len(options),
                error=str(e),
            )
            raise PricingCalculationError(
                "Failed to calculate options total",
                option_count=len(options),
            ) from e

    def calculate_package_discount(
        self, package: Package, options_price: Decimal
    ) -> Decimal:
        """
        Calculate package discount amount.

        Args:
            package: Package instance
            options_price: Total price of options in package

        Returns:
            Discount amount

        Raises:
            PricingValidationError: If discount is invalid
        """
        if package.discount_percentage < Decimal("0.00"):
            raise PricingValidationError(
                "Discount percentage cannot be negative",
                package_id=str(package.id),
                discount_percentage=float(package.discount_percentage),
            )

        if package.discount_percentage > self.MAX_DISCOUNT_PERCENTAGE:
            raise PricingValidationError(
                "Discount percentage exceeds maximum",
                package_id=str(package.id),
                discount_percentage=float(package.discount_percentage),
                max_discount=float(self.MAX_DISCOUNT_PERCENTAGE),
            )

        discount_amount = (
            options_price * package.discount_percentage / Decimal("100.00")
        )

        logger.debug(
            "Calculated package discount",
            package_id=str(package.id),
            package_name=package.name,
            options_price=float(options_price),
            discount_percentage=float(package.discount_percentage),
            discount_amount=float(discount_amount),
        )

        return discount_amount

    def calculate_package_price(
        self, package: Package, included_options: list[VehicleOption]
    ) -> Decimal:
        """
        Calculate package price with discount.

        Args:
            package: Package instance
            included_options: Options included in package

        Returns:
            Package price after discount

        Raises:
            PricingCalculationError: If calculation fails
        """
        try:
            options_total = self.calculate_options_total(included_options)
            discount = self.calculate_package_discount(package, options_total)
            package_price = options_total - discount

            self._validate_price(package_price, "package_price")

            logger.debug(
                "Calculated package price",
                package_id=str(package.id),
                package_name=package.name,
                options_total=float(options_total),
                discount=float(discount),
                final_price=float(package_price),
            )

            return package_price

        except Exception as e:
            logger.error(
                "Failed to calculate package price",
                package_id=str(package.id),
                error=str(e),
            )
            raise PricingCalculationError(
                "Failed to calculate package price",
                package_id=str(package.id),
            ) from e

    def get_tax_rate(self, region: Optional[str] = None) -> Decimal:
        """
        Get tax rate for region.

        Args:
            region: Region code (e.g., "CA", "NY")

        Returns:
            Tax rate as decimal
        """
        if region is None:
            region = self._default_region

        tax_rate = self.REGIONAL_TAX_RATES.get(
            region, self.DEFAULT_TAX_RATE
        )

        logger.debug(
            "Retrieved tax rate",
            region=region,
            tax_rate=float(tax_rate),
        )

        return tax_rate

    def calculate_tax(
        self, subtotal: Decimal, region: Optional[str] = None
    ) -> Decimal:
        """
        Calculate tax amount.

        Args:
            subtotal: Subtotal before tax
            region: Region code for tax rate

        Returns:
            Tax amount

        Raises:
            PricingValidationError: If tax calculation is invalid
        """
        self._validate_price(subtotal, "subtotal")

        tax_rate = self.get_tax_rate(region)
        tax_amount = subtotal * tax_rate

        logger.debug(
            "Calculated tax",
            subtotal=float(subtotal),
            region=region,
            tax_rate=float(tax_rate),
            tax_amount=float(tax_amount),
        )

        return tax_amount

    def calculate_destination_charge(self, vehicle: Vehicle) -> Decimal:
        """
        Calculate destination charge.

        Args:
            vehicle: Vehicle instance

        Returns:
            Destination charge

        Raises:
            PricingValidationError: If destination charge is invalid
        """
        destination_charge = vehicle.destination_charge
        self._validate_price(destination_charge, "destination_charge")

        logger.debug(
            "Calculated destination charge",
            vehicle_id=str(vehicle.id),
            destination_charge=float(destination_charge),
        )

        return destination_charge

    async def calculate_total_price(
        self,
        vehicle: Vehicle,
        options: Optional[list[VehicleOption]] = None,
        packages: Optional[list[tuple[Package, list[VehicleOption]]]] = None,
        region: Optional[str] = None,
        include_tax: bool = True,
        include_destination: bool = True,
    ) -> dict[str, Any]:
        """
        Calculate total vehicle price with all components.

        Args:
            vehicle: Vehicle instance
            options: List of selected options
            packages: List of (package, included_options) tuples
            region: Region code for tax calculation
            include_tax: Include tax in total
            include_destination: Include destination charge in total

        Returns:
            Dictionary with price breakdown

        Raises:
            PricingCalculationError: If calculation fails
        """
        try:
            # Generate cache key
            cache_key = self._make_cache_key(
                str(vehicle.id),
                ",".join(str(opt.id) for opt in (options or [])),
                ",".join(str(pkg[0].id) for pkg in (packages or [])),
                region,
                include_tax,
                include_destination,
            )

            # Check cache
            cached_result = await self._get_cached_price(cache_key)
            if cached_result:
                return cached_result

            # Calculate base price
            base_price = self.calculate_base_price(vehicle)

            # Calculate options price
            options_price = Decimal("0.00")
            if options:
                options_price = self.calculate_options_total(options)

            # Calculate packages price
            packages_price = Decimal("0.00")
            packages_discount = Decimal("0.00")
            if packages:
                for package, included_options in packages:
                    package_price = self.calculate_package_price(
                        package, included_options
                    )
                    packages_price += package_price

                    # Calculate discount saved
                    options_total = self.calculate_options_total(
                        included_options
                    )
                    discount = self.calculate_package_discount(
                        package, options_total
                    )
                    packages_discount += discount

            # Calculate subtotal
            subtotal = base_price + options_price + packages_price

            # Calculate destination charge
            destination_charge = Decimal("0.00")
            if include_destination:
                destination_charge = self.calculate_destination_charge(vehicle)

            # Calculate tax
            tax_amount = Decimal("0.00")
            if include_tax:
                taxable_amount = subtotal + destination_charge
                tax_amount = self.calculate_tax(taxable_amount, region)

            # Calculate total
            total = subtotal + destination_charge + tax_amount

            # Validate final total
            self._validate_price(total, "total_price")

            # Build result
            result = {
                "vehicle_id": str(vehicle.id),
                "base_price": float(base_price),
                "options_price": float(options_price),
                "packages_price": float(packages_price),
                "packages_discount": float(packages_discount),
                "subtotal": float(subtotal),
                "destination_charge": float(destination_charge),
                "tax_amount": float(tax_amount),
                "tax_rate": float(self.get_tax_rate(region)),
                "total": float(total),
                "region": region or self._default_region,
                "calculated_at": datetime.utcnow().isoformat(),
                "breakdown": {
                    "base": float(base_price),
                    "options": float(options_price),
                    "packages": float(packages_price),
                    "destination": float(destination_charge),
                    "tax": float(tax_amount),
                },
            }

            # Cache result
            await self._set_cached_price(cache_key, result)

            logger.info(
                "Calculated total price",
                vehicle_id=str(vehicle.id),
                total=float(total),
                options_count=len(options) if options else 0,
                packages_count=len(packages) if packages else 0,
            )

            return result

        except PricingError:
            raise
        except Exception as e:
            logger.error(
                "Failed to calculate total price",
                vehicle_id=str(vehicle.id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise PricingCalculationError(
                "Failed to calculate total price",
                vehicle_id=str(vehicle.id),
            ) from e

    async def invalidate_cache(
        self, vehicle_id: Optional[uuid.UUID] = None
    ) -> int:
        """
        Invalidate pricing cache.

        Args:
            vehicle_id: Vehicle ID to invalidate (None for all)

        Returns:
            Number of cache entries invalidated
        """
        redis = await self._get_redis_client()
        if redis is None:
            return 0

        try:
            if vehicle_id:
                pattern = self._make_cache_key(str(vehicle_id), "*")
            else:
                pattern = self._make_cache_key("*")

            count = await redis.delete_pattern(pattern)

            logger.info(
                "Invalidated pricing cache",
                vehicle_id=str(vehicle_id) if vehicle_id else "all",
                count=count,
            )

            return count

        except Exception as e:
            logger.error(
                "Failed to invalidate pricing cache",
                vehicle_id=str(vehicle_id) if vehicle_id else "all",
                error=str(e),
            )
            return 0