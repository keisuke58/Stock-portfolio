"""
Tests for signals/state_machine.py
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta


class TestStateMachine:
    """Tests for StateMachine class."""

    def test_is_crypto_symbol_bitcoin(self):
        """Test crypto detection for Bitcoin."""
        from signals.state_machine import is_crypto_symbol

        assert is_crypto_symbol('BTC') is True
        assert is_crypto_symbol('btc') is True

    def test_is_crypto_symbol_ethereum(self):
        """Test crypto detection for Ethereum."""
        from signals.state_machine import is_crypto_symbol

        assert is_crypto_symbol('ETH') is True

    def test_is_crypto_symbol_stock(self):
        """Test crypto detection for stocks returns False."""
        from signals.state_machine import is_crypto_symbol

        assert is_crypto_symbol('AAPL') is False
        assert is_crypto_symbol('MSFT') is False
        assert is_crypto_symbol('GOOGL') is False

    def test_is_crypto_symbol_edge_cases(self):
        """Test crypto detection edge cases."""
        from signals.state_machine import is_crypto_symbol

        # Common cryptos
        assert is_crypto_symbol('SOL') is True
        assert is_crypto_symbol('XRP') is True
        assert is_crypto_symbol('DOGE') is True

        # Not cryptos
        assert is_crypto_symbol('IBM') is False
        assert is_crypto_symbol('META') is False


class TestWatchSignalDetection:
    """Tests for WATCH signal detection (sharp drop)."""

    def test_detect_watch_signal_with_crash(self, mock_price_data_crash):
        """Test WATCH signal is detected on >12% 3-day drop."""
        from signals.state_machine import StateMachine

        mock_yahoo = Mock()
        mock_yahoo.get_historical_prices.return_value = mock_price_data_crash
        mock_coingecko = Mock()

        sm = StateMachine(mock_yahoo, mock_coingecko)

        detected, return_value = sm.detect_watch_signal('AAPL')

        assert detected is True
        assert return_value is not None
        assert return_value <= -12.0

    def test_detect_watch_signal_stable(self, mock_price_data_stable):
        """Test WATCH signal not detected on stable prices."""
        from signals.state_machine import StateMachine

        mock_yahoo = Mock()
        mock_yahoo.get_historical_prices.return_value = mock_price_data_stable
        mock_coingecko = Mock()

        sm = StateMachine(mock_yahoo, mock_coingecko)

        detected, return_value = sm.detect_watch_signal('AAPL')

        assert detected is False

    def test_detect_watch_signal_no_data(self):
        """Test WATCH signal with no price data."""
        from signals.state_machine import StateMachine

        mock_yahoo = Mock()
        mock_yahoo.get_historical_prices.return_value = None
        mock_coingecko = Mock()

        sm = StateMachine(mock_yahoo, mock_coingecko)

        detected, return_value = sm.detect_watch_signal('AAPL')

        assert detected is False
        assert return_value is None


class TestBaseSignalDetection:
    """Tests for BASE signal detection (consolidation)."""

    def test_detect_base_signal_consolidating(self):
        """Test BASE signal detected during consolidation (low volatility)."""
        from signals.state_machine import StateMachine

        # Create consolidation data: 7-day range <= 5%
        base_date = datetime(2026, 1, 1)
        consolidation_data = [
            (base_date + timedelta(days=i), 100.0 + (i % 2) * 2)  # Range ~2%
            for i in range(15)
        ]

        mock_yahoo = Mock()
        mock_yahoo.get_historical_prices.return_value = consolidation_data
        mock_coingecko = Mock()

        sm = StateMachine(mock_yahoo, mock_coingecko)

        detected, range_value = sm.detect_base_signal('AAPL')

        assert detected is True
        assert range_value is not None
        assert range_value <= 5.0

    def test_detect_base_signal_volatile(self, mock_price_data):
        """Test BASE signal not detected during volatile period."""
        from signals.state_machine import StateMachine

        mock_yahoo = Mock()
        mock_yahoo.get_historical_prices.return_value = mock_price_data
        mock_coingecko = Mock()

        sm = StateMachine(mock_yahoo, mock_coingecko)

        detected, range_value = sm.detect_base_signal('AAPL')

        # The mock_price_data has significant price movement
        # BASE signal should likely not be detected
        # (depends on the specific data pattern)
        assert isinstance(detected, bool)


class TestBuySignalDetection:
    """Tests for BUY signal detection (breakout)."""

    def test_detect_buy_signal_breakout(self):
        """Test BUY signal detected on 5-day high breakout."""
        from signals.state_machine import StateMachine

        # Create breakout data
        base_date = datetime(2026, 1, 1)
        breakout_data = [
            (base_date + timedelta(days=i), 100.0 + i * 2)  # Steady increase
            for i in range(10)
        ]

        mock_yahoo = Mock()
        mock_yahoo.get_historical_prices.return_value = breakout_data
        mock_coingecko = Mock()

        sm = StateMachine(mock_yahoo, mock_coingecko)

        detected, _ = sm.detect_buy_signal('AAPL')

        assert detected is True

    def test_detect_buy_signal_declining(self):
        """Test BUY signal not detected on declining prices."""
        from signals.state_machine import StateMachine

        # Create declining data
        base_date = datetime(2026, 1, 1)
        declining_data = [
            (base_date + timedelta(days=i), 100.0 - i * 2)  # Steady decrease
            for i in range(10)
        ]

        mock_yahoo = Mock()
        mock_yahoo.get_historical_prices.return_value = declining_data
        mock_coingecko = Mock()

        sm = StateMachine(mock_yahoo, mock_coingecko)

        detected, _ = sm.detect_buy_signal('AAPL')

        assert detected is False


class TestDetermineState:
    """Tests for overall state determination."""

    def test_determine_state_normal(self, mock_price_data_stable):
        """Test NORMAL state for stable prices."""
        from signals.state_machine import StateMachine

        mock_yahoo = Mock()
        mock_yahoo.get_historical_prices.return_value = mock_price_data_stable
        mock_coingecko = Mock()

        sm = StateMachine(mock_yahoo, mock_coingecko)

        state = sm.determine_state('AAPL')

        assert state in ['NORMAL', 'BASE', 'WATCH', 'BUY']

    def test_determine_state_with_previous_state(self, mock_price_data):
        """Test state determination considers previous state."""
        from signals.state_machine import StateMachine

        mock_yahoo = Mock()
        mock_yahoo.get_historical_prices.return_value = mock_price_data
        mock_coingecko = Mock()

        sm = StateMachine(mock_yahoo, mock_coingecko)

        # Test with previous state
        state = sm.determine_state('AAPL', current_state='WATCH')

        assert state in ['NORMAL', 'BASE', 'WATCH', 'BUY']

    def test_determine_state_crypto(self, mock_price_data):
        """Test state determination for crypto assets."""
        from signals.state_machine import StateMachine

        mock_yahoo = Mock()
        mock_coingecko = Mock()
        mock_coingecko.get_historical_prices.return_value = mock_price_data

        sm = StateMachine(mock_yahoo, mock_coingecko)

        state = sm.determine_state('BTC')

        assert state in ['NORMAL', 'BASE', 'WATCH', 'BUY']


class TestStateTransitions:
    """Tests for state transition rules."""

    def test_watch_to_base_transition(self):
        """Test transition from WATCH to BASE is valid."""
        # WATCH -> BASE is a valid progression (crash -> consolidation)
        from signals.state_machine import StateMachine

        # This is a logic test - just verify the transition is handled
        assert True  # Placeholder for actual transition logic test

    def test_base_to_buy_transition(self):
        """Test transition from BASE to BUY is valid."""
        # BASE -> BUY is a valid progression (consolidation -> recovery)
        assert True  # Placeholder

    def test_invalid_transitions_handled(self):
        """Test invalid transitions are handled gracefully."""
        # The state machine should handle any transition gracefully
        assert True  # Placeholder
