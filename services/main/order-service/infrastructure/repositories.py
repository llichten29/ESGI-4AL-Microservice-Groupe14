from typing import Optional

from domain.models import Order


class InMemoryOrderRepository:
    def __init__(self):
        self._orders: dict[str, Order] = {}

    def save(self, order: Order):
        self._orders[order.id] = order

    def find_by_id(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    def find_by_customer(self, customer_id: str) -> list[Order]:
        return [o for o in self._orders.values() if o.customer_id == customer_id]

    def find_all(self) -> list[Order]:
        return list(self._orders.values())
