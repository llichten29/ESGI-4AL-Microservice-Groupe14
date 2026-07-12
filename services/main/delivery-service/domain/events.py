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

    def get_routing_key(self) -> str:
        return self.ROUTING_KEY or self.event_type

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DeliveryAssigned(BaseEvent):
    ROUTING_KEY = "delivery.assigned"
    delivery_id: str = ""
    order_id: str = ""
    deliverer_id: str = ""
    deliverer_name: str = ""
    customer_id: str = ""
    restaurant_id: str = ""


@dataclass
class DeliveryInTransit(BaseEvent):
    ROUTING_KEY = "delivery.in_transit"
    delivery_id: str = ""
    order_id: str = ""
    location: dict = field(default_factory=dict)


@dataclass
class DeliveryCompleted(BaseEvent):
    ROUTING_KEY = "delivery.completed"
    delivery_id: str = ""
    order_id: str = ""
    deliverer_id: str = ""


@dataclass
class DeliveryFailed(BaseEvent):
    ROUTING_KEY = "delivery.failed"
    delivery_id: str = ""
    order_id: str = ""
    reason: str = ""
