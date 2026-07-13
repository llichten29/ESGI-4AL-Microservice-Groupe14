import logging

import requests

from main.shared.circuit_breaker import CircuitBreaker, CircuitBreakerException
from main.shared.retry import retry_with_backoff

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5


class RestaurantClient:
    """Synchronous calls to restaurant-service, protected by a circuit breaker.

    Network errors and 5xx responses trip the breaker; business rejections
    (4xx with isValid=false) are normal responses and do not.
    """

    def __init__(self, base_url: str, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.circuit_breaker = CircuitBreaker(
            name="order->restaurant",
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=(requests.RequestException,)
        )

    def _post_validate(self, restaurant_id: str, items: list) -> dict:
        resp = requests.post(
            f"{self.base_url}/restaurants/{restaurant_id}/validate",
            json={"items": items},
            timeout=self.timeout
        )
        if resp.status_code >= 500:
            resp.raise_for_status()
        return resp.json()

    def _get_restaurant(self, restaurant_id: str) -> dict:
        resp = requests.get(
            f"{self.base_url}/restaurants/{restaurant_id}",
            timeout=self.timeout
        )
        if resp.status_code >= 500:
            resp.raise_for_status()
        return resp.json()

    def validate_order(self, restaurant_id: str, items: list) -> dict:
        return self.circuit_breaker.call(self._post_validate, restaurant_id, items)

    def get_restaurant(self, restaurant_id: str) -> dict:
        return self.circuit_breaker.call(self._get_restaurant, restaurant_id)


class PaymentClient:
    """Synchronous compensation calls to payment-service (refunds), protected by
    a circuit breaker AND an exponential retry (1s/2s/4s)."""

    def __init__(self, base_url: str, timeout: int = DEFAULT_TIMEOUT, sleep=None):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.circuit_breaker = CircuitBreaker(
            name="order->payment",
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=(requests.RequestException,)
        )
        retry_kwargs = {
            "max_retries": 3,
            "base_delay": 1.0,
            "multiplier": 2.0,
            "exceptions": (requests.RequestException,)
        }
        if sleep is not None:
            retry_kwargs["sleep"] = sleep
        self._refund_with_retry = retry_with_backoff(**retry_kwargs)(self._post_refund)

    def _post_refund(self, payment_id: str, amount: float, reason: str) -> dict:
        def _do():
            resp = requests.post(
                f"{self.base_url}/payments/{payment_id}/refund",
                json={"amount": amount, "reason": reason},
                timeout=self.timeout
            )
            if resp.status_code >= 500:
                resp.raise_for_status()
            return resp.json()
        return self.circuit_breaker.call(_do)

    def refund(self, payment_id: str, amount: float = 0.0, reason: str = "") -> dict:
        return self._refund_with_retry(payment_id, amount, reason)
