import json
import logging

logger = logging.getLogger(__name__)

QUEUE_ORDER_EVENTS = 'gateway.order.events'
QUEUE_RESTAURANT_EVENTS = 'gateway.restaurant.events'


def setup_consumers(broker):
    broker.declare_exchange('order.events')
    broker.declare_exchange('restaurant.events')

    broker.declare_queue(QUEUE_ORDER_EVENTS)
    broker.bind_queue(QUEUE_ORDER_EVENTS, 'order.events', 'order.#')
    broker.subscribe_event(QUEUE_ORDER_EVENTS, lambda ch, method, body: _handle_order_event(ch, method, body))

    broker.declare_queue(QUEUE_RESTAURANT_EVENTS)
    broker.bind_queue(QUEUE_RESTAURANT_EVENTS, 'restaurant.events', 'Order*')
    broker.subscribe_event(QUEUE_RESTAURANT_EVENTS, lambda ch, method, body: _handle_restaurant_event(ch, method, body))


def _handle_order_event(ch, method, body):
    try:
        event = json.loads(body)
        logger.info("Order event received: %s - %s", method.routing_key, event)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        logger.exception("Error handling order event")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def _handle_restaurant_event(ch, method, body):
    try:
        event = json.loads(body)
        logger.info("Restaurant event received: %s - %s", method.routing_key, event)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        logger.exception("Error handling restaurant event")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
