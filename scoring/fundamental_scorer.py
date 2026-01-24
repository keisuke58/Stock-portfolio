"""
Fundamental Health Scoring for Deep Bottom Detection
Filters value traps by assessing financial health

Score Range: 0-25 points
- P/E Ratio: 0-6 points
- P/B Ratio: 0-5 points
- Free Cash Flow: 0-5 points
- Debt/Equity: 0-5 points
- Revenue Growth: 0-4 points
"""
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetchers import YahooFetcher
from cache import PriceCache
from core.constants import FUNDAMENTAL_SCORING_CONFIG, CACHE_TTL

logger = logging.getLogger(__name__)


class FundamentalHealth(Enum):
    """Fundamental health status classification"""
    HEALTHY = "healthy"          # Score >= 15
    MODERATE = "moderate"        # Score 10-14
    WEAK = "weak"               # Score 5-9
    VALUE_TRAP = "value_trap"   # Score < 5


@dataclass
class FundamentalScore:
    """Fundamental health assessment result"""
    # Individual scores
    pe_score: float           # 0-6 points
    pb_score: float           # 0-5 points
    fcf_score: float          # 0-5 points
    debt_score: float         # 0-5 points
    growth_score: float       # 0-4 points

    # Total and status
    total_score: float        # 0-25 points
    health_status: FundamentalHealth

    # Warnings and details
    warnings: List[str]       # Value trap warnings
    raw_data: Dict           # Original data for debugging

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'pe_score': self.pe_score,
            'pb_score': self.pb_score,
            'fcf_score': self.fcf_score,
            'debt_score': self.debt_score,
            'growth_score': self.growth_score,
            'total_score': self.total_score,
            'health_status': self.health_status.value,
            'warnings': self.warnings,
        }


class FundamentalScorer:
    """
    Calculate fundamental health score for stocks.

    Only applies to stocks - crypto returns None (no fundamentals available).

    Scoring breakdown:
    - P/E Ratio (0-6): Lower PE = better value
    - P/B Ratio (0-5): Below book value = strong value
    - Free Cash Flow (0-5): Positive = financial health
    - Debt/Equity (0-5): Low leverage = safety
    - Revenue Growth (0-4): Growing business = viability
    """

    def __init__(self, cache: Optional[PriceCache] = None):
        self.yahoo_fetcher = YahooFetcher()
        self.cache = cache or PriceCache()
        self.config = FUNDAMENTAL_SCORING_CONFIG

    def calculate_score(self, symbol: str) -> Optional[FundamentalScore]:
        """
        Calculate fundamental score for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            FundamentalScore object or None if data unavailable
        """
        # Try cache first
        cached = self._get_cached(symbol)
        if cached:
            return cached

        # Fetch fundamental data
        data = self.yahoo_fetcher.get_fundamental_data(symbol)
        if not data:
            logger.debug(f"No fundamental data available for {symbol}")
            return None

        warnings = []

        # Calculate individual scores
        pe_score, pe_warnings = self._score_pe_ratio(data.get('pe_ratio'))
        pb_score, pb_warnings = self._score_pb_ratio(data.get('pb_ratio'))
        fcf_score, fcf_warnings = self._score_fcf(
            data.get('free_cash_flow'),
            data.get('market_cap')
        )
        debt_score, debt_warnings = self._score_debt(data.get('debt_to_equity'))
        growth_score, growth_warnings = self._score_growth(data.get('revenue_growth'))

        warnings.extend(pe_warnings)
        warnings.extend(pb_warnings)
        warnings.extend(fcf_warnings)
        warnings.extend(debt_warnings)
        warnings.extend(growth_warnings)

        # Calculate total
        total_score = pe_score + pb_score + fcf_score + debt_score + growth_score
        total_score = max(0, min(25, total_score))  # Clamp to 0-25

        # Determine health status
        if total_score >= self.config.HEALTHY_MIN_SCORE:
            health_status = FundamentalHealth.HEALTHY
        elif total_score >= self.config.MODERATE_MIN_SCORE:
            health_status = FundamentalHealth.MODERATE
        elif total_score >= self.config.WEAK_MIN_SCORE:
            health_status = FundamentalHealth.WEAK
        else:
            health_status = FundamentalHealth.VALUE_TRAP
            if "VALUE TRAP" not in " ".join(warnings):
                warnings.append("VALUE TRAP: Very low fundamental score")

        result = FundamentalScore(
            pe_score=pe_score,
            pb_score=pb_score,
            fcf_score=fcf_score,
            debt_score=debt_score,
            growth_score=growth_score,
            total_score=total_score,
            health_status=health_status,
            warnings=warnings,
            raw_data=data
        )

        # Cache the result
        self._set_cached(symbol, result)

        return result

    def _score_pe_ratio(self, pe: Optional[float]) -> Tuple[float, List[str]]:
        """
        Score P/E ratio (0-6 points).

        Lower PE = better value
        Negative PE (losses) = penalty
        """
        warnings = []

        if pe is None:
            return 0, ["P/E data unavailable"]

        if pe < 0:
            warnings.append(f"Negative earnings (PE: {pe:.1f})")
            return self.config.PE_NEGATIVE_PENALTY, warnings

        if pe < self.config.PE_EXCELLENT:
            score = 6
        elif pe < self.config.PE_FAIR:
            score = 4
        elif pe < self.config.PE_GROWTH:
            score = 2
        else:
            score = 0
            warnings.append(f"High PE ratio ({pe:.1f}) - expensive")

        return score, warnings

    def _score_pb_ratio(self, pb: Optional[float]) -> Tuple[float, List[str]]:
        """
        Score P/B ratio (0-5 points).

        Below book value = strong value signal
        """
        warnings = []

        if pb is None:
            return 0, ["P/B data unavailable"]

        if pb < 0:
            warnings.append("Negative book value - distressed")
            return 0, warnings

        if pb < self.config.PB_VALUE:
            score = 5  # Trading below book value
        elif pb < self.config.PB_FAIR:
            score = 3
        elif pb < self.config.PB_MAX:
            score = 1
        else:
            score = 0
            warnings.append(f"High P/B ratio ({pb:.1f})")

        return score, warnings

    def _score_fcf(
        self,
        fcf: Optional[float],
        market_cap: Optional[int]
    ) -> Tuple[float, List[str]]:
        """
        Score Free Cash Flow (0-5 points).

        Positive FCF = company can survive downturn
        FCF yield considered if market cap available
        """
        warnings = []

        if fcf is None:
            return 0, ["FCF data unavailable"]

        if fcf < 0:
            warnings.append("Negative FCF - burning cash")
            return 0, warnings

        # Calculate FCF yield if market cap available
        if market_cap and market_cap > 0:
            fcf_yield = fcf / market_cap

            if fcf_yield > 0.10:  # 10%+ yield
                score = 5
            elif fcf_yield > 0.05:  # 5%+ yield
                score = 4
            elif fcf_yield > 0.02:  # 2%+ yield
                score = 3
            else:
                score = 2
        else:
            # Just check if positive
            score = 3 if fcf > 0 else 0

        return score, warnings

    def _score_debt(self, debt_to_equity: Optional[float]) -> Tuple[float, List[str]]:
        """
        Score Debt/Equity ratio (0-5 points).

        Low leverage = safer during downturns
        """
        warnings = []

        if debt_to_equity is None:
            return 0, ["D/E data unavailable"]

        # Convert from percentage if needed (some APIs return as %)
        if debt_to_equity > 10:
            debt_to_equity = debt_to_equity / 100

        if debt_to_equity < 0:
            # Negative D/E usually means negative equity - bad sign
            warnings.append("Negative equity - distressed")
            return 0, warnings

        if debt_to_equity < self.config.DEBT_LOW:
            score = 5
        elif debt_to_equity < self.config.DEBT_MODERATE:
            score = 3
        elif debt_to_equity < self.config.DEBT_HIGH:
            score = 1
        else:
            score = 0
            warnings.append(f"High leverage (D/E: {debt_to_equity:.1f})")

        return score, warnings

    def _score_growth(self, revenue_growth: Optional[float]) -> Tuple[float, List[str]]:
        """
        Score Revenue Growth (0-4 points).

        Growing revenue = viable business, not a value trap
        """
        warnings = []

        if revenue_growth is None:
            return 0, ["Revenue growth data unavailable"]

        if revenue_growth > self.config.GROWTH_HIGH:
            score = 4
        elif revenue_growth > self.config.GROWTH_STABLE:
            score = 2
        elif revenue_growth > -0.10:  # Up to 10% decline
            score = 1
        else:
            score = 0
            warnings.append(f"Declining revenue ({revenue_growth*100:.1f}%) - value trap risk")

        return score, warnings

    def _get_cached(self, symbol: str) -> Optional[FundamentalScore]:
        """Get cached fundamental score"""
        try:
            cached_data = self.cache.get(symbol, 'fundamental_score')
            if cached_data:
                return FundamentalScore(
                    pe_score=cached_data['pe_score'],
                    pb_score=cached_data['pb_score'],
                    fcf_score=cached_data['fcf_score'],
                    debt_score=cached_data['debt_score'],
                    growth_score=cached_data['growth_score'],
                    total_score=cached_data['total_score'],
                    health_status=FundamentalHealth(cached_data['health_status']),
                    warnings=cached_data.get('warnings', []),
                    raw_data=cached_data.get('raw_data', {})
                )
        except Exception:
            pass
        return None

    def _set_cached(self, symbol: str, score: FundamentalScore) -> None:
        """Cache fundamental score"""
        try:
            cache_data = score.to_dict()
            cache_data['raw_data'] = score.raw_data
            self.cache.set(symbol, cache_data, 'fundamental_score', CACHE_TTL.FUNDAMENTALS)
        except Exception as e:
            logger.debug(f"Failed to cache fundamental score for {symbol}: {e}")

    def get_health_summary(self, symbol: str) -> Optional[str]:
        """
        Get a one-line summary of fundamental health.

        Returns:
            String like "HEALTHY (19/25): Strong FCF, moderate PE"
        """
        score = self.calculate_score(symbol)
        if not score:
            return None

        status = score.health_status.value.upper()
        details = []

        if score.fcf_score >= 4:
            details.append("Strong FCF")
        if score.pe_score >= 4:
            details.append("Good value")
        if score.debt_score >= 4:
            details.append("Low debt")
        if score.growth_score >= 3:
            details.append("Growing")

        if score.warnings:
            details.extend([f"⚠️{w}" for w in score.warnings[:2]])

        detail_str = ", ".join(details) if details else "Limited data"
        return f"{status} ({score.total_score:.0f}/25): {detail_str}"
