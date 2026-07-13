import sys
import os

import pytest

_catalog_base = os.path.join(os.path.dirname(__file__), '..', '..', 'main', 'catalog-service')
_other_bases = [
    p for p in sys.path
    if ('-service' in p or 'api-gateway' in p) and 'catalog-service' not in p
]
for p in _other_bases:
    sys.path.remove(p)

_conflicting_modules = ['domain', 'application', 'infrastructure', 'interfaces']
for mod in list(sys.modules.keys()):
    parts = mod.split('.')
    if parts[0] in _conflicting_modules:
        sys.modules.pop(mod, None)

sys.path.insert(0, _catalog_base)


@pytest.fixture
def models():
    import domain.models as m
    return m


@pytest.fixture
def repo():
    from infrastructure.repositories import InMemoryCatalogRepository
    return InMemoryCatalogRepository()


@pytest.fixture
def catalog_service(repo):
    from application.catalog_service import CatalogService
    return CatalogService(repository=repo)


@pytest.fixture
def catalog_app(catalog_service):
    from flask import Flask
    from interfaces.http.routes import routes as catalog_routes
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.catalog_service = catalog_service
    app.register_blueprint(catalog_routes)
    return app


@pytest.fixture
def catalog_client(catalog_app):
    return catalog_app.test_client()


@pytest.fixture
def restaurant_registered():
    return {
        "restaurant_id": "rest-1",
        "name": "Chez Testeur",
        "cuisine_type": "ITALIAN",
        "address": {"street": "1 rue des Tests", "city": "Paris"}
    }


@pytest.fixture
def menu_updated():
    return {
        "restaurant_id": "rest-1",
        "items": [
            {"id": "dish-1", "name": "Pizza", "price": 12.5},
            {"id": "dish-2", "name": "Pasta", "price": 14.0}
        ]
    }


@pytest.fixture
def second_restaurant():
    return {
        "restaurant_id": "rest-2",
        "name": "Sushi Bar",
        "cuisine_type": "JAPANESE",
        "address": {"street": "2 rue des Sushis", "city": "Lyon"}
    }
