"""
Base class for all fetchers with shared functionality.

Provides common cache integration, error handling, and logging setup.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Dict
from datetime import datetime
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cache import PriceCache
from core.constants import CACHE_TTL, API_TIMEOUTS


class BaseFetcher(ABC):
    """
    Abstract base class for price fetchers.

    Provides:
    - Cache integration for both current and historical prices
    - Common logging setup
    - Template methods for cache operations

    Subclasses must implement:
    - get_current_price()
    - get_historical_prices()
    """

    def __init__(self, cache: Optional[PriceCache] = None):
        """
        Initialize fetcher with optional cache.

        Args:
            cache: PriceCache instance. If None, creates a new one.
        """
        self.cache = cache or PriceCache()
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetch current price. Must be implemented by subclasses.

        Args:
            symbol: Asset symbol (e.g., 'AAPL', 'BTC')

        Returns:
            Current price as float, or None if unavailable
        """
        pass

    @abstractmethod
    def get_historical_prices(
        self,
        symbol: str,
        days: int = 30
    ) -> Optional[List[Tuple[datetime, float]]]:
        """
        Fetch historical prices. Must be implemented by subclasses.

        Args:
            symbol: Asset symbol
            days: Number of days of history to fetch

        Returns:
            List of (datetime, price) tuples sorted chronologically,
            or None if unavailable
        """
        pass

    # =========================================================================
    # Cache helper methods
    # =========================================================================

    def _get_cached_current_price(self, symbol: str) -> Optional[float]:
        """
        Check cache for current price.

        Args:
            symbol: Asset symbol

        Returns:
            Cached price or None if not cached/expired
        """
        return self.cache.get_current_price(symbol)

    def _cache_current_price(
        self,
        symbol: str,
        price: float,
        ttl_seconds: int = None
    ) -> None:
        """
        Store current price in cache.

        Args:
            symbol: Asset symbol
            price: Price to cache
            ttl_seconds: Time-to-live (defaults to CACHE_TTL.CURRENT_PRICE)
        """
        ttl = ttl_seconds or CACHE_TTL.CURRENT_PRICE
        self.cache.set_current_price(symbol, price, ttl_seconds=ttl)

    def _get_cached_historical(
        self,
        symbol: str,
        days: int = 30
    ) -> Optional[List[Tuple[datetime, float]]]:
        """
        Check cache for historical prices.

        Args:
            symbol: Asset symbol
            days: Required number of days

        Returns:
            Cached prices if sufficient data exists, None otherwise
        """
        cached = self.cache.get_historical_prices(symbol)
        if cached is not None and len(cached) >= days:
            return cached[-days:]
        return None

    def _cache_historical_prices(
        self,
        symbol: str,
        prices: List[Tuple[datetime, float]],
        ttl_seconds: int = None
    ) -> None:
        """
        Store historical prices in cache.

        Args:
            symbol: Asset symbol
            prices: List of (datetime, price) tuples
            ttl_seconds: Time-to-live (defaults to CACHE_TTL.HISTORICAL_PRICES)
        """
        ttl = ttl_seconds or CACHE_TTL.HISTORICAL_PRICES
        self.cache.set_historical_prices(symbol, prices, ttl_seconds=ttl)

    # =========================================================================
    # Utility methods
    # =========================================================================

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol for API calls.

        Default implementation uppercases. Override for different behavior.

        Args:
            symbol: Raw symbol

        Returns:
            Normalized symbol
        """
        return symbol.upper()

    def clear_cache(self, symbol: str) -> None:
        """
        Clear all cached data for a symbol.

        Args:
            symbol: Asset symbol
        """
        self.cache.delete(symbol, 'current')
        self.cache.delete(symbol, 'historical')
        self.cache.delete(symbol, 'metrics')
        self.logger.debug(f"Cleared cache for {symbol}")

    def get_timeout(self, long_running: bool = False) -> int:
        """
        Get appropriate timeout value.

        Args:
            long_running: Whether this is a long-running operation

        Returns:
            Timeout in seconds
        """
        return API_TIMEOUTS.LONG_RUNNING if long_running else API_TIMEOUTS.DEFAULT
