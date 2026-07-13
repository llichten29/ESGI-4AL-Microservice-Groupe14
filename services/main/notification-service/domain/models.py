import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


class NotificationException(Exception):
    def __init__(self, message: str, code: str = "NOTIFICATION_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotificationNotFound(NotificationException):
    def __init__(self, notification_id: str):
        super().__init__(f"Notification {notification_id} not found", "NOTIFICATION_NOT_FOUND", 404)


class RecipientType:
    CUSTOMER = "CUSTOMER"
    RESTAURANT = "RESTAURANT"
    DELIVERER = "DELIVERER"


@dataclass
class Notification:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    recipient_id: str = ""
    recipient_type: str = RecipientType.CUSTOMER
    type: str = ""
    # The prototype only simulates the channels described in the docs (EMAIL/PUSH/SMS)
    # by logging: notifications are persisted so the SAGA effects stay observable.
    channel: str = "LOG"
    message: str = ""
    payload: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
