"""
Payment repository for secure payment data access with encryption support.

This module implements the PaymentRepository class for managing payment records
with comprehensive encryption support, status tracking, and audit trails. Provides
async methods for creating, retrieving, and updating payment records with proper
error handling and logging.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.logging import get_logger
from src.database.models.payment import (
    Payment,
    PaymentStatus,
    PaymentMethodType,
    PaymentStatusHistory,
)

logger = get_logger(__name__)


class PaymentRepositoryError(Exception):
    """Base exception for payment repository errors."""

    def __init__(self, message: str, **context: Any):
        super().__init__(message)
        self.context = context


class PaymentNotFoundError(PaymentRepositoryError):
    """Raised when payment is not found."""

    pass


class PaymentRepository:
    """
    Repository for payment data access with encryption support.

    Provides async methods for creating, retrieving, and updating payment records
    with comprehensive error handling, logging, and audit trail management.
    Implements encryption for sensitive payment data and status history tracking.

    Attributes:
        session: Async database session for executing queries
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize payment repository.

        Args:
            session: Async database session
        """
        self.session = session
        logger.debug("PaymentRepository initialized")

    async def create_payment(
        self,
        order_id: uuid.UUID,
        stripe_payment_intent_id: str,
        amount: Decimal,
        currency: str,
        payment_method_type: PaymentMethodType,
        payment_method_token: Optional[str] = None,
        last_four: Optional[str] = None,
        card_brand: Optional[str] = None,
        metadata: Optional[dict] = None,
        created_by: Optional[str] = None,
    ) -> Payment:
        """
        Create new payment record.

        Args:
            order_id: Associated order identifier
            stripe_payment_intent_id: Stripe payment intent ID
            amount: Payment amount in cents
            currency: Payment currency code (ISO 4217)
            payment_method_type: Type of payment method
            payment_method_token: Tokenized payment method (encrypted)
            last_four: Last 4 digits of card/account
            card_brand: Card brand (Visa, Mastercard, etc.)
            metadata: Additional payment metadata
            created_by: User who created this record

        Returns:
            Created payment record

        Raises:
            PaymentRepositoryError: If payment creation fails
        """
        try:
            payment = Payment(
                order_id=order_id,
                stripe_payment_intent_id=stripe_payment_intent_id,
                amount=amount,
                currency=currency,
                status=PaymentStatus.PENDING,
                payment_method_type=payment_method_type,
                payment_method_token=payment_method_token,
                last_four=last_four,
                card_brand=card_brand,
                metadata=metadata or {},
                created_by=created_by,
                updated_by=created_by,
            )

            self.session.add(payment)
            await self.session.flush()

            # Create initial status history
            await self._create_status_history(
                payment_id=payment.id,
                from_status=None,
                to_status=PaymentStatus.PENDING,
                reason="Payment created",
                created_by=created_by,
            )

            await self.session.commit()

            logger.info(
                "Payment created successfully",
                payment_id=str(payment.id),
                order_id=str(order_id),
                amount=float(amount),
                currency=currency,
                payment_method_type=payment_method_type.value,
            )

            return payment

        except IntegrityError as e:
            await self.session.rollback()
            logger.error(
                "Payment creation failed - integrity error",
                order_id=str(order_id),
                error=str(e),
            )
            raise PaymentRepositoryError(
                "Payment creation failed - duplicate or constraint violation",
                order_id=str(order_id),
                error=str(e),
            ) from e
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Payment creation failed - database error",
                order_id=str(order_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise PaymentRepositoryError(
                "Payment creation failed",
                order_id=str(order_id),
                error=str(e),
            ) from e

    async def get_payment_by_id(
        self,
        payment_id: uuid.UUID,
        include_history: bool = False,
    ) -> Optional[Payment]:
        """
        Retrieve payment by ID.

        Args:
            payment_id: Payment identifier
            include_history: Whether to include status history

        Returns:
            Payment record or None if not found

        Raises:
            PaymentRepositoryError: If retrieval fails
        """
        try:
            stmt = select(Payment).where(Payment.id == payment_id)

            if include_history:
                stmt = stmt.options(selectinload(Payment.payment_status_history))

            result = await self.session.execute(stmt)
            payment = result.scalar_one_or_none()

            if payment:
                logger.debug(
                    "Payment retrieved successfully",
                    payment_id=str(payment_id),
                    status=payment.status.value,
                )
            else:
                logger.debug(
                    "Payment not found",
                    payment_id=str(payment_id),
                )

            return payment

        except SQLAlchemyError as e:
            logger.error(
                "Payment retrieval failed",
                payment_id=str(payment_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise PaymentRepositoryError(
                "Payment retrieval failed",
                payment_id=str(payment_id),
                error=str(e),
            ) from e

    async def get_payment_by_stripe_intent_id(
        self,
        stripe_payment_intent_id: str,
        include_history: bool = False,
    ) -> Optional[Payment]:
        """
        Retrieve payment by Stripe payment intent ID.

        Args:
            stripe_payment_intent_id: Stripe payment intent identifier
            include_history: Whether to include status history

        Returns:
            Payment record or None if not found

        Raises:
            PaymentRepositoryError: If retrieval fails
        """
        try:
            stmt = select(Payment).where(
                Payment.stripe_payment_intent_id == stripe_payment_intent_id
            )

            if include_history:
                stmt = stmt.options(selectinload(Payment.payment_status_history))

            result = await self.session.execute(stmt)
            payment = result.scalar_one_or_none()

            if payment:
                logger.debug(
                    "Payment retrieved by Stripe intent ID",
                    stripe_payment_intent_id=stripe_payment_intent_id,
                    payment_id=str(payment.id),
                )
            else:
                logger.debug(
                    "Payment not found by Stripe intent ID",
                    stripe_payment_intent_id=stripe_payment_intent_id,
                )

            return payment

        except SQLAlchemyError as e:
            logger.error(
                "Payment retrieval by Stripe intent ID failed",
                stripe_payment_intent_id=stripe_payment_intent_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise PaymentRepositoryError(
                "Payment retrieval failed",
                stripe_payment_intent_id=stripe_payment_intent_id,
                error=str(e),
            ) from e

    async def get_payments_by_order_id(
        self,
        order_id: uuid.UUID,
        include_history: bool = False,
    ) -> list[Payment]:
        """
        Retrieve all payments for an order.

        Args:
            order_id: Order identifier
            include_history: Whether to include status history

        Returns:
            List of payment records

        Raises:
            PaymentRepositoryError: If retrieval fails
        """
        try:
            stmt = (
                select(Payment)
                .where(Payment.order_id == order_id)
                .order_by(Payment.created_at.desc())
            )

            if include_history:
                stmt = stmt.options(selectinload(Payment.payment_status_history))

            result = await self.session.execute(stmt)
            payments = list(result.scalars().all())

            logger.debug(
                "Payments retrieved for order",
                order_id=str(order_id),
                count=len(payments),
            )

            return payments

        except SQLAlchemyError as e:
            logger.error(
                "Payment retrieval by order ID failed",
                order_id=str(order_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise PaymentRepositoryError(
                "Payment retrieval failed",
                order_id=str(order_id),
                error=str(e),
            ) from e

    async def update_payment_status(
        self,
        payment_id: uuid.UUID,
        new_status: PaymentStatus,
        failure_code: Optional[str] = None,
        failure_message: Optional[str] = None,
        reason: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> Payment:
        """
        Update payment status with validation and history tracking.

        Args:
            payment_id: Payment identifier
            new_status: New payment status
            failure_code: Failure code if status is FAILED
            failure_message: Failure message if status is FAILED
            reason: Reason for status change
            updated_by: User who updated this record

        Returns:
            Updated payment record

        Raises:
            PaymentNotFoundError: If payment not found
            PaymentRepositoryError: If update fails
        """
        try:
            payment = await self.get_payment_by_id(payment_id)
            if not payment:
                raise PaymentNotFoundError(
                    "Payment not found",
                    payment_id=str(payment_id),
                )

            old_status = payment.status

            # Update status with validation
            payment.update_status(
                new_status=new_status,
                failure_code=failure_code,
                failure_message=failure_message,
            )
            payment.updated_by = updated_by

            # Create status history
            await self._create_status_history(
                payment_id=payment_id,
                from_status=old_status,
                to_status=new_status,
                reason=reason or f"Status changed to {new_status.value}",
                created_by=updated_by,
            )

            await self.session.commit()

            logger.info(
                "Payment status updated",
                payment_id=str(payment_id),
                old_status=old_status.value,
                new_status=new_status.value,
                failure_code=failure_code,
            )

            return payment

        except PaymentNotFoundError:
            raise
        except ValueError as e:
            await self.session.rollback()
            logger.error(
                "Payment status update failed - validation error",
                payment_id=str(payment_id),
                new_status=new_status.value,
                error=str(e),
            )
            raise PaymentRepositoryError(
                "Invalid status transition",
                payment_id=str(payment_id),
                new_status=new_status.value,
                error=str(e),
            ) from e
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Payment status update failed",
                payment_id=str(payment_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise PaymentRepositoryError(
                "Payment status update failed",
                payment_id=str(payment_id),
                error=str(e),
            ) from e

    async def add_refund(
        self,
        payment_id: uuid.UUID,
        refund_amount: Decimal,
        reason: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> Payment:
        """
        Add refund to payment.

        Args:
            payment_id: Payment identifier
            refund_amount: Amount to refund
            reason: Reason for refund
            updated_by: User who updated this record

        Returns:
            Updated payment record

        Raises:
            PaymentNotFoundError: If payment not found
            PaymentRepositoryError: If refund fails
        """
        try:
            payment = await self.get_payment_by_id(payment_id)
            if not payment:
                raise PaymentNotFoundError(
                    "Payment not found",
                    payment_id=str(payment_id),
                )

            old_status = payment.status

            # Add refund with validation
            payment.add_refund(refund_amount)
            payment.updated_by = updated_by

            # Create status history if status changed
            if payment.status != old_status:
                await self._create_status_history(
                    payment_id=payment_id,
                    from_status=old_status,
                    to_status=payment.status,
                    reason=reason or f"Refund of {refund_amount} applied",
                    created_by=updated_by,
                )

            await self.session.commit()

            logger.info(
                "Refund added to payment",
                payment_id=str(payment_id),
                refund_amount=float(refund_amount),
                total_refunded=float(payment.refund_amount),
                new_status=payment.status.value,
            )

            return payment

        except PaymentNotFoundError:
            raise
        except ValueError as e:
            await self.session.rollback()
            logger.error(
                "Refund addition failed - validation error",
                payment_id=str(payment_id),
                refund_amount=float(refund_amount),
                error=str(e),
            )
            raise PaymentRepositoryError(
                "Invalid refund amount",
                payment_id=str(payment_id),
                refund_amount=float(refund_amount),
                error=str(e),
            ) from e
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Refund addition failed",
                payment_id=str(payment_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise PaymentRepositoryError(
                "Refund addition failed",
                payment_id=str(payment_id),
                error=str(e),
            ) from e

    async def update_payment_metadata(
        self,
        payment_id: uuid.UUID,
        metadata: dict,
        updated_by: Optional[str] = None,
    ) -> Payment:
        """
        Update payment metadata.

        Args:
            payment_id: Payment identifier
            metadata: New metadata dictionary
            updated_by: User who updated this record

        Returns:
            Updated payment record

        Raises:
            PaymentNotFoundError: If payment not found
            PaymentRepositoryError: If update fails
        """
        try:
            payment = await self.get_payment_by_id(payment_id)
            if not payment:
                raise PaymentNotFoundError(
                    "Payment not found",
                    payment_id=str(payment_id),
                )

            payment.metadata = metadata
            payment.updated_by = updated_by

            await self.session.commit()

            logger.info(
                "Payment metadata updated",
                payment_id=str(payment_id),
                metadata_keys=list(metadata.keys()),
            )

            return payment

        except PaymentNotFoundError:
            raise
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Payment metadata update failed",
                payment_id=str(payment_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise PaymentRepositoryError(
                "Payment metadata update failed",
                payment_id=str(payment_id),
                error=str(e),
            ) from e

    async def get_payment_statistics(
        self,
        order_id: Optional[uuid.UUID] = None,
        status: Optional[PaymentStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """
        Get payment statistics with optional filters.

        Args:
            order_id: Filter by order ID
            status: Filter by payment status
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            Dictionary containing payment statistics

        Raises:
            PaymentRepositoryError: If statistics retrieval fails
        """
        try:
            conditions = []

            if order_id:
                conditions.append(Payment.order_id == order_id)
            if status:
                conditions.append(Payment.status == status)
            if start_date:
                conditions.append(Payment.created_at >= start_date)
            if end_date:
                conditions.append(Payment.created_at <= end_date)

            base_stmt = select(Payment)
            if conditions:
                base_stmt = base_stmt.where(and_(*conditions))

            # Total count
            count_stmt = select(func.count()).select_from(base_stmt.subquery())
            count_result = await self.session.execute(count_stmt)
            total_count = count_result.scalar() or 0

            # Total amount
            amount_stmt = select(func.sum(Payment.amount)).select_from(
                base_stmt.subquery()
            )
            amount_result = await self.session.execute(amount_stmt)
            total_amount = amount_result.scalar() or Decimal("0.00")

            # Total refunded
            refund_stmt = select(func.sum(Payment.refund_amount)).select_from(
                base_stmt.subquery()
            )
            refund_result = await self.session.execute(refund_stmt)
            total_refunded = refund_result.scalar() or Decimal("0.00")

            # Status breakdown
            status_stmt = (
                select(Payment.status, func.count())
                .select_from(base_stmt.subquery())
                .group_by(Payment.status)
            )
            status_result = await self.session.execute(status_stmt)
            status_breakdown = {
                status.value: count for status, count in status_result.all()
            }

            statistics = {
                "total_count": total_count,
                "total_amount": float(total_amount),
                "total_refunded": float(total_refunded),
                "net_amount": float(total_amount - total_refunded),
                "status_breakdown": status_breakdown,
            }

            logger.debug(
                "Payment statistics retrieved",
                total_count=total_count,
                total_amount=float(total_amount),
            )

            return statistics

        except SQLAlchemyError as e:
            logger.error(
                "Payment statistics retrieval failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise PaymentRepositoryError(
                "Payment statistics retrieval failed",
                error=str(e),
            ) from e

    async def _create_status_history(
        self,
        payment_id: uuid.UUID,
        from_status: Optional[PaymentStatus],
        to_status: PaymentStatus,
        reason: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> PaymentStatusHistory:
        """
        Create payment status history record.

        Args:
            payment_id: Payment identifier
            from_status: Previous payment status
            to_status: New payment status
            reason: Reason for status change
            created_by: User who created this record

        Returns:
            Created status history record

        Raises:
            PaymentRepositoryError: If creation fails
        """
        try:
            history = PaymentStatusHistory(
                payment_id=payment_id,
                from_status=from_status,
                to_status=to_status,
                reason=reason,
                created_by=created_by,
            )

            self.session.add(history)
            await self.session.flush()

            logger.debug(
                "Payment status history created",
                payment_id=str(payment_id),
                from_status=from_status.value if from_status else None,
                to_status=to_status.value,
            )

            return history

        except SQLAlchemyError as e:
            logger.error(
                "Payment status history creation failed",
                payment_id=str(payment_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise PaymentRepositoryError(
                "Payment status history creation failed",
                payment_id=str(payment_id),
                error=str(e),
            ) from e