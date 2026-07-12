import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


class DeliveryException(Exception):
    def __init__(self, message: str, code: str = "DELIVERY_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class DelivererNotFound(DeliveryException):
    def __init__(self, deliverer_id: str):
        super().__init__(f"Deliverer {deliverer_id} not found", "DELIVERER_NOT_FOUND", 404)


class DelivererStatus:
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


@dataclass
class Deliverer:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    phone: str = ""
    vehicle: str = "BIKE"
    status: str = DelivererStatus.AVAILABLE
    location: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
