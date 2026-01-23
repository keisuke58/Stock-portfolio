"""
Protocol definitions for dependency injection and interface contracts.

These protocols define the expected interfaces for key components,
enabling type checking, testing with mocks, and dependency injection.
"""
from typing import Protocol, Optional, List, Tuple, Dict, Any, runtime_checkable
from datetime import datetime


@runtime_checkable
class PriceFetcher(Protocol):
    """
    Protocol for price data fetchers.

    Implementations: YahooFetcher, CoinGeckoFetcher
    """

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetch current price for a symbol.

        Args:
            symbol: Asset symbol (e.g., 'AAPL', 'BTC')

        Returns:
            Current price as float, or None if unavailable
        """
        ...

    def get_historical_prices(
        self,
        symbol: str,
        days: int = 30
    ) -> Optional[List[Tuple[datetime, float]]]:
        """
        Fetch historical prices for a symbol.

        Args:
            symbol: Asset symbol
            days: Number of days of history to fetch

        Returns:
            List of (datetime, price) tuples, or None if unavailable
        """
        ...


@runtime_checkable
class Notifier(Protocol):
    """
    Protocol for notification services.

    Implementations: DiscordNotifier, SlackNotifier, LineNotifier, GmailNotifier
    """

    def send(self, message: str) -> bool:
        """
        Send a raw message.

        Args:
            message: Message content to send

        Returns:
            True if sent successfully, False otherwise
        """
        ...

    def notify_state_change(
        self,
        symbol: str,
        old_state: Optional[str],
        new_state: str,
        price: float
    ) -> bool:
        """
        Notify about state change.

        Args:
            symbol: Asset symbol
            old_state: Previous state (None if new)
            new_state: Current state
            price: Current price

        Returns:
            True if notification sent successfully
        """
        ...

    def notify_daily_pick(self, daily_pick: Dict[str, Any]) -> bool:
        """
        Notify about daily pick.

        Args:
            daily_pick: Daily pick data dictionary

        Returns:
            True if notification sent successfully
        """
        ...


@runtime_checkable
class CacheProvider(Protocol):
    """
    Protocol for cache implementations.

    Implementations: PriceCache (SQLite-based)
    """

    def get(self, symbol: str, cache_type: str) -> Optional[Dict]:
        """
        Get cached data.

        Args:
            symbol: Asset symbol
            cache_type: Type of cache ('current', 'historical', 'metrics')

        Returns:
            Cached data dict or None if not cached/expired
        """
        ...

    def set(
        self,
        symbol: str,
        data: Dict,
        cache_type: str,
        ttl_seconds: int
    ) -> None:
        """
        Set cached data.

        Args:
            symbol: Asset symbol
            data: Data to cache
            cache_type: Type of cache
            ttl_seconds: Time-to-live in seconds
        """
        ...

    def delete(self, symbol: str, cache_type: str) -> None:
        """Delete cached data."""
        ...


@runtime_checkable
class StateStoreProtocol(Protocol):
    """
    Protocol for state persistence.

    Implementations: StateStore (SQLite-based)
    """

    def get_state(self, symbol: str) -> Optional[str]:
        """Get current state for a symbol."""
        ...

    def set_state(self, symbol: str, state: str, price: float) -> bool:
        """
        Set state for a symbol.

        Returns:
            True if state changed, False if unchanged
        """
        ...

    def should_notify(self, symbol: str, new_state: str) -> bool:
        """Check if notification should be sent."""
        ...

    def mark_notified(self, symbol: str, state: str) -> None:
        """Mark state as notified."""
        ...


@runtime_checkable
class Scorer(Protocol):
    """
    Protocol for scoring implementations.

    Implementations: VMSScorer
    """

    def calculate_all_scores(
        self,
        features: Dict[str, Any],
        current_state: str,
        **kwargs
    ) -> Dict[str, float]:
        """
        Calculate all scores.

        Args:
            features: Feature dictionary from FeatureCalculator
            current_state: Current asset state
            **kwargs: Additional scoring parameters

        Returns:
            Dictionary with value_score, momentum_score, stability_score, total_score
        """
        ...


@runtime_checkable
class DataIngester(Protocol):
    """
    Protocol for data ingestion services.

    Implementations: FundamentalIngester, NewsIngester, SECEdgarIngester
    """

    def get_data(self, symbol: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Get ingested data for a symbol.

        Args:
            symbol: Asset symbol
            **kwargs: Additional parameters

        Returns:
            Data dictionary or None if unavailable
        """
        ...


@runtime_checkable
class EventClassifierProtocol(Protocol):
    """
    Protocol for event classification.

    Implementations: EventClassifier
    """

    def classify_news(self, news_items: List[Dict]) -> List[Dict]:
        """Classify news items by sentiment and impact."""
        ...

    def classify_sec_filings(self, filings: List[Dict]) -> List[Dict]:
        """Classify SEC filings by type and impact."""
        ...
