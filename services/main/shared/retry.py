import logging
import time
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    multiplier: float = 2.0,
    exceptions: tuple = (Exception,),
    sleep: Callable[[float], None] = time.sleep
):
    """Retry with exponential backoff: delays of base_delay * multiplier^attempt (1s, 2s, 4s by default)."""
    def decorator(func: Callable) -> Callable:
        func_name = getattr(func, '__name__', repr(func))

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    if attempt >= max_retries:
                        logger.exception(
                            "'%s' failed after %d retries", func_name, max_retries
                        )
                        raise
                    delay = base_delay * (multiplier ** attempt)
                    logger.warning(
                        "'%s' attempt %d/%d failed, retrying in %.1fs",
                        func_name, attempt + 1, max_retries + 1, delay
                    )
                    sleep(delay)
        return wrapper
    return decorator
