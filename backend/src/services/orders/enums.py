"""Order status and state machine enums for order lifecycle management.

This module defines the core enums for order management including order status,
payment status, and fulfillment status with comprehensive state transition
validation rules.
"""

from enum import Enum
from typing import Set, Dict, Optional


class OrderStatus(str, Enum):
    """Order lifecycle status with state machine transitions.
    
    Valid transitions:
    - PENDING -> PAYMENT_PROCESSING, CANCELLED
    - PAYMENT_PROCESSING -> CONFIRMED, CANCELLED
    - CONFIRMED -> IN_PRODUCTION, CANCELLED
    - IN_PRODUCTION -> QUALITY_CHECK
    - QUALITY_CHECK -> IN_TRANSIT, IN_PRODUCTION (rework)
    - IN_TRANSIT -> OUT_FOR_DELIVERY
    - OUT_FOR_DELIVERY -> DELIVERED, IN_TRANSIT (failed delivery)
    - DELIVERED -> REFUNDED (within return window)
    - CANCELLED -> (terminal state)
    - REFUNDED -> (terminal state)
    """
    
    PENDING = "pending"
    PAYMENT_PROCESSING = "payment_processing"
    CONFIRMED = "confirmed"
    IN_PRODUCTION = "in_production"
    QUALITY_CHECK = "quality_check"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    
    @classmethod
    def from_string(cls, value: str) -> "OrderStatus":
        """Convert string to OrderStatus enum.
        
        Args:
            value: String representation of status
            
        Returns:
            OrderStatus enum value
            
        Raises:
            ValueError: If value is not a valid status
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_values = ", ".join([s.value for s in cls])
            raise ValueError(
                f"Invalid order status: {value}. "
                f"Valid values are: {valid_values}"
            )
    
    def is_terminal(self) -> bool:
        """Check if status is a terminal state.
        
        Returns:
            True if status is terminal (DELIVERED, CANCELLED, REFUNDED)
        """
        return self in {
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED,
            OrderStatus.REFUNDED
        }
    
    def is_active(self) -> bool:
        """Check if order is in an active processing state.
        
        Returns:
            True if order is being actively processed
        """
        return self in {
            OrderStatus.PAYMENT_PROCESSING,
            OrderStatus.CONFIRMED,
            OrderStatus.IN_PRODUCTION,
            OrderStatus.QUALITY_CHECK,
            OrderStatus.IN_TRANSIT,
            OrderStatus.OUT_FOR_DELIVERY
        }
    
    def can_cancel(self) -> bool:
        """Check if order can be cancelled from current status.
        
        Returns:
            True if cancellation is allowed
        """
        return self in {
            OrderStatus.PENDING,
            OrderStatus.PAYMENT_PROCESSING,
            OrderStatus.CONFIRMED
        }
    
    def can_refund(self) -> bool:
        """Check if order can be refunded from current status.
        
        Returns:
            True if refund is allowed
        """
        return self == OrderStatus.DELIVERED
    
    @property
    def display_name(self) -> str:
        """Get human-readable display name for status.
        
        Returns:
            Formatted display name
        """
        return self.value.replace("_", " ").title()


class PaymentStatus(str, Enum):
    """Payment processing status for order transactions.
    
    Valid transitions:
    - PENDING -> PROCESSING, FAILED, CANCELLED
    - PROCESSING -> AUTHORIZED, FAILED
    - AUTHORIZED -> CAPTURED, CANCELLED
    - CAPTURED -> REFUNDED, PARTIALLY_REFUNDED
    - PARTIALLY_REFUNDED -> REFUNDED
    - FAILED -> (terminal state)
    - CANCELLED -> (terminal state)
    - REFUNDED -> (terminal state)
    """
    
    PENDING = "pending"
    PROCESSING = "processing"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
    @classmethod
    def from_string(cls, value: str) -> "PaymentStatus":
        """Convert string to PaymentStatus enum.
        
        Args:
            value: String representation of payment status
            
        Returns:
            PaymentStatus enum value
            
        Raises:
            ValueError: If value is not a valid payment status
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_values = ", ".join([s.value for s in cls])
            raise ValueError(
                f"Invalid payment status: {value}. "
                f"Valid values are: {valid_values}"
            )
    
    def is_successful(self) -> bool:
        """Check if payment was successful.
        
        Returns:
            True if payment is captured or refunded
        """
        return self in {
            PaymentStatus.CAPTURED,
            PaymentStatus.PARTIALLY_REFUNDED,
            PaymentStatus.REFUNDED
        }
    
    def is_terminal(self) -> bool:
        """Check if payment status is terminal.
        
        Returns:
            True if status is terminal
        """
        return self in {
            PaymentStatus.REFUNDED,
            PaymentStatus.FAILED,
            PaymentStatus.CANCELLED
        }
    
    def can_refund(self) -> bool:
        """Check if payment can be refunded.
        
        Returns:
            True if refund is possible
        """
        return self in {
            PaymentStatus.CAPTURED,
            PaymentStatus.PARTIALLY_REFUNDED
        }
    
    @property
    def display_name(self) -> str:
        """Get human-readable display name for payment status.
        
        Returns:
            Formatted display name
        """
        return self.value.replace("_", " ").title()


class FulfillmentStatus(str, Enum):
    """Order fulfillment and delivery status.
    
    Valid transitions:
    - PENDING -> PROCESSING, CANCELLED
    - PROCESSING -> READY_FOR_SHIPMENT, ON_HOLD
    - ON_HOLD -> PROCESSING, CANCELLED
    - READY_FOR_SHIPMENT -> SHIPPED
    - SHIPPED -> IN_TRANSIT
    - IN_TRANSIT -> OUT_FOR_DELIVERY, DELAYED
    - DELAYED -> IN_TRANSIT, RETURNED
    - OUT_FOR_DELIVERY -> DELIVERED, DELIVERY_FAILED
    - DELIVERY_FAILED -> OUT_FOR_DELIVERY, RETURNED
    - DELIVERED -> RETURNED (within return window)
    - RETURNED -> (terminal state)
    - CANCELLED -> (terminal state)
    """
    
    PENDING = "pending"
    PROCESSING = "processing"
    ON_HOLD = "on_hold"
    READY_FOR_SHIPMENT = "ready_for_shipment"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    DELAYED = "delayed"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERY_FAILED = "delivery_failed"
    DELIVERED = "delivered"
    RETURNED = "returned"
    CANCELLED = "cancelled"
    
    @classmethod
    def from_string(cls, value: str) -> "FulfillmentStatus":
        """Convert string to FulfillmentStatus enum.
        
        Args:
            value: String representation of fulfillment status
            
        Returns:
            FulfillmentStatus enum value
            
        Raises:
            ValueError: If value is not a valid fulfillment status
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_values = ", ".join([s.value for s in cls])
            raise ValueError(
                f"Invalid fulfillment status: {value}. "
                f"Valid values are: {valid_values}"
            )
    
    def is_terminal(self) -> bool:
        """Check if fulfillment status is terminal.
        
        Returns:
            True if status is terminal
        """
        return self in {
            FulfillmentStatus.DELIVERED,
            FulfillmentStatus.RETURNED,
            FulfillmentStatus.CANCELLED
        }
    
    def is_in_transit(self) -> bool:
        """Check if order is currently in transit.
        
        Returns:
            True if order is being shipped or delivered
        """
        return self in {
            FulfillmentStatus.SHIPPED,
            FulfillmentStatus.IN_TRANSIT,
            FulfillmentStatus.OUT_FOR_DELIVERY
        }
    
    def can_cancel(self) -> bool:
        """Check if fulfillment can be cancelled.
        
        Returns:
            True if cancellation is allowed
        """
        return self in {
            FulfillmentStatus.PENDING,
            FulfillmentStatus.PROCESSING,
            FulfillmentStatus.ON_HOLD
        }
    
    @property
    def display_name(self) -> str:
        """Get human-readable display name for fulfillment status.
        
        Returns:
            Formatted display name
        """
        return self.value.replace("_", " ").title()


# State transition validation rules
ORDER_STATUS_TRANSITIONS: Dict[OrderStatus, Set[OrderStatus]] = {
    OrderStatus.PENDING: {
        OrderStatus.PAYMENT_PROCESSING,
        OrderStatus.CANCELLED
    },
    OrderStatus.PAYMENT_PROCESSING: {
        OrderStatus.CONFIRMED,
        OrderStatus.CANCELLED
    },
    OrderStatus.CONFIRMED: {
        OrderStatus.IN_PRODUCTION,
        OrderStatus.CANCELLED
    },
    OrderStatus.IN_PRODUCTION: {
        OrderStatus.QUALITY_CHECK
    },
    OrderStatus.QUALITY_CHECK: {
        OrderStatus.IN_TRANSIT,
        OrderStatus.IN_PRODUCTION  # Rework needed
    },
    OrderStatus.IN_TRANSIT: {
        OrderStatus.OUT_FOR_DELIVERY
    },
    OrderStatus.OUT_FOR_DELIVERY: {
        OrderStatus.DELIVERED,
        OrderStatus.IN_TRANSIT  # Failed delivery attempt
    },
    OrderStatus.DELIVERED: {
        OrderStatus.REFUNDED
    },
    OrderStatus.CANCELLED: set(),  # Terminal
    OrderStatus.REFUNDED: set()  # Terminal
}

PAYMENT_STATUS_TRANSITIONS: Dict[PaymentStatus, Set[PaymentStatus]] = {
    PaymentStatus.PENDING: {
        PaymentStatus.PROCESSING,
        PaymentStatus.FAILED,
        PaymentStatus.CANCELLED
    },
    PaymentStatus.PROCESSING: {
        PaymentStatus.AUTHORIZED,
        PaymentStatus.FAILED
    },
    PaymentStatus.AUTHORIZED: {
        PaymentStatus.CAPTURED,
        PaymentStatus.CANCELLED
    },
    PaymentStatus.CAPTURED: {
        PaymentStatus.REFUNDED,
        PaymentStatus.PARTIALLY_REFUNDED
    },
    PaymentStatus.PARTIALLY_REFUNDED: {
        PaymentStatus.REFUNDED
    },
    PaymentStatus.FAILED: set(),  # Terminal
    PaymentStatus.CANCELLED: set(),  # Terminal
    PaymentStatus.REFUNDED: set()  # Terminal
}

FULFILLMENT_STATUS_TRANSITIONS: Dict[FulfillmentStatus, Set[FulfillmentStatus]] = {
    FulfillmentStatus.PENDING: {
        FulfillmentStatus.PROCESSING,
        FulfillmentStatus.CANCELLED
    },
    FulfillmentStatus.PROCESSING: {
        FulfillmentStatus.READY_FOR_SHIPMENT,
        FulfillmentStatus.ON_HOLD
    },
    FulfillmentStatus.ON_HOLD: {
        FulfillmentStatus.PROCESSING,
        FulfillmentStatus.CANCELLED
    },
    FulfillmentStatus.READY_FOR_SHIPMENT: {
        FulfillmentStatus.SHIPPED
    },
    FulfillmentStatus.SHIPPED: {
        FulfillmentStatus.IN_TRANSIT
    },
    FulfillmentStatus.IN_TRANSIT: {
        FulfillmentStatus.OUT_FOR_DELIVERY,
        FulfillmentStatus.DELAYED
    },
    FulfillmentStatus.DELAYED: {
        FulfillmentStatus.IN_TRANSIT,
        FulfillmentStatus.RETURNED
    },
    FulfillmentStatus.OUT_FOR_DELIVERY: {
        FulfillmentStatus.DELIVERED,
        FulfillmentStatus.DELIVERY_FAILED
    },
    FulfillmentStatus.DELIVERY_FAILED: {
        FulfillmentStatus.OUT_FOR_DELIVERY,
        FulfillmentStatus.RETURNED
    },
    FulfillmentStatus.DELIVERED: {
        FulfillmentStatus.RETURNED
    },
    FulfillmentStatus.RETURNED: set(),  # Terminal
    FulfillmentStatus.CANCELLED: set()  # Terminal
}


def validate_order_status_transition(
    current: OrderStatus,
    new: OrderStatus
) -> bool:
    """Validate if order status transition is allowed.
    
    Args:
        current: Current order status
        new: Desired new status
        
    Returns:
        True if transition is valid
    """
    return new in ORDER_STATUS_TRANSITIONS.get(current, set())


def validate_payment_status_transition(
    current: PaymentStatus,
    new: PaymentStatus
) -> bool:
    """Validate if payment status transition is allowed.
    
    Args:
        current: Current payment status
        new: Desired new status
        
    Returns:
        True if transition is valid
    """
    return new in PAYMENT_STATUS_TRANSITIONS.get(current, set())


def validate_fulfillment_status_transition(
    current: FulfillmentStatus,
    new: FulfillmentStatus
) -> bool:
    """Validate if fulfillment status transition is allowed.
    
    Args:
        current: Current fulfillment status
        new: Desired new status
        
    Returns:
        True if transition is valid
    """
    return new in FULFILLMENT_STATUS_TRANSITIONS.get(current, set())


def get_allowed_order_transitions(
    current: OrderStatus
) -> Set[OrderStatus]:
    """Get all allowed transitions from current order status.
    
    Args:
        current: Current order status
        
    Returns:
        Set of allowed next statuses
    """
    return ORDER_STATUS_TRANSITIONS.get(current, set()).copy()


def get_allowed_payment_transitions(
    current: PaymentStatus
) -> Set[PaymentStatus]:
    """Get all allowed transitions from current payment status.
    
    Args:
        current: Current payment status
        
    Returns:
        Set of allowed next statuses
    """
    return PAYMENT_STATUS_TRANSITIONS.get(current, set()).copy()


def get_allowed_fulfillment_transitions(
    current: FulfillmentStatus
) -> Set[FulfillmentStatus]:
    """Get all allowed transitions from current fulfillment status.
    
    Args:
        current: Current fulfillment status
        
    Returns:
        Set of allowed next statuses
    """
    return FULFILLMENT_STATUS_TRANSITIONS.get(current, set()).copy()