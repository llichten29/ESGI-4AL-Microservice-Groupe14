import os

class Config:
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
    RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', '5672'))
    SERVICE_PORT = int(os.getenv('SERVICE_PORT', '8000'))

    ORDER_SERVICE_URL = os.getenv('ORDER_SERVICE_URL', 'http://order-service:8001')
    RESTAURANT_SERVICE_URL = os.getenv('RESTAURANT_SERVICE_URL', 'http://restaurant-service:8002')
    CATALOG_SERVICE_URL = os.getenv('CATALOG_SERVICE_URL', 'http://catalog-service:8003')
    PAYMENT_SERVICE_URL = os.getenv('PAYMENT_SERVICE_URL', 'http://payment-service:8004')
    DELIVERY_SERVICE_URL = os.getenv('DELIVERY_SERVICE_URL', 'http://delivery-service:8005')
    NOTIFICATION_SERVICE_URL = os.getenv('NOTIFICATION_SERVICE_URL', 'http://notification-service:8006')
    RATING_SERVICE_URL = os.getenv('RATING_SERVICE_URL', 'http://rating-service:8007')
    CUSTOMER_SERVICE_URL = os.getenv('CUSTOMER_SERVICE_URL', 'http://customer-service:8008')
    DELIVERER_SERVICE_URL = os.getenv('DELIVERER_SERVICE_URL', 'http://deliverer-service:8009')
