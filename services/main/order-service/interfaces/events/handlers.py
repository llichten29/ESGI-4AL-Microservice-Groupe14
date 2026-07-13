import json
import logging

logger = logging.getLogger(__name__)


def setup_consumers(broker, service):
    """Bind the SAGA reaction queues: payment results, restaurant decisions, delivery updates."""

    def _consume(queue, exchange, bindings, dispatch):
        broker.declare_exchange(exchange, "topic")
        broker.declare_queue(queue, durable=True)
        for routing_key in bindings:
            broker.bind_queue(queue, exchange, routing_key)

        def callback(ch, method, properties, body):
            try:
                event = json.loads(body)
                handler = dispatch.get(method.routing_key)
                if handler:
                    handler(event)
                else:
                    logger.warning(f"No handler for routing key {method.routing_key}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logging.exception(f"Failed to process {method.routing_key}: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        broker.subscribe_event(queue, callback)
        logger.info(f"Subscribed to {queue} ({exchange}: {', '.join(bindings)})")

    try:
        _consume(
            queue="order.payment_results",
            exchange="payment.events",
            bindings=["payment.processed", "payment.failed"],
            dispatch={
                "payment.processed": service.on_payment_processed,
                "payment.failed": service.on_payment_failed
            }
        )

        # restaurant.events uses PascalCase routing keys (existing convention
        # of restaurant-service) with snake_case payloads.
        _consume(
            queue="order.restaurant_updates",
            exchange="restaurant.events",
            bindings=["OrderAccepted", "OrderRejected", "OrderPreparing", "OrderReady"],
            dispatch={
                "OrderAccepted": service.on_order_accepted,
                "OrderRejected": service.on_order_rejected,
                "OrderPreparing": service.on_order_preparing,
                "OrderReady": service.on_order_ready
            }
        )

        _consume(
            queue="order.delivery_updates",
            exchange="delivery.events",
            bindings=["delivery.assigned", "delivery.in_progress", "delivery.completed"],
            dispatch={
                "delivery.assigned": service.on_delivery_assigned,
                "delivery.in_progress": service.on_delivery_in_progress,
                "delivery.completed": service.on_delivery_completed
            }
        )
    except Exception as e:
        logger.warning(f"Could not set up event consumers: {e}")
