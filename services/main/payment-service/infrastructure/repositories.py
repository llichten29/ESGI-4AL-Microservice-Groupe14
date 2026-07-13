from typing import Optional

from domain.models import Payment


class InMemoryPaymentRepository:
    def __init__(self):
        self._payments: dict[str, Payment] = {}

    def save(self, payment: Payment):
        self._payments[payment.id] = payment

    def find_by_id(self, payment_id: str) -> Optional[Payment]:
        return self._payments.get(payment_id)

    def find_by_order_id(self, order_id: str) -> Optional[Payment]:
        for payment in self._payments.values():
            if payment.order_id == order_id:
                return payment
        return None

    def find_all(self) -> list[Payment]:
        return list(self._payments.values())
