import pytest


class TestAssignDeliverer:
    def test_assign_available_returns_delivery(self, delivery_service, mock_broker):
        delivery = delivery_service.assign_deliverer(
            order_id="order-1",
            customer_id="cust-1",
            restaurant_id="rest-1"
        )
        assert delivery.order_id == "order-1"
        assert delivery.deliverer_id == "del-1"
        assert delivery.deliverer_name == "John"
        assert delivery.status == "ASSIGNED"
        assert delivery.assigned_at != ""
        assert len(mock_broker.published_events) == 1
        assert mock_broker.published_events[0]["routing_key"] == "delivery.assigned"

    def test_assign_no_deliverer_raises(self, repo, mock_client_unavailable, mock_broker, models):
        mock_client_unavailable.available = False
        from application.delivery_service import DeliveryService
        svc = DeliveryService(repository=repo, deliverer_client=mock_client_unavailable, broker=mock_broker)
        with pytest.raises(models.DeliveryException) as exc:
            svc.assign_deliverer(order_id="order-1")
        assert exc.value.status_code == 503
        assert exc.value.code == "NO_DELIVERER_AVAILABLE"

    def test_assign_does_not_publish_without_broker(self, delivery_service_no_broker):
        delivery = delivery_service_no_broker.assign_deliverer(order_id="order-1")
        assert delivery.status == "ASSIGNED"


class TestGetDelivery:
    def test_get_by_id_returns_delivery(self, delivery_service):
        created = delivery_service.assign_deliverer(order_id="order-1")
        found = delivery_service.get_delivery(created.id)
        assert found.id == created.id
        assert found.order_id == "order-1"

    def test_get_unknown_raises_404(self, delivery_service, models):
        with pytest.raises(models.DeliveryNotFound):
            delivery_service.get_delivery("unknown")

    def test_get_by_order(self, delivery_service):
        created = delivery_service.assign_deliverer(order_id="order-42")
        found = delivery_service.get_delivery_by_order("order-42")
        assert found.id == created.id

    def test_get_by_unknown_order_raises(self, delivery_service, models):
        with pytest.raises(models.DeliveryNotFound):
            delivery_service.get_delivery_by_order("no-such-order")


class TestUpdateLocation:
    def test_update_location_sets_in_transit(self, delivery_service, mock_broker):
        created = delivery_service.assign_deliverer(order_id="order-1")
        loc = {"lat": 48.8566, "lng": 2.3522}
        updated = delivery_service.update_location(created.id, loc)
        assert updated.status == "IN_TRANSIT"
        assert updated.location == loc
        assert mock_broker.published_events[-1]["routing_key"] == "delivery.in_transit"

    def test_update_location_on_delivered_raises(self, delivery_service, models):
        created = delivery_service.assign_deliverer(order_id="order-1")
        delivery_service.update_location(created.id, {"lat": 1, "lng": 2})
        delivery_service.confirm_delivery(created.id)
        with pytest.raises(models.DeliveryException) as exc:
            delivery_service.update_location(created.id, {"lat": 3, "lng": 4})
        assert exc.value.status_code == 422


class TestConfirmDelivery:
    def test_confirm_delivery_success(self, delivery_service, mock_broker, mock_client):
        created = delivery_service.assign_deliverer(order_id="order-1")
        confirmed = delivery_service.confirm_delivery(created.id)
        assert confirmed.status == "DELIVERED"
        assert confirmed.delivered_at != ""
        assert mock_client.released == "del-1"
        assert mock_broker.published_events[-1]["routing_key"] == "delivery.completed"

    def test_confirm_already_delivered_raises(self, delivery_service, models):
        created = delivery_service.assign_deliverer(order_id="order-1")
        delivery_service.confirm_delivery(created.id)
        with pytest.raises(models.DeliveryException) as exc:
            delivery_service.confirm_delivery(created.id)
        assert exc.value.status_code == 422


class TestFailDelivery:
    def test_fail_releases_deliverer(self, delivery_service, mock_broker, mock_client):
        created = delivery_service.assign_deliverer(order_id="order-1")
        failed = delivery_service.fail_delivery(created.id, reason="Accident")
        assert failed.status == "FAILED"
        assert mock_client.released == "del-1"
        assert mock_broker.published_events[-1]["routing_key"] == "delivery.failed"
