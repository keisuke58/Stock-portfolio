"""
Unified Stock Screener
Combines all screening perspectives for comprehensive stock recommendations
"""
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)


@dataclass
class UnifiedScore:
    """Comprehensive score combining all screening perspectives."""
    symbol: str

    # Overall
    unified_score: float = 0.0  # 0-100 master score
    recommendation: str = "HOLD"  # STRONG_BUY, BUY, HOLD, WATCH, AVOID
    confidence: str = "LOW"  # HIGH, MEDIUM, LOW

    # Ten Bagger perspective
    ten_bagger_score: float = 0.0
    ten_bagger_rating: str = "WEAK"
    growth_score: float = 0.0
    profitability_score: float = 0.0
    valuation_score: float = 0.0

    # Relative Strength perspective
    rs_rating: int = 50
    rs_trend: str = "STABLE"
    momentum_rank: int = 0

    # Deep Bottom perspective (value/recovery)
    deep_bottom_score: float = 0.0
    is_deep_bottom: bool = False
    recovery_potential: str = "LOW"

    # Fundamental perspective
    fundamental_score: float = 0.0
    financial_health: str = "MODERATE"

    # VMS perspective
    value_score: float = 0.0
    momentum_score: float = 0.0
    stability_score: float = 0.0

    # Price data
    current_price: float = 0.0
    ath_ratio: float = 1.0
    drawdown_pct: float = 0.0
    return_30d: float = 0.0

    # Signals
    current_state: str = "NORMAL"
    key_signals: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)

    # Category
    category: str = "Unknown"
    sector: Optional[str] = None


@dataclass
class ScreeningResult:
    """Results from unified screening."""
    timestamp: str
    total_screened: int

    # Top picks by category
    strong_buys: List[UnifiedScore] = field(default_factory=list)
    ten_bagger_candidates: List[UnifiedScore] = field(default_factory=list)
    momentum_leaders: List[UnifiedScore] = field(default_factory=list)
    deep_value_plays: List[UnifiedScore] = field(default_factory=list)
    recovery_candidates: List[UnifiedScore] = field(default_factory=list)

    # All scores
    all_scores: List[UnifiedScore] = field(default_factory=list)


class UnifiedScreener:
    """
    Unified screening system combining all analysis perspectives.

    Perspectives:
    1. Ten Bagger - Growth potential for 10x returns
    2. Relative Strength - Momentum leaders
    3. Deep Bottom - Value recovery opportunities
    4. Fundamentals - Financial health
    5. VMS - Value/Momentum/Stability balance
    """

    def __init__(self, stock_fetcher=None):
        """Initialize with optional stock fetcher."""
        self.stock_fetcher = stock_fetcher
        self._init_screeners()

    def _init_screeners(self):
        """Initialize individual screeners lazily."""
        self._ten_bagger = None
        self._rs_calculator = None
        self._fundamental_scorer = None
        self._vms_scorer = None
        self._feature_calculator = None

    @property
    def ten_bagger_screener(self):
        if self._ten_bagger is None:
            try:
                from screeners.ten_bagger_screener import TenBaggerScreener
                self._ten_bagger = TenBaggerScreener(self.stock_fetcher)
            except ImportError:
                logger.warning("TenBaggerScreener not available")
        return self._ten_bagger

    @property
    def rs_calculator(self):
        if self._rs_calculator is None:
            try:
                from screeners.relative_strength import RelativeStrengthCalculator
                self._rs_calculator = RelativeStrengthCalculator(self.stock_fetcher)
            except ImportError:
                logger.warning("RelativeStrengthCalculator not available")
        return self._rs_calculator

    @property
    def fundamental_scorer(self):
        if self._fundamental_scorer is None:
            try:
                from scoring.fundamental_scorer import FundamentalScorer
                self._fundamental_scorer = FundamentalScorer(self.stock_fetcher)
            except ImportError:
                logger.warning("FundamentalScorer not available")
        return self._fundamental_scorer

    @property
    def vms_scorer(self):
        if self._vms_scorer is None:
            try:
                from scoring.vms_scorer import VMSScorer
                self._vms_scorer = VMSScorer
            except ImportError:
                logger.warning("VMSScorer not available")
        return self._vms_scorer

    @property
    def feature_calculator(self):
        if self._feature_calculator is None:
            try:
                from features.indicators import FeatureCalculator
                self._feature_calculator = FeatureCalculator()
            except ImportError:
                logger.warning("FeatureCalculator not available")
        return self._feature_calculator

    def _fetch_price_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch price data from stock fetcher and convert to DataFrame."""
        if not self.stock_fetcher:
            return None

        try:
            # Try get_historical_prices_with_volume first (returns list of tuples)
            if hasattr(self.stock_fetcher, 'get_historical_prices_with_volume'):
                data = self.stock_fetcher.get_historical_prices_with_volume(symbol, days=365)
                if data:
                    df = pd.DataFrame(data, columns=['Date', 'Close', 'Volume'])
                    df.set_index('Date', inplace=True)
                    return df

            # Fallback to get_historical_prices
            if hasattr(self.stock_fetcher, 'get_historical_prices'):
                data = self.stock_fetcher.get_historical_prices(symbol, days=365)
                if data:
                    df = pd.DataFrame(data, columns=['Date', 'Close'])
                    df.set_index('Date', inplace=True)
                    return df

        except Exception as e:
            logger.debug(f"Error fetching price data for {symbol}: {e}")

        return None

    def screen_stock(self, symbol: str, price_data: pd.DataFrame = None) -> UnifiedScore:
        """
        Screen a single stock from all perspectives.

        Args:
            symbol: Stock symbol
            price_data: Optional pre-fetched price data

        Returns:
            UnifiedScore with all perspective scores
        """
        score = UnifiedScore(symbol=symbol)

        try:
            # Fetch price data if not provided
            if price_data is None:
                price_data = self._fetch_price_data(symbol)

            if price_data is not None and not price_data.empty:
                score = self._calculate_price_metrics(score, price_data)
            else:
                # Fallback: try to get at least current price
                if self.stock_fetcher and hasattr(self.stock_fetcher, 'get_current_price'):
                    try:
                        price = self.stock_fetcher.get_current_price(symbol)
                        if price:
                            score.current_price = price
                    except Exception:
                        pass

            # Ten Bagger analysis (may also set current_price)
            score = self._calculate_ten_bagger(score, symbol)

            # Relative Strength analysis
            score = self._calculate_rs(score, symbol)

            # Deep Bottom analysis
            score = self._calculate_deep_bottom(score, symbol, price_data)

            # Fundamental analysis
            score = self._calculate_fundamentals(score, symbol)

            # VMS analysis
            score = self._calculate_vms(score, symbol, price_data)

            # Calculate unified score and recommendation
            score = self._calculate_unified_score(score)

        except Exception as e:
            logger.error(f"Error screening {symbol}: {e}")
            score.risk_factors.append(f"Screening error: {str(e)[:50]}")

        return score

    def _calculate_price_metrics(self, score: UnifiedScore, price_data: pd.DataFrame) -> UnifiedScore:
        """Calculate basic price metrics."""
        try:
            close = price_data['Close']
            score.current_price = float(close.iloc[-1])

            # ATH and drawdown
            ath = close.max()
            score.ath_ratio = score.current_price / ath if ath > 0 else 1.0
            score.drawdown_pct = (1 - score.ath_ratio) * 100

            # 30-day return
            if len(close) >= 30:
                price_30d_ago = close.iloc[-30]
                score.return_30d = ((score.current_price / price_30d_ago) - 1) * 100

        except Exception as e:
            logger.debug(f"Price metrics error: {e}")

        return score

    def _calculate_ten_bagger(self, score: UnifiedScore, symbol: str) -> UnifiedScore:
        """Calculate Ten Bagger perspective scores."""
        try:
            if self.ten_bagger_screener:
                tb_score = self.ten_bagger_screener.score_stock(symbol)
                if tb_score:
                    score.ten_bagger_score = tb_score.total_score
                    score.ten_bagger_rating = tb_score.rating
                    score.growth_score = tb_score.growth_score
                    score.profitability_score = tb_score.profitability_score
                    score.valuation_score = tb_score.valuation_score
                    score.sector = tb_score.sector

                    # Get current_price from metrics if not already set
                    if score.current_price == 0 and tb_score.metrics:
                        price = tb_score.metrics.get('current_price')
                        if price:
                            score.current_price = price

                    # Get RS data if available
                    if tb_score.rs_rating:
                        score.rs_rating = tb_score.rs_rating
                    if tb_score.rs_trend:
                        score.rs_trend = tb_score.rs_trend

                    if tb_score.key_strengths:
                        score.key_signals.extend(tb_score.key_strengths[:3])
                    if tb_score.key_risks:
                        score.risk_factors.extend(tb_score.key_risks[:3])
        except Exception as e:
            logger.debug(f"Ten Bagger error for {symbol}: {e}")

        return score

    def _calculate_rs(self, score: UnifiedScore, symbol: str) -> UnifiedScore:
        """Calculate Relative Strength perspective."""
        try:
            if self.rs_calculator:
                rs_rating = self.rs_calculator.calculate_rs_rating(symbol)
                if rs_rating:
                    score.rs_rating = rs_rating.rs_rating
                    score.rs_trend = rs_rating.rs_trend

                    if rs_rating.rs_rating >= 80:
                        score.key_signals.append(f"RS Leader ({rs_rating.rs_rating})")
                    elif rs_rating.rs_trend == "IMPROVING":
                        score.key_signals.append("RS Improving")
        except Exception as e:
            logger.debug(f"RS error for {symbol}: {e}")

        return score

    def _calculate_deep_bottom(self, score: UnifiedScore, symbol: str,
                                price_data: pd.DataFrame = None) -> UnifiedScore:
        """Calculate Deep Bottom (value/recovery) perspective."""
        try:
            if self.feature_calculator and price_data is not None and not price_data.empty:
                features = self.feature_calculator.calculate_all_features(price_data)

                # Deep bottom indicators
                ath_drawdown = features.get('ath_drawdown', 0)
                rsi = features.get('rsi', 50)
                near_52w_low = features.get('near_52w_low', False)

                # Calculate deep bottom score
                db_score = 0

                # Value component (drawdown)
                if ath_drawdown >= 50:
                    db_score += 30
                    score.key_signals.append(f"Deep Value (-{ath_drawdown:.0f}% from ATH)")
                elif ath_drawdown >= 30:
                    db_score += 20

                # RSI oversold
                if rsi < 30:
                    db_score += 25
                    score.key_signals.append(f"RSI Oversold ({rsi:.0f})")
                elif rsi < 40:
                    db_score += 15

                # Near 52-week low
                if near_52w_low:
                    db_score += 20
                    score.key_signals.append("Near 52-Week Low")

                # Recovery signals
                higher_lows = features.get('higher_lows', False)
                rsi_divergence = features.get('rsi_divergence', False)

                if higher_lows:
                    db_score += 15
                    score.key_signals.append("Higher Lows Forming")
                if rsi_divergence:
                    db_score += 10
                    score.key_signals.append("Bullish RSI Divergence")

                score.deep_bottom_score = min(db_score, 100)
                score.is_deep_bottom = db_score >= 50

                if db_score >= 70:
                    score.recovery_potential = "HIGH"
                elif db_score >= 50:
                    score.recovery_potential = "MEDIUM"
                else:
                    score.recovery_potential = "LOW"

        except Exception as e:
            logger.debug(f"Deep Bottom error for {symbol}: {e}")

        return score

    def _calculate_fundamentals(self, score: UnifiedScore, symbol: str) -> UnifiedScore:
        """Calculate fundamental health perspective."""
        try:
            if self.fundamental_scorer:
                fund_score = self.fundamental_scorer.calculate_score(symbol)
                if fund_score:
                    score.fundamental_score = fund_score.total_score
                    score.financial_health = fund_score.health_rating

                    if fund_score.health_rating == "HEALTHY":
                        score.key_signals.append("Strong Fundamentals")
                    elif fund_score.health_rating == "VALUE_TRAP":
                        score.risk_factors.append("Potential Value Trap")
        except Exception as e:
            logger.debug(f"Fundamental error for {symbol}: {e}")

        return score

    def _calculate_vms(self, score: UnifiedScore, symbol: str,
                       price_data: pd.DataFrame = None) -> UnifiedScore:
        """Calculate VMS (Value/Momentum/Stability) perspective."""
        try:
            if self.vms_scorer and price_data is not None:
                # VMS requires state info
                state = score.current_state
                vms = self.vms_scorer(
                    symbol=symbol,
                    current_state=state,
                    price_history=price_data
                )
                scores = vms.calculate_all_scores()

                score.value_score = scores.get('value_score', 0)
                score.momentum_score = scores.get('momentum_score', 0)
                score.stability_score = scores.get('stability_score', 0)

        except Exception as e:
            logger.debug(f"VMS error for {symbol}: {e}")

        return score

    def _calculate_unified_score(self, score: UnifiedScore) -> UnifiedScore:
        """
        Calculate unified score combining all perspectives.

        Weighting:
        - Ten Bagger: 25% (growth potential)
        - RS Rating: 20% (momentum)
        - Deep Bottom: 15% (value opportunity)
        - Fundamentals: 20% (financial health)
        - VMS Average: 20% (balanced view)
        """
        # Normalize scores to 0-100
        ten_bagger_norm = score.ten_bagger_score  # Already 0-100
        rs_norm = score.rs_rating  # Already 1-99
        deep_bottom_norm = score.deep_bottom_score  # Already 0-100
        fundamental_norm = (score.fundamental_score / 25) * 100  # 0-25 -> 0-100
        vms_avg = (score.value_score + score.momentum_score + score.stability_score) / 3

        # Weighted calculation
        unified = (
            ten_bagger_norm * 0.25 +
            rs_norm * 0.20 +
            deep_bottom_norm * 0.15 +
            fundamental_norm * 0.20 +
            vms_avg * 0.20
        )

        score.unified_score = round(unified, 1)

        # Determine recommendation
        if unified >= 75 and score.rs_rating >= 70 and score.ten_bagger_rating in ['EXCELLENT', 'GOOD']:
            score.recommendation = "STRONG_BUY"
            score.confidence = "HIGH"
        elif unified >= 65 or (score.ten_bagger_score >= 70 and score.rs_rating >= 60):
            score.recommendation = "BUY"
            score.confidence = "MEDIUM" if unified >= 60 else "LOW"
        elif unified >= 50 or score.is_deep_bottom:
            score.recommendation = "HOLD"
            score.confidence = "MEDIUM"
        elif unified >= 35:
            score.recommendation = "WATCH"
            score.confidence = "LOW"
        else:
            score.recommendation = "AVOID"
            score.confidence = "LOW"

        # Boost for special conditions
        if score.is_deep_bottom and score.rs_trend == "IMPROVING":
            if score.recommendation == "HOLD":
                score.recommendation = "BUY"
                score.key_signals.append("Recovery + Momentum")

        return score

    def screen_universe(self, symbols: List[str], max_workers: int = 5,
                        top_n: int = 50) -> ScreeningResult:
        """
        Screen multiple stocks and categorize results.

        Args:
            symbols: List of stock symbols
            max_workers: Parallel workers
            top_n: Top N results per category

        Returns:
            ScreeningResult with categorized recommendations
        """
        from datetime import datetime

        all_scores = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.screen_stock, s): s for s in symbols}

            for future in as_completed(futures):
                try:
                    score = future.result()
                    if score:
                        all_scores.append(score)
                except Exception as e:
                    logger.error(f"Screening error: {e}")

        # Sort and categorize
        result = ScreeningResult(
            timestamp=datetime.now().isoformat(),
            total_screened=len(symbols),
            all_scores=sorted(all_scores, key=lambda x: x.unified_score, reverse=True)
        )

        # Strong Buys (highest unified score with good confidence)
        result.strong_buys = [
            s for s in all_scores
            if s.recommendation == "STRONG_BUY"
        ][:top_n]

        # Ten Bagger Candidates (high growth potential)
        result.ten_bagger_candidates = sorted(
            [s for s in all_scores if s.ten_bagger_score >= 60],
            key=lambda x: x.ten_bagger_score,
            reverse=True
        )[:top_n]

        # Momentum Leaders (high RS rating)
        result.momentum_leaders = sorted(
            [s for s in all_scores if s.rs_rating >= 70],
            key=lambda x: x.rs_rating,
            reverse=True
        )[:top_n]

        # Deep Value Plays (significant drawdown with good fundamentals)
        result.deep_value_plays = sorted(
            [s for s in all_scores if s.drawdown_pct >= 30 and s.fundamental_score >= 12],
            key=lambda x: x.drawdown_pct,
            reverse=True
        )[:top_n]

        # Recovery Candidates (deep bottom with improving momentum)
        result.recovery_candidates = sorted(
            [s for s in all_scores if s.is_deep_bottom],
            key=lambda x: x.deep_bottom_score,
            reverse=True
        )[:top_n]

        return result

    def get_top_recommendations(self, symbols: List[str], top_n: int = 10) -> Dict[str, List[UnifiedScore]]:
        """
        Get top recommendations across all categories.

        Returns dict with:
        - overall: Top unified scores
        - growth: Top ten bagger candidates
        - momentum: Top RS leaders
        - value: Top deep value plays
        - recovery: Top recovery candidates
        """
        result = self.screen_universe(symbols, top_n=top_n)

        return {
            'overall': result.all_scores[:top_n],
            'growth': result.ten_bagger_candidates[:top_n],
            'momentum': result.momentum_leaders[:top_n],
            'value': result.deep_value_plays[:top_n],
            'recovery': result.recovery_candidates[:top_n],
            'strong_buys': result.strong_buys[:top_n]
        }


# Default stock universe for screening
DEFAULT_SCREENING_UNIVERSE = [
    # Tech Giants
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
    # Semiconductors
    'AMD', 'AVGO', 'QCOM', 'INTC', 'MU', 'AMAT', 'LRCX', 'KLAC', 'MRVL', 'ARM',
    # Software/Cloud
    'CRM', 'NOW', 'SNOW', 'NET', 'DDOG', 'ZS', 'CRWD', 'PANW', 'OKTA',
    # E-commerce/Fintech
    'SHOP', 'SQ', 'PYPL', 'COIN', 'AFRM', 'SOFI', 'UPST',
    # Healthcare/Biotech
    'UNH', 'JNJ', 'PFE', 'MRNA', 'ABBV', 'LLY', 'BMY',
    # Financial
    'JPM', 'BAC', 'GS', 'MS', 'V', 'MA', 'AXP',
    # Consumer
    'NKE', 'SBUX', 'MCD', 'DIS', 'NFLX', 'COST', 'WMT', 'TGT',
    # Industrial/Energy
    'CAT', 'DE', 'BA', 'LMT', 'RTX', 'XOM', 'CVX',
    # Growth/Speculative
    'PLTR', 'RKLB', 'IONQ', 'SMCI', 'AI', 'PATH', 'U',
]
