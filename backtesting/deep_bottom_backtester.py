"""
Deep Bottom Backtesting Engine
Validates historical performance of Deep Bottom signals

Tests if Deep Bottom signals historically led to significant gains (50%+)
within 12 months.
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signals.state_machine import StateMachine, is_crypto_symbol
from features.indicators import FeatureCalculator
from features.pattern_detector import PatternDetector
from fetchers import YahooFetcher, CoinGeckoFetcher
from core.constants import (
    DEEP_BOTTOM_BACKTEST_CONFIG,
    DEEP_BOTTOM_THRESHOLDS,
    RISK_MANAGEMENT_CONFIG,
    PATTERN_DETECTION_CONFIG
)
from portfolio.risk_manager import PositionSizer, ExitStrategyManager, PortfolioRiskCalculator

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Type of Deep Bottom signal detected"""
    BASIC = "basic"
    ADVANCED = "advanced"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


@dataclass
class DeepBottomSignal:
    """Represents a detected Deep Bottom signal"""
    symbol: str
    signal_date: datetime
    signal_type: SignalType
    entry_price: float
    drawdown_pct: float
    rsi: float
    score: Optional[float] = None
    metrics_snapshot: Dict = field(default_factory=dict)


@dataclass
class SignalOutcome:
    """Tracks the outcome of a Deep Bottom signal"""
    signal: DeepBottomSignal
    return_3m: Optional[float] = None
    return_6m: Optional[float] = None
    return_12m: Optional[float] = None
    max_drawdown_after: float = 0.0
    days_to_50pct: Optional[int] = None
    peak_return: float = 0.0
    is_winner: bool = False  # True if achieved 50%+ within 12 months

    def to_dict(self) -> Dict:
        return {
            'symbol': self.signal.symbol,
            'signal_date': self.signal.signal_date.isoformat(),
            'signal_type': self.signal.signal_type.value,
            'entry_price': self.signal.entry_price,
            'drawdown_pct': self.signal.drawdown_pct,
            'rsi': self.signal.rsi,
            'score': self.signal.score,
            'return_3m': self.return_3m,
            'return_6m': self.return_6m,
            'return_12m': self.return_12m,
            'max_drawdown_after': self.max_drawdown_after,
            'days_to_50pct': self.days_to_50pct,
            'peak_return': self.peak_return,
            'is_winner': self.is_winner,
        }


@dataclass
class BacktestResult:
    """Aggregated backtest results"""
    symbol: str
    start_date: datetime
    end_date: datetime
    total_signals: int
    winners: int
    win_rate: float
    avg_return_3m: float
    avg_return_6m: float
    avg_return_12m: float
    avg_max_drawdown: float
    avg_days_to_target: Optional[float]
    best_signal: Optional[SignalOutcome]
    worst_signal: Optional[SignalOutcome]
    outcomes: List[SignalOutcome]

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'total_signals': self.total_signals,
            'winners': self.winners,
            'win_rate': self.win_rate,
            'avg_return_3m': self.avg_return_3m,
            'avg_return_6m': self.avg_return_6m,
            'avg_return_12m': self.avg_return_12m,
            'avg_max_drawdown': self.avg_max_drawdown,
            'avg_days_to_target': self.avg_days_to_target,
            'outcomes': [o.to_dict() for o in self.outcomes],
        }


@dataclass
class V2SignalMetrics:
    """V2 signal metrics with volume confirmation and sync bonuses"""
    total_score: float
    signal_strength: Optional[str]  # 'strong', 'moderate', 'weak'
    confidence: int  # 50-95
    volume_confirmed: bool
    component_scores: Dict = field(default_factory=dict)
    risk_factors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'total_score': self.total_score,
            'signal_strength': self.signal_strength,
            'confidence': self.confidence,
            'volume_confirmed': self.volume_confirmed,
            'component_scores': self.component_scores,
            'risk_factors': self.risk_factors,
        }


@dataclass
class V2ComparisonResult:
    """Comparison result between V1 and V2 scoring"""
    symbol: str
    period: str
    v1_result: Optional[BacktestResult]
    v2_result: Optional[BacktestResult]
    comparison_metrics: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'period': self.period,
            'v1_result': self.v1_result.to_dict() if self.v1_result else None,
            'v2_result': self.v2_result.to_dict() if self.v2_result else None,
            'comparison_metrics': self.comparison_metrics,
        }


class DeepBottomBacktester:
    """
    Backtest Deep Bottom detection strategy.

    Key metrics:
    - Win rate (% achieving 50%+ in 12 months)
    - Average return at 3/6/12 month marks
    - Maximum drawdown after signal
    - Time to recovery
    """

    # Known historical crash periods for specialized testing
    CRASH_PERIODS = {
        'btc_2018': {
            'symbol': 'BTC',
            'name': 'BTC Dec 2018 Bottom',
            'start': '2018-11-01',
            'end': '2019-02-28',
            'expected_bottom': '2018-12-15'
        },
        'covid_2020': {
            'symbol': 'SPY',
            'name': 'COVID Crash Mar 2020',
            'start': '2020-02-15',
            'end': '2020-04-30',
            'expected_bottom': '2020-03-23'
        },
        'crypto_2022': {
            'symbol': 'BTC',
            'name': 'Crypto Winter Nov 2022',
            'start': '2022-10-01',
            'end': '2023-01-31',
            'expected_bottom': '2022-11-21'
        },
        'tech_crash_2022': {
            'symbol': 'QQQ',
            'name': 'Tech Selloff 2022',
            'start': '2022-09-01',
            'end': '2023-01-31',
            'expected_bottom': '2022-10-13'
        }
    }

    def __init__(self):
        self.yahoo_fetcher = YahooFetcher()
        self.coingecko_fetcher = CoinGeckoFetcher()
        self.config = DEEP_BOTTOM_BACKTEST_CONFIG

    def backtest_symbol(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        detection_mode: str = 'both'
    ) -> Optional[BacktestResult]:
        """
        Backtest a single symbol over a date range.

        Args:
            symbol: Stock or crypto symbol
            start_date: Start of backtest period
            end_date: End of backtest period
            detection_mode: 'basic', 'advanced', or 'both'

        Returns:
            BacktestResult with all signals and outcomes
        """
        logger.info(f"Backtesting {symbol} from {start_date} to {end_date}")

        # Get extended historical data
        prices = self._get_extended_prices(symbol, start_date, end_date)
        if not prices or len(prices) < 365:
            logger.warning(f"Insufficient data for {symbol}")
            return None

        # Detect signals
        signals = self._detect_signals_in_range(
            symbol, prices, start_date, end_date, detection_mode
        )

        if not signals:
            logger.info(f"No signals detected for {symbol}")
            return BacktestResult(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                total_signals=0,
                winners=0,
                win_rate=0.0,
                avg_return_3m=0.0,
                avg_return_6m=0.0,
                avg_return_12m=0.0,
                avg_max_drawdown=0.0,
                avg_days_to_target=None,
                best_signal=None,
                worst_signal=None,
                outcomes=[]
            )

        # Calculate outcomes for each signal
        outcomes = self._calculate_outcomes(signals, prices)

        # Aggregate metrics
        return self._aggregate_results(symbol, start_date, end_date, outcomes)

    def _get_extended_prices(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[List[Tuple[datetime, float]]]:
        """Get extended historical prices for backtesting"""
        # Need extra data before start_date for lookback window
        lookback_start = start_date - timedelta(days=400)
        # Need extra data after end_date for outcome measurement
        forward_end = end_date + timedelta(days=400)

        if is_crypto_symbol(symbol):
            return self.coingecko_fetcher.get_historical_prices_extended(
                symbol, lookback_start, forward_end
            )
        else:
            return self.yahoo_fetcher.get_historical_prices_extended(
                symbol, lookback_start, forward_end
            )

    def _detect_signals_in_range(
        self,
        symbol: str,
        prices: List[Tuple[datetime, float]],
        start_date: datetime,
        end_date: datetime,
        detection_mode: str
    ) -> List[DeepBottomSignal]:
        """
        Detect all Deep Bottom signals within the date range.

        Uses rolling window analysis to simulate real-time detection.
        """
        signals = []
        last_signal_date = None

        # Convert prices to dict for easier lookup
        price_dict = {p[0].date(): p[1] for p in prices}
        price_dates = sorted(price_dict.keys())

        for i, current_date in enumerate(price_dates):
            dt = datetime.combine(current_date, datetime.min.time())

            # Only check within backtest range
            if dt < start_date or dt > end_date:
                continue

            # Minimum days between signals
            if last_signal_date:
                days_since = (dt - last_signal_date).days
                if days_since < self.config.MIN_DAYS_BETWEEN_SIGNALS:
                    continue

            # Build lookback window (365 days)
            lookback_prices = []
            for j in range(max(0, i - 365), i + 1):
                date = price_dates[j]
                lookback_prices.append((
                    datetime.combine(date, datetime.min.time()),
                    price_dict[date]
                ))

            if len(lookback_prices) < 100:
                continue

            # Run detection
            signal = self._check_signal(symbol, lookback_prices, detection_mode)

            if signal:
                signal.signal_date = dt
                signals.append(signal)
                last_signal_date = dt
                logger.debug(f"Signal detected for {symbol} on {dt.date()}")

        return signals

    def _check_signal(
        self,
        symbol: str,
        prices: List[Tuple[datetime, float]],
        detection_mode: str
    ) -> Optional[DeepBottomSignal]:
        """Check if current point triggers a Deep Bottom signal"""
        current_price = prices[-1][1]

        # Calculate indicators
        drawdown = FeatureCalculator.calculate_drawdown_from_ath(prices)
        week52_proximity = FeatureCalculator.calculate_52week_low_proximity(prices)
        rsi = FeatureCalculator.calculate_rsi(prices, 14)
        ma_200 = FeatureCalculator.calculate_moving_average(prices, 200)
        return_7d = FeatureCalculator.calculate_return(prices, 7)

        if None in [drawdown, week52_proximity, rsi, return_7d]:
            return None

        # Basic conditions
        basic_conditions = {
            'ath_drawdown': drawdown >= DEEP_BOTTOM_THRESHOLDS.ATH_DRAWDOWN_MIN,
            'near_52week_low': week52_proximity <= DEEP_BOTTOM_THRESHOLDS.WEEK52_LOW_PROXIMITY_MAX,
            'rsi_oversold': rsi <= DEEP_BOTTOM_THRESHOLDS.RSI_OVERSOLD,
            'below_ma200': ma_200 is not None and current_price < ma_200,
            'not_crashing': return_7d > DEEP_BOTTOM_THRESHOLDS.MIN_7D_RETURN
        }

        basic_met = sum(1 for v in basic_conditions.values() if v)

        # Check based on mode
        signal_type = None
        score = None

        if detection_mode in ['basic', 'both']:
            if all(basic_conditions.values()):
                signal_type = SignalType.BASIC

        if detection_mode in ['advanced', 'both']:
            # Advanced scoring
            deep_score = FeatureCalculator.calculate_deep_bottom_score(prices)

            if deep_score:
                score = deep_score.get('total_score', 0)

                # Advanced conditions
                if score >= 70:
                    signal_type = SignalType.STRONG
                elif score >= 50 and basic_met >= 4:
                    signal_type = SignalType.MODERATE
                elif basic_met >= 4:
                    signal_type = SignalType.WEAK

        if signal_type:
            return DeepBottomSignal(
                symbol=symbol,
                signal_date=prices[-1][0],
                signal_type=signal_type,
                entry_price=current_price,
                drawdown_pct=drawdown,
                rsi=rsi,
                score=score,
                metrics_snapshot={
                    'basic_conditions': basic_conditions,
                    'week52_proximity': week52_proximity,
                    'ma_200': ma_200,
                    'return_7d': return_7d
                }
            )

        return None

    def _calculate_outcomes(
        self,
        signals: List[DeepBottomSignal],
        prices: List[Tuple[datetime, float]]
    ) -> List[SignalOutcome]:
        """Calculate outcomes for each signal"""
        outcomes = []
        price_dict = {p[0].date(): p[1] for p in prices}

        for signal in signals:
            outcome = self._calculate_single_outcome(signal, price_dict)
            outcomes.append(outcome)

        return outcomes

    def _calculate_single_outcome(
        self,
        signal: DeepBottomSignal,
        price_dict: Dict
    ) -> SignalOutcome:
        """Calculate outcome for a single signal"""
        entry_date = signal.signal_date.date()
        entry_price = signal.entry_price

        # Calculate returns at intervals
        return_3m = self._get_return_at_days(price_dict, entry_date, entry_price, 90)
        return_6m = self._get_return_at_days(price_dict, entry_date, entry_price, 180)
        return_12m = self._get_return_at_days(price_dict, entry_date, entry_price, 365)

        # Calculate max drawdown and peak return after signal
        max_dd = 0.0
        peak_return = 0.0
        days_to_50pct = None

        sorted_dates = sorted(price_dict.keys())
        entry_idx = None
        for i, d in enumerate(sorted_dates):
            if d >= entry_date:
                entry_idx = i
                break

        if entry_idx is not None:
            peak_price = entry_price
            for i in range(entry_idx, min(entry_idx + 365, len(sorted_dates))):
                date = sorted_dates[i]
                price = price_dict[date]

                current_return = (price - entry_price) / entry_price * 100
                peak_return = max(peak_return, current_return)

                # Check for 50% target
                if days_to_50pct is None and current_return >= 50:
                    days_to_50pct = (date - entry_date).days

                # Track drawdown from peak
                if price > peak_price:
                    peak_price = price
                dd = (peak_price - price) / peak_price * 100
                max_dd = max(max_dd, dd)

        is_winner = return_12m is not None and return_12m >= self.config.TARGET_RETURN_PCT

        return SignalOutcome(
            signal=signal,
            return_3m=return_3m,
            return_6m=return_6m,
            return_12m=return_12m,
            max_drawdown_after=max_dd,
            days_to_50pct=days_to_50pct,
            peak_return=peak_return,
            is_winner=is_winner
        )

    def _get_return_at_days(
        self,
        price_dict: Dict,
        entry_date,
        entry_price: float,
        days: int
    ) -> Optional[float]:
        """Get return at specific number of days after entry"""
        target_date = entry_date + timedelta(days=days)

        # Find closest available date
        for offset in range(0, 7):
            check_date = target_date + timedelta(days=offset)
            if check_date in price_dict:
                return (price_dict[check_date] - entry_price) / entry_price * 100

            check_date = target_date - timedelta(days=offset)
            if check_date in price_dict:
                return (price_dict[check_date] - entry_price) / entry_price * 100

        return None

    def _aggregate_results(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        outcomes: List[SignalOutcome]
    ) -> BacktestResult:
        """Aggregate individual outcomes into summary statistics"""
        if not outcomes:
            return BacktestResult(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                total_signals=0,
                winners=0,
                win_rate=0.0,
                avg_return_3m=0.0,
                avg_return_6m=0.0,
                avg_return_12m=0.0,
                avg_max_drawdown=0.0,
                avg_days_to_target=None,
                best_signal=None,
                worst_signal=None,
                outcomes=[]
            )

        total = len(outcomes)
        winners = sum(1 for o in outcomes if o.is_winner)

        # Calculate averages (excluding None values)
        returns_3m = [o.return_3m for o in outcomes if o.return_3m is not None]
        returns_6m = [o.return_6m for o in outcomes if o.return_6m is not None]
        returns_12m = [o.return_12m for o in outcomes if o.return_12m is not None]
        drawdowns = [o.max_drawdown_after for o in outcomes]
        days_to_target = [o.days_to_50pct for o in outcomes if o.days_to_50pct is not None]

        avg_return_3m = sum(returns_3m) / len(returns_3m) if returns_3m else 0.0
        avg_return_6m = sum(returns_6m) / len(returns_6m) if returns_6m else 0.0
        avg_return_12m = sum(returns_12m) / len(returns_12m) if returns_12m else 0.0
        avg_max_dd = sum(drawdowns) / len(drawdowns) if drawdowns else 0.0
        avg_days = sum(days_to_target) / len(days_to_target) if days_to_target else None

        # Best and worst signals
        best_signal = max(outcomes, key=lambda o: o.return_12m or -999) if returns_12m else None
        worst_signal = min(outcomes, key=lambda o: o.return_12m or 999) if returns_12m else None

        return BacktestResult(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            total_signals=total,
            winners=winners,
            win_rate=(winners / total * 100) if total > 0 else 0.0,
            avg_return_3m=avg_return_3m,
            avg_return_6m=avg_return_6m,
            avg_return_12m=avg_return_12m,
            avg_max_drawdown=avg_max_dd,
            avg_days_to_target=avg_days,
            best_signal=best_signal,
            worst_signal=worst_signal,
            outcomes=outcomes
        )

    # ========== V2 BACKTEST METHODS ==========

    def _get_extended_prices_with_volume(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[List[Tuple[datetime, float, float]]]:
        """
        Get extended historical prices with volume for V2 backtesting.

        Returns:
            List of (datetime, price, volume) tuples, or None if unavailable
        """
        # Calculate total days needed (lookback + range + forward)
        lookback_start = start_date - timedelta(days=400)
        forward_end = end_date + timedelta(days=400)
        total_days = (forward_end - lookback_start).days

        try:
            if is_crypto_symbol(symbol):
                # CoinGecko returns prices with volume
                data = self.coingecko_fetcher.get_historical_prices_with_volume(
                    symbol, days=total_days
                )
            else:
                # Yahoo Finance returns OHLCV data
                data = self.yahoo_fetcher.get_historical_prices_with_volume(
                    symbol, days=total_days
                )

            if data:
                # Filter to our date range
                return [
                    (dt, price, vol) for dt, price, vol in data
                    if lookback_start <= dt <= forward_end
                ]
            return None
        except Exception as e:
            logger.warning(f"Failed to get volume data for {symbol}: {e}")
            return None

    def _check_signal_v2(
        self,
        symbol: str,
        prices: List[Tuple[datetime, float]],
        prices_with_volume: List[Tuple[datetime, float, float]] = None,
        min_confidence: int = 50
    ) -> Optional[Tuple[DeepBottomSignal, V2SignalMetrics]]:
        """
        Check if current point triggers a V2 Deep Bottom signal.

        Args:
            symbol: Stock or crypto symbol
            prices: List of (datetime, price) tuples
            prices_with_volume: Optional list of (datetime, price, volume) tuples
            min_confidence: Minimum confidence threshold (default 50)

        Returns:
            Tuple of (DeepBottomSignal, V2SignalMetrics) if signal detected, None otherwise
        """
        current_price = prices[-1][1]

        # Calculate V2 score
        v2_result = FeatureCalculator.calculate_deep_bottom_score_v2(
            prices, prices_with_volume
        )

        if not v2_result:
            return None

        total_score = v2_result.get('total_score', 0)
        signal_strength = v2_result.get('signal_strength')
        confidence = v2_result.get('confidence', 0)
        volume_confirmed = v2_result.get('volume_confirmed', False)
        component_scores = v2_result.get('component_scores', {})
        risk_info = v2_result.get('risk', {})

        # Check minimum confidence
        if confidence < min_confidence:
            return None

        # Must have a signal strength
        if signal_strength is None:
            return None

        # Map signal strength to SignalType
        signal_type_map = {
            'strong': SignalType.STRONG,
            'moderate': SignalType.MODERATE,
            'weak': SignalType.WEAK
        }
        signal_type = signal_type_map.get(signal_strength, SignalType.WEAK)

        # Calculate basic indicators for the signal
        drawdown = FeatureCalculator.calculate_drawdown_from_ath(prices) or 0
        rsi = FeatureCalculator.calculate_rsi(prices, 14) or 50

        # Extract risk factors
        risk_factors = []
        if risk_info:
            if risk_info.get('recent_spike', 0) > 0:
                risk_factors.append('recent_spike')
            if risk_info.get('high_volatility', 0) > 0:
                risk_factors.append('high_volatility')
            if risk_info.get('thin_volume', 0) > 0:
                risk_factors.append('thin_volume')

        signal = DeepBottomSignal(
            symbol=symbol,
            signal_date=prices[-1][0],
            signal_type=signal_type,
            entry_price=current_price,
            drawdown_pct=drawdown,
            rsi=rsi,
            score=total_score,
            metrics_snapshot={
                'v2_component_scores': component_scores,
                'confidence': confidence,
                'volume_confirmed': volume_confirmed
            }
        )

        metrics = V2SignalMetrics(
            total_score=total_score,
            signal_strength=signal_strength,
            confidence=confidence,
            volume_confirmed=volume_confirmed,
            component_scores=component_scores,
            risk_factors=risk_factors
        )

        return (signal, metrics)

    def _detect_signals_in_range_v2(
        self,
        symbol: str,
        prices: List[Tuple[datetime, float]],
        prices_with_volume: List[Tuple[datetime, float, float]],
        start_date: datetime,
        end_date: datetime,
        min_confidence: int = 50,
        volume_filter: bool = True
    ) -> List[Tuple[DeepBottomSignal, V2SignalMetrics]]:
        """
        Detect all V2 Deep Bottom signals within the date range.

        Args:
            symbol: Stock or crypto symbol
            prices: List of (datetime, price) tuples
            prices_with_volume: List of (datetime, price, volume) tuples
            start_date: Start of detection range
            end_date: End of detection range
            min_confidence: Minimum confidence threshold
            volume_filter: If True, only return volume-confirmed signals

        Returns:
            List of (DeepBottomSignal, V2SignalMetrics) tuples
        """
        signals = []
        last_signal_date = None

        # Convert prices to dict for easier lookup
        price_dict = {p[0].date(): p[1] for p in prices}
        volume_dict = {}
        if prices_with_volume:
            volume_dict = {p[0].date(): (p[1], p[2]) for p in prices_with_volume}

        price_dates = sorted(price_dict.keys())

        for i, current_date in enumerate(price_dates):
            dt = datetime.combine(current_date, datetime.min.time())

            # Only check within backtest range
            if dt < start_date or dt > end_date:
                continue

            # Minimum days between signals
            if last_signal_date:
                days_since = (dt - last_signal_date).days
                if days_since < self.config.MIN_DAYS_BETWEEN_SIGNALS:
                    continue

            # Build lookback window (365 days)
            lookback_prices = []
            lookback_with_volume = []

            for j in range(max(0, i - 365), i + 1):
                date = price_dates[j]
                lookback_prices.append((
                    datetime.combine(date, datetime.min.time()),
                    price_dict[date]
                ))
                if date in volume_dict:
                    pv = volume_dict[date]
                    lookback_with_volume.append((
                        datetime.combine(date, datetime.min.time()),
                        pv[0], pv[1]
                    ))

            if len(lookback_prices) < 100:
                continue

            # Run V2 detection
            result = self._check_signal_v2(
                symbol,
                lookback_prices,
                lookback_with_volume if lookback_with_volume else None,
                min_confidence
            )

            if result:
                signal, metrics = result

                # Apply volume filter if enabled
                if volume_filter and not metrics.volume_confirmed:
                    continue

                signal.signal_date = dt
                signals.append((signal, metrics))
                last_signal_date = dt
                logger.debug(
                    f"V2 Signal detected for {symbol} on {dt.date()}: "
                    f"confidence={metrics.confidence}, volume_confirmed={metrics.volume_confirmed}"
                )

        return signals

    def backtest_symbol_v2(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        min_confidence: int = 50,
        volume_filter: bool = True
    ) -> Optional[BacktestResult]:
        """
        Backtest a single symbol using V2 scoring.

        Args:
            symbol: Stock or crypto symbol
            start_date: Start of backtest period
            end_date: End of backtest period
            min_confidence: Minimum confidence threshold (default 50)
            volume_filter: If True, only consider volume-confirmed signals

        Returns:
            BacktestResult with V2 signals and outcomes
        """
        logger.info(f"V2 Backtesting {symbol} from {start_date} to {end_date}")

        # Get extended historical data with volume
        prices = self._get_extended_prices(symbol, start_date, end_date)
        prices_with_volume = self._get_extended_prices_with_volume(symbol, start_date, end_date)

        if not prices or len(prices) < 365:
            logger.warning(f"Insufficient price data for {symbol}")
            return None

        # Detect V2 signals
        v2_signals = self._detect_signals_in_range_v2(
            symbol, prices, prices_with_volume,
            start_date, end_date,
            min_confidence, volume_filter
        )

        if not v2_signals:
            logger.info(f"No V2 signals detected for {symbol}")
            return BacktestResult(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                total_signals=0,
                winners=0,
                win_rate=0.0,
                avg_return_3m=0.0,
                avg_return_6m=0.0,
                avg_return_12m=0.0,
                avg_max_drawdown=0.0,
                avg_days_to_target=None,
                best_signal=None,
                worst_signal=None,
                outcomes=[]
            )

        # Extract just the signals for outcome calculation
        signals = [s[0] for s in v2_signals]

        # Calculate outcomes for each signal
        outcomes = self._calculate_outcomes(signals, prices)

        # Store V2 metrics in outcomes
        for i, outcome in enumerate(outcomes):
            if i < len(v2_signals):
                _, v2_metrics = v2_signals[i]
                outcome.signal.metrics_snapshot['v2_metrics'] = v2_metrics.to_dict()

        # Aggregate metrics
        return self._aggregate_results(symbol, start_date, end_date, outcomes)

    def compare_v1_vs_v2(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        min_confidence_v2: int = 50,
        volume_filter_v2: bool = True
    ) -> V2ComparisonResult:
        """
        Compare V1 (score-based) vs V2 (volume-enhanced) performance.

        Args:
            symbol: Stock or crypto symbol
            start_date: Start of backtest period
            end_date: End of backtest period
            min_confidence_v2: Minimum confidence for V2 signals
            volume_filter_v2: Whether to apply volume filter for V2

        Returns:
            V2ComparisonResult with side-by-side metrics
        """
        logger.info(f"Comparing V1 vs V2 for {symbol} from {start_date} to {end_date}")

        # Run V1 backtest (advanced mode = score-based)
        v1_result = self.backtest_symbol(symbol, start_date, end_date, 'advanced')

        # Run V2 backtest
        v2_result = self.backtest_symbol_v2(
            symbol, start_date, end_date,
            min_confidence_v2, volume_filter_v2
        )

        # Calculate comparison metrics
        comparison_metrics = {}

        if v1_result and v2_result:
            # Win rate comparison
            comparison_metrics['win_rate_diff'] = v2_result.win_rate - v1_result.win_rate
            comparison_metrics['win_rate_improvement'] = (
                ((v2_result.win_rate - v1_result.win_rate) / v1_result.win_rate * 100)
                if v1_result.win_rate > 0 else 0
            )

            # Signal count comparison
            comparison_metrics['signal_count_v1'] = v1_result.total_signals
            comparison_metrics['signal_count_v2'] = v2_result.total_signals
            comparison_metrics['signal_reduction'] = (
                ((v1_result.total_signals - v2_result.total_signals) / v1_result.total_signals * 100)
                if v1_result.total_signals > 0 else 0
            )

            # Return comparison
            comparison_metrics['avg_return_12m_diff'] = v2_result.avg_return_12m - v1_result.avg_return_12m

            # Volume confirmation rate (from V2 signals)
            if v2_result.outcomes:
                volume_confirmed_count = sum(
                    1 for o in v2_result.outcomes
                    if o.signal.metrics_snapshot.get('v2_metrics', {}).get('volume_confirmed', False)
                )
                comparison_metrics['volume_confirmation_rate'] = (
                    volume_confirmed_count / len(v2_result.outcomes) * 100
                )
            else:
                comparison_metrics['volume_confirmation_rate'] = 0

            # Confidence distribution
            confidences = [
                o.signal.metrics_snapshot.get('v2_metrics', {}).get('confidence', 0)
                for o in v2_result.outcomes
                if 'v2_metrics' in o.signal.metrics_snapshot
            ]
            if confidences:
                comparison_metrics['avg_confidence'] = sum(confidences) / len(confidences)
                comparison_metrics['confidence_distribution'] = {
                    'high_75_plus': sum(1 for c in confidences if c >= 75),
                    'moderate_55_74': sum(1 for c in confidences if 55 <= c < 75),
                    'low_below_55': sum(1 for c in confidences if c < 55)
                }

            # Determine winner
            if v2_result.win_rate > v1_result.win_rate:
                comparison_metrics['winner'] = 'v2'
            elif v1_result.win_rate > v2_result.win_rate:
                comparison_metrics['winner'] = 'v1'
            else:
                # Tie-breaker: use average return
                if v2_result.avg_return_12m > v1_result.avg_return_12m:
                    comparison_metrics['winner'] = 'v2'
                else:
                    comparison_metrics['winner'] = 'v1'

        return V2ComparisonResult(
            symbol=symbol,
            period=f"{start_date.date()} to {end_date.date()}",
            v1_result=v1_result,
            v2_result=v2_result,
            comparison_metrics=comparison_metrics
        )

    def backtest_crash_period(self, period_name: str) -> Optional[BacktestResult]:
        """
        Specialized backtest for known crash periods.

        Args:
            period_name: Key from CRASH_PERIODS dict

        Returns:
            BacktestResult for that crash period
        """
        if period_name not in self.CRASH_PERIODS:
            logger.error(f"Unknown crash period: {period_name}")
            return None

        period = self.CRASH_PERIODS[period_name]
        start_date = datetime.strptime(period['start'], '%Y-%m-%d')
        end_date = datetime.strptime(period['end'], '%Y-%m-%d')

        result = self.backtest_symbol(
            period['symbol'],
            start_date,
            end_date,
            detection_mode='both'
        )

        if result:
            logger.info(
                f"Crash period {period_name}: "
                f"{result.total_signals} signals, "
                f"{result.win_rate:.1f}% win rate, "
                f"avg 12m return: {result.avg_return_12m:.1f}%"
            )

        return result

    def compare_basic_vs_advanced(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Compare performance of basic vs advanced detection methods.

        Returns:
            Dict with 'basic' and 'advanced' BacktestResults
        """
        basic_result = self.backtest_symbol(symbol, start_date, end_date, 'basic')
        advanced_result = self.backtest_symbol(symbol, start_date, end_date, 'advanced')

        comparison = {
            'symbol': symbol,
            'period': f"{start_date.date()} to {end_date.date()}",
            'basic': basic_result.to_dict() if basic_result else None,
            'advanced': advanced_result.to_dict() if advanced_result else None,
        }

        # Add comparison summary
        if basic_result and advanced_result:
            comparison['summary'] = {
                'signals': {
                    'basic': basic_result.total_signals,
                    'advanced': advanced_result.total_signals,
                },
                'win_rate': {
                    'basic': basic_result.win_rate,
                    'advanced': advanced_result.win_rate,
                },
                'avg_return_12m': {
                    'basic': basic_result.avg_return_12m,
                    'advanced': advanced_result.avg_return_12m,
                },
                'winner': 'advanced' if advanced_result.win_rate > basic_result.win_rate else 'basic'
            }

        return comparison

    # ========== RISK MANAGEMENT BACKTEST METHODS ==========

    def backtest_with_risk_management(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        portfolio_value: float = 100000.0,
        risk_per_trade: float = 0.02,
        use_trailing_stop: bool = True,
        trailing_stop_pct: float = 0.10,
        use_atr_stop: bool = True,
        atr_multiplier: float = 2.0,
        require_pattern: bool = False
    ) -> Optional[Dict]:
        """
        Backtest with full risk management (position sizing, exits).

        Args:
            symbol: Stock or crypto symbol
            start_date: Backtest start date
            end_date: Backtest end date
            portfolio_value: Starting portfolio value
            risk_per_trade: Risk percentage per trade
            use_trailing_stop: Enable trailing stop
            trailing_stop_pct: Trailing stop percentage
            use_atr_stop: Enable ATR-based stop
            atr_multiplier: ATR multiplier for stop
            require_pattern: Require pattern confirmation

        Returns:
            Dict with comprehensive backtest results including risk metrics
        """
        logger.info(
            f"Risk-managed backtest for {symbol} "
            f"(risk={risk_per_trade:.1%}, trailing={use_trailing_stop})"
        )

        # Get price data
        prices = self._get_extended_prices(symbol, start_date, end_date)
        prices_with_volume = self._get_extended_prices_with_volume(symbol, start_date, end_date)

        if not prices or len(prices) < 365:
            logger.warning(f"Insufficient data for {symbol}")
            return None

        # Initialize risk management tools
        position_sizer = PositionSizer({
            'default_risk_per_trade': risk_per_trade,
            'max_position_size': RISK_MANAGEMENT_CONFIG.MAX_POSITION_SIZE,
            'kelly_fraction': RISK_MANAGEMENT_CONFIG.KELLY_FRACTION,
            'atr_stop_multiplier': atr_multiplier
        })

        exit_manager = ExitStrategyManager({
            'trailing_stop_pct': trailing_stop_pct,
            'max_holding_days': RISK_MANAGEMENT_CONFIG.MAX_HOLDING_DAYS
        })

        # Pattern detector (if required)
        pattern_detector = None
        if require_pattern:
            pattern_detector = PatternDetector({
                'min_pattern_confidence': PATTERN_DETECTION_CONFIG.MIN_PATTERN_CONFIDENCE
            })

        # Detect signals with pattern filtering
        signals = self._detect_signals_in_range(
            symbol, prices, start_date, end_date, 'advanced'
        )

        if require_pattern and pattern_detector:
            filtered_signals = []
            price_dict = {p[0].date(): p[1] for p in prices}
            price_dates = sorted(price_dict.keys())

            for signal in signals:
                signal_date = signal.signal_date.date()

                # Build lookback window for pattern detection
                signal_idx = price_dates.index(signal_date) if signal_date in price_dates else -1
                if signal_idx < 0:
                    continue

                lookback_prices = []
                for j in range(max(0, signal_idx - 60), signal_idx + 1):
                    date = price_dates[j]
                    lookback_prices.append((
                        datetime.combine(date, datetime.min.time()),
                        price_dict[date]
                    ))

                if len(lookback_prices) >= 20:
                    patterns = pattern_detector.detect_all_patterns(lookback_prices)
                    bullish = pattern_detector.get_bullish_patterns(patterns)

                    if bullish:
                        signal.metrics_snapshot['patterns'] = [p.to_dict() for p in bullish]
                        filtered_signals.append(signal)

            signals = filtered_signals
            logger.info(f"Filtered to {len(signals)} signals with pattern confirmation")

        if not signals:
            return {
                'symbol': symbol,
                'period': f"{start_date.date()} to {end_date.date()}",
                'total_signals': 0,
                'trades': [],
                'portfolio_metrics': None,
                'message': 'No signals detected'
            }

        # Simulate trades with risk management
        trades = []
        portfolio_returns = []
        current_portfolio = portfolio_value

        price_dict = {p[0].date(): p[1] for p in prices}

        for signal in signals:
            entry_date = signal.signal_date.date()
            entry_price = signal.entry_price

            # Calculate position size
            # First, calculate ATR for sizing
            signal_idx = None
            for i, (dt, _) in enumerate(prices):
                if dt.date() >= entry_date:
                    signal_idx = i
                    break

            if signal_idx is None or signal_idx < 14:
                continue

            lookback_for_atr = prices[max(0, signal_idx - 30):signal_idx + 1]
            atr_data = FeatureCalculator.calculate_atr(lookback_for_atr)

            if atr_data and use_atr_stop:
                position = position_sizer.volatility_based_sizing(
                    current_portfolio, entry_price, atr_data['atr'], risk_per_trade
                )
                initial_stop = atr_data['suggested_stop']
            else:
                # Fixed percentage stop
                stop_price = entry_price * (1 - trailing_stop_pct)
                position = position_sizer.calculate_position(
                    current_portfolio, entry_price, stop_price, risk_per_trade
                )
                initial_stop = stop_price

            if position.shares == 0:
                continue

            # Simulate trade with exit management
            sorted_dates = sorted(price_dict.keys())
            entry_idx = sorted_dates.index(entry_date) if entry_date in sorted_dates else -1

            if entry_idx < 0:
                continue

            high_since_entry = entry_price
            exit_price = None
            exit_date = None
            exit_reason = None
            max_holding = RISK_MANAGEMENT_CONFIG.MAX_HOLDING_DAYS

            for days_held in range(1, min(max_holding + 1, len(sorted_dates) - entry_idx)):
                current_date = sorted_dates[entry_idx + days_held]
                current_price = price_dict[current_date]

                # Update high since entry
                high_since_entry = max(high_since_entry, current_price)

                # Check exit conditions
                exit_signals = exit_manager.evaluate_all_exits(
                    entry_price=entry_price,
                    current_price=current_price,
                    high_since_entry=high_since_entry,
                    entry_date=signal.signal_date,
                    current_date=datetime.combine(current_date, datetime.min.time()),
                    profit_targets=[0.50]  # 50% target
                )

                # Check ATR stop if enabled
                if use_atr_stop and current_price <= initial_stop:
                    exit_price = current_price
                    exit_date = current_date
                    exit_reason = 'atr_stop'
                    break

                # Check other exit signals
                if exit_signals:
                    exit_price = current_price
                    exit_date = current_date
                    exit_reason = exit_signals[0].reason.value
                    break

            # If no exit triggered, use end of period
            if exit_price is None:
                last_date = sorted_dates[min(entry_idx + max_holding, len(sorted_dates) - 1)]
                exit_price = price_dict[last_date]
                exit_date = last_date
                exit_reason = 'end_of_period'

            # Calculate trade P&L
            trade_return_pct = (exit_price - entry_price) / entry_price
            trade_pnl = position.shares * (exit_price - entry_price)
            trade_pnl_pct = trade_pnl / current_portfolio

            # Update portfolio
            current_portfolio += trade_pnl
            portfolio_returns.append(trade_pnl_pct)

            trades.append({
                'symbol': symbol,
                'entry_date': entry_date.isoformat(),
                'entry_price': entry_price,
                'exit_date': exit_date.isoformat(),
                'exit_price': exit_price,
                'exit_reason': exit_reason,
                'shares': position.shares,
                'position_size': position.dollar_amount,
                'position_pct': position.position_pct,
                'trade_return_pct': trade_return_pct * 100,
                'trade_pnl': trade_pnl,
                'portfolio_return_pct': trade_pnl_pct * 100,
                'signal_score': signal.score,
                'has_pattern': 'patterns' in signal.metrics_snapshot
            })

        # Calculate portfolio metrics
        risk_calculator = PortfolioRiskCalculator()

        if portfolio_returns:
            equity_curve = [portfolio_value]
            for r in portfolio_returns:
                equity_curve.append(equity_curve[-1] * (1 + r))

            risk_metrics = risk_calculator.calculate_all_metrics(
                portfolio_returns, equity_curve
            )
        else:
            risk_metrics = None

        # Aggregate results
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['trade_pnl'] > 0)
        total_return = (current_portfolio - portfolio_value) / portfolio_value * 100

        return {
            'symbol': symbol,
            'period': f"{start_date.date()} to {end_date.date()}",
            'settings': {
                'initial_portfolio': portfolio_value,
                'risk_per_trade': risk_per_trade,
                'trailing_stop': use_trailing_stop,
                'trailing_stop_pct': trailing_stop_pct,
                'atr_stop': use_atr_stop,
                'atr_multiplier': atr_multiplier,
                'pattern_required': require_pattern
            },
            'summary': {
                'total_signals': len(signals),
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                'total_return_pct': total_return,
                'final_portfolio': current_portfolio,
                'avg_trade_return': sum(t['trade_return_pct'] for t in trades) / total_trades if trades else 0
            },
            'risk_metrics': risk_metrics.to_dict() if risk_metrics else None,
            'trades': trades
        }

    def compare_risk_strategies(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        portfolio_value: float = 100000.0
    ) -> Dict:
        """
        Compare different risk management strategies.

        Compares:
        1. No risk management (buy and hold to target)
        2. Trailing stop only
        3. ATR stop only
        4. Combined (trailing + ATR)
        5. Pattern-filtered with risk management

        Returns:
            Dict with comparison results for each strategy
        """
        strategies = {
            'baseline': {
                'use_trailing_stop': False,
                'use_atr_stop': False,
                'require_pattern': False
            },
            'trailing_only': {
                'use_trailing_stop': True,
                'trailing_stop_pct': 0.10,
                'use_atr_stop': False,
                'require_pattern': False
            },
            'atr_only': {
                'use_trailing_stop': False,
                'use_atr_stop': True,
                'atr_multiplier': 2.0,
                'require_pattern': False
            },
            'combined': {
                'use_trailing_stop': True,
                'trailing_stop_pct': 0.15,
                'use_atr_stop': True,
                'atr_multiplier': 2.5,
                'require_pattern': False
            },
            'pattern_filtered': {
                'use_trailing_stop': True,
                'trailing_stop_pct': 0.10,
                'use_atr_stop': True,
                'atr_multiplier': 2.0,
                'require_pattern': True
            }
        }

        results = {}

        for name, settings in strategies.items():
            logger.info(f"Testing strategy: {name}")
            result = self.backtest_with_risk_management(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                portfolio_value=portfolio_value,
                **settings
            )
            results[name] = result

        # Build comparison summary
        comparison = {
            'symbol': symbol,
            'period': f"{start_date.date()} to {end_date.date()}",
            'strategies': {}
        }

        for name, result in results.items():
            if result and result.get('summary'):
                comparison['strategies'][name] = {
                    'total_return': result['summary']['total_return_pct'],
                    'win_rate': result['summary']['win_rate'],
                    'total_trades': result['summary']['total_trades'],
                    'sharpe': result['risk_metrics']['sharpe_ratio'] if result.get('risk_metrics') else None,
                    'max_drawdown': result['risk_metrics']['max_drawdown'] if result.get('risk_metrics') else None
                }

        # Determine best strategy
        valid_strategies = {
            k: v for k, v in comparison['strategies'].items()
            if v.get('sharpe') is not None
        }

        if valid_strategies:
            best_by_sharpe = max(valid_strategies.items(), key=lambda x: x[1]['sharpe'] or 0)
            best_by_return = max(valid_strategies.items(), key=lambda x: x[1]['total_return'] or 0)

            comparison['best_strategy'] = {
                'by_sharpe': best_by_sharpe[0],
                'by_return': best_by_return[0]
            }

        comparison['full_results'] = results

        return comparison


def backtest_all_crash_periods() -> Dict[str, BacktestResult]:
    """Run backtests on all known crash periods"""
    backtester = DeepBottomBacktester()
    results = {}

    for period_name in backtester.CRASH_PERIODS:
        result = backtester.backtest_crash_period(period_name)
        if result:
            results[period_name] = result

    return results
