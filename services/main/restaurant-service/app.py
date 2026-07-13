import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import logging
import threading
from flask import Flask, jsonify
from flask_cors import CORS

from infrastructure.repositories import InMemoryRestaurantRepository
from application.restaurant_service import RestaurantService
from interfaces.http.routes import routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    CORS(app, resources={r"/*": {"origins": ["http://localhost:8000"]}})

    repo = InMemoryRestaurantRepository()

    broker = None
    if app.config.get('RABBITMQ_HOST'):
        try:
            from main.shared.message_broker import MessageBroker
            broker = MessageBroker(
                host=app.config['RABBITMQ_HOST'],
                port=app.config['RABBITMQ_PORT'],
                user=app.config['RABBITMQ_USER'],
                password=app.config['RABBITMQ_PASSWORD']
            )
            broker.connect()
            broker.declare_exchange(app.config['RABBITMQ_EXCHANGE'])
            logger.info("Message broker connected successfully")
        except Exception as e:
            logger.warning(f"Message broker unavailable, running without events: {e}")

    service = RestaurantService(repository=repo, broker=broker)
    app.restaurant_service = service

    if broker:
        try:
            from main.shared.message_broker import MessageBroker
            from interfaces.events.handlers import setup_consumers
            consumer_broker = MessageBroker(
                host=app.config['RABBITMQ_HOST'],
                port=app.config['RABBITMQ_PORT'],
                user=app.config['RABBITMQ_USER'],
                password=app.config['RABBITMQ_PASSWORD']
            )
            consumer_broker.connect()
            setup_consumers(consumer_broker, service)
            threading.Thread(
                target=consumer_broker.start_consuming,
                daemon=True,
                name="restaurant-event-consumer"
            ).start()
            logger.info("Restaurant event consumers started")
        except Exception as e:
            logger.warning(f"Could not start event consumers: {e}")

    app.register_blueprint(routes)

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "healthy", "service": "restaurant-service"})

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "Internal server error"}), 500

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=app.config.get('SERVICE_PORT', 8002), debug=app.config.get('DEBUG', False))
