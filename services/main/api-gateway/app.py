import os
import re
import sys
import logging
import threading

import yaml

from flask import Flask, jsonify, Response
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, '..', '..'))

from domain.models import RouteRule
from domain.routing import RoutingTable
from infrastructure.service_client import ServiceClient
from application.gateway_service import GatewayService
from interfaces.http.routes import routes
from interfaces.events.handlers import setup_consumers
from main.shared.message_broker import MessageBroker
from main.shared.openapi_validator import load_spec, resolve_refs

SWAGGER_UI = """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>DashEat API - Documentation</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css"/>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.onload = () => SwaggerUIBundle({
      url: '/openapi.yaml',
      dom_id: '#swagger-ui'
    });
  </script>
</body>
</html>"""

TAG_SERVICE_MAP = {
    'Customers': 'CUSTOMER_SERVICE_URL',
    'Restaurants': 'RESTAURANT_SERVICE_URL',
    'Catalog': 'CATALOG_SERVICE_URL',
    'Orders': 'ORDER_SERVICE_URL',
    'Payments': 'PAYMENT_SERVICE_URL',
    'Deliveries': 'DELIVERY_SERVICE_URL',
    'Deliverers': 'DELIVERER_SERVICE_URL',
    'Notifications': 'NOTIFICATION_SERVICE_URL',
    'Ratings': 'RATING_SERVICE_URL',
}

GATEWAY_HANDLED_PATHS = frozenset({
    '/health', '/docs', '/openapi.yaml', '/orders/{order_id}/details',
})

GATEWAY_CONTRACT = 'api-gateway.openapi.yaml'


def _load_contracts(spec_dir: str) -> list:
    if not os.path.isdir(spec_dir):
        logger.warning("OpenAPI contracts directory not found at %s", spec_dir)
        return []
    contracts = []
    for filename in sorted(os.listdir(spec_dir)):
        if filename.endswith('.openapi.yaml'):
            contracts.append((filename, load_spec(os.path.join(spec_dir, filename))))
    logger.info("Loaded %d OpenAPI contract(s) from %s", len(contracts), spec_dir)
    return contracts


def _load_routing_table(contracts: list, app: Flask) -> RoutingTable:
    table = RoutingTable()
    for filename, spec in contracts:
        if filename == GATEWAY_CONTRACT:
            continue
        for path, path_item in spec.get('paths', {}).items():
            if path in GATEWAY_HANDLED_PATHS:
                continue
            _add_path_operations(path, path_item, app, table)
    logger.info("Routing table loaded with %d rule(s) from OpenAPI contracts", len(table._rules))
    return table


def _build_aggregated_spec(contracts: list) -> str:
    aggregated = {
        'openapi': '3.0.3',
        'info': {'title': 'DashEat Platform API', 'version': '1.0.0'},
        'servers': [{'url': 'http://localhost:8000'}],
        'tags': [],
        'paths': {},
    }
    for filename, spec in contracts:
        if filename == GATEWAY_CONTRACT:
            aggregated['openapi'] = spec.get('openapi', aggregated['openapi'])
            aggregated['info'] = spec.get('info', aggregated['info'])
            aggregated['servers'] = spec.get('servers', aggregated['servers'])
            break
    for filename, spec in contracts:
        resolved = resolve_refs(spec, spec, convert_nullable=False)
        known_tags = {tag.get('name') for tag in aggregated['tags']}
        for tag in resolved.get('tags', []):
            if tag.get('name') not in known_tags:
                aggregated['tags'].append(tag)
        for path, path_item in resolved.get('paths', {}).items():
            if filename != GATEWAY_CONTRACT and path in GATEWAY_HANDLED_PATHS:
                continue
            aggregated['paths'].setdefault(path, path_item)
    return yaml.safe_dump(aggregated, sort_keys=False, allow_unicode=True)


def _add_path_operations(path: str, path_item: dict, app: Flask, table: RoutingTable):
    for method in ('get', 'post', 'put', 'patch', 'delete'):
        operation = path_item.get(method)
        if not operation:
            continue
        tags = operation.get('tags', [])
        if not tags:
            continue
        config_key = TAG_SERVICE_MAP.get(tags[0])
        if not config_key:
            continue
        service_url = app.config.get(config_key)
        if not service_url:
            logger.warning("No URL configured for %s (%s)", tags[0], config_key)
            continue

        path_pattern = re.sub(r'\{(\w+)\}', r'<\1>', path)
        rule = RouteRule(
            path_pattern=path_pattern,
            method=method.upper(),
            service_url=service_url,
            timeout=10.0,
        )
        table.add_rule(rule)


def _build_service_urls(app: Flask) -> dict:
    return {
        'order': app.config.get('ORDER_SERVICE_URL', 'http://order-service:8001'),
        'restaurant': app.config.get('RESTAURANT_SERVICE_URL', 'http://restaurant-service:8002'),
        'catalog': app.config.get('CATALOG_SERVICE_URL', 'http://catalog-service:8003'),
    }


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    CORS(app, resources={r"/*": {"origins": app.config['CORS_ALLOWED_ORIGINS']}})

    spec_dir = os.environ.get(
        'OPENAPI_SPEC_DIR',
        os.path.join(_BASE, '..', '..', 'ressources', 'endpoints'),
    )
    app.config['OPENAPI_SPEC_DIR'] = spec_dir
    contracts = _load_contracts(spec_dir)
    aggregated_spec = _build_aggregated_spec(contracts)

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "healthy", "service": "api-gateway"})

    @app.route('/openapi.yaml', methods=['GET'])
    def openapi_spec():
        return Response(aggregated_spec, mimetype='application/yaml')

    @app.route('/docs', methods=['GET'])
    def docs():
        return Response(SWAGGER_UI, mimetype='text/html')

    routing_table = _load_routing_table(contracts, app)
    service_client = ServiceClient(base_url='')
    gateway_service = GatewayService(
        routing_table=routing_table,
        service_client=service_client,
        service_urls=_build_service_urls(app),
    )
    app.gateway_service = gateway_service

    app.register_blueprint(routes)

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "Internal server error"}), 500

    _start_event_consumers(app)

    return app


def _start_event_consumers(app: Flask):
    try:
        broker = MessageBroker(
            host=app.config.get('RABBITMQ_HOST', 'rabbitmq'),
            port=app.config.get('RABBITMQ_PORT', 5672),
        )
        broker.connect()
        setup_consumers(broker)
        thread = threading.Thread(target=broker.start_consuming, daemon=True)
        thread.start()
        logger.info("Event consumers started")
    except Exception as e:
        logger.warning("Failed to start event consumers: %s", e)


if __name__ == '__main__':
    application = create_app()
    application.run(
        host='0.0.0.0',
        port=application.config.get('SERVICE_PORT', 8000),
        debug=application.config.get('DEBUG', False),
    )
