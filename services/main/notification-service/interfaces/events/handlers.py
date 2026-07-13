import json
import logging

logger = logging.getLogger(__name__)


def setup_consumers(broker, service):
    """One queue per source exchange, bound with wildcard routing keys."""

    def _consume(queue, exchange, pattern):
        broker.declare_exchange(exchange, "topic")
        broker.declare_queue(queue, durable=True)
        broker.bind_queue(queue, exchange, pattern)

        def callback(ch, method, properties, body):
            try:
                event = json.loads(body)
                service.on_event(method.routing_key, event)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logging.exception(f"Failed to process {method.routing_key}: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        broker.subscribe_event(queue, callback)
        logger.info(f"Subscribed to {queue} ({exchange}: {pattern})")

    try:
        _consume("notification.order_events", "order.events", "order.#")
        _consume("notification.payment_events", "payment.events", "payment.#")
        _consume("notification.delivery_events", "delivery.events", "delivery.#")
    except Exception as e:
        logger.warning(f"Could not set up event consumers: {e}")
