"""
Relative Strength Ranking System (IBD-Style)
Calculates price performance percentile rankings (1-99) comparing
a stock's performance against all other stocks in the market.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime, timedelta
import logging
import statistics
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetchers import YahooFetcher

logger = logging.getLogger(__name__)


@dataclass
class RSRating:
    """Relative Strength Rating result for a stock."""
    symbol: str
    rs_rating: int                    # 1-99 percentile
    rs_rating_sector: Optional[int]   # 1-99 vs sector peers

    # Component returns (weighted for RS calculation)
    return_3m: Optional[float]        # 3-month return
    return_6m: Optional[float]        # 6-month return
    return_9m: Optional[float]        # 9-month return
    return_12m: Optional[float]       # 12-month return
    weighted_return: float            # IBD-weighted composite

    # Trend indicators
    rs_trend: str                     # IMPROVING, STABLE, DECLINING
    rs_change_4w: Optional[int]       # Change in RS over 4 weeks

    # Additional context
    sector: Optional[str] = None
    industry: Optional[str] = None
    current_price: Optional[float] = None

    # Percentile details
    percentile_3m: Optional[int] = None
    percentile_6m: Optional[int] = None
    percentile_12m: Optional[int] = None


class RelativeStrengthCalculator:
    """
    Calculator for IBD-style Relative Strength ratings.

    The RS Rating measures a stock's price performance over the last 12 months
    compared to all other stocks. A rating of 99 means the stock outperformed
    99% of all other stocks.

    IBD Weighting:
    - 40% weight on most recent quarter (3 months)
    - 20% weight on prior quarter (3-6 months)
    - 20% weight on 6-9 months ago
    - 20% weight on 9-12 months ago
    """

    # Default benchmark universe for comparison
    DEFAULT_UNIVERSE = [
        # S&P 500 representative sample
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B',
        'UNH', 'JNJ', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'MRK', 'ABBV',
        'PEP', 'COST', 'TMO', 'AVGO', 'CSCO', 'WMT', 'DIS', 'VZ', 'ADBE',
        'ACN', 'NFLX', 'CRM', 'AMD', 'INTC', 'QCOM', 'TXN', 'HON', 'IBM',
        # Growth stocks
        'CRWD', 'SNOW', 'DDOG', 'NET', 'ZS', 'PANW', 'NOW', 'SHOP', 'SQ',
        'COIN', 'MELI', 'SE', 'ROKU', 'RBLX', 'U', 'PATH', 'MDB', 'TEAM',
        # Semiconductors
        'TSM', 'ASML', 'LRCX', 'AMAT', 'KLAC', 'MRVL', 'MU', 'ADI', 'NXPI',
        # Healthcare
        'LLY', 'PFE', 'BMY', 'GILD', 'REGN', 'VRTX', 'MRNA', 'ISRG', 'DHR',
        # Financials
        'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'COF',
        # Industrials
        'CAT', 'DE', 'BA', 'RTX', 'LMT', 'GE', 'UPS', 'FDX', 'UNP',
        # Consumer
        'NKE', 'SBUX', 'MCD', 'LOW', 'TGT', 'TJX', 'ROST', 'CMG', 'YUM',
        # Energy
        'XOM', 'COP', 'SLB', 'EOG', 'OXY', 'PSX', 'VLO', 'MPC',
        # Communications
        'CMCSA', 'T', 'TMUS', 'CHTR', 'EA', 'TTWO', 'WBD',
    ]

    # Sector groupings for sector-relative RS
    SECTOR_GROUPS = {
        'Technology': ['AAPL', 'MSFT', 'GOOGL', 'META', 'CRM', 'ADBE', 'NOW', 'ORCL', 'IBM', 'CSCO'],
        'Semiconductors': ['NVDA', 'AMD', 'AVGO', 'QCOM', 'TXN', 'INTC', 'MU', 'LRCX', 'AMAT', 'KLAC',
                          'MRVL', 'ADI', 'NXPI', 'TSM', 'ASML'],
        'Software': ['MSFT', 'CRM', 'ADBE', 'NOW', 'SNOW', 'DDOG', 'NET', 'ZS', 'PANW', 'CRWD',
                    'MDB', 'TEAM', 'OKTA', 'SPLK', 'HUBS'],
        'E-Commerce': ['AMZN', 'SHOP', 'MELI', 'SE', 'BABA', 'JD', 'PDD', 'ETSY', 'EBAY', 'W'],
        'Healthcare': ['UNH', 'JNJ', 'LLY', 'PFE', 'ABBV', 'MRK', 'TMO', 'DHR', 'BMY', 'AMGN',
                      'GILD', 'REGN', 'VRTX', 'ISRG', 'MDT'],
        'Financials': ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'V', 'MA'],
        'Consumer': ['TSLA', 'NKE', 'SBUX', 'MCD', 'HD', 'LOW', 'TGT', 'COST', 'WMT', 'TJX'],
        'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'OXY', 'PSX', 'VLO', 'MPC', 'HAL'],
        'Industrials': ['CAT', 'DE', 'BA', 'RTX', 'LMT', 'GE', 'HON', 'UPS', 'UNP', 'MMM'],
    }

    def __init__(
        self,
        yahoo_fetcher: Optional[YahooFetcher] = None,
        universe: Optional[List[str]] = None
    ):
        self.fetcher = yahoo_fetcher or YahooFetcher()
        self.universe = universe or self.DEFAULT_UNIVERSE
        self._returns_cache: Dict[str, Dict[str, float]] = {}
        self._cache_date: Optional[datetime] = None

    def calculate_rs_rating(
        self,
        symbol: str,
        include_sector_rs: bool = True,
        refresh_cache: bool = False
    ) -> Optional[RSRating]:
        """
        Calculate the Relative Strength rating for a stock.

        Args:
            symbol: Stock ticker symbol
            include_sector_rs: Also calculate sector-relative RS
            refresh_cache: Force refresh of universe returns cache

        Returns:
            RSRating object or None if calculation fails
        """
        try:
            # Get stock's returns
            stock_returns = self._get_stock_returns(symbol)
            if not stock_returns or stock_returns.get('weighted') is None:
                logger.warning(f"Could not calculate returns for {symbol}")
                return None

            # Build/refresh universe returns cache
            if refresh_cache or not self._is_cache_valid():
                self._build_universe_cache()

            # Calculate percentile ranking
            rs_rating = self._calculate_percentile(
                stock_returns['weighted'],
                [r.get('weighted', 0) for r in self._returns_cache.values() if r.get('weighted') is not None]
            )

            # Calculate individual period percentiles
            percentile_3m = self._calculate_percentile(
                stock_returns.get('return_3m'),
                [r.get('return_3m', 0) for r in self._returns_cache.values() if r.get('return_3m') is not None]
            ) if stock_returns.get('return_3m') is not None else None

            percentile_6m = self._calculate_percentile(
                stock_returns.get('return_6m'),
                [r.get('return_6m', 0) for r in self._returns_cache.values() if r.get('return_6m') is not None]
            ) if stock_returns.get('return_6m') is not None else None

            percentile_12m = self._calculate_percentile(
                stock_returns.get('return_12m'),
                [r.get('return_12m', 0) for r in self._returns_cache.values() if r.get('return_12m') is not None]
            ) if stock_returns.get('return_12m') is not None else None

            # Calculate sector RS if requested
            sector_rs = None
            sector = None
            if include_sector_rs:
                sector = self._identify_sector(symbol)
                if sector:
                    sector_rs = self._calculate_sector_rs(symbol, sector, stock_returns['weighted'])

            # Determine RS trend
            rs_trend = self._determine_rs_trend(symbol, stock_returns)
            rs_change_4w = self._calculate_rs_change(symbol)

            # Get additional info
            fundamentals = self.fetcher.get_fundamental_data(symbol)
            industry = fundamentals.get('industry') if fundamentals else None

            prices = self.fetcher.get_historical_prices(symbol, days=5)
            current_price = prices[-1][1] if prices else None

            return RSRating(
                symbol=symbol,
                rs_rating=rs_rating,
                rs_rating_sector=sector_rs,
                return_3m=stock_returns.get('return_3m'),
                return_6m=stock_returns.get('return_6m'),
                return_9m=stock_returns.get('return_9m'),
                return_12m=stock_returns.get('return_12m'),
                weighted_return=stock_returns['weighted'],
                rs_trend=rs_trend,
                rs_change_4w=rs_change_4w,
                sector=sector,
                industry=industry,
                current_price=current_price,
                percentile_3m=percentile_3m,
                percentile_6m=percentile_6m,
                percentile_12m=percentile_12m
            )

        except Exception as e:
            logger.error(f"Error calculating RS for {symbol}: {e}")
            return None

    def _get_stock_returns(self, symbol: str) -> Optional[Dict[str, float]]:
        """Calculate returns for different time periods."""
        try:
            prices = self.fetcher.get_historical_prices(symbol, days=365)
            if not prices or len(prices) < 60:  # Need at least ~3 months
                return None

            current_price = prices[-1][1]

            # Calculate returns for each period
            returns = {}

            # 3-month return (~63 trading days)
            if len(prices) >= 63:
                price_3m_ago = prices[-63][1]
                returns['return_3m'] = (current_price - price_3m_ago) / price_3m_ago

            # 6-month return (~126 trading days)
            if len(prices) >= 126:
                price_6m_ago = prices[-126][1]
                returns['return_6m'] = (current_price - price_6m_ago) / price_6m_ago

            # 9-month return (~189 trading days)
            if len(prices) >= 189:
                price_9m_ago = prices[-189][1]
                returns['return_9m'] = (current_price - price_9m_ago) / price_9m_ago

            # 12-month return (~252 trading days)
            if len(prices) >= 252:
                price_12m_ago = prices[0][1]  # Use first available
                returns['return_12m'] = (current_price - price_12m_ago) / price_12m_ago
            elif len(prices) > 0:
                # Use available data
                price_start = prices[0][1]
                returns['return_12m'] = (current_price - price_start) / price_start

            # Calculate IBD-weighted return
            # 40% recent quarter, 20% each prior quarter
            weighted = 0.0
            weight_sum = 0.0

            if 'return_3m' in returns:
                # Most recent 3 months (Q1) - 40% weight
                weighted += returns['return_3m'] * 0.40
                weight_sum += 0.40

            if 'return_6m' in returns and 'return_3m' in returns:
                # 3-6 months ago (Q2) - 20% weight
                q2_return = returns['return_6m'] - returns['return_3m']
                weighted += q2_return * 0.20
                weight_sum += 0.20

            if 'return_9m' in returns and 'return_6m' in returns:
                # 6-9 months ago (Q3) - 20% weight
                q3_return = returns['return_9m'] - returns['return_6m']
                weighted += q3_return * 0.20
                weight_sum += 0.20

            if 'return_12m' in returns and 'return_9m' in returns:
                # 9-12 months ago (Q4) - 20% weight
                q4_return = returns['return_12m'] - returns['return_9m']
                weighted += q4_return * 0.20
                weight_sum += 0.20

            # Normalize if we don't have all periods
            if weight_sum > 0:
                returns['weighted'] = weighted / weight_sum * (1 / 0.4)  # Scale as if 40% = full weight
            else:
                returns['weighted'] = returns.get('return_3m', 0)

            return returns

        except Exception as e:
            logger.warning(f"Error getting returns for {symbol}: {e}")
            return None

    def _build_universe_cache(self):
        """Build cache of returns for the comparison universe."""
        logger.info(f"Building RS universe cache for {len(self.universe)} stocks...")
        self._returns_cache = {}

        for symbol in self.universe:
            try:
                returns = self._get_stock_returns(symbol)
                if returns:
                    self._returns_cache[symbol] = returns
            except Exception as e:
                logger.debug(f"Skipping {symbol} in universe cache: {e}")
                continue

        self._cache_date = datetime.now()
        logger.info(f"RS universe cache built with {len(self._returns_cache)} stocks")

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid (less than 1 day old)."""
        if not self._cache_date or not self._returns_cache:
            return False
        return (datetime.now() - self._cache_date).total_seconds() < 86400

    def _calculate_percentile(self, value: Optional[float], distribution: List[float]) -> int:
        """Calculate percentile ranking (1-99)."""
        if value is None or not distribution:
            return 50  # Default to median

        # Count how many values are below the target
        below_count = sum(1 for v in distribution if v < value)
        percentile = (below_count / len(distribution)) * 100

        # Clamp to 1-99 range
        return max(1, min(99, int(percentile)))

    def _identify_sector(self, symbol: str) -> Optional[str]:
        """Identify which sector a stock belongs to."""
        for sector, symbols in self.SECTOR_GROUPS.items():
            if symbol.upper() in symbols:
                return sector
        return None

    def _calculate_sector_rs(
        self,
        symbol: str,
        sector: str,
        weighted_return: float
    ) -> Optional[int]:
        """Calculate RS relative to sector peers."""
        sector_symbols = self.SECTOR_GROUPS.get(sector, [])
        if not sector_symbols or symbol not in sector_symbols:
            return None

        # Get sector returns from cache
        sector_returns = []
        for s in sector_symbols:
            if s in self._returns_cache:
                weighted = self._returns_cache[s].get('weighted')
                if weighted is not None:
                    sector_returns.append(weighted)

        if not sector_returns:
            return None

        return self._calculate_percentile(weighted_return, sector_returns)

    def _determine_rs_trend(self, symbol: str, returns: Dict[str, float]) -> str:
        """Determine if RS is improving, stable, or declining."""
        return_3m = returns.get('return_3m')
        return_6m = returns.get('return_6m')
        return_12m = returns.get('return_12m')

        if return_3m is None:
            return 'STABLE'

        # Compare recent performance to longer-term
        if return_6m is not None:
            # Recent 3m return vs prior 3m return
            prior_3m = return_6m - return_3m

            if return_3m > prior_3m * 1.2:  # 20% better
                return 'IMPROVING'
            elif return_3m < prior_3m * 0.8:  # 20% worse
                return 'DECLINING'

        return 'STABLE'

    def _calculate_rs_change(self, symbol: str) -> Optional[int]:
        """Calculate change in RS rating over past 4 weeks."""
        # This would require historical RS data storage
        # For now, return None (to be implemented with data persistence)
        return None

    def rank_stocks(
        self,
        symbols: List[str],
        min_rs: int = 0
    ) -> List[RSRating]:
        """
        Rank multiple stocks by RS rating.

        Args:
            symbols: List of stock symbols
            min_rs: Minimum RS rating to include

        Returns:
            List of RSRating sorted by rs_rating descending
        """
        # First, ensure cache is populated
        if not self._is_cache_valid():
            self._build_universe_cache()

        results = []
        for symbol in symbols:
            try:
                rating = self.calculate_rs_rating(symbol, include_sector_rs=True)
                if rating and rating.rs_rating >= min_rs:
                    results.append(rating)
            except Exception as e:
                logger.warning(f"Error ranking {symbol}: {e}")
                continue

        # Sort by RS rating descending
        return sorted(results, key=lambda x: x.rs_rating, reverse=True)

    def get_rs_leaders(
        self,
        min_rs: int = 80,
        top_n: int = 20
    ) -> List[RSRating]:
        """
        Get stocks with highest RS ratings from the universe.

        Args:
            min_rs: Minimum RS rating
            top_n: Number of top stocks to return

        Returns:
            List of top RS-rated stocks
        """
        return self.rank_stocks(self.universe, min_rs=min_rs)[:top_n]

    def get_sector_rs_leaders(self, top_n: int = 3) -> Dict[str, List[RSRating]]:
        """
        Get top RS stocks in each sector.

        Args:
            top_n: Number of top stocks per sector

        Returns:
            Dict mapping sector to list of RSRating
        """
        sector_leaders = {}

        for sector, symbols in self.SECTOR_GROUPS.items():
            ratings = self.rank_stocks(symbols)
            sector_leaders[sector] = ratings[:top_n]

        return sector_leaders

    def get_improving_rs_stocks(
        self,
        symbols: List[str] = None,
        min_rs: int = 50
    ) -> List[RSRating]:
        """
        Find stocks with improving RS trend.

        Args:
            symbols: List to scan (default: universe)
            min_rs: Minimum current RS rating

        Returns:
            List of stocks with IMPROVING trend
        """
        scan_list = symbols or self.universe
        ratings = self.rank_stocks(scan_list, min_rs=min_rs)

        return [r for r in ratings if r.rs_trend == 'IMPROVING']
