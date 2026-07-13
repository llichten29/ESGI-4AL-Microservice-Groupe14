from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import ClassVar


@dataclass
class BaseEvent:
    event_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    ROUTING_KEY: ClassVar[str] = ""

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    @property
    def routing_key(self) -> str:
        return self.ROUTING_KEY or self.event_type

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PaymentProcessed(BaseEvent):
    ROUTING_KEY = "payment.processed"
    payment_id: str = ""
    order_id: str = ""
    customer_id: str = ""
    amount: float = 0.0
    transaction_id: str = ""


@dataclass
class PaymentFailed(BaseEvent):
    ROUTING_KEY = "payment.failed"
    payment_id: str = ""
    order_id: str = ""
    customer_id: str = ""
    amount: float = 0.0
    reason: str = ""


@dataclass
class PaymentRefunded(BaseEvent):
    ROUTING_KEY = "payment.refunded"
    payment_id: str = ""
    order_id: str = ""
    refund_id: str = ""
    amount: float = 0.0
    reason: str = ""
