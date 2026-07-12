import logging
from datetime import datetime, timezone

from domain.models import (
    Delivery, DeliveryStatus,
    DeliveryException, DeliveryNotFound
)
from domain.events import (
    DeliveryAssigned, DeliveryInTransit,
    DeliveryCompleted, DeliveryFailed
)

logger = logging.getLogger(__name__)


class DeliveryService:
    def __init__(self, repository, deliverer_client, broker=None):
        self.repository = repository
        self.deliverer_client = deliverer_client
        self.broker = broker
        self.exchange = "delivery.events"

    def _publish(self, event):
        if not self.broker:
            return
        try:
            self.broker.publish_event(
                exchange=self.exchange,
                routing_key=event.get_routing_key(),
                event_data=event.to_dict()
            )
        except Exception as e:
            logger.exception(f"Failed to publish event {event.event_type}: {e}")

    def assign_deliverer(self, order_id: str, customer_id: str = "", restaurant_id: str = "") -> Delivery:
        result = self.deliverer_client.assign_available()
        if not result or "id" not in result:
            raise DeliveryException(
                "No deliverer available", "NO_DELIVERER_AVAILABLE", 503
            )

        now = datetime.now(timezone.utc).isoformat()
        delivery = Delivery(
            order_id=order_id,
            deliverer_id=result["id"],
            deliverer_name=result.get("name", ""),
            customer_id=customer_id,
            restaurant_id=restaurant_id,
            status=DeliveryStatus.ASSIGNED,
            assigned_at=now,
            created_at=now,
            updated_at=now
        )
        self.repository.save(delivery)
        self._publish(DeliveryAssigned(
            delivery_id=delivery.id,
            order_id=delivery.order_id,
            deliverer_id=delivery.deliverer_id,
            deliverer_name=delivery.deliverer_name,
            customer_id=delivery.customer_id,
            restaurant_id=delivery.restaurant_id
        ))
        return delivery

    def get_delivery(self, delivery_id: str) -> Delivery:
        delivery = self.repository.find_by_id(delivery_id)
        if not delivery:
            raise DeliveryNotFound(delivery_id)
        return delivery

    def get_delivery_by_order(self, order_id: str) -> Delivery:
        delivery = self.repository.find_by_order_id(order_id)
        if not delivery:
            raise DeliveryNotFound(order_id)
        return delivery

    def update_location(self, delivery_id: str, location: dict) -> Delivery:
        delivery = self.get_delivery(delivery_id)
        if delivery.status not in (DeliveryStatus.ASSIGNED, DeliveryStatus.IN_TRANSIT):
            raise DeliveryException(
                f"Cannot update location in status {delivery.status}",
                "INVALID_STATUS", 422
            )
        delivery.location = location
        delivery.status = DeliveryStatus.IN_TRANSIT
        delivery.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(delivery)
        self._publish(DeliveryInTransit(
            delivery_id=delivery.id,
            order_id=delivery.order_id,
            location=delivery.location
        ))
        return delivery

    def confirm_delivery(self, delivery_id: str) -> Delivery:
        delivery = self.get_delivery(delivery_id)
        if delivery.status not in (DeliveryStatus.ASSIGNED, DeliveryStatus.IN_TRANSIT):
            raise DeliveryException(
                f"Cannot confirm delivery in status {delivery.status}",
                "INVALID_STATUS", 422
            )
        now = datetime.now(timezone.utc).isoformat()
        delivery.status = DeliveryStatus.DELIVERED
        delivery.delivered_at = now
        delivery.updated_at = now
        self.repository.save(delivery)
        self.deliverer_client.release_deliverer(delivery.deliverer_id)
        self._publish(DeliveryCompleted(
            delivery_id=delivery.id,
            order_id=delivery.order_id,
            deliverer_id=delivery.deliverer_id
        ))
        return delivery

    def fail_delivery(self, delivery_id: str, reason: str = "") -> Delivery:
        delivery = self.get_delivery(delivery_id)
        delivery.status = DeliveryStatus.FAILED
        delivery.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(delivery)
        self.deliverer_client.release_deliverer(delivery.deliverer_id)
        self._publish(DeliveryFailed(
            delivery_id=delivery.id,
            order_id=delivery.order_id,
            reason=reason
        ))
        return delivery
