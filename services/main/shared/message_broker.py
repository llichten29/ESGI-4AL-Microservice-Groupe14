import json
import os
import pika
import logging
from typing import Callable, Dict, Any

logger = logging.getLogger(__name__)

class MessageBroker:
    def __init__(self, host: str = 'localhost', port: int = 5672, user: str = 'guest', password: str | None = None):
        self.host = host
        self.port = port
        self.user = user
        self.password = password or os.environ.get('RABBITMQ_PASSWORD', 'guest')
        self.connection = None
        self.channel = None
        self.consumers = {}

    def connect(self):
        try:
            credentials = pika.PlainCredentials(self.user, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                connection_attempts=3,
                retry_delay=2
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            logger.info(f"Connected to RabbitMQ at {self.host}:{self.port}")
        except Exception as e:
            logging.exception(f"Failed to connect to RabbitMQ: {e}")
            raise

    def declare_exchange(self, exchange: str, exchange_type: str = 'topic'):
        try:
            self.channel.exchange_declare(exchange=exchange, exchange_type=exchange_type, durable=True)
            logger.info(f"Exchange declared: {exchange}")
        except Exception as e:
            logging.exception(f"Failed to declare exchange {exchange}: {e}")
            raise

    def declare_queue(self, queue: str, durable: bool = True):
        try:
            self.channel.queue_declare(queue=queue, durable=durable)
            logger.info(f"Queue declared: {queue}")
        except Exception as e:
            logging.exception(f"Failed to declare queue {queue}: {e}")
            raise

    def bind_queue(self, queue: str, exchange: str, routing_key: str):
        try:
            self.channel.queue_bind(queue=queue, exchange=exchange, routing_key=routing_key)
            logger.info(f"Queue {queue} bound to {exchange} with key {routing_key}")
        except Exception as e:
            logging.exception(f"Failed to bind queue: {e}")
            raise

    def publish_event(self, exchange: str, routing_key: str, event_data: Dict[str, Any]):
        try:
            message = json.dumps(event_data)
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=message,
                properties=pika.BasicProperties(delivery_mode=2, content_type='application/json')
            )
            logger.info(f"Event published: {routing_key}")
        except Exception as e:
            logging.exception(f"Failed to publish event: {e}")
            raise

    def subscribe_event(self, queue: str, callback: Callable):
        try:
            self.channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=False)
            logger.info(f"Subscribed to queue: {queue}")
        except Exception as e:
            logging.exception(f"Failed to subscribe to queue: {e}")
            raise

    def start_consuming(self):
        try:
            logger.info("Starting to consume messages...")
            self.channel.start_consuming()
        except Exception as e:
            logging.exception(f"Error consuming messages: {e}")
            raise

    def close(self):
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Disconnected from RabbitMQ")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
