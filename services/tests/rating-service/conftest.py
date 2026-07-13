import sys
import os

import pytest

_rating_base = os.path.join(os.path.dirname(__file__), '..', '..', 'main', 'rating-service')
_other_bases = [
    p for p in sys.path
    if ('-service' in p or 'api-gateway' in p) and 'rating-service' not in p
]
for p in _other_bases:
    sys.path.remove(p)

_conflicting_modules = ['domain', 'application', 'infrastructure', 'interfaces']
for mod in list(sys.modules.keys()):
    parts = mod.split('.')
    if parts[0] in _conflicting_modules:
        sys.modules.pop(mod, None)

sys.path.insert(0, _rating_base)


@pytest.fixture
def models():
    import domain.models as m
    return m


@pytest.fixture
def repo():
    from infrastructure.repositories import InMemoryRatingRepository
    return InMemoryRatingRepository()


@pytest.fixture
def rating_service(repo, mock_broker):
    from application.rating_service import RatingService
    return RatingService(repository=repo, broker=mock_broker)


@pytest.fixture
def rating_app(rating_service):
    from flask import Flask
    from interfaces.http.routes import routes as rating_routes
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.rating_service = rating_service
    app.register_blueprint(rating_routes)
    return app


@pytest.fixture
def rating_client(rating_app):
    return rating_app.test_client()


@pytest.fixture
def rating_payload():
    return {
        "order_id": "order-1",
        "rater_id": "cust-1",
        "rater_type": "CUSTOMER",
        "target_id": "rest-1",
        "target_type": "RESTAURANT",
        "score": 5,
        "comment": "Excellent!"
    }
