import sys
import os
import importlib

import pytest
from unittest.mock import patch, MagicMock


_customer_base = os.path.join(os.path.dirname(__file__), '..', '..', 'main', 'customer-service')
_other_bases = [
    p for p in sys.path
    if 'restaurant-service' in p or 'order-service' in p or 'delivery-service' in p
]
for p in _other_bases:
    sys.path.remove(p)

_conflicting_modules = ['domain', 'application', 'infrastructure', 'interfaces']
for mod in list(sys.modules.keys()):
    parts = mod.split('.')
    if any(c in mod for c in ['restaurant', 'order', 'delivery']):
        sys.modules.pop(mod, None)
    elif parts[0] in _conflicting_modules:
        sys.modules.pop(mod, None)

sys.path.insert(0, _customer_base)


def _fake_hash(password):
    return f"fakehash:{password}"


def _fake_check(hash_val, password):
    return hash_val == f"fakehash:{password}"


@pytest.fixture(autouse=True)
def _mock_password_hashing():
    _mod = importlib.import_module('application.customer_service')
    with patch.object(_mod, 'generate_password_hash', side_effect=_fake_hash):
        with patch.object(_mod, 'check_password_hash', side_effect=_fake_check):
            yield


@pytest.fixture
def customer_repo():
    import mongomock
    with patch('pymongo.MongoClient', return_value=mongomock.MongoClient('mongodb://localhost:27017/test')):
        from infrastructure.repositories import MongoDBCustomerRepository
        repo = MongoDBCustomerRepository("mongodb://localhost:27017/test")
        repo.db = repo.client.test
        repo.collection = repo.db.customers
        yield repo
        repo.collection.delete_many({})


@pytest.fixture
def customer_service(customer_repo, mock_broker):
    from application.customer_service import CustomerService
    return CustomerService(repository=customer_repo, broker=mock_broker, jwt_secret="test-secret")


@pytest.fixture
def customer_service_no_broker(customer_repo):
    from application.customer_service import CustomerService
    return CustomerService(repository=customer_repo, broker=None, jwt_secret="test-secret")


@pytest.fixture
def customer_app(customer_service):
    from flask import Flask
    from interfaces.http.routes import routes as customer_routes
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['JWT_SECRET'] = 'test-secret'
    app.customer_service = customer_service
    app.register_blueprint(customer_routes)
    return app


@pytest.fixture
def customer_client(customer_app):
    return customer_app.test_client()


@pytest.fixture
def auth_headers(customer_service):
    customer, token = customer_service.register({
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123"
    })
    return {"Authorization": f"Bearer {token}"}
