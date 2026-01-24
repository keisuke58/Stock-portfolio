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

    def check_deep_bottom_advanced(self, symbol: str) -> Tuple[bool, Optional[Dict]]:
        """
        高度なDEEP_BOTTOM分析（スコアリングシステム）

        複数の指標を組み合わせてスコア化し、より精度の高い底打ち検出を行う

        戻り値: (検出されたか, 詳細メトリクス辞書)
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

        # 基本メトリクス
        drawdown = FeatureCalculator.calculate_drawdown_from_ath(prices)
        week52_proximity = FeatureCalculator.calculate_52week_low_proximity(prices)
        rsi = FeatureCalculator.calculate_rsi(prices, 14)
        ma_200 = FeatureCalculator.calculate_moving_average(prices, DEEP_BOTTOM_THRESHOLDS.MA_PERIOD)
        return_7d = FeatureCalculator.calculate_return(prices, 7)
        return_30d = FeatureCalculator.calculate_return(prices, 30)

        # 高度な分析
        deep_score = FeatureCalculator.calculate_deep_bottom_score(prices)
        divergence = FeatureCalculator.calculate_rsi_divergence(prices)
        support = FeatureCalculator.calculate_support_level(prices)
        consolidation = FeatureCalculator.calculate_consolidation(prices)
        higher_lows = FeatureCalculator.calculate_higher_lows(prices)
        bollinger = FeatureCalculator.calculate_bollinger_position(prices)
        stochastic = FeatureCalculator.calculate_stochastic(prices)
        macd = FeatureCalculator.calculate_macd(prices)

        # メトリクス辞書
        metrics = {
            'current_price': current_price,
            'ath_price': max([p[1] for p in prices]),
            'drawdown_pct': drawdown,
            'week52_low_proximity': week52_proximity,
            'rsi_14': rsi,
            'ma_200': ma_200,
            'return_7d': return_7d,
            'return_30d': return_30d,
            # スコアリング
            'deep_score': deep_score,
            # 高度な指標
            'divergence': divergence,
            'support': support,
            'consolidation': consolidation,
            'higher_lows': higher_lows,
            'bollinger': bollinger,
            'stochastic': stochastic,
            'macd': macd
        }

        # 基本条件チェック
        basic_conditions = {
            'ath_drawdown': drawdown is not None and drawdown >= DEEP_BOTTOM_THRESHOLDS.ATH_DRAWDOWN_MIN,
            'near_52week_low': week52_proximity is not None and week52_proximity <= DEEP_BOTTOM_THRESHOLDS.WEEK52_LOW_PROXIMITY_MAX,
            'rsi_oversold': rsi is not None and rsi <= DEEP_BOTTOM_THRESHOLDS.RSI_OVERSOLD,
            'below_ma200': ma_200 is not None and current_price < ma_200,
            'not_crashing': return_7d is not None and return_7d > DEEP_BOTTOM_THRESHOLDS.MIN_7D_RETURN
        }

        # 高度な条件チェック
        advanced_conditions = {
            'bullish_divergence': divergence is not None and divergence.get('bullish_divergence', False),
            'at_support': support is not None and support.get('at_support', False),
            'consolidating': consolidation is not None and consolidation.get('is_consolidating', False),
            'higher_lows_forming': higher_lows is not None and higher_lows.get('higher_lows', False),
            'below_bollinger': bollinger is not None and bollinger.get('below_lower', False),
            'stoch_oversold': stochastic is not None and stochastic.get('oversold', False),
            'macd_bullish': macd is not None and (macd.get('bullish_cross', False) or macd.get('histogram_rising', False))
        }

        metrics['basic_conditions'] = basic_conditions
        metrics['advanced_conditions'] = advanced_conditions

        # シグナル判定
        basic_score = sum(1 for v in basic_conditions.values() if v)
        advanced_score = sum(1 for v in advanced_conditions.values() if v)

        # 判定ロジック:
        # 1. 全ての基本条件を満たす（厳格モード）
        # 2. 4/5以上の基本条件 + 3以上の高度条件（バランスモード）
        # 3. スコアが70以上（スコアモード）

        strict_signal = all(basic_conditions.values())
        balanced_signal = basic_score >= 4 and advanced_score >= 3
        score_signal = deep_score is not None and deep_score.get('total_score', 0) >= 70

        # シグナル強度
        signal_strength = 'none'
        if strict_signal:
            signal_strength = 'strong'
        elif balanced_signal or score_signal:
            signal_strength = 'moderate'
        elif basic_score >= 3:
            signal_strength = 'weak'

        metrics['signal_strength'] = signal_strength
        metrics['basic_score'] = f"{basic_score}/5"
        metrics['advanced_score'] = f"{advanced_score}/7"

        # 検出判定（strong または moderate）
        detected = signal_strength in ['strong', 'moderate']

        return (detected, metrics)

    def get_bottom_recommendation(self, symbol: str) -> Optional[Dict]:
        """
        底打ち投資の推奨を生成

        戻り値: {
            'symbol': str,
            'recommendation': str,       # 'strong_buy', 'buy', 'watch', 'avoid'
            'confidence': float,         # 信頼度 (0-100)
            'reasons': list,             # 推奨理由
            'risks': list,               # リスク要因
            'entry_zone': dict,          # エントリーゾーン
            'metrics': dict              # 詳細メトリクス
        }
        """
        detected, metrics = self.check_deep_bottom_advanced(symbol)

        if metrics is None:
            return None

        reasons = []
        risks = []

        # 推奨理由を収集
        if metrics.get('basic_conditions', {}).get('ath_drawdown'):
            reasons.append(f"ATHから{metrics.get('drawdown_pct', 0):.1f}%下落（歴史的割安）")

        if metrics.get('basic_conditions', {}).get('rsi_oversold'):
            reasons.append(f"RSI {metrics.get('rsi_14', 0):.1f}（売られすぎ）")

        if metrics.get('advanced_conditions', {}).get('bullish_divergence'):
            reasons.append("強気ダイバージェンス検出（底打ちサイン）")

        if metrics.get('advanced_conditions', {}).get('higher_lows_forming'):
            reasons.append("安値切り上げパターン形成中")

        if metrics.get('advanced_conditions', {}).get('at_support'):
            support = metrics.get('support', {})
            reasons.append(f"サポートレベル（{support.get('touches', 0)}回反発）に接近")

        if metrics.get('advanced_conditions', {}).get('macd_bullish'):
            reasons.append("MACDが反転の兆候")

        # リスク要因を収集
        return_7d = metrics.get('return_7d', 0)
        if return_7d is not None and return_7d < -15:
            risks.append(f"直近7日で{return_7d:.1f}%下落（急落中の可能性）")

        volatility = metrics.get('deep_score', {}).get('components', {}).get('volatility', 0)
        if volatility and volatility > 4:
            risks.append(f"高ボラティリティ（{volatility:.1f}%）")

        if not metrics.get('advanced_conditions', {}).get('consolidating'):
            risks.append("コンソリデーション未形成（底固めが不十分）")

        if not metrics.get('advanced_conditions', {}).get('at_support'):
            risks.append("明確なサポートレベルが確認できない")

        # 推奨判定
        signal_strength = metrics.get('signal_strength', 'none')
        deep_score = metrics.get('deep_score', {}).get('total_score', 0)

        if signal_strength == 'strong' and deep_score >= 70:
            recommendation = 'strong_buy'
            confidence = min(95, deep_score + 10)
        elif signal_strength in ['strong', 'moderate'] and deep_score >= 50:
            recommendation = 'buy'
            confidence = min(80, deep_score)
        elif signal_strength == 'moderate' or deep_score >= 40:
            recommendation = 'watch'
            confidence = min(60, deep_score)
        else:
            recommendation = 'avoid'
            confidence = max(20, 100 - deep_score if deep_score else 50)

        # エントリーゾーン
        current_price = metrics.get('current_price', 0)
        support_price = metrics.get('support', {}).get('support_price', current_price * 0.95)

        entry_zone = {
            'ideal_entry': support_price,
            'max_entry': current_price * 1.05,
            'stop_loss': support_price * 0.90,
            'target_1': current_price * 1.20,
            'target_2': current_price * 1.50
        }

        return {
            'symbol': symbol,
            'recommendation': recommendation,
            'confidence': confidence,
            'reasons': reasons,
            'risks': risks,
            'entry_zone': entry_zone,
            'metrics': metrics
        }


# グローバル関数（後方互換性のため）
def determine_state(symbol: str, current_state: Optional[str] = None) -> str:
    """グローバル関数: 状態を判定"""
    state_machine = StateMachine()
    return state_machine.determine_state(symbol, current_state)
