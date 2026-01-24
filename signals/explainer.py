"""
シグナル理由説明生成モジュール
signals/の出力から、人間が理解できる説明テキストを生成
"""
from typing import Dict, List, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SignalExplainer:
    """シグナルの理由を説明するクラス"""
    
    # 閾値定義
    WATCH_THRESHOLD = -12.0  # 3日リターン ≤ -12%でWATCH
    BASE_THRESHOLD = 5.0     # 7日レンジ ≤ 5%でBASE
    
    @staticmethod
    def explain_state_change(
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
        explanations = []
        
        if old_state == new_state:
            # 状態変化なし
            return explanations
        
        return_3d = features.get('return_3d')
        return_7d = features.get('return_7d')
        range_7d = features.get('range_7d')
        breakout_5d = features.get('breakout_5d', False)
        current_price = features.get('current_price')
        high_5d = features.get('high_5d')
        
        # WATCH状態への変化
        if new_state == 'WATCH':
            if return_3d is not None:
                explanations.append(
                    f"3日リターン {return_3d:.1f}%（閾値: {SignalExplainer.WATCH_THRESHOLD:.1f}%）"
                )
        
        # BASE状態への変化
        if new_state == 'BASE':
            if range_7d is not None:
                explanations.append(
                    f"7日レンジ {range_7d:.1f}%（閾値: {SignalExplainer.BASE_THRESHOLD:.1f}%）"
                )
        
        # BUY状態への変化
        if new_state == 'BUY':
            if breakout_5d:
                if current_price is not None and high_5d is not None:
                    explanations.append(
                        f"5日高値ブレイク: ${high_5d:.2f} → ${current_price:.2f}"
                    )
                else:
                    explanations.append("5日高値を上抜け")
        
        return explanations
    
    @staticmethod
    def explain_score_breakdown(
        scores: Dict,
        score_type: str = 'vms'
    ) -> List[str]:
        """
        スコアの根拠を説明
        
        Args:
            scores: スコア辞書
            score_type: スコアタイプ（'vms' または 'v2'）
        
        Returns:
            説明のリスト
        """
        explanations = []
        
        if score_type == 'v2':
            # ScoreV2の場合
            return_score = scores.get('return_score')
            risk_score = scores.get('risk_score')
            confidence_score = scores.get('confidence_score')
            regime_score = scores.get('regime_score')
            
            if return_score is not None:
                explanations.append(f"Returnスコア: {return_score:.1f}/40点")
            if risk_score is not None:
                explanations.append(f"Riskスコア: {risk_score:.1f}/25点")
            if confidence_score is not None:
                explanations.append(f"Confidenceスコア: {confidence_score:.1f}/20点")
            if regime_score is not None:
                explanations.append(f"Regimeスコア: {regime_score:.1f}/15点")
        else:
            # VMSスコアの場合
            value_score = scores.get('value_score')
            momentum_score = scores.get('momentum_score')
            stability_score = scores.get('stability_score')
            
            if value_score is not None:
                explanations.append(f"Valueスコア: {value_score:.1f}/100点")
            if momentum_score is not None:
                explanations.append(f"Momentumスコア: {momentum_score:.1f}/100点")
            if stability_score is not None:
                explanations.append(f"Stabilityスコア: {stability_score:.1f}/100点")
        
        return explanations
    
    @staticmethod
    def explain_features(
        features: Dict
    ) -> List[str]:
        """
        特徴量の要約を説明
        
        Args:
            features: 特徴量辞書
        
        Returns:
            説明のリスト
        """
        explanations = []
        
        # ATH比
        ath_ratio = features.get('ath_ratio')
        if ath_ratio is not None:
            drop_pct = (1 - ath_ratio) * 100
            explanations.append(f"ATH比: {ath_ratio:.2f}（ATHから{drop_pct:.1f}%下落）")
        
        # 出来高増加（volume_ratioがあれば）
        volume_ratio = features.get('volume_ratio')
        if volume_ratio is not None:
            explanations.append(f"出来高増: 過去7日平均の{volume_ratio:.0f}%")
        
        # ブレイク
        breakout_5d = features.get('breakout_5d', False)
        if breakout_5d:
            explanations.append("ブレイク: 5日高値を上抜け")
        
        # ボラティリティ
        volatility = features.get('volatility')
        if volatility is not None:
            if volatility < 2.0:
                explanations.append(f"ボラ低下: 30日ボラティリティ {volatility:.1f}%（低リスク）")
            elif volatility < 5.0:
                explanations.append(f"ボラ適正: 30日ボラティリティ {volatility:.1f}%")
            else:
                explanations.append(f"ボラ上昇: 30日ボラティリティ {volatility:.1f}%（高リスク）")
        
        # リターン
        return_30d = features.get('return_30d')
        if return_30d is not None:
            if return_30d > 0:
                explanations.append(f"30日リターン: +{return_30d:.1f}%")
            else:
                explanations.append(f"30日リターン: {return_30d:.1f}%")
        
        return_7d = features.get('return_7d')
        if return_7d is not None:
            if return_7d > 0:
                explanations.append(f"7日リターン: +{return_7d:.1f}%")
            else:
                explanations.append(f"7日リターン: {return_7d:.1f}%")
        
        return explanations
    
    @staticmethod
    def explain_data_quality(
        data_layers_used: Optional[Dict[str, bool]] = None
    ) -> str:
        """
        データ品質を説明
        
        Args:
            data_layers_used: 使用されたデータレイヤー
        
        Returns:
            データ品質の説明
        """
        if data_layers_used is None:
            return "データ品質: L0のみ（基本データ）"
        
        layers = []
        if data_layers_used.get('L0', False):
            layers.append("L0:価格")
        if data_layers_used.get('L1', False):
            layers.append("L1:財務")
        if data_layers_used.get('L3', False):
            layers.append("L3:イベント")
        
        if not layers:
            return "データ品質: データなし"
        
        quality_desc = "高信頼度" if len(layers) >= 3 else "中信頼度" if len(layers) >= 2 else "低信頼度"
        return f"データ品質: {'+'.join(layers)}（{quality_desc}）"
    
    @staticmethod
    def explain_regime(
        market_regime: Optional[str] = None,
        volatility: Optional[float] = None
    ) -> str:
        """
        市場レジームを説明
        
        Args:
            market_regime: 市場レジーム（'HIGH_VOLATILITY', 'LOW_VOLATILITY', 'NORMAL'）
            volatility: ボラティリティ（%）
        
        Returns:
            レジームの説明
        """
        if market_regime is None:
            if volatility is not None:
                if volatility > 6.0:
                    market_regime = "HIGH_VOLATILITY"
                elif volatility < 2.5:
                    market_regime = "LOW_VOLATILITY"
                else:
                    market_regime = "NORMAL"
            else:
                market_regime = "NORMAL"
        
        regime_names = {
            'HIGH_VOLATILITY': '高ボラ（Stability重視）',
            'LOW_VOLATILITY': '低ボラ（Momentum重視）',
            'NORMAL': '通常（バランス）'
        }
        
        return f"市場レジーム: {regime_names.get(market_regime, market_regime)}"
    
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
            old_state: 以前の状態（オプション）
            data_layers_used: 使用されたデータレイヤー（オプション）
            market_regime: 市場レジーム（オプション）
            score_type: スコアタイプ（'vms' または 'v2'）
        
        Returns:
            説明のリスト
        
        例:
        [
            "出来高増: 過去7日平均の150%",
            "ブレイク: 5日高値を上抜け",
            "ボラ低下: 30日ボラティリティ 2.1%"
        ]
        """
        explanations = []
        
        # 状態変化の理由
        if old_state is not None and old_state != state:
            state_explanations = self.explain_state_change(symbol, old_state, state, features)
            explanations.extend(state_explanations)
        
        # 特徴量の要約
        feature_explanations = self.explain_features(features)
        explanations.extend(feature_explanations)
        
        # スコアの根拠
        score_explanations = self.explain_score_breakdown(scores, score_type)
        explanations.extend(score_explanations)
        
        # データ品質
        if data_layers_used is not None:
            data_quality = self.explain_data_quality(data_layers_used)
            explanations.append(data_quality)
        
        # 市場レジーム
        volatility = features.get('volatility')
        regime_explanation = self.explain_regime(market_regime, volatility)
        explanations.append(regime_explanation)
        
        return explanations
