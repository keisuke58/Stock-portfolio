"""
Core module containing shared utilities, protocols, and configurations.
"""
from .constants import (
    SIGNAL_THRESHOLDS,
    CACHE_TTL,
    API_TIMEOUTS,
    SCORING_THRESHOLDS,
    RATE_LIMITING,
    SignalThresholds,
    CacheTTL,
    APITimeouts,
    ScoringThresholds,
    RateLimiting,
)

__all__ = [
    # Singleton instances
    'SIGNAL_THRESHOLDS',
    'CACHE_TTL',
    'API_TIMEOUTS',
    'SCORING_THRESHOLDS',
    'RATE_LIMITING',
    # Classes for type hints
    'SignalThresholds',
    'CacheTTL',
    'APITimeouts',
    'ScoringThresholds',
    'RateLimiting',
]
