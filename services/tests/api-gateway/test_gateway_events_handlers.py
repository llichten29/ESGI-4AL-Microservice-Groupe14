import json
from unittest.mock import MagicMock

from interfaces.events.handlers import (
    QUEUE_ORDER_EVENTS,
    QUEUE_RESTAURANT_EVENTS,
    _handle_order_event,
    _handle_restaurant_event,
    setup_consumers,
)


class TestSetupConsumers:
    def test_declares_queues_and_subscriptions(self):
        broker = MagicMock()
        setup_consumers(broker)
        broker.declare_exchange.assert_any_call('order.events')
        broker.declare_exchange.assert_any_call('restaurant.events')
        broker.declare_queue.assert_any_call(QUEUE_ORDER_EVENTS)
        broker.declare_queue.assert_any_call(QUEUE_RESTAURANT_EVENTS)
        broker.bind_queue.assert_any_call(QUEUE_ORDER_EVENTS, 'order.events', 'order.#')
        broker.bind_queue.assert_any_call(QUEUE_RESTAURANT_EVENTS, 'restaurant.events', 'Order*')
        assert broker.subscribe_event.call_count == 2

    def test_subscribed_callbacks_are_invocable(self):
        broker = MagicMock()
        setup_consumers(broker)
        ch, method = MagicMock(), MagicMock(routing_key='order.created', delivery_tag=1)
        for call in broker.subscribe_event.call_args_list:
            callback = call.args[1]
            callback(ch, method, json.dumps({"orderId": "o1"}))
        assert ch.basic_ack.call_count == 2


class TestEventHandlers:
    def test_order_event_is_acked(self):
        ch = MagicMock()
        method = MagicMock(routing_key='order.created', delivery_tag=7)
        _handle_order_event(ch, method, json.dumps({"orderId": "o1"}))
        ch.basic_ack.assert_called_once_with(delivery_tag=7)
        ch.basic_nack.assert_not_called()

    def test_invalid_order_event_is_nacked_without_requeue(self):
        ch = MagicMock()
        method = MagicMock(routing_key='order.created', delivery_tag=8)
        _handle_order_event(ch, method, "not-json{")
        ch.basic_nack.assert_called_once_with(delivery_tag=8, requeue=False)

    def test_restaurant_event_is_acked(self):
        ch = MagicMock()
        method = MagicMock(routing_key='OrderAccepted', delivery_tag=9)
        _handle_restaurant_event(ch, method, json.dumps({"orderId": "o1"}))
        ch.basic_ack.assert_called_once_with(delivery_tag=9)

    def test_invalid_restaurant_event_is_nacked_without_requeue(self):
        ch = MagicMock()
        method = MagicMock(routing_key='OrderAccepted', delivery_tag=10)
        _handle_restaurant_event(ch, method, "not-json{")
        ch.basic_nack.assert_called_once_with(delivery_tag=10, requeue=False)
