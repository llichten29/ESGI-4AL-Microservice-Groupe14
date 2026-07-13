import sys
import os

_services_base = os.path.join(os.path.dirname(__file__), '..', 'main')
_conflicting_modules = ['domain', 'application', 'infrastructure', 'interfaces']
_service_dirs = sorted(
    d for d in os.listdir(_services_base)
    if os.path.isdir(os.path.join(_services_base, d)) and d != 'shared'
)

sys.path.insert(0, os.path.join(_services_base, 'shared'))
sys.path.insert(0, os.path.join(_services_base, '..'))

from unittest.mock import MagicMock
import pytest


def pytest_runtest_setup(item):
    test_path = str(item.fspath)
    current = next((d for d in _service_dirs if d in test_path), None)
    if not current:
        return

    _service_path = os.path.join(_services_base, current)
    _other_keys = [d for d in _service_dirs if d != current]

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
