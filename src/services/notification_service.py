"""
通知サービス
notifiersを統合
"""
from typing import Dict, List, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from notifiers import DiscordNotifier, NotificationThrottler


class NotificationService:
    """通知サービス"""
    
    def __init__(
        self,
        discord_webhook_url: Optional[str] = None,
        cooldown_hours: int = 24
    ):
        """
        初期化
        
        Args:
            discord_webhook_url: Discord Webhook URL
            cooldown_hours: クールダウン時間（時間）
        """
        self.discord_notifier = None
        if discord_webhook_url:
            self.discord_notifier = DiscordNotifier(
                discord_webhook_url,
                cooldown_hours=cooldown_hours
            )
    
    def notify_state_change(
        self,
        symbol: str,
        old_state: str,
        new_state: str,
        price: float
    ) -> bool:
        """
        状態変化を通知
        
        Args:
            symbol: シンボル名
            old_state: 以前の状態
            new_state: 新しい状態
            price: 価格
        
        Returns:
            True=成功、False=失敗
        """
        if not self.discord_notifier:
            return False
        
        return self.discord_notifier.notify_state_change(
            symbol,
            old_state,
            new_state,
            price
        )
    
    def notify_daily_pick(self, daily_pick: dict) -> bool:
        """
        Daily pickを通知
        
        Args:
            daily_pick: Daily pick辞書
        
        Returns:
            True=成功、False=失敗
        """
        if not self.discord_notifier:
            return False
        
        return self.discord_notifier.notify_daily_pick(daily_pick)
    
    def notify_score_threshold(
        self,
        symbol: str,
        score: float,
        threshold: float,
        direction: str = 'above'
    ) -> bool:
        """
        スコア閾値通知
        
        Args:
            symbol: シンボル名
            score: 現在のスコア
            threshold: 閾値
            direction: 'above'（上回った）または 'below'（下回った）
        
        Returns:
            True=成功、False=失敗
        """
        if not self.discord_notifier:
            return False
        
        return self.discord_notifier.notify_score_threshold(
            symbol,
            score,
            threshold,
            direction
        )
    
    def notify_anomaly(
        self,
        symbol: str,
        anomaly_type: str,
        details: Dict
    ) -> bool:
        """
        異常検知通知
        
        Args:
            symbol: シンボル名
            anomaly_type: 異常タイプ
            details: 詳細情報
        
        Returns:
            True=成功、False=失敗
        """
        if not self.discord_notifier:
            return False
        
        return self.discord_notifier.notify_anomaly(
            symbol,
            anomaly_type,
            details
        )
    
    def notify_regime_change(
        self,
        old_regime: str,
        new_regime: str,
        affected_symbols: List[str] = None
    ) -> bool:
        """
        レジーム変化通知
        
        Args:
            old_regime: 以前のレジーム
            new_regime: 新しいレジーム
            affected_symbols: 影響を受けた銘柄のリスト
        
        Returns:
            True=成功、False=失敗
        """
        if not self.discord_notifier:
            return False
        
        return self.discord_notifier.notify_regime_change(
            old_regime,
            new_regime,
            affected_symbols
        )
