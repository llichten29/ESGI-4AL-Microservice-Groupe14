import sys
import os

import pytest
from unittest.mock import MagicMock


_payment_base = os.path.join(os.path.dirname(__file__), '..', '..', 'main', 'payment-service')
_other_bases = [
    p for p in sys.path
    if ('-service' in p or 'api-gateway' in p) and 'payment-service' not in p
]
for p in _other_bases:
    sys.path.remove(p)

_conflicting_modules = ['domain', 'application', 'infrastructure', 'interfaces', 'app', 'config']
for mod in list(sys.modules.keys()):
    parts = mod.split('.')
    if parts[0] in _conflicting_modules:
        sys.modules.pop(mod, None)

sys.path.insert(0, _payment_base)


@pytest.fixture
def models():
    import domain.models
    return domain.models


@pytest.fixture
def payment_repo():
    from infrastructure.repositories import InMemoryPaymentRepository
    return InMemoryPaymentRepository()


@pytest.fixture
def fake_sleep():
    return MagicMock()


@pytest.fixture
def payment_service(payment_repo, mock_broker, fake_sleep):
    from application.payment_service import PaymentService
    return PaymentService(repository=payment_repo, broker=mock_broker, sleep=fake_sleep)


@pytest.fixture
def payment_app(payment_service):
    from flask import Flask
    from interfaces.http.routes import routes as payment_routes
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.payment_service = payment_service
    app.register_blueprint(payment_routes)
    return app


@pytest.fixture
def payment_client(payment_app):
    return payment_app.test_client()
