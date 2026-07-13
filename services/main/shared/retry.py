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
                except exceptions as e:
                    if attempt >= max_retries:
                        logger.error(
                            f"'{func_name}' failed after {max_retries} retries: {e}"
                        )
                        raise
                    delay = base_delay * (multiplier ** attempt)
                    logger.warning(
                        f"'{func_name}' attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s"
                    )
                    sleep(delay)
        return wrapper
    return decorator
