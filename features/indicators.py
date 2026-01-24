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
    def calculate_rsi(prices: List[Tuple[datetime, float]], period: int = 14) -> Optional[float]:
        """
        RSI（相対力指数）を計算
        戻り値: 0-100の値（30以下が売られすぎ、70以上が買われすぎ）
        """
        if len(prices) < period + 1:
            return None

        # 日次価格変動を計算
        changes = []
        for i in range(1, len(prices)):
            change = prices[i][1] - prices[i-1][1]
            changes.append(change)

        if len(changes) < period:
            return None

        # 直近period日分の変動を使用
        recent_changes = changes[-period:]

        # 上昇・下落を分離
        gains = [c if c > 0 else 0 for c in recent_changes]
        losses = [-c if c < 0 else 0 for c in recent_changes]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100.0  # 全て上昇

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_52week_low_proximity(prices: List[Tuple[datetime, float]]) -> Optional[float]:
        """
        52週（約252営業日）安値からの距離を計算
        戻り値: 0.0（安値）〜 1.0（高値）の間の値
        安値に近いほど0に近い
        """
        if len(prices) < 20:  # 最低20日分は必要
            return None

        # 直近252日分（または全データ）を使用
        lookback = min(len(prices), 252)
        recent_prices = [p[1] for p in prices[-lookback:]]

        current_price = recent_prices[-1]
        low_52week = min(recent_prices)
        high_52week = max(recent_prices)

        if high_52week == low_52week:
            return 0.5  # 変動なし

        # 0 = 安値、1 = 高値
        proximity = (current_price - low_52week) / (high_52week - low_52week)
        return proximity

    @staticmethod
    def calculate_moving_average(prices: List[Tuple[datetime, float]], period: int) -> Optional[float]:
        """
        単純移動平均を計算
        戻り値: 移動平均価格
        """
        if len(prices) < period:
            return None

        recent_prices = [p[1] for p in prices[-period:]]
        return sum(recent_prices) / period

    @staticmethod
    def calculate_drawdown_from_ath(prices: List[Tuple[datetime, float]]) -> Optional[float]:
        """
        ATH（史上最高値）からの下落率を計算
        戻り値: 下落率（パーセンテージ、例: 70.5 = ATHから70.5%下落）
        """
        if not prices or len(prices) < 2:
            return None

        current_price = prices[-1][1]
        ath_price = max([p[1] for p in prices])

        if ath_price == 0:
            return None

        drawdown = ((ath_price - current_price) / ath_price) * 100
        return drawdown

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

        # Deep Bottom用指標
        features['rsi_14'] = FeatureCalculator.calculate_rsi(prices, 14)
        features['week52_low_proximity'] = FeatureCalculator.calculate_52week_low_proximity(prices)
        features['ma_200'] = FeatureCalculator.calculate_moving_average(prices, 200)
        features['drawdown_from_ath'] = FeatureCalculator.calculate_drawdown_from_ath(prices)

        return features

    # ============================================
    # Advanced Deep Bottom Indicators
    # ============================================

    @staticmethod
    def calculate_rsi_divergence(prices: List[Tuple[datetime, float]], period: int = 14, lookback: int = 20) -> Optional[dict]:
        """
        RSIダイバージェンスを検出
        価格が新安値をつけているのにRSIが上昇している場合、底打ちの兆候

        戻り値: {
            'bullish_divergence': bool,  # 強気ダイバージェンス（買いシグナル）
            'price_trend': str,          # 'lower_low', 'higher_low', 'flat'
            'rsi_trend': str             # 'lower_low', 'higher_low', 'flat'
        }
        """
        if len(prices) < period + lookback:
            return None

        # 直近のRSIを計算
        rsi_values = []
        for i in range(lookback):
            end_idx = len(prices) - lookback + i + 1
            subset = prices[:end_idx]
            rsi = FeatureCalculator.calculate_rsi(subset, period)
            if rsi is not None:
                rsi_values.append(rsi)

        if len(rsi_values) < 10:
            return None

        # 価格の安値を比較
        recent_prices = [p[1] for p in prices[-lookback:]]
        first_half_low = min(recent_prices[:len(recent_prices)//2])
        second_half_low = min(recent_prices[len(recent_prices)//2:])

        # RSIの安値を比較
        first_half_rsi_low = min(rsi_values[:len(rsi_values)//2])
        second_half_rsi_low = min(rsi_values[len(rsi_values)//2:])

        # トレンド判定
        price_trend = 'flat'
        if second_half_low < first_half_low * 0.98:
            price_trend = 'lower_low'
        elif second_half_low > first_half_low * 1.02:
            price_trend = 'higher_low'

        rsi_trend = 'flat'
        if second_half_rsi_low < first_half_rsi_low - 3:
            rsi_trend = 'lower_low'
        elif second_half_rsi_low > first_half_rsi_low + 3:
            rsi_trend = 'higher_low'

        # 強気ダイバージェンス: 価格が安値更新、RSIは安値切り上げ
        bullish_divergence = (price_trend == 'lower_low' and rsi_trend == 'higher_low')

        return {
            'bullish_divergence': bullish_divergence,
            'price_trend': price_trend,
            'rsi_trend': rsi_trend
        }

    @staticmethod
    def calculate_support_level(prices: List[Tuple[datetime, float]], lookback: int = 60) -> Optional[dict]:
        """
        サポートレベルを検出
        過去の安値で複数回反発しているポイント

        戻り値: {
            'support_price': float,      # サポートレベル価格
            'touches': int,              # サポートに触れた回数
            'distance_pct': float,       # 現在価格からサポートまでの距離(%)
            'at_support': bool           # サポート付近にいるか
        }
        """
        if len(prices) < lookback:
            return None

        recent_prices = [p[1] for p in prices[-lookback:]]
        current_price = recent_prices[-1]

        # 局所的な安値を検出
        local_lows = []
        for i in range(2, len(recent_prices) - 2):
            if (recent_prices[i] < recent_prices[i-1] and
                recent_prices[i] < recent_prices[i-2] and
                recent_prices[i] < recent_prices[i+1] and
                recent_prices[i] < recent_prices[i+2]):
                local_lows.append(recent_prices[i])

        if not local_lows:
            return None

        # クラスタリングでサポートレベルを特定
        local_lows.sort()
        support_price = local_lows[0]  # 最安値をサポートとする

        # サポート付近（±3%以内）に触れた回数をカウント
        tolerance = support_price * 0.03
        touches = sum(1 for low in local_lows if abs(low - support_price) <= tolerance)

        # 現在価格からの距離
        distance_pct = ((current_price - support_price) / support_price) * 100

        # サポート付近にいるか（5%以内）
        at_support = distance_pct <= 5.0

        return {
            'support_price': support_price,
            'touches': touches,
            'distance_pct': distance_pct,
            'at_support': at_support
        }

    @staticmethod
    def calculate_consolidation(prices: List[Tuple[datetime, float]], period: int = 14) -> Optional[dict]:
        """
        コンソリデーション（横ばい/底固め）パターンを検出

        戻り値: {
            'is_consolidating': bool,    # 横ばい中か
            'range_pct': float,          # 値幅(%)
            'days_in_range': int,        # レンジ内の日数
            'breakout_direction': str    # 'none', 'up', 'down'
        }
        """
        if len(prices) < period + 5:
            return None

        recent_prices = [p[1] for p in prices[-period:]]
        current_price = recent_prices[-1]

        high = max(recent_prices)
        low = min(recent_prices)

        if low == 0:
            return None

        range_pct = ((high - low) / low) * 100

        # 狭いレンジ（10%以内）ならコンソリデーション
        is_consolidating = range_pct <= 10.0

        # レンジ内の日数
        days_in_range = 0
        for price in reversed(recent_prices):
            if low <= price <= high:
                days_in_range += 1
            else:
                break

        # ブレイクアウト方向
        breakout_direction = 'none'
        if len(prices) >= period + 3:
            prev_high = max([p[1] for p in prices[-period-3:-3]])
            prev_low = min([p[1] for p in prices[-period-3:-3]])

            if current_price > prev_high:
                breakout_direction = 'up'
            elif current_price < prev_low:
                breakout_direction = 'down'

        return {
            'is_consolidating': is_consolidating,
            'range_pct': range_pct,
            'days_in_range': days_in_range,
            'breakout_direction': breakout_direction
        }

    @staticmethod
    def calculate_higher_lows(prices: List[Tuple[datetime, float]], lookback: int = 30) -> Optional[dict]:
        """
        高値切り上げ/安値切り上げパターンを検出（回復の兆候）

        戻り値: {
            'higher_lows': bool,         # 安値切り上げ
            'higher_highs': bool,        # 高値切り上げ
            'lows_count': int,           # 安値の数
            'trend_strength': float      # トレンド強度 (0-100)
        }
        """
        if len(prices) < lookback:
            return None

        recent_prices = [p[1] for p in prices[-lookback:]]

        # 局所的な安値を検出
        local_lows = []
        local_highs = []

        for i in range(2, len(recent_prices) - 2):
            # 安値
            if (recent_prices[i] <= recent_prices[i-1] and
                recent_prices[i] <= recent_prices[i-2] and
                recent_prices[i] <= recent_prices[i+1] and
                recent_prices[i] <= recent_prices[i+2]):
                local_lows.append((i, recent_prices[i]))

            # 高値
            if (recent_prices[i] >= recent_prices[i-1] and
                recent_prices[i] >= recent_prices[i-2] and
                recent_prices[i] >= recent_prices[i+1] and
                recent_prices[i] >= recent_prices[i+2]):
                local_highs.append((i, recent_prices[i]))

        if len(local_lows) < 2:
            return {
                'higher_lows': False,
                'higher_highs': False,
                'lows_count': len(local_lows),
                'trend_strength': 0
            }

        # 安値切り上げチェック
        higher_lows = all(
            local_lows[i][1] >= local_lows[i-1][1] * 0.98
            for i in range(1, len(local_lows))
        )

        # 高値切り上げチェック
        higher_highs = False
        if len(local_highs) >= 2:
            higher_highs = all(
                local_highs[i][1] >= local_highs[i-1][1] * 0.98
                for i in range(1, len(local_highs))
            )

        # トレンド強度
        trend_strength = 0
        if higher_lows:
            trend_strength += 50
        if higher_highs:
            trend_strength += 50

        return {
            'higher_lows': higher_lows,
            'higher_highs': higher_highs,
            'lows_count': len(local_lows),
            'trend_strength': trend_strength
        }

    @staticmethod
    def calculate_bollinger_position(prices: List[Tuple[datetime, float]], period: int = 20, std_dev: float = 2.0) -> Optional[dict]:
        """
        ボリンジャーバンド位置を計算

        戻り値: {
            'upper_band': float,
            'middle_band': float,
            'lower_band': float,
            'position': float,           # 0=下限, 0.5=中央, 1=上限
            'below_lower': bool,         # 下限を下回っている
            'bandwidth': float           # バンド幅(%)
        }
        """
        if len(prices) < period:
            return None

        recent_prices = [p[1] for p in prices[-period:]]
        current_price = prices[-1][1]

        # 移動平均
        middle_band = sum(recent_prices) / period

        # 標準偏差
        variance = sum((p - middle_band) ** 2 for p in recent_prices) / period
        std = variance ** 0.5

        upper_band = middle_band + (std_dev * std)
        lower_band = middle_band - (std_dev * std)

        # 位置（0-1）
        if upper_band == lower_band:
            position = 0.5
        else:
            position = (current_price - lower_band) / (upper_band - lower_band)
            position = max(0, min(1, position))

        # バンド幅
        bandwidth = ((upper_band - lower_band) / middle_band) * 100

        return {
            'upper_band': upper_band,
            'middle_band': middle_band,
            'lower_band': lower_band,
            'position': position,
            'below_lower': current_price < lower_band,
            'bandwidth': bandwidth
        }

    @staticmethod
    def calculate_stochastic(prices: List[Tuple[datetime, float]], k_period: int = 14, d_period: int = 3) -> Optional[dict]:
        """
        ストキャスティクス（%K, %D）を計算

        戻り値: {
            'k': float,                  # %K (0-100)
            'd': float,                  # %D (0-100)
            'oversold': bool,            # 売られすぎ (K < 20)
            'bullish_cross': bool        # ゴールデンクロス
        }
        """
        if len(prices) < k_period + d_period:
            return None

        # %Kを計算
        k_values = []
        for i in range(d_period):
            end_idx = len(prices) - d_period + i + 1
            subset = prices[end_idx - k_period:end_idx]

            if len(subset) < k_period:
                continue

            prices_only = [p[1] for p in subset]
            highest = max(prices_only)
            lowest = min(prices_only)
            current = prices_only[-1]

            if highest == lowest:
                k = 50
            else:
                k = ((current - lowest) / (highest - lowest)) * 100

            k_values.append(k)

        if len(k_values) < d_period:
            return None

        current_k = k_values[-1]
        current_d = sum(k_values[-d_period:]) / d_period

        # 前回の%D
        prev_d = sum(k_values[-d_period-1:-1]) / d_period if len(k_values) > d_period else current_d

        # ゴールデンクロス
        bullish_cross = k_values[-2] < prev_d and current_k > current_d if len(k_values) >= 2 else False

        return {
            'k': current_k,
            'd': current_d,
            'oversold': current_k < 20,
            'bullish_cross': bullish_cross
        }

    @staticmethod
    def calculate_macd(prices: List[Tuple[datetime, float]], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[dict]:
        """
        MACD（移動平均収束拡散法）を計算

        戻り値: {
            'macd_line': float,
            'signal_line': float,
            'histogram': float,
            'bullish_cross': bool,       # ゴールデンクロス
            'histogram_rising': bool     # ヒストグラム上昇中
        }
        """
        if len(prices) < slow + signal:
            return None

        price_values = [p[1] for p in prices]

        # EMA計算
        def calculate_ema(data, period):
            ema = [sum(data[:period]) / period]
            multiplier = 2 / (period + 1)
            for price in data[period:]:
                ema.append((price - ema[-1]) * multiplier + ema[-1])
            return ema

        fast_ema = calculate_ema(price_values, fast)
        slow_ema = calculate_ema(price_values, slow)

        # MACDライン
        macd_line_values = []
        offset = slow - fast
        for i in range(len(slow_ema)):
            macd_line_values.append(fast_ema[i + offset] - slow_ema[i])

        if len(macd_line_values) < signal:
            return None

        # シグナルライン（MACDのEMA）
        signal_ema = calculate_ema(macd_line_values, signal)

        current_macd = macd_line_values[-1]
        current_signal = signal_ema[-1]
        current_histogram = current_macd - current_signal

        # 前回値
        prev_macd = macd_line_values[-2] if len(macd_line_values) >= 2 else current_macd
        prev_signal = signal_ema[-2] if len(signal_ema) >= 2 else current_signal
        prev_histogram = prev_macd - prev_signal

        # ゴールデンクロス
        bullish_cross = prev_macd < prev_signal and current_macd > current_signal

        # ヒストグラム上昇
        histogram_rising = current_histogram > prev_histogram

        return {
            'macd_line': current_macd,
            'signal_line': current_signal,
            'histogram': current_histogram,
            'bullish_cross': bullish_cross,
            'histogram_rising': histogram_rising
        }

    @staticmethod
    def calculate_volume_analysis(prices_with_volume: List[Tuple[datetime, float, float]]) -> Optional[dict]:
        """
        出来高分析（価格と出来高のデータが必要）

        戻り値: {
            'avg_volume': float,
            'current_volume': float,
            'volume_ratio': float,       # 現在/平均
            'climax_volume': bool,       # 出来高急増（2倍以上）
            'volume_dry_up': bool        # 出来高減少（0.5倍以下）
        }
        """
        if len(prices_with_volume) < 20:
            return None

        volumes = [p[2] for p in prices_with_volume if len(p) > 2]

        if len(volumes) < 20:
            return None

        avg_volume = sum(volumes[-20:]) / 20
        current_volume = volumes[-1]

        if avg_volume == 0:
            return None

        volume_ratio = current_volume / avg_volume

        return {
            'avg_volume': avg_volume,
            'current_volume': current_volume,
            'volume_ratio': volume_ratio,
            'climax_volume': volume_ratio >= 2.0,
            'volume_dry_up': volume_ratio <= 0.5
        }

    @staticmethod
    def calculate_deep_bottom_score(prices: List[Tuple[datetime, float]]) -> Optional[dict]:
        """
        Deep Bottomスコアを総合計算（0-100）

        複数の指標を組み合わせて、底打ちの可能性をスコア化

        戻り値: {
            'total_score': float,        # 総合スコア (0-100)
            'value_score': float,        # 割安度スコア
            'technical_score': float,    # テクニカルスコア
            'momentum_score': float,     # モメンタムスコア
            'risk_score': float,         # リスクスコア（低いほど安全）
            'components': dict           # 各指標の詳細
        }
        """
        if len(prices) < 100:
            return None

        components = {}
        value_score = 0
        technical_score = 0
        momentum_score = 0
        risk_factors = 0

        # 1. ATH下落率スコア (0-30)
        drawdown = FeatureCalculator.calculate_drawdown_from_ath(prices)
        if drawdown is not None:
            components['drawdown'] = drawdown
            if drawdown >= 80:
                value_score += 30
            elif drawdown >= 70:
                value_score += 25
            elif drawdown >= 60:
                value_score += 20
            elif drawdown >= 50:
                value_score += 15
            elif drawdown >= 40:
                value_score += 10

        # 2. 52週安値近接度スコア (0-20)
        proximity = FeatureCalculator.calculate_52week_low_proximity(prices)
        if proximity is not None:
            components['52week_proximity'] = proximity
            if proximity <= 0.05:
                value_score += 20
            elif proximity <= 0.10:
                value_score += 15
            elif proximity <= 0.20:
                value_score += 10
            elif proximity <= 0.30:
                value_score += 5

        # 3. RSIスコア (0-20)
        rsi = FeatureCalculator.calculate_rsi(prices, 14)
        if rsi is not None:
            components['rsi'] = rsi
            if rsi <= 20:
                technical_score += 20
            elif rsi <= 30:
                technical_score += 15
            elif rsi <= 40:
                technical_score += 10
            elif rsi <= 50:
                technical_score += 5

        # 4. ボリンジャーバンド位置スコア (0-10)
        bb = FeatureCalculator.calculate_bollinger_position(prices)
        if bb is not None:
            components['bollinger'] = bb
            if bb['below_lower']:
                technical_score += 10
            elif bb['position'] <= 0.2:
                technical_score += 7
            elif bb['position'] <= 0.3:
                technical_score += 4

        # 5. RSIダイバージェンススコア (0-15)
        divergence = FeatureCalculator.calculate_rsi_divergence(prices)
        if divergence is not None:
            components['divergence'] = divergence
            if divergence['bullish_divergence']:
                momentum_score += 15

        # 6. 安値切り上げスコア (0-10)
        higher_lows = FeatureCalculator.calculate_higher_lows(prices)
        if higher_lows is not None:
            components['higher_lows'] = higher_lows
            if higher_lows['higher_lows']:
                momentum_score += 10
            if higher_lows['higher_highs']:
                momentum_score += 5

        # 7. MACDスコア (0-10)
        macd = FeatureCalculator.calculate_macd(prices)
        if macd is not None:
            components['macd'] = macd
            if macd['bullish_cross']:
                momentum_score += 10
            elif macd['histogram_rising']:
                momentum_score += 5

        # 8. ストキャスティクススコア (0-10)
        stoch = FeatureCalculator.calculate_stochastic(prices)
        if stoch is not None:
            components['stochastic'] = stoch
            if stoch['oversold'] and stoch['bullish_cross']:
                momentum_score += 10
            elif stoch['oversold']:
                momentum_score += 5

        # 9. サポートレベルスコア (0-10)
        support = FeatureCalculator.calculate_support_level(prices)
        if support is not None:
            components['support'] = support
            if support['at_support'] and support['touches'] >= 2:
                technical_score += 10
            elif support['at_support']:
                technical_score += 5

        # リスク要因
        # 急落中（7日リターン < -20%）
        return_7d = FeatureCalculator.calculate_return(prices, 7)
        if return_7d is not None:
            components['return_7d'] = return_7d
            if return_7d < -20:
                risk_factors += 30  # 高リスク
            elif return_7d < -15:
                risk_factors += 20
            elif return_7d < -10:
                risk_factors += 10

        # ボラティリティ過大
        volatility = FeatureCalculator.calculate_volatility(prices)
        if volatility is not None:
            components['volatility'] = volatility
            if volatility > 5:
                risk_factors += 20
            elif volatility > 3:
                risk_factors += 10

        # 総合スコア計算
        raw_score = value_score + technical_score + momentum_score
        risk_score = min(100, risk_factors)

        # リスク調整後スコア
        total_score = max(0, raw_score - (risk_score * 0.3))

        return {
            'total_score': min(100, total_score),
            'value_score': value_score,
            'technical_score': technical_score,
            'momentum_score': momentum_score,
            'risk_score': risk_score,
            'components': components
        }

    # ============================================
    # Deep Bottom Scoring V2 - Enhanced Accuracy
    # ============================================

    @staticmethod
    def calculate_volume_score(prices_with_volume: List[Tuple[datetime, float, float]]) -> dict:
        """
        出来高に基づく底打ちシグナルを計算

        Args:
            prices_with_volume: [(datetime, price, volume), ...]

        Returns:
            {
                'climax_ratio': float,    # 直近最大出来高 / 平均出来高
                'dryup_ratio': float,     # 直近平均出来高 / 20日平均
                'volume_trend': float,    # 出来高トレンド（傾き）
                'climax_score': int,      # 0-8
                'dryup_score': int,       # 0-5
                'trend_score': int,       # 0-2
                'total_score': int        # 0-15
            }
        """
        if not prices_with_volume or len(prices_with_volume) < 25:
            return {
                'climax_ratio': 0, 'dryup_ratio': 1.0, 'volume_trend': 0,
                'climax_score': 0, 'dryup_score': 0, 'trend_score': 0, 'total_score': 0
            }

        volumes = [v for _, _, v in prices_with_volume]

        # Filter out zero volumes
        valid_volumes = [v for v in volumes if v > 0]
        if len(valid_volumes) < 20:
            return {
                'climax_ratio': 0, 'dryup_ratio': 1.0, 'volume_trend': 0,
                'climax_score': 0, 'dryup_score': 0, 'trend_score': 0, 'total_score': 0
            }

        avg_volume = sum(valid_volumes[-20:]) / min(20, len(valid_volumes[-20:]))

        if avg_volume == 0:
            return {
                'climax_ratio': 0, 'dryup_ratio': 1.0, 'volume_trend': 0,
                'climax_score': 0, 'dryup_score': 0, 'trend_score': 0, 'total_score': 0
            }

        # Climax volume detection (capitulation)
        recent_volumes = volumes[-5:]
        max_recent_volume = max(recent_volumes) if recent_volumes else 0
        climax_ratio = max_recent_volume / avg_volume if avg_volume > 0 else 0

        # Volume dryup (exhaustion)
        recent_avg = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
        dryup_ratio = recent_avg / avg_volume if avg_volume > 0 else 1.0

        # Volume trend (decreasing selling pressure)
        if len(recent_volumes) >= 5:
            # Simple linear regression slope
            x_mean = 2  # Mean of [0,1,2,3,4]
            y_mean = sum(recent_volumes) / 5
            numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(recent_volumes))
            denominator = sum((i - x_mean) ** 2 for i in range(5))
            vol_trend = numerator / denominator if denominator != 0 else 0
        else:
            vol_trend = 0

        # Calculate scores
        climax_score = 8 if climax_ratio >= 2.0 else (5 if climax_ratio >= 1.5 else 0)
        dryup_score = 5 if dryup_ratio <= 0.5 else (3 if dryup_ratio <= 0.7 else 0)
        trend_score = 2 if vol_trend < 0 else 0

        return {
            'climax_ratio': round(climax_ratio, 2),
            'dryup_ratio': round(dryup_ratio, 2),
            'volume_trend': round(vol_trend, 2),
            'climax_score': climax_score,
            'dryup_score': dryup_score,
            'trend_score': trend_score,
            'total_score': climax_score + dryup_score + trend_score
        }

    @staticmethod
    def calculate_ma_distance_score(current_price: float, ma200: float) -> dict:
        """
        200日移動平均線からの距離をスコア化

        Args:
            current_price: 現在価格
            ma200: 200日移動平均

        Returns:
            {'ma_distance_pct': float, 'ma_distance_score': int}
        """
        if ma200 is None or ma200 <= 0 or current_price >= ma200:
            return {'ma_distance_pct': 0, 'ma_distance_score': 0}

        distance_pct = (ma200 - current_price) / ma200 * 100

        if distance_pct >= 50:
            score = 10
        elif distance_pct >= 30:
            score = 7
        elif distance_pct >= 20:
            score = 5
        elif distance_pct >= 10:
            score = 3
        else:
            score = 0

        return {'ma_distance_pct': round(distance_pct, 2), 'ma_distance_score': score}

    @staticmethod
    def calculate_exhaustion_days(prices: List[Tuple[datetime, float]], rsi_threshold: float = 30) -> dict:
        """
        売られ過ぎ状態が続いた日数を計算

        Args:
            prices: 価格データ
            rsi_threshold: 売られ過ぎとみなすRSI閾値

        Returns:
            {'exhaustion_days': int, 'exhaustion_score': int}
        """
        if len(prices) < 20:
            return {'exhaustion_days': 0, 'exhaustion_score': 0}

        # Calculate RSI for recent days
        consecutive_oversold = 0

        # Check backward from most recent
        for i in range(min(20, len(prices) - 14)):
            end_idx = len(prices) - i
            if end_idx < 15:
                break
            subset = prices[:end_idx]
            rsi = FeatureCalculator.calculate_rsi(subset, 14)
            if rsi is not None and rsi <= rsi_threshold:
                consecutive_oversold += 1
            else:
                break

        if consecutive_oversold >= 5:
            score = 5
        elif consecutive_oversold >= 3:
            score = 3
        else:
            score = 0

        return {'exhaustion_days': consecutive_oversold, 'exhaustion_score': score}

    @staticmethod
    def calculate_synchronization_bonus(prices: List[Tuple[datetime, float]]) -> dict:
        """
        複数指標の同時シグナルボーナスを計算

        Returns:
            {'sync_bonus': int, 'sync_details': list}
        """
        if len(prices) < 50:
            return {'sync_bonus': 0, 'sync_details': []}

        bonus = 0
        details = []

        # Get indicator values
        rsi = FeatureCalculator.calculate_rsi(prices, 14)
        stoch = FeatureCalculator.calculate_stochastic(prices)
        bb = FeatureCalculator.calculate_bollinger_position(prices)
        divergence = FeatureCalculator.calculate_rsi_divergence(prices)
        macd = FeatureCalculator.calculate_macd(prices)
        higher_lows = FeatureCalculator.calculate_higher_lows(prices)
        support = FeatureCalculator.calculate_support_level(prices)
        consolidation = FeatureCalculator.calculate_consolidation(prices)

        # Triple oversold: RSI + Stochastic + Bollinger
        triple_oversold = (
            (rsi is not None and rsi <= 30) and
            (stoch is not None and stoch.get('k', 100) <= 20) and
            (bb is not None and bb.get('position', 1) <= 0.1)
        )
        if triple_oversold:
            bonus += 5
            details.append('triple_oversold')

        # Divergence confluence: RSI + MACD divergence
        rsi_div = divergence is not None and divergence.get('bullish_divergence', False)
        macd_bullish = macd is not None and (macd.get('bullish_cross', False) or macd.get('histogram_rising', False))
        if rsi_div and macd_bullish:
            bonus += 3
            details.append('divergence_confluence')

        # Pattern alignment: higher lows + support + consolidation
        has_higher_lows = higher_lows is not None and higher_lows.get('higher_lows', False)
        at_support = support is not None and support.get('at_support', False)
        is_consolidating = consolidation is not None and consolidation.get('is_consolidating', False)
        if has_higher_lows and at_support and is_consolidating:
            bonus += 2
            details.append('pattern_alignment')

        return {'sync_bonus': bonus, 'sync_details': details}

    @staticmethod
    def calculate_divergence_strength(prices: List[Tuple[datetime, float]]) -> dict:
        """
        RSIダイバージェンスの強度を計算（単なる有無ではなく強さを評価）

        Returns:
            {'divergence_strength': str, 'divergence_score': int, 'rsi_rise': float, 'price_drop': float}
        """
        if len(prices) < 30:
            return {'divergence_strength': 'none', 'divergence_score': 0, 'rsi_rise': 0, 'price_drop': 0}

        # Get RSI values for recent period
        rsi_values = []
        for i in range(20):
            end_idx = len(prices) - 20 + i + 1
            if end_idx < 15:
                continue
            subset = prices[:end_idx]
            rsi = FeatureCalculator.calculate_rsi(subset, 14)
            if rsi is not None:
                rsi_values.append(rsi)

        if len(rsi_values) < 10:
            return {'divergence_strength': 'none', 'divergence_score': 0, 'rsi_rise': 0, 'price_drop': 0}

        # Find lows in first and second half
        price_values = [p[1] for p in prices[-20:]]
        first_half_prices = price_values[:10]
        second_half_prices = price_values[10:]
        first_half_rsi = rsi_values[:len(rsi_values)//2]
        second_half_rsi = rsi_values[len(rsi_values)//2:]

        price_low1 = min(first_half_prices)
        price_low2 = min(second_half_prices)
        rsi_low1 = min(first_half_rsi) if first_half_rsi else 50
        rsi_low2 = min(second_half_rsi) if second_half_rsi else 50

        # Check for bullish divergence: price makes lower low, RSI makes higher low
        if price_low2 >= price_low1 or rsi_low2 <= rsi_low1:
            return {'divergence_strength': 'none', 'divergence_score': 0, 'rsi_rise': 0, 'price_drop': 0}

        # Calculate strength
        price_drop = (price_low1 - price_low2) / price_low1 * 100 if price_low1 > 0 else 0
        rsi_rise = rsi_low2 - rsi_low1

        if rsi_rise >= 10 and price_drop >= 5:
            strength = 'strong'
            score = 10
        elif rsi_rise >= 5:
            strength = 'moderate'
            score = 6
        else:
            strength = 'weak'
            score = 3

        return {
            'divergence_strength': strength,
            'divergence_score': score,
            'rsi_rise': round(rsi_rise, 2),
            'price_drop': round(price_drop, 2)
        }

    @staticmethod
    def calculate_deep_bottom_score_v2(
        prices: List[Tuple[datetime, float]],
        prices_with_volume: List[Tuple[datetime, float, float]] = None
    ) -> Optional[dict]:
        """
        Deep Bottom V2スコアを計算（出来高確認とシンクボーナス付き）

        新スコアリング（150点満点→100点に正規化）:
        - Value: 50点 (ATH下落25 + 52週近接15 + MA距離10)
        - Technical: 40点 (RSI15 + BB10 + サポート10 + 疲弊日数5)
        - Momentum: 35点 (ダイバージェンス10 + 安値切り上げ10 + MACD8 + ストキャス7)
        - Volume: 15点 (クライマックス8 + ドライアップ5 + トレンド2)
        - Sync: 10点 (トリプル5 + ダイバ合流3 + パターン2)
        - Risk: -30まで

        Returns:
            {
                'total_score': float,
                'signal_strength': str or None,
                'confidence': int,
                'component_scores': dict,
                'risk': dict,
                'volume_confirmed': bool
            }
        """
        if len(prices) < 100:
            return None

        # === VALUE SCORE (50 max) ===
        # ATH Drawdown (0-25)
        drawdown = FeatureCalculator.calculate_drawdown_from_ath(prices)
        if drawdown is not None:
            if drawdown >= 80:
                ath_score = 25
            elif drawdown >= 75:
                ath_score = 22
            elif drawdown >= 70:
                ath_score = 18
            elif drawdown >= 65:
                ath_score = 14
            elif drawdown >= 60:
                ath_score = 10
            else:
                ath_score = 0
        else:
            ath_score = 0
            drawdown = 0

        # 52-Week Proximity (0-15)
        proximity = FeatureCalculator.calculate_52week_low_proximity(prices)
        if proximity is not None:
            if proximity <= 0.05:
                week52_score = 15
            elif proximity <= 0.10:
                week52_score = 12
            elif proximity <= 0.15:
                week52_score = 8
            elif proximity <= 0.20:
                week52_score = 5
            else:
                week52_score = 0
        else:
            week52_score = 0
            proximity = 1.0

        # MA Distance (0-10)
        ma200 = FeatureCalculator.calculate_moving_average(prices, 200)
        current_price = prices[-1][1] if prices else 0
        ma_dist = FeatureCalculator.calculate_ma_distance_score(current_price, ma200)

        value_score = ath_score + week52_score + ma_dist['ma_distance_score']

        # === TECHNICAL SCORE (40 max) ===
        # RSI (0-15)
        rsi = FeatureCalculator.calculate_rsi(prices, 14)
        if rsi is not None:
            if rsi <= 20:
                rsi_score = 15
            elif rsi <= 25:
                rsi_score = 12
            elif rsi <= 30:
                rsi_score = 9
            elif rsi <= 35:
                rsi_score = 5
            else:
                rsi_score = 0
        else:
            rsi_score = 0
            rsi = 50

        # Bollinger (0-10)
        bb = FeatureCalculator.calculate_bollinger_position(prices)
        if bb is not None:
            if bb.get('below_lower', False):
                bb_score = 10
            elif bb.get('position', 1) <= 0.15:
                bb_score = 7
            elif bb.get('position', 1) <= 0.25:
                bb_score = 4
            else:
                bb_score = 0
        else:
            bb_score = 0

        # Support Level (0-10)
        support = FeatureCalculator.calculate_support_level(prices)
        if support is not None:
            touches = support.get('touches', 0)
            if support.get('at_support', False) and touches >= 3:
                support_score = 10
            elif support.get('at_support', False) and touches >= 2:
                support_score = 7
            elif support.get('at_support', False):
                support_score = 4
            else:
                support_score = 0
        else:
            support_score = 0

        # Exhaustion Days (0-5)
        exhaustion = FeatureCalculator.calculate_exhaustion_days(prices)

        technical_score = rsi_score + bb_score + support_score + exhaustion['exhaustion_score']

        # === MOMENTUM SCORE (35 max) ===
        # Divergence Strength (0-10)
        divergence = FeatureCalculator.calculate_divergence_strength(prices)

        # Higher Lows (0-10)
        higher_lows = FeatureCalculator.calculate_higher_lows(prices)
        if higher_lows is not None:
            hl_count = higher_lows.get('count', 0)
            if hl_count >= 3:
                hl_score = 10
            elif hl_count >= 2:
                hl_score = 7
            elif higher_lows.get('higher_lows', False):
                hl_score = 4
            else:
                hl_score = 0
        else:
            hl_score = 0

        # MACD (0-8)
        macd = FeatureCalculator.calculate_macd(prices)
        if macd is not None:
            if macd.get('bullish_cross', False) and macd.get('histogram_rising', False):
                macd_score = 8
            elif macd.get('bullish_cross', False):
                macd_score = 5
            elif macd.get('histogram_rising', False):
                macd_score = 3
            else:
                macd_score = 0
        else:
            macd_score = 0

        # Stochastic (0-7)
        stoch = FeatureCalculator.calculate_stochastic(prices)
        if stoch is not None:
            if stoch.get('oversold', False) and stoch.get('bullish_cross', False):
                stoch_score = 7
            elif stoch.get('oversold', False):
                stoch_score = 4
            else:
                stoch_score = 0
        else:
            stoch_score = 0

        momentum_score = divergence['divergence_score'] + hl_score + macd_score + stoch_score

        # === VOLUME SCORE (15 max) ===
        if prices_with_volume:
            volume_data = FeatureCalculator.calculate_volume_score(prices_with_volume)
            volume_score = volume_data['total_score']
        else:
            volume_data = {'climax_score': 0, 'dryup_score': 0, 'trend_score': 0, 'total_score': 0}
            volume_score = 0

        # === SYNCHRONIZATION BONUS (10 max) ===
        sync = FeatureCalculator.calculate_synchronization_bonus(prices)
        sync_score = sync['sync_bonus']

        # === RISK DEDUCTIONS ===
        risk_deduction = 0
        risk_factors = []

        # Active crash (7-day return < -25%)
        return_7d = FeatureCalculator.calculate_return(prices, 7)
        if return_7d is not None and return_7d < -25:
            risk_deduction += 20
            risk_factors.append('active_crash')

        # High volatility
        volatility = FeatureCalculator.calculate_volatility(prices)
        if volatility is not None and volatility > 6:
            risk_deduction += 10
            risk_factors.append('high_volatility')

        # No volume confirmation (if volume data was provided)
        if prices_with_volume and volume_score == 0:
            risk_deduction += 5
            risk_factors.append('no_volume_confirmation')

        # === FINAL CALCULATION ===
        raw_score = value_score + technical_score + momentum_score + volume_score + sync_score
        risk_adjusted = raw_score - risk_deduction
        final_score = min(100, max(0, risk_adjusted * 100 / 150))

        # === SIGNAL STRENGTH ===
        if final_score >= 75:
            signal_strength = 'strong'
        elif final_score >= 55:
            signal_strength = 'moderate'
        elif final_score >= 40:
            signal_strength = 'weak'
        else:
            signal_strength = None

        # === CONFIDENCE ===
        indicators_triggered = sum([
            ath_score >= 18,
            week52_score >= 12,
            rsi_score >= 9,
            support_score >= 7,
            divergence['divergence_score'] >= 6,
            volume_score >= 8
        ])
        confidence = min(95, 50 + (indicators_triggered * 8))

        return {
            'total_score': round(final_score, 1),
            'signal_strength': signal_strength,
            'confidence': confidence,
            'component_scores': {
                'value': {
                    'score': value_score,
                    'max': 50,
                    'details': {
                        'ath_drawdown': {'value': drawdown, 'score': ath_score},
                        'week52_proximity': {'value': proximity, 'score': week52_score},
                        'ma_distance': ma_dist
                    }
                },
                'technical': {
                    'score': technical_score,
                    'max': 40,
                    'details': {
                        'rsi': {'value': rsi, 'score': rsi_score},
                        'bollinger': {'score': bb_score},
                        'support': {'score': support_score},
                        'exhaustion': exhaustion
                    }
                },
                'momentum': {
                    'score': momentum_score,
                    'max': 35,
                    'details': {
                        'divergence': divergence,
                        'higher_lows': {'score': hl_score},
                        'macd': {'score': macd_score},
                        'stochastic': {'score': stoch_score}
                    }
                },
                'volume': {
                    'score': volume_score,
                    'max': 15,
                    'details': volume_data
                },
                'sync_bonus': {
                    'score': sync_score,
                    'max': 10,
                    'details': sync
                }
            },
            'risk': {
                'deduction': risk_deduction,
                'factors': risk_factors
            },
            'raw_score': raw_score,
            'volume_confirmed': volume_score >= 8
        }
