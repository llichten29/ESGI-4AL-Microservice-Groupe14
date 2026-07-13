import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


class OrderException(Exception):
    def __init__(self, message: str, code: str = "ORDER_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class OrderNotFound(OrderException):
    def __init__(self, order_id: str):
        super().__init__(f"Order {order_id} not found", "ORDER_NOT_FOUND", 404)


class InvalidOrder(OrderException):
    def __init__(self, reason: str):
        super().__init__(reason, "INVALID_ORDER", 422)


class RestaurantUnavailable(OrderException):
    """Fallback raised when the restaurant-service circuit breaker is open."""
    def __init__(self, reason: str = "Restaurant service temporarily unavailable"):
        super().__init__(reason, "RESTAURANT_UNAVAILABLE", 503)


class CancellationNotAllowed(OrderException):
    def __init__(self, status: str):
        super().__init__(
            f"Order can no longer be cancelled (status {status})",
            "CANCELLATION_NOT_ALLOWED", 409
        )


class OrderStatus:
    CREATED = "CREATED"
    PAID = "PAID"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY = "READY"
    ASSIGNED = "ASSIGNED"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class SagaState:
    """States of the order placement SAGA (see documentation/07-SAGA_PATTERN.md)."""
    STARTED = "STARTED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    AWAITING_ACCEPTANCE = "AWAITING_ACCEPTANCE"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    READY_FOR_DELIVERY = "READY_FOR_DELIVERY"
    DELIVERY_ASSIGNED = "DELIVERY_ASSIGNED"
    DELIVERING = "DELIVERING"
    COMPLETED = "COMPLETED"
    COMPENSATED = "COMPENSATED"
    FAILED = "FAILED"


@dataclass
class OrderItem:
    dish_id: str = ""
    name: str = ""
    quantity: int = 1
    unit_price: float = 0.0

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price


@dataclass
class SagaStep:
    state: str = ""
    detail: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Order:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str = ""
    restaurant_id: str = ""
    restaurant_name: str = ""
    items: list[OrderItem] = field(default_factory=list)
    delivery_fee: float = 0.0
    total_price: float = 0.0
    delivery_address: dict = field(default_factory=dict)
    payment: dict = field(default_factory=dict)
    status: str = OrderStatus.CREATED
    saga_state: str = SagaState.STARTED
    saga_history: list[SagaStep] = field(default_factory=list)
    payment_id: str = ""
    delivery_id: str = ""
    cancellation_reason: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def advance_saga(self, state: str, detail: str = ""):
        self.saga_state = state
        self.saga_history.append(SagaStep(state=state, detail=detail))
        self.updated_at = datetime.now(timezone.utc).isoformat()
