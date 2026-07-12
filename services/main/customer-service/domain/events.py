from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime, timezone


@dataclass
class BaseEvent:
    event_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CustomerRegistered(BaseEvent):
    customer_id: str = ""
    name: str = ""
    email: str = ""
