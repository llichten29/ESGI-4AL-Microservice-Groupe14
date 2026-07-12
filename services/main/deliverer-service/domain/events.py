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
class DelivererRegistered(BaseEvent):
    ROUTING_KEY = "deliverer.registered"
    deliverer_id: str = ""
    deliverer_name: str = ""
    status: str = ""


@dataclass
class DelivererAvailabilityChanged(BaseEvent):
    ROUTING_KEY = "deliverer.availability_changed"
    deliverer_id: str = ""
    deliverer_name: str = ""
    status: str = ""
