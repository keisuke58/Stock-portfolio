"""
VMSスコア計算: Value/Momentum/Stability を分解
L1-L4データを考慮した拡張版
"""
from typing import Optional, Dict, List
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features import FeatureCalculator
from optimization import WeightOptimizer


class VMSScorer:
    """Value/Momentum/Stabilityスコアを計算するクラス"""
    
    @staticmethod
    def calculate_value_score(
        ath_ratio: Optional[float],
        pe_ratio: Optional[float] = None,
        fundamental_data: Optional[Dict] = None
    ) -> float:
        """
        Valueスコア（割安度）を計算（0-100点）
        ATH比、PER、FCF、売上成長、利益率を考慮（L1データ拡張）
        """
        score = 0.0
        max_score = 100.0
        
        # ATH比による評価（低いほど割安で高スコア）- 40点満点
        if ath_ratio is not None:
            if ath_ratio < 0.5:
                score += 40  # 大幅割安
            elif ath_ratio < 0.7:
                score += 32  # 割安
            elif ath_ratio < 0.85:
                score += 24  # やや割安
            elif ath_ratio < 0.95:
                score += 16  # ほぼ適正
            else:
                score += 8  # 高値圏
        
        # PERによる評価（米国株の場合）- 30点満点
        if pe_ratio is not None:
            if pe_ratio < 10:
                score += 30  # 割安PER
            elif 10 <= pe_ratio <= 25:
                score += 20  # 適正PER
            elif 25 < pe_ratio <= 50:
                score += 10  # やや高PER
            else:
                score += 0  # 高PER
        
        # L1データ拡張: FCF、売上成長、利益率 - 30点満点
        if fundamental_data:
            # FCFが正の場合は追加ポイント（10点）
            fcf = fundamental_data.get('fcf')
            if fcf is not None and fcf > 0:
                score += 10
            
            # 売上成長率（10点）
            revenue_growth = fundamental_data.get('revenue_growth')
            if revenue_growth is not None:
                if revenue_growth > 0.2:  # 20%以上
                    score += 10
                elif revenue_growth > 0.1:  # 10%以上
                    score += 7
                elif revenue_growth > 0:  # プラス成長
                    score += 4
            
            # 利益率（10点）
            profit_margin = fundamental_data.get('profit_margin')
            if profit_margin is not None:
                if profit_margin > 0.2:  # 20%以上
                    score += 10
                elif profit_margin > 0.1:  # 10%以上
                    score += 7
                elif profit_margin > 0.05:  # 5%以上
                    score += 4
        
        return min(max_score, score)
    
    @staticmethod
    def calculate_momentum_score(
        current_state: str,
        return_30d: Optional[float],
        breakout_5d: bool,
        return_7d: Optional[float] = None,
        events: Optional[List[Dict]] = None,
        analyst_data: Optional[Dict] = None
    ) -> float:
        """
        Momentumスコア（反転の確からしさ）を計算（0-100点）
        5日高値ブレイク、出来高増加、30日リターン、ニュースイベント、アナリスト改定を考慮（L3-L4データ拡張）
        """
        score = 0.0
        max_score = 100.0
        
        # 状態による評価 - 50点満点
        if current_state == 'BUY':
            score += 50  # 反転確認
        elif current_state == 'BASE':
            score += 30  # 低迷・横ばい
        elif current_state == 'WATCH':
            score += 10  # 急落直後（まだ買わない）
        
        # 5日高値ブレイクチェック - 30点満点
        if breakout_5d:
            score += 30  # 反転シグナル強
        
        # 30日リターンチェック（極端でないことを確認）- 20点満点
        if return_30d is not None:
            if -30 <= return_30d <= 10:  # 適度な下落または上昇
                score += 20
            elif return_30d < -30:  # 行き過ぎ下落
                score += 5  # まだ危険
            elif return_30d > 30:  # 行き過ぎ上昇
                score += 5  # 買い遅れ
        
        # 7日リターンがプラスの場合は追加ポイント
        if return_7d is not None and return_7d > 0:
            score += 10
        
        # L3データ拡張: ニュースイベント - 追加ポイント（最大20点）
        if events:
            positive_events = [e for e in events if e.get('event_type') == 'positive']
            negative_events = [e for e in events if e.get('event_type') == 'negative']
            
            # 好材料イベント
            if positive_events:
                high_impact = [e for e in positive_events if e.get('impact') == 'high']
                if high_impact:
                    score += 20
                elif positive_events:
                    score += 10
            
            # 悪材料イベント（減点）
            if negative_events:
                high_impact = [e for e in negative_events if e.get('impact') == 'high']
                if high_impact:
                    score -= 20
                elif negative_events:
                    score -= 10
        
        # L1データ拡張: アナリスト改定・EPS推移 - 追加ポイント（最大10点）
        if analyst_data:
            # 目標株価が現在価格より高い場合
            target_price = analyst_data.get('target_price')
            if target_price:
                # 現在価格は呼び出し側で渡す必要があるが、ここでは簡易的に
                # 推奨が"buy"の場合は追加ポイント
                recommendation = analyst_data.get('recommendation', '').lower()
                if recommendation in ['buy', 'strong buy']:
                    score += 10
                elif recommendation == 'hold':
                    score += 5
            
            # EPS成長率がプラスの場合
            eps_growth = analyst_data.get('eps_growth')
            if eps_growth is not None and eps_growth > 0:
                score += 5
        
        return max(0.0, min(max_score, score))
    
    @staticmethod
    def calculate_stability_score(
        volatility: Optional[float],
        quality_score: int = 3,
        fundamental_data: Optional[Dict] = None
    ) -> float:
        """
        Stabilityスコア（事業・ボラ耐性）を計算（0-100点）
        ボラティリティ、質スコア、財務健全性を考慮（L1データ拡張）
        """
        score = 0.0
        max_score = 100.0
        
        # 質スコアによる評価 - 50点満点
        if quality_score >= 5:
            score += 50  # 最高品質
        elif quality_score >= 4:
            score += 40  # 高品質
        elif quality_score >= 3:
            score += 30  # 標準品質
        elif quality_score >= 2:
            score += 20  # やや低品質
        else:
            score += 10  # 低品質
        
        # ボラティリティによる評価（低いほど安定）- 30点満点
        if volatility is not None:
            if volatility < 2:
                score += 30  # 非常に安定
            elif volatility < 3:
                score += 25  # 安定
            elif volatility < 5:
                score += 15  # やや不安定
            elif volatility < 8:
                score += 5  # 不安定
            else:
                score += 0  # 非常に不安定
        
        # L1データ拡張: 財務健全性スコア - 20点満点
        if fundamental_data:
            financial_health_score = fundamental_data.get('financial_health_score')
            if financial_health_score is not None:
                # 0-100点を0-20点にスケール
                score += (financial_health_score / 100.0) * 20
        
        return min(max_score, score)
    
    @staticmethod
    def calculate_total_score(
        value_score: float,
        momentum_score: float,
        stability_score: float,
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """
        総合スコアを計算
        デフォルトの重み: Value 40%, Momentum 35%, Stability 25%
        """
        if weights is None:
            weights = {'value': 0.4, 'momentum': 0.35, 'stability': 0.25}
        
        total = (
            weights['value'] * value_score +
            weights['momentum'] * momentum_score +
            weights['stability'] * stability_score
        )
        
        return total
    
    @staticmethod
    def calculate_all_scores(
        features: Dict,
        current_state: str,
        pe_ratio: Optional[float] = None,
        quality_score: int = 3,
        fundamental_data: Optional[Dict] = None,
        events: Optional[List[Dict]] = None,
        analyst_data: Optional[Dict] = None,
        market_volatility: Optional[float] = None,
        use_dynamic_weights: bool = True
    ) -> Dict:
        """
        全スコアを一度に計算（L1-L3データ統合版、動的重み調整対応）
        
        Args:
            features: 価格指標（L0）
            current_state: 現在の状態
            pe_ratio: PER
            quality_score: 質スコア
            fundamental_data: 財務データ（L1）
            events: イベントリスト（L3）
            analyst_data: アナリストデータ（L1）
            market_volatility: 市場全体のボラティリティ（オプション）
            use_dynamic_weights: 動的重み調整を使用するか（デフォルト: True）
        
        戻り値: スコアの辞書
        """
        # Valueスコア（L1データ統合）
        value_score = VMSScorer.calculate_value_score(
            features.get('ath_ratio'),
            pe_ratio,
            fundamental_data
        )
        
        # Momentumスコア（L3イベント・L1アナリストデータを考慮）
        momentum_score = VMSScorer.calculate_momentum_score(
            current_state,
            features.get('return_30d'),
            features.get('breakout_5d', False),
            features.get('return_7d'),
            events,
            analyst_data
        )
        
        # Stabilityスコア（L1データ統合）
        stability_score = VMSScorer.calculate_stability_score(
            features.get('volatility'),
            quality_score,
            fundamental_data
        )
        
        # 動的重み調整
        weights = None
        if use_dynamic_weights:
            revenue_growth = fundamental_data.get('revenue_growth') if fundamental_data else None
            weights = WeightOptimizer.get_optimized_weights(
                volatility=features.get('volatility'),
                market_volatility=market_volatility,
                pe_ratio=pe_ratio,
                revenue_growth=revenue_growth
            )
        
        # 総合スコア（動的重みを使用）
        total_score = VMSScorer.calculate_total_score(
            value_score,
            momentum_score,
            stability_score,
            weights
        )
        
        return {
            'value_score': value_score,
            'momentum_score': momentum_score,
            'stability_score': stability_score,
            'total_score': total_score,
            'weights_used': weights if weights else WeightOptimizer.DEFAULT_WEIGHTS,
            'score_breakdown': {
                'value': value_score,
                'momentum': momentum_score,
                'stability': stability_score
            },
            'data_layers_used': {
                'L0': True,  # 価格データ
                'L1': fundamental_data is not None,  # 財務データ
                'L3': events is not None and len(events) > 0  # イベント
            }
        }
    
    @staticmethod
    def _adjust_momentum_from_events(events: List[Dict]) -> float:
        """
        イベントからMomentumスコアを調整
        
        Args:
            events: イベントリスト
        
        Returns:
            調整値（-20 〜 +20）
        """
        adjustment = 0.0
        
        for event in events:
            event_type = event.get('event_type')
            impact = event.get('impact', 'low')
            
            # 影響度の重み
            impact_weight = {
                'high': 1.0,
                'medium': 0.5,
                'low': 0.2
            }.get(impact, 0.2)
            
            # イベントタイプによる調整
            if event_type == 'positive':
                adjustment += 5 * impact_weight  # 好材料
            elif event_type == 'negative':
                adjustment -= 5 * impact_weight  # 悪材料
        
        # 調整値を制限（-20 〜 +20）
        return max(-20.0, min(20.0, adjustment))
