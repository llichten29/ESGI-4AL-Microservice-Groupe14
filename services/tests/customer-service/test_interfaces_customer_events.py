from unittest.mock import MagicMock, patch
import json
from interfaces.events.handlers import setup_consumers


class TestCustomerEventHandlers:
    def test_setup_consumers_declares_exchange_and_queue(self):
        broker = MagicMock()
        service = MagicMock()
        setup_consumers(broker, service)
        broker.declare_exchange.assert_called_once_with("order.events", "topic")
        broker.declare_queue.assert_called_once_with("customer.order_history", durable=True)
        broker.bind_queue.assert_called_once_with("customer.order_history", "order.events", "order.created")
        broker.subscribe_event.assert_called_once()

    def test_on_order_created_adds_order_ref(self):
        broker = MagicMock()
        service = MagicMock()
        setup_consumers(broker, service)
        callback = broker.subscribe_event.call_args[0][1]

        ch = MagicMock()
        method = MagicMock()
        method.delivery_tag = 1
        body = json.dumps({
            "orderId": "order-123",
            "customerId": "cust-1",
            "totalPrice": 35.50,
            "timestamp": "2026-01-01T12:00:00",
            "restaurantName": "Test Restaurant"
        })

        callback(ch, method, None, body)
        service.add_order_ref.assert_called_once_with("cust-1", {
            "order_id": "order-123",
            "status": "CREATED",
            "total": 35.50,
            "date": "2026-01-01T12:00:00",
            "restaurant_name": "Test Restaurant"
        })
        ch.basic_ack.assert_called_once_with(delivery_tag=1)

    def test_on_order_created_nacks_on_failure(self):
        broker = MagicMock()
        service = MagicMock()
        service.add_order_ref.side_effect = Exception("processing failed")
        setup_consumers(broker, service)
        callback = broker.subscribe_event.call_args[0][1]

        ch = MagicMock()
        method = MagicMock()
        method.delivery_tag = 2
        body = json.dumps({"orderId": "bad-order"})

        callback(ch, method, None, body)
        ch.basic_nack.assert_called_once_with(delivery_tag=2, requeue=True)
