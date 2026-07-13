import json
import logging

logger = logging.getLogger(__name__)


def setup_consumers(broker, gateway_service):
    broker.declare_exchange('order.events')
    broker.declare_exchange('restaurant.events')

    broker.declare_queue('gateway.order.events')
    broker.bind_queue('gateway.order.events', 'order.events', 'order.#')
    broker.subscribe_event('gateway.order.events', lambda ch, method, properties, body: _handle_order_event(ch, method, properties, body, gateway_service))

    broker.declare_queue('gateway.restaurant.events')
    broker.bind_queue('gateway.restaurant.events', 'restaurant.events', 'Order*')
    broker.subscribe_event('gateway.restaurant.events', lambda ch, method, properties, body: _handle_restaurant_event(ch, method, properties, body, gateway_service))


def _handle_order_event(ch, method, properties, body, gateway_service):
    try:
        event = json.loads(body)
        logger.info(f"Order event received: {method.routing_key} - {event}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error handling order event: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def _handle_restaurant_event(ch, method, properties, body, gateway_service):
    try:
        event = json.loads(body)
        logger.info(f"Restaurant event received: {method.routing_key} - {event}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error handling restaurant event: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
