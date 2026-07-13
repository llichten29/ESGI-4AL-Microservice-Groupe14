import pytest
from unittest.mock import MagicMock

from retry import retry_with_backoff


class TestRetryWithBackoff:
    def test_returns_result_on_first_success(self):
        sleep = MagicMock()
        func = MagicMock(return_value=42)
        wrapped = retry_with_backoff(sleep=sleep)(func)
        assert wrapped() == 42
        func.assert_called_once()
        sleep.assert_not_called()

    def test_retries_with_exponential_delays(self):
        sleep = MagicMock()
        func = MagicMock(side_effect=[ConnectionError("down"), ConnectionError("down"), "ok"])
        wrapped = retry_with_backoff(max_retries=3, base_delay=1.0, multiplier=2.0, sleep=sleep)(func)
        assert wrapped() == "ok"
        assert func.call_count == 3
        assert [call.args[0] for call in sleep.call_args_list] == [1.0, 2.0]

    def test_raises_after_max_retries(self):
        sleep = MagicMock()
        func = MagicMock(side_effect=ConnectionError("down"))
        wrapped = retry_with_backoff(max_retries=3, sleep=sleep)(func)
        with pytest.raises(ConnectionError):
            wrapped()
        assert func.call_count == 4
        assert [call.args[0] for call in sleep.call_args_list] == [1.0, 2.0, 4.0]

    def test_does_not_retry_unexpected_exceptions(self):
        sleep = MagicMock()
        func = MagicMock(side_effect=ValueError("bad input"))
        wrapped = retry_with_backoff(exceptions=(ConnectionError,), sleep=sleep)(func)
        with pytest.raises(ValueError):
            wrapped()
        func.assert_called_once()
        sleep.assert_not_called()

    def test_passes_arguments_through(self):
        sleep = MagicMock()

        @retry_with_backoff(sleep=sleep)
        def add(a, b=0):
            return a + b

        assert add(40, b=2) == 42
