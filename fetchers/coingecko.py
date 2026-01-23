"""
CoinGecko APIから仮想通貨データを取得
キャッシュ対応
"""
from typing import Optional, List, Tuple
from datetime import datetime
import logging
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cache import PriceCache
from core.constants import CACHE_TTL, API_TIMEOUTS

logger = logging.getLogger(__name__)


class CoinGeckoFetcher:
    """CoinGeckoからデータを取得するクラス"""
    
    # シンボルマッピング（BTC -> bitcoin）
    SYMBOL_MAP = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'BNB': 'binancecoin',
        'SOL': 'solana',
        'ADA': 'cardano',
        'XRP': 'ripple',
        'DOGE': 'dogecoin',
        'DOT': 'polkadot',
        'MATIC': 'matic-network',
        'AVAX': 'avalanche-2',
        'LINK': 'chainlink',
        'UNI': 'uniswap',
        'ATOM': 'cosmos',
        'LTC': 'litecoin',
    }
    
    def __init__(self, cache: Optional[PriceCache] = None):
        self.cache = cache or PriceCache()
    
    def _get_coin_id(self, symbol: str) -> str:
        """シンボルからCoinGeckoのcoin_idを取得"""
        return self.SYMBOL_MAP.get(symbol.upper(), symbol.lower())
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """現在価格を取得（キャッシュ優先）"""
        # キャッシュから取得を試みる
        cached_price = self.cache.get_current_price(symbol)
        if cached_price is not None:
            return cached_price
        
        # キャッシュになければAPIから取得
        coin_id = self._get_coin_id(symbol)
        
        try:
            url = f'https://api.coingecko.com/api/v3/simple/price'
            params = {
                'ids': coin_id,
                'vs_currencies': 'usd'
            }
            response = requests.get(url, params=params, timeout=API_TIMEOUTS.DEFAULT)
            response.raise_for_status()
            data = response.json()

            if coin_id in data and 'usd' in data[coin_id]:
                price = float(data[coin_id]['usd'])
                # キャッシュに保存
                self.cache.set_current_price(symbol, price, ttl_seconds=CACHE_TTL.CURRENT_PRICE)
                return price

            return None

        except requests.Timeout as e:
            logger.warning(f"Timeout fetching CoinGecko price for {symbol}: {e}")
            return None
        except requests.RequestException as e:
            logger.warning(f"Network error fetching CoinGecko price for {symbol}: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Data error fetching CoinGecko price for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching CoinGecko price for {symbol}: {e}", exc_info=True)
            return None
    
    def get_historical_prices(self, symbol: str, days: int = 30) -> Optional[List[Tuple[datetime, float]]]:
        """履歴価格を取得（キャッシュ優先）"""
        # キャッシュから取得を試みる
        cached = self.cache.get_historical_prices(symbol)
        if cached is not None:
            # キャッシュのデータが十分な日数分あるかチェック
            if len(cached) >= days:
                return cached[-days:]  # 必要な日数分だけ返す
        
        # キャッシュになければAPIから取得
        coin_id = self._get_coin_id(symbol)
        
        try:
            url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart'
            params = {
                'vs_currency': 'usd',
                'days': days,
                'interval': 'daily'  # 1日1回のデータポイント
            }
            response = requests.get(url, params=params, timeout=API_TIMEOUTS.DEFAULT)
            response.raise_for_status()
            data = response.json()

            # pricesは [[timestamp_ms, price], ...] の形式
            prices = data.get('prices', [])
            if not prices:
                return None

            # datetimeと価格のタプルリストに変換
            result = []
            for ts_ms, price in prices:
                dt = datetime.fromtimestamp(ts_ms / 1000)
                result.append((dt, float(price)))

            result = sorted(result, key=lambda x: x[0])  # 時系列順にソート

            # キャッシュに保存
            self.cache.set_historical_prices(symbol, result, ttl_seconds=CACHE_TTL.HISTORICAL_PRICES)

            return result

        except requests.Timeout as e:
            logger.warning(f"Timeout fetching CoinGecko historical prices for {symbol}: {e}")
            return None
        except requests.RequestException as e:
            logger.warning(f"Network error fetching CoinGecko historical prices for {symbol}: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Data error fetching CoinGecko historical prices for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching CoinGecko historical prices for {symbol}: {e}", exc_info=True)
            return None

    def _get_coingecko_id(self, symbol: str) -> str:
        """Alias for _get_coin_id for BaseFetcher compatibility."""
        return self._get_coin_id(symbol)
