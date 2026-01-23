"""
投資スコア2.0: Return/Risk/Confidence/Regimeを統合
0-100点の統合スコアを算出
"""
from typing import Optional, Dict, List
from enum import Enum
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimization.weight_optimizer import MarketRegime, WeightOptimizer


class ScoreV2:
    """投資スコア2.0: Return/Risk/Confidence/Regime統合スコア"""
    
    # デフォルト値（欠損時）
    DEFAULT_RETURN_SCORE = 30.0  # 中立的な値
    DEFAULT_RISK_SCORE = 15.0    # 中立的な値
    DEFAULT_CONFIDENCE_SCORE = 10.0  # L0のみ想定
    DEFAULT_REGIME_SCORE = 5.0   # 通常時想定
    
    @staticmethod
    def calculate_return_score(
        return_30d: Optional[float] = None,
        return_7d: Optional[float] = None
    ) -> float:
        """
        Returnスコア（0-40点）を計算
        
        Args:
            return_30d: 30日リターン（%）
            return_7d: 7日リターン（%）
        
        Returns:
            Returnスコア（0-40点）
        """
        if return_30d is None:
            return ScoreV2.DEFAULT_RETURN_SCORE
        
        # 30日リターンから基本スコアを計算
        base_score = 0.0
        if return_30d <= -30.0:
            base_score = 0.0
        elif return_30d <= -20.0:
            base_score = 5.0
        elif return_30d <= -10.0:
            base_score = 20.0
        elif return_30d <= 0.0:
            base_score = 30.0
        elif return_30d <= 10.0:
            base_score = 35.0
        elif return_30d <= 30.0:
            base_score = 40.0
        else:
            base_score = 40.0
        
        # 7日リターンがプラスの場合はボーナス（最大+5点）
        bonus = 0.0
        if return_7d is not None and return_7d > 0:
            # 7日リターンがプラスなら+5点ボーナス
            bonus = 5.0
        
        # 正規化: 0-40点の範囲に収める
        total_score = base_score + bonus
        return min(40.0, max(0.0, total_score))
    
    @staticmethod
    def calculate_risk_score(
        volatility: Optional[float] = None,
        max_drawdown: Optional[float] = None
    ) -> float:
        """
        Riskスコア（0-25点）を計算（低リスクほど高スコア）
        
        Args:
            volatility: ボラティリティ（%）
            max_drawdown: 最大ドローダウン（%、負の値）
        
        Returns:
            Riskスコア（0-25点）
        """
        volatility_score = 0.0
        if volatility is None:
            # 欠損時は中立的な値
            volatility_score = 12.5
        else:
            # ボラティリティが低いほど高スコア
            if volatility < 2.0:
                volatility_score = 25.0
            elif volatility < 3.0:
                volatility_score = 20.0
            elif volatility < 5.0:
                volatility_score = 15.0
            elif volatility < 8.0:
                volatility_score = 5.0
            else:
                volatility_score = 0.0
        
        # 最大ドローダウンの評価（最大+5点）
        dd_score = 0.0
        if max_drawdown is not None:
            # max_drawdownは負の値なので、絶対値で評価
            abs_dd = abs(max_drawdown)
            if abs_dd <= 5.0:
                dd_score = 5.0
            elif abs_dd <= 10.0:
                dd_score = 3.0
            elif abs_dd <= 20.0:
                dd_score = 1.0
            else:
                dd_score = 0.0
        
        # 正規化: 0-25点の範囲に収める（volatility_score + dd_scoreの合計が25を超えないように）
        total_score = min(25.0, volatility_score + dd_score)
        return max(0.0, total_score)
    
    @staticmethod
    def calculate_confidence_score(
        data_layers_used: Optional[Dict[str, bool]] = None,
        current_state: Optional[str] = None
    ) -> float:
        """
        Confidenceスコア（0-20点）を計算
        
        Args:
            data_layers_used: 使用されたデータレイヤー {'L0': True, 'L1': True, 'L3': True}
            current_state: 現在の状態（'BUY', 'BASE', 'WATCH', 'NORMAL'）
        
        Returns:
            Confidenceスコア（0-20点）
        """
        # データ品質スコア
        data_quality_score = 0.0
        if data_layers_used is None:
            # 欠損時はL0のみ想定
            data_quality_score = 5.0
        else:
            l0 = data_layers_used.get('L0', False)
            l1 = data_layers_used.get('L1', False)
            l3 = data_layers_used.get('L3', False)
            
            if l0 and l1 and l3:
                data_quality_score = 20.0  # L0+L1+L3
            elif l0 and l1:
                data_quality_score = 12.0  # L0+L1
            elif l0:
                data_quality_score = 5.0  # L0のみ
            else:
                data_quality_score = 0.0
        
        # 状態によるボーナス（最大+5点）
        state_score = 0.0
        if current_state == 'BUY':
            state_score = 5.0
        elif current_state == 'BASE':
            state_score = 3.0
        elif current_state == 'WATCH':
            state_score = 1.0
        else:
            state_score = 0.0
        
        # 正規化: 0-20点の範囲に収める
        total_score = min(20.0, data_quality_score + state_score)
        return max(0.0, total_score)
    
    @staticmethod
    def calculate_regime_score(
        market_regime: Optional[MarketRegime] = None,
        volatility: Optional[float] = None,
        market_volatility: Optional[float] = None
    ) -> float:
        """
        Regimeスコア（0-15点）を計算
        
        Args:
            market_regime: 市場レジーム（既に判定済みの場合）
            volatility: 個別資産のボラティリティ（%）
            market_volatility: 市場全体のボラティリティ（%）
        
        Returns:
            Regimeスコア（0-15点）
        """
        # 市場レジームを判定（未指定の場合は自動判定）
        if market_regime is None:
            market_regime = WeightOptimizer.determine_market_regime(
                volatility, market_volatility
            )
        
        # レジームに応じたスコア
        if market_regime == MarketRegime.HIGH_VOLATILITY:
            # 高ボラ時: Stability重視（+10点）
            return 10.0
        elif market_regime == MarketRegime.LOW_VOLATILITY:
            # 低ボラ時: Momentum重視（+10点）
            return 10.0
        else:
            # 通常時: バランス（+5点）
            return 5.0
    
    @staticmethod
    def calculate_total_score(
        return_score: float,
        risk_score: float,
        confidence_score: float,
        regime_score: float
    ) -> float:
        """
        総合スコア（0-100点）を計算
        
        Args:
            return_score: Returnスコア（0-40点）
            risk_score: Riskスコア（0-25点）
            confidence_score: Confidenceスコア（0-20点）
            regime_score: Regimeスコア（0-15点）
        
        Returns:
            総合スコア（0-100点）
        """
        total = return_score + risk_score + confidence_score + regime_score
        return min(100.0, max(0.0, total))
    
    @staticmethod
    def calculate_all_scores(
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
        全スコアを一度に計算
        
        Args:
            return_30d: 30日リターン（%）
            return_7d: 7日リターン（%）
            volatility: ボラティリティ（%）
            max_drawdown: 最大ドローダウン（%、負の値）
            data_layers_used: 使用されたデータレイヤー
            current_state: 現在の状態
            market_regime: 市場レジーム（既に判定済みの場合）
            market_volatility: 市場全体のボラティリティ（%）
        
        Returns:
            スコアの辞書
        """
        # 各スコアを計算
        return_score = ScoreV2.calculate_return_score(return_30d, return_7d)
        risk_score = ScoreV2.calculate_risk_score(volatility, max_drawdown)
        confidence_score = ScoreV2.calculate_confidence_score(
            data_layers_used, current_state
        )
        regime_score = ScoreV2.calculate_regime_score(
            market_regime, volatility, market_volatility
        )
        
        # 総合スコア
        total_score = ScoreV2.calculate_total_score(
            return_score, risk_score, confidence_score, regime_score
        )
        
        return {
            'return_score': return_score,
            'risk_score': risk_score,
            'confidence_score': confidence_score,
            'regime_score': regime_score,
            'total_score': total_score,
            'score_breakdown': {
                'return': return_score,
                'risk': risk_score,
                'confidence': confidence_score,
                'regime': regime_score
            }
        }
