"""
Tests for scoring/vms_scorer.py (Value/Momentum/Stability scoring)
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime


class TestVMSScorer:
    """Tests for VMSScorer class."""

    def test_calculate_value_score_high_quality(self, sample_fundamental_data, sample_metrics):
        """Test value score calculation with high quality fundamentals."""
        from scoring.vms_scorer import VMSScorer

        features = {
            'ath_ratio': 0.95,  # Near all-time high
            'return_30d': 0.10,
        }

        score = VMSScorer.calculate_value_score(
            features=features,
            pe_ratio=sample_metrics.get('pe_ratio'),
            fundamental_data=sample_fundamental_data
        )

        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_calculate_value_score_no_fundamentals(self):
        """Test value score with minimal data."""
        from scoring.vms_scorer import VMSScorer

        features = {
            'ath_ratio': 0.70,
        }

        score = VMSScorer.calculate_value_score(
            features=features,
            pe_ratio=None,
            fundamental_data=None
        )

        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_calculate_value_score_undervalued(self):
        """Test value score for potentially undervalued stock."""
        from scoring.vms_scorer import VMSScorer

        features = {
            'ath_ratio': 0.50,  # 50% from ATH - potentially undervalued
        }

        fundamental_data = {
            'fcf': 50_000_000_000,
            'revenue_growth': 0.20,  # Strong growth
            'profit_margin': 0.30,   # High margins
        }

        score = VMSScorer.calculate_value_score(
            features=features,
            pe_ratio=15.0,  # Reasonable PE
            fundamental_data=fundamental_data
        )

        # Should have higher value score due to low ATH ratio with good fundamentals
        assert score >= 60


class TestMomentumScore:
    """Tests for momentum score calculation."""

    def test_calculate_momentum_score_buy_state(self):
        """Test momentum score for BUY state."""
        from scoring.vms_scorer import VMSScorer

        features = {
            'return_30d': 0.15,
            'return_7d': 0.08,
            'return_3d': 0.03,
            'breakout_5d': True,
        }

        score = VMSScorer.calculate_momentum_score(
            features=features,
            current_state='BUY',
            events=None,
            analyst_data=None
        )

        assert isinstance(score, float)
        assert 0 <= score <= 100
        # BUY state should contribute positively to momentum
        assert score >= 50

    def test_calculate_momentum_score_watch_state(self):
        """Test momentum score for WATCH state (negative momentum)."""
        from scoring.vms_scorer import VMSScorer

        features = {
            'return_30d': -0.20,
            'return_7d': -0.10,
            'return_3d': -0.15,
            'breakout_5d': False,
        }

        score = VMSScorer.calculate_momentum_score(
            features=features,
            current_state='WATCH',
            events=None,
            analyst_data=None
        )

        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_calculate_momentum_score_with_positive_events(self, sample_news_items):
        """Test momentum score boost from positive events."""
        from scoring.vms_scorer import VMSScorer

        features = {
            'return_30d': 0.05,
            'breakout_5d': False,
        }

        events = [
            {'title': 'Earnings beat', 'impact': 'positive', 'event_type': 'earnings'},
        ]

        score_with_events = VMSScorer.calculate_momentum_score(
            features=features,
            current_state='NORMAL',
            events=events,
            analyst_data={'recommendation': 'Buy'}
        )

        score_without_events = VMSScorer.calculate_momentum_score(
            features=features,
            current_state='NORMAL',
            events=None,
            analyst_data=None
        )

        # Positive events should boost momentum score
        assert score_with_events >= score_without_events


class TestStabilityScore:
    """Tests for stability score calculation."""

    def test_calculate_stability_score_low_volatility(self):
        """Test stability score for low volatility stock."""
        from scoring.vms_scorer import VMSScorer

        features = {
            'volatility': 0.10,  # 10% volatility - low
        }

        fundamental_data = {
            'financial_health_score': 90.0,
            'debt_to_equity': 0.5,  # Low debt
        }

        score = VMSScorer.calculate_stability_score(
            features=features,
            fundamental_data=fundamental_data,
            market_volatility=0.20
        )

        assert isinstance(score, float)
        assert 0 <= score <= 100
        # Low volatility should result in higher stability
        assert score >= 60

    def test_calculate_stability_score_high_volatility(self):
        """Test stability score for high volatility asset."""
        from scoring.vms_scorer import VMSScorer

        features = {
            'volatility': 0.50,  # 50% volatility - high (crypto-like)
        }

        score = VMSScorer.calculate_stability_score(
            features=features,
            fundamental_data=None,
            market_volatility=0.20
        )

        assert isinstance(score, float)
        assert 0 <= score <= 100
        # High volatility should result in lower stability
        assert score <= 70

    def test_calculate_stability_score_healthy_fundamentals(self):
        """Test stability score with healthy fundamentals."""
        from scoring.vms_scorer import VMSScorer

        features = {
            'volatility': 0.20,
        }

        fundamental_data = {
            'financial_health_score': 95.0,
            'debt_to_equity': 0.3,
            'current_ratio': 2.0,  # Strong liquidity
        }

        score = VMSScorer.calculate_stability_score(
            features=features,
            fundamental_data=fundamental_data,
            market_volatility=0.20
        )

        # Healthy fundamentals should boost stability
        assert score >= 70


class TestTotalScoreCalculation:
    """Tests for total score calculation with weights."""

    def test_calculate_all_scores(self, sample_fundamental_data):
        """Test complete score calculation."""
        from scoring.vms_scorer import VMSScorer

        features = {
            'ath_ratio': 0.85,
            'return_30d': 0.10,
            'return_7d': 0.05,
            'return_3d': 0.02,
            'volatility': 0.15,
            'breakout_5d': True,
        }

        scores = VMSScorer.calculate_all_scores(
            features=features,
            current_state='BUY',
            pe_ratio=25.0,
            fundamental_data=sample_fundamental_data,
            events=None,
            analyst_data=None
        )

        assert 'value_score' in scores
        assert 'momentum_score' in scores
        assert 'stability_score' in scores
        assert 'total_score' in scores

        # All scores should be in valid range
        for key, value in scores.items():
            if 'score' in key:
                assert 0 <= value <= 100

    def test_score_weights_sum_to_one(self):
        """Test that default weights sum to 1.0."""
        from scoring.vms_scorer import VMSScorer

        # Default weights should be: Value 40%, Momentum 35%, Stability 25%
        weights = VMSScorer.get_default_weights()

        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01  # Allow small floating point error

    def test_total_score_is_weighted_average(self, sample_fundamental_data):
        """Test that total score is correctly weighted."""
        from scoring.vms_scorer import VMSScorer

        features = {
            'ath_ratio': 0.80,
            'return_30d': 0.05,
            'volatility': 0.20,
        }

        scores = VMSScorer.calculate_all_scores(
            features=features,
            current_state='NORMAL',
            pe_ratio=20.0,
            fundamental_data=sample_fundamental_data
        )

        # Verify total is reasonable weighted combination
        v = scores['value_score']
        m = scores['momentum_score']
        s = scores['stability_score']

        # With default weights (0.4, 0.35, 0.25)
        expected_total = v * 0.4 + m * 0.35 + s * 0.25

        # Allow some tolerance for implementation differences
        assert abs(scores['total_score'] - expected_total) < 5.0


class TestDynamicWeights:
    """Tests for dynamic weight adjustment."""

    def test_dynamic_weights_high_volatility(self):
        """Test weight adjustment for high market volatility."""
        from scoring.vms_scorer import VMSScorer

        features = {
            'ath_ratio': 0.80,
            'return_30d': 0.05,
            'volatility': 0.40,  # High volatility
        }

        scores = VMSScorer.calculate_all_scores(
            features=features,
            current_state='WATCH',
            use_dynamic_weights=True,
            market_volatility=0.40  # High market volatility
        )

        assert scores is not None
        assert 'weights_used' in scores or 'total_score' in scores

    def test_dynamic_weights_low_volatility(self):
        """Test weight adjustment for low market volatility."""
        from scoring.vms_scorer import VMSScorer

        features = {
            'ath_ratio': 0.90,
            'return_30d': 0.10,
            'volatility': 0.10,  # Low volatility
        }

        scores = VMSScorer.calculate_all_scores(
            features=features,
            current_state='BUY',
            use_dynamic_weights=True,
            market_volatility=0.10  # Low market volatility
        )

        assert scores is not None


class TestEdgeCases:
    """Tests for edge cases in scoring."""

    def test_score_with_none_features(self):
        """Test scoring handles None features gracefully."""
        from scoring.vms_scorer import VMSScorer

        features = {}  # Empty features

        scores = VMSScorer.calculate_all_scores(
            features=features,
            current_state='NORMAL'
        )

        # Should return valid scores even with missing data
        assert scores is not None
        assert 'total_score' in scores

    def test_score_with_extreme_values(self):
        """Test scoring handles extreme values."""
        from scoring.vms_scorer import VMSScorer

        features = {
            'ath_ratio': 0.01,  # 99% from ATH
            'return_30d': -0.90,  # 90% loss
            'volatility': 1.0,  # 100% volatility
        }

        scores = VMSScorer.calculate_all_scores(
            features=features,
            current_state='WATCH'
        )

        # Scores should still be bounded 0-100
        assert 0 <= scores['total_score'] <= 100
