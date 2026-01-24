"""
シグナル判定サービス
StateMachineをラップ
"""
from typing import Optional, Tuple
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from signals import StateMachine, determine_state, is_crypto_symbol


class SignalService:
    """シグナル判定サービス"""
    
    def __init__(self):
        """初期化"""
        self.state_machine = StateMachine()
    
    def determine_state(
        self,
        symbol: str,
        current_state: Optional[str] = None
    ) -> str:
        """
        現在の状態を判定
        
        Args:
            symbol: シンボル名
            current_state: 現在の状態（オプション）
        
        Returns:
            状態（'NORMAL', 'WATCH', 'BASE', 'BUY'）
        """
        return self.state_machine.determine_state(symbol, current_state)
    
    def detect_watch_signal(self, symbol: str) -> Tuple[bool, Optional[float]]:
        """
        WATCHシグナル（急落）を検出
        
        Args:
            symbol: シンボル名
        
        Returns:
            (検出されたか, 3日リターン値)
        """
        return self.state_machine.detect_watch_signal(symbol)
    
    def detect_base_signal(self, symbol: str) -> Tuple[bool, Optional[float]]:
        """
        BASEシグナル（低迷）を検出
        
        Args:
            symbol: シンボル名
        
        Returns:
            (検出されたか, レンジ幅%)
        """
        return self.state_machine.detect_base_signal(symbol)
    
    def detect_buy_signal(self, symbol: str) -> Tuple[bool, Optional[float]]:
        """
        BUYシグナル（反転）を検出
        
        Args:
            symbol: シンボル名
        
        Returns:
            (検出されたか, 現在価格)
        """
        return self.state_machine.detect_buy_signal(symbol)
    
    def is_crypto(self, symbol: str) -> bool:
        """
        シンボルが仮想通貨かどうかを判定
        
        Args:
            symbol: シンボル名
        
        Returns:
            True=仮想通貨、False=その他
        """
        return is_crypto_symbol(symbol)
