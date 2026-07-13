import os


class Config:
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    SERVICE_PORT = int(os.getenv('SERVICE_PORT', '8001'))
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', '5672'))
    RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
    RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'guest')
    RABBITMQ_EXCHANGE = os.getenv('RABBITMQ_EXCHANGE', 'order.events')
    RESTAURANT_SERVICE_URL = os.getenv('RESTAURANT_SERVICE_URL', 'http://localhost:8002')
    PAYMENT_SERVICE_URL = os.getenv('PAYMENT_SERVICE_URL', 'http://localhost:8004')
    DELIVERY_SERVICE_URL = os.getenv('DELIVERY_SERVICE_URL', 'http://localhost:8005')
