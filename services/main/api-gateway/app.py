import os
import re
import sys
import logging
import threading

import yaml

from flask import Flask, jsonify, send_from_directory, Response
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

SWAGGER_UI = """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>FoodDelivery API - Documentation</title>
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


def _load_routing_table(openapi_path: str, app: Flask) -> RoutingTable:
    if not os.path.exists(openapi_path):
        logger.warning("OpenAPI spec not found at %s, using empty routing table", openapi_path)
        return RoutingTable()

    with open(openapi_path, 'r') as f:
        spec = yaml.safe_load(f)

    table = RoutingTable()
    paths = spec.get('paths', {})

    for path, path_item in paths.items():
        if path in GATEWAY_HANDLED_PATHS:
            continue
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

    logger.info("Routing table loaded with %d rule(s) from OpenAPI spec", len(table._rules))
    return table


def _build_service_urls(app: Flask) -> dict:
    return {
        'order': app.config.get('ORDER_SERVICE_URL', 'http://order-service:8001'),
        'restaurant': app.config.get('RESTAURANT_SERVICE_URL', 'http://restaurant-service:8002'),
        'catalog': app.config.get('CATALOG_SERVICE_URL', 'http://catalog-service:8003'),
    }


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    CORS(app)

    openapi_path = os.environ.get(
        'OPENAPI_SPEC_PATH',
        os.path.join(_BASE, 'openapi.yaml'),
    )
    app.config['OPENAPI_SPEC_PATH'] = openapi_path

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "healthy", "service": "api-gateway"})

    @app.route('/openapi.yaml', methods=['GET'])
    def openapi_spec():
        spec_dir = os.path.dirname(app.config['OPENAPI_SPEC_PATH'])
        spec_file = os.path.basename(app.config['OPENAPI_SPEC_PATH'])
        return send_from_directory(spec_dir, spec_file, mimetype='application/yaml')

    @app.route('/docs', methods=['GET'])
    def docs():
        return Response(SWAGGER_UI, mimetype='text/html')

    routing_table = _load_routing_table(openapi_path, app)
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

    _start_event_consumers(app, gateway_service)

    return app


def _start_event_consumers(app: Flask, gateway_service: GatewayService):
    try:
        broker = MessageBroker(
            host=app.config.get('RABBITMQ_HOST', 'rabbitmq'),
            port=app.config.get('RABBITMQ_PORT', 5672),
        )
        broker.connect()
        setup_consumers(broker, gateway_service)
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
