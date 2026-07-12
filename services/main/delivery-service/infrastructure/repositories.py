from typing import Optional

from domain.models import Delivery


class InMemoryDeliveryRepository:
    def __init__(self):
        self._store: dict[str, Delivery] = {}

    def save(self, delivery: Delivery):
        self._store[delivery.id] = delivery

    def find_by_id(self, delivery_id: str) -> Optional[Delivery]:
        return self._store.get(delivery_id)

    def find_by_order_id(self, order_id: str) -> Optional[Delivery]:
        for d in self._store.values():
            if d.order_id == order_id:
                return d
        return None

    def find_all(self) -> list[Delivery]:
        return list(self._store.values())
