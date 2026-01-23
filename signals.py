"""
Backward compatibility shim for signals module.

All functionality has been moved to signals/state_machine.py.
This module re-exports functions to maintain backward compatibility
with existing code that imports from 'signals'.

Usage:
    # Old imports still work:
    from signals import is_crypto_symbol, detect_watch_signal, determine_state

    # New preferred imports:
    from signals.state_machine import StateMachine, is_crypto_symbol
"""
import logging
from typing import List, Tuple, Optional
from datetime import datetime

# Import from the canonical implementation
from signals.state_machine import (
    StateMachine,
    is_crypto_symbol,
    determine_state as _determine_state,
)

# Import fetchers for backward-compatible module-level functions
from fetchers import YahooFetcher, CoinGeckoFetcher
from core.constants import CRYPTO_SYMBOLS

logger = logging.getLogger(__name__)

# Re-export the key function and class
__all__ = [
    'is_crypto_symbol',
    'get_historical_prices',
    'get_current_price',
    'detect_watch_signal',
    'detect_base_signal',
    'detect_buy_signal',
    'determine_state',
    'calculate_3day_return',
    'calculate_7day_range',
    'calculate_5day_high_breakout',
    'get_crypto_historical_prices',
    'get_stock_historical_prices',
    'get_crypto_current_price',
    'get_stock_current_price',
]

# ============================================================================
# Lazy initialization of default fetchers/state machine
# ============================================================================

_yahoo_fetcher = None
_coingecko_fetcher = None
_state_machine = None


def _get_yahoo_fetcher() -> YahooFetcher:
    """Get or create the default Yahoo fetcher."""
    global _yahoo_fetcher
    if _yahoo_fetcher is None:
        _yahoo_fetcher = YahooFetcher()
    return _yahoo_fetcher


def _get_coingecko_fetcher() -> CoinGeckoFetcher:
    """Get or create the default CoinGecko fetcher."""
    global _coingecko_fetcher
    if _coingecko_fetcher is None:
        _coingecko_fetcher = CoinGeckoFetcher()
    return _coingecko_fetcher


def _get_state_machine() -> StateMachine:
    """Get or create the default state machine."""
    global _state_machine
    if _state_machine is None:
        _state_machine = StateMachine(
            _get_yahoo_fetcher(),
            _get_coingecko_fetcher()
        )
    return _state_machine


# ============================================================================
# Backward-compatible functions (delegate to fetchers/state machine)
# ============================================================================

def get_crypto_historical_prices(
    symbol: str,
    days: int = 30
) -> Optional[List[Tuple[datetime, float]]]:
    """
    CoinGecko APIから仮想通貨の履歴価格データを取得

    Deprecated: Use CoinGeckoFetcher.get_historical_prices() instead.
    """
    return _get_coingecko_fetcher().get_historical_prices(symbol, days)


def get_stock_historical_prices(
    symbol: str,
    days: int = 30
) -> Optional[List[Tuple[datetime, float]]]:
    """
    yfinanceから米国株の履歴価格データを取得

    Deprecated: Use YahooFetcher.get_historical_prices() instead.
    """
    return _get_yahoo_fetcher().get_historical_prices(symbol, days)


def get_historical_prices(
    symbol: str,
    days: int = 30
) -> Optional[List[Tuple[datetime, float]]]:
    """
    仮想通貨または米国株の履歴価格データを取得（自動判定）
    """
    if is_crypto_symbol(symbol):
        return get_crypto_historical_prices(symbol, days)
    else:
        return get_stock_historical_prices(symbol, days)


def get_crypto_current_price(symbol: str) -> Optional[float]:
    """
    仮想通貨の現在価格を取得（CoinGecko）

    Deprecated: Use CoinGeckoFetcher.get_current_price() instead.
    """
    return _get_coingecko_fetcher().get_current_price(symbol)


def get_stock_current_price(symbol: str) -> Optional[float]:
    """
    米国株の現在価格を取得（yfinance）

    Deprecated: Use YahooFetcher.get_current_price() instead.
    """
    return _get_yahoo_fetcher().get_current_price(symbol)


def get_current_price(symbol: str) -> Optional[float]:
    """現在の価格を取得（仮想通貨または米国株を自動判定）"""
    if is_crypto_symbol(symbol):
        return get_crypto_current_price(symbol)
    else:
        return get_stock_current_price(symbol)


# ============================================================================
# Signal detection functions (delegate to state machine)
# ============================================================================

def detect_watch_signal(symbol: str) -> Tuple[bool, Optional[float]]:
    """
    WATCHシグナル（急落）を検出
    条件: 3日リターン ≤ -12%
    """
    return _get_state_machine().detect_watch_signal(symbol)


def detect_base_signal(symbol: str) -> Tuple[bool, Optional[float]]:
    """
    BASEシグナル（低迷）を検出
    条件: WATCH後、7日の価格レンジが ±5%以内
    """
    return _get_state_machine().detect_base_signal(symbol)


def detect_buy_signal(symbol: str) -> Tuple[bool, Optional[float]]:
    """
    BUYシグナル（反転）を検出
    条件: 直近5日高値を上抜け
    """
    return _get_state_machine().detect_buy_signal(symbol)


def determine_state(symbol: str, current_state: Optional[str] = None) -> str:
    """
    現在の状態を判定（状態遷移ロジック）
    戻り値: 'NORMAL', 'WATCH', 'BASE', 'BUY' のいずれか
    """
    return _get_state_machine().determine_state(symbol, current_state)


# ============================================================================
# Calculation helpers (for backward compatibility)
# ============================================================================

def calculate_3day_return(prices: List[Tuple[datetime, float]]) -> Optional[float]:
    """
    3日リターンを計算

    Deprecated: Use FeatureCalculator.calculate_return() instead.
    """
    from features import FeatureCalculator
    return FeatureCalculator.calculate_return(prices, 3)


def calculate_7day_range(
    prices: List[Tuple[datetime, float]]
) -> Optional[Tuple[float, float, float]]:
    """
    直近7日間の価格レンジを計算

    Deprecated: Use FeatureCalculator.calculate_range() instead.
    """
    from features import FeatureCalculator
    return FeatureCalculator.calculate_range(prices, 7)


def calculate_5day_high_breakout(prices: List[Tuple[datetime, float]]) -> bool:
    """
    直近5日間の高値を上抜けしたかどうか

    Deprecated: Use FeatureCalculator.calculate_high_breakout() instead.
    """
    from features import FeatureCalculator
    return FeatureCalculator.calculate_high_breakout(prices, 5)
