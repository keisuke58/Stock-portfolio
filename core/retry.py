"""
Retry utilities with exponential backoff.

Provides decorators and utilities for retrying failed operations
with configurable backoff strategies.
"""
import time
import logging
import random
from functools import wraps
from typing import Callable, Type, Tuple, Optional, TypeVar, Any
import requests

logger = logging.getLogger(__name__)

# Type variable for generic return type
T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exponential_base: Base for exponential calculation (default: 2.0)
        jitter: Add random jitter to prevent thundering herd (default: True)
        exceptions: Tuple of exceptions to retry on (default: all)
        on_retry: Optional callback called on each retry with (exception, attempt)

    Returns:
        Decorated function

    Example:
        @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
        def fetch_data(url: str) -> dict:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)

                    # Add jitter (±50%)
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    # Call on_retry callback if provided
                    if on_retry:
                        try:
                            on_retry(e, attempt)
                        except Exception as callback_error:
                            logger.warning(f"on_retry callback error: {callback_error}")

                    time.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper
    return decorator


def retry_on_network_error(
    max_retries: int = 3,
    base_delay: float = 1.0
) -> Callable:
    """
    Convenience decorator for retrying on network errors.

    Retries on:
    - requests.RequestException
    - requests.Timeout
    - requests.ConnectionError
    - ConnectionError

    Args:
        max_retries: Maximum retry attempts
        base_delay: Initial delay in seconds

    Example:
        @retry_on_network_error(max_retries=3)
        def call_api(url: str) -> dict:
            return requests.get(url).json()
    """
    return retry_with_backoff(
        max_retries=max_retries,
        base_delay=base_delay,
        exceptions=(
            requests.RequestException,
            requests.Timeout,
            requests.ConnectionError,
            ConnectionError,
            TimeoutError,
        )
    )


def retry_on_rate_limit(
    max_retries: int = 5,
    base_delay: float = 5.0,
    max_delay: float = 120.0
) -> Callable:
    """
    Convenience decorator for handling rate limiting (429 errors).

    Uses longer delays since rate limits typically require waiting.

    Args:
        max_retries: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds

    Example:
        @retry_on_rate_limit()
        def call_rate_limited_api(url: str) -> dict:
            response = requests.get(url)
            if response.status_code == 429:
                raise requests.RequestException("Rate limited")
            return response.json()
    """
    return retry_with_backoff(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=2.0,
        jitter=True,
        exceptions=(requests.RequestException,)
    )


class RetryConfig:
    """
    Configuration class for retry behavior.

    Allows passing retry configuration as an object.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        if self.jitter:
            delay = delay * (0.5 + random.random())
        return delay

    def to_decorator(
        self,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ) -> Callable:
        """Convert config to a retry decorator."""
        return retry_with_backoff(
            max_retries=self.max_retries,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            exponential_base=self.exponential_base,
            jitter=self.jitter,
            exceptions=exceptions
        )


# Pre-configured retry configs for common scenarios
NETWORK_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0
)

RATE_LIMIT_RETRY_CONFIG = RetryConfig(
    max_retries=5,
    base_delay=5.0,
    max_delay=120.0
)

AGGRESSIVE_RETRY_CONFIG = RetryConfig(
    max_retries=10,
    base_delay=0.5,
    max_delay=300.0
)


def with_retry(
    func: Callable[..., T],
    *args,
    config: RetryConfig = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs
) -> T:
    """
    Execute a function with retry logic (non-decorator version).

    Useful when you can't use a decorator (e.g., lambda or already-defined functions).

    Args:
        func: Function to execute
        *args: Arguments to pass to function
        config: RetryConfig or None for defaults
        exceptions: Exceptions to catch and retry
        **kwargs: Keyword arguments to pass to function

    Returns:
        Function result

    Example:
        result = with_retry(
            requests.get,
            "https://api.example.com/data",
            config=NETWORK_RETRY_CONFIG,
            exceptions=(requests.RequestException,),
            timeout=10
        )
    """
    config = config or RetryConfig()
    last_exception: Optional[Exception] = None

    for attempt in range(config.max_retries + 1):
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            last_exception = e

            if attempt == config.max_retries:
                logger.error(
                    f"{func.__name__} failed after {config.max_retries + 1} attempts: {e}"
                )
                raise

            delay = config.calculate_delay(attempt)
            logger.warning(
                f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                f"Retrying in {delay:.2f}s..."
            )
            time.sleep(delay)

    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected retry loop exit")
