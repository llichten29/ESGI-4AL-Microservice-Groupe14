import pytest


class TestDelivererRegistration:
    def test_register_deliverer(self, deliverer_service):
        deliverer = deliverer_service.register_deliverer({"name": "Marco", "vehicle": "SCOOTER"})
        assert deliverer.status == "AVAILABLE"
        assert deliverer_service.get_deliverer(deliverer.id).name == "Marco"

    def test_get_unknown_raises_404(self, deliverer_service, models):
        with pytest.raises(models.DelivererNotFound):
            deliverer_service.get_deliverer("ghost")


class TestAvailability:
    def test_set_availability(self, deliverer_service):
        deliverer = deliverer_service.register_deliverer({"name": "Marco"})
        updated = deliverer_service.set_availability(deliverer.id, "OFFLINE")
        assert updated.status == "OFFLINE"

    def test_invalid_availability_rejected(self, deliverer_service, models):
        deliverer = deliverer_service.register_deliverer({"name": "Marco"})
        with pytest.raises(models.DeliveryException) as exc:
            deliverer_service.set_availability(deliverer.id, "NAPPING")
        assert exc.value.status_code == 422

    def test_availability_change_publishes_event(self, deliverer_service, mock_broker):
        deliverer = deliverer_service.register_deliverer({"name": "Marco"})
        mock_broker.publish_event.reset_mock()
        deliverer_service.set_availability(deliverer.id, "AVAILABLE")
        published = [c.kwargs["routing_key"] for c in mock_broker.publish_event.call_args_list]
        assert "deliverer.availability_changed" in published


class TestAssignRelease:
    def test_assign_available_returns_deliverer(self, deliverer_service):
        deliverer_service.register_deliverer({"name": "Marco"})
        deliverer_service.register_deliverer({"name": "Sophie", "vehicle": "CAR"})

        result = deliverer_service.assign_available()
        assert result["id"]
        assert result["name"] == "Marco"
        assert deliverer_service.get_deliverer(result["id"]).status == "BUSY"

    def test_assign_when_none_available(self, deliverer_service):
        result = deliverer_service.assign_available()
        assert result == {}

    def test_release_marks_available(self, deliverer_service):
        deliverer = deliverer_service.register_deliverer({"name": "Marco"})
        deliverer_service.assign_available()

        released = deliverer_service.release_deliverer(deliverer.id)
        assert released.status == "AVAILABLE"

    def test_release_publishes_event(self, deliverer_service, mock_broker):
        deliverer = deliverer_service.register_deliverer({"name": "Marco"})
        mock_broker.publish_event.reset_mock()
        deliverer_service.release_deliverer(deliverer.id)
        published = [c.kwargs["routing_key"] for c in mock_broker.publish_event.call_args_list]
        assert "deliverer.availability_changed" in published
