import uuid
import logging
from datetime import datetime, timezone

from domain.models import (
    Deliverer, DelivererStatus,
    DeliveryException, DelivererNotFound
)
from domain.events import DelivererRegistered, DelivererAvailabilityChanged

logger = logging.getLogger(__name__)


class DelivererService:
    def __init__(self, repository, broker=None):
        self.repository = repository
        self.broker = broker
        self.exchange = "deliverer.events"

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
            logging.exception(f"Failed to publish event {event.event_type}: {e}")

    def register_deliverer(self, data: dict) -> Deliverer:
        deliverer = Deliverer(
            id=str(uuid.uuid4()),
            name=data.get("name", ""),
            phone=data.get("phone", ""),
            vehicle=data.get("vehicle", "BIKE"),
            status=DelivererStatus.AVAILABLE,
            location=data.get("location", {})
        )
        self.repository.save(deliverer)
        self._publish(DelivererRegistered(
            deliverer_id=deliverer.id,
            deliverer_name=deliverer.name,
            status=deliverer.status
        ))
        self._publish(DelivererAvailabilityChanged(
            deliverer_id=deliverer.id,
            deliverer_name=deliverer.name,
            status=deliverer.status
        ))
        return deliverer

    def get_deliverers(self) -> list[Deliverer]:
        return self.repository.find_all()

    def get_deliverer(self, deliverer_id: str) -> Deliverer:
        deliverer = self.repository.find_by_id(deliverer_id)
        if not deliverer:
            raise DelivererNotFound(deliverer_id)
        return deliverer

    def set_availability(self, deliverer_id: str, status: str) -> Deliverer:
        if status not in (DelivererStatus.AVAILABLE, DelivererStatus.BUSY, DelivererStatus.OFFLINE):
            raise DeliveryException(f"Invalid status {status}", "INVALID_STATUS", 422)
        deliverer = self.get_deliverer(deliverer_id)
        deliverer.status = status
        deliverer.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(deliverer)
        if status == DelivererStatus.AVAILABLE:
            self._publish(DelivererAvailabilityChanged(
                deliverer_id=deliverer.id,
                deliverer_name=deliverer.name,
                status=deliverer.status
            ))
        return deliverer

    def assign_available(self) -> dict:
        deliverer = self.repository.find_first_available()
        if not deliverer:
            return {}
        deliverer.status = DelivererStatus.BUSY
        deliverer.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(deliverer)
        return {"id": deliverer.id, "name": deliverer.name}

    def release_deliverer(self, deliverer_id: str) -> Deliverer:
        deliverer = self.get_deliverer(deliverer_id)
        deliverer.status = DelivererStatus.AVAILABLE
        deliverer.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(deliverer)
        self._publish(DelivererAvailabilityChanged(
            deliverer_id=deliverer.id,
            deliverer_name=deliverer.name,
            status=deliverer.status
        ))
        return deliverer
