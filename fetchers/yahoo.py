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

    def _get_coingecko_id(self, symbol: str) -> str:
        """Compatibility method for BaseFetcher interface."""
        return symbol.lower()
