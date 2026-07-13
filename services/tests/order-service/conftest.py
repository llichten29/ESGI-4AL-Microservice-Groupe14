import sys
import os

import pytest
from unittest.mock import MagicMock


_order_base = os.path.join(os.path.dirname(__file__), '..', '..', 'main', 'order-service')
_other_bases = [
    p for p in sys.path
    if ('-service' in p or 'api-gateway' in p) and 'order-service' not in p
]
for p in _other_bases:
    sys.path.remove(p)

_conflicting_modules = ['domain', 'application', 'infrastructure', 'interfaces']
for mod in list(sys.modules.keys()):
    parts = mod.split('.')
    if parts[0] in _conflicting_modules:
        sys.modules.pop(mod, None)

sys.path.insert(0, _order_base)

RESTAURANT = {
    "id": "resto-1",
    "name": "Chez Testeur",
    "menus": [{
        "id": "menu-1",
        "items": [
            {"id": "dish-1", "name": "Pizza", "price": 12.5},
            {"id": "dish-2", "name": "Tiramisu", "price": 6.0}
        ]
    }]
}


@pytest.fixture
def models():
    import domain.models
    return domain.models


@pytest.fixture
def order_repo():
    from infrastructure.repositories import InMemoryOrderRepository
    return InMemoryOrderRepository()


@pytest.fixture
def restaurant_client():
    client = MagicMock()
    client.validate_order.return_value = {"isValid": True, "estimatedPrepTime": 25}
    client.get_restaurant.return_value = RESTAURANT
    client.circuit_breaker.get_state.return_value = {"name": "order->restaurant", "state": "CLOSED"}
    return client


@pytest.fixture
def payment_client():
    client = MagicMock()
    client.refund.return_value = {"status": "REFUNDED"}
    client.circuit_breaker.get_state.return_value = {"name": "order->payment", "state": "CLOSED"}
    return client


@pytest.fixture
def order_service(order_repo, restaurant_client, payment_client, mock_broker):
    from application.order_service import OrderService
    return OrderService(
        repository=order_repo,
        restaurant_client=restaurant_client,
        payment_client=payment_client,
        broker=mock_broker
    )


@pytest.fixture
def order_app(order_service):
    from flask import Flask
    from interfaces.http.routes import routes as order_routes
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.order_service = order_service
    app.register_blueprint(order_routes)
    return app


@pytest.fixture
def order_client(order_app):
    return order_app.test_client()


@pytest.fixture
def order_payload():
    return {
        "customerId": "cust-1",
        "restaurantId": "resto-1",
        "items": [
            {"dishId": "dish-1", "quantity": 2},
            {"dishId": "dish-2", "quantity": 1}
        ],
        "deliveryAddress": {"street": "1 rue des Tests", "city": "Paris"},
        "payment": {"method": "CARD", "cardToken": "card_ok"}
    }
