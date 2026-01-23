"""
Dependency injection container for managing service instances.

Provides a simple, lightweight DI container for:
- Service registration and resolution
- Singleton/transient lifecycle management
- Factory-based lazy initialization
- Testing support (easy mocking)
"""
from typing import Dict, Any, Callable, Optional, Type, TypeVar, Generic
import logging
import threading

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceContainer:
    """
    Simple dependency injection container.

    Manages service lifecycle and dependencies with support for:
    - Singleton services (created once, reused)
    - Transient services (created each time)
    - Factory functions for lazy initialization

    Example:
        container = ServiceContainer()

        # Register services
        container.register(PriceCache, PriceCache)
        container.register(
            YahooFetcher,
            lambda: YahooFetcher(container.resolve(PriceCache))
        )

        # Resolve services
        fetcher = container.resolve(YahooFetcher)
    """

    def __init__(self):
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._singletons: Dict[Type, Any] = {}
        self._singleton_types: set = set()
        self._lock = threading.RLock()

    def register(
        self,
        service_type: Type[T],
        factory: Callable[[], T],
        singleton: bool = True
    ) -> 'ServiceContainer':
        """
        Register a service factory.

        Args:
            service_type: The type/interface to register
            factory: Factory function to create instances
            singleton: Whether to cache the instance (default: True)

        Returns:
            Self for method chaining

        Example:
            container.register(PriceCache, lambda: PriceCache('cache.db'))
            container.register(YahooFetcher, YahooFetcher)  # Class as factory
        """
        with self._lock:
            self._factories[service_type] = factory
            if singleton:
                self._singleton_types.add(service_type)
            elif service_type in self._singleton_types:
                self._singleton_types.remove(service_type)

            logger.debug(
                f"Registered {service_type.__name__} "
                f"(singleton={singleton})"
            )
        return self

    def register_instance(
        self,
        service_type: Type[T],
        instance: T
    ) -> 'ServiceContainer':
        """
        Register an existing instance as a singleton.

        Args:
            service_type: The type/interface to register
            instance: The instance to use

        Returns:
            Self for method chaining

        Example:
            cache = PriceCache('cache.db')
            container.register_instance(PriceCache, cache)
        """
        with self._lock:
            self._singletons[service_type] = instance
            self._singleton_types.add(service_type)
            self._factories[service_type] = lambda: instance

            logger.debug(f"Registered instance of {service_type.__name__}")
        return self

    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service instance.

        Args:
            service_type: The type/interface to resolve

        Returns:
            Service instance

        Raises:
            KeyError: If service is not registered
        """
        with self._lock:
            if service_type not in self._factories:
                raise KeyError(
                    f"Service {service_type.__name__} not registered. "
                    f"Available: {[t.__name__ for t in self._factories.keys()]}"
                )

            # Return cached singleton if available
            if service_type in self._singleton_types:
                if service_type not in self._singletons:
                    self._singletons[service_type] = self._factories[service_type]()
                    logger.debug(f"Created singleton {service_type.__name__}")
                return self._singletons[service_type]

            # Create transient instance
            return self._factories[service_type]()

    def try_resolve(self, service_type: Type[T]) -> Optional[T]:
        """
        Try to resolve a service, returning None if not registered.

        Args:
            service_type: The type/interface to resolve

        Returns:
            Service instance or None
        """
        try:
            return self.resolve(service_type)
        except KeyError:
            return None

    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        return service_type in self._factories

    def reset(self) -> None:
        """Reset all singleton instances (useful for testing)."""
        with self._lock:
            self._singletons.clear()
            logger.debug("Container singletons reset")

    def clear(self) -> None:
        """Clear all registrations and instances."""
        with self._lock:
            self._factories.clear()
            self._singletons.clear()
            self._singleton_types.clear()
            logger.debug("Container cleared")

    def get_registered_types(self) -> list:
        """Get list of all registered service types."""
        return list(self._factories.keys())


# Global container instance
container = ServiceContainer()


def setup_container(config: Dict[str, Any]) -> ServiceContainer:
    """
    Configure the service container with all dependencies.

    This is the main setup function that wires up all services.
    Call this once at application startup.

    Args:
        config: Application configuration dictionary

    Returns:
        Configured container
    """
    from cache import PriceCache
    from fetchers import YahooFetcher, CoinGeckoFetcher
    from state_store import StateStore
    from signals.state_machine import StateMachine

    # Clear any existing registrations
    container.reset()

    # Register cache
    container.register(PriceCache, PriceCache, singleton=True)

    # Register fetchers
    container.register(
        YahooFetcher,
        lambda: YahooFetcher(container.resolve(PriceCache)),
        singleton=True
    )
    container.register(
        CoinGeckoFetcher,
        lambda: CoinGeckoFetcher(container.resolve(PriceCache)),
        singleton=True
    )

    # Register state machine
    container.register(
        StateMachine,
        lambda: StateMachine(
            container.resolve(YahooFetcher),
            container.resolve(CoinGeckoFetcher)
        ),
        singleton=True
    )

    # Register state store
    container.register(StateStore, StateStore, singleton=True)

    # Register notifiers based on config
    _register_notifiers(config)

    logger.info(
        f"Container setup complete with {len(container.get_registered_types())} services"
    )
    return container


def _register_notifiers(config: Dict[str, Any]) -> None:
    """Register notifier services based on config."""
    from notifiers import DiscordNotifier, SlackNotifier, GmailNotifier, LineNotifier

    notifiers = []

    # Discord
    webhook = config.get('webhook')
    if webhook:
        notifiers.append(DiscordNotifier(webhook))
        logger.debug("Discord notifier registered")

    # Line
    line_token = config.get('line_token')
    if line_token:
        notifiers.append(LineNotifier(line_token))
        logger.debug("Line notifier registered")

    # Slack
    slack_webhook = config.get('slack_webhook')
    if slack_webhook:
        notifiers.append(SlackNotifier(slack_webhook))
        logger.debug("Slack notifier registered")

    # Gmail
    gmail_user = config.get('gmail_user')
    gmail_password = config.get('gmail_password')
    gmail_to = config.get('gmail_to')
    if gmail_user and gmail_password and gmail_to:
        notifiers.append(GmailNotifier(gmail_user, gmail_password, gmail_to))
        logger.debug("Gmail notifier registered")

    # Register notifier list
    container.register_instance(list, notifiers)


def get_container() -> ServiceContainer:
    """Get the global container instance."""
    return container


# ============================================================================
# Convenience functions for common services
# ============================================================================

def get_yahoo_fetcher() -> 'YahooFetcher':
    """Get the Yahoo Finance fetcher."""
    from fetchers import YahooFetcher
    return container.resolve(YahooFetcher)


def get_coingecko_fetcher() -> 'CoinGeckoFetcher':
    """Get the CoinGecko fetcher."""
    from fetchers import CoinGeckoFetcher
    return container.resolve(CoinGeckoFetcher)


def get_state_machine() -> 'StateMachine':
    """Get the state machine."""
    from signals.state_machine import StateMachine
    return container.resolve(StateMachine)


def get_state_store() -> 'StateStore':
    """Get the state store."""
    from state_store import StateStore
    return container.resolve(StateStore)


def get_notifiers() -> list:
    """Get the list of configured notifiers."""
    return container.resolve(list)
