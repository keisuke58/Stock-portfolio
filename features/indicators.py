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
