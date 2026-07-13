import os


class Config:
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    SERVICE_PORT = int(os.getenv('SERVICE_PORT', '8005'))
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', '5672'))
    RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
    RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD')
    RABBITMQ_EXCHANGE = os.getenv('RABBITMQ_EXCHANGE', 'delivery.events')
    MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/delivery_db')
    DELIVERER_SERVICE_URL = os.getenv('DELIVERER_SERVICE_URL', 'http://deliverer-service:8009')
