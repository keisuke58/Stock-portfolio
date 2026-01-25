"""
状態機械: WATCH/BASE/BUY/DEEP_BOTTOM 判定
急落→低迷→反転の状態遷移を管理
長期投資向けのDEEP_BOTTOM検出も対応
"""
from typing import Optional, List, Tuple, Dict
from datetime import datetime
import logging
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features import FeatureCalculator
from features.pattern_detector import PatternDetector, PatternType
from fetchers import YahooFetcher, CoinGeckoFetcher
from core.constants import DEEP_BOTTOM_THRESHOLDS, PATTERN_DETECTION_CONFIG, TEN_BAGGER_CONFIG
from scoring.fundamental_scorer import FundamentalScorer, FundamentalHealth


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

    def check_deep_bottom_advanced(self, symbol: str, include_fundamentals: bool = True) -> Tuple[bool, Optional[Dict]]:
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

        # ファンダメンタル分析（株式のみ）
        if include_fundamentals and not is_crypto_symbol(symbol):
            try:
                fundamental_scorer = FundamentalScorer()
                fundamental_result = fundamental_scorer.calculate_score(symbol)

                if fundamental_result:
                    metrics['fundamental_score'] = fundamental_result.total_score
                    metrics['fundamental_health'] = fundamental_result.health_status.value
                    metrics['fundamental_warnings'] = fundamental_result.warnings
                    metrics['fundamental_details'] = {
                        'pe_score': fundamental_result.pe_score,
                        'pb_score': fundamental_result.pb_score,
                        'fcf_score': fundamental_result.fcf_score,
                        'debt_score': fundamental_result.debt_score,
                        'growth_score': fundamental_result.growth_score,
                    }

                    # 総合スコア調整: テクニカル(75) + ファンダメンタル(25) = 100
                    if deep_score:
                        original_score = deep_score.get('total_score', 0)
                        # テクニカルスコアを75点満点にスケール
                        technical_adjusted = (original_score / 100) * 75
                        # ファンダメンタルスコアを加算
                        adjusted_total = technical_adjusted + fundamental_result.total_score
                        metrics['adjusted_total_score'] = adjusted_total

                        # ファンダメンタルが弱い場合はシグナル強度を下げる
                        if fundamental_result.health_status == FundamentalHealth.VALUE_TRAP:
                            if signal_strength == 'strong':
                                signal_strength = 'moderate'
                            elif signal_strength == 'moderate':
                                signal_strength = 'weak'
                            metrics['signal_strength'] = signal_strength
                            metrics['fundamental_adjustment'] = 'downgraded due to value trap risk'
            except Exception as e:
                # ファンダメンタル取得失敗は無視（テクニカルのみで判定）
                pass

        # 検出判定（strong または moderate）
        detected = signal_strength in ['strong', 'moderate']

        return (detected, metrics)

    def check_deep_bottom_advanced_v2(
        self,
        symbol: str,
        include_volume: bool = True,
        include_fundamentals: bool = True
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Deep Bottom検出（V2: 出来高確認とシンクボーナス付き）

        改善点:
        - 出来高クライマックス/ドライアップ検出 (+15点)
        - 複数指標同時シグナルボーナス (+10点)
        - MA距離のグラデーションスコア (+10点)
        - 疲弊日数スコア (+5点)
        - ダイバージェンス強度評価

        Args:
            symbol: 銘柄シンボル
            include_volume: 出来高データを含むか
            include_fundamentals: ファンダメンタルスコアを含むか

        Returns:
            (detected: bool, metrics: dict)
        """
        # データ取得
        is_crypto = is_crypto_symbol(symbol)

        if is_crypto:
            if include_volume:
                prices_with_volume = self.coingecko_fetcher.get_historical_prices_with_volume(symbol, days=365)
                if prices_with_volume:
                    prices = [(dt, p) for dt, p, _ in prices_with_volume]
                else:
                    prices = self.coingecko_fetcher.get_historical_prices(symbol, days=365)
                    prices_with_volume = None
            else:
                prices = self.coingecko_fetcher.get_historical_prices(symbol, days=365)
                prices_with_volume = None
        else:
            if include_volume:
                prices_with_volume = self.yahoo_fetcher.get_historical_prices_with_volume(symbol, days=365)
                if prices_with_volume:
                    prices = [(dt, p) for dt, p, _ in prices_with_volume]
                else:
                    prices = self.yahoo_fetcher.get_historical_prices(symbol, days=365)
                    prices_with_volume = None
            else:
                prices = self.yahoo_fetcher.get_historical_prices(symbol, days=365)
                prices_with_volume = None

        if not prices or len(prices) < 100:
            return (False, None)

        # V2スコア計算
        score_result = FeatureCalculator.calculate_deep_bottom_score_v2(prices, prices_with_volume)

        if score_result is None:
            return (False, None)

        current_price = prices[-1][1] if prices else 0

        metrics = {
            'symbol': symbol,
            'current_price': current_price,
            'scoring_version': 'v2',

            # V2スコア結果
            'total_score': score_result['total_score'],
            'signal_strength': score_result['signal_strength'],
            'confidence': score_result['confidence'],
            'volume_confirmed': score_result['volume_confirmed'],

            # コンポーネント別スコア
            'value_score': score_result['component_scores']['value'],
            'technical_score': score_result['component_scores']['technical'],
            'momentum_score': score_result['component_scores']['momentum'],
            'volume_score': score_result['component_scores']['volume'],
            'sync_bonus': score_result['component_scores']['sync_bonus'],

            # リスク
            'risk_deduction': score_result['risk']['deduction'],
            'risk_factors': score_result['risk']['factors'],
            'raw_score': score_result['raw_score'],

            'timestamp': datetime.now().isoformat()
        }

        signal_strength = score_result['signal_strength']

        # ファンダメンタルスコア統合（株式のみ）
        if include_fundamentals and not is_crypto:
            try:
                fundamental_scorer = FundamentalScorer()
                fundamental_result = fundamental_scorer.calculate_score(symbol)

                if fundamental_result:
                    metrics['fundamental_score'] = fundamental_result.total_score
                    metrics['fundamental_health'] = fundamental_result.health_status.value
                    metrics['fundamental_warnings'] = fundamental_result.warnings
                    metrics['fundamental_details'] = {
                        'pe_score': fundamental_result.pe_score,
                        'pb_score': fundamental_result.pb_score,
                        'fcf_score': fundamental_result.fcf_score,
                        'debt_score': fundamental_result.debt_score,
                        'growth_score': fundamental_result.growth_score,
                    }

                    # 調整後総合スコア: V2テクニカル(75) + ファンダメンタル(25) = 100
                    technical_adjusted = score_result['total_score'] * 0.75
                    metrics['adjusted_total_score'] = technical_adjusted + fundamental_result.total_score

                    # VALUE_TRAPの場合はシグナル強度を下げる
                    if fundamental_result.health_status == FundamentalHealth.VALUE_TRAP:
                        if signal_strength == 'strong':
                            signal_strength = 'moderate'
                        elif signal_strength == 'moderate':
                            signal_strength = 'weak'
                        metrics['signal_strength'] = signal_strength
                        metrics['fundamental_adjustment'] = 'downgraded due to value trap risk'
            except Exception:
                pass

        detected = signal_strength in ['strong', 'moderate']

        return (detected, metrics)

    def check_pattern_confirmation(
        self,
        symbol: str,
        signal_type: str = 'bullish',
        lookback: int = 60
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Check for pattern confirmation of trading signals.

        Args:
            symbol: Stock or crypto symbol
            signal_type: 'bullish' or 'bearish'
            lookback: Days to analyze for patterns

        Returns:
            (has_confirmation: bool, pattern_details: dict)
        """
        # Fetch price data
        if is_crypto_symbol(symbol):
            prices = self.coingecko_fetcher.get_historical_prices(symbol, days=lookback)
        else:
            prices = self.yahoo_fetcher.get_historical_prices(symbol, days=lookback)

        if not prices or len(prices) < 20:
            return (False, None)

        # Initialize pattern detector with config
        config = {
            'gap_min_pct': PATTERN_DETECTION_CONFIG.GAP_MIN_PCT,
            'double_top_tolerance_pct': PATTERN_DETECTION_CONFIG.DOUBLE_TOP_TOLERANCE_PCT,
            'wedge_min_touches': PATTERN_DETECTION_CONFIG.WEDGE_MIN_TOUCHES,
            'trendline_break_threshold_pct': PATTERN_DETECTION_CONFIG.TRENDLINE_BREAK_THRESHOLD_PCT,
            'min_pattern_confidence': PATTERN_DETECTION_CONFIG.MIN_PATTERN_CONFIDENCE
        }
        detector = PatternDetector(config)

        # Detect patterns
        all_patterns = detector.detect_all_patterns(prices, lookback=lookback)

        if not all_patterns:
            return (False, {'patterns': [], 'confirmation': False})

        # Filter by signal type
        if signal_type == 'bullish':
            relevant_patterns = detector.get_bullish_patterns(all_patterns)
        else:
            relevant_patterns = detector.get_bearish_patterns(all_patterns)

        # Check for strong confirmation
        high_confidence_patterns = [
            p for p in relevant_patterns
            if p.confidence >= PATTERN_DETECTION_CONFIG.MIN_PATTERN_CONFIDENCE
        ]

        has_confirmation = len(high_confidence_patterns) > 0

        # Build details
        pattern_details = {
            'patterns': [p.to_dict() for p in relevant_patterns],
            'high_confidence_patterns': [p.to_dict() for p in high_confidence_patterns],
            'confirmation': has_confirmation,
            'pattern_count': len(relevant_patterns),
            'high_confidence_count': len(high_confidence_patterns)
        }

        # Add strongest pattern info
        if high_confidence_patterns:
            strongest = max(high_confidence_patterns, key=lambda p: p.confidence)
            pattern_details['strongest_pattern'] = {
                'type': strongest.pattern_type.value,
                'confidence': strongest.confidence,
                'target': strongest.target_price,
                'invalidation': strongest.invalidation_price
            }

        return (has_confirmation, pattern_details)

    def check_deep_bottom_with_patterns(
        self,
        symbol: str,
        include_volume: bool = True,
        include_fundamentals: bool = True,
        require_pattern: bool = False
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Enhanced Deep Bottom detection with pattern confirmation.

        Combines V2 scoring with pattern detection for higher confidence signals.

        Args:
            symbol: Stock or crypto symbol
            include_volume: Include volume analysis
            include_fundamentals: Include fundamental scoring (stocks only)
            require_pattern: If True, requires pattern confirmation for detection

        Returns:
            (detected: bool, metrics: dict)
        """
        # Get V2 deep bottom analysis
        detected, metrics = self.check_deep_bottom_advanced_v2(
            symbol, include_volume, include_fundamentals
        )

        if metrics is None:
            return (False, None)

        # Check for bullish patterns
        pattern_confirmed, pattern_details = self.check_pattern_confirmation(
            symbol, signal_type='bullish', lookback=60
        )

        # Add pattern info to metrics
        metrics['pattern_analysis'] = pattern_details
        metrics['pattern_confirmed'] = pattern_confirmed

        # Adjust signal based on pattern confirmation
        signal_strength = metrics.get('signal_strength')

        if pattern_confirmed:
            # Upgrade signal strength if patterns confirm
            if signal_strength == 'weak':
                metrics['signal_strength'] = 'moderate'
                metrics['pattern_upgrade'] = True
            elif signal_strength == 'moderate':
                metrics['confidence'] = min(95, metrics.get('confidence', 50) + 10)
                metrics['pattern_bonus'] = True

            # Add pattern-based target prices
            if pattern_details and pattern_details.get('strongest_pattern'):
                strongest = pattern_details['strongest_pattern']
                if strongest.get('target'):
                    metrics['pattern_target'] = strongest['target']
                if strongest.get('invalidation'):
                    metrics['pattern_invalidation'] = strongest['invalidation']

        elif require_pattern:
            # If pattern required but not found, downgrade signal
            if signal_strength in ['strong', 'moderate']:
                metrics['signal_strength'] = 'weak'
                metrics['pattern_required_missing'] = True
                detected = False

        # Update detection based on new signal strength
        if not require_pattern:
            detected = metrics.get('signal_strength') in ['strong', 'moderate']

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


    def check_ten_bagger_potential(self, symbol: str) -> Optional[Dict]:
        """
        Check if a stock meets ten bagger criteria.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dict with signal info if criteria met, None otherwise
        """
        # Skip crypto assets
        if is_crypto_symbol(symbol):
            return None

        try:
            from screeners.ten_bagger_screener import TenBaggerScreener

            screener = TenBaggerScreener(yahoo_fetcher=self.yahoo_fetcher)
            score = screener.score_stock(symbol)

            if score is None:
                return None

            if score.total_score >= TEN_BAGGER_CONFIG.SCORE_GOOD:
                return {
                    'signal': 'TEN_BAGGER_CANDIDATE',
                    'symbol': symbol,
                    'score': score.total_score,
                    'rating': score.rating,
                    'growth_score': score.growth_score,
                    'profitability_score': score.profitability_score,
                    'valuation_score': score.valuation_score,
                    'market_position_score': score.market_position_score,
                    'strengths': score.key_strengths,
                    'risks': score.key_risks,
                    'sector': score.sector,
                    'metrics': score.metrics,
                    'timestamp': datetime.now().isoformat()
                }

            return None

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Error checking ten bagger potential for {symbol}: {e}")
            return None


# グローバル関数（後方互換性のため）
def determine_state(symbol: str, current_state: Optional[str] = None) -> str:
    """グローバル関数: 状態を判定"""
    state_machine = StateMachine()
    return state_machine.determine_state(symbol, current_state)
