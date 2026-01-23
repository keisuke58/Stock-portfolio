"""
状態機械: WATCH/BASE/BUY 判定
急落→低迷→反転の状態遷移を管理
"""
from typing import Optional, List, Tuple
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features import FeatureCalculator
from fetchers import YahooFetcher, CoinGeckoFetcher


def is_crypto_symbol(symbol: str) -> bool:
    """
    シンボルが仮想通貨かどうかを判定
    """
    crypto_symbols = {
        'BTC', 'ETH', 'BNB', 'SOL', 'ADA', 'XRP', 'DOGE', 
        'DOT', 'MATIC', 'AVAX', 'LINK', 'UNI', 'ATOM', 'LTC'
    }
    
    if symbol.upper() in crypto_symbols:
        return True
    
    crypto_ids = ['bitcoin', 'ethereum', 'binancecoin', 'solana', 'cardano', 
                  'ripple', 'dogecoin', 'polkadot', 'matic-network', 'avalanche-2']
    
    if symbol.lower() in crypto_ids:
        return True
    
    return False


class StateMachine:
    """状態遷移を管理するクラス"""
    
    def __init__(self, yahoo_fetcher: YahooFetcher = None, coingecko_fetcher: CoinGeckoFetcher = None):
        self.yahoo_fetcher = yahoo_fetcher or YahooFetcher()
        self.coingecko_fetcher = coingecko_fetcher or CoinGeckoFetcher()
    
    def detect_watch_signal(self, symbol: str) -> Tuple[bool, Optional[float]]:
        """
        WATCHシグナル（急落）を検出
        条件: 3日リターン ≤ -12%
        戻り値: (検出されたか, 3日リターン値)
        """
        if is_crypto_symbol(symbol):
            prices = self.coingecko_fetcher.get_historical_prices(symbol, days=10)
        else:
            prices = self.yahoo_fetcher.get_historical_prices(symbol, days=10)
        
        if not prices:
            return (False, None)
        
        return_3d = FeatureCalculator.calculate_return(prices, 3)
        if return_3d is None:
            return (False, None)
        
        return (return_3d <= -12.0, return_3d)
    
    def detect_base_signal(self, symbol: str) -> Tuple[bool, Optional[float]]:
        """
        BASEシグナル（低迷）を検出
        条件: WATCH後、7日の価格レンジが ±5%以内
        戻り値: (検出されたか, レンジ幅%)
        """
        if is_crypto_symbol(symbol):
            prices = self.coingecko_fetcher.get_historical_prices(symbol, days=15)
        else:
            prices = self.yahoo_fetcher.get_historical_prices(symbol, days=15)
        
        if not prices:
            return (False, None)
        
        range_info = FeatureCalculator.calculate_range(prices, 7)
        if range_info is None:
            return (False, None)
        
        min_price, max_price, range_pct = range_info
        return (range_pct <= 5.0, range_pct)
    
    def detect_buy_signal(self, symbol: str) -> Tuple[bool, Optional[float]]:
        """
        BUYシグナル（反転）を検出
        条件: 直近5日高値を上抜け
        戻り値: (検出されたか, 現在価格)
        """
        if is_crypto_symbol(symbol):
            prices = self.coingecko_fetcher.get_historical_prices(symbol, days=10)
        else:
            prices = self.yahoo_fetcher.get_historical_prices(symbol, days=10)
        
        if not prices:
            return (False, None)
        
        breakout = FeatureCalculator.calculate_high_breakout(prices, 5)
        current_price = prices[-1][1] if prices else None
        
        return (breakout, current_price)
    
    def determine_state(self, symbol: str, current_state: Optional[str] = None) -> str:
        """
        現在の状態を判定（状態遷移ロジック）
        戻り値: 'NORMAL', 'WATCH', 'BASE', 'BUY' のいずれか
        """
        # BUYシグナルが最優先
        buy_detected, _ = self.detect_buy_signal(symbol)
        if buy_detected:
            return 'BUY'
        
        # BASEシグナル（WATCH状態の時のみ有効）
        if current_state in ['WATCH', 'BASE']:
            base_detected, _ = self.detect_base_signal(symbol)
            if base_detected:
                return 'BASE'
        
        # WATCHシグナル（急落）
        watch_detected, _ = self.detect_watch_signal(symbol)
        if watch_detected:
            return 'WATCH'
        
        # デフォルトはNORMAL
        return 'NORMAL'


# グローバル関数（後方互換性のため）
def determine_state(symbol: str, current_state: Optional[str] = None) -> str:
    """グローバル関数: 状態を判定"""
    state_machine = StateMachine()
    return state_machine.determine_state(symbol, current_state)
