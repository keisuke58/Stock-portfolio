"""
理由説明生成サービス
SignalExplainerをラップ
"""
from typing import Dict, List, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from signals import SignalExplainer
from optimization.weight_optimizer import MarketRegime


class ExplanationService:
    """理由説明生成サービス"""
    
    def __init__(self):
        """初期化"""
        self.explainer = SignalExplainer()
    
    def explain_signal(
        self,
        symbol: str,
        state: str,
        features: Dict,
        scores: Dict,
        old_state: Optional[str] = None,
        data_layers_used: Optional[Dict[str, bool]] = None,
        market_regime: Optional[str] = None,
        score_type: str = 'vms'
    ) -> List[str]:
        """
        シグナルの理由を箇条書きで返す
        
        Args:
            symbol: シンボル名
            state: 現在の状態
            features: 特徴量辞書
            scores: スコア辞書
            old_state: 以前の状態
            data_layers_used: 使用されたデータレイヤー
            market_regime: 市場レジーム
            score_type: スコアタイプ（'vms' または 'v2'）
        
        Returns:
            説明のリスト
        """
        return self.explainer.explain_signal(
            symbol,
            state,
            features,
            scores,
            old_state,
            data_layers_used,
            market_regime,
            score_type
        )
    
    def explain_state_change(
        self,
        symbol: str,
        old_state: Optional[str],
        new_state: str,
        features: Dict
    ) -> List[str]:
        """
        状態変化の理由を説明
        
        Args:
            symbol: シンボル名
            old_state: 以前の状態
            new_state: 新しい状態
            features: 特徴量辞書
        
        Returns:
            説明のリスト
        """
        return self.explainer.explain_state_change(
            symbol,
            old_state,
            new_state,
            features
        )
    
    def explain_features(self, features: Dict) -> List[str]:
        """
        特徴量の要約を説明
        
        Args:
            features: 特徴量辞書
        
        Returns:
            説明のリスト
        """
        return self.explainer.explain_features(features)
    
    def explain_data_quality(
        self,
        data_layers_used: Optional[Dict[str, bool]] = None
    ) -> str:
        """
        データ品質を説明
        
        Args:
            data_layers_used: 使用されたデータレイヤー
        
        Returns:
            データ品質の説明
        """
        return self.explainer.explain_data_quality(data_layers_used)
    
    def explain_regime(
        self,
        market_regime: Optional[str] = None,
        volatility: Optional[float] = None
    ) -> str:
        """
        市場レジームを説明
        
        Args:
            market_regime: 市場レジーム
            volatility: ボラティリティ（%）
        
        Returns:
            レジームの説明
        """
        return self.explainer.explain_regime(market_regime, volatility)
