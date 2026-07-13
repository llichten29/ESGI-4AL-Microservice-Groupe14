import json
from unittest.mock import MagicMock


def _setup(broker, service):
    from interfaces.events.handlers import setup_consumers
    setup_consumers(broker, service)


def _callback_for(broker, queue):
    for c in broker.subscribe_event.call_args_list:
        if c.args[0] == queue:
            return c.args[1]
    raise AssertionError(f"No subscription for {queue}")


class TestCatalogEventSetup:
    def test_declares_two_queues(self):
        broker, service = MagicMock(), MagicMock()
        _setup(broker, service)
        declared = [c.args[0] for c in broker.declare_queue.call_args_list]
        assert set(declared) == {"catalog.update_index", "catalog.update_ratings"}

    def test_binds_expected_routing_keys(self):
        broker, service = MagicMock(), MagicMock()
        _setup(broker, service)
        keys = {c.args[2] for c in broker.bind_queue.call_args_list}
        assert "RestaurantRegistered" in keys
        assert "RestaurantUpdated" in keys
        assert "RestaurantClosed" in keys
        assert "MenuUpdated" in keys
        assert "rating.created" in keys


class TestCatalogEventDispatch:
    def test_restaurant_registered_dispatches(self):
        broker, service = MagicMock(), MagicMock()
        _setup(broker, service)
        callback = _callback_for(broker, "catalog.update_index")

        ch, method = MagicMock(), MagicMock()
        method.delivery_tag = 1
        method.routing_key = "RestaurantRegistered"
        event = {"restaurant_id": "rest-1", "name": "Chez Testeur"}
        callback(ch, method, None, json.dumps(event))

        service.on_restaurant_registered.assert_called_once_with(event)
        ch.basic_ack.assert_called_once_with(delivery_tag=1)

    def test_rating_created_dispatches(self):
        broker, service = MagicMock(), MagicMock()
        _setup(broker, service)
        callback = _callback_for(broker, "catalog.update_ratings")

        ch, method = MagicMock(), MagicMock()
        method.delivery_tag = 2
        method.routing_key = "rating.created"
        event = {"entity_type": "RESTAURANT", "entity_id": "rest-1", "average_score": 4.5}
        callback(ch, method, None, json.dumps(event))

        service.on_rating_created.assert_called_once_with(event)
        ch.basic_ack.assert_called_once_with(delivery_tag=2)

    def test_handler_failure_nacks_with_requeue(self):
        broker, service = MagicMock(), MagicMock()
        service.on_restaurant_registered.side_effect = RuntimeError("boom")
        _setup(broker, service)
        callback = _callback_for(broker, "catalog.update_index")

        ch, method = MagicMock(), MagicMock()
        method.delivery_tag = 3
        method.routing_key = "RestaurantRegistered"
        callback(ch, method, None, json.dumps({}))

        ch.basic_nack.assert_called_once_with(delivery_tag=3, requeue=True)
