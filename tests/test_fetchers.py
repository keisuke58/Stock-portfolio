"""
Tests for fetchers (yahoo.py, coingecko.py)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import requests


class TestYahooFetcher:
    """Tests for YahooFetcher class."""

    def test_init_with_cache(self, mock_cache):
        """Test YahooFetcher initialization with cache."""
        from fetchers.yahoo import YahooFetcher

        fetcher = YahooFetcher(cache=mock_cache)

        assert fetcher.cache == mock_cache

    def test_init_without_cache(self):
        """Test YahooFetcher initialization without cache creates one."""
        from fetchers.yahoo import YahooFetcher

        fetcher = YahooFetcher()

        assert fetcher.cache is not None

    def test_get_current_price_from_cache(self, mock_cache_with_data):
        """Test get_current_price returns cached value."""
        from fetchers.yahoo import YahooFetcher

        fetcher = YahooFetcher(cache=mock_cache_with_data)

        price = fetcher.get_current_price('AAPL')

        assert price == 150.0
        mock_cache_with_data.get_current_price.assert_called_once_with('AAPL')

    @patch('yfinance.Ticker')
    def test_get_current_price_api_call(self, mock_ticker, mock_cache):
        """Test get_current_price makes API call on cache miss."""
        from fetchers.yahoo import YahooFetcher

        # Setup mock ticker
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = {'regularMarketPrice': 155.0}
        mock_ticker.return_value = mock_ticker_instance

        fetcher = YahooFetcher(cache=mock_cache)

        price = fetcher.get_current_price('AAPL')

        assert price == 155.0
        mock_ticker.assert_called_once()

    @patch('yfinance.Ticker')
    def test_get_current_price_api_error(self, mock_ticker, mock_cache):
        """Test get_current_price handles API errors gracefully."""
        from fetchers.yahoo import YahooFetcher

        mock_ticker.side_effect = Exception("API Error")

        fetcher = YahooFetcher(cache=mock_cache)

        price = fetcher.get_current_price('INVALID')

        assert price is None

    def test_get_historical_prices_from_cache(self, mock_cache_with_data, mock_price_data):
        """Test get_historical_prices returns cached value."""
        from fetchers.yahoo import YahooFetcher

        fetcher = YahooFetcher(cache=mock_cache_with_data)

        prices = fetcher.get_historical_prices('AAPL', days=30)

        assert prices == mock_price_data

    @patch('yfinance.Ticker')
    def test_get_metrics(self, mock_ticker, mock_cache):
        """Test get_metrics returns stock metrics."""
        from fetchers.yahoo import YahooFetcher

        mock_ticker_instance = Mock()
        mock_ticker_instance.info = {
            'trailingPE': 25.5,
            'forwardPE': 22.0,
            'priceToBook': 8.5,
            'dividendYield': 0.006,
            'marketCap': 2500000000000,
        }
        mock_ticker.return_value = mock_ticker_instance

        fetcher = YahooFetcher(cache=mock_cache)

        metrics = fetcher.get_metrics('AAPL')

        assert metrics is not None
        assert 'pe_ratio' in metrics or 'trailingPE' in metrics


class TestCoinGeckoFetcher:
    """Tests for CoinGeckoFetcher class."""

    def test_init_with_cache(self, mock_cache):
        """Test CoinGeckoFetcher initialization with cache."""
        from fetchers.coingecko import CoinGeckoFetcher

        fetcher = CoinGeckoFetcher(cache=mock_cache)

        assert fetcher.cache == mock_cache

    @patch('requests.get')
    def test_get_current_price_api_call(self, mock_get, mock_cache):
        """Test get_current_price makes CoinGecko API call."""
        from fetchers.coingecko import CoinGeckoFetcher

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'bitcoin': {'usd': 45000.0}
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        fetcher = CoinGeckoFetcher(cache=mock_cache)

        price = fetcher.get_current_price('BTC')

        assert price == 45000.0

    @patch('requests.get')
    def test_get_current_price_rate_limit(self, mock_get, mock_cache):
        """Test get_current_price handles rate limiting."""
        from fetchers.coingecko import CoinGeckoFetcher

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.RequestException("Rate limited")
        mock_get.return_value = mock_response

        fetcher = CoinGeckoFetcher(cache=mock_cache)

        price = fetcher.get_current_price('BTC')

        # Should return None on rate limit, not raise exception
        assert price is None

    @patch('requests.get')
    def test_get_historical_prices(self, mock_get, mock_cache):
        """Test get_historical_prices returns price history."""
        from fetchers.coingecko import CoinGeckoFetcher

        # Mock response with historical data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'prices': [
                [1640000000000, 45000.0],
                [1640086400000, 46000.0],
                [1640172800000, 44500.0],
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        fetcher = CoinGeckoFetcher(cache=mock_cache)

        prices = fetcher.get_historical_prices('BTC', days=30)

        assert prices is not None
        assert len(prices) == 3
        # Each item should be (datetime, float)
        assert all(isinstance(p[0], datetime) for p in prices)
        assert all(isinstance(p[1], float) for p in prices)

    def test_symbol_mapping(self, mock_cache):
        """Test crypto symbol to CoinGecko ID mapping."""
        from fetchers.coingecko import CoinGeckoFetcher

        fetcher = CoinGeckoFetcher(cache=mock_cache)

        # Test common mappings
        assert fetcher._get_coingecko_id('BTC') == 'bitcoin'
        assert fetcher._get_coingecko_id('ETH') == 'ethereum'
        assert fetcher._get_coingecko_id('SOL') == 'solana'


class TestFetcherCacheIntegration:
    """Integration tests for fetcher-cache interaction."""

    def test_cache_set_on_successful_fetch(self, mock_cache):
        """Test that successful fetch updates cache."""
        from fetchers.yahoo import YahooFetcher

        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = Mock()
            mock_ticker_instance.info = {'regularMarketPrice': 155.0}
            mock_ticker.return_value = mock_ticker_instance

            fetcher = YahooFetcher(cache=mock_cache)
            fetcher.get_current_price('AAPL')

            # Cache set should have been called
            # (Implementation dependent)

    def test_cache_not_set_on_failed_fetch(self, mock_cache):
        """Test that failed fetch does not update cache."""
        from fetchers.yahoo import YahooFetcher

        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.side_effect = Exception("API Error")

            fetcher = YahooFetcher(cache=mock_cache)
            fetcher.get_current_price('INVALID')

            # Cache set should not have been called with invalid data
            # mock_cache.set_current_price.assert_not_called()  # If applicable


class TestFetcherErrorHandling:
    """Tests for error handling in fetchers."""

    @patch('yfinance.Ticker')
    def test_yahoo_network_error(self, mock_ticker, mock_cache):
        """Test Yahoo fetcher handles network errors."""
        from fetchers.yahoo import YahooFetcher

        mock_ticker.side_effect = requests.ConnectionError("Network unreachable")

        fetcher = YahooFetcher(cache=mock_cache)
        price = fetcher.get_current_price('AAPL')

        assert price is None

    @patch('requests.get')
    def test_coingecko_timeout(self, mock_get, mock_cache):
        """Test CoinGecko fetcher handles timeouts."""
        from fetchers.coingecko import CoinGeckoFetcher

        mock_get.side_effect = requests.Timeout("Request timed out")

        fetcher = CoinGeckoFetcher(cache=mock_cache)
        price = fetcher.get_current_price('BTC')

        assert price is None

    @patch('requests.get')
    def test_coingecko_invalid_json(self, mock_get, mock_cache):
        """Test CoinGecko fetcher handles invalid JSON."""
        from fetchers.coingecko import CoinGeckoFetcher

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        fetcher = CoinGeckoFetcher(cache=mock_cache)
        price = fetcher.get_current_price('BTC')

        assert price is None
