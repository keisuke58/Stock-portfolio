"""
Base class for all notifiers with shared formatting logic.

Provides common message formatting, emoji mappings, and template methods.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
from datetime import datetime
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.constants import CRYPTO_SYMBOLS


class BaseNotifier(ABC):
    """
    Abstract base class for notification services.

    Provides:
    - Shared emoji and state name mappings
    - Common formatting helpers
    - Template methods for platform-specific rendering

    Subclasses must implement:
    - send() - Send raw message
    - _format_link() - Platform-specific link formatting
    """

    # =========================================================================
    # Shared mappings (eliminates duplication across notifiers)
    # =========================================================================

    STATE_EMOJIS = {
        'WATCH': ':warning:',
        'BASE': ':chart_with_upwards_trend:',
        'BUY': ':rocket:',
        'NORMAL': ':chart_increasing:',
    }

    STATE_NAMES = {
        'WATCH': 'Sharp Drop Detected (WATCH)',
        'BASE': 'Consolidating (BASE)',
        'BUY': 'Reversal Signal (BUY)',
        'NORMAL': 'Normal State',
    }

    STATE_NAMES_JP = {
        'WATCH': '急落検出 (WATCH)',
        'BASE': '低迷継続 (BASE)',
        'BUY': '反転シグナル (BUY)',
        'NORMAL': '通常状態',
    }

    CONFIDENCE_EMOJIS = {
        'High': ':green_circle:',
        'Mid': ':yellow_circle:',
        'Spec': ':orange_circle:',
    }

    CONFIDENCE_NAMES = {
        'High': 'High Confidence',
        'Mid': 'Medium Confidence',
        'Spec': 'Speculative',
    }

    def __init__(self):
        """Initialize notifier with logging."""
        self.logger = logging.getLogger(self.__class__.__name__)

    # =========================================================================
    # Abstract methods (must be implemented by subclasses)
    # =========================================================================

    @abstractmethod
    def send(self, message: str) -> bool:
        """
        Send raw message. Must be implemented by subclass.

        Args:
            message: Message content

        Returns:
            True if sent successfully, False otherwise
        """
        pass

    @abstractmethod
    def _format_link(self, url: str, text: str) -> str:
        """
        Format link for the specific platform.

        Args:
            url: Link URL
            text: Display text

        Returns:
            Platform-specific formatted link
        """
        pass

    # =========================================================================
    # Template methods for notifications
    # =========================================================================

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
        message = self._format_state_change_message(symbol, old_state, new_state, price)
        return self.send(message)

    def notify_daily_pick(self, daily_pick: Dict[str, Any]) -> bool:
        """
        Notify about daily pick.

        Args:
            daily_pick: Daily pick data dictionary

        Returns:
            True if notification sent successfully
        """
        message = self._format_daily_pick_message(daily_pick)
        return self.send(message)

    # =========================================================================
    # Formatting helpers
    # =========================================================================

    def _format_state_change_message(
        self,
        symbol: str,
        old_state: Optional[str],
        new_state: str,
        price: float
    ) -> str:
        """
        Format state change message.

        Override in subclass for platform-specific formatting.
        Default implementation returns plain text.

        Args:
            symbol: Asset symbol
            old_state: Previous state
            new_state: Current state
            price: Current price

        Returns:
            Formatted message string
        """
        emoji = self._get_state_emoji(new_state)
        state_name = self.STATE_NAMES_JP.get(new_state, new_state)
        symbol_link = self._get_symbol_link(symbol)

        transition = f"{old_state or 'N/A'} -> {new_state}"

        return (
            f"{emoji} State Change: {symbol}\n"
            f"State: {state_name}\n"
            f"Transition: {transition}\n"
            f"Price: ${price:,.2f}\n"
            f"Link: {symbol_link}"
        )

    def _format_daily_pick_message(self, daily_pick: Dict[str, Any]) -> str:
        """
        Format daily pick message.

        Override in subclass for platform-specific formatting.
        Default implementation returns plain text.

        Args:
            daily_pick: Daily pick data dictionary

        Returns:
            Formatted message string
        """
        symbol = daily_pick.get('symbol', 'N/A')
        total_score = daily_pick.get('total_score', 0)
        value_score = daily_pick.get('value_score', 0)
        momentum_score = daily_pick.get('momentum_score', 0)
        stability_score = daily_pick.get('stability_score', 0)
        current_state = daily_pick.get('current_state', 'N/A')
        confidence = daily_pick.get('confidence', 'N/A')
        price = daily_pick.get('current_price', 0)

        emoji = self._get_state_emoji(current_state)
        confidence_emoji = self._get_confidence_emoji(confidence)

        return (
            f"{emoji} Daily Pick: {symbol}\n"
            f"State: {current_state} | Confidence: {confidence} {confidence_emoji}\n"
            f"Total Score: {total_score:.1f}/100\n"
            f"  - Value: {value_score:.1f}\n"
            f"  - Momentum: {momentum_score:.1f}\n"
            f"  - Stability: {stability_score:.1f}\n"
            f"Price: ${price:,.2f}"
        )

    # =========================================================================
    # Utility methods
    # =========================================================================

    def _get_state_emoji(self, state: str) -> str:
        """
        Get emoji for state.

        Args:
            state: State string

        Returns:
            Emoji string
        """
        return self.STATE_EMOJIS.get(state, ':question:')

    def _get_confidence_emoji(self, confidence: str) -> str:
        """
        Get emoji for confidence level.

        Args:
            confidence: Confidence level

        Returns:
            Emoji string
        """
        return self.CONFIDENCE_EMOJIS.get(confidence, ':grey_question:')

    def _get_symbol_url(self, symbol: str) -> str:
        """
        Get appropriate URL for symbol (crypto vs stock).

        Args:
            symbol: Asset symbol

        Returns:
            URL string
        """
        if self._is_crypto(symbol):
            return f"https://www.coingecko.com/en/coins/{symbol.lower()}"
        return f"https://finance.yahoo.com/quote/{symbol.upper()}"

    def _get_symbol_link(self, symbol: str) -> str:
        """
        Get formatted link for symbol.

        Args:
            symbol: Asset symbol

        Returns:
            Platform-specific formatted link
        """
        url = self._get_symbol_url(symbol)
        return self._format_link(url, symbol)

    def _is_crypto(self, symbol: str) -> bool:
        """
        Check if symbol is cryptocurrency.

        Args:
            symbol: Asset symbol

        Returns:
            True if crypto, False otherwise
        """
        return symbol.upper() in CRYPTO_SYMBOLS

    def _get_timestamp(self) -> str:
        """
        Get formatted UTC timestamp.

        Returns:
            ISO format timestamp string
        """
        return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    def _format_price(self, price: float) -> str:
        """
        Format price for display.

        Args:
            price: Price value

        Returns:
            Formatted price string
        """
        if price >= 1:
            return f"${price:,.2f}"
        elif price >= 0.01:
            return f"${price:.4f}"
        else:
            return f"${price:.8f}"

    def _format_percentage(self, value: float) -> str:
        """
        Format percentage for display.

        Args:
            value: Decimal value (e.g., 0.15 for 15%)

        Returns:
            Formatted percentage string with sign
        """
        pct = value * 100
        sign = '+' if pct >= 0 else ''
        return f"{sign}{pct:.2f}%"

    def _truncate(self, text: str, max_length: int = 100) -> str:
        """
        Truncate text to maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + '...'
