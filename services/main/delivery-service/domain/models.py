import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


class DeliveryException(Exception):
    def __init__(self, message: str, code: str = "DELIVERY_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class DeliveryNotFound(DeliveryException):
    def __init__(self, delivery_id: str):
        super().__init__(f"Delivery {delivery_id} not found", "DELIVERY_NOT_FOUND", 404)


class DeliveryStatus:
    PENDING_ASSIGNMENT = "PENDING_ASSIGNMENT"
    ASSIGNED = "ASSIGNED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


@dataclass
class Delivery:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    deliverer_id: str = ""
    deliverer_name: str = ""
    customer_id: str = ""
    restaurant_id: str = ""
    status: str = DeliveryStatus.PENDING_ASSIGNMENT
    location: dict = field(default_factory=dict)
    assigned_at: str = ""
    picked_up_at: str = ""
    delivered_at: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
