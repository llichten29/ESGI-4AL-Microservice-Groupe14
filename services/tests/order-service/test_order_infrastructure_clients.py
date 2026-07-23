import pytest
import requests
from unittest.mock import MagicMock

from main.shared.circuit_breaker import CircuitBreakerException


def _response(status_code, payload=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload if payload is not None else {}
    if status_code >= 500:
        resp.raise_for_status.side_effect = requests.HTTPError(f"{status_code} server error")
    else:
        resp.raise_for_status.return_value = None
    return resp


@pytest.fixture
def clients_module(monkeypatch):
    import infrastructure.clients as clients
    monkeypatch.setattr(clients, 'requests', MagicMock(
        RequestException=requests.RequestException,
        HTTPError=requests.HTTPError,
        ConnectionError=requests.ConnectionError,
    ))
    return clients


class TestRestaurantClient:
    def test_validate_order_success(self, clients_module):
        clients_module.requests.post.return_value = _response(200, {"isValid": True})
        client = clients_module.RestaurantClient("http://restaurant:8002/")
        result = client.validate_order("rest-1", [{"dishId": "d1", "quantity": 2}])
        assert result == {"isValid": True}
        args, kwargs = clients_module.requests.post.call_args
        assert args[0] == "http://restaurant:8002/restaurants/rest-1/validate"
        assert kwargs["json"] == {"items": [{"dishId": "d1", "quantity": 2}]}

    def test_business_rejection_does_not_trip_breaker(self, clients_module):
        clients_module.requests.post.return_value = _response(422, {"isValid": False, "reason": "closed"})
        client = clients_module.RestaurantClient("http://restaurant:8002")
        for _ in range(5):
            assert client.validate_order("rest-1", [])["isValid"] is False
        assert client.circuit_breaker.state.value == "CLOSED"

    def test_server_errors_open_the_circuit(self, clients_module):
        clients_module.requests.post.return_value = _response(503)
        client = clients_module.RestaurantClient("http://restaurant:8002")
        for _ in range(3):
            with pytest.raises(requests.HTTPError):
                client.validate_order("rest-1", [])
        with pytest.raises(CircuitBreakerException):
            client.validate_order("rest-1", [])
        assert clients_module.requests.post.call_count == 3

    def test_get_restaurant_success(self, clients_module):
        clients_module.requests.get.return_value = _response(200, {"id": "rest-1", "name": "Chez Nino"})
        client = clients_module.RestaurantClient("http://restaurant:8002")
        assert client.get_restaurant("rest-1")["name"] == "Chez Nino"

    def test_get_restaurant_server_error_raises(self, clients_module):
        clients_module.requests.get.return_value = _response(500)
        client = clients_module.RestaurantClient("http://restaurant:8002")
        with pytest.raises(requests.HTTPError):
            client.get_restaurant("rest-1")


class TestPaymentClient:
    def test_refund_success(self, clients_module):
        clients_module.requests.post.return_value = _response(200, {"status": "REFUNDED"})
        client = clients_module.PaymentClient("http://payment:8004", sleep=lambda s: None)
        result = client.refund("pay-1", amount=12.5, reason="Order rejected")
        assert result == {"status": "REFUNDED"}
        args, kwargs = clients_module.requests.post.call_args
        assert args[0] == "http://payment:8004/payments/pay-1/refund"
        assert kwargs["json"] == {"amount": 12.5, "reason": "Order rejected"}

    def test_refund_retries_transient_failure_then_succeeds(self, clients_module):
        clients_module.requests.post.side_effect = [
            requests.ConnectionError("down"),
            requests.ConnectionError("down"),
            _response(200, {"status": "REFUNDED"}),
        ]
        client = clients_module.PaymentClient("http://payment:8004", sleep=lambda s: None)
        assert client.refund("pay-1")["status"] == "REFUNDED"
        assert clients_module.requests.post.call_count == 3

    def test_refund_persistent_failure_opens_circuit(self, clients_module):
        clients_module.requests.post.side_effect = requests.ConnectionError("down")
        client = clients_module.PaymentClient("http://payment:8004", sleep=lambda s: None)
        with pytest.raises(CircuitBreakerException):
            client.refund("pay-1")
        assert clients_module.requests.post.call_count == 3
        assert client.circuit_breaker.state.value == "OPEN"
