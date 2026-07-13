import time
import uuid
import logging
from datetime import datetime, timezone

from domain.models import (
    Payment, Refund, PaymentStatus,
    PaymentException, PaymentNotFound, PaymentDeclined, PaymentGatewayError, InvalidRefund
)
from domain.events import PaymentProcessed, PaymentFailed, PaymentRefunded
from main.shared.retry import retry_with_backoff

logger = logging.getLogger(__name__)

DECLINE_CARD_TOKEN = "card_declined"
FLAKY_CARD_TOKEN = "card_flaky"
MAX_PAYMENT_AMOUNT = 500.0


class PaymentService:
    """Simulates an external payment gateway behind a retry with exponential backoff (1s/2s/4s).

    Deterministic simulation for demos and tests:
    - card_token == "card_declined" or amount > 500 -> declined (no retry, business failure)
    - card_token == "card_flaky" -> two transient gateway errors, then success (shows the retry)
    - anything else -> success
    """

    def __init__(self, repository, broker=None, sleep=time.sleep):
        self.repository = repository
        self.broker = broker
        self.exchange = "payment.events"
        self._flaky_attempts: dict[str, int] = {}
        self._gateway_call = retry_with_backoff(
            max_retries=3,
            base_delay=1.0,
            multiplier=2.0,
            exceptions=(PaymentGatewayError, ConnectionError),
            sleep=sleep
        )(self._call_gateway)

    def _publish(self, event):
        if not self.broker:
            return
        try:
            self.broker.publish_event(
                exchange=self.exchange,
                routing_key=event.routing_key,
                event_data=event.to_dict()
            )
        except Exception as e:
            logging.exception(f"Failed to publish event {event.event_type}: {e}")

    def _call_gateway(self, payment: Payment) -> str:
        if payment.card_token == DECLINE_CARD_TOKEN:
            raise PaymentDeclined("Card declined by provider")
        if payment.amount > MAX_PAYMENT_AMOUNT:
            raise PaymentDeclined(f"Amount exceeds the {MAX_PAYMENT_AMOUNT:.0f} EUR limit")
        if payment.card_token == FLAKY_CARD_TOKEN:
            attempts = self._flaky_attempts.get(payment.id, 0) + 1
            self._flaky_attempts[payment.id] = attempts
            if attempts <= 2:
                raise PaymentGatewayError(f"Gateway timeout (simulated, attempt {attempts})")
        return f"txn_{uuid.uuid4().hex[:12]}"

    def process_payment(self, data: dict) -> Payment:
        order_id = data.get("order_id", "")
        if not order_id:
            raise PaymentException("order_id is required", "INVALID_INPUT", 422)

        existing = self.repository.find_by_order_id(order_id)
        if existing and existing.status in (PaymentStatus.COMPLETED, PaymentStatus.PROCESSING):
            logger.info(f"Payment for order {order_id} already processed - idempotent replay")
            return existing

        amount = float(data.get("amount", 0))
        if amount <= 0:
            raise PaymentException("amount must be positive", "INVALID_INPUT", 422)

        payment = Payment(
            id=str(uuid.uuid4()),
            order_id=order_id,
            customer_id=data.get("customer_id", ""),
            amount=amount,
            currency=data.get("currency", "EUR"),
            payment_method=data.get("payment_method", "CARD"),
            card_token=data.get("card_token", ""),
            status=PaymentStatus.PROCESSING
        )
        self.repository.save(payment)

        try:
            transaction_id = self._gateway_call(payment)
        except PaymentDeclined as e:
            self._mark_failed(payment, e.message)
            raise
        except (PaymentGatewayError, ConnectionError) as e:
            self._mark_failed(payment, str(e))
            raise PaymentGatewayError(f"Gateway unreachable after retries: {e}")

        payment.status = PaymentStatus.COMPLETED
        payment.transaction_id = transaction_id
        payment.completed_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(payment)

        self._publish(PaymentProcessed(
            payment_id=payment.id,
            order_id=payment.order_id,
            customer_id=payment.customer_id,
            amount=payment.amount,
            transaction_id=payment.transaction_id
        ))

        return payment

    def _mark_failed(self, payment: Payment, reason: str):
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = reason
        self.repository.save(payment)

        self._publish(PaymentFailed(
            payment_id=payment.id,
            order_id=payment.order_id,
            customer_id=payment.customer_id,
            amount=payment.amount,
            reason=reason
        ))

    def get_payment(self, payment_id: str) -> Payment:
        payment = self.repository.find_by_id(payment_id)
        if not payment:
            raise PaymentNotFound(payment_id)
        return payment

    def get_payment_by_order(self, order_id: str) -> Payment:
        payment = self.repository.find_by_order_id(order_id)
        if not payment:
            raise PaymentNotFound(f"for order {order_id}")
        return payment

    def refund(self, payment_id: str, amount: float = 0.0, reason: str = "") -> Payment:
        payment = self.get_payment(payment_id)

        if payment.status not in (PaymentStatus.COMPLETED, PaymentStatus.REFUNDED):
            raise InvalidRefund(f"Cannot refund a payment in status {payment.status}")

        refund_amount = float(amount) if amount else payment.amount - payment.refunded_amount
        if refund_amount <= 0:
            raise InvalidRefund("Refund amount must be positive")
        if payment.refunded_amount + refund_amount > payment.amount:
            raise InvalidRefund("Refund exceeds the amount paid")

        refund = Refund(amount=refund_amount, reason=reason)
        payment.refunds.append(refund)
        if payment.refunded_amount >= payment.amount:
            payment.status = PaymentStatus.REFUNDED
        self.repository.save(payment)

        self._publish(PaymentRefunded(
            payment_id=payment.id,
            order_id=payment.order_id,
            refund_id=refund.id,
            amount=refund.amount,
            reason=reason
        ))

        return payment
