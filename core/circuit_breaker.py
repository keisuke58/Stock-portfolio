"""
Circuit breaker pattern for external service calls.

Prevents cascading failures by failing fast when a service is unhealthy,
and automatically recovering when the service becomes available again.

States:
- CLOSED: Normal operation, requests go through
- OPEN: Service unhealthy, requests fail immediately
- HALF_OPEN: Testing if service recovered
"""
import time
import logging
import threading
from enum import Enum
from typing import Callable, Optional, TypeVar, Any
from functools import wraps
from dataclasses import dataclass

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitOpenError(Exception):
    """Raised when circuit is open and calls are rejected."""

    def __init__(self, message: str, circuit_name: str = ""):
        super().__init__(message)
        self.circuit_name = circuit_name


@dataclass
class CircuitStats:
    """Statistics for circuit breaker monitoring."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    current_state: CircuitState = CircuitState.CLOSED
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    Usage:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)

        try:
            result = breaker.call(external_api_call, arg1, arg2)
        except CircuitOpenError:
            # Handle circuit open (use fallback, etc.)
            pass

    Or as a decorator:
        @circuit_breaker(failure_threshold=5)
        def call_external_api():
            ...
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exception: type = Exception,
        name: str = ""
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again
            expected_exception: Exception type to count as failure
            name: Optional name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name or f"circuit_{id(self)}"

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._lock = threading.RLock()
        self._stats = CircuitStats()

    @property
    def state(self) -> CircuitState:
        """Get current state, checking if recovery timeout has passed."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._last_failure_time is not None:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.recovery_timeout:
                        logger.info(
                            f"[{self.name}] Circuit transitioning to HALF_OPEN "
                            f"after {elapsed:.1f}s"
                        )
                        self._state = CircuitState.HALF_OPEN
            return self._state

    @property
    def stats(self) -> CircuitStats:
        """Get circuit statistics."""
        with self._lock:
            self._stats.current_state = self._state
            self._stats.last_failure_time = self._last_failure_time
            self._stats.last_success_time = self._last_success_time
            return self._stats

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function

        Returns:
            Function result

        Raises:
            CircuitOpenError: If circuit is open
            Exception: If function raises and circuit trips
        """
        current_state = self.state

        with self._lock:
            self._stats.total_calls += 1

        if current_state == CircuitState.OPEN:
            with self._lock:
                self._stats.rejected_calls += 1
            raise CircuitOpenError(
                f"Circuit [{self.name}] is open, rejecting call to {func.__name__}",
                circuit_name=self.name
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure(e)
            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        with self._lock:
            self._failure_count = 0
            self._last_success_time = time.time()
            self._stats.successful_calls += 1

            if self._state == CircuitState.HALF_OPEN:
                logger.info(
                    f"[{self.name}] Circuit closing after successful test call"
                )
                self._state = CircuitState.CLOSED

    def _on_failure(self, exception: Exception) -> None:
        """Handle failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            self._stats.failed_calls += 1

            logger.warning(
                f"[{self.name}] Failure {self._failure_count}/{self.failure_threshold}: "
                f"{type(exception).__name__}: {exception}"
            )

            if self._failure_count >= self.failure_threshold:
                if self._state != CircuitState.OPEN:
                    logger.error(
                        f"[{self.name}] Circuit opening after {self._failure_count} failures"
                    )
                self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Manually reset circuit to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            logger.info(f"[{self.name}] Circuit manually reset")

    def force_open(self) -> None:
        """Manually open the circuit."""
        with self._lock:
            self._state = CircuitState.OPEN
            self._last_failure_time = time.time()
            logger.info(f"[{self.name}] Circuit manually opened")


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    expected_exception: type = Exception,
    name: str = ""
) -> Callable:
    """
    Decorator for circuit breaker pattern.

    Args:
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before trying again
        expected_exception: Exception type to count as failure
        name: Optional circuit name

    Returns:
        Decorated function

    Example:
        @circuit_breaker(failure_threshold=3, recovery_timeout=30)
        def call_external_api():
            response = requests.get("https://api.example.com")
            return response.json()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            name=name or func.__name__
        )

        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return breaker.call(func, *args, **kwargs)

        # Expose the breaker for testing/monitoring
        wrapper.circuit_breaker = breaker
        return wrapper

    return decorator


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Useful for monitoring and coordinating circuits across the application.
    """

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def register(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0
    ) -> CircuitBreaker:
        """Register or get a circuit breaker by name."""
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    name=name
                )
            return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name."""
        with self._lock:
            return self._breakers.get(name)

    def get_all_stats(self) -> dict[str, CircuitStats]:
        """Get stats for all registered breakers."""
        with self._lock:
            return {name: breaker.stats for name, breaker in self._breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuits to closed state."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()


# Global registry for application-wide circuit breakers
circuit_registry = CircuitBreakerRegistry()


# Pre-configured circuit breakers for common services
def get_yahoo_circuit() -> CircuitBreaker:
    """Get circuit breaker for Yahoo Finance API."""
    return circuit_registry.register(
        "yahoo_finance",
        failure_threshold=5,
        recovery_timeout=60.0
    )


def get_coingecko_circuit() -> CircuitBreaker:
    """Get circuit breaker for CoinGecko API."""
    return circuit_registry.register(
        "coingecko",
        failure_threshold=3,  # More sensitive due to rate limits
        recovery_timeout=120.0  # Longer recovery for rate limits
    )


def get_discord_circuit() -> CircuitBreaker:
    """Get circuit breaker for Discord webhook."""
    return circuit_registry.register(
        "discord",
        failure_threshold=3,
        recovery_timeout=30.0
    )
