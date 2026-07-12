import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import logging
import threading
from flask import Flask, jsonify
from flask_cors import CORS

from infrastructure.repositories import MongoDBDelivererRepository
from application.deliverer_service import DelivererService
from interfaces.http.routes import routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    CORS(app, resources={r"/*": {"origins": ["http://localhost:8000"]}})

    repo = MongoDBDelivererRepository(app.config['MONGODB_URL'])

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
            broker = None

    service = DelivererService(repository=repo, broker=broker)
    app.deliverer_service = service

    app.register_blueprint(routes)

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "healthy", "service": "deliverer-service"})

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "Internal server error"}), 500

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=app.config.get('SERVICE_PORT', 8009), debug=app.config.get('DEBUG', False))
