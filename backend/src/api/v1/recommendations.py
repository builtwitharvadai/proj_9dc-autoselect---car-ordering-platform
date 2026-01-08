"""
Recommendation API endpoints for package recommendations and analytics.

This module provides FastAPI router endpoints for the recommendation engine,
including package recommendations, popular configurations, and event tracking.
Implements comprehensive error handling, caching, and performance optimization
to meet the <100ms response time requirement.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import DatabaseSession, OptionalUser
from src.cache.redis_client import RedisClient, get_redis_client
from src.core.logging import get_logger
from src.database.models.recommendation_analytics import RecommendationEventType
from src.schemas.recommendations import (
    PackageRecommendation,
    PopularConfiguration,
    RecommendationRequest,
    RecommendationResponse,
)
from src.services.recommendations.service import (
    RecommendationService,
    RecommendationServiceError,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# Cache configuration
RECOMMENDATION_CACHE_TTL = 300  # 5 minutes
POPULAR_CONFIG_CACHE_TTL = 600  # 10 minutes


async def get_recommendation_service(
    db: DatabaseSession,
    redis: RedisClient = Depends(get_redis_client),
) -> RecommendationService:
    """
    Dependency to get recommendation service instance.

    Args:
        db: Database session
        redis: Redis client for caching

    Returns:
        Configured recommendation service
    """
    return RecommendationService(
        db_session=db,
        redis_client=redis,
        enable_cache=True,
        enable_analytics=True,
    )


@router.post(
    "/packages",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get package recommendations",
    description="Generate intelligent package recommendations based on selected options",
)
async def get_package_recommendations(
    request: RecommendationRequest,
    service: RecommendationService = Depends(get_recommendation_service),
    current_user: OptionalUser = None,
) -> RecommendationResponse:
    """
    Get package recommendations for a vehicle configuration.

    Analyzes selected options and generates personalized package recommendations
    with savings calculations and value propositions. Includes popular
    configurations for similar vehicles.

    Args:
        request: Recommendation request with vehicle and selections
        service: Recommendation service instance
        current_user: Optional authenticated user

    Returns:
        Recommendation response with packages and metadata

    Raises:
        HTTPException: If recommendation generation fails
    """
    start_time = datetime.utcnow()

    try:
        # Extract user context
        user_id = current_user.id if current_user else None

        # Convert string IDs to UUIDs
        try:
            vehicle_id = uuid.UUID(str(request.vehicle_id))
            selected_option_ids = [
                uuid.UUID(opt_id) for opt_id in request.selected_options
            ]
        except ValueError as e:
            logger.warning(
                "Invalid UUID format in request",
                error=str(e),
                vehicle_id=str(request.vehicle_id),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UUID format in request parameters",
            ) from e

        # Generate recommendations
        logger.info(
            "Generating package recommendations",
            vehicle_id=str(vehicle_id),
            option_count=len(selected_option_ids),
            user_id=str(user_id) if user_id else None,
        )

        result = await service.get_package_recommendations(
            vehicle_id=vehicle_id,
            selected_option_ids=selected_option_ids,
            user_id=user_id,
            session_id=None,  # Could be extracted from request headers
            max_results=request.max_recommendations,
            include_popular=request.include_popular,
        )

        # Calculate processing time
        processing_time_ms = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )

        # Build response
        response = RecommendationResponse(
            vehicle_id=vehicle_id,
            recommendations=[
                PackageRecommendation(**rec) for rec in result["recommendations"]
            ],
            popular_configurations=[
                PopularConfiguration(**config)
                for config in result.get("popular_configurations", [])
            ],
            total_potential_savings=sum(
                rec["savings_amount"] for rec in result["recommendations"]
            ),
            recommendation_metadata=result.get("metadata", {}),
            generated_at=datetime.utcnow(),
            algorithm_version="1.0",
            processing_time_ms=processing_time_ms,
        )

        logger.info(
            "Package recommendations generated successfully",
            vehicle_id=str(vehicle_id),
            recommendation_count=len(response.recommendations),
            processing_time_ms=processing_time_ms,
        )

        return response

    except RecommendationServiceError as e:
        logger.error(
            "Recommendation service error",
            error=str(e),
            vehicle_id=str(request.vehicle_id),
            **e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error generating recommendations",
            error=str(e),
            vehicle_id=str(request.vehicle_id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating recommendations",
        ) from e


@router.get(
    "/popular",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get popular configurations",
    description="Retrieve popular vehicle configurations for similar vehicles",
)
async def get_popular_configurations(
    vehicle_id: str = Query(..., description="Vehicle ID to find similar configurations"),
    make: Optional[str] = Query(None, description="Vehicle make for broader matching"),
    model: Optional[str] = Query(None, description="Vehicle model for broader matching"),
    year: Optional[int] = Query(None, description="Vehicle year for broader matching"),
    body_style: Optional[str] = Query(None, description="Vehicle body style for broader matching"),
    limit: int = Query(5, ge=1, le=10, description="Maximum number of configurations"),
    service: RecommendationService = Depends(get_recommendation_service),
) -> dict[str, Any]:
    """
    Get popular configurations for similar vehicles.

    Retrieves the most popular vehicle configurations based on historical data,
    filtered by vehicle attributes for relevance.

    Args:
        vehicle_id: Vehicle ID for specific matching
        make: Optional vehicle make
        model: Optional vehicle model
        year: Optional vehicle year
        body_style: Optional body style
        limit: Maximum configurations to return
        service: Recommendation service instance

    Returns:
        Dictionary with popular configurations and metadata

    Raises:
        HTTPException: If query fails
    """
    start_time = datetime.utcnow()

    try:
        # Convert vehicle_id to UUID
        try:
            vehicle_uuid = uuid.UUID(vehicle_id)
        except ValueError as e:
            logger.warning(
                "Invalid vehicle ID format",
                error=str(e),
                vehicle_id=vehicle_id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid vehicle ID format",
            ) from e

        logger.info(
            "Retrieving popular configurations",
            vehicle_id=vehicle_id,
            make=make,
            model=model,
            year=year,
            body_style=body_style,
            limit=limit,
        )

        result = await service.get_popular_configurations(
            vehicle_id=vehicle_uuid,
            make=make,
            model=model,
            year=year,
            body_style=body_style,
            limit=limit,
        )

        processing_time_ms = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )

        logger.info(
            "Popular configurations retrieved successfully",
            vehicle_id=vehicle_id,
            configuration_count=len(result["configurations"]),
            processing_time_ms=processing_time_ms,
        )

        return result

    except RecommendationServiceError as e:
        logger.error(
            "Failed to retrieve popular configurations",
            error=str(e),
            vehicle_id=vehicle_id,
            **e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve popular configurations: {str(e)}",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error retrieving popular configurations",
            error=str(e),
            vehicle_id=vehicle_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving configurations",
        ) from e


@router.post(
    "/track",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Track recommendation events",
    description="Track user interactions with recommendations for analytics",
)
async def track_recommendation_event(
    vehicle_id: str = Query(..., description="Vehicle ID"),
    event_type: str = Query(..., description="Event type (viewed, clicked, selected)"),
    package_ids: list[str] = Query(..., description="Package IDs involved in event"),
    service: RecommendationService = Depends(get_recommendation_service),
    current_user: OptionalUser = None,
) -> None:
    """
    Track recommendation interaction events.

    Records user interactions with recommendations for analytics and model
    improvement. Events include viewing, clicking, and selecting packages.

    Args:
        vehicle_id: Vehicle ID
        event_type: Type of event (viewed, clicked, selected)
        package_ids: Package IDs involved in the event
        service: Recommendation service instance
        current_user: Optional authenticated user

    Raises:
        HTTPException: If tracking fails or invalid event type
    """
    try:
        # Validate event type
        try:
            event_type_enum = RecommendationEventType(event_type.lower())
        except ValueError as e:
            logger.warning(
                "Invalid event type",
                error=str(e),
                event_type=event_type,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type: {event_type}. Must be one of: viewed, clicked, selected, dismissed",
            ) from e

        # Convert IDs to UUIDs
        try:
            vehicle_uuid = uuid.UUID(vehicle_id)
            package_uuids = [uuid.UUID(pkg_id) for pkg_id in package_ids]
        except ValueError as e:
            logger.warning(
                "Invalid UUID format in tracking request",
                error=str(e),
                vehicle_id=vehicle_id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UUID format in request parameters",
            ) from e

        # Extract user context
        user_id = current_user.id if current_user else None

        logger.info(
            "Tracking recommendation event",
            vehicle_id=vehicle_id,
            event_type=event_type,
            package_count=len(package_uuids),
            user_id=str(user_id) if user_id else None,
        )

        await service.track_recommendation_events(
            vehicle_id=vehicle_uuid,
            event_type=event_type_enum,
            package_ids=package_uuids,
            user_id=user_id,
            session_id=None,  # Could be extracted from request headers
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "source": "api",
            },
        )

        logger.info(
            "Recommendation event tracked successfully",
            vehicle_id=vehicle_id,
            event_type=event_type,
        )

    except RecommendationServiceError as e:
        logger.error(
            "Failed to track recommendation event",
            error=str(e),
            vehicle_id=vehicle_id,
            event_type=event_type,
            **e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track event: {str(e)}",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error tracking recommendation event",
            error=str(e),
            vehicle_id=vehicle_id,
            event_type=event_type,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while tracking event",
        ) from e