import json


class TestDelivererEventPublishing:
    def test_register_publishes_registered_and_available(self, deliverer_service, mock_broker):
        deliverer_service.register_deliverer({"name": "Marco"})
        published = [c.kwargs["routing_key"] for c in mock_broker.publish_event.call_args_list]
        assert "deliverer.registered" in published
        assert "deliverer.availability_changed" in published

    def test_release_publishes_availability_changed(self, deliverer_service, mock_broker):
        deliverer = deliverer_service.register_deliverer({"name": "Marco"})
        mock_broker.publish_event.reset_mock()
        deliverer_service.release_deliverer(deliverer.id)
        published = [c.kwargs["routing_key"] for c in mock_broker.publish_event.call_args_list]
        assert "deliverer.availability_changed" in published
