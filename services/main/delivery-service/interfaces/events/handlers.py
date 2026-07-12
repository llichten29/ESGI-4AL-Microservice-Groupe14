import logging
import json

logger = logging.getLogger(__name__)


class DeliveryEventHandlers:
    def __init__(self, delivery_service):
        self.delivery_service = delivery_service
        self.exchange = "delivery.events"
        self.queues = {}

    def setup_consumers(self, broker):
        broker.declare_exchange(self.exchange)
        broker.declare_exchange("order.events")

        queue_name = "delivery-order-events"
        broker.declare_queue(queue_name)
        broker.bind_queue(queue_name, "order.events", "order.ready")
        broker.subscribe_event(queue_name, self._on_order_ready)
        self.queues["order_ready"] = queue_name

    def _on_order_ready(self, channel, method, properties, body):
        try:
            event = json.loads(body)
            order_id = event.get("order_id", "")
            if not order_id:
                logger.warning("order.ready event missing order_id")
                channel.basic_ack(delivery_tag=method.delivery_tag)
                return
            logger.info(f"Order ready, assigning deliverer for {order_id}")
            self.delivery_service.assign_deliverer(
                order_id=order_id,
                customer_id=event.get("customer_id", ""),
                restaurant_id=event.get("restaurant_id", "")
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.exception(f"Error handling order.ready: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
