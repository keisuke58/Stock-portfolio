"""
状態機械: WATCH/BASE/BUY 判定（新バージョン）
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
    """状態遷移を管理するクラス（新バージョン）"""
    
    def __init__(self, yahoo_fetcher: YahooFetcher = None, coingecko_fetcher: CoinGeckoFetcher = None):
        self.yahoo_fetcher = yahoo_fetcher or YahooFetcher()
        self.coingecko_fetcher = coingecko_fetcher or CoinGeckoFetcher()
    
    def detect_watch_signal(self, prices: List[Tuple[datetime, float]]) -> Tuple[bool, Optional[float]]:
        """
        WATCHシグナル（急落）を検出
        条件: 5日リターン <= -10%
        戻り値: (検出されたか, 5日リターン値)
        """
        if not prices or len(prices) < 6:
            return (False, None)
        
        return_5d = FeatureCalculator.calculate_return(prices, 5)
        if return_5d is None:
            return (False, None)
        
        return (return_5d <= -10.0, return_5d)
    
    def detect_base_signal(self, prices: List[Tuple[datetime, float]]) -> Tuple[bool, Optional[float]]:
        """
        BASEシグナル（低迷・横ばい）を検出
        条件: 直近5日がレンジ±5%以内（横ばい必須）
        戻り値: (検出されたか, レンジ幅%)
        """
        if not prices or len(prices) < 5:
            return (False, None)
        
        range_info = FeatureCalculator.calculate_range(prices, 5)
        if range_info is None:
            return (False, None)
        
        min_price, max_price, range_pct = range_info
        return (range_pct <= 5.0, range_pct)
    
    def detect_buy_signal(self, prices: List[Tuple[datetime, float]], was_base: bool) -> Tuple[bool, Optional[float]]:
        """
        BUYシグナル（反転）を検出
        条件: BASEの後に直近高値ブレイク（例: close > rolling_max(20)）
        戻り値: (検出されたか, 現在価格)
        """
        if not prices or len(prices) < 21:
            return (False, None)
        
        # BASE状態の後にのみBUYシグナルを検出
        if not was_base:
            return (False, None)
        
        # 直近20日の高値を計算（最新を除く）
        last_20_days = [p[1] for p in prices[-21:-1]]
        if not last_20_days:
            return (False, None)
        
        rolling_max_20 = max(last_20_days)
        current_price = prices[-1][1]
        
        # 現在価格が20日高値を上抜けしたか
        breakout = current_price > rolling_max_20
        
        return (breakout, current_price if breakout else None)
    
    def determine_state(
        self, 
        symbol: str, 
        prices: List[Tuple[datetime, float]],
        current_state: Optional[str] = None
    ) -> str:
        """
        現在の状態を判定（状態遷移ロジック）
        
        Args:
            symbol: シンボル名
            prices: 価格データのリスト [(datetime, price), ...]
            current_state: 現在の状態（'NORMAL', 'WATCH', 'BASE', 'BUY'）
            
        戻り値: 'NORMAL', 'WATCH', 'BASE', 'BUY' のいずれか
        """
        if not prices:
            return current_state or 'NORMAL'
        
        # 1. WATCHシグナル（急落）をチェック
        watch_detected, return_5d = self.detect_watch_signal(prices)
        if watch_detected:
            return 'WATCH'
        
        # 2. BASEシグナル（低迷・横ばい）をチェック
        # WATCH状態の時のみBASEに遷移可能
        if current_state in ['WATCH', 'BASE']:
            base_detected, range_pct = self.detect_base_signal(prices)
            if base_detected:
                # BASE状態を維持
                return 'BASE'
        
        # 3. BUYシグナル（反転）をチェック
        # BASE状態の時のみBUYに遷移可能
        if current_state == 'BASE':
            buy_detected, _ = self.detect_buy_signal(prices, was_base=True)
            if buy_detected:
                return 'BUY'
        
        # 4. 既にBUY状態の場合は維持
        if current_state == 'BUY':
            # BUY状態を維持（一度BUYになったら、明確なシグナルがない限り維持）
            return 'BUY'
        
        # デフォルトはNORMAL（または現在の状態を維持）
        return current_state or 'NORMAL'
