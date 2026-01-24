"""
指標計算モジュール
リターン、ATH比、ボラティリティ、出来高等を計算
"""
from typing import Optional, List, Tuple
from datetime import datetime
import statistics


class FeatureCalculator:
    """各種指標を計算するクラス"""
    
    @staticmethod
    def calculate_return(prices: List[Tuple[datetime, float]], days: int) -> Optional[float]:
        """
        指定日数のリターンを計算
        戻り値: パーセンテージ（例: -12.5 は -12.5%）
        """
        if len(prices) < days + 1:
            return None
        
        latest_price = prices[-1][1]
        old_price = prices[-days-1][1] if len(prices) >= days + 1 else prices[0][1]
        
        if old_price == 0:
            return None
        
        return ((latest_price - old_price) / old_price) * 100
    
    @staticmethod
    def calculate_ath_ratio(prices: List[Tuple[datetime, float]]) -> Optional[float]:
        """
        ATH（All-Time High）比を計算
        戻り値: 現在価格 / ATH価格（0.0-1.0、低いほど割安）
        """
        if not prices or len(prices) < 2:
            return None
        
        current_price = prices[-1][1]
        ath_price = max([p[1] for p in prices])
        
        if ath_price == 0:
            return None
        
        return current_price / ath_price
    
    @staticmethod
    def calculate_volatility(prices: List[Tuple[datetime, float]]) -> Optional[float]:
        """
        ボラティリティを計算（標準偏差）
        戻り値: 標準偏差（パーセンテージ）
        """
        if len(prices) < 2:
            return None
        
        price_values = [p[1] for p in prices]
        
        # 日次リターンを計算
        returns = []
        for i in range(1, len(price_values)):
            if price_values[i-1] != 0:
                daily_return = (price_values[i] - price_values[i-1]) / price_values[i-1]
                returns.append(daily_return)
        
        if len(returns) < 2:
            return None
        
        # 標準偏差を計算
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        
        return std_dev * 100  # パーセンテージに変換
    
    @staticmethod
    def calculate_range(prices: List[Tuple[datetime, float]], days: int) -> Optional[Tuple[float, float, float]]:
        """
        指定日数の価格レンジを計算
        戻り値: (min_price, max_price, range_pct) または None
        range_pct: (max - min) / min * 100
        """
        if len(prices) < days:
            return None
        
        # 直近days日分
        recent_prices = [p[1] for p in prices[-days:]]
        min_price = min(recent_prices)
        max_price = max(recent_prices)
        
        if min_price == 0:
            return None
        
        range_pct = ((max_price - min_price) / min_price) * 100
        return (min_price, max_price, range_pct)
    
    @staticmethod
    def calculate_high_breakout(prices: List[Tuple[datetime, float]], days: int) -> bool:
        """
        直近days日間の高値を上抜けしたかどうか
        戻り値: True=上抜け、False=未上抜け
        """
        if len(prices) < days + 1:
            return False
        
        # 直近days日分（最新を除く）
        last_days = [p[1] for p in prices[-days-1:-1]]
        if not last_days:
            return False
        
        high_price = max(last_days)
        current_price = prices[-1][1]
        
        return current_price > high_price
    
    @staticmethod
    def calculate_all_features(prices: List[Tuple[datetime, float]]) -> dict:
        """
        全指標を一度に計算
        戻り値: 指標の辞書
        """
        features = {}
        
        # リターン（3日、7日、30日）
        features['return_3d'] = FeatureCalculator.calculate_return(prices, 3)
        features['return_7d'] = FeatureCalculator.calculate_return(prices, 7)
        features['return_30d'] = FeatureCalculator.calculate_return(prices, 30)
        
        # ATH比
        features['ath_ratio'] = FeatureCalculator.calculate_ath_ratio(prices)
        
        # ボラティリティ
        features['volatility'] = FeatureCalculator.calculate_volatility(prices)
        
        # レンジ（7日、14日）
        range_7d = FeatureCalculator.calculate_range(prices, 7)
        if range_7d:
            features['range_7d_min'], features['range_7d_max'], features['range_7d_pct'] = range_7d
        else:
            features['range_7d_min'] = None
            features['range_7d_max'] = None
            features['range_7d_pct'] = None
        
        range_14d = FeatureCalculator.calculate_range(prices, 14)
        if range_14d:
            features['range_14d_min'], features['range_14d_max'], features['range_14d_pct'] = range_14d
        else:
            features['range_14d_min'] = None
            features['range_14d_max'] = None
            features['range_14d_pct'] = None
        
        # 高値ブレイク（5日、10日）
        features['breakout_5d'] = FeatureCalculator.calculate_high_breakout(prices, 5)
        features['breakout_10d'] = FeatureCalculator.calculate_high_breakout(prices, 10)
        
        return features
