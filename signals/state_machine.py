"""
状態機械: WATCH/BASE/BUY/DEEP_BOTTOM 判定
急落→低迷→反転の状態遷移を管理
長期投資向けのDEEP_BOTTOM検出も対応
"""
from typing import Optional, List, Tuple, Dict
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features import FeatureCalculator
from fetchers import YahooFetcher, CoinGeckoFetcher
from core.constants import DEEP_BOTTOM_THRESHOLDS


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

    def detect_deep_bottom_signal(self, symbol: str) -> Tuple[bool, Optional[Dict]]:
        """
        DEEP_BOTTOMシグナル（長期投資向け）を検出
        条件（全て満たす必要あり）:
          1. ATH下落率 >= 70%
          2. 52週安値に近い（10%以内）
          3. RSI <= 30（売られすぎ）
          4. 200日移動平均より下
          5. 7日リターン > -20%（急落中ではない）

        戻り値: (検出されたか, メトリクス辞書)
        """
        # 1年分のデータを取得
        if is_crypto_symbol(symbol):
            prices = self.coingecko_fetcher.get_historical_prices(
                symbol, days=DEEP_BOTTOM_THRESHOLDS.DETECTION_DAYS
            )
        else:
            prices = self.yahoo_fetcher.get_historical_prices(
                symbol, days=DEEP_BOTTOM_THRESHOLDS.DETECTION_DAYS
            )

        if not prices or len(prices) < 100:
            return (False, None)

        current_price = prices[-1][1]

        # 各指標を計算
        drawdown = FeatureCalculator.calculate_drawdown_from_ath(prices)
        week52_proximity = FeatureCalculator.calculate_52week_low_proximity(prices)
        rsi = FeatureCalculator.calculate_rsi(prices, 14)
        ma_200 = FeatureCalculator.calculate_moving_average(prices, DEEP_BOTTOM_THRESHOLDS.MA_PERIOD)
        return_7d = FeatureCalculator.calculate_return(prices, 7)

        # メトリクス辞書
        metrics = {
            'current_price': current_price,
            'ath_price': max([p[1] for p in prices]),
            'drawdown_pct': drawdown,
            'week52_low_proximity': week52_proximity,
            'rsi_14': rsi,
            'ma_200': ma_200,
            'return_7d': return_7d
        }

        # いずれかの指標が計算できない場合は検出しない
        if None in [drawdown, week52_proximity, rsi, return_7d]:
            return (False, metrics)

        # 条件チェック
        conditions = {
            'ath_drawdown': drawdown >= DEEP_BOTTOM_THRESHOLDS.ATH_DRAWDOWN_MIN,
            'near_52week_low': week52_proximity <= DEEP_BOTTOM_THRESHOLDS.WEEK52_LOW_PROXIMITY_MAX,
            'rsi_oversold': rsi <= DEEP_BOTTOM_THRESHOLDS.RSI_OVERSOLD,
            'below_ma200': ma_200 is not None and current_price < ma_200,
            'not_crashing': return_7d > DEEP_BOTTOM_THRESHOLDS.MIN_7D_RETURN
        }

        metrics['conditions'] = conditions
        all_conditions_met = all(conditions.values())

        return (all_conditions_met, metrics)

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

    def check_deep_bottom(self, symbol: str) -> Tuple[bool, Optional[Dict]]:
        """
        DEEP_BOTTOMシグナルを独立してチェック（長期投資向け）
        既存のWATCH/BASE/BUYフローとは別に動作

        戻り値: (DEEP_BOTTOM検出されたか, メトリクス辞書)
        """
        return self.detect_deep_bottom_signal(symbol)


# グローバル関数（後方互換性のため）
def determine_state(symbol: str, current_state: Optional[str] = None) -> str:
    """グローバル関数: 状態を判定"""
    state_machine = StateMachine()
    return state_machine.determine_state(symbol, current_state)
