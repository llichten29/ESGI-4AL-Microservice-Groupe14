import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


class PaymentException(Exception):
    def __init__(self, message: str, code: str = "PAYMENT_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class PaymentNotFound(PaymentException):
    def __init__(self, payment_id: str):
        super().__init__(f"Payment {payment_id} not found", "PAYMENT_NOT_FOUND", 404)


class PaymentDeclined(PaymentException):
    def __init__(self, reason: str = "Payment declined by provider"):
        super().__init__(reason, "PAYMENT_DECLINED", 402)


class PaymentGatewayError(PaymentException):
    """Transient failure of the external payment gateway - safe to retry."""
    def __init__(self, message: str = "Payment gateway unavailable"):
        super().__init__(message, "GATEWAY_ERROR", 502)


class InvalidRefund(PaymentException):
    def __init__(self, reason: str):
        super().__init__(reason, "INVALID_REFUND", 400)


class PaymentStatus:
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


@dataclass
class Refund:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    amount: float = 0.0
    reason: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Payment:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    customer_id: str = ""
    amount: float = 0.0
    currency: str = "EUR"
    payment_method: str = "CARD"
    card_token: str = ""
    status: str = PaymentStatus.PENDING
    transaction_id: str = ""
    failure_reason: str = ""
    refunds: list[Refund] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""

    @property
    def refunded_amount(self) -> float:
        return sum(r.amount for r in self.refunds)
