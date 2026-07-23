import os

import pytest
import yaml
from flask import Flask

import app as gateway_app

ENDPOINTS_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'ressources', 'endpoints'
)

SERVICE_URLS = {
    'ORDER_SERVICE_URL': 'http://order-service:8001',
    'RESTAURANT_SERVICE_URL': 'http://restaurant-service:8002',
    'CATALOG_SERVICE_URL': 'http://catalog-service:8003',
    'PAYMENT_SERVICE_URL': 'http://payment-service:8004',
    'DELIVERY_SERVICE_URL': 'http://delivery-service:8005',
    'NOTIFICATION_SERVICE_URL': 'http://notification-service:8006',
    'RATING_SERVICE_URL': 'http://rating-service:8007',
    'CUSTOMER_SERVICE_URL': 'http://customer-service:8008',
    'DELIVERER_SERVICE_URL': 'http://deliverer-service:8009',
}


@pytest.fixture
def flask_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config.update(SERVICE_URLS)
    return app


@pytest.fixture
def contracts():
    return gateway_app._load_contracts(ENDPOINTS_DIR)


class TestLoadContracts:
    def test_loads_all_ten_contracts(self, contracts):
        assert len(contracts) == 10
        filenames = [filename for filename, _ in contracts]
        assert gateway_app.GATEWAY_CONTRACT in filenames

    def test_missing_directory_returns_empty_list(self):
        assert gateway_app._load_contracts('/nonexistent/dir') == []


class TestRoutingTableFromContracts:
    def test_routes_orders_to_order_service(self, contracts, flask_app):
        table = gateway_app._load_routing_table(contracts, flask_app)
        match = table.match('POST', '/orders')
        assert match is not None
        assert match.rule.service_url == 'http://order-service:8001'

    def test_routes_ratings_to_rating_service(self, contracts, flask_app):
        table = gateway_app._load_routing_table(contracts, flask_app)
        match = table.match('POST', '/ratings')
        assert match is not None
        assert match.rule.service_url == 'http://rating-service:8007'

    def test_routes_parametrized_paths(self, contracts, flask_app):
        table = gateway_app._load_routing_table(contracts, flask_app)
        match = table.match('POST', '/restaurants/r-1/orders/o-1/accept')
        assert match is not None
        assert match.rule.service_url == 'http://restaurant-service:8002'

    def test_gateway_handled_paths_excluded(self, contracts, flask_app):
        table = gateway_app._load_routing_table(contracts, flask_app)
        assert table.match('GET', '/health') is None
        assert table.match('GET', '/openapi.yaml') is None
        assert table.match('GET', '/orders/o-1/details') is None


class TestAggregatedSpec:
    def test_aggregated_spec_is_valid_yaml_with_all_services(self, contracts):
        aggregated = yaml.safe_load(gateway_app._build_aggregated_spec(contracts))
        assert aggregated['openapi'] == '3.0.3'
        assert aggregated['info']['title'] == 'DashEat Platform API'
        paths = aggregated['paths']
        assert '/orders' in paths
        assert '/ratings' in paths
        assert '/customers/register' in paths
        assert '/deliveries' in paths
        assert '/orders/{order_id}/details' in paths

    def test_aggregated_spec_has_no_unresolved_refs(self, contracts):
        aggregated = gateway_app._build_aggregated_spec(contracts)
        assert '$ref' not in aggregated

    def test_per_service_health_paths_excluded(self, contracts):
        aggregated = yaml.safe_load(gateway_app._build_aggregated_spec(contracts))
        health = aggregated['paths']['/health']
        assert health['get']['tags'] == ['Gateway']

    def test_tags_merged_without_duplicates(self, contracts):
        aggregated = yaml.safe_load(gateway_app._build_aggregated_spec(contracts))
        names = [tag['name'] for tag in aggregated['tags']]
        assert len(names) == len(set(names))
        assert 'Orders' in names and 'Gateway' in names
