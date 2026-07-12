import sys
import os

import pytest

_delivery_base = os.path.join(os.path.dirname(__file__), '..', '..', 'main', 'delivery-service')
_conflicting_modules = ['domain', 'application', 'infrastructure', 'interfaces']
for mod in list(sys.modules.keys()):
    parts = mod.split('.')
    if parts[0] in _conflicting_modules:
        sys.modules.pop(mod, None)

sys.path.insert(0, _delivery_base)


@pytest.fixture
def models():
    import domain.models as m
    return m


@pytest.fixture
def events():
    import domain.events as e
    return e


@pytest.fixture
def repo():
    from infrastructure.repositories import InMemoryDeliveryRepository
    return InMemoryDeliveryRepository()


@pytest.fixture
def mock_broker():
    class MockBroker:
        def __init__(self):
            self.published_events = []
            self.declared_exchanges = []
            self.declared_queues = []
            self.bound_queues = []
            self.subscribed_events = []

        def publish_event(self, exchange, routing_key, event_data):
            self.published_events.append({
                "exchange": exchange,
                "routing_key": routing_key,
                "event_data": event_data
            })

        def declare_exchange(self, name):
            self.declared_exchanges.append(name)

        def declare_queue(self, name):
            self.declared_queues.append(name)

        def bind_queue(self, queue, exchange, routing_key):
            self.bound_queues.append({
                "queue": queue,
                "exchange": exchange,
                "routing_key": routing_key
            })

        def subscribe_event(self, queue, callback):
            self.subscribed_events.append({"queue": queue, "callback": callback})

        def start_consuming(self):
            pass

    return MockBroker()


@pytest.fixture
def mock_client():
    from infrastructure.deliverer_client import DelivererClient

    class MockDelivererClient:
        def __init__(self):
            self.available = True
            self.deliverer_id = "del-1"
            self.deliverer_name = "John"
            self.released = None

        def assign_available(self):
            if not self.available:
                return None
            return {"id": self.deliverer_id, "name": self.deliverer_name}

        def release_deliverer(self, deliverer_id):
            self.released = deliverer_id
            return True

    return MockDelivererClient()


@pytest.fixture
def mock_client_unavailable(mock_client):
    mock_client.available = False
    return mock_client


@pytest.fixture
def delivery_service(repo, mock_client, mock_broker):
    from application.delivery_service import DeliveryService
    return DeliveryService(repository=repo, deliverer_client=mock_client, broker=mock_broker)


@pytest.fixture
def delivery_service_no_broker(repo, mock_client):
    from application.delivery_service import DeliveryService
    return DeliveryService(repository=repo, deliverer_client=mock_client, broker=None)
