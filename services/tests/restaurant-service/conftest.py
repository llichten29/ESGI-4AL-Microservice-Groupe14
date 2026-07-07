import sys
import os

_restaurant_base = os.path.join(os.path.dirname(__file__), '..', '..', 'main', 'restaurant-service')
_other_bases = [
    p for p in sys.path
    if 'customer-service' in p or 'order-service' in p or 'delivery-service' in p
]
for p in _other_bases:
    sys.path.remove(p)

_conflicting_modules = ['domain', 'application', 'infrastructure', 'interfaces']
for mod in list(sys.modules.keys()):
    parts = mod.split('.')
    if any(c in mod for c in ['customer', 'order', 'delivery']):
        sys.modules.pop(mod, None)
    elif parts[0] in _conflicting_modules:
        sys.modules.pop(mod, None)

sys.path.insert(0, _restaurant_base)

import pytest


@pytest.fixture
def restaurant_repo():
    from infrastructure.repositories import InMemoryRestaurantRepository
    return InMemoryRestaurantRepository()


@pytest.fixture
def restaurant_service(restaurant_repo, mock_broker):
    from application.restaurant_service import RestaurantService
    return RestaurantService(repository=restaurant_repo, broker=mock_broker)


@pytest.fixture
def restaurant_service_no_broker(restaurant_repo):
    from application.restaurant_service import RestaurantService
    return RestaurantService(repository=restaurant_repo, broker=None)


@pytest.fixture
def restaurant_app(restaurant_service):
    from flask import Flask
    from interfaces.http.routes import routes as restaurant_routes
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.restaurant_service = restaurant_service
    app.register_blueprint(restaurant_routes)
    return app


@pytest.fixture
def restaurant_client(restaurant_app):
    return restaurant_app.test_client()
