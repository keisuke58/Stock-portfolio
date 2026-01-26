"""
Yahoo Finance (yfinance) から米国株データを取得
キャッシュ対応
"""
from typing import Optional, List, Tuple
from datetime import datetime
import logging
import yfinance as yf
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cache import PriceCache
from core.constants import CACHE_TTL, API_TIMEOUTS

logger = logging.getLogger(__name__)


class YahooFetcher:
    """Yahoo Financeからデータを取得するクラス"""
    
    def __init__(self, cache: Optional[PriceCache] = None):
        self.cache = cache or PriceCache()
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """現在価格を取得（キャッシュ優先）"""
        # キャッシュから取得を試みる
        cached_price = self.cache.get_current_price(symbol)
        if cached_price is not None:
            return cached_price
        
        # キャッシュになければAPIから取得
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            
            # 最新の終値を取得
            if 'regularMarketPrice' in info:
                price = float(info['regularMarketPrice'])
            elif 'previousClose' in info:
                price = float(info['previousClose'])
            else:
                # 履歴データから最新の終値を取得
                hist = ticker.history(period="1d", interval="1d")
                if not hist.empty:
                    price = float(hist['Close'].iloc[-1])
                else:
                    return None
            
            # キャッシュに保存
            self.cache.set_current_price(symbol, price, ttl_seconds=CACHE_TTL.CURRENT_PRICE)
            return price

        except requests.RequestException as e:
            logger.warning(f"Network error fetching Yahoo price for {symbol}: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Data error fetching Yahoo price for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Yahoo price for {symbol}: {e}", exc_info=True)
            return None
    
    def get_historical_prices(self, symbol: str, days: int = 30) -> Optional[List[Tuple[datetime, float]]]:
        """履歴価格を取得（キャッシュ優先）"""
        # キャッシュから取得を試みる（同じdaysの場合のみ）
        cached = self.cache.get_historical_prices(symbol)
        if cached is not None:
            # キャッシュのデータが十分な日数分あるかチェック
            if len(cached) >= days:
                return cached[-days:]  # 必要な日数分だけ返す
        
        # キャッシュになければAPIから取得
        try:
            ticker = yf.Ticker(symbol.upper())
            hist = ticker.history(period=f"{days}d", interval="1d")
            
            if hist.empty:
                return None
            
            # datetimeと終値（Close）のタプルリストに変換
            result = []
            for date, row in hist.iterrows():
                dt = date.to_pydatetime() if hasattr(date, 'to_pydatetime') else datetime.fromtimestamp(date.timestamp())
                price = float(row['Close'])
                result.append((dt, price))
            
            result = sorted(result, key=lambda x: x[0])  # 時系列順にソート

            # キャッシュに保存
            self.cache.set_historical_prices(symbol, result, ttl_seconds=CACHE_TTL.HISTORICAL_PRICES)

            return result

        except requests.RequestException as e:
            logger.warning(f"Network error fetching Yahoo historical prices for {symbol}: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Data error fetching Yahoo historical prices for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Yahoo historical prices for {symbol}: {e}", exc_info=True)
            return None
    
    def get_metrics(self, symbol: str) -> dict:
        """財務指標を取得（PER、PBRなど）"""
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            
            return {
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'pb_ratio': info.get('priceToBook'),
                'dividend_yield': info.get('dividendYield'),
                'market_cap': info.get('marketCap'),
                'enterprise_value': info.get('enterpriseValue'),
            }
        except requests.RequestException as e:
            logger.warning(f"Network error fetching Yahoo metrics for {symbol}: {e}")
            return self._empty_metrics()
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Data error fetching Yahoo metrics for {symbol}: {e}")
            return self._empty_metrics()
        except Exception as e:
            logger.error(f"Unexpected error fetching Yahoo metrics for {symbol}: {e}", exc_info=True)
            return self._empty_metrics()

    @staticmethod
    def _empty_metrics() -> dict:
        """Return empty metrics dict."""
        return {
            'pe_ratio': None,
            'forward_pe': None,
            'pb_ratio': None,
            'dividend_yield': None,
            'market_cap': None,
            'enterprise_value': None,
        }

    def get_historical_prices_extended(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[List[Tuple[datetime, float]]]:
        """
        指定期間の履歴価格を取得（バックテスト用、最大5年）

        Args:
            symbol: 銘柄シンボル
            start_date: 開始日
            end_date: 終了日

        Returns:
            [(datetime, price), ...] or None
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            hist = ticker.history(start=start_date, end=end_date, interval="1d")

            if hist.empty:
                return None

            result = []
            for date, row in hist.iterrows():
                dt = date.to_pydatetime() if hasattr(date, 'to_pydatetime') else datetime.fromtimestamp(date.timestamp())
                # Make datetime timezone-naive for consistency
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                price = float(row['Close'])
                result.append((dt, price))

            return sorted(result, key=lambda x: x[0])

        except Exception as e:
            logger.warning(f"Error fetching extended historical prices for {symbol}: {e}")
            return None

    def get_fundamental_data(self, symbol: str) -> Optional[dict]:
        """
        ファンダメンタルデータを取得（Deep Bottom分析用）

        Returns:
            dict with: pe_ratio, pb_ratio, free_cash_flow, debt_to_equity,
                       revenue_growth, market_cap, profit_margin, etc.
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info

            return {
                # Valuation
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'pb_ratio': info.get('priceToBook'),
                'ps_ratio': info.get('priceToSalesTrailing12Months'),

                # Profitability
                'profit_margin': info.get('profitMargins'),
                'operating_margin': info.get('operatingMargins'),
                'roe': info.get('returnOnEquity'),
                'roa': info.get('returnOnAssets'),

                # Financial Health
                'free_cash_flow': info.get('freeCashflow'),
                'operating_cash_flow': info.get('operatingCashflow'),
                'total_debt': info.get('totalDebt'),
                'total_cash': info.get('totalCash'),
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'quick_ratio': info.get('quickRatio'),

                # Growth
                'revenue_growth': info.get('revenueGrowth'),
                'earnings_growth': info.get('earningsGrowth'),
                'earnings_quarterly_growth': info.get('earningsQuarterlyGrowth'),

                # Size
                'market_cap': info.get('marketCap'),
                'enterprise_value': info.get('enterpriseValue'),

                # Dividend
                'dividend_yield': info.get('dividendYield'),
                'payout_ratio': info.get('payoutRatio'),

                # Other
                'beta': info.get('beta'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),

                # Company Info
                'company_name': info.get('shortName') or info.get('longName'),
                'website': info.get('website'),
            }
        except Exception as e:
            logger.warning(f"Error fetching fundamental data for {symbol}: {e}")
            return None

    def get_company_info(self, symbol: str) -> Optional[dict]:
        """
        Get company name and website.

        Returns:
            dict with: name, website, sector, industry
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info

            return {
                'name': info.get('shortName') or info.get('longName') or symbol,
                'website': info.get('website'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
            }
        except Exception as e:
            logger.debug(f"Error fetching company info for {symbol}: {e}")
            return None

    def get_historical_prices_with_volume(
        self,
        symbol: str,
        days: int = 365
    ) -> Optional[List[Tuple[datetime, float, float]]]:
        """
        履歴価格と出来高を取得（Deep Bottom V2スコアリング用）

        Args:
            symbol: 銘柄シンボル
            days: 取得日数（デフォルト365日）

        Returns:
            [(datetime, price, volume), ...] or None
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            hist = ticker.history(period=f"{days}d", interval="1d")

            if hist.empty:
                return None

            result = []
            for date, row in hist.iterrows():
                dt = date.to_pydatetime() if hasattr(date, 'to_pydatetime') else datetime.fromtimestamp(date.timestamp())
                # Make datetime timezone-naive for consistency
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                price = float(row['Close'])
                volume = float(row['Volume']) if 'Volume' in row else 0.0
                result.append((dt, price, volume))

            return sorted(result, key=lambda x: x[0])

        except Exception as e:
            logger.warning(f"Error fetching historical prices with volume for {symbol}: {e}")
            return None

    def _get_coingecko_id(self, symbol: str) -> str:
        """Compatibility method for BaseFetcher interface."""
        return symbol.lower()
