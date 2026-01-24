"""
Centralized constants for the application.
All magic numbers should be defined here for maintainability.
"""
from dataclasses import dataclass
from typing import Set


@dataclass(frozen=True)
class SignalThresholds:
    """
    Thresholds for signal detection in the state machine.

    WATCH: Sharp drop detection (crash)
    BASE: Consolidation detection (low volatility range)
    BUY: Recovery/breakout detection
    """
    # WATCH signal: 3-day return threshold for crash detection
    WATCH_RETURN_THRESHOLD: float = -12.0
    WATCH_DETECTION_DAYS: int = 10
    WATCH_RETURN_PERIOD: int = 3

    # BASE signal: Price range threshold for consolidation detection
    BASE_RANGE_THRESHOLD: float = 5.0
    BASE_DETECTION_DAYS: int = 15
    BASE_RANGE_PERIOD: int = 7

    # BUY signal: Breakout detection parameters
    BUY_DETECTION_DAYS: int = 10
    BUY_BREAKOUT_PERIOD: int = 5


@dataclass(frozen=True)
class CacheTTL:
    """
    Time-To-Live settings for cache entries (in seconds).
    """
    # Current price: 1 hour
    CURRENT_PRICE: int = 3600

    # Historical prices: 24 hours
    HISTORICAL_PRICES: int = 86400

    # Stock metrics: 24 hours
    METRICS: int = 86400

    # Fundamental data: 24 hours
    FUNDAMENTALS: int = 86400

    # News data: 6 hours
    NEWS: int = 21600

    # SEC filings: 12 hours
    SEC_FILINGS: int = 43200


@dataclass(frozen=True)
class APITimeouts:
    """
    Timeout settings for API calls (in seconds).
    """
    # Default timeout for quick API calls
    DEFAULT: int = 10

    # Extended timeout for longer operations
    LONG_RUNNING: int = 30

    # Analysis pipeline timeout
    ANALYSIS: int = 300

    # Batch processing timeout
    BATCH: int = 600


@dataclass(frozen=True)
class ScoringThresholds:
    """
    Thresholds used in VMS (Value/Momentum/Stability) scoring.
    """
    # Market cap tiers
    MEGA_CAP: int = 200_000_000_000  # $200B+
    LARGE_CAP: int = 10_000_000_000   # $10B+
    MID_CAP: int = 2_000_000_000      # $2B+
    SMALL_CAP: int = 300_000_000      # $300M+

    # PE Ratio tiers
    PE_VERY_LOW: int = 10
    PE_LOW: int = 15
    PE_FAIR: int = 25
    PE_HIGH: int = 40
    PE_VERY_HIGH: int = 60

    # ATH Ratio tiers (current price / all-time high)
    ATH_NEAR_HIGH: float = 0.95  # Within 5% of ATH
    ATH_MODERATE: float = 0.80   # Within 20% of ATH
    ATH_DISCOUNT: float = 0.60   # 40% below ATH
    ATH_DEEP_VALUE: float = 0.40 # 60% below ATH

    # Revenue growth tiers
    GROWTH_HIGH: float = 0.20    # 20%+
    GROWTH_MODERATE: float = 0.10 # 10%+
    GROWTH_LOW: float = 0.05     # 5%+

    # Profit margin tiers
    MARGIN_HIGH: float = 0.20    # 20%+
    MARGIN_MODERATE: float = 0.10 # 10%+
    MARGIN_LOW: float = 0.05     # 5%+

    # Volatility tiers (annualized)
    VOL_LOW: float = 0.15        # <15% - stable
    VOL_MODERATE: float = 0.25   # <25% - normal
    VOL_HIGH: float = 0.40       # <40% - volatile
    VOL_EXTREME: float = 0.60    # 60%+ - very volatile

    # Score thresholds
    SCORE_HIGH: float = 70.0
    SCORE_MEDIUM: float = 50.0
    SCORE_LOW: float = 30.0

    # Default weights for VMS scoring
    WEIGHT_VALUE: float = 0.40
    WEIGHT_MOMENTUM: float = 0.35
    WEIGHT_STABILITY: float = 0.25


@dataclass(frozen=True)
class RateLimiting:
    """
    Rate limiting settings to avoid API throttling.
    """
    # Batch processing
    BATCH_SIZE: int = 10
    BATCH_DELAY: float = 2.0  # seconds between batches

    # Single request delay
    SINGLE_DELAY: float = 0.5  # seconds between single requests

    # CoinGecko specific (stricter free tier)
    COINGECKO_DELAY: float = 1.5
    COINGECKO_BATCH_SIZE: int = 5

    # SEC EDGAR specific (10 requests per second limit)
    SEC_EDGAR_DELAY: float = 0.2
    SEC_EDGAR_BATCH_SIZE: int = 10

    # Notification throttling
    NOTIFICATION_COOLDOWN: int = 86400  # 24 hours default


@dataclass(frozen=True)
class NotificationConfig:
    """
    Configuration for notification behavior.
    """
    # Cooldown periods (in seconds)
    DEFAULT_COOLDOWN: int = 86400  # 24 hours
    ANOMALY_COOLDOWN: int = 3600   # 1 hour for anomalies

    # Throttle settings
    MAX_NOTIFICATIONS_PER_HOUR: int = 10
    MAX_NOTIFICATIONS_PER_DAY: int = 50


@dataclass(frozen=True)
class DeepBottomBacktestConfig:
    """
    Configuration for Deep Bottom backtesting.
    """
    # Target return to consider a "win"
    TARGET_RETURN_PCT: float = 50.0  # 50% gain

    # Time window to achieve target return (months)
    TARGET_PERIOD_MONTHS: int = 12

    # Intervals to check returns (months)
    CHECK_INTERVALS: tuple = (3, 6, 12)

    # Minimum days between signals to avoid clustering
    MIN_DAYS_BETWEEN_SIGNALS: int = 30

    # Known crash periods for specialized testing
    # Format: {'name': {'symbol': str, 'start': str, 'end': str}}


@dataclass(frozen=True)
class FundamentalScoringConfig:
    """
    Configuration for fundamental health scoring.
    Score range: 0-25 points
    """
    # P/E Ratio thresholds
    PE_EXCELLENT: float = 15.0    # Score 6
    PE_FAIR: float = 25.0         # Score 4
    PE_GROWTH: float = 40.0       # Score 2
    PE_NEGATIVE_PENALTY: float = -3.0  # Negative earnings penalty

    # P/B Ratio thresholds
    PB_VALUE: float = 1.0         # Score 5 (below book value)
    PB_FAIR: float = 2.0          # Score 3
    PB_MAX: float = 3.0           # Score 1

    # Debt/Equity thresholds
    DEBT_LOW: float = 0.5         # Score 5
    DEBT_MODERATE: float = 1.0    # Score 3
    DEBT_HIGH: float = 2.0        # Score 1

    # Revenue growth thresholds
    GROWTH_HIGH: float = 0.10     # Score 4 (10%+)
    GROWTH_STABLE: float = 0.0    # Score 2 (0%+)

    # Health status thresholds
    HEALTHY_MIN_SCORE: int = 15   # >= 15 = HEALTHY
    MODERATE_MIN_SCORE: int = 10  # >= 10 = MODERATE
    WEAK_MIN_SCORE: int = 5       # >= 5 = WEAK
    # < 5 = VALUE_TRAP


@dataclass(frozen=True)
class DeepBottomThresholds:
    """
    Thresholds for deep bottom detection (long-term investing).
    Designed to trigger only at historically extreme lows with upside potential.
    """
    # ATH drawdown: minimum percentage below all-time high
    ATH_DRAWDOWN_MIN: float = 70.0  # At least 70% below ATH

    # 52-week low proximity: how close to yearly low (0 = at low, 1 = at high)
    WEEK52_LOW_PROXIMITY_MAX: float = 0.10  # Within 10% of 52-week low

    # RSI threshold for oversold
    RSI_OVERSOLD: float = 30.0  # RSI below 30

    # Moving average period for mean reversion
    MA_PERIOD: int = 200  # 200-day moving average

    # Minimum days of historical data required
    DETECTION_DAYS: int = 365  # 1 year of data needed

    # Not in active crash: 7-day return must be above this
    MIN_7D_RETURN: float = -20.0  # Avoid catching falling knives


@dataclass(frozen=True)
class SelectionConfig:
    """
    Configuration for daily selection logic.
    """
    # Maximum assets in each state
    MAX_BUY_SELECTIONS: int = 3
    MAX_BASE_SELECTIONS: int = 5

    # Rotation blacklist period (days)
    ROTATION_BLACKLIST_DAYS: int = 7

    # Bias control limits
    MAX_PER_SECTOR: int = 2
    MAX_PER_CATEGORY: int = 3

    # Minimum score for selection
    MIN_SCORE_THRESHOLD: float = 70.0


# Crypto symbol sets for identification
CRYPTO_SYMBOLS: Set[str] = {
    'BTC', 'ETH', 'BNB', 'SOL', 'ADA', 'XRP', 'DOGE',
    'DOT', 'MATIC', 'AVAX', 'LINK', 'UNI', 'ATOM', 'LTC',
    'SHIB', 'TRX', 'ETC', 'XLM', 'NEAR', 'ALGO', 'FIL',
    'VET', 'ICP', 'APT', 'HBAR', 'AAVE', 'MKR', 'SAND',
    'MANA', 'AXS', 'ENJ', 'CRV', 'SUSHI', 'COMP', 'YFI',
}

CRYPTO_IDS: Set[str] = {
    'bitcoin', 'ethereum', 'binancecoin', 'solana', 'cardano',
    'ripple', 'dogecoin', 'polkadot', 'matic-network', 'avalanche-2',
    'chainlink', 'uniswap', 'cosmos', 'litecoin', 'shiba-inu',
}

# ETF symbols for category identification
ETF_SYMBOLS: Set[str] = {
    'SPY', 'QQQ', 'IVV', 'VTI', 'VOO', 'GLD', 'SLV',
    'DIA', 'IWM', 'EFA', 'VEA', 'VWO', 'AGG', 'BND',
    'TLT', 'LQD', 'HYG', 'XLF', 'XLK', 'XLE', 'XLV',
}

# Major tech symbols
TECH_SYMBOLS: Set[str] = {
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA',
    'META', 'TSLA', 'AMD', 'INTC', 'CRM', 'ORCL',
    'ADBE', 'NFLX', 'PYPL', 'SHOP', 'SQ', 'UBER',
}


# Singleton instances for easy import
SIGNAL_THRESHOLDS = SignalThresholds()
CACHE_TTL = CacheTTL()
API_TIMEOUTS = APITimeouts()
SCORING_THRESHOLDS = ScoringThresholds()
RATE_LIMITING = RateLimiting()
NOTIFICATION_CONFIG = NotificationConfig()
SELECTION_CONFIG = SelectionConfig()
DEEP_BOTTOM_THRESHOLDS = DeepBottomThresholds()
DEEP_BOTTOM_BACKTEST_CONFIG = DeepBottomBacktestConfig()
FUNDAMENTAL_SCORING_CONFIG = FundamentalScoringConfig()
