import pytest
from unittest.mock import MagicMock


def _published(mock_broker):
    return [call.kwargs["routing_key"] for call in mock_broker.publish_event.call_args_list]


class TestCreateOrder:
    def test_creates_order_with_computed_total(self, order_service, order_payload):
        order = order_service.create_order(order_payload)
        assert order.status == "CREATED"
        assert order.saga_state == "PAYMENT_PENDING"
        # 2 x 12.50 + 1 x 6.00 + 2.99 delivery fee
        assert order.total_price == 33.99
        assert order.restaurant_name == "Chez Testeur"

    def test_validates_at_restaurant_before_creating(self, order_service, order_payload, restaurant_client):
        order_service.create_order(order_payload)
        restaurant_client.validate_order.assert_called_once_with(
            "resto-1", order_payload["items"]
        )

    def test_publishes_order_created_in_camel_case(self, order_service, order_payload, mock_broker):
        order = order_service.create_order(order_payload)
        kwargs = mock_broker.publish_event.call_args.kwargs
        assert kwargs["exchange"] == "order.events"
        assert kwargs["routing_key"] == "order.created"
        event = kwargs["event_data"]
        assert event["orderId"] == order.id
        assert event["customerId"] == "cust-1"
        assert event["totalPrice"] == 33.99
        assert event["restaurantName"] == "Chez Testeur"
        assert event["payment"] == {"method": "CARD", "cardToken": "card_ok"}

    def test_rejects_order_refused_by_restaurant(self, order_service, order_payload, restaurant_client, models):
        restaurant_client.validate_order.return_value = {"isValid": False, "reason": "Dish not in stock"}
        with pytest.raises(models.InvalidOrder):
            order_service.create_order(order_payload)

    def test_rejects_empty_order(self, order_service, order_payload, models):
        order_payload["items"] = []
        with pytest.raises(models.InvalidOrder):
            order_service.create_order(order_payload)

    def test_open_circuit_breaker_fails_fast_with_503(self, order_service, order_payload, restaurant_client, models):
        from main.shared.circuit_breaker import CircuitBreakerException
        restaurant_client.validate_order.side_effect = CircuitBreakerException("OPEN")
        with pytest.raises(models.RestaurantUnavailable) as exc:
            order_service.create_order(order_payload)
        assert exc.value.status_code == 503

    def test_restaurant_network_failure_maps_to_503(self, order_service, order_payload, restaurant_client, models):
        restaurant_client.validate_order.side_effect = ConnectionError("down")
        with pytest.raises(models.RestaurantUnavailable):
            order_service.create_order(order_payload)


class TestSagaNominalFlow:
    def test_full_happy_path(self, order_service, order_payload, mock_broker):
        order = order_service.create_order(order_payload)

        order_service.on_payment_processed({"order_id": order.id, "payment_id": "pay-1"})
        assert order.status == "PAID"
        assert order.payment_id == "pay-1"
        assert order.saga_state == "AWAITING_ACCEPTANCE"

        order_service.on_order_accepted({"order_id": order.id})
        assert order.status == "CONFIRMED"

        order_service.on_order_preparing({"order_id": order.id})
        assert order.status == "PREPARING"

        order_service.on_order_ready({"order_id": order.id})
        assert order.status == "READY"
        assert order.saga_state == "READY_FOR_DELIVERY"

        order_service.on_delivery_assigned({"order_id": order.id, "delivery_id": "del-1"})
        assert order.status == "ASSIGNED"
        assert order.delivery_id == "del-1"

        order_service.on_delivery_in_progress({"order_id": order.id})
        assert order.status == "DELIVERING"

        order_service.on_delivery_completed({"order_id": order.id})
        assert order.status == "DELIVERED"
        assert order.saga_state == "COMPLETED"

        assert _published(mock_broker) == [
            "order.created", "order.confirmed", "order.delivered"
        ]

    def test_payment_processed_is_idempotent(self, order_service, order_payload, mock_broker):
        order = order_service.create_order(order_payload)
        order_service.on_payment_processed({"order_id": order.id, "payment_id": "pay-1"})
        order_service.on_payment_processed({"order_id": order.id, "payment_id": "pay-2"})
        assert order.payment_id == "pay-1"
        assert _published(mock_broker).count("order.confirmed") == 1

    def test_ignores_events_for_unknown_orders(self, order_service):
        order_service.on_payment_processed({"order_id": "ghost", "payment_id": "pay-1"})
        order_service.on_delivery_completed({"order_id": "ghost"})


class TestSagaCompensations:
    def test_payment_failed_cancels_order(self, order_service, order_payload, mock_broker):
        order = order_service.create_order(order_payload)
        order_service.on_payment_failed({"order_id": order.id, "reason": "Card declined"})

        assert order.status == "CANCELLED"
        assert order.saga_state == "COMPENSATED"
        assert "Card declined" in order.cancellation_reason
        assert _published(mock_broker) == ["order.created", "order.cancelled"]

    def test_restaurant_rejection_refunds_payment(self, order_service, order_payload, payment_client, mock_broker):
        order = order_service.create_order(order_payload)
        order_service.on_payment_processed({"order_id": order.id, "payment_id": "pay-1"})

        order_service.on_order_rejected({"order_id": order.id, "reason": "TOO_BUSY"})

        payment_client.refund.assert_called_once()
        assert payment_client.refund.call_args.args[0] == "pay-1"
        assert order.status == "CANCELLED"
        assert order.saga_state == "COMPENSATED"
        assert _published(mock_broker) == ["order.created", "order.confirmed", "order.cancelled"]

    def test_failed_refund_marks_saga_failed(self, order_service, order_payload, payment_client):
        payment_client.refund.side_effect = ConnectionError("payment down")
        order = order_service.create_order(order_payload)
        order_service.on_payment_processed({"order_id": order.id, "payment_id": "pay-1"})

        order_service.on_order_rejected({"order_id": order.id, "reason": "TOO_BUSY"})

        assert order.status == "CANCELLED"
        assert any(s.state == "FAILED" for s in order.saga_history)

    def test_rejection_is_idempotent(self, order_service, order_payload, payment_client):
        order = order_service.create_order(order_payload)
        order_service.on_payment_processed({"order_id": order.id, "payment_id": "pay-1"})
        order_service.on_order_rejected({"order_id": order.id, "reason": "TOO_BUSY"})
        order_service.on_order_rejected({"order_id": order.id, "reason": "TOO_BUSY"})
        payment_client.refund.assert_called_once()


class TestCancellation:
    def test_customer_can_cancel_created_order(self, order_service, order_payload):
        order = order_service.create_order(order_payload)
        cancelled = order_service.cancel_order(order.id)
        assert cancelled.status == "CANCELLED"

    def test_cancel_paid_order_triggers_refund(self, order_service, order_payload, payment_client):
        order = order_service.create_order(order_payload)
        order_service.on_payment_processed({"order_id": order.id, "payment_id": "pay-1"})
        order_service.cancel_order(order.id)
        payment_client.refund.assert_called_once()

    def test_cannot_cancel_order_in_preparation(self, order_service, order_payload, models):
        order = order_service.create_order(order_payload)
        order_service.on_payment_processed({"order_id": order.id, "payment_id": "pay-1"})
        order_service.on_order_accepted({"order_id": order.id})
        with pytest.raises(models.CancellationNotAllowed):
            order_service.cancel_order(order.id)


class TestCircuitBreakerStates:
    def test_exposes_both_breakers(self, order_service):
        states = order_service.get_circuit_breakers()
        assert len(states) == 2
        assert {s["name"] for s in states} == {"order->restaurant", "order->payment"}
