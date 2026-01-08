"""Order state machine implementation with transition validation.

This module implements the OrderStateMachine class for managing order lifecycle
transitions with comprehensive validation, side effects, and business rule
enforcement.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from src.services.orders.enums import (
    OrderStatus,
    PaymentStatus,
    FulfillmentStatus,
    validate_order_status_transition,
    validate_payment_status_transition,
    validate_fulfillment_status_transition,
    get_allowed_order_transitions,
)

logger = logging.getLogger(__name__)


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(
        self,
        message: str,
        current_state: OrderStatus,
        target_state: OrderStatus,
        **context: Any
    ):
        super().__init__(message)
        self.current_state = current_state
        self.target_state = target_state
        self.context = context


class OrderStateMachine:
    """State machine for managing order lifecycle transitions.

    Handles order status transitions with validation, guards, and side effects.
    Implements business rules for order processing workflow.
    """

    def __init__(self, db_session: Session):
        """Initialize state machine with database session.

        Args:
            db_session: SQLAlchemy database session for persistence
        """
        self.db = db_session
        self._transition_guards: Dict[
            tuple[OrderStatus, OrderStatus],
            Callable[[Any], bool]
        ] = self._initialize_guards()
        self._side_effects: Dict[
            OrderStatus,
            Callable[[Any], None]
        ] = self._initialize_side_effects()

        logger.info(
            "OrderStateMachine initialized",
            guards_count=len(self._transition_guards),
            side_effects_count=len(self._side_effects)
        )

    def _initialize_guards(
        self
    ) -> Dict[tuple[OrderStatus, OrderStatus], Callable[[Any], bool]]:
        """Initialize transition guard functions.

        Returns:
            Dictionary mapping state transitions to guard functions
        """
        return {
            (OrderStatus.PENDING, OrderStatus.PAYMENT_PROCESSING): (
                self._guard_payment_processing
            ),
            (OrderStatus.PAYMENT_PROCESSING, OrderStatus.CONFIRMED): (
                self._guard_payment_confirmed
            ),
            (OrderStatus.CONFIRMED, OrderStatus.IN_PRODUCTION): (
                self._guard_production_start
            ),
            (OrderStatus.QUALITY_CHECK, OrderStatus.IN_TRANSIT): (
                self._guard_quality_passed
            ),
            (OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED): (
                self._guard_delivery_confirmed
            ),
            (OrderStatus.DELIVERED, OrderStatus.REFUNDED): (
                self._guard_refund_eligible
            ),
        }

    def _initialize_side_effects(
        self
    ) -> Dict[OrderStatus, Callable[[Any], None]]:
        """Initialize side effect handlers for state transitions.

        Returns:
            Dictionary mapping target states to side effect functions
        """
        return {
            OrderStatus.PAYMENT_PROCESSING: self._effect_payment_processing,
            OrderStatus.CONFIRMED: self._effect_order_confirmed,
            OrderStatus.IN_PRODUCTION: self._effect_production_started,
            OrderStatus.QUALITY_CHECK: self._effect_quality_check,
            OrderStatus.IN_TRANSIT: self._effect_shipment_started,
            OrderStatus.OUT_FOR_DELIVERY: self._effect_out_for_delivery,
            OrderStatus.DELIVERED: self._effect_delivered,
            OrderStatus.CANCELLED: self._effect_cancelled,
            OrderStatus.REFUNDED: self._effect_refunded,
        }

    def validate_transition(
        self,
        order: Any,
        target_status: OrderStatus,
        user_id: Optional[UUID] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Validate if transition to target status is allowed.

        Args:
            order: Order instance to validate
            target_status: Desired target status
            user_id: User initiating the transition
            reason: Optional reason for transition

        Returns:
            True if transition is valid

        Raises:
            StateTransitionError: If transition is invalid
        """
        current_status = order.status

        logger.debug(
            "Validating state transition",
            order_id=str(order.id),
            current_status=current_status.value,
            target_status=target_status.value,
            user_id=str(user_id) if user_id else None
        )

        # Check if transition is allowed by state machine rules
        if not validate_order_status_transition(current_status, target_status):
            allowed = get_allowed_order_transitions(current_status)
            raise StateTransitionError(
                f"Invalid transition from {current_status.value} to "
                f"{target_status.value}",
                current_state=current_status,
                target_state=target_status,
                allowed_transitions=[s.value for s in allowed]
            )

        # Execute transition guard if defined
        guard_key = (current_status, target_status)
        if guard_key in self._transition_guards:
            guard_func = self._transition_guards[guard_key]
            if not guard_func(order):
                raise StateTransitionError(
                    f"Transition guard failed for {current_status.value} -> "
                    f"{target_status.value}",
                    current_state=current_status,
                    target_state=target_status,
                    guard_failed=True
                )

        logger.info(
            "State transition validated",
            order_id=str(order.id),
            transition=f"{current_status.value}->{target_status.value}",
            user_id=str(user_id) if user_id else None
        )

        return True

    def apply_transition(
        self,
        order: Any,
        target_status: OrderStatus,
        user_id: Optional[UUID] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Apply state transition to order with side effects.

        Args:
            order: Order instance to transition
            target_status: Target status to transition to
            user_id: User initiating the transition
            reason: Optional reason for transition
            metadata: Additional metadata for transition

        Raises:
            StateTransitionError: If transition fails
        """
        current_status = order.status

        try:
            # Validate transition
            self.validate_transition(order, target_status, user_id, reason)

            # Update order status
            old_status = order.status
            order.status = target_status
            order.updated_at = datetime.utcnow()

            # Record status history
            self._record_status_change(
                order,
                old_status,
                target_status,
                user_id,
                reason,
                metadata
            )

            # Execute side effects
            if target_status in self._side_effects:
                side_effect = self._side_effects[target_status]
                side_effect(order)

            # Commit changes
            self.db.commit()

            logger.info(
                "State transition applied successfully",
                order_id=str(order.id),
                transition=f"{old_status.value}->{target_status.value}",
                user_id=str(user_id) if user_id else None
            )

        except Exception as e:
            self.db.rollback()
            logger.error(
                "State transition failed",
                order_id=str(order.id),
                transition=f"{current_status.value}->{target_status.value}",
                error=str(e),
                exc_info=True
            )
            raise

    def get_allowed_transitions(self, order: Any) -> Set[OrderStatus]:
        """Get allowed transitions from current order status.

        Args:
            order: Order instance

        Returns:
            Set of allowed target statuses
        """
        return get_allowed_order_transitions(order.status)

    def can_cancel(self, order: Any) -> bool:
        """Check if order can be cancelled from current status.

        Args:
            order: Order instance

        Returns:
            True if cancellation is allowed
        """
        return order.status.can_cancel()

    def can_refund(self, order: Any) -> bool:
        """Check if order can be refunded from current status.

        Args:
            order: Order instance

        Returns:
            True if refund is allowed
        """
        return order.status.can_refund()

    def _record_status_change(
        self,
        order: Any,
        old_status: OrderStatus,
        new_status: OrderStatus,
        user_id: Optional[UUID],
        reason: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> None:
        """Record status change in order history.

        Args:
            order: Order instance
            old_status: Previous status
            new_status: New status
            user_id: User who initiated change
            reason: Reason for change
            metadata: Additional metadata
        """
        from src.database.models.order import OrderStatusHistory

        history_entry = OrderStatusHistory(
            order_id=order.id,
            old_status=old_status,
            new_status=new_status,
            changed_by=user_id,
            reason=reason,
            metadata=metadata or {},
            created_at=datetime.utcnow()
        )

        self.db.add(history_entry)

        logger.debug(
            "Status change recorded",
            order_id=str(order.id),
            old_status=old_status.value,
            new_status=new_status.value
        )

    # Transition Guards

    def _guard_payment_processing(self, order: Any) -> bool:
        """Guard for payment processing transition.

        Args:
            order: Order instance

        Returns:
            True if payment can be processed
        """
        has_payment_method = bool(order.payment_method)
        has_valid_amount = order.total_amount > 0

        logger.debug(
            "Payment processing guard check",
            order_id=str(order.id),
            has_payment_method=has_payment_method,
            has_valid_amount=has_valid_amount
        )

        return has_payment_method and has_valid_amount

    def _guard_payment_confirmed(self, order: Any) -> bool:
        """Guard for payment confirmation transition.

        Args:
            order: Order instance

        Returns:
            True if payment is confirmed
        """
        payment_successful = (
            order.payment_status == PaymentStatus.CAPTURED
        )

        logger.debug(
            "Payment confirmation guard check",
            order_id=str(order.id),
            payment_status=order.payment_status.value,
            payment_successful=payment_successful
        )

        return payment_successful

    def _guard_production_start(self, order: Any) -> bool:
        """Guard for production start transition.

        Args:
            order: Order instance

        Returns:
            True if production can start
        """
        has_inventory = all(
            item.inventory_reserved for item in order.items
        )
        payment_confirmed = order.payment_status == PaymentStatus.CAPTURED

        logger.debug(
            "Production start guard check",
            order_id=str(order.id),
            has_inventory=has_inventory,
            payment_confirmed=payment_confirmed
        )

        return has_inventory and payment_confirmed

    def _guard_quality_passed(self, order: Any) -> bool:
        """Guard for quality check passed transition.

        Args:
            order: Order instance

        Returns:
            True if quality check passed
        """
        quality_approved = order.quality_check_status == "approved"

        logger.debug(
            "Quality check guard",
            order_id=str(order.id),
            quality_approved=quality_approved
        )

        return quality_approved

    def _guard_delivery_confirmed(self, order: Any) -> bool:
        """Guard for delivery confirmation transition.

        Args:
            order: Order instance

        Returns:
            True if delivery can be confirmed
        """
        has_delivery_confirmation = bool(order.delivery_confirmation)
        signature_received = bool(order.delivery_signature)

        logger.debug(
            "Delivery confirmation guard",
            order_id=str(order.id),
            has_confirmation=has_delivery_confirmation,
            has_signature=signature_received
        )

        return has_delivery_confirmation or signature_received

    def _guard_refund_eligible(self, order: Any) -> bool:
        """Guard for refund eligibility check.

        Args:
            order: Order instance

        Returns:
            True if refund is eligible
        """
        if not order.delivered_at:
            return False

        days_since_delivery = (
            datetime.utcnow() - order.delivered_at
        ).days
        within_return_window = days_since_delivery <= 30

        logger.debug(
            "Refund eligibility guard",
            order_id=str(order.id),
            days_since_delivery=days_since_delivery,
            within_return_window=within_return_window
        )

        return within_return_window

    # Side Effects

    def _effect_payment_processing(self, order: Any) -> None:
        """Side effect for payment processing state.

        Args:
            order: Order instance
        """
        logger.info(
            "Payment processing initiated",
            order_id=str(order.id),
            amount=order.total_amount
        )
        # Trigger payment service integration
        # This would call payment service to process payment

    def _effect_order_confirmed(self, order: Any) -> None:
        """Side effect for order confirmation state.

        Args:
            order: Order instance
        """
        order.confirmed_at = datetime.utcnow()

        logger.info(
            "Order confirmed",
            order_id=str(order.id),
            confirmed_at=order.confirmed_at.isoformat()
        )
        # Send confirmation email
        # Reserve inventory
        # Notify fulfillment system

    def _effect_production_started(self, order: Any) -> None:
        """Side effect for production start state.

        Args:
            order: Order instance
        """
        order.production_started_at = datetime.utcnow()

        logger.info(
            "Production started",
            order_id=str(order.id),
            started_at=order.production_started_at.isoformat()
        )
        # Notify production system
        # Update estimated completion date

    def _effect_quality_check(self, order: Any) -> None:
        """Side effect for quality check state.

        Args:
            order: Order instance
        """
        order.quality_check_at = datetime.utcnow()

        logger.info(
            "Quality check initiated",
            order_id=str(order.id),
            check_at=order.quality_check_at.isoformat()
        )
        # Trigger quality inspection workflow

    def _effect_shipment_started(self, order: Any) -> None:
        """Side effect for shipment start state.

        Args:
            order: Order instance
        """
        order.shipped_at = datetime.utcnow()
        order.fulfillment_status = FulfillmentStatus.IN_TRANSIT

        logger.info(
            "Shipment started",
            order_id=str(order.id),
            shipped_at=order.shipped_at.isoformat()
        )
        # Generate tracking number
        # Send shipping notification
        # Update carrier system

    def _effect_out_for_delivery(self, order: Any) -> None:
        """Side effect for out for delivery state.

        Args:
            order: Order instance
        """
        order.out_for_delivery_at = datetime.utcnow()
        order.fulfillment_status = FulfillmentStatus.OUT_FOR_DELIVERY

        logger.info(
            "Out for delivery",
            order_id=str(order.id),
            out_for_delivery_at=order.out_for_delivery_at.isoformat()
        )
        # Send delivery notification
        # Update estimated delivery time

    def _effect_delivered(self, order: Any) -> None:
        """Side effect for delivered state.

        Args:
            order: Order instance
        """
        order.delivered_at = datetime.utcnow()
        order.fulfillment_status = FulfillmentStatus.DELIVERED

        logger.info(
            "Order delivered",
            order_id=str(order.id),
            delivered_at=order.delivered_at.isoformat()
        )
        # Send delivery confirmation
        # Request feedback
        # Release inventory reservation

    def _effect_cancelled(self, order: Any) -> None:
        """Side effect for cancelled state.

        Args:
            order: Order instance
        """
        order.cancelled_at = datetime.utcnow()
        order.fulfillment_status = FulfillmentStatus.CANCELLED

        logger.info(
            "Order cancelled",
            order_id=str(order.id),
            cancelled_at=order.cancelled_at.isoformat()
        )
        # Release inventory
        # Process refund if payment captured
        # Send cancellation notification

    def _effect_refunded(self, order: Any) -> None:
        """Side effect for refunded state.

        Args:
            order: Order instance
        """
        order.refunded_at = datetime.utcnow()
        order.payment_status = PaymentStatus.REFUNDED

        logger.info(
            "Order refunded",
            order_id=str(order.id),
            refunded_at=order.refunded_at.isoformat()
        )
        # Process refund through payment service
        # Send refund confirmation
        # Update inventory


def get_order_state_machine(db_session: Session) -> OrderStateMachine:
    """Factory function to create OrderStateMachine instance.

    Args:
        db_session: SQLAlchemy database session

    Returns:
        OrderStateMachine instance
    """
    return OrderStateMachine(db_session)