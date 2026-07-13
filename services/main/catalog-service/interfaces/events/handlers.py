import json
import logging

logger = logging.getLogger(__name__)


def setup_consumers(broker, service):
    """Projects restaurant.events (PascalCase routing keys, existing convention)
    and rating.events into the search read model."""

    def _consume(queue, exchange, dispatch):
        broker.declare_exchange(exchange, "topic")
        broker.declare_queue(queue, durable=True)
        for routing_key in dispatch:
            broker.bind_queue(queue, exchange, routing_key)

        def callback(ch, method, properties, body):
            try:
                event = json.loads(body)
                handler = dispatch.get(method.routing_key)
                if handler:
                    handler(event)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logging.exception(f"Failed to process {method.routing_key}: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        broker.subscribe_event(queue, callback)
        logger.info(f"Subscribed to {queue} ({exchange})")

    try:
        _consume(
            queue="catalog.update_index",
            exchange="restaurant.events",
            dispatch={
                "RestaurantRegistered": service.on_restaurant_registered,
                "RestaurantUpdated": service.on_restaurant_updated,
                "RestaurantClosed": service.on_restaurant_closed,
                "MenuUpdated": service.on_menu_updated
            }
        )
        _consume(
            queue="catalog.update_ratings",
            exchange="rating.events",
            dispatch={"rating.created": service.on_rating_created}
        )
    except Exception as e:
        logger.warning(f"Could not set up event consumers: {e}")
