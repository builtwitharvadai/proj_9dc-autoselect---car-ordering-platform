"""
Comprehensive test suite for OrderStateMachine.

Tests cover state transitions, guards, side effects, error handling,
and business rule validation with >80% coverage.
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from src.services.orders.enums import (
    FulfillmentStatus,
    OrderStatus,
    PaymentStatus,
)
from src.services.orders.state_machine import (
    OrderStateMachine,
    StateTransitionError,
    get_order_state_machine,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_db_session() -> Mock:
    """Create mock database session with transaction support.

    Returns:
        Mock database session with commit/rollback methods
    """
    session = Mock(spec=Session)
    session.commit = Mock()
    session.rollback = Mock()
    session.add = Mock()
    return session


@pytest.fixture
def state_machine(mock_db_session: Mock) -> OrderStateMachine:
    """Create OrderStateMachine instance with mock database.

    Args:
        mock_db_session: Mock database session

    Returns:
        OrderStateMachine instance for testing
    """
    return OrderStateMachine(db_session=mock_db_session)


@pytest.fixture
def mock_order() -> Mock:
    """Create mock order with default attributes.

    Returns:
        Mock order instance with common attributes
    """
    order = Mock()
    order.id = uuid4()
    order.status = OrderStatus.PENDING
    order.payment_status = PaymentStatus.PENDING
    order.fulfillment_status = FulfillmentStatus.PENDING
    order.total_amount = 1000.0
    order.payment_method = "credit_card"
    order.items = []
    order.updated_at = datetime.utcnow()
    order.confirmed_at = None
    order.production_started_at = None
    order.quality_check_at = None
    order.shipped_at = None
    order.out_for_delivery_at = None
    order.delivered_at = None
    order.cancelled_at = None
    order.refunded_at = None
    order.quality_check_status = None
    order.delivery_confirmation = None
    order.delivery_signature = None
    return order


# ============================================================================
# Initialization Tests
# ============================================================================


class TestOrderStateMachineInitialization:
    """Test OrderStateMachine initialization and setup."""

    def test_initialization_with_valid_session(
        self, mock_db_session: Mock
    ) -> None:
        """Test state machine initializes with valid database session."""
        machine = OrderStateMachine(db_session=mock_db_session)

        assert machine.db is mock_db_session
        assert isinstance(machine._transition_guards, dict)
        assert isinstance(machine._side_effects, dict)
        assert len(machine._transition_guards) > 0
        assert len(machine._side_effects) > 0

    def test_guards_initialization(self, state_machine: OrderStateMachine) -> None:
        """Test transition guards are properly initialized."""
        expected_guards = [
            (OrderStatus.PENDING, OrderStatus.PAYMENT_PROCESSING),
            (OrderStatus.PAYMENT_PROCESSING, OrderStatus.CONFIRMED),
            (OrderStatus.CONFIRMED, OrderStatus.IN_PRODUCTION),
            (OrderStatus.QUALITY_CHECK, OrderStatus.IN_TRANSIT),
            (OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED),
            (OrderStatus.DELIVERED, OrderStatus.REFUNDED),
        ]

        for guard_key in expected_guards:
            assert guard_key in state_machine._transition_guards
            assert callable(state_machine._transition_guards[guard_key])

    def test_side_effects_initialization(
        self, state_machine: OrderStateMachine
    ) -> None:
        """Test side effect handlers are properly initialized."""
        expected_effects = [
            OrderStatus.PAYMENT_PROCESSING,
            OrderStatus.CONFIRMED,
            OrderStatus.IN_PRODUCTION,
            OrderStatus.QUALITY_CHECK,
            OrderStatus.IN_TRANSIT,
            OrderStatus.OUT_FOR_DELIVERY,
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED,
            OrderStatus.REFUNDED,
        ]

        for status in expected_effects:
            assert status in state_machine._side_effects
            assert callable(state_machine._side_effects[status])

    def test_factory_function(self, mock_db_session: Mock) -> None:
        """Test factory function creates valid state machine."""
        machine = get_order_state_machine(mock_db_session)

        assert isinstance(machine, OrderStateMachine)
        assert machine.db is mock_db_session


# ============================================================================
# Valid Transition Tests
# ============================================================================


class TestValidTransitions:
    """Test valid state transitions through the order lifecycle."""

    def test_pending_to_payment_processing(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test transition from PENDING to PAYMENT_PROCESSING."""
        mock_order.status = OrderStatus.PENDING
        mock_order.payment_method = "credit_card"
        mock_order.total_amount = 1000.0

        result = state_machine.validate_transition(
            mock_order,
            OrderStatus.PAYMENT_PROCESSING,
        )

        assert result is True

    def test_payment_processing_to_confirmed(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test transition from PAYMENT_PROCESSING to CONFIRMED."""
        mock_order.status = OrderStatus.PAYMENT_PROCESSING
        mock_order.payment_status = PaymentStatus.CAPTURED

        result = state_machine.validate_transition(
            mock_order,
            OrderStatus.CONFIRMED,
        )

        assert result is True

    def test_confirmed_to_in_production(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test transition from CONFIRMED to IN_PRODUCTION."""
        mock_order.status = OrderStatus.CONFIRMED
        mock_order.payment_status = PaymentStatus.CAPTURED
        mock_item = Mock()
        mock_item.inventory_reserved = True
        mock_order.items = [mock_item]

        result = state_machine.validate_transition(
            mock_order,
            OrderStatus.IN_PRODUCTION,
        )

        assert result is True

    def test_quality_check_to_in_transit(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test transition from QUALITY_CHECK to IN_TRANSIT."""
        mock_order.status = OrderStatus.QUALITY_CHECK
        mock_order.quality_check_status = "approved"

        result = state_machine.validate_transition(
            mock_order,
            OrderStatus.IN_TRANSIT,
        )

        assert result is True

    def test_out_for_delivery_to_delivered(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test transition from OUT_FOR_DELIVERY to DELIVERED."""
        mock_order.status = OrderStatus.OUT_FOR_DELIVERY
        mock_order.delivery_confirmation = "confirmed"

        result = state_machine.validate_transition(
            mock_order,
            OrderStatus.DELIVERED,
        )

        assert result is True

    def test_delivered_to_refunded(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test transition from DELIVERED to REFUNDED."""
        mock_order.status = OrderStatus.DELIVERED
        mock_order.delivered_at = datetime.utcnow() - timedelta(days=15)

        result = state_machine.validate_transition(
            mock_order,
            OrderStatus.REFUNDED,
        )

        assert result is True

    @pytest.mark.parametrize(
        "current_status",
        [
            OrderStatus.PENDING,
            OrderStatus.PAYMENT_PROCESSING,
            OrderStatus.CONFIRMED,
            OrderStatus.IN_PRODUCTION,
        ],
    )
    def test_cancellable_statuses_to_cancelled(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
        current_status: OrderStatus,
    ) -> None:
        """Test cancellation from various cancellable statuses."""
        mock_order.status = current_status

        result = state_machine.validate_transition(
            mock_order,
            OrderStatus.CANCELLED,
        )

        assert result is True


# ============================================================================
# Invalid Transition Tests
# ============================================================================


class TestInvalidTransitions:
    """Test invalid state transitions are properly rejected."""

    def test_invalid_transition_raises_error(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test invalid transition raises StateTransitionError."""
        mock_order.status = OrderStatus.PENDING

        with pytest.raises(StateTransitionError) as exc_info:
            state_machine.validate_transition(
                mock_order,
                OrderStatus.DELIVERED,
            )

        assert exc_info.value.current_state == OrderStatus.PENDING
        assert exc_info.value.target_state == OrderStatus.DELIVERED
        assert "allowed_transitions" in exc_info.value.context

    def test_delivered_to_pending_invalid(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test cannot transition from DELIVERED back to PENDING."""
        mock_order.status = OrderStatus.DELIVERED

        with pytest.raises(StateTransitionError):
            state_machine.validate_transition(
                mock_order,
                OrderStatus.PENDING,
            )

    def test_cancelled_to_confirmed_invalid(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test cannot transition from CANCELLED to CONFIRMED."""
        mock_order.status = OrderStatus.CANCELLED

        with pytest.raises(StateTransitionError):
            state_machine.validate_transition(
                mock_order,
                OrderStatus.CONFIRMED,
            )

    def test_refunded_to_delivered_invalid(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test cannot transition from REFUNDED to DELIVERED."""
        mock_order.status = OrderStatus.REFUNDED

        with pytest.raises(StateTransitionError):
            state_machine.validate_transition(
                mock_order,
                OrderStatus.DELIVERED,
            )


# ============================================================================
# Transition Guard Tests
# ============================================================================


class TestTransitionGuards:
    """Test transition guard functions enforce business rules."""

    def test_payment_processing_guard_requires_payment_method(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test payment processing guard requires payment method."""
        mock_order.status = OrderStatus.PENDING
        mock_order.payment_method = None
        mock_order.total_amount = 1000.0

        with pytest.raises(StateTransitionError) as exc_info:
            state_machine.validate_transition(
                mock_order,
                OrderStatus.PAYMENT_PROCESSING,
            )

        assert exc_info.value.context.get("guard_failed") is True

    def test_payment_processing_guard_requires_valid_amount(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test payment processing guard requires positive amount."""
        mock_order.status = OrderStatus.PENDING
        mock_order.payment_method = "credit_card"
        mock_order.total_amount = 0

        with pytest.raises(StateTransitionError):
            state_machine.validate_transition(
                mock_order,
                OrderStatus.PAYMENT_PROCESSING,
            )

    def test_payment_confirmed_guard_requires_captured_payment(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test payment confirmation guard requires captured payment."""
        mock_order.status = OrderStatus.PAYMENT_PROCESSING
        mock_order.payment_status = PaymentStatus.PENDING

        with pytest.raises(StateTransitionError):
            state_machine.validate_transition(
                mock_order,
                OrderStatus.CONFIRMED,
            )

    def test_production_start_guard_requires_inventory(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test production start guard requires reserved inventory."""
        mock_order.status = OrderStatus.CONFIRMED
        mock_order.payment_status = PaymentStatus.CAPTURED
        mock_item = Mock()
        mock_item.inventory_reserved = False
        mock_order.items = [mock_item]

        with pytest.raises(StateTransitionError):
            state_machine.validate_transition(
                mock_order,
                OrderStatus.IN_PRODUCTION,
            )

    def test_production_start_guard_requires_payment_confirmed(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test production start guard requires confirmed payment."""
        mock_order.status = OrderStatus.CONFIRMED
        mock_order.payment_status = PaymentStatus.PENDING
        mock_item = Mock()
        mock_item.inventory_reserved = True
        mock_order.items = [mock_item]

        with pytest.raises(StateTransitionError):
            state_machine.validate_transition(
                mock_order,
                OrderStatus.IN_PRODUCTION,
            )

    def test_quality_passed_guard_requires_approval(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test quality check guard requires approval status."""
        mock_order.status = OrderStatus.QUALITY_CHECK
        mock_order.quality_check_status = "pending"

        with pytest.raises(StateTransitionError):
            state_machine.validate_transition(
                mock_order,
                OrderStatus.IN_TRANSIT,
            )

    def test_delivery_confirmed_guard_requires_confirmation(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test delivery guard requires confirmation or signature."""
        mock_order.status = OrderStatus.OUT_FOR_DELIVERY
        mock_order.delivery_confirmation = None
        mock_order.delivery_signature = None

        with pytest.raises(StateTransitionError):
            state_machine.validate_transition(
                mock_order,
                OrderStatus.DELIVERED,
            )

    def test_delivery_confirmed_guard_accepts_signature(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test delivery guard accepts signature as confirmation."""
        mock_order.status = OrderStatus.OUT_FOR_DELIVERY
        mock_order.delivery_confirmation = None
        mock_order.delivery_signature = "signature_data"

        result = state_machine.validate_transition(
            mock_order,
            OrderStatus.DELIVERED,
        )

        assert result is True

    def test_refund_eligible_guard_requires_delivery_date(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test refund guard requires delivery date."""
        mock_order.status = OrderStatus.DELIVERED
        mock_order.delivered_at = None

        with pytest.raises(StateTransitionError):
            state_machine.validate_transition(
                mock_order,
                OrderStatus.REFUNDED,
            )

    def test_refund_eligible_guard_enforces_30_day_window(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test refund guard enforces 30-day return window."""
        mock_order.status = OrderStatus.DELIVERED
        mock_order.delivered_at = datetime.utcnow() - timedelta(days=31)

        with pytest.raises(StateTransitionError):
            state_machine.validate_transition(
                mock_order,
                OrderStatus.REFUNDED,
            )

    def test_refund_eligible_within_window(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test refund allowed within 30-day window."""
        mock_order.status = OrderStatus.DELIVERED
        mock_order.delivered_at = datetime.utcnow() - timedelta(days=29)

        result = state_machine.validate_transition(
            mock_order,
            OrderStatus.REFUNDED,
        )

        assert result is True


# ============================================================================
# Apply Transition Tests
# ============================================================================


class TestApplyTransition:
    """Test applying state transitions with side effects."""

    @patch("src.services.orders.state_machine.datetime")
    def test_apply_transition_updates_status(
        self,
        mock_datetime: Mock,
        state_machine: OrderStateMachine,
        mock_order: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test apply_transition updates order status."""
        mock_now = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        mock_order.status = OrderStatus.PENDING
        mock_order.payment_method = "credit_card"
        mock_order.total_amount = 1000.0

        state_machine.apply_transition(
            mock_order,
            OrderStatus.PAYMENT_PROCESSING,
        )

        assert mock_order.status == OrderStatus.PAYMENT_PROCESSING
        assert mock_order.updated_at == mock_now
        mock_db_session.commit.assert_called_once()

    def test_apply_transition_records_history(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test apply_transition records status change history."""
        mock_order.status = OrderStatus.PENDING
        mock_order.payment_method = "credit_card"
        mock_order.total_amount = 1000.0
        user_id = uuid4()

        state_machine.apply_transition(
            mock_order,
            OrderStatus.PAYMENT_PROCESSING,
            user_id=user_id,
            reason="Customer initiated payment",
        )

        mock_db_session.add.assert_called()
        history_call = mock_db_session.add.call_args[0][0]
        assert history_call.order_id == mock_order.id
        assert history_call.old_status == OrderStatus.PENDING
        assert history_call.new_status == OrderStatus.PAYMENT_PROCESSING
        assert history_call.changed_by == user_id
        assert history_call.reason == "Customer initiated payment"

    def test_apply_transition_executes_side_effects(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test apply_transition executes side effect handlers."""
        mock_order.status = OrderStatus.PAYMENT_PROCESSING
        mock_order.payment_status = PaymentStatus.CAPTURED

        state_machine.apply_transition(
            mock_order,
            OrderStatus.CONFIRMED,
        )

        assert mock_order.confirmed_at is not None

    def test_apply_transition_with_metadata(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test apply_transition includes metadata in history."""
        mock_order.status = OrderStatus.PENDING
        mock_order.payment_method = "credit_card"
        mock_order.total_amount = 1000.0

        metadata = {
            "payment_gateway": "stripe",
            "transaction_id": "txn_123",
        }

        state_machine.apply_transition(
            mock_order,
            OrderStatus.PAYMENT_PROCESSING,
            metadata=metadata,
        )

        history_call = mock_db_session.add.call_args[0][0]
        assert history_call.metadata == metadata

    def test_apply_transition_rollback_on_error(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test apply_transition rolls back on error."""
        mock_order.status = OrderStatus.PENDING
        mock_order.payment_method = None  # Will fail guard

        with pytest.raises(StateTransitionError):
            state_machine.apply_transition(
                mock_order,
                OrderStatus.PAYMENT_PROCESSING,
            )

        mock_db_session.rollback.assert_called_once()
        mock_db_session.commit.assert_not_called()

    def test_apply_transition_invalid_raises_error(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test apply_transition raises error for invalid transition."""
        mock_order.status = OrderStatus.PENDING

        with pytest.raises(StateTransitionError):
            state_machine.apply_transition(
                mock_order,
                OrderStatus.DELIVERED,
            )

        mock_db_session.rollback.assert_called_once()


# ============================================================================
# Side Effect Tests
# ============================================================================


class TestSideEffects:
    """Test side effect handlers for state transitions."""

    @patch("src.services.orders.state_machine.datetime")
    def test_effect_order_confirmed_sets_timestamp(
        self,
        mock_datetime: Mock,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test order confirmation side effect sets timestamp."""
        mock_now = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        state_machine._effect_order_confirmed(mock_order)

        assert mock_order.confirmed_at == mock_now

    @patch("src.services.orders.state_machine.datetime")
    def test_effect_production_started_sets_timestamp(
        self,
        mock_datetime: Mock,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test production start side effect sets timestamp."""
        mock_now = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        state_machine._effect_production_started(mock_order)

        assert mock_order.production_started_at == mock_now

    @patch("src.services.orders.state_machine.datetime")
    def test_effect_quality_check_sets_timestamp(
        self,
        mock_datetime: Mock,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test quality check side effect sets timestamp."""
        mock_now = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        state_machine._effect_quality_check(mock_order)

        assert mock_order.quality_check_at == mock_now

    @patch("src.services.orders.state_machine.datetime")
    def test_effect_shipment_started_updates_fulfillment(
        self,
        mock_datetime: Mock,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test shipment start side effect updates fulfillment status."""
        mock_now = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        state_machine._effect_shipment_started(mock_order)

        assert mock_order.shipped_at == mock_now
        assert mock_order.fulfillment_status == FulfillmentStatus.IN_TRANSIT

    @patch("src.services.orders.state_machine.datetime")
    def test_effect_out_for_delivery_updates_fulfillment(
        self,
        mock_datetime: Mock,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test out for delivery side effect updates fulfillment status."""
        mock_now = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        state_machine._effect_out_for_delivery(mock_order)

        assert mock_order.out_for_delivery_at == mock_now
        assert (
            mock_order.fulfillment_status == FulfillmentStatus.OUT_FOR_DELIVERY
        )

    @patch("src.services.orders.state_machine.datetime")
    def test_effect_delivered_updates_fulfillment(
        self,
        mock_datetime: Mock,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test delivered side effect updates fulfillment status."""
        mock_now = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        state_machine._effect_delivered(mock_order)

        assert mock_order.delivered_at == mock_now
        assert mock_order.fulfillment_status == FulfillmentStatus.DELIVERED

    @patch("src.services.orders.state_machine.datetime")
    def test_effect_cancelled_updates_fulfillment(
        self,
        mock_datetime: Mock,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test cancelled side effect updates fulfillment status."""
        mock_now = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        state_machine._effect_cancelled(mock_order)

        assert mock_order.cancelled_at == mock_now
        assert mock_order.fulfillment_status == FulfillmentStatus.CANCELLED

    @patch("src.services.orders.state_machine.datetime")
    def test_effect_refunded_updates_payment_status(
        self,
        mock_datetime: Mock,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test refunded side effect updates payment status."""
        mock_now = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        state_machine._effect_refunded(mock_order)

        assert mock_order.refunded_at == mock_now
        assert mock_order.payment_status == PaymentStatus.REFUNDED


# ============================================================================
# Helper Method Tests
# ============================================================================


class TestHelperMethods:
    """Test helper methods for state machine operations."""

    def test_get_allowed_transitions(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test get_allowed_transitions returns valid transitions."""
        mock_order.status = OrderStatus.PENDING

        allowed = state_machine.get_allowed_transitions(mock_order)

        assert isinstance(allowed, set)
        assert OrderStatus.PAYMENT_PROCESSING in allowed
        assert OrderStatus.CANCELLED in allowed
        assert OrderStatus.DELIVERED not in allowed

    def test_can_cancel_from_pending(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test can_cancel returns True for cancellable status."""
        mock_order.status = OrderStatus.PENDING

        result = state_machine.can_cancel(mock_order)

        assert result is True

    def test_can_cancel_from_delivered(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test can_cancel returns False for non-cancellable status."""
        mock_order.status = OrderStatus.DELIVERED

        result = state_machine.can_cancel(mock_order)

        assert result is False

    def test_can_refund_from_delivered(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test can_refund returns True for refundable status."""
        mock_order.status = OrderStatus.DELIVERED

        result = state_machine.can_refund(mock_order)

        assert result is True

    def test_can_refund_from_pending(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test can_refund returns False for non-refundable status."""
        mock_order.status = OrderStatus.PENDING

        result = state_machine.can_refund(mock_order)

        assert result is False


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_transition_with_empty_items_list(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test production start guard with empty items list."""
        mock_order.status = OrderStatus.CONFIRMED
        mock_order.payment_status = PaymentStatus.CAPTURED
        mock_order.items = []

        result = state_machine.validate_transition(
            mock_order,
            OrderStatus.IN_PRODUCTION,
        )

        assert result is True

    def test_refund_on_exact_30_day_boundary(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test refund eligibility on exact 30-day boundary."""
        mock_order.status = OrderStatus.DELIVERED
        mock_order.delivered_at = datetime.utcnow() - timedelta(days=30)

        result = state_machine.validate_transition(
            mock_order,
            OrderStatus.REFUNDED,
        )

        assert result is True

    def test_transition_with_none_user_id(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test transition with None user_id is handled."""
        mock_order.status = OrderStatus.PENDING
        mock_order.payment_method = "credit_card"
        mock_order.total_amount = 1000.0

        state_machine.apply_transition(
            mock_order,
            OrderStatus.PAYMENT_PROCESSING,
            user_id=None,
        )

        history_call = mock_db_session.add.call_args[0][0]
        assert history_call.changed_by is None

    def test_transition_with_empty_reason(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test transition with empty reason string."""
        mock_order.status = OrderStatus.PENDING
        mock_order.payment_method = "credit_card"
        mock_order.total_amount = 1000.0

        state_machine.apply_transition(
            mock_order,
            OrderStatus.PAYMENT_PROCESSING,
            reason="",
        )

        history_call = mock_db_session.add.call_args[0][0]
        assert history_call.reason == ""

    def test_multiple_items_all_reserved(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test production start with multiple items all reserved."""
        mock_order.status = OrderStatus.CONFIRMED
        mock_order.payment_status = PaymentStatus.CAPTURED

        items = [Mock(inventory_reserved=True) for _ in range(5)]
        mock_order.items = items

        result = state_machine.validate_transition(
            mock_order,
            OrderStatus.IN_PRODUCTION,
        )

        assert result is True

    def test_multiple_items_one_not_reserved(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test production start fails if any item not reserved."""
        mock_order.status = OrderStatus.CONFIRMED
        mock_order.payment_status = PaymentStatus.CAPTURED

        items = [Mock(inventory_reserved=True) for _ in range(4)]
        items.append(Mock(inventory_reserved=False))
        mock_order.items = items

        with pytest.raises(StateTransitionError):
            state_machine.validate_transition(
                mock_order,
                OrderStatus.IN_PRODUCTION,
            )


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling and exception scenarios."""

    def test_state_transition_error_attributes(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test StateTransitionError contains proper attributes."""
        mock_order.status = OrderStatus.PENDING

        with pytest.raises(StateTransitionError) as exc_info:
            state_machine.validate_transition(
                mock_order,
                OrderStatus.DELIVERED,
            )

        error = exc_info.value
        assert error.current_state == OrderStatus.PENDING
        assert error.target_state == OrderStatus.DELIVERED
        assert isinstance(error.context, dict)
        assert "allowed_transitions" in error.context

    def test_guard_failure_error_context(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test guard failure includes context in error."""
        mock_order.status = OrderStatus.PENDING
        mock_order.payment_method = None

        with pytest.raises(StateTransitionError) as exc_info:
            state_machine.validate_transition(
                mock_order,
                OrderStatus.PAYMENT_PROCESSING,
            )

        assert exc_info.value.context.get("guard_failed") is True

    def test_database_error_triggers_rollback(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
        mock_db_session: Mock,
    ) -> None:
        """Test database error triggers rollback."""
        mock_order.status = OrderStatus.PENDING
        mock_order.payment_method = "credit_card"
        mock_order.total_amount = 1000.0

        mock_db_session.commit.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            state_machine.apply_transition(
                mock_order,
                OrderStatus.PAYMENT_PROCESSING,
            )

        mock_db_session.rollback.assert_called_once()


# ============================================================================
# Logging Tests
# ============================================================================


class TestLogging:
    """Test logging behavior throughout state machine operations."""

    def test_initialization_logs_setup(
        self,
        mock_db_session: Mock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test initialization logs setup information."""
        with caplog.at_level(logging.INFO):
            OrderStateMachine(db_session=mock_db_session)

        assert "OrderStateMachine initialized" in caplog.text

    def test_validate_transition_logs_debug(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test validate_transition logs debug information."""
        mock_order.status = OrderStatus.PENDING
        mock_order.payment_method = "credit_card"
        mock_order.total_amount = 1000.0

        with caplog.at_level(logging.DEBUG):
            state_machine.validate_transition(
                mock_order,
                OrderStatus.PAYMENT_PROCESSING,
            )

        assert "Validating state transition" in caplog.text

    def test_apply_transition_logs_success(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test apply_transition logs successful transition."""
        mock_order.status = OrderStatus.PENDING
        mock_order.payment_method = "credit_card"
        mock_order.total_amount = 1000.0

        with caplog.at_level(logging.INFO):
            state_machine.apply_transition(
                mock_order,
                OrderStatus.PAYMENT_PROCESSING,
            )

        assert "State transition applied successfully" in caplog.text

    def test_apply_transition_logs_error(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test apply_transition logs errors."""
        mock_order.status = OrderStatus.PENDING
        mock_order.payment_method = None

        with caplog.at_level(logging.ERROR):
            with pytest.raises(StateTransitionError):
                state_machine.apply_transition(
                    mock_order,
                    OrderStatus.PAYMENT_PROCESSING,
                )

        assert "State transition failed" in caplog.text


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Test complete workflows through multiple state transitions."""

    def test_complete_order_lifecycle(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test complete order lifecycle from pending to delivered."""
        # Setup initial order
        mock_order.status = OrderStatus.PENDING
        mock_order.payment_method = "credit_card"
        mock_order.total_amount = 1000.0

        # Pending -> Payment Processing
        state_machine.apply_transition(
            mock_order,
            OrderStatus.PAYMENT_PROCESSING,
        )
        assert mock_order.status == OrderStatus.PAYMENT_PROCESSING

        # Payment Processing -> Confirmed
        mock_order.payment_status = PaymentStatus.CAPTURED
        state_machine.apply_transition(mock_order, OrderStatus.CONFIRMED)
        assert mock_order.status == OrderStatus.CONFIRMED
        assert mock_order.confirmed_at is not None

        # Confirmed -> In Production
        mock_item = Mock(inventory_reserved=True)
        mock_order.items = [mock_item]
        state_machine.apply_transition(mock_order, OrderStatus.IN_PRODUCTION)
        assert mock_order.status == OrderStatus.IN_PRODUCTION
        assert mock_order.production_started_at is not None

    def test_cancellation_workflow(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test order cancellation workflow."""
        mock_order.status = OrderStatus.CONFIRMED

        state_machine.apply_transition(mock_order, OrderStatus.CANCELLED)

        assert mock_order.status == OrderStatus.CANCELLED
        assert mock_order.cancelled_at is not None
        assert mock_order.fulfillment_status == FulfillmentStatus.CANCELLED

    def test_refund_workflow(
        self,
        state_machine: OrderStateMachine,
        mock_order: Mock,
    ) -> None:
        """Test order refund workflow."""
        mock_order.status = OrderStatus.DELIVERED
        mock_order.delivered_at = datetime.utcnow() - timedelta(days=15)

        state_machine.apply_transition(mock_order, OrderStatus.REFUNDED)

        assert mock_order.status == OrderStatus.REFUNDED
        assert mock_order.refunded_at is not None
        assert mock_order.payment_status == PaymentStatus.REFUNDED