from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


@dataclass
class BaseEvent:
    event_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RestaurantRegistered(BaseEvent):
    restaurant_id: str = ""
    name: str = ""
    address: Optional[dict] = None
    cuisine_type: str = ""


@dataclass
class RestaurantUpdated(BaseEvent):
    restaurant_id: str = ""
    name: str = ""
    cuisine_type: str = ""


@dataclass
class RestaurantClosed(BaseEvent):
    restaurant_id: str = ""
    reason: str = ""


@dataclass
class MenuUpdated(BaseEvent):
    restaurant_id: str = ""
    menu_id: str = ""
    items: list = field(default_factory=list)


@dataclass
class OrderAccepted(BaseEvent):
    restaurant_id: str = ""
    order_id: str = ""
    estimated_prep_time: int = 0


@dataclass
class OrderRejected(BaseEvent):
    restaurant_id: str = ""
    order_id: str = ""
    reason: str = ""


@dataclass
class OrderPreparing(BaseEvent):
    restaurant_id: str = ""
    order_id: str = ""
    estimated_prep_time: int = 0


@dataclass
class OrderReady(BaseEvent):
    restaurant_id: str = ""
    order_id: str = ""
