import sys
import os

import pytest
from unittest.mock import MagicMock

_deliverer_base = os.path.join(os.path.dirname(__file__), '..', '..', 'main', 'deliverer-service')
_conflicting_modules = ['domain', 'application', 'infrastructure', 'interfaces', 'app', 'config']
for mod in list(sys.modules.keys()):
    parts = mod.split('.')
    if parts[0] in _conflicting_modules:
        sys.modules.pop(mod, None)

sys.path.insert(0, _deliverer_base)


@pytest.fixture
def models():
    import domain.models
    return domain.models


@pytest.fixture
def mongo_client():
    import mongomock
    return mongomock.MongoClient('mongodb://localhost:27020/test')


@pytest.fixture
def deliverer_repo(mongo_client):
    from infrastructure.repositories import MongoDBDelivererRepository
    repo = MongoDBDelivererRepository("mongodb://localhost:27020/test", client=mongo_client)
    repo.db = repo.client.test
    repo.collection = repo.db.deliverers
    yield repo
    repo.collection.delete_many({})


@pytest.fixture
def deliverer_service(deliverer_repo, mock_broker):
    from application.deliverer_service import DelivererService
    return DelivererService(repository=deliverer_repo, broker=mock_broker)


@pytest.fixture
def deliverer_app(deliverer_service):
    from flask import Flask
    from interfaces.http.routes import routes as deliverer_routes
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.deliverer_service = deliverer_service
    app.register_blueprint(deliverer_routes)
    return app


@pytest.fixture
def deliverer_client(deliverer_app):
    return deliverer_app.test_client()
