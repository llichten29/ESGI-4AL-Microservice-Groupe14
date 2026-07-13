from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import ClassVar


@dataclass
class BaseEvent:
    """Events on the order.events exchange use camelCase payloads: this is the
    contract already consumed by customer-service (queue customer.order_history)."""
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
class OrderCreated(BaseEvent):
    ROUTING_KEY = "order.created"
    order_id: str = ""
    customer_id: str = ""
    restaurant_id: str = ""
    restaurant_name: str = ""
    total_price: float = 0.0
    items: list = field(default_factory=list)
    delivery_address: dict = field(default_factory=dict)
    payment: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "eventId": self.event_id,
            "timestamp": self.timestamp,
            "orderId": self.order_id,
            "customerId": self.customer_id,
            "restaurantId": self.restaurant_id,
            "restaurantName": self.restaurant_name,
            "totalPrice": self.total_price,
            "items": self.items,
            "deliveryAddress": self.delivery_address,
            "payment": self.payment
        }


@dataclass
class OrderConfirmed(BaseEvent):
    ROUTING_KEY = "order.confirmed"
    order_id: str = ""
    customer_id: str = ""
    restaurant_id: str = ""
    payment_id: str = ""
    total_price: float = 0.0

    def to_dict(self) -> dict:
        return {
            "eventId": self.event_id,
            "timestamp": self.timestamp,
            "orderId": self.order_id,
            "customerId": self.customer_id,
            "restaurantId": self.restaurant_id,
            "paymentId": self.payment_id,
            "totalPrice": self.total_price
        }


@dataclass
class OrderCancelled(BaseEvent):
    ROUTING_KEY = "order.cancelled"
    order_id: str = ""
    customer_id: str = ""
    restaurant_id: str = ""
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "eventId": self.event_id,
            "timestamp": self.timestamp,
            "orderId": self.order_id,
            "customerId": self.customer_id,
            "restaurantId": self.restaurant_id,
            "reason": self.reason
        }


@dataclass
class OrderDelivered(BaseEvent):
    ROUTING_KEY = "order.delivered"
    order_id: str = ""
    customer_id: str = ""
    restaurant_id: str = ""
    delivery_id: str = ""

    def to_dict(self) -> dict:
        return {
            "eventId": self.event_id,
            "timestamp": self.timestamp,
            "orderId": self.order_id,
            "customerId": self.customer_id,
            "restaurantId": self.restaurant_id,
            "deliveryId": self.delivery_id
        }
