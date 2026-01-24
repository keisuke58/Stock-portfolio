"""
Line通知モジュール
状態変化 or Daily pick を通知
"""
import logging
import requests
from typing import Optional
from datetime import datetime

from core.retry import retry_with_backoff
from core.circuit_breaker import CircuitBreaker, CircuitOpenError

logger = logging.getLogger(__name__)

# Line circuit breaker
_line_circuit = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30.0,
    name="line"
)


class LineNotifier:
    """Line Notify APIに通知を送信するクラス"""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.api_url = 'https://notify-api.line.me/api/notify'

    def send(self, message: str) -> bool:
        """メッセージを送信（リトライ・サーキットブレーカー対応）"""
        try:
            return _line_circuit.call(self._send_with_retry, message)
        except CircuitOpenError as e:
            logger.warning(f"Line circuit open, skipping notification: {e}")
            return False
        except requests.RequestException as e:
            logger.error(f"Line notification failed after retries: {e}")
            return False

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        exceptions=(requests.RequestException,)
    )
    def _send_with_retry(self, message: str) -> bool:
        """リトライ付きメッセージ送信"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {'message': message}

        response = requests.post(self.api_url, headers=headers, data=data, timeout=10)
        response.raise_for_status()

        preview = message[:50].encode('ascii', errors='ignore').decode('ascii')
        logger.info(f"Line notification sent: {preview}...")
        return True
    
    def format_state_change_message(
        self,
        symbol: str,
        old_state: str,
        new_state: str,
        price: float
    ) -> str:
        """状態変化時のメッセージを生成"""
        emoji_map = {
            'WATCH': '⚠️',
            'BASE': '📊',
            'BUY': '🚀',
            'NORMAL': '📈'
        }
        
        state_names = {
            'WATCH': '急落検知（WATCH入り）',
            'BASE': '低迷継続（BASE入り）',
            'BUY': '反転シグナル（BUY候補）',
            'NORMAL': '通常状態'
        }
        
        emoji = emoji_map.get(new_state, '📌')
        state_name = state_names.get(new_state, new_state)
        
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        if old_state is None:
            msg = f"{emoji} {symbol} 状態更新: {state_name}\n"
        else:
            msg = f"{emoji} {symbol} 状態変化: {old_state} → {new_state}\n"
            msg += f"{state_name}\n"
        
        msg += f"現在価格: ${price:,.2f}\n"
        msg += f"時刻: {timestamp}\n"
        
        # 仮想通貨か米国株かでURLを変更
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from signals import is_crypto_symbol
        if is_crypto_symbol(symbol):
            msg += f"https://www.coingecko.com/en/coins/{symbol.lower()}"
        else:
            msg += f"https://finance.yahoo.com/quote/{symbol.upper()}"
        
        return msg
    
    def format_daily_pick_message(self, daily_pick: dict) -> str:
        """Daily pickのメッセージを生成"""
        symbol = daily_pick['symbol']
        category = daily_pick.get('asset_category', 'その他')
        state = daily_pick.get('current_state', 'NORMAL')
        total_score = daily_pick.get('total_score', 0)
        confidence = daily_pick.get('confidence', 'Spec')
        
        value_score = daily_pick.get('value_score', 0)
        momentum_score = daily_pick.get('momentum_score', 0)
        stability_score = daily_pick.get('stability_score', 0)
        
        current_price = daily_pick.get('current_price', 0)
        ath_ratio = daily_pick.get('ath_ratio')
        return_30d = daily_pick.get('return_30d')
        
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # 信頼度の絵文字
        confidence_emoji = {
            'High': '🟢',
            'Mid': '🟡',
            'Spec': '🟠'
        }
        
        emoji = confidence_emoji.get(confidence, '⚪')
        
        msg = f"{emoji} 【今日の1個】{symbol}\n"
        msg += f"信頼度: {confidence} | 状態: {state} | カテゴリ: {category}\n"
        msg += f"\n投資スコア: {total_score:.1f}/100点\n"
        msg += f"  • Value（割安度）: {value_score:.1f}/100\n"
        msg += f"  • Momentum（反転）: {momentum_score:.1f}/100\n"
        msg += f"  • Stability（安定性）: {stability_score:.1f}/100\n"
        
        msg += f"\n基本情報\n"
        msg += f"  現在価格: ${current_price:,.2f}\n"
        
        if ath_ratio:
            msg += f"  ATH比: {ath_ratio:.1%} (ATHから{(1-ath_ratio)*100:.1f}%下落)\n"
        
        if return_30d:
            msg += f"  30日リターン: {return_30d:+.1f}%\n"
        
        msg += f"\n時刻: {timestamp}\n"
        
        # URL
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from signals import is_crypto_symbol
        if is_crypto_symbol(symbol):
            msg += f"https://www.coingecko.com/en/coins/{symbol.lower()}"
        else:
            msg += f"https://finance.yahoo.com/quote/{symbol.upper()}"
        
        return msg
    
    def notify_state_change(
        self,
        symbol: str,
        old_state: str,
        new_state: str,
        price: float
    ) -> bool:
        """状態変化を通知"""
        message = self.format_state_change_message(symbol, old_state, new_state, price)
        return self.send(message)
    
    def notify_daily_pick(self, daily_pick: dict) -> bool:
        """Daily pickを通知"""
        message = self.format_daily_pick_message(daily_pick)
        return self.send(message)
