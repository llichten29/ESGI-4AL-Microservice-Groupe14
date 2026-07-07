import sys
import os

_services_base = os.path.join(os.path.dirname(__file__), '..', 'main')
_conflicting_modules = ['domain', 'application', 'infrastructure', 'interfaces']

sys.path.insert(0, os.path.join(_services_base, 'shared'))

from unittest.mock import MagicMock
import pytest


def pytest_runtest_setup(item):
    test_path = str(item.fspath)
    if 'restaurant-service' in test_path:
        _service_path = os.path.join(_services_base, 'restaurant-service')
        _other_keys = ['customer-service', 'order-service', 'delivery-service']
    elif 'customer-service' in test_path:
        _service_path = os.path.join(_services_base, 'customer-service')
        _other_keys = ['restaurant-service', 'order-service', 'delivery-service']
    else:
        return

    for p in sys.path[:]:
        if any(k in p for k in _other_keys):
            sys.path.remove(p)
    sys.path.insert(0, _service_path)

    for mod in list(sys.modules.keys()):
        parts = mod.split('.')
        if parts[0] in _conflicting_modules:
            sys.modules.pop(mod, None)


@pytest.fixture
def mock_broker():
    return MagicMock()
