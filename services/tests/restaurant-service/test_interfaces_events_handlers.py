from unittest.mock import MagicMock
from interfaces.events.handlers import setup_consumers


class TestRestaurantEventHandlers:
    def test_setup_consumers_logs_no_consumers(self, mock_broker):
        setup_consumers(mock_broker)
        assert mock_broker.declare_exchange.call_count == 0
