"""
Shared pytest fixtures for the test suite.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any, Optional
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Price Data Fixtures
# ============================================================================

@pytest.fixture
def mock_price_data() -> List[Tuple[datetime, float]]:
    """
    Generate 30-day mock historical price data.
    Simulates a price drop followed by consolidation and recovery.
    """
    base_date = datetime(2026, 1, 1)
    prices = []

    # Days 1-10: Normal prices around $100
    for i in range(10):
        prices.append((base_date + timedelta(days=i), 100.0 + (i % 3)))

    # Days 11-15: Sharp drop (WATCH signal trigger)
    for i in range(10, 15):
        prices.append((base_date + timedelta(days=i), 100.0 - (i - 10) * 3))

    # Days 16-22: Consolidation (BASE signal trigger)
    for i in range(15, 22):
        prices.append((base_date + timedelta(days=i), 86.0 + (i % 2)))

    # Days 23-30: Recovery (BUY signal trigger)
    for i in range(22, 30):
        prices.append((base_date + timedelta(days=i), 87.0 + (i - 22) * 1.5))

    return prices


@pytest.fixture
def mock_price_data_stable() -> List[Tuple[datetime, float]]:
    """Generate stable price data with minimal volatility."""
    base_date = datetime(2026, 1, 1)
    return [
        (base_date + timedelta(days=i), 100.0 + (i % 2) * 0.5)
        for i in range(30)
    ]


@pytest.fixture
def mock_price_data_crash() -> List[Tuple[datetime, float]]:
    """Generate price data simulating a crash (>12% drop in 3 days)."""
    base_date = datetime(2026, 1, 1)
    prices = []

    # Initial stable period
    for i in range(7):
        prices.append((base_date + timedelta(days=i), 100.0))

    # Sharp crash
    for i in range(7, 10):
        prices.append((base_date + timedelta(days=i), 100.0 - (i - 6) * 5))

    return prices


# ============================================================================
# Cache Fixtures
# ============================================================================

@pytest.fixture
def mock_cache():
    """
    Mock PriceCache for unit tests.
    Returns None for all gets (cache miss).
    """
    cache = Mock()
    cache.get.return_value = None
    cache.get_current_price.return_value = None
    cache.get_historical_prices.return_value = None
    cache.set.return_value = None
    cache.set_current_price.return_value = None
    cache.set_historical_prices.return_value = None
    return cache


@pytest.fixture
def mock_cache_with_data(mock_price_data):
    """Mock PriceCache with pre-populated data."""
    cache = Mock()
    cache.get_current_price.return_value = 150.0
    cache.get_historical_prices.return_value = mock_price_data
    cache.get.return_value = {'price': 150.0, 'timestamp': datetime.utcnow().isoformat()}
    return cache


# ============================================================================
# Daily Pick / Analysis Result Fixtures
# ============================================================================

@pytest.fixture
def sample_daily_pick() -> Dict[str, Any]:
    """Sample daily pick data for notifier tests."""
    return {
        'symbol': 'AAPL',
        'total_score': 75.5,
        'value_score': 80.0,
        'momentum_score': 70.0,
        'stability_score': 75.0,
        'current_price': 150.0,
        'current_state': 'BUY',
        'old_state': 'BASE',
        'asset_category': 'US_LARGE_CAP',
        'confidence': 'High',
        'ath_ratio': 0.85,
        'return_30d': 0.12,
        'return_7d': 0.05,
        'return_3d': 0.02,
        'volatility': 0.15,
        'breakout_5d': True,
        'data_quality_score': 95,
        'report_timestamp': datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_daily_pick_crypto() -> Dict[str, Any]:
    """Sample daily pick data for crypto assets."""
    return {
        'symbol': 'BTC',
        'total_score': 72.0,
        'value_score': 65.0,
        'momentum_score': 80.0,
        'stability_score': 70.0,
        'current_price': 45000.0,
        'current_state': 'WATCH',
        'old_state': 'NORMAL',
        'asset_category': 'CRYPTO',
        'confidence': 'Mid',
        'ath_ratio': 0.65,
        'return_30d': -0.08,
        'return_7d': -0.03,
        'return_3d': -0.15,
        'volatility': 0.45,
        'breakout_5d': False,
        'data_quality_score': 80,
        'report_timestamp': datetime.utcnow().isoformat(),
    }


# ============================================================================
# Fundamental Data Fixtures
# ============================================================================

@pytest.fixture
def sample_fundamental_data() -> Dict[str, Any]:
    """Sample fundamental financial data."""
    return {
        'fcf': 100_000_000_000,  # $100B
        'revenue_growth': 0.15,
        'profit_margin': 0.25,
        'financial_health_score': 85.0,
        'debt_to_equity': 1.5,
        'current_ratio': 1.2,
        'data_sources': ['yfinance', 'sec_edgar'],
    }


@pytest.fixture
def sample_analyst_data() -> Dict[str, Any]:
    """Sample analyst data."""
    return {
        'target_price': 200.0,
        'recommendation': 'Buy',
        'num_analysts': 35,
        'eps_growth': 0.12,
        'revenue_estimate': 400_000_000_000,
    }


@pytest.fixture
def sample_metrics() -> Dict[str, Any]:
    """Sample stock metrics."""
    return {
        'pe_ratio': 25.5,
        'forward_pe': 22.0,
        'pb_ratio': 8.5,
        'dividend_yield': 0.006,
        'market_cap': 2_500_000_000_000,
        'enterprise_value': 2_600_000_000_000,
        'beta': 1.2,
    }


# ============================================================================
# Event / News Fixtures
# ============================================================================

@pytest.fixture
def sample_news_items() -> List[Dict[str, Any]]:
    """Sample news items for event classification tests."""
    return [
        {
            'title': 'Apple beats earnings expectations with strong iPhone sales',
            'link': 'https://example.com/news1',
            'published_time': '2026-01-20T10:00:00',
            'source': 'Reuters',
        },
        {
            'title': 'Company faces regulatory investigation',
            'link': 'https://example.com/news2',
            'published_time': '2026-01-19T15:00:00',
            'source': 'Bloomberg',
        },
        {
            'title': 'Quarterly financial report released',
            'link': 'https://example.com/news3',
            'published_time': '2026-01-18T09:00:00',
            'source': 'SEC',
        },
    ]


@pytest.fixture
def sample_sec_filings() -> List[Dict[str, Any]]:
    """Sample SEC filings for classification tests."""
    return [
        {
            'form': '8-K',
            'filing_date': '2026-01-15',
            'description': 'Acquisition of new technology company',
            'url': 'https://www.sec.gov/filing1',
        },
        {
            'form': '10-K',
            'filing_date': '2025-12-31',
            'description': 'Annual report',
            'url': 'https://www.sec.gov/filing2',
        },
        {
            'form': '10-Q',
            'filing_date': '2025-09-30',
            'description': 'Quarterly report',
            'url': 'https://www.sec.gov/filing3',
        },
    ]


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample application configuration."""
    return {
        'symbols': ['AAPL', 'MSFT', 'BTC', 'ETH'],
        'check_interval': 3600,
        'webhook': 'https://discord.com/api/webhooks/test/test',
        'line_token': 'test_line_token',
        'slack_webhook': 'https://hooks.slack.com/test',
        'gmail_user': 'test@gmail.com',
        'gmail_password': 'test_password',
        'gmail_to': 'recipient@example.com',
        'llm_model': 'gpt-4o-mini',
        'llm_temperature': 0.3,
    }


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_yahoo_fetcher(mock_cache, mock_price_data):
    """Mock YahooFetcher for testing."""
    fetcher = Mock()
    fetcher.cache = mock_cache
    fetcher.get_current_price.return_value = 150.0
    fetcher.get_historical_prices.return_value = mock_price_data
    fetcher.get_metrics.return_value = {
        'pe_ratio': 25.5,
        'market_cap': 2_500_000_000_000,
    }
    return fetcher


@pytest.fixture
def mock_coingecko_fetcher(mock_cache, mock_price_data):
    """Mock CoinGeckoFetcher for testing."""
    fetcher = Mock()
    fetcher.cache = mock_cache
    fetcher.get_current_price.return_value = 45000.0
    fetcher.get_historical_prices.return_value = mock_price_data
    return fetcher


@pytest.fixture
def mock_state_store():
    """Mock StateStore for testing."""
    store = Mock()
    store.get_state.return_value = 'NORMAL'
    store.set_state.return_value = True
    store.get_all_states.return_value = {
        'AAPL': 'BUY',
        'MSFT': 'BASE',
        'BTC': 'WATCH',
    }
    return store


@pytest.fixture
def mock_notifier():
    """Mock notifier for testing."""
    notifier = Mock()
    notifier.send.return_value = True
    notifier.notify_state_change.return_value = True
    notifier.notify_daily_pick.return_value = True
    return notifier


# ============================================================================
# HTTP Response Fixtures
# ============================================================================

@pytest.fixture
def mock_requests_get():
    """Mock requests.get for API tests."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_requests_post():
    """Mock requests.post for webhook tests."""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        yield mock_post


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a temporary database path for tests."""
    return str(tmp_path / "test.db")


@pytest.fixture
def temp_cache_db(tmp_path):
    """Provide a temporary cache database."""
    from cache import PriceCache
    db_path = str(tmp_path / "test_cache.db")
    return PriceCache(db_path=db_path)


@pytest.fixture
def temp_state_store(tmp_path):
    """Provide a temporary state store."""
    from state_store import StateStore
    db_path = str(tmp_path / "test_state.db")
    return StateStore(db_path=db_path)
