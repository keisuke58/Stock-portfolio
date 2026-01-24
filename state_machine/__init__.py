"""
State Machine: 状態遷移管理モジュール
- WATCH: 5日リターン <= -10%
- BASE: 直近5日がレンジ±5%以内（横ばい必須）
- BUY: BASEの後に直近高値ブレイク（例: close > rolling_max(20)）
"""
from .state_machine import StateMachine

__all__ = ['StateMachine']
