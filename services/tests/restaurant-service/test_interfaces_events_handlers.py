import json
from unittest.mock import MagicMock

from interfaces.events.handlers import setup_consumers


class TestRestaurantEventHandlers:
    def test_setup_consumers_binds_rating_created(self):
        broker = MagicMock()
        service = MagicMock()
        setup_consumers(broker, service)
        broker.declare_exchange.assert_called_once_with("rating.events", "topic")
        broker.declare_queue.assert_called_once_with("restaurant.update_rating", durable=True)
        broker.bind_queue.assert_called_once_with(
            "restaurant.update_rating", "rating.events", "rating.created"
        )

    def test_callback_dispatches_to_service(self):
        broker = MagicMock()
        service = MagicMock()
        setup_consumers(broker, service)
        callback = broker.subscribe_event.call_args[0][1]

        ch, method = MagicMock(), MagicMock()
        method.delivery_tag = 1
        method.routing_key = "rating.created"
        event = {"entity_type": "RESTAURANT", "entity_id": "rest-1", "average_score": 4.5, "review_count": 10}
        callback(ch, method, None, json.dumps(event))

        service.on_rating_created.assert_called_once_with(event)
        ch.basic_ack.assert_called_once_with(delivery_tag=1)

    def test_failure_nacks_with_requeue(self):
        broker = MagicMock()
        service = MagicMock()
        service.on_rating_created.side_effect = RuntimeError("boom")
        setup_consumers(broker, service)
        callback = broker.subscribe_event.call_args[0][1]

        ch, method = MagicMock(), MagicMock()
        method.delivery_tag = 2
        method.routing_key = "rating.created"
        callback(ch, method, None, json.dumps({}))

        ch.basic_nack.assert_called_once_with(delivery_tag=2, requeue=True)
