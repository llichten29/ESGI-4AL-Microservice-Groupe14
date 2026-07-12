import pytest
import json
import sys
import os


class TestDeliveryEventHandlerSetup:
    def test_setup_declares_queues_and_bindings(self):
        from infrastructure.repositories import InMemoryDeliveryRepository
        from infrastructure.deliverer_client import DelivererClient
        from application.delivery_service import DeliveryService
        from interfaces.events.handlers import DeliveryEventHandlers

        repo = InMemoryDeliveryRepository()
        client = DelivererClient("http://test:8009")
        svc = DeliveryService(repository=repo, deliverer_client=client, broker=None)
        handlers = DeliveryEventHandlers(svc)

        class MockBroker:
            def __init__(self):
                self.declared = []
                self.queues = []
                self.bound = []
                self.subscribed = []

            def declare_exchange(self, name):
                self.declared.append(name)

            def declare_queue(self, name):
                self.queues.append(name)

            def bind_queue(self, queue, exchange, routing_key):
                self.bound.append({"queue": queue, "exchange": exchange, "routing_key": routing_key})

            def subscribe_event(self, queue, callback):
                self.subscribed.append({"queue": queue, "callback": callback})

        broker = MockBroker()
        handlers.setup_consumers(broker)

        assert "delivery.events" in broker.declared
        assert "order.events" in broker.declared
        assert "delivery-order-events" in broker.queues
        assert any(b["routing_key"] == "order.ready" for b in broker.bound)
        assert any(s["queue"] == "delivery-order-events" for s in broker.subscribed)


class TestDeliveryEventHandlerCallbacks:
    def test_on_order_ready_assigns_deliverer(self, delivery_service, mock_broker):
        from interfaces.events.handlers import DeliveryEventHandlers

        handlers = DeliveryEventHandlers(delivery_service)

        class MockChannel:
            acked = []

            def basic_ack(self, delivery_tag):
                self.acked.append(delivery_tag)

            def basic_nack(self, delivery_tag, requeue=True):
                pass

        class MockMethod:
            delivery_tag = "tag-1"

        body = json.dumps({
            "order_id": "order-ready-1",
            "customer_id": "cust-1",
            "restaurant_id": "rest-1"
        }).encode("utf-8")

        handlers._on_order_ready(MockChannel(), MockMethod(), None, body)

        delivery = delivery_service.get_delivery_by_order("order-ready-1")
        assert delivery.deliverer_id == "del-1"
        assert len(MockChannel.acked) == 1

    def test_on_order_ready_missing_order_id_acks(self):
        from infrastructure.repositories import InMemoryDeliveryRepository
        from infrastructure.deliverer_client import DelivererClient
        from application.delivery_service import DeliveryService
        from interfaces.events.handlers import DeliveryEventHandlers

        repo = InMemoryDeliveryRepository()
        client = DelivererClient("http://test:8009")
        svc = DeliveryService(repository=repo, deliverer_client=client, broker=None)
        handlers = DeliveryEventHandlers(svc)

        class MockChannel:
            acked = []

            def basic_ack(self, delivery_tag):
                self.acked.append(delivery_tag)

            def basic_nack(self, delivery_tag, requeue=True):
                pass

        class MockMethod:
            delivery_tag = "tag-2"

        body = json.dumps({"other": "data"}).encode("utf-8")
        handlers._on_order_ready(MockChannel(), MockMethod(), None, body)
        assert len(MockChannel.acked) == 1
