import json
import logging

logger = logging.getLogger(__name__)


def setup_consumers(broker, service):
    logger.info("Setting up consumer for order.events exchange")

    try:
        exchange = "order.events"
        queue = "customer.order_history"
        routing_key = "order.created"

        broker.declare_exchange(exchange, "topic")
        broker.declare_queue(queue, durable=True)
        broker.bind_queue(queue, exchange, routing_key)

        def on_order_created(ch, method, properties, body):
            try:
                event = json.loads(body)
                logger.info(f"OrderCreated received: {event.get('orderId')}")
                service.add_order_ref(event.get("customerId"), {
                    "order_id": event.get("orderId"),
                    "status": "CREATED",
                    "total": event.get("totalPrice", 0),
                    "date": event.get("timestamp", ""),
                    "restaurant_name": event.get("restaurantName", "")
                })
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Failed to process OrderCreated: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        broker.subscribe_event(queue, on_order_created)
        logger.info(f"Subscribed to {queue}")
    except Exception as e:
        logger.warning(f"Could not set up event consumers: {e}")
