"""
Ten Bagger Stock Screener
Identifies stocks with potential for 10x returns based on growth metrics,
profitability indicators, valuation measures, and sector analysis.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetchers import YahooFetcher
from core.constants import TEN_BAGGER_CONFIG, GROWTH_SECTORS, TenBaggerConfig

logger = logging.getLogger(__name__)


@dataclass
class TenBaggerScore:
    """Score result for a potential ten bagger stock."""
    symbol: str
    total_score: float           # 0-100
    growth_score: float          # 0-35
    profitability_score: float   # 0-25
    valuation_score: float       # 0-20
    market_position_score: float # 0-20
    rating: str                  # EXCELLENT, GOOD, MARGINAL, WEAK
    sector: Optional[str] = None
    key_strengths: List[str] = field(default_factory=list)
    key_risks: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    # Relative Strength metrics
    rs_rating: Optional[int] = None           # 1-99 IBD-style RS
    rs_rating_sector: Optional[int] = None    # 1-99 vs sector peers
    rs_trend: Optional[str] = None            # IMPROVING, STABLE, DECLINING


class TenBaggerScreener:
    """
    Screener for identifying stocks with ten bagger (10x) potential.

    Scoring breakdown (100 points total):
    - Growth Score: 35 points max
    - Profitability Score: 25 points max
    - Valuation Score: 20 points max
    - Market Position Score: 20 points max

    Also includes IBD-style Relative Strength (RS) rating (1-99).
    """

    def __init__(
        self,
        yahoo_fetcher: Optional[YahooFetcher] = None,
        config: TenBaggerConfig = TEN_BAGGER_CONFIG,
        include_rs: bool = True
    ):
        self.fetcher = yahoo_fetcher or YahooFetcher()
        self.config = config
        self.include_rs = include_rs
        self._rs_calculator = None

    @property
    def rs_calculator(self):
        """Lazy-load RS calculator."""
        if self._rs_calculator is None and self.include_rs:
            from screeners.relative_strength import RelativeStrengthCalculator
            self._rs_calculator = RelativeStrengthCalculator(yahoo_fetcher=self.fetcher)
        return self._rs_calculator

    def score_stock(self, symbol: str) -> Optional[TenBaggerScore]:
        """
        Score a single stock on ten bagger potential.

        Args:
            symbol: Stock ticker symbol

        Returns:
            TenBaggerScore object or None if data unavailable
        """
        try:
            # Fetch fundamental data
            fundamentals = self.fetcher.get_fundamental_data(symbol)
            if not fundamentals:
                logger.warning(f"No fundamental data available for {symbol}")
                return None

            # Fetch price data for momentum calculation
            prices = self.fetcher.get_historical_prices(symbol, days=365)
            if not prices or len(prices) < 50:
                logger.warning(f"Insufficient price data for {symbol}")
                return None

            # Calculate component scores
            growth_score, growth_strengths = self._calculate_growth_score(fundamentals)
            profit_score, profit_strengths = self._calculate_profitability_score(fundamentals)
            value_score, value_strengths = self._calculate_valuation_score(fundamentals)
            position_score, position_strengths = self._calculate_market_position_score(
                fundamentals, prices
            )

            # Total score
            total_score = growth_score + profit_score + value_score + position_score

            # Collect all strengths
            all_strengths = growth_strengths + profit_strengths + value_strengths + position_strengths

            # Identify risks
            risks = self._identify_risks(fundamentals, prices)

            # Determine rating
            if total_score >= self.config.SCORE_EXCELLENT:
                rating = 'EXCELLENT'
            elif total_score >= self.config.SCORE_GOOD:
                rating = 'GOOD'
            elif total_score >= self.config.SCORE_MARGINAL:
                rating = 'MARGINAL'
            else:
                rating = 'WEAK'

            # Determine sector
            sector = self._identify_sector(symbol)

            # Calculate Relative Strength rating
            rs_rating = None
            rs_rating_sector = None
            rs_trend = None

            if self.include_rs and self.rs_calculator:
                try:
                    rs_result = self.rs_calculator.calculate_rs_rating(symbol)
                    if rs_result:
                        rs_rating = rs_result.rs_rating
                        rs_rating_sector = rs_result.rs_rating_sector
                        rs_trend = rs_result.rs_trend

                        # Add RS to strengths/risks
                        if rs_rating >= 80:
                            all_strengths.insert(0, f"Strong RS Rating: {rs_rating} (top {100-rs_rating}%)")
                        elif rs_rating >= 70:
                            all_strengths.append(f"Solid RS Rating: {rs_rating}")

                        if rs_trend == 'IMPROVING':
                            all_strengths.append("RS trend improving (momentum building)")
                        elif rs_trend == 'DECLINING':
                            risks.append("RS trend declining (momentum fading)")

                        if rs_rating < 50:
                            risks.append(f"Weak RS Rating: {rs_rating} (underperforming peers)")

                except Exception as e:
                    logger.debug(f"RS calculation failed for {symbol}: {e}")

            # Extract metrics including RS data
            metrics = self._extract_key_metrics(fundamentals, prices)
            metrics['rs_rating'] = rs_rating
            metrics['rs_rating_sector'] = rs_rating_sector
            metrics['rs_trend'] = rs_trend

            return TenBaggerScore(
                symbol=symbol,
                total_score=total_score,
                growth_score=growth_score,
                profitability_score=profit_score,
                valuation_score=value_score,
                market_position_score=position_score,
                rating=rating,
                sector=sector,
                key_strengths=all_strengths[:5],  # Top 5 strengths
                key_risks=risks[:5],              # Top 5 risks
                metrics=metrics,
                rs_rating=rs_rating,
                rs_rating_sector=rs_rating_sector,
                rs_trend=rs_trend
            )

        except Exception as e:
            logger.error(f"Error scoring {symbol}: {e}")
            return None

    def _calculate_growth_score(self, metrics: Dict) -> Tuple[float, List[str]]:
        """
        Calculate growth score (0-35 points max).

        - Revenue Growth: 0-15 points
        - Earnings Growth: 0-12 points
        - Revenue Acceleration: 0-5 points (bonus)
        - Multi-year Growth: 0-3 points (bonus)
        """
        score = 0.0
        strengths = []

        # Revenue Growth (15 points max)
        revenue_growth = metrics.get('revenue_growth')
        if revenue_growth is not None:
            if revenue_growth > 0.50:
                score += 15
                strengths.append(f"Exceptional revenue growth: {revenue_growth*100:.1f}%")
            elif revenue_growth > 0.30:
                score += 12
                strengths.append(f"Strong revenue growth: {revenue_growth*100:.1f}%")
            elif revenue_growth > 0.20:
                score += 8
                strengths.append(f"Solid revenue growth: {revenue_growth*100:.1f}%")
            elif revenue_growth > 0.10:
                score += 4

        # Earnings Growth (12 points max)
        earnings_growth = metrics.get('earnings_growth')
        if earnings_growth is not None:
            if earnings_growth > 0.50:
                score += 12
                strengths.append(f"Exceptional earnings growth: {earnings_growth*100:.1f}%")
            elif earnings_growth > 0.40:
                score += 10
                strengths.append(f"Strong earnings growth: {earnings_growth*100:.1f}%")
            elif earnings_growth > 0.20:
                score += 6

        # Quarterly earnings acceleration bonus (5 points)
        quarterly_growth = metrics.get('earnings_quarterly_growth')
        if quarterly_growth is not None and revenue_growth is not None:
            if quarterly_growth > revenue_growth:
                score += 5
                strengths.append("Earnings accelerating faster than revenue")

        # Multi-year growth consistency bonus (3 points)
        # Check if both revenue and earnings growth are positive
        if revenue_growth and earnings_growth and revenue_growth > 0.25 and earnings_growth > 0.25:
            score += 3
            strengths.append("Consistent high growth profile")

        return min(score, 35.0), strengths

    def _calculate_profitability_score(self, metrics: Dict) -> Tuple[float, List[str]]:
        """
        Calculate profitability score (0-25 points max).

        - Gross Margin: 0-8 points
        - Net Margin: 0-7 points
        - ROE: 0-7 points
        - Margin Expansion: 0-3 points (bonus)
        """
        score = 0.0
        strengths = []

        # Gross Margin (8 points max) - use operating margin as proxy
        operating_margin = metrics.get('operating_margins')
        if operating_margin is not None:
            if operating_margin > 0.30:  # 30%+ operating margin is exceptional
                score += 8
                strengths.append(f"High operating margin: {operating_margin*100:.1f}%")
            elif operating_margin > 0.20:
                score += 6
                strengths.append(f"Solid operating margin: {operating_margin*100:.1f}%")
            elif operating_margin > 0.10:
                score += 3

        # Net Margin (7 points max)
        profit_margin = metrics.get('profit_margin')
        if profit_margin is not None:
            if profit_margin > 0.20:
                score += 7
                strengths.append(f"Excellent profit margin: {profit_margin*100:.1f}%")
            elif profit_margin > 0.15:
                score += 5
                strengths.append(f"Strong profit margin: {profit_margin*100:.1f}%")
            elif profit_margin > 0.10:
                score += 3

        # ROE (7 points max)
        roe = metrics.get('roe')
        if roe is not None:
            if roe > 0.30:
                score += 7
                strengths.append(f"Exceptional ROE: {roe*100:.1f}%")
            elif roe > 0.20:
                score += 5
                strengths.append(f"Strong ROE: {roe*100:.1f}%")
            elif roe > 0.15:
                score += 3

        # ROA bonus for capital efficiency
        roa = metrics.get('roa')
        if roa is not None and roa > 0.10:
            score += 3
            strengths.append(f"Efficient capital deployment (ROA: {roa*100:.1f}%)")

        return min(score, 25.0), strengths

    def _calculate_valuation_score(self, metrics: Dict) -> Tuple[float, List[str]]:
        """
        Calculate valuation score (0-20 points max).

        - PEG Ratio: 0-10 points
        - FCF Yield: 0-6 points
        - P/S to Growth Ratio: 0-4 points
        """
        score = 0.0
        strengths = []

        # PEG Ratio (10 points max)
        pe_ratio = metrics.get('pe_ratio')
        earnings_growth = metrics.get('earnings_growth')

        if pe_ratio is not None and pe_ratio > 0 and earnings_growth is not None and earnings_growth > 0:
            peg = pe_ratio / (earnings_growth * 100)
            if peg < 1.0:
                score += 10
                strengths.append(f"Attractive PEG ratio: {peg:.2f}")
            elif peg < 1.5:
                score += 7
                strengths.append(f"Reasonable PEG ratio: {peg:.2f}")
            elif peg < 2.0:
                score += 4

        # FCF Yield (6 points max)
        fcf = metrics.get('free_cash_flow')
        market_cap = metrics.get('market_cap')

        if fcf is not None and market_cap is not None and market_cap > 0:
            fcf_yield = fcf / market_cap
            if fcf_yield > 0.05:
                score += 6
                strengths.append(f"Strong FCF yield: {fcf_yield*100:.1f}%")
            elif fcf_yield > 0.03:
                score += 4
                strengths.append(f"Solid FCF yield: {fcf_yield*100:.1f}%")
            elif fcf_yield > 0.01:
                score += 2

        # P/S to Growth evaluation (4 points max)
        ps_ratio = metrics.get('ps_ratio')
        revenue_growth = metrics.get('revenue_growth')

        if ps_ratio is not None and revenue_growth is not None and revenue_growth > 0:
            # Rule of 40 inspired: good if P/S < revenue_growth * 100 / 10
            ps_threshold = revenue_growth * 10  # e.g., 30% growth -> 3x P/S is fair
            if ps_ratio < ps_threshold:
                score += 4
                strengths.append(f"P/S ({ps_ratio:.1f}x) justified by growth")
            elif ps_ratio < ps_threshold * 1.5:
                score += 2

        return min(score, 20.0), strengths

    def _calculate_market_position_score(
        self,
        metrics: Dict,
        prices: List[Tuple[datetime, float]]
    ) -> Tuple[float, List[str]]:
        """
        Calculate market position score (0-20 points max).

        - Market Cap Sweet Spot: 0-8 points
        - Growth Sector Membership: 0-6 points
        - 52-Week Momentum: 0-6 points
        """
        score = 0.0
        strengths = []

        # Market Cap Sweet Spot (8 points max)
        market_cap = metrics.get('market_cap')
        if market_cap is not None:
            if self.config.MARKET_CAP_OPTIMAL_MIN <= market_cap <= self.config.MARKET_CAP_OPTIMAL_MAX:
                score += 8
                cap_billions = market_cap / 1e9
                strengths.append(f"Optimal market cap: ${cap_billions:.1f}B (room to grow)")
            elif self.config.MARKET_CAP_MIN <= market_cap <= self.config.MARKET_CAP_MAX:
                score += 5
                cap_billions = market_cap / 1e9
                strengths.append(f"Market cap in range: ${cap_billions:.1f}B")
            elif market_cap < self.config.MARKET_CAP_MIN:
                score += 2  # Small cap - higher risk but more upside

        # Growth Sector (6 points max)
        sector = metrics.get('sector')
        industry = metrics.get('industry')
        sector_name = self._identify_sector_from_info(sector, industry)
        if sector_name:
            score += 6
            strengths.append(f"In growth sector: {sector_name}")

        # 52-Week Momentum (6 points max)
        if prices and len(prices) >= 252:
            start_price = prices[0][1]
            current_price = prices[-1][1]
            return_52w = (current_price - start_price) / start_price

            if return_52w > 0.50:
                score += 6
                strengths.append(f"Strong momentum: +{return_52w*100:.1f}% (52w)")
            elif return_52w > 0.20:
                score += 4
                strengths.append(f"Positive momentum: +{return_52w*100:.1f}% (52w)")
            elif return_52w > 0:
                score += 2
        elif prices:
            # Use available data
            start_price = prices[0][1]
            current_price = prices[-1][1]
            return_period = (current_price - start_price) / start_price
            if return_period > 0.20:
                score += 4
                strengths.append(f"Positive momentum: +{return_period*100:.1f}%")

        return min(score, 20.0), strengths

    def _identify_risks(self, metrics: Dict, prices: List) -> List[str]:
        """Identify key risks for the stock."""
        risks = []

        # Valuation risk
        pe_ratio = metrics.get('pe_ratio')
        if pe_ratio is not None and pe_ratio > 60:
            risks.append(f"High valuation risk (P/E: {pe_ratio:.1f})")

        # Debt risk
        debt_to_equity = metrics.get('debt_to_equity')
        if debt_to_equity is not None and debt_to_equity > 100:
            risks.append(f"High debt level (D/E: {debt_to_equity:.1f}%)")

        # Negative cash flow
        fcf = metrics.get('free_cash_flow')
        if fcf is not None and fcf < 0:
            risks.append("Negative free cash flow")

        # Profit margin concerns
        profit_margin = metrics.get('profit_margin')
        if profit_margin is not None and profit_margin < 0:
            risks.append("Currently unprofitable")
        elif profit_margin is not None and profit_margin < 0.05:
            risks.append("Thin profit margins")

        # Growth deceleration
        earnings_growth = metrics.get('earnings_growth')
        quarterly_growth = metrics.get('earnings_quarterly_growth')
        if earnings_growth and quarterly_growth and quarterly_growth < earnings_growth * 0.5:
            risks.append("Earnings growth decelerating")

        # Market cap too large
        market_cap = metrics.get('market_cap')
        if market_cap and market_cap > self.config.MARKET_CAP_MAX:
            cap_billions = market_cap / 1e9
            risks.append(f"Large cap (${cap_billions:.0f}B) - 10x potential limited")

        # Volatility risk from price data
        if prices and len(prices) > 50:
            # Calculate simple volatility
            returns = []
            for i in range(1, len(prices)):
                ret = (prices[i][1] - prices[i-1][1]) / prices[i-1][1]
                returns.append(ret)

            if returns:
                import statistics
                volatility = statistics.stdev(returns) * (252 ** 0.5)  # Annualized
                if volatility > 0.60:
                    risks.append(f"High volatility ({volatility*100:.0f}% annualized)")

        # Beta risk
        beta = metrics.get('beta')
        if beta is not None and beta > 1.5:
            risks.append(f"High beta ({beta:.2f}) - amplified market risk")

        return risks

    def _identify_sector(self, symbol: str) -> Optional[str]:
        """Identify if stock belongs to a growth sector."""
        for sector_name, symbols in GROWTH_SECTORS.items():
            if symbol.upper() in symbols:
                return sector_name
        return None

    def _identify_sector_from_info(self, sector: Optional[str], industry: Optional[str]) -> Optional[str]:
        """Identify growth sector from company info."""
        if not sector and not industry:
            return None

        sector_lower = (sector or '').lower()
        industry_lower = (industry or '').lower()

        # Map to growth sectors
        if 'semiconductor' in industry_lower or 'chip' in industry_lower:
            return 'SEMICONDUCTORS'
        if 'software' in industry_lower or 'cloud' in industry_lower:
            return 'CLOUD_COMPUTING'
        if 'security' in industry_lower or 'cyber' in industry_lower:
            return 'CYBERSECURITY'
        if 'biotech' in industry_lower or 'genomics' in industry_lower:
            return 'BIOTECH_GENOMICS'
        if 'solar' in industry_lower or 'renewable' in industry_lower or 'clean energy' in industry_lower:
            return 'CLEAN_ENERGY'
        if 'payment' in industry_lower or 'fintech' in industry_lower:
            return 'FINTECH'
        if 'aerospace' in industry_lower or 'defense' in industry_lower:
            return 'SPACE_DEFENSE'
        if 'artificial intelligence' in industry_lower or 'ai' in industry_lower:
            return 'AI_INFRASTRUCTURE'

        return None

    def _extract_key_metrics(
        self,
        metrics: Dict,
        prices: List[Tuple[datetime, float]]
    ) -> Dict[str, Any]:
        """Extract key metrics for display."""
        result = {
            'revenue_growth': metrics.get('revenue_growth'),
            'earnings_growth': metrics.get('earnings_growth'),
            'profit_margin': metrics.get('profit_margin'),
            'operating_margin': metrics.get('operating_margins'),
            'roe': metrics.get('roe'),
            'roa': metrics.get('roa'),
            'pe_ratio': metrics.get('pe_ratio'),
            'forward_pe': metrics.get('forward_pe'),
            'ps_ratio': metrics.get('ps_ratio'),
            'market_cap': metrics.get('market_cap'),
            'free_cash_flow': metrics.get('free_cash_flow'),
            'debt_to_equity': metrics.get('debt_to_equity'),
            'beta': metrics.get('beta'),
            'sector': metrics.get('sector'),
            'industry': metrics.get('industry'),
        }

        # Calculate PEG if possible
        if result['pe_ratio'] and result['earnings_growth'] and result['earnings_growth'] > 0:
            result['peg_ratio'] = result['pe_ratio'] / (result['earnings_growth'] * 100)
        else:
            result['peg_ratio'] = None

        # Calculate FCF Yield
        if result['free_cash_flow'] and result['market_cap'] and result['market_cap'] > 0:
            result['fcf_yield'] = result['free_cash_flow'] / result['market_cap']
        else:
            result['fcf_yield'] = None

        # 52-week return
        if prices and len(prices) >= 252:
            result['return_52w'] = (prices[-1][1] - prices[0][1]) / prices[0][1]
        elif prices and len(prices) > 1:
            result['return_52w'] = (prices[-1][1] - prices[0][1]) / prices[0][1]
        else:
            result['return_52w'] = None

        # Current price
        if prices:
            result['current_price'] = prices[-1][1]

        return result

    def screen_universe(
        self,
        symbols: List[str],
        min_score: float = 50.0,
        top_n: Optional[int] = None
    ) -> List[TenBaggerScore]:
        """
        Screen multiple stocks and return ranked results.

        Args:
            symbols: List of stock symbols to screen
            min_score: Minimum score threshold (default 50)
            top_n: Return only top N results (optional)

        Returns:
            List of TenBaggerScore objects, sorted by total_score descending
        """
        results = []

        for symbol in symbols:
            try:
                score = self.score_stock(symbol)
                if score and score.total_score >= min_score:
                    results.append(score)
            except Exception as e:
                logger.warning(f"Error screening {symbol}: {e}")
                continue

        # Sort by total score descending
        results.sort(key=lambda x: x.total_score, reverse=True)

        if top_n:
            return results[:top_n]

        return results

    def get_sector_leaders(self, top_n: int = 3) -> Dict[str, List[TenBaggerScore]]:
        """
        Get top stocks in each growth sector.

        Args:
            top_n: Number of top stocks per sector

        Returns:
            Dict mapping sector name to list of TenBaggerScore
        """
        sector_leaders = {}

        for sector_name, symbols in GROWTH_SECTORS.items():
            sector_scores = []
            for symbol in symbols:
                try:
                    score = self.score_stock(symbol)
                    if score:
                        sector_scores.append(score)
                except Exception as e:
                    logger.warning(f"Error scoring {symbol}: {e}")
                    continue

            # Sort and take top N
            sector_scores.sort(key=lambda x: x.total_score, reverse=True)
            sector_leaders[sector_name] = sector_scores[:top_n]

        return sector_leaders

    def compare_stocks(self, symbols: List[str]) -> List[TenBaggerScore]:
        """
        Compare multiple stocks side by side.

        Args:
            symbols: List of stock symbols to compare

        Returns:
            List of TenBaggerScore objects
        """
        results = []
        for symbol in symbols:
            score = self.score_stock(symbol)
            if score:
                results.append(score)

        return sorted(results, key=lambda x: x.total_score, reverse=True)
