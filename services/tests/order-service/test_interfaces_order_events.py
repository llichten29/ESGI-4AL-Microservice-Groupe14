import json
from unittest.mock import MagicMock, call


def _setup(broker, service):
    from interfaces.events.handlers import setup_consumers
    setup_consumers(broker, service)


def _callback_for(broker, queue):
    for c in broker.subscribe_event.call_args_list:
        if c.args[0] == queue:
            return c.args[1]
    raise AssertionError(f"No subscription for {queue}")


class TestOrderEventBindings:
    def test_declares_three_queues(self):
        broker, service = MagicMock(), MagicMock()
        _setup(broker, service)
        declared = [c.args[0] for c in broker.declare_queue.call_args_list]
        assert declared == ["order.payment_results", "order.restaurant_updates", "order.delivery_updates"]

    def test_binds_expected_routing_keys(self):
        broker, service = MagicMock(), MagicMock()
        _setup(broker, service)
        bindings = {(c.args[1], c.args[2]) for c in broker.bind_queue.call_args_list}
        assert ("payment.events", "payment.processed") in bindings
        assert ("payment.events", "payment.failed") in bindings
        assert ("restaurant.events", "OrderAccepted") in bindings
        assert ("restaurant.events", "OrderRejected") in bindings
        assert ("restaurant.events", "OrderReady") in bindings
        assert ("delivery.events", "delivery.completed") in bindings


class TestOrderEventDispatch:
    def test_payment_processed_dispatches_to_service(self):
        broker, service = MagicMock(), MagicMock()
        _setup(broker, service)
        callback = _callback_for(broker, "order.payment_results")

        ch, method = MagicMock(), MagicMock()
        method.delivery_tag = 1
        method.routing_key = "payment.processed"
        event = {"order_id": "order-1", "payment_id": "pay-1"}
        callback(ch, method, None, json.dumps(event))

        service.on_payment_processed.assert_called_once_with(event)
        ch.basic_ack.assert_called_once_with(delivery_tag=1)

    def test_restaurant_rejected_dispatches_to_service(self):
        broker, service = MagicMock(), MagicMock()
        _setup(broker, service)
        callback = _callback_for(broker, "order.restaurant_updates")

        ch, method = MagicMock(), MagicMock()
        method.delivery_tag = 2
        method.routing_key = "OrderRejected"
        event = {"order_id": "order-1", "reason": "TOO_BUSY"}
        callback(ch, method, None, json.dumps(event))

        service.on_order_rejected.assert_called_once_with(event)
        ch.basic_ack.assert_called_once_with(delivery_tag=2)

    def test_handler_failure_nacks_with_requeue(self):
        broker, service = MagicMock(), MagicMock()
        service.on_delivery_completed.side_effect = RuntimeError("boom")
        _setup(broker, service)
        callback = _callback_for(broker, "order.delivery_updates")

        ch, method = MagicMock(), MagicMock()
        method.delivery_tag = 3
        method.routing_key = "delivery.completed"
        callback(ch, method, None, json.dumps({"order_id": "order-1"}))

        ch.basic_nack.assert_called_once_with(delivery_tag=3, requeue=True)

    def test_unknown_routing_key_still_acks(self):
        broker, service = MagicMock(), MagicMock()
        _setup(broker, service)
        callback = _callback_for(broker, "order.payment_results")

        ch, method = MagicMock(), MagicMock()
        method.delivery_tag = 4
        method.routing_key = "payment.unknown"
        callback(ch, method, None, json.dumps({}))

        ch.basic_ack.assert_called_once_with(delivery_tag=4)
