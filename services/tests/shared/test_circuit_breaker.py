import time
from unittest.mock import patch, MagicMock
import pytest
from circuit_breaker import CircuitBreaker, CircuitBreakerException, CircuitState, circuit_breaker


class TestCircuitBreakerInitialState:
    def test_initial_state_is_closed(self):
        cb = CircuitBreaker(name="test")
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0

    def test_custom_parameters(self):
        cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=60, success_threshold=3)
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 60
        assert cb.success_threshold == 3


class TestCircuitBreakerCall:
    def test_executes_function_when_closed(self):
        cb = CircuitBreaker(name="test")
        result = cb.call(lambda x: x + 1, 41)
        assert result == 42

    def test_raises_when_open(self):
        cb = CircuitBreaker(name="test", failure_threshold=1)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        with pytest.raises(CircuitBreakerException, match="is OPEN"):
            cb.call(lambda: "should not run")

    def test_does_not_catch_unrelated_exceptions(self):
        cb = CircuitBreaker(name="test", expected_exception=ValueError)
        with pytest.raises(TypeError):
            cb.call(lambda: (_ for _ in ()).throw(TypeError("unexpected")))


class TestCircuitBreakerTransitions:
    def test_transitions_to_open_after_failure_threshold(self):
        cb = CircuitBreaker(name="test", failure_threshold=3)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=10)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitState.OPEN

        with patch.object(time, 'time', return_value=time.time() + 15):
            assert cb._should_attempt_reset() is True
            cb.call(lambda: "success")
            assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_goes_back_to_open(self):
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=10, success_threshold=1)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitState.OPEN

        with patch.object(time, 'time', return_value=time.time() + 15):
            with pytest.raises(RuntimeError, match="fail"):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
            assert cb.state == CircuitState.OPEN

    def test_stays_closed_on_success(self):
        cb = CircuitBreaker(name="test", failure_threshold=3)
        cb.call(lambda: "ok")
        cb.call(lambda: "ok")
        cb.call(lambda: "ok")
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_multiple_successes_in_half_open_close_circuit(self):
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=10, success_threshold=2)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitState.OPEN

        with patch.object(time, 'time', return_value=time.time() + 15):
            cb.call(lambda: "first")
            assert cb.state == CircuitState.HALF_OPEN
            assert cb.success_count == 1
            cb.call(lambda: "second")
            assert cb.state == CircuitState.CLOSED


class TestCircuitBreakerGetState:
    def test_get_state_returns_dict(self):
        cb = CircuitBreaker(name="test", failure_threshold=3)
        state = cb.get_state()
        assert state["name"] == "test"
        assert state["state"] == "CLOSED"
        assert state["failure_count"] == 0
        assert state["failure_threshold"] == 3
        assert state["opened_at"] is None

    def test_get_state_after_open(self):
        cb = CircuitBreaker(name="test", failure_threshold=1)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        state = cb.get_state()
        assert state["state"] == "OPEN"
        assert state["opened_at"] is not None


class TestCircuitBreakerDecorator:
    def test_decorator_wraps_function(self):
        @circuit_breaker(name="decorated", failure_threshold=2)
        def risky(x):
            if x < 0:
                raise ValueError("negative")
            return x

        assert risky(5) == 5
        assert risky.circuit_breaker.state == CircuitState.CLOSED

    def test_decorator_opens_after_threshold(self):
        @circuit_breaker(name="decorated", failure_threshold=2)
        def failing():
            raise RuntimeError("always fails")

        for _ in range(2):
            with pytest.raises(RuntimeError):
                failing()
        assert failing.circuit_breaker.state == CircuitState.OPEN
