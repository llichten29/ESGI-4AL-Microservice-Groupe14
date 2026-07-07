import logging
import time
from enum import Enum
from typing import Callable, Any, Dict
from functools import wraps

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreakerException(Exception):
    pass

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        success_threshold: int = 1,
        expected_exception: Exception = Exception
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.expected_exception = expected_exception
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None

    def _should_attempt_reset(self) -> bool:
        if self.state != CircuitState.OPEN:
            return False
        if self.opened_at is None:
            return False
        elapsed = time.time() - self.opened_at
        return elapsed >= self.recovery_timeout

    def _reset(self):
        logger.info(f"Circuit Breaker '{self.name}' transitioning to HALF_OPEN")
        self.state = CircuitState.HALF_OPEN
        self.failure_count = 0
        self.success_count = 0

    def _open(self):
        logger.warning(f"Circuit Breaker '{self.name}' transitioning to OPEN")
        self.state = CircuitState.OPEN
        self.opened_at = time.time()

    def _close(self):
        logger.info(f"Circuit Breaker '{self.name}' transitioning to CLOSED")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._reset()
            else:
                raise CircuitBreakerException(
                    f"Circuit Breaker '{self.name}' is OPEN"
                )
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info(f"Circuit Breaker '{self.name}' recovered - closing circuit")
                self._close()
            else:
                logger.info(
                    f"Circuit Breaker '{self.name}' HALF_OPEN: "
                    f"{self.success_count}/{self.success_threshold} successes"
                )

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        logger.error(
            f"Circuit Breaker '{self.name}': failure {self.failure_count}/{self.failure_threshold}"
        )
        if self.failure_count >= self.failure_threshold:
            self._open()

    def get_state(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'opened_at': self.opened_at
        }

def circuit_breaker(name: str, failure_threshold: int = 5, recovery_timeout: int = 30, success_threshold: int = 1):
    def decorator(func: Callable) -> Callable:
        cb = CircuitBreaker(name=name, failure_threshold=failure_threshold, recovery_timeout=recovery_timeout, success_threshold=success_threshold)
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return cb.call(func, *args, **kwargs)
        wrapper.circuit_breaker = cb
        return wrapper
    return decorator
