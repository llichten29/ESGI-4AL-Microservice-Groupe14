import json
from unittest.mock import MagicMock


def _setup(broker, service):
    from interfaces.events.handlers import setup_consumers
    setup_consumers(broker, service)


class TestNotificationEventHandlers:
    def test_binds_three_wildcard_queues(self):
        broker, service = MagicMock(), MagicMock()
        _setup(broker, service)
        bindings = {(c.args[0], c.args[1], c.args[2]) for c in broker.bind_queue.call_args_list}
        assert ("notification.order_events", "order.events", "order.#") in bindings
        assert ("notification.payment_events", "payment.events", "payment.#") in bindings
        assert ("notification.delivery_events", "delivery.events", "delivery.#") in bindings

    def test_callback_forwards_routing_key_and_event(self):
        broker, service = MagicMock(), MagicMock()
        _setup(broker, service)
        callback = broker.subscribe_event.call_args_list[0].args[1]

        ch, method = MagicMock(), MagicMock()
        method.delivery_tag = 1
        method.routing_key = "order.created"
        event = {"orderId": "order-1", "customerId": "cust-1"}
        callback(ch, method, None, json.dumps(event))

        service.on_event.assert_called_once_with("order.created", event)
        ch.basic_ack.assert_called_once_with(delivery_tag=1)

    def test_failure_nacks_with_requeue(self):
        broker, service = MagicMock(), MagicMock()
        service.on_event.side_effect = RuntimeError("boom")
        _setup(broker, service)
        callback = broker.subscribe_event.call_args_list[0].args[1]

        ch, method = MagicMock(), MagicMock()
        method.delivery_tag = 2
        method.routing_key = "order.created"
        callback(ch, method, None, json.dumps({}))

        ch.basic_nack.assert_called_once_with(delivery_tag=2, requeue=True)
