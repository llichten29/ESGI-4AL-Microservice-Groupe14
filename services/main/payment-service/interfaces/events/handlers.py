import json
import logging

from domain.models import PaymentException

logger = logging.getLogger(__name__)


def setup_consumers(broker, service):
    """Consume order.created and trigger the payment step of the order SAGA."""
    logger.info("Setting up consumer for order.events exchange")

    try:
        exchange = "order.events"
        queue = "payment.process_payment"
        routing_key = "order.created"

        broker.declare_exchange(exchange, "topic")
        broker.declare_queue(queue, durable=True)
        broker.bind_queue(queue, exchange, routing_key)

        def on_order_created(ch, method, properties, body):
            try:
                event = json.loads(body)
                logger.info(f"OrderCreated received: {event.get('orderId')}")
                payment_data = event.get("payment") or {}
                try:
                    service.process_payment({
                        "order_id": event.get("orderId"),
                        "customer_id": event.get("customerId"),
                        "amount": event.get("totalPrice", 0),
                        "payment_method": payment_data.get("method", "CARD"),
                        "card_token": payment_data.get("cardToken", "")
                    })
                except PaymentException as e:
                    # Business failure (declined, gateway down): the SAGA continues via
                    # the payment.failed event already published - ack, do not requeue.
                    logger.warning(f"Payment for order {event.get('orderId')} failed: {e.message}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logging.exception(f"Failed to process OrderCreated: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        broker.subscribe_event(queue, on_order_created)
        logger.info(f"Subscribed to {queue}")
    except Exception as e:
        logger.warning(f"Could not set up event consumers: {e}")
