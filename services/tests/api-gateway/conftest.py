import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../main/api-gateway'))

import pytest
from domain.models import RouteRule, RouteMatch
from domain.routing import RoutingTable
from infrastructure.service_client import ServiceClient
from application.gateway_service import GatewayService


@pytest.fixture
def routing_table():
    rt = RoutingTable()
    rt.add_rule(RouteRule('/orders', 'POST', 'http://order-service:8001', 15))
    rt.add_rule(RouteRule('/orders/<order_id>', 'GET', 'http://order-service:8001', 10))
    rt.add_rule(RouteRule('/restaurants/search', 'GET', 'http://catalog-service:8003', 5))
    rt.add_rule(RouteRule('/restaurants/<restaurant_id>', 'GET', 'http://restaurant-service:8002', 10))
    rt.add_rule(RouteRule('/restaurants/<restaurant_id>/orders/<order_id>/accept', 'POST', 'http://restaurant-service:8002', 10))
    return rt


@pytest.fixture
def service_client():
    return ServiceClient(base_url='')


@pytest.fixture
def gateway_service(routing_table, service_client):
    service_urls = {
        'order': 'http://order-service:8001',
        'restaurant': 'http://restaurant-service:8002',
        'catalog': 'http://catalog-service:8003',
    }
    return GatewayService(routing_table, service_client, service_urls=service_urls)


@pytest.fixture
def app():
    from flask import Flask
    from unittest.mock import MagicMock
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.gateway_service = MagicMock()
    return app
