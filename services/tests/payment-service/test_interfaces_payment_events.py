import json
from unittest.mock import MagicMock


def _setup_consumers():
    from interfaces.events.handlers import setup_consumers
    return setup_consumers


def _order_created_body(card_token="card_ok"):
    return json.dumps({
        "orderId": "order-1",
        "customerId": "cust-1",
        "totalPrice": 35.5,
        "payment": {"method": "CARD", "cardToken": card_token}
    })


class TestPaymentEventHandlers:
    def test_setup_consumers_binds_order_created(self):
        broker = MagicMock()
        service = MagicMock()
        _setup_consumers()(broker, service)
        broker.declare_exchange.assert_called_once_with("order.events", "topic")
        broker.declare_queue.assert_called_once_with("payment.process_payment", durable=True)
        broker.bind_queue.assert_called_once_with("payment.process_payment", "order.events", "order.created")
        broker.subscribe_event.assert_called_once()

    def test_on_order_created_processes_payment(self):
        broker = MagicMock()
        service = MagicMock()
        _setup_consumers()(broker, service)
        callback = broker.subscribe_event.call_args[0][1]

        ch, method = MagicMock(), MagicMock()
        method.delivery_tag = 1
        callback(ch, method, None, _order_created_body())

        service.process_payment.assert_called_once_with({
            "order_id": "order-1",
            "customer_id": "cust-1",
            "amount": 35.5,
            "payment_method": "CARD",
            "card_token": "card_ok"
        })
        ch.basic_ack.assert_called_once_with(delivery_tag=1)

    def test_business_failure_still_acks(self, models):
        broker = MagicMock()
        service = MagicMock()
        service.process_payment.side_effect = models.PaymentDeclined("declined")
        _setup_consumers()(broker, service)
        callback = broker.subscribe_event.call_args[0][1]

        ch, method = MagicMock(), MagicMock()
        method.delivery_tag = 2
        callback(ch, method, None, _order_created_body("card_declined"))

        ch.basic_ack.assert_called_once_with(delivery_tag=2)
        ch.basic_nack.assert_not_called()

    def test_unexpected_failure_nacks_with_requeue(self):
        broker = MagicMock()
        service = MagicMock()
        service.process_payment.side_effect = RuntimeError("boom")
        _setup_consumers()(broker, service)
        callback = broker.subscribe_event.call_args[0][1]

        ch, method = MagicMock(), MagicMock()
        method.delivery_tag = 3
        callback(ch, method, None, _order_created_body())

        ch.basic_nack.assert_called_once_with(delivery_tag=3, requeue=True)
