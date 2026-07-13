import json
import logging

logger = logging.getLogger(__name__)


def setup_consumers(broker, service):
    """Consume rating.created events to update the restaurant's average rating."""

    try:
        exchange = "rating.events"
        queue = "restaurant.update_rating"
        routing_key = "rating.created"

        broker.declare_exchange(exchange, "topic")
        broker.declare_queue(queue, durable=True)
        broker.bind_queue(queue, exchange, routing_key)

        def callback(ch, method, properties, body):
            try:
                event = json.loads(body)
                service.on_rating_created(event)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logging.exception(f"Failed to process rating.created: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        broker.subscribe_event(queue, callback)
        logger.info(f"Subscribed to {queue} ({exchange}: {routing_key})")
    except Exception as e:
        logger.warning(f"Could not set up rating consumer: {e}")
