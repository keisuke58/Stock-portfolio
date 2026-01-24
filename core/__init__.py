"""
Core module containing shared utilities, protocols, and configurations.

This module provides:
- constants: Centralized configuration values
- protocols: Interface definitions for dependency injection
- models: Type-safe dataclasses for structured data
- logging_config: Structured logging setup
- retry: Exponential backoff utilities
- circuit_breaker: Failure protection patterns
- container: Dependency injection container
"""
from .constants import (
    SIGNAL_THRESHOLDS,
    CACHE_TTL,
    API_TIMEOUTS,
    SCORING_THRESHOLDS,
    RATE_LIMITING,
    NOTIFICATION_CONFIG,
    SELECTION_CONFIG,
    CRYPTO_SYMBOLS,
    CRYPTO_IDS,
    ETF_SYMBOLS,
    TECH_SYMBOLS,
    SignalThresholds,
    CacheTTL,
    APITimeouts,
    ScoringThresholds,
    RateLimiting,
    NotificationConfig,
    SelectionConfig,
)

from .protocols import (
    PriceFetcher,
    Notifier,
    CacheProvider,
    StateStoreProtocol,
    Scorer,
    DataIngester,
    EventClassifierProtocol,
)

from .models import (
    AssetState,
    Confidence,
    AssetCategory,
    PricePoint,
    PriceData,
    StockMetrics,
    FundamentalData,
    AnalystData,
    Features,
    VMSScores,
    Event,
    AnalysisResult,
    DailyPick,
)

from .logging_config import (
    setup_logging,
    setup_development_logging,
    setup_production_logging,
    setup_test_logging,
    get_logger,
    JSONFormatter,
    ColoredFormatter,
)

from .retry import (
    retry_with_backoff,
    retry_on_network_error,
    retry_on_rate_limit,
    RetryConfig,
    NETWORK_RETRY_CONFIG,
    RATE_LIMIT_RETRY_CONFIG,
    AGGRESSIVE_RETRY_CONFIG,
    with_retry,
)

from .circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitOpenError,
    CircuitStats,
    circuit_breaker,
    CircuitBreakerRegistry,
    circuit_registry,
    get_yahoo_circuit,
    get_coingecko_circuit,
    get_discord_circuit,
)

from .container import (
    ServiceContainer,
    container,
    setup_container,
    get_container,
    get_yahoo_fetcher,
    get_coingecko_fetcher,
    get_state_machine,
    get_state_store,
    get_notifiers,
)

__all__ = [
    # Constants - Instances
    'SIGNAL_THRESHOLDS',
    'CACHE_TTL',
    'API_TIMEOUTS',
    'SCORING_THRESHOLDS',
    'RATE_LIMITING',
    'NOTIFICATION_CONFIG',
    'SELECTION_CONFIG',
    'CRYPTO_SYMBOLS',
    'CRYPTO_IDS',
    'ETF_SYMBOLS',
    'TECH_SYMBOLS',
    # Constants - Classes
    'SignalThresholds',
    'CacheTTL',
    'APITimeouts',
    'ScoringThresholds',
    'RateLimiting',
    'NotificationConfig',
    'SelectionConfig',
    # Protocols
    'PriceFetcher',
    'Notifier',
    'CacheProvider',
    'StateStoreProtocol',
    'Scorer',
    'DataIngester',
    'EventClassifierProtocol',
    # Models
    'AssetState',
    'Confidence',
    'AssetCategory',
    'PricePoint',
    'PriceData',
    'StockMetrics',
    'FundamentalData',
    'AnalystData',
    'Features',
    'VMSScores',
    'Event',
    'AnalysisResult',
    'DailyPick',
    # Logging
    'setup_logging',
    'setup_development_logging',
    'setup_production_logging',
    'setup_test_logging',
    'get_logger',
    'JSONFormatter',
    'ColoredFormatter',
    # Retry
    'retry_with_backoff',
    'retry_on_network_error',
    'retry_on_rate_limit',
    'RetryConfig',
    'NETWORK_RETRY_CONFIG',
    'RATE_LIMIT_RETRY_CONFIG',
    'AGGRESSIVE_RETRY_CONFIG',
    'with_retry',
    # Circuit Breaker
    'CircuitBreaker',
    'CircuitState',
    'CircuitOpenError',
    'CircuitStats',
    'circuit_breaker',
    'CircuitBreakerRegistry',
    'circuit_registry',
    'get_yahoo_circuit',
    'get_coingecko_circuit',
    'get_discord_circuit',
    # Container
    'ServiceContainer',
    'container',
    'setup_container',
    'get_container',
    'get_yahoo_fetcher',
    'get_coingecko_fetcher',
    'get_state_machine',
    'get_state_store',
    'get_notifiers',
]
