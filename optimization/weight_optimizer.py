"""
重み最適化モジュール
市場状況・セクターに応じた動的重み調整
"""
from typing import Dict, Optional
from enum import Enum


class MarketRegime(Enum):
    """市場レジーム"""
    HIGH_VOLATILITY = "high_volatility"  # 高ボラティリティ市場
    LOW_VOLATILITY = "low_volatility"  # 低ボラティリティ市場
    NORMAL = "normal"  # 通常市場


class SectorType(Enum):
    """セクタータイプ"""
    GROWTH = "growth"  # 成長株
    VALUE = "value"  # バリュー株
    BLEND = "blend"  # 混合


class WeightOptimizer:
    """重み最適化クラス"""
    
    # デフォルト重み
    DEFAULT_WEIGHTS = {
        'value': 0.4,
        'momentum': 0.35,
        'stability': 0.25
    }
    
    @staticmethod
    def determine_market_regime(volatility: Optional[float], market_volatility: Optional[float] = None) -> MarketRegime:
        """
        市場レジームを判定
        
        Args:
            volatility: 個別資産のボラティリティ
            market_volatility: 市場全体のボラティリティ（オプション）
        
        Returns:
            市場レジーム
        """
        # 市場全体のボラティリティが利用可能な場合
        if market_volatility is not None:
            if market_volatility > 5.0:
                return MarketRegime.HIGH_VOLATILITY
            elif market_volatility < 2.0:
                return MarketRegime.LOW_VOLATILITY
            else:
                return MarketRegime.NORMAL
        
        # 個別資産のボラティリティから推定
        if volatility is not None:
            if volatility > 6.0:
                return MarketRegime.HIGH_VOLATILITY
            elif volatility < 2.5:
                return MarketRegime.LOW_VOLATILITY
            else:
                return MarketRegime.NORMAL
        
        return MarketRegime.NORMAL
    
    @staticmethod
    def determine_sector_type(pe_ratio: Optional[float], revenue_growth: Optional[float] = None) -> SectorType:
        """
        セクタータイプを判定
        
        Args:
            pe_ratio: PER
            revenue_growth: 売上成長率（オプション）
        
        Returns:
            セクタータイプ
        """
        # 売上成長率が利用可能な場合
        if revenue_growth is not None:
            if revenue_growth > 0.15:  # 15%以上の成長
                return SectorType.GROWTH
            elif revenue_growth < 0.05:  # 5%未満の成長
                return SectorType.VALUE
            else:
                return SectorType.BLEND
        
        # PERから推定
        if pe_ratio is not None:
            if pe_ratio > 30:  # 高PER = 成長株
                return SectorType.GROWTH
            elif pe_ratio < 15:  # 低PER = バリュー株
                return SectorType.VALUE
            else:
                return SectorType.BLEND
        
        return SectorType.BLEND
    
    @staticmethod
    def optimize_weights(
        market_regime: MarketRegime,
        sector_type: SectorType,
        base_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        市場状況・セクターに応じて重みを最適化
        
        Args:
            market_regime: 市場レジーム
            sector_type: セクタータイプ
            base_weights: ベース重み（デフォルト: DEFAULT_WEIGHTS）
        
        Returns:
            最適化された重みの辞書
        """
        if base_weights is None:
            base_weights = WeightOptimizer.DEFAULT_WEIGHTS.copy()
        
        weights = base_weights.copy()
        
        # 市場レジームに応じた調整
        if market_regime == MarketRegime.HIGH_VOLATILITY:
            # 高ボラティリティ市場: Stability重みを増加
            weights['stability'] = min(0.4, weights['stability'] + 0.1)
            weights['momentum'] = max(0.25, weights['momentum'] - 0.05)
            weights['value'] = max(0.3, weights['value'] - 0.05)
        elif market_regime == MarketRegime.LOW_VOLATILITY:
            # 低ボラティリティ市場: Momentum重みを増加
            weights['momentum'] = min(0.45, weights['momentum'] + 0.1)
            weights['stability'] = max(0.15, weights['stability'] - 0.05)
            weights['value'] = max(0.3, weights['value'] - 0.05)
        
        # セクタータイプに応じた調整
        if sector_type == SectorType.GROWTH:
            # 成長株: Momentum重みを増加
            weights['momentum'] = min(0.45, weights['momentum'] + 0.1)
            weights['value'] = max(0.3, weights['value'] - 0.05)
            weights['stability'] = max(0.15, weights['stability'] - 0.05)
        elif sector_type == SectorType.VALUE:
            # バリュー株: Value重みを増加
            weights['value'] = min(0.5, weights['value'] + 0.1)
            weights['momentum'] = max(0.25, weights['momentum'] - 0.05)
            weights['stability'] = max(0.15, weights['stability'] - 0.05)
        
        # 重みの正規化（合計が1.0になるように）
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        
        return weights
    
    @staticmethod
    def get_optimized_weights(
        volatility: Optional[float] = None,
        market_volatility: Optional[float] = None,
        pe_ratio: Optional[float] = None,
        revenue_growth: Optional[float] = None,
        base_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        重みを最適化（簡易版）
        
        Args:
            volatility: 個別資産のボラティリティ
            market_volatility: 市場全体のボラティリティ
            pe_ratio: PER
            revenue_growth: 売上成長率
            base_weights: ベース重み
        
        Returns:
            最適化された重みの辞書
        """
        market_regime = WeightOptimizer.determine_market_regime(volatility, market_volatility)
        sector_type = WeightOptimizer.determine_sector_type(pe_ratio, revenue_growth)
        
        return WeightOptimizer.optimize_weights(market_regime, sector_type, base_weights)
