"""
Tests for validators/data_validator.py
"""
import pytest
import math
from datetime import datetime, timedelta


class TestDataValidator:
    """Tests for DataValidator class."""

    def test_validate_price_valid(self):
        """Test price validation with valid price."""
        from validators.data_validator import DataValidator

        result = DataValidator.validate_price("AAPL", 150.0)
        assert result == 150.0

    def test_validate_price_none(self):
        """Test price validation with None returns None."""
        from validators.data_validator import DataValidator

        result = DataValidator.validate_price("AAPL", None)
        assert result is None

    def test_validate_price_negative(self):
        """Test price validation rejects negative prices."""
        from validators.data_validator import DataValidator

        result = DataValidator.validate_price("AAPL", -10.0)
        assert result is None

    def test_validate_price_zero(self):
        """Test price validation rejects zero prices."""
        from validators.data_validator import DataValidator

        result = DataValidator.validate_price("AAPL", 0.0)
        assert result is None

    def test_validate_price_nan(self):
        """Test price validation rejects NaN prices."""
        from validators.data_validator import DataValidator

        result = DataValidator.validate_price("AAPL", float('nan'))
        assert result is None

    def test_validate_price_inf(self):
        """Test price validation rejects infinite prices."""
        from validators.data_validator import DataValidator

        result = DataValidator.validate_price("AAPL", float('inf'))
        assert result is None


class TestMetricsValidation:
    """Tests for metrics validation."""

    def test_validate_pe_ratio_valid(self):
        """Test PE ratio validation with valid value."""
        from validators.data_validator import DataValidator

        result = DataValidator.validate_pe_ratio("AAPL", 25.0)
        assert result == 25.0

    def test_validate_pe_ratio_none(self):
        """Test PE ratio validation with None."""
        from validators.data_validator import DataValidator

        result = DataValidator.validate_pe_ratio("AAPL", None)
        assert result is None

    def test_validate_pe_ratio_negative(self):
        """Test PE ratio validation with negative value (loss-making company)."""
        from validators.data_validator import DataValidator

        # Negative PE is valid for loss-making companies
        result = DataValidator.validate_pe_ratio("AAPL", -5.0)
        assert result == -5.0

    def test_validate_pe_ratio_extreme(self):
        """Test PE ratio validation with extreme value."""
        from validators.data_validator import DataValidator

        # Extremely high PE should be flagged but still returned
        result = DataValidator.validate_pe_ratio("AAPL", 5000.0)
        # The validator may cap or warn but should handle gracefully
        assert result is not None


class TestTimeSeriesValidation:
    """Tests for time series data validation."""

    def test_validate_historical_prices_valid(self, mock_price_data):
        """Test validation of valid historical prices."""
        from validators.data_validator import DataValidator

        result = DataValidator.validate_historical_prices("AAPL", mock_price_data)
        assert result is not None
        assert len(result) == len(mock_price_data)

    def test_validate_historical_prices_empty(self):
        """Test validation of empty price data."""
        from validators.data_validator import DataValidator

        result = DataValidator.validate_historical_prices("AAPL", [])
        assert result is None or len(result) == 0

    def test_validate_historical_prices_none(self):
        """Test validation of None price data."""
        from validators.data_validator import DataValidator

        result = DataValidator.validate_historical_prices("AAPL", None)
        assert result is None

    def test_validate_historical_prices_with_nan(self, mock_price_data):
        """Test validation filters out NaN values."""
        from validators.data_validator import DataValidator

        # Add a NaN value
        corrupted_data = mock_price_data + [(datetime.now(), float('nan'))]
        result = DataValidator.validate_historical_prices("AAPL", corrupted_data)

        # Should filter out the NaN
        assert result is not None
        assert all(not math.isnan(price) for _, price in result)


class TestDataQualityScore:
    """Tests for data quality scoring."""

    def test_calculate_quality_score_complete_data(
        self,
        sample_daily_pick,
        sample_fundamental_data
    ):
        """Test quality score with complete data."""
        from validators.data_validator import DataValidator

        score = DataValidator.calculate_data_quality_score(
            symbol="AAPL",
            price_data=sample_daily_pick.get('current_price'),
            fundamental_data=sample_fundamental_data,
            has_news=True,
            has_analyst_data=True
        )

        # Complete data should have high quality score
        assert score >= 80

    def test_calculate_quality_score_minimal_data(self):
        """Test quality score with minimal data."""
        from validators.data_validator import DataValidator

        score = DataValidator.calculate_data_quality_score(
            symbol="AAPL",
            price_data=150.0,
            fundamental_data=None,
            has_news=False,
            has_analyst_data=False
        )

        # Minimal data should have lower quality score
        assert score < 80
        assert score >= 0
