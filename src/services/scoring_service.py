"""
スコアリングサービス
VMSとScoreV2を統合
"""
from typing import Dict, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scoring import VMSScorer, ScoreV2
from optimization.weight_optimizer import MarketRegime, WeightOptimizer


class ScoringService:
    """スコアリングサービス"""
    
    def calculate_vms_score(
        self,
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
        VMSスコアを計算
        
        Args:
            features: 特徴量辞書
            current_state: 現在の状態
            pe_ratio: PER
            quality_score: 質スコア
            fundamental_data: 財務データ
            events: イベントリスト
            analyst_data: アナリストデータ
            market_volatility: 市場ボラティリティ
            use_dynamic_weights: 動的重み調整を使用するか
        
        Returns:
            VMSスコア辞書
        """
        return VMSScorer.calculate_all_scores(
            features,
            current_state,
            pe_ratio,
            quality_score,
            fundamental_data,
            events,
            analyst_data,
            market_volatility,
            use_dynamic_weights
        )
    
    def calculate_score_v2(
        self,
        return_30d: Optional[float] = None,
        return_7d: Optional[float] = None,
        volatility: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        data_layers_used: Optional[Dict[str, bool]] = None,
        current_state: Optional[str] = None,
        market_regime: Optional[MarketRegime] = None,
        market_volatility: Optional[float] = None
    ) -> Dict:
        """
        ScoreV2を計算
        
        Args:
            return_30d: 30日リターン（%）
            return_7d: 7日リターン（%）
            volatility: ボラティリティ（%）
            max_drawdown: 最大ドローダウン（%、負の値）
            data_layers_used: 使用されたデータレイヤー
            current_state: 現在の状態
            market_regime: 市場レジーム
            market_volatility: 市場全体のボラティリティ（%）
        
        Returns:
            ScoreV2辞書
        """
        return ScoreV2.calculate_all_scores(
            return_30d,
            return_7d,
            volatility,
            max_drawdown,
            data_layers_used,
            current_state,
            market_regime,
            market_volatility
        )
    
    def calculate_both_scores(
        self,
        features: Dict,
        current_state: str,
        pe_ratio: Optional[float] = None,
        quality_score: int = 3,
        fundamental_data: Optional[Dict] = None,
        events: Optional[List[Dict]] = None,
        analyst_data: Optional[Dict] = None,
        market_volatility: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        use_dynamic_weights: bool = True
    ) -> Dict:
        """
        VMSとScoreV2の両方を計算
        
        Args:
            features: 特徴量辞書
            current_state: 現在の状態
            pe_ratio: PER
            quality_score: 質スコア
            fundamental_data: 財務データ
            events: イベントリスト
            analyst_data: アナリストデータ
            market_volatility: 市場ボラティリティ
            max_drawdown: 最大ドローダウン
            use_dynamic_weights: 動的重み調整を使用するか
        
        Returns:
            両方のスコアを含む辞書
        """
        # VMSスコア
        vms_scores = self.calculate_vms_score(
            features,
            current_state,
            pe_ratio,
            quality_score,
            fundamental_data,
            events,
            analyst_data,
            market_volatility,
            use_dynamic_weights
        )
        
        # ScoreV2
        # データレイヤーを判定
        data_layers_used = {
            'L0': True,  # 価格データは常に使用
            'L1': fundamental_data is not None,
            'L3': events is not None and len(events) > 0
        }
        
        # 市場レジームを判定
        market_regime = WeightOptimizer.determine_market_regime(
            features.get('volatility'),
            market_volatility
        )
        
        score_v2 = self.calculate_score_v2(
            return_30d=features.get('return_30d'),
            return_7d=features.get('return_7d'),
            volatility=features.get('volatility'),
            max_drawdown=max_drawdown,
            data_layers_used=data_layers_used,
            current_state=current_state,
            market_regime=market_regime,
            market_volatility=market_volatility
        )
        
        return {
            'vms': vms_scores,
            'v2': score_v2,
            'score_type': 'both'
        }
